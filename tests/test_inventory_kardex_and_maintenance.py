"""Pruebas TDD para Kardex de movimientos, backups con rotación y optimización SQLite (Pasos 6.2, 6.3 y 6.4)."""

import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.connection import Base
from database.models import Producto, Presentacion, TipoPresentacion, MovimientoInventario, EstadoMovimiento
from core.inventory_manager import GestorInventario


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def test_obtener_kardex_producto(db_session):
    gestor = GestorInventario(db_session)
    prod = Producto(gtin="770000000001", nombre="Arroz 1kg")
    db_session.add(prod)
    db_session.flush()

    pres = Presentacion(
        producto_id=prod.id,
        tipo=TipoPresentacion.UNIDAD,
        precio_unitario=2000.0,
        precio_venta=2500.0,
        stock_actual=10,
    )
    db_session.add(pres)
    db_session.flush()

    # Registrar entradas y salidas
    mov1 = MovimientoInventario(
        producto_id=prod.id,
        presentacion_id=pres.id,
        tipo_movimiento=EstadoMovimiento.ENTRADA,
        cantidad=15,
        razon="Compra inicial",
        usuario="admin",
    )
    mov2 = MovimientoInventario(
        producto_id=prod.id,
        presentacion_id=pres.id,
        tipo_movimiento=EstadoMovimiento.SALIDA,
        cantidad=5,
        razon="Venta ticket",
        usuario="cajero",
    )
    db_session.add_all([mov1, mov2])
    db_session.commit()

    # Consultar Kardex
    kardex = gestor.obtener_kardex_producto(producto_id=prod.id)
    assert len(kardex) == 2
    assert kardex[0]["tipo_movimiento"] == "entrada"
    assert kardex[0]["cantidad"] == 15
    assert kardex[1]["tipo_movimiento"] == "salida"
    assert kardex[1]["cantidad"] == 5


def test_rotacion_backups_antiguos(tmp_path):
    # Crear directorio simulado con backups viejos (> 15 días) y recientes
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    ahora = time.time()
    dia_segundos = 86400

    archivo_viejo = backup_dir / "backup_inventario_20260101_120000.db"
    archivo_viejo.write_text("viejo")
    # Modificar mtime para simular 20 días de antigüedad
    os.utime(archivo_viejo, (ahora - (20 * dia_segundos), ahora - (20 * dia_segundos)))

    archivo_reciente = backup_dir / "backup_inventario_20261110_120000.db"
    archivo_reciente.write_text("reciente")
    os.utime(archivo_reciente, (ahora - (2 * dia_segundos), ahora - (2 * dia_segundos)))

    gestor = GestorInventario(None)
    eliminados = gestor.rotar_backups_antiguos(backup_dir=str(backup_dir), dias_retencion=15)

    assert eliminados == 1
    assert not archivo_viejo.exists()
    assert archivo_reciente.exists()


def test_optimizar_base_de_datos(db_session):
    gestor = GestorInventario(db_session)
    resultado = gestor.optimizar_base_de_datos()
    assert resultado["exito"] is True
    assert "vacuum" in resultado["operaciones"]
    assert "analyze" in resultado["operaciones"]
