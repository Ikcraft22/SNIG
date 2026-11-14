"""Pruebas TDD para atajos de teclado F-Keys y autocompletado predictivo en GUI (Paso 5.2 y 5.3)."""

import pytest
from unittest.mock import Mock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent

from ui.gui_ui import VentanaPrincipal


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_atajos_f_keys_y_escape_en_ventana_principal(qapp):
    with patch("ui.gui_ui.SessionLocal"):
        ventana = VentanaPrincipal()

        # Asegurar que los componentes necesarios existen
        assert hasattr(ventana, "keyPressEvent")
        assert hasattr(ventana, "entrada_gtin_pos")
        assert hasattr(ventana, "procesar_pago_gui")
        assert hasattr(ventana, "vaciar_carrito_gui")
        assert hasattr(ventana, "pausar_carrito_gui")
        assert hasattr(ventana, "mostrar_carritos_en_espera_gui")

        # F1: debe enfocar la búsqueda/código en POS y cambiar a pestaña POS
        evento_f1 = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_F1, Qt.NoModifier)
        ventana.keyPressEvent(evento_f1)
        assert ventana.pestanas.currentWidget() == ventana.pestana_pos

        # F3: debe invocar vaciar carrito
        with patch.object(ventana, "vaciar_carrito_gui") as mock_vaciar:
            evento_f3 = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_F3, Qt.NoModifier)
            ventana.keyPressEvent(evento_f3)
            mock_vaciar.assert_called_once()

        # F4: debe invocar pausar carrito
        with patch.object(ventana, "pausar_carrito_gui") as mock_pausar:
            evento_f4 = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_F4, Qt.NoModifier)
            ventana.keyPressEvent(evento_f4)
            mock_pausar.assert_called_once()

        # F5: debe mostrar carritos en espera
        with patch.object(ventana, "mostrar_carritos_en_espera_gui") as mock_lista_espera:
            evento_f5 = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_F5, Qt.NoModifier)
            ventana.keyPressEvent(evento_f5)
            mock_lista_espera.assert_called_once()

        # F2: debe invocar procesar pago
        with patch.object(ventana, "procesar_pago_gui") as mock_pago:
            evento_f2 = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_F2, Qt.NoModifier)
            ventana.keyPressEvent(evento_f2)
            mock_pago.assert_called_once()


def test_buscador_predictivo_autocompleter_en_pos(qapp):
    with patch("ui.gui_ui.SessionLocal"):
        ventana = VentanaPrincipal()
        assert hasattr(ventana, "completer_pos")
        assert ventana.completer_pos is not None
        assert ventana.entrada_gtin_pos.completer() == ventana.completer_pos
