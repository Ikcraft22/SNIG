from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication, QLineEdit, QTableWidget

from ui.gui_ui import VentanaPrincipal


def test_inventory_shows_supplier_for_search_and_full_catalog():
    app = QApplication.instance() or QApplication([])
    product = SimpleNamespace(
        id=1,
        gtin="100000000004",
        nombre="Producto de prueba",
        proveedores=[
            SimpleNamespace(nombre="Proveedor Z"),
            SimpleNamespace(nombre="Proveedor A"),
        ],
        presentaciones=[
            SimpleNamespace(id=2, stock_actual=8, precio_venta=1200),
        ],
    )
    ventana = SimpleNamespace(
        entrada_gtin=QLineEdit("prueba"),
        tabla_inventario=QTableWidget(0, 5),
        _nombres_proveedores=VentanaPrincipal._nombres_proveedores,
        inventario=SimpleNamespace(
            buscar_productos=lambda termino: [product],
            obtener_productos=lambda: [product],
        ),
    )

    VentanaPrincipal.buscar_producto(ventana)
    assert ventana.tabla_inventario.columnCount() == 5
    assert ventana.tabla_inventario.item(0, 4).text() == "Proveedor A, Proveedor Z"

    VentanaPrincipal.ver_todos_productos(ventana)
    assert ventana.tabla_inventario.item(0, 4).text() == "Proveedor A, Proveedor Z"
    app.processEvents()


def test_inventory_displays_products_without_a_supplier():
    product = SimpleNamespace(proveedores=[])

    assert VentanaPrincipal._nombres_proveedores(product) == "Sin proveedor"
