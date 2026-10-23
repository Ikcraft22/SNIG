import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.inventory_manager import GestorInventario
from core.pos_manager import GestorPOS
from database.connection import Base
from database.models import Presentacion, Producto, SyncChange, TipoPresentacion


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_inventario_rechaza_datos_invalidos_y_movimientos_inconsistentes(db_session):
    inventario = GestorInventario(db_session)
    assert inventario.registrar_producto("", "Producto") is None
    assert inventario.registrar_producto("750000000001", "  ") is None

    producto = inventario.registrar_producto("750000000001", "Cuaderno")
    assert inventario.agregar_presentacion(
        producto.id, "unidad", 1, 10, 20, stock_inicial=-1
    ) is None
    assert inventario.agregar_presentacion(
        producto.id, "unidad", 0, 10, 20
    ) is None

    presentacion = inventario.agregar_presentacion(producto.id, "unidad", 1, 10, 20, 5)
    otro_producto = inventario.registrar_producto("750000000002", "Lápiz")
    assert inventario.registrar_movimiento(
        otro_producto.id, presentacion.id, "entrada", 2
    ) is None
    assert inventario.registrar_movimiento(
        producto.id, presentacion.id, "salida", 6
    ) is None
    assert presentacion.stock_actual == 5


def test_movimiento_de_ajuste_actualiza_stock_de_forma_atomica(db_session):
    inventario = GestorInventario(db_session)
    producto = inventario.registrar_producto("750000000005", "Marcador")
    presentacion = inventario.agregar_presentacion(producto.id, "unidad", 1, 2, 5, 4)

    movimiento = inventario.registrar_movimiento(
        producto.id, presentacion.id, "ajuste", -2
    )

    assert movimiento is not None
    assert db_session.query(Presentacion).filter_by(id=presentacion.id).one().stock_actual == 2
    assert inventario.registrar_movimiento(
        producto.id, presentacion.id, "ajuste", -3
    ) is None
    assert db_session.query(Presentacion).filter_by(id=presentacion.id).one().stock_actual == 2


def test_cambios_de_inventario_y_eliminaciones_se_registran_para_sync(db_session):
    inventario = GestorInventario(db_session)
    producto = inventario.registrar_producto("750000000006", "Tiza")
    presentacion = inventario.agregar_presentacion(producto.id, "unidad", 1, 1, 3, 2)
    cursor = db_session.query(SyncChange.id).order_by(SyncChange.id.desc()).first()[0]

    movimiento = inventario.registrar_movimiento(
        producto.id, presentacion.id, "entrada", 4
    )
    cambios = db_session.query(SyncChange).filter(SyncChange.id > cursor).all()

    assert movimiento is not None
    assert any(
        cambio.entity_type == "presentaciones"
        and cambio.operation == "upsert"
        and '"stock_actual": 6' in cambio.payload
        for cambio in cambios
    )
    assert any(
        cambio.entity_type == "movimientos_inventario"
        and cambio.operation == "upsert"
        for cambio in cambios
    )

    cursor_eliminacion = max(cambio.id for cambio in cambios)
    assert inventario.eliminar_producto(producto.id)
    eliminaciones = db_session.query(SyncChange).filter(
        SyncChange.id > cursor_eliminacion,
        SyncChange.entity_type == "productos",
        SyncChange.entity_id == producto.id,
        SyncChange.operation == "delete",
    ).all()
    assert len(eliminaciones) == 1


def test_alertas_de_stock_incluyen_productos_en_minimo_y_clasifican_urgencia(db_session):
    inventario = GestorInventario(db_session)
    producto = inventario.registrar_producto("750000000003", "Borrador")
    presentacion = inventario.agregar_presentacion(producto.id, "unidad", 1, 1, 2, 9)
    presentacion.stock_minimo = 10
    db_session.commit()

    alertas = inventario.obtener_productos_stock_bajo()

    assert len(alertas) == 1
    assert alertas[0]["urgencia"] == "BAJO"
    assert alertas[0]["stock_actual"] == 9


def test_pos_no_vende_stock_insuficiente_ni_metodo_de_pago_desconocido(db_session):
    producto = Producto(gtin="750000000004", nombre="Regla")
    db_session.add(producto)
    db_session.flush()
    presentacion = Presentacion(
        producto_id=producto.id,
        tipo=TipoPresentacion.UNIDAD,
        cantidad=1,
        precio_unitario=5,
        precio_venta=10,
        stock_actual=1,
    )
    db_session.add(presentacion)
    db_session.commit()

    pos = GestorPOS(db_session)
    pos.carrito.agregar_item(producto.id, presentacion.id, 2, 10)
    assert pos.crear_venta("TK-TEST-1", "efectivo", "cajero") is None
    assert db_session.query(Presentacion).filter_by(id=presentacion.id).one().stock_actual == 1

    pos.carrito.vaciar_carrito()
    pos.carrito.agregar_item(producto.id, presentacion.id, 1, 10)
    assert pos.crear_venta("TK-TEST-2", "cheque", "cajero") is None
    assert db_session.query(Presentacion).filter_by(id=presentacion.id).one().stock_actual == 1


def test_carrito_rechaza_precios_y_cantidades_invalidos():
    from core.pos_manager import CarritoCompra

    carrito = CarritoCompra()
    assert not carrito.agregar_item(1, 1, 1, 0)
    assert not carrito.agregar_item(1, 1, 1.5, 10)
    assert not carrito.agregar_item(1, 1, 1, float("nan"))
