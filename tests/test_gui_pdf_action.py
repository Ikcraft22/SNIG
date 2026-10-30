from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import ui.gui_ui as gui_ui


def test_exportar_reporte_pdf_guarda_abre_y_avisa(monkeypatch, tmp_path):
    destino = tmp_path / "reporte.pdf"
    datos = {"ventas": []}
    owner = SimpleNamespace(
        texto_reporte=SimpleNamespace(setText=Mock()),
        _obtener_datos_reporte_pdf=Mock(return_value=datos),
    )
    monkeypatch.setattr(gui_ui, "QFileDialog", SimpleNamespace(
        getSaveFileName=lambda *args: (str(destino), ""),
    ))
    monkeypatch.setattr(gui_ui, "QDesktopServices", SimpleNamespace(openUrl=Mock(return_value=True)))
    monkeypatch.setattr(gui_ui, "QUrl", SimpleNamespace(fromLocalFile=lambda path: path))
    monkeypatch.setattr(
        "reporting.pdf_export.generar_reporte_pdf",
        lambda received: b"%PDF-test" if received is datos else b"",
    )

    gui_ui.VentanaPrincipal.exportar_reporte_pdf_gui(owner)

    assert destino.read_bytes() == b"%PDF-test"
    gui_ui.QDesktopServices.openUrl.assert_called_once()
    assert str(destino) in owner.texto_reporte.setText.call_args.args[0]


def test_exportar_reporte_pdf_muestra_error_si_falla(monkeypatch, tmp_path):
    owner = SimpleNamespace(_obtener_datos_reporte_pdf=Mock(return_value={}))
    destino = tmp_path / "reporte.pdf"
    monkeypatch.setattr(gui_ui, "QFileDialog", SimpleNamespace(
        getSaveFileName=lambda *args: (str(destino), ""),
    ))
    monkeypatch.setattr(
        "reporting.pdf_export.generar_reporte_pdf",
        Mock(side_effect=RuntimeError("fallo de generación")),
    )
    error = Mock()
    monkeypatch.setattr(gui_ui, "QMessageBox", SimpleNamespace(critical=error))

    gui_ui.VentanaPrincipal.exportar_reporte_pdf_gui(owner)

    error.assert_called_once()
    assert "fallo de generación" in error.call_args.args[2]
    assert not destino.exists()


def test_exportar_reporte_pdf_anade_extension_y_cancela(monkeypatch, tmp_path):
    owner = SimpleNamespace(
        _obtener_datos_reporte_pdf=Mock(return_value={}),
        texto_reporte=SimpleNamespace(setText=Mock()),
    )
    destino = tmp_path / "reporte"
    monkeypatch.setattr(gui_ui, "QFileDialog", SimpleNamespace(
        getSaveFileName=lambda *args: (str(destino), ""),
    ))
    monkeypatch.setattr(gui_ui, "QDesktopServices", SimpleNamespace(openUrl=Mock(return_value=True)))
    monkeypatch.setattr(gui_ui, "QUrl", SimpleNamespace(fromLocalFile=lambda path: path))
    monkeypatch.setattr("reporting.pdf_export.generar_reporte_pdf", lambda datos: b"%PDF-test")

    gui_ui.VentanaPrincipal.exportar_reporte_pdf_gui(owner)
    assert Path(f"{destino}.pdf").exists()

    monkeypatch.setattr(gui_ui.QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    gui_ui.VentanaPrincipal.exportar_reporte_pdf_gui(owner)
