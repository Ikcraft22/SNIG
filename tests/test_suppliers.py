from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget

from database.connection import Base
from database.models import Producto, Proveedor
from ui.gui_ui import DialogoAsignarProductos, DialogoProveedor


def test_supplier_can_be_linked_to_multiple_products_and_unlinked_on_delete():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        proveedor = Proveedor(nombre="Proveedor Demo", email="ventas@example.com")
        productos = [
            Producto(gtin="100000000001", nombre="Producto A"),
            Producto(gtin="100000000002", nombre="Producto B"),
        ]
        proveedor.productos.extend(productos)
        session.add(proveedor)
        session.commit()

        recuperado = session.query(Proveedor).one()
        assert {producto.nombre for producto in recuperado.productos} == {
            "Producto A",
            "Producto B",
        }

        session.delete(recuperado)
        session.commit()
        assert session.query(Proveedor).count() == 0
        assert session.query(Producto).count() == 2
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_supplier_dialog_returns_normalized_contact_fields():
    app = QApplication.instance() or QApplication([])
    dialogo = DialogoProveedor()
    dialogo.campo_nombre.setText("  Distribuidora Central  ")
    dialogo.campo_contacto.setText("  Ana Pérez ")
    dialogo.campo_telefono.setText("  3001234567 ")
    dialogo.campo_email.setText(" ventas@example.com ")

    datos = dialogo.obtener_datos()

    assert datos["nombre"] == "Distribuidora Central"
    assert datos["contacto"] == "Ana Pérez"
    assert datos["telefono"] == "3001234567"
    assert datos["email"] == "ventas@example.com"
    dialogo.close()
    app.processEvents()


def test_supplier_product_assignment_dialog_tracks_checked_products():
    app = QApplication.instance() or QApplication([])
    proveedor = Proveedor(nombre="Proveedor Demo")
    producto = Producto(gtin="100000000003", nombre="Producto asignable")
    producto.id = 3
    otro_producto = Producto(gtin="100000000004", nombre="Otro producto")
    otro_producto.id = 4
    dialogo = DialogoAsignarProductos(proveedor, [producto, otro_producto])

    elemento = dialogo.lista_productos.item(0)
    elemento.setCheckState(Qt.Checked)

    assert dialogo.productos_seleccionados() == [producto.id]
    assert dialogo.resumen_seleccion.text() == "1 producto(s) seleccionado(s)"
    dialogo.busqueda.setText("GTIN 100000000004")
    assert dialogo.lista_productos.item(0).isHidden()
    assert not dialogo.lista_productos.item(1).isHidden()
    dialogo.close()
    app.processEvents()


def test_supplier_dialogs_follow_the_active_theme():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.modo_oscuro = True
    proveedor = Proveedor(nombre="Proveedor Demo")

    dialogo_proveedor = DialogoProveedor(proveedor=proveedor, parent=parent)
    dialogo_productos = DialogoAsignarProductos(proveedor, [], parent)

    assert "#101827" in dialogo_proveedor.styleSheet()
    assert "#101827" in dialogo_productos.styleSheet()

    parent.modo_oscuro = False
    dialogo_claro = DialogoProveedor(parent=parent)
    assert "#f3f6fb" in dialogo_claro.styleSheet()

    dialogo_proveedor.close()
    dialogo_productos.close()
    dialogo_claro.close()
    parent.close()
    app.processEvents()
