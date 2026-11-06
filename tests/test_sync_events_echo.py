"""Pruebas TDD para el registro enriquecido de eventos de sincronización y prevención de eco."""

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.connection import Base
from database.models import (
    Producto,
    SyncChange,
    sin_disparo_sync,
)


def test_sync_change_incluye_entity_uuid_y_origen_nodo_id():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    prod = Producto(gtin="7701234567890", nombre="Galletas Avena")
    session.add(prod)
    session.commit()

    # Verificar que el evento en SyncChange se registró con entity_uuid y origen_nodo_id
    evento = session.query(SyncChange).filter_by(entity_id=prod.id).one()
    assert evento.entity_uuid == prod.uuid
    assert evento.origen_nodo_id is not None
    assert len(evento.origen_nodo_id) > 0

    session.close()
    engine.dispose()


def test_context_manager_sin_disparo_sync_previene_bucles_de_eco():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Inserción normal: genera SyncChange
    prod1 = Producto(gtin="1111111111111", nombre="Producto Local")
    session.add(prod1)
    session.commit()
    assert session.query(SyncChange).filter_by(entity_id=prod1.id).count() == 1

    # Inserción dentro del context manager: NO debe generar SyncChange
    with sin_disparo_sync():
        prod2 = Producto(gtin="2222222222222", nombre="Producto Remoto")
        session.add(prod2)
        session.commit()

    assert session.query(SyncChange).filter_by(entity_id=prod2.id).count() == 0

    # Fuera del context manager vuelve a registrar normalmente
    prod3 = Producto(gtin="3333333333333", nombre="Otro Producto Local")
    session.add(prod3)
    session.commit()
    assert session.query(SyncChange).filter_by(entity_id=prod3.id).count() == 1

    session.close()
    engine.dispose()
