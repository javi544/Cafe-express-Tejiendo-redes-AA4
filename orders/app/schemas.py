from pydantic import BaseModel, Field
from typing import List, Optional


class ItemPedido(BaseModel):
    producto: str
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)


class PedidoCreate(BaseModel):
    cliente: str
    items: List[ItemPedido]


class CambioEstado(BaseModel):
    estado: str


class HistorialEntry(BaseModel):
    estado: str
    timestamp: str


class PedidoOut(BaseModel):
    id: int
    cliente: str
    items: List[ItemPedido]
    total: float
    estado: str
    historial: List[HistorialEntry]
    creado_en: Optional[str] = None

    class Config:
        from_attributes = True
