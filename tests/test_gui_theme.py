from types import SimpleNamespace
from unittest.mock import Mock

from PyQt5.QtWidgets import QApplication, QLabel, QTableWidget

from ui.gui_ui import VentanaPrincipal


def test_cambiar_tema_conserva_el_carrito_pos():
    app = QApplication.instance() or QApplication([])
    carrito = SimpleNamespace(
        obtener_items=lambda: [
            {
                "producto_nombre": "Producto demo",
                "producto_id": 1,
                "presentacion_id": 2,
                "cantidad": 2,
                "precio_unitario": 4.5,
                "subtotal": 9.0,
            }
        ],
        obtener_resumen=lambda: {"subtotal": 9.0, "total": 9.0},
    )
    ventana = SimpleNamespace(
        modo_oscuro=False,
        pestanas=SimpleNamespace(currentIndex=lambda: 1),
        pos=SimpleNamespace(carrito=carrito),
        _guardar_modo_oscuro=Mock(),
        configurar_logger_grafico=Mock(),
    )

    def reconstruir_interfaz():
        ventana.tabla_carrito = QTableWidget()
        ventana.tabla_carrito.setColumnCount(4)
        ventana.label_subtotal = QLabel()
        ventana.label_total = QLabel()

    ventana.crear_ui = reconstruir_interfaz
    ventana.actualizar_tabla_carrito = lambda: VentanaPrincipal.actualizar_tabla_carrito(ventana)
    ventana.actualizar_resumen_carrito = lambda: VentanaPrincipal.actualizar_resumen_carrito(ventana)

    VentanaPrincipal.cambiar_tema(ventana, True)

    assert ventana.tabla_carrito.rowCount() == 1
    assert ventana.tabla_carrito.item(0, 0).text() == "Producto demo"
    assert "9" in ventana.label_subtotal.text()
    assert "9" in ventana.label_total.text()
