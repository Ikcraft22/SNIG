from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.pos_manager import calcular_vuelto
from ui import gui_ui
from ui.gui_ui import VentanaPrincipal


def test_calcular_vuelto_resta_total_del_efectivo_recibido():
    assert calcular_vuelto(275, 300) == 25
    assert calcular_vuelto(275, 275) == 0


def test_calcular_vuelto_rechaza_efectivo_insuficiente():
    with pytest.raises(ValueError, match="no cubre el total"):
        calcular_vuelto(275, 274)


def test_pago_efectivo_muestra_vuelto_al_completar_venta(monkeypatch):
    total = 275
    venta = SimpleNamespace(numero_ticket="T-100", total=total)
    pos = SimpleNamespace(
        carrito=SimpleNamespace(
            obtener_resumen=lambda: {"cantidad_items": 1, "total": total}
        ),
        generar_numero_ticket=Mock(return_value="T-100"),
        crear_venta=Mock(return_value=venta),
    )
    ventana = SimpleNamespace(
        pos=pos,
        actualizar_tabla_carrito=Mock(),
        actualizar_resumen_carrito=Mock(),
        ver_todos_productos=Mock(),
    )
    monkeypatch.setattr(
        gui_ui.QInputDialog,
        "getText",
        lambda *args: ("1", True),
    )
    entrada_efectivo = {}

    def pedir_efectivo(*args):
        entrada_efectivo["argumentos"] = args
        return 300, True

    monkeypatch.setattr(gui_ui.QInputDialog, "getInt", pedir_efectivo)
    mensajes = []
    monkeypatch.setattr(
        gui_ui.QMessageBox,
        "information",
        lambda *args: mensajes.append(args[2]),
    )

    VentanaPrincipal.procesar_pago_gui(ventana)

    pos.crear_venta.assert_called_once_with(
        numero_ticket="T-100",
        metodo_pago="efectivo",
        usuario="Sistema",
        notas=None,
    )
    assert entrada_efectivo["argumentos"][3:5] == (total, total)
    assert "Efectivo recibido: $300" in mensajes[0]
    assert "Vuelto: $25" in mensajes[0]
