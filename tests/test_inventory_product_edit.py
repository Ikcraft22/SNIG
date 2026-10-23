from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.inventory_manager import GestorInventario
from core.pos_manager import CarritoCompra
from database.connection import Base
from database.models import Presentacion, Producto, TipoPresentacion
from ui import gui_ui
from ui.gui_ui import DialogoEditarProducto, DialogoNuevoProducto, VentanaPrincipal


@pytest.fixture
def inventario_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def crear_producto_con_presentacion(session, gtin, nombre, precio=4.5):
    producto = Producto(gtin=gtin, nombre=nombre)
    session.add(producto)
    session.flush()
    presentacion = Presentacion(
        producto_id=producto.id,
        tipo=TipoPresentacion.UNIDAD,
        cantidad=1,
        precio_unitario=precio,
        precio_venta=precio,
        stock_actual=8,
    )
    session.add(presentacion)
    session.commit()
    return producto, presentacion


def test_actualizar_producto_edita_datos_y_precio_sin_cambiar_stock(inventario_db):
    producto, presentacion = crear_producto_con_presentacion(
        inventario_db, "1234567890123", "Nombre anterior"
    )
    gestor = GestorInventario(inventario_db)

    actualizado = gestor.actualizar_producto(
        producto_id=producto.id,
        gtin=" 1234567890124 ",
        nombre=" Nombre actualizado ",
        laboratorio="Laboratorio",
        descripcion="Descripción",
        presentacion_id=presentacion.id,
        precio_venta=6,
    )

    assert actualizado
    inventario_db.refresh(producto)
    inventario_db.refresh(presentacion)
    assert producto.gtin == "1234567890124"
    assert producto.nombre == "Nombre actualizado"
    assert producto.laboratorio == "Laboratorio"
    assert producto.descripcion == "Descripción"
    assert presentacion.precio_venta == 6
    assert presentacion.precio_unitario == 4.5
    assert presentacion.stock_actual == 8


def test_actualizar_producto_rechaza_gtin_duplicado(inventario_db):
    producto, _ = crear_producto_con_presentacion(
        inventario_db, "1234567890123", "Producto original"
    )
    crear_producto_con_presentacion(inventario_db, "1234567890124", "Otro producto")
    gestor = GestorInventario(inventario_db)

    actualizado = gestor.actualizar_producto(
        producto_id=producto.id,
        gtin="1234567890124",
        nombre="Nombre nuevo",
    )

    assert not actualizado
    inventario_db.refresh(producto)
    assert producto.gtin == "1234567890123"
    assert producto.nombre == "Producto original"


def test_precios_y_totales_pos_se_redondean_a_unidades_enteras(inventario_db):
    producto, _ = crear_producto_con_presentacion(
        inventario_db, "1234567890123", "Producto con precio decimal"
    )
    gestor = GestorInventario(inventario_db)
    presentacion = gestor.agregar_presentacion(
        producto_id=producto.id,
        tipo_presentacion="unidad",
        cantidad=1,
        precio_unitario=4.6,
        precio_venta=5.4,
    )
    carrito = CarritoCompra()

    assert presentacion is not None
    assert presentacion.precio_unitario == 5
    assert presentacion.precio_venta == 5
    assert carrito.agregar_item(
        producto_id=producto.id,
        presentacion_id=presentacion.id,
        cantidad=3,
        precio_unitario=5.4,
    )
    assert carrito.obtener_items()[0]["precio_unitario"] == 5
    assert carrito.obtener_resumen()["total"] == 15


def test_dialogos_de_producto_solo_aceptan_precios_enteros():
    app = QApplication.instance() or QApplication([])
    producto = SimpleNamespace(
        gtin="1234567890123",
        nombre="Producto",
        descripcion="",
        laboratorio="",
    )
    presentacion = SimpleNamespace(
        precio_venta=5,
        tipo=SimpleNamespace(value="unidad"),
    )

    dialogo_nuevo = DialogoNuevoProducto()
    dialogo_editar = DialogoEditarProducto(producto, presentacion)

    assert dialogo_nuevo.campo_precio.decimals() == 0
    assert dialogo_editar.campo_precio_venta.decimals() == 0
    assert dialogo_nuevo.campo_gtin.placeholderText()
    assert dialogo_nuevo.campo_stock_inicial.suffix() == " unidades"
    dialogo_nuevo.campo_gtin.setText("1234567890123")
    dialogo_nuevo.campo_nombre.setText("Producto nuevo")
    dialogo_nuevo.campo_descripcion.setPlainText("Descripción de prueba")
    dialogo_nuevo.campo_precio.setValue(2500)
    assert dialogo_nuevo.obtener_datos()["descripcion"] == "Descripción de prueba"
    assert any(
        button.text() == "Guardar producto"
        for button in dialogo_nuevo.findChildren(gui_ui.QPushButton)
    )


def test_menu_inventario_incluye_edicion_y_usa_presentacion_seleccionada(monkeypatch):
    app = QApplication.instance() or QApplication([])

    class TablaPrueba(QTableWidget):
        def rowAt(self, posicion_y):
            return 0

    tabla = TablaPrueba(1, 1)
    tabla.setItem(0, 0, QTableWidgetItem("1234567890123"))
    presentacion_no_seleccionada = SimpleNamespace(id=10)
    presentacion_seleccionada = SimpleNamespace(id=11)
    producto = SimpleNamespace(
        gtin="1234567890123",
        presentaciones=[presentacion_no_seleccionada, presentacion_seleccionada],
    )
    tabla.item(0, 0).setData(Qt.UserRole, presentacion_seleccionada.id)
    menu_actions = []

    class MenuFalso:
        def __init__(self, parent):
            pass

        def addAction(self, action):
            menu_actions.append(action)

        def exec_(self, posicion):
            pass

    monkeypatch.setattr(gui_ui, "QMenu", MenuFalso)
    ventana = SimpleNamespace(
        tabla_inventario=tabla,
        inventario=SimpleNamespace(obtener_producto_por_gtin=lambda gtin: producto),
        obtener_producto_y_presentacion_desde_fila=lambda fila: (
            VentanaPrincipal.obtener_producto_y_presentacion_desde_fila(ventana, fila)
        ),
        editar_producto_contextual=Mock(),
        registrar_movimiento_contextual=Mock(),
        mostrar_detalle_producto=Mock(),
    )

    producto_recuperado, presentacion_recuperada = (
        VentanaPrincipal.obtener_producto_y_presentacion_desde_fila(ventana, 0)
    )
    assert producto_recuperado is producto
    assert presentacion_recuperada is presentacion_seleccionada

    VentanaPrincipal.mostrar_menu_contextual_inventario(ventana, QPoint(1, 1))
    acciones = {action.text(): action for action in menu_actions}
    assert "➕ Registrar entrada" in acciones
    assert "➖ Registrar salida" in acciones
    assert "✏️ Editar producto" in acciones

    acciones["✏️ Editar producto"].trigger()
    ventana.editar_producto_contextual.assert_called_once_with(
        producto, presentacion_seleccionada
    )
