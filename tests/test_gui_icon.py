from unittest.mock import Mock
from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication

import ui.gui_ui as gui_ui


def test_interfaz_aplica_logo_a_la_aplicacion_y_la_ventana(monkeypatch):
    app = QApplication.instance() or QApplication([])
    ventana = Mock()
    usuario = SimpleNamespace(nombre="Administradora", rol="admin")
    login = Mock()
    login.exec_.return_value = gui_ui.QDialog.Accepted
    login.usuario = usuario
    session = Mock()
    monkeypatch.setattr(gui_ui, "init_db", Mock())
    monkeypatch.setattr(gui_ui, "SessionLocal", Mock(return_value=session))
    monkeypatch.setattr(gui_ui, "VentanaPrincipal", Mock(return_value=ventana))
    monkeypatch.setattr(gui_ui, "DialogoLogin", Mock(return_value=login))
    monkeypatch.setattr(gui_ui.InterfazGUI, "_configurar_alertas_bandeja", Mock())

    gui_ui.InterfazGUI(app)

    assert not app.windowIcon().isNull()
    ventana.setWindowIcon.assert_called_once()
    assert not ventana.setWindowIcon.call_args.args[0].isNull()
