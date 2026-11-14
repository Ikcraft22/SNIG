"""Pruebas TDD para Carritos en Espera / Multi-Ticket en POS (Paso 5.1)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.connection import Base
from core.pos_manager import CarritoCompra, GestorPOS


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def test_pausar_y_recuperar_carrito_en_espera(db_session):
    pos = GestorPOS(db_session)

    # Agregar productos al carrito activo
    pos.carrito.agregar_item(
        producto_id=1,
        presentacion_id=10,
        cantidad=2,
        precio_unitario=1500.0,
        producto_nombre="Galletas",
    )
    assert len(pos.carrito.items) == 1
    assert pos.carrito.total == 3000.0

    # Pausar carrito asignando etiqueta o identificador
    cart_id = pos.pausar_carrito(etiqueta="Cliente con prisa")
    assert cart_id is not None
    assert pos.contar_carritos_en_espera() == 1
    assert len(pos.carrito.items) == 0  # El carrito activo queda libre y limpio

    # Otro cliente llega y usa el carrito activo
    pos.carrito.agregar_item(
        producto_id=2,
        presentacion_id=20,
        cantidad=1,
        precio_unitario=5000.0,
        producto_nombre="Leche",
    )
    assert len(pos.carrito.items) == 1
    assert pos.carrito.total == 5000.0

    # Pausar también este segundo cliente
    cart_id_2 = pos.pausar_carrito(etiqueta="Cliente 2")
    assert pos.contar_carritos_en_espera() == 2
    assert len(pos.carrito.items) == 0

    # Listar carritos en espera
    lista = pos.listar_carritos_en_espera()
    assert len(lista) == 2
    assert any(c["id"] == cart_id and c["etiqueta"] == "Cliente con prisa" for c in lista)

    # Reanudar el primer carrito
    exito = pos.reanudar_carrito(cart_id)
    assert exito is True
    assert pos.contar_carritos_en_espera() == 1
    assert len(pos.carrito.items) == 1
    assert pos.carrito.items[0]["producto_nombre"] == "Galletas"
    assert pos.carrito.total == 3000.0


def test_descartar_carrito_en_espera(db_session):
    pos = GestorPOS(db_session)
    pos.carrito.agregar_item(
        producto_id=1,
        presentacion_id=10,
        cantidad=1,
        precio_unitario=100.0,
        producto_nombre="Jugo",
    )
    cart_id = pos.pausar_carrito("Cliente canceló")
    assert pos.contar_carritos_en_espera() == 1

    descartado = pos.descartar_carrito_en_espera(cart_id)
    assert descartado is True
    assert pos.contar_carritos_en_espera() == 0


def test_pausar_carrito_vacio_falla(db_session):
    pos = GestorPOS(db_session)
    assert pos.pausar_carrito("Carrito vacio") is None
    assert pos.contar_carritos_en_espera() == 0
