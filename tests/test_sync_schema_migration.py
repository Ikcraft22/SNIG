"""Pruebas TDD para la migración de identidades globales UUID y bajas lógicas (tombstones)."""

import uuid
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from database.connection import Base
from database.migrations import asegurar_columnas_uuid_y_tombstone
from database.models import (
    MovimientoInventario,
    Presentacion,
    Producto,
    Proveedor,
    TipoPresentacion,
    Venta,
    VentaItem,
)


def test_migracion_agrega_columnas_uuid_y_eliminado_a_tablas_existentes():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE productos (id INTEGER PRIMARY KEY, gtin VARCHAR(20), nombre VARCHAR(255))"))
        conn.execute(text("INSERT INTO productos (id, gtin, nombre) VALUES (1, '750100', 'Producto Viejo')"))
        conn.execute(text("CREATE TABLE proveedores (id INTEGER PRIMARY KEY, nombre VARCHAR(255))"))
        conn.execute(text("INSERT INTO proveedores (id, nombre) VALUES (1, 'Proveedor Viejo')"))

    aplicado = asegurar_columnas_uuid_y_tombstone(engine)
    assert aplicado is True

    inspector = inspect(engine)
    cols_prod = {c["name"]: c for c in inspector.get_columns("productos")}
    assert "uuid" in cols_prod
    assert "eliminado" in cols_prod
    assert "fecha_eliminacion" in cols_prod

    cols_prov = {c["name"]: c for c in inspector.get_columns("proveedores")}
    assert "uuid" in cols_prov
    assert "eliminado" in cols_prov

    with engine.connect() as conn:
        fila = conn.execute(text("SELECT id, gtin, uuid, eliminado FROM productos WHERE id = 1")).mappings().one()
        assert fila["id"] == 1
        assert fila["eliminado"] == 0
        # Debe haber generado un UUID válido para registros existentes
        uuid_obj = uuid.UUID(fila["uuid"])
        assert str(uuid_obj) == fila["uuid"]


def test_modelos_orm_tienen_uuid_generado_automaticamente_y_eliminado_por_defecto():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    prod = Producto(gtin="1234567890123", nombre="Cuaderno Pro")
    prov = Proveedor(nombre="Distribuidora Alfa")
    session.add_all([prod, prov])
    session.flush()

    assert prod.uuid is not None
    assert len(prod.uuid) == 36
    assert prod.eliminado is False
    assert prod.fecha_eliminacion is None

    assert prov.uuid is not None
    assert len(prov.uuid) == 36
    assert prov.eliminado is False

    pres = Presentacion(
        producto_id=prod.id,
        tipo=TipoPresentacion.UNIDAD,
        precio_unitario=10.0,
        precio_venta=15.0,
        stock_actual=50,
    )
    session.add(pres)
    session.flush()

    assert pres.uuid is not None
    assert pres.eliminado is False

    session.close()
    engine.dispose()
