from types import SimpleNamespace
from unittest.mock import Mock

from PyQt5.QtWidgets import QSystemTrayIcon

from ui.gui_ui import InterfazGUI


def test_notificacion_bandeja_se_deduplica_hasta_cambiar_alertas():
    alerta = {
        "gtin": "750000000001",
        "presentacion": "unidad",
        "stock_actual": 0,
        "urgencia": "CRÍTICO",
    }
    alertas = [alerta]
    tray = SimpleNamespace(showMessage=Mock())
    agente = SimpleNamespace(
        ventana_principal=SimpleNamespace(
            inventario=SimpleNamespace(obtener_productos_stock_bajo=lambda: alertas),
        ),
        tray_icon=tray,
        _firma_alertas_stock=None,
    )

    InterfazGUI._comprobar_stock_bajo(agente)
    InterfazGUI._comprobar_stock_bajo(agente)

    tray.showMessage.assert_called_once_with(
        "SNIG: alerta de inventario",
        "1 presentaciones requieren atención (1 críticos · 0 bajos). Pulsa para abrir Inventario.",
        QSystemTrayIcon.Warning,
        10_000,
    )

    alertas[0] = {**alerta, "stock_actual": 1, "urgencia": "BAJO"}
    InterfazGUI._comprobar_stock_bajo(agente)
    assert tray.showMessage.call_count == 2


def test_click_de_aviso_abre_inventario_filtrado():
    ventana = SimpleNamespace(
        showNormal=Mock(),
        raise_=Mock(),
        activateWindow=Mock(),
        pestanas=SimpleNamespace(setCurrentIndex=Mock()),
        filtrar_productos_stock_bajo_gui=Mock(),
    )
    agente = SimpleNamespace(ventana_principal=ventana)

    InterfazGUI._mostrar_stock_bajo(agente)

    ventana.pestanas.setCurrentIndex.assert_called_once_with(1)
    ventana.filtrar_productos_stock_bajo_gui.assert_called_once_with()
