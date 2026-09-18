"""
Servicio Dispatch — Café Express Distribuido

Simula el despacho/entrega de un pedido ya preparado. Misma forma que
Kitchen: recibe la orden de procesar, responde 202 de inmediato y hace
el trabajo en un hilo de un ThreadPoolExecutor, reportando el avance a
Orders mediante PATCH.

Puerto por defecto: 8004
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

logging.basicConfig(level=logging.INFO, format="[dispatch] %(asctime)s %(message)s")
logger = logging.getLogger("dispatch")

ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:8001")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
TIEMPO_MIN = float(os.getenv("TIEMPO_MIN_SEGUNDOS", "0.5"))
TIEMPO_MAX = float(os.getenv("TIEMPO_MAX_SEGUNDOS", "1.5"))

app = FastAPI(title="Café Express Distribuido — Dispatch")
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


def _despachar_pedido(pedido_id: int) -> None:
    logger.info("despachando pedido %s", pedido_id)
    _patch_estado(pedido_id, "EN_DESPACHO")
    time.sleep(random.uniform(TIEMPO_MIN, TIEMPO_MAX))  # simula tiempo de entrega
    _patch_estado(pedido_id, "ENTREGADO")
    logger.info("pedido %s entregado", pedido_id)


@app.get("/health")
def health():
    return {"status": "ok", "service": "dispatch", "max_workers": MAX_WORKERS}


@app.post("/procesar", status_code=202)
def procesar(payload: Procesar):
    _pool.submit(_despachar_pedido, payload.pedido_id)
    return {"status": "accepted", "pedido_id": payload.pedido_id}
