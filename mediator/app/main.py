"""
Servicio Mediator — Café Express Distribuido

Aplica el patrón Mediator: es el ÚNICO servicio que conoce la existencia
de Kitchen, Dispatch y Notifications. Orders solo le habla a él (le
publica eventos); el Mediator decide, según una tabla de enrutamiento,
a quién reenviar cada evento. Esto desacopla a Orders de todos los
servicios "reactivos" del sistema: se puede agregar un séptimo servicio
que reaccione a los eventos sin tocar una sola línea de Orders.

Puerto por defecto: 8002
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[mediator] %(asctime)s %(message)s")
logger = logging.getLogger("mediator")

KITCHEN_URL = os.getenv("KITCHEN_URL", "http://localhost:8003")
DISPATCH_URL = os.getenv("DISPATCH_URL", "http://localhost:8004")
NOTIFICATIONS_URL = os.getenv("NOTIFICATIONS_URL", "http://localhost:8005")

app = FastAPI(title="Café Express Distribuido — Mediator")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_pool = ThreadPoolExecutor(max_workers=int(os.getenv("MEDIATOR_WORKERS", "8")))

# Tabla de enrutamiento: evento -> lista de (servicio, path) a notificar.
# Notifications se suscribe a TODOS los eventos (patrón Observer).
ROUTING_TABLE = {
    "pedido_creado": [(KITCHEN_URL, "/procesar"), (NOTIFICATIONS_URL, "/notificar")],
    "pedido_en_preparacion": [(NOTIFICATIONS_URL, "/notificar")],
    "pedido_listo": [(DISPATCH_URL, "/procesar"), (NOTIFICATIONS_URL, "/notificar")],
    "pedido_en_despacho": [(NOTIFICATIONS_URL, "/notificar")],
    "pedido_entregado": [(NOTIFICATIONS_URL, "/notificar")],
    "pedido_cancelado": [(NOTIFICATIONS_URL, "/notificar")],
}

# Bitácora en memoria de los últimos eventos, útil para depuración y demo.
_EVENTOS_RECIENTES: list = []
_MAX_HISTORIAL = 200


class Evento(BaseModel):
    tipo: str
    pedido_id: int


def _reenviar(base_url: str, path: str, tipo: str, pedido_id: int) -> None:
    try:
        requests.post(f"{base_url}{path}", json={"evento": tipo, "pedido_id": pedido_id}, timeout=5)
    except requests.RequestException as exc:
        logger.warning("fallo reenviando %s a %s%s: %s", tipo, base_url, path, exc)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mediator"}


@app.post("/eventos", status_code=202)
def recibir_evento(evento: Evento):
    destinos = ROUTING_TABLE.get(evento.tipo, [])

    _EVENTOS_RECIENTES.append(
        {
            "tipo": evento.tipo,
            "pedido_id": evento.pedido_id,
            "destinos": [f"{url}{path}" for url, path in destinos],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    if len(_EVENTOS_RECIENTES) > _MAX_HISTORIAL:
        del _EVENTOS_RECIENTES[: len(_EVENTOS_RECIENTES) - _MAX_HISTORIAL]

    for base_url, path in destinos:
        _pool.submit(_reenviar, base_url, path, evento.tipo, evento.pedido_id)

    return {"status": "routed", "tipo": evento.tipo, "destinos": len(destinos)}


@app.get("/eventos")
def historial_eventos():
    return list(reversed(_EVENTOS_RECIENTES))
