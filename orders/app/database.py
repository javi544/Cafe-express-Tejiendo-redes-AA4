"""
Configuración de la base de datos del servicio Orders.

Orders es el ÚNICO servicio con persistencia propia dentro de la
arquitectura distribuida (los demás servicios son sin estado / stateless).
Usa SQLite por defecto; puede apuntarse a otra base vía DATABASE_URL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pedidos.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
