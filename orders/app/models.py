import json
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from .database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String, nullable=False)
    items = Column(Text, nullable=False)          # JSON: [{producto, cantidad, precio_unitario}]
    total = Column(Float, default=0.0)
    estado = Column(String, default="CREADO", index=True)
    historial = Column(Text, default="[]")        # JSON: [{estado, timestamp}]
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())

    def items_list(self):
        return json.loads(self.items)

    def historial_list(self):
        return json.loads(self.historial)
