"""
Servicio Orders — Café Express Distribuido

Responsabilidad única: es la fuente de verdad del ciclo de vida de un
pedido (crear, consultar, cambiar de estado). NO conoce a Kitchen, a
Dispatch ni a Notifications: cada vez que cambia el estado de un pedido,
publica un evento al Mediator (patrón Mediator) y sigue su camino. Quién
reacciona a ese evento es decisión exclusiva del Mediator.

Puerto por defecto: 8001
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, SessionLocal, engine, get_db

logging.basicConfig(level=logging.INFO, format="[orders] %(asctime)s %(message)s")
logger = logging.getLogger("orders")

Base.metadata.create_all(bind=engine)

MEDIATOR_URL = os.getenv("MEDIATOR_URL", "http://localhost:8002")

app = FastAPI(title="Café Express Distribuido — Orders")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Pool dedicado SOLO a publicar eventos al Mediator, para que la respuesta
# al cliente (o al proxy) nunca espere a que el evento se entregue: esto es
# justamente lo que representan las flechas "->>" (async) del diagrama de
# secuencia.
_event_pool = ThreadPoolExecutor(max_workers=int(os.getenv("EVENT_WORKERS", "4")))

ESTADOS_VALIDOS = [
    "CREADO",
    "EN_PREPARACION",
    "LISTO",
    "EN_DESPACHO",
    "ENTREGADO",
    "CANCELADO",
]

TRANSICIONES_VALIDAS = {
    "CREADO": ["EN_PREPARACION", "CANCELADO"],
    "EN_PREPARACION": ["LISTO", "CANCELADO"],
    "LISTO": ["EN_DESPACHO"],
    "EN_DESPACHO": ["ENTREGADO"],
    "ENTREGADO": [],
    "CANCELADO": [],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _publicar_evento(tipo_evento: str, pedido_id: int) -> None:
    """Publica un evento en el Mediator. Se ejecuta en un hilo del pool
    de eventos: si el Mediator está lento o caído, no afecta la respuesta
    ya entregada al cliente (tolerancia a fallos básica)."""
    try:
        requests.post(
            f"{MEDIATOR_URL}/eventos",
            json={"tipo": tipo_evento, "pedido_id": pedido_id},
            timeout=5,
        )
    except requests.RequestException as exc:
        logger.warning("no se pudo publicar evento %s para pedido %s: %s", tipo_evento, pedido_id, exc)


def _emitir(tipo_evento: str, pedido_id: int) -> None:
    _event_pool.submit(_publicar_evento, tipo_evento, pedido_id)


def _to_out(p: models.Pedido) -> dict:
    return {
        "id": p.id,
        "cliente": p.cliente,
        "items": p.items_list(),
        "total": p.total,
        "estado": p.estado,
        "historial": p.historial_list(),
        "creado_en": p.creado_en.isoformat() if p.creado_en else None,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "orders"}


@app.post("/pedidos", status_code=201)
def crear_pedido(payload: schemas.PedidoCreate, db: Session = Depends(get_db)):
    total = sum(item.cantidad * item.precio_unitario for item in payload.items)
    historial = [{"estado": "CREADO", "timestamp": _now_iso()}]

    pedido = models.Pedido(
        cliente=payload.cliente,
        items=json.dumps([item.model_dump() for item in payload.items]),
        total=total,
        estado="CREADO",
        historial=json.dumps(historial),
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    _emitir("pedido_creado", pedido.id)

    return _to_out(pedido)


@app.get("/pedidos")
def listar_pedidos(db: Session = Depends(get_db)):
    pedidos = db.query(models.Pedido).order_by(models.Pedido.id.desc()).all()
    return [_to_out(p) for p in pedidos]


@app.get("/pedidos/{pedido_id}")
def obtener_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return _to_out(pedido)


@app.patch("/pedidos/{pedido_id}/estado")
def cambiar_estado(pedido_id: int, payload: schemas.CambioEstado, db: Session = Depends(get_db)):
    nuevo_estado = payload.estado.upper()

    if nuevo_estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Estado inválido: {nuevo_estado}")

    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    permitidos = TRANSICIONES_VALIDAS.get(pedido.estado, [])
    if nuevo_estado not in permitidos:
        raise HTTPException(
            status_code=409,
            detail=f"Transición no permitida: {pedido.estado} -> {nuevo_estado}",
        )

    historial = pedido.historial_list()
    historial.append({"estado": nuevo_estado, "timestamp": _now_iso()})

    pedido.estado = nuevo_estado
    pedido.historial = json.dumps(historial)
    db.commit()
    db.refresh(pedido)

    # El nombre del evento se deriva directamente del nuevo estado:
    # EN_PREPARACION -> pedido_en_preparacion, LISTO -> pedido_listo, etc.
    _emitir(f"pedido_{nuevo_estado.lower()}", pedido.id)

    return _to_out(pedido)
