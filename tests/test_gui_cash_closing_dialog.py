from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QApplication

import ui.gui_ui as gui_ui


class PosMetricsStub:
    def __init__(self):
        self.fechas = []

    def obtener_metricas_cierre_caja(self, fecha, usuario=None):
        self.fechas.append(fecha)
        return {
            "total_ingresos": 125000,
            "cantidad_ventas": 2,
            "ticket_promedio": 62500,
            "metodos_pago": {"efectivo": 75000, "transferencia": 50000},
        }

    def obtener_resumen_por_cajero(self, fecha=None, usuario=None):
        self.fechas.append(fecha)
        return {"Ana": {"total": 75000, "cantidad": 1}, "Luis": {"total": 50000, "cantidad": 1}}


def test_cierre_caja_muestra_metricas_por_fecha_y_exporta_pdf(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    pos = PosMetricsStub()
    dialogo = gui_ui.DialogoCierreCaja(pos)
    fecha = date(2026, 10, 20)
    dialogo.selector_fecha.setDate(QDate(fecha.year, fecha.month, fecha.day))

    assert dialogo.resumen_ingresos.text() == "Ingresos del día: $125.000"
    assert dialogo.tabla_cajeros.rowCount() == 2
    assert dialogo.tabla_metodos.rowCount() == 2
    assert pos.fechas[-1] == "2026-10-20"

    destino = tmp_path / "cierre.pdf"
    monkeypatch.setattr(gui_ui, "QFileDialog", SimpleNamespace(
        getSaveFileName=lambda *args: (str(destino), ""),
    ))
    monkeypatch.setattr(gui_ui, "QMessageBox", SimpleNamespace(
        information=Mock(),
        critical=Mock(),
    ))
    dialogo.exportar_pdf()

    assert destino.read_bytes().startswith(b"%PDF-")
    assert pos.fechas[-2:] == ["2026-10-20", "2026-10-20"]
    gui_ui.QMessageBox.information.assert_called_once()
    dialogo.close()
