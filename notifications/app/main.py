"""
Servicio Notifications — Café Express Distribuido

Aplica el patrón Observer: se suscribe (vía el Mediator) a TODOS los
tipos de evento del ciclo de vida de un pedido, sin necesidad de que
Orders, Kitchen o Dispatch sepan que existe. Aquí, "notificar" se
simula guardando cada aviso en memoria y por log; en un sistema real
este servicio sería el que envía el correo, el push o el SMS al
cliente.

Puerto por defecto: 8005
"""
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[notifications] %(asctime)s %(message)s")
logger = logging.getLogger("notifications")

app = FastAPI(title="Café Express Distribuido — Notifications")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MENSAJES = {
    "pedido_creado": "Hemos recibido tu pedido #{id}.",
    "pedido_en_preparacion": "Tu pedido #{id} está en preparación.",
    "pedido_listo": "Tu pedido #{id} está listo.",
    "pedido_en_despacho": "Tu pedido #{id} está en camino.",
    "pedido_entregado": "Tu pedido #{id} fue entregado. ¡Buen provecho!",
    "pedido_cancelado": "Tu pedido #{id} fue cancelado.",
}

_NOTIFICACIONES: list = []
_MAX_HISTORIAL = 500


class Notificar(BaseModel):
    pedido_id: int
    evento: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "notifications"}


@app.post("/notificar", status_code=201)
def notificar(payload: Notificar):
    mensaje = MENSAJES.get(payload.evento, f"Actualización de pedido: {payload.evento}").format(id=payload.pedido_id)
    registro = {
        "pedido_id": payload.pedido_id,
        "evento": payload.evento,
        "mensaje": mensaje,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _NOTIFICACIONES.append(registro)
    if len(_NOTIFICACIONES) > _MAX_HISTORIAL:
        del _NOTIFICACIONES[: len(_NOTIFICACIONES) - _MAX_HISTORIAL]

    logger.info("%s", mensaje)
    return registro


@app.get("/notificaciones")
def listar_notificaciones():
    return list(reversed(_NOTIFICACIONES))


@app.get("/notificaciones/{pedido_id}")
def notificaciones_de_pedido(pedido_id: int):
    return [n for n in reversed(_NOTIFICACIONES) if n["pedido_id"] == pedido_id]
