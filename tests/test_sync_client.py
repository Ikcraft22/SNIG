"""Pruebas TDD para el Cliente de Sincronización Multi-sucursal (Paso 4.2.3)."""

import json
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.connection import Base
from database.models import (
    Producto,
    Presentacion,
    TipoPresentacion,
    Proveedor,
    MovimientoInventario,
    Venta,
    VentaItem,
    SyncChange,
    SyncState,
)
from core.sync_client import ClienteSincronizacion, ResultadoSincronizacion


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def test_cliente_sincronizacion_inicializacion(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="secreto-token",
        nodo_id="sucursal-norte",
    )
    assert cliente.servidor_url == "http://testserver:5000"
    assert cliente.api_token == "secreto-token"
    assert cliente.nodo_id == "sucursal-norte"
    assert cliente.obtener_cursor_local() == 0


def test_descargar_cambios_aplica_cursor_y_headers(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="token-abc",
        nodo_id="nodo-1",
    )

    respuesta_mock = Mock()
    respuesta_mock.status_code = 200
    respuesta_mock.json.return_value = {
        "changes": [
            {
                "cursor": 1,
                "entity_type": "productos",
                "entity_id": 1,
                "operation": "upsert",
                "payload": {"uuid": "u-prod-1", "gtin": "770111", "nombre": "Arroz 1kg", "eliminado": False},
                "occurred_at": "2026-11-12T10:00:00",
            }
        ],
        "next_cursor": 1,
        "has_more": False,
    }

    with patch("requests.get", return_value=respuesta_mock) as mock_get:
        datos = cliente.descargar_novedades_remotas(cursor=0, limit=50)
        assert len(datos["changes"]) == 1
        assert datos["next_cursor"] == 1
        mock_get.assert_called_once_with(
            "http://testserver:5000/api/sync/changes?cursor=0&limit=50",
            headers={"Authorization": "Bearer token-abc"},
            timeout=15,
        )


def test_aplicar_cambio_remoto_upsert_producto(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="token-abc",
        nodo_id="nodo-cliente",
    )

    cambio = {
        "cursor": 5,
        "entity_type": "productos",
        "entity_id": 10,
        "operation": "upsert",
        "payload": {
            "uuid": "prod-uuid-999",
            "gtin": "7709999999999",
            "nombre": "Aceite Vegetal 900ml",
            "descripcion": "Aceite para cocina",
            "eliminado": False,
        },
    }

    resultado = cliente.aplicar_cambio_remoto(cambio)
    assert resultado is True

    # Verificar que el producto fue creado localmente con su UUID
    prod = db_session.query(Producto).filter_by(uuid="prod-uuid-999").first()
    assert prod is not None
    assert prod.nombre == "Aceite Vegetal 900ml"
    assert prod.gtin == "7709999999999"

    # Verificar que al ser un cambio remoto, NO disparó SyncChange local (anti-eco)
    assert db_session.query(SyncChange).count() == 0


def test_aplicar_cambio_remoto_lww_actualiza_producto_existente(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="token-abc",
        nodo_id="nodo-cliente",
    )

    # Crear producto local inicial
    prod_local = Producto(
        uuid="prod-uuid-123",
        gtin="770123",
        nombre="Nombre Viejo",
    )
    db_session.add(prod_local)
    db_session.commit()

    # Cambio remoto con actualización
    cambio = {
        "cursor": 8,
        "entity_type": "productos",
        "operation": "upsert",
        "payload": {
            "uuid": "prod-uuid-123",
            "gtin": "770123",
            "nombre": "Nombre Actualizado Remotamente",
            "eliminado": False,
        },
    }

    resultado = cliente.aplicar_cambio_remoto(cambio)
    assert resultado is True

    db_session.refresh(prod_local)
    assert prod_local.nombre == "Nombre Actualizado Remotamente"


def test_aplicar_cambio_remoto_tombstone_baja_logica(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="token-abc",
        nodo_id="nodo-cliente",
    )

    prod = Producto(
        uuid="prod-a-eliminar",
        gtin="770888",
        nombre="Producto Activo",
        eliminado=False,
    )
    db_session.add(prod)
    db_session.commit()

    cambio_tombstone = {
        "cursor": 9,
        "entity_type": "productos",
        "operation": "upsert",
        "payload": {
            "uuid": "prod-a-eliminar",
            "gtin": "770888",
            "nombre": "Producto Activo",
            "eliminado": True,
            "fecha_eliminacion": "2026-11-12T10:15:00",
        },
    }

    cliente.aplicar_cambio_remoto(cambio_tombstone)
    db_session.refresh(prod)
    assert prod.eliminado is True


def test_aplicar_venta_remota_inmutable_e_idempotente(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="token-abc",
        nodo_id="nodo-cliente",
    )

    cambio_venta = {
        "cursor": 12,
        "entity_type": "ventas",
        "operation": "upsert",
        "payload": {
            "uuid": "venta-uuid-777",
            "numero_ticket": "TK-20261112-0001",
            "total": 150.0,
            "subtotal": 150.0,
            "descuento": 0.0,
            "metodo_pago": "efectivo",
            "usuario": "cajero1",
            "fecha": "2026-11-12T09:30:00",
        },
    }

    # Primera aplicación: inserta la venta
    assert cliente.aplicar_cambio_remoto(cambio_venta) is True
    assert db_session.query(Venta).filter_by(uuid="venta-uuid-777").count() == 1

    # Segunda aplicación (idempotencia / ledger inmutable): no duplica ni falla
    assert cliente.aplicar_cambio_remoto(cambio_venta) is True
    assert db_session.query(Venta).filter_by(uuid="venta-uuid-777").count() == 1


def test_sincronizar_ciclo_completo_actualiza_cursor_local(db_session):
    cliente = ClienteSincronizacion(
        db=db_session,
        servidor_url="http://testserver:5000",
        api_token="token-abc",
        nodo_id="nodo-sucursal",
    )

    # Simular lote de 2 novedades en servidor
    respuesta_mock = Mock()
    respuesta_mock.status_code = 200
    respuesta_mock.json.return_value = {
        "changes": [
            {
                "cursor": 1,
                "entity_type": "proveedores",
                "operation": "upsert",
                "payload": {"uuid": "prov-1", "nombre": "Proveedor Central", "eliminado": False},
            },
            {
                "cursor": 2,
                "entity_type": "productos",
                "operation": "upsert",
                "payload": {"uuid": "prod-1", "gtin": "12345", "nombre": "Pan Tajado", "eliminado": False},
            },
        ],
        "next_cursor": 2,
        "has_more": False,
    }

    with patch("requests.get", return_value=respuesta_mock):
        resultado = cliente.sincronizar_desde_remoto()

    assert isinstance(resultado, ResultadoSincronizacion)
    assert resultado.exitoso is True
    assert resultado.cambios_aplicados == 2
    assert cliente.obtener_cursor_local() == 2

    # El proveedor y el producto deben existir en la base local
    assert db_session.query(Proveedor).filter_by(uuid="prov-1").first() is not None
    assert db_session.query(Producto).filter_by(uuid="prod-1").first() is not None
