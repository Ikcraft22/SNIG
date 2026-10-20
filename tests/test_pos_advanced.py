from datetime import datetime, date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Producto, Presentacion, TipoPresentacion, Venta, VentaItem
from core.pos_manager import CarritoCompra, GestorPOS


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos en memoria para pruebas."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_carrito_modificar_cantidad_y_descuento():
    carrito = CarritoCompra()
    # Agregar item
    assert carrito.agregar_item(
        producto_id=1,
        presentacion_id=10,
        cantidad=2,
        precio_unitario=50.0,
        descuento=0.0,
        producto_nombre="Cuaderno",
        presentacion_nombre="unidad"
    ) is True
    assert carrito.total == 100

    # Modificar cantidad a 5
    assert carrito.modificar_cantidad_item(10, 5) is True
    assert carrito.total == 250
    item = next(it for it in carrito.items if it["presentacion_id"] == 10)
    assert item["cantidad"] == 5

    # Modificar cantidad a 0 debe rechazar o requerir eliminación
    assert carrito.modificar_cantidad_item(10, -1) is False

    # Aplicar descuento de 10%
    assert carrito.aplicar_descuento_item(10, 10.0) is True
    # 5 * 50 = 250 - 10% (25) = 225
    assert carrito.total == 225

    # Intentar aplicar descuento inválido
    assert carrito.aplicar_descuento_item(10, 150.0) is False
    assert carrito.aplicar_descuento_item(999, 10.0) is False


def test_cierre_de_caja_y_metricas_pos(db_session):
    pos = GestorPOS(db_session)

    # Crear producto y presentación con stock
    prod = Producto(gtin="750000000001", nombre="Producto Test", laboratorio="Lab")
    db_session.add(prod)
    db_session.commit()

    pres = Presentacion(
        producto_id=prod.id,
        tipo=TipoPresentacion.UNIDAD,
        cantidad=1,
        precio_unitario=20,
        precio_venta=40,
        stock_actual=100
    )
    db_session.add(pres)
    db_session.commit()

    # Venta 1: Efectivo ($80)
    pos.carrito.agregar_item(prod.id, pres.id, 2, 40, producto_nombre="Producto Test")
    t1 = pos.generar_numero_ticket()
    pos.crear_venta(t1, "efectivo", "Cajero1")

    # Venta 2: Tarjeta ($120)
    pos.carrito.agregar_item(prod.id, pres.id, 3, 40, producto_nombre="Producto Test")
    t2 = pos.generar_numero_ticket()
    pos.crear_venta(t2, "tarjeta", "Cajero1")

    # Venta 3: Transferencia ($40)
    pos.carrito.agregar_item(prod.id, pres.id, 1, 40, producto_nombre="Producto Test")
    t3 = pos.generar_numero_ticket()
    pos.crear_venta(t3, "transferencia", "Cajero2")

    hoy = date.today().isoformat()
    cierre = pos.obtener_metricas_cierre_caja(hoy)

    assert cierre["total_ingresos"] == 240
    assert cierre["cantidad_ventas"] == 3
    assert cierre["ticket_promedio"] == 80
    assert cierre["metodos_pago"]["efectivo"] == 80
    assert cierre["metodos_pago"]["tarjeta"] == 120
    assert cierre["metodos_pago"]["transferencia"] == 40

    # Resumen por cajero
    por_cajero = pos.obtener_resumen_por_cajero()
    assert "Cajero1" in por_cajero
    assert por_cajero["Cajero1"]["total"] == 200
    assert por_cajero["Cajero1"]["cantidad"] == 2
    assert "Cajero2" in por_cajero
    assert por_cajero["Cajero2"]["total"] == 40
    assert por_cajero["Cajero2"]["cantidad"] == 1

    # Rango de fechas
    ventas_rango = pos.obtener_ventas_rango(hoy, hoy)
    assert len(ventas_rango) == 3
