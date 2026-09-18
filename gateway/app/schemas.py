from typing import List

from pydantic import BaseModel, Field


class ItemPedido(BaseModel):
    producto: str
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)


class PedidoCreate(BaseModel):
    cliente: str
    items: List[ItemPedido]


class CambioEstado(BaseModel):
    estado: str
