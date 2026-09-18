"""
Servicio Kitchen — Café Express Distribuido

Simula la preparación de un pedido. Recibe la orden de procesar un
pedido, la acepta de inmediato (202) y hace el trabajo pesado (la
"cocción") en un hilo de un ThreadPoolExecutor, para poder atender
muchas solicitudes concurrentes sin bloquear al Mediator que lo llama.

Kitchen NUNCA le habla al Mediator directamente: solo le hace PATCH a
Orders para reportar el nuevo estado. Es Orders quien, al cambiar de
estado, vuelve a publicar el evento correspondiente.

Puerto por defecto: 8003
"""
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[kitchen] %(asctime)s %(message)s")
logger = logging.getLogger("kitchen")

ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:8001")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
TIEMPO_MIN = float(os.getenv("TIEMPO_MIN_SEGUNDOS", "0.5"))
TIEMPO_MAX = float(os.getenv("TIEMPO_MAX_SEGUNDOS", "1.5"))

app = FastAPI(title="Café Express Distribuido — Kitchen")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)


class Procesar(BaseModel):
    pedido_id: int
    evento: str | None = None


def _patch_estado(pedido_id: int, estado: str) -> None:
    try:
        requests.patch(
            f"{ORDERS_URL}/pedidos/{pedido_id}/estado",
            json={"estado": estado},
            timeout=5,
        )
    except requests.RequestException as exc:
        logger.warning("no se pudo actualizar pedido %s a %s: %s", pedido_id, estado, exc)


def _preparar_pedido(pedido_id: int) -> None:
    logger.info("preparando pedido %s en hilo %s", pedido_id, os.getpid())
    _patch_estado(pedido_id, "EN_PREPARACION")
    time.sleep(random.uniform(TIEMPO_MIN, TIEMPO_MAX))  # simula tiempo de cocción
    _patch_estado(pedido_id, "LISTO")
    logger.info("pedido %s listo", pedido_id)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kitchen", "max_workers": MAX_WORKERS}


@app.post("/procesar", status_code=202)
def procesar(payload: Procesar):
    _pool.submit(_preparar_pedido, payload.pedido_id)
    return {"status": "accepted", "pedido_id": payload.pedido_id}
