"""
Servicio Gateway — Café Express Distribuido

Aplica el patrón Proxy: es el ÚNICO punto de entrada público del
sistema. El cliente nunca le habla a Orders directamente; siempre pasa
por el Gateway, que reenvía ("proxea") la solicitud al servicio real y
devuelve la respuesta tal cual. Esto permite, sin tocar a los clientes,
agregar más adelante autenticación, límites de tasa (rate limiting) o
balanceo de carga en un solo lugar.

Puerto por defecto: 8000 (el único puerto publicado al host en Docker).
"""
import os
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .schemas import CambioEstado, PedidoCreate

ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:8001")

app = FastAPI(title="Café Express Distribuido — Gateway (Proxy)")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def _proxy_response(resp: requests.Response) -> Response:
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.post("/pedidos")
def crear_pedido(payload: PedidoCreate):
    try:
        resp = requests.post(f"{ORDERS_URL}/pedidos", json=payload.model_dump(), timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Servicio Orders no disponible")
    return _proxy_response(resp)


@app.get("/pedidos")
def listar_pedidos():
    try:
        resp = requests.get(f"{ORDERS_URL}/pedidos", timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Servicio Orders no disponible")
    return _proxy_response(resp)


@app.get("/pedidos/{pedido_id}")
def obtener_pedido(pedido_id: int):
    try:
        resp = requests.get(f"{ORDERS_URL}/pedidos/{pedido_id}", timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Servicio Orders no disponible")
    return _proxy_response(resp)


@app.patch("/pedidos/{pedido_id}/estado")
def cambiar_estado(pedido_id: int, payload: CambioEstado):
    try:
        resp = requests.patch(
            f"{ORDERS_URL}/pedidos/{pedido_id}/estado", json=payload.model_dump(), timeout=10
        )
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Servicio Orders no disponible")
    return _proxy_response(resp)


# Frontend estático: el Gateway, al ser el único punto de entrada público,
# también sirve la interfaz web del cliente. Se monta DESPUÉS de las rutas
# de la API para que /pedidos, /health, etc. tengan prioridad.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
