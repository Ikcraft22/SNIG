from types import SimpleNamespace
from unittest.mock import Mock

import ui.terminal_ui as terminal_ui
from ui.terminal_ui import InterfazTerminal


def crear_interfaz():
    interfaz = InterfazTerminal.__new__(InterfazTerminal)
    interfaz.limpiar_pantalla = Mock()
    interfaz.inventario = Mock()
    interfaz.pos = Mock()
    return interfaz


def test_seleccionar_opcion_acepta_letra_indice_y_cancelacion(monkeypatch, capsys):
    interfaz = crear_interfaz()
    respuestas = iter(["inválida", "2"])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))

    assert interfaz.seleccionar_opcion([("uno", "Primero"), "Segundo"]) == 1
    assert "a. Primero" in capsys.readouterr().out

    monkeypatch.setattr("builtins.input", lambda *_: "q")
    assert interfaz.seleccionar_opcion(["Salir"]) is None


def test_registrar_producto_manual_y_agregar_presentacion(monkeypatch, capsys):
    interfaz = crear_interfaz()
    interfaz.buscador = Mock()
    interfaz.buscador.buscar.return_value = {"encontrado": False, "datos": None}
    interfaz.inventario.registrar_producto.return_value = SimpleNamespace(
        id=7, gtin="750123", nombre="Producto"
    )
    respuestas = iter(["750123", "Producto", "Descripción", "s", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.seleccionar_opcion = Mock(return_value=0)
    interfaz.agregar_presentacion_a_producto = Mock()

    interfaz.registrar_producto()

    interfaz.inventario.registrar_producto.assert_called_once_with(
        gtin="750123", nombre="Producto", descripcion="Descripción"
    )
    interfaz.agregar_presentacion_a_producto.assert_called_once_with(7)
    assert "Producto registrado exitosamente" in capsys.readouterr().out

    del interfaz.agregar_presentacion_a_producto
    interfaz.seleccionar_opcion = Mock(return_value=1)
    interfaz.inventario.agregar_presentacion.return_value = SimpleNamespace(
        tipo=SimpleNamespace(value="bolsa")
    )
    respuestas = iter(["12", "100", "150", "4"])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.agregar_presentacion_a_producto(7)

    interfaz.inventario.agregar_presentacion.assert_called_once_with(
        producto_id=7,
        tipo_presentacion="bolsa",
        cantidad=12,
        precio_unitario=100,
        precio_venta=150,
        stock_inicial=4,
    )


def test_buscar_producto_muestra_resultado_y_puede_registrarlo(monkeypatch, capsys):
    interfaz = crear_interfaz()
    producto = SimpleNamespace(
        nombre="Arroz",
        gtin="750123",
        descripcion="Grano",
        presentaciones=[
            SimpleNamespace(
                tipo=SimpleNamespace(value="bolsa"),
                precio_venta=25,
                stock_actual=6,
            )
        ],
    )
    interfaz.inventario.obtener_producto_por_gtin.side_effect = [producto, None]
    respuestas = iter(["750123", "", "750999", "s", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.registrar_producto = Mock()

    interfaz.buscar_producto()
    interfaz.buscar_producto()

    interfaz.registrar_producto.assert_called_once_with()
    salida = capsys.readouterr().out
    assert "Barcode: 750123" in salida
    assert "Producto no encontrado: 750999" in salida


def test_registrar_entrada_y_salida_validas_y_rechaza_entradas_invalidas(
    monkeypatch, capsys
):
    interfaz = crear_interfaz()
    presentacion = SimpleNamespace(
        id=4,
        tipo=SimpleNamespace(value="unidad"),
        stock_actual=10,
    )
    producto = SimpleNamespace(id=3, nombre="Lápiz", presentaciones=[presentacion])
    interfaz.inventario.obtener_producto_por_gtin.return_value = producto
    interfaz.seleccionar_opcion = Mock(return_value=0)
    respuestas = iter(["750123", "5", "Compra", "F-1", "", "750123", "2", "Merma", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))

    interfaz.registrar_entrada()
    interfaz.registrar_salida()

    assert interfaz.inventario.registrar_movimiento.call_count == 2
    assert interfaz.inventario.registrar_movimiento.call_args_list[0].kwargs == {
        "producto_id": 3,
        "presentacion_id": 4,
        "tipo": "entrada",
        "cantidad": 5,
        "razon": "Compra",
        "referencia": "F-1",
    }
    assert interfaz.inventario.registrar_movimiento.call_args_list[1].kwargs == {
        "producto_id": 3,
        "presentacion_id": 4,
        "tipo": "salida",
        "cantidad": 2,
        "razon": "Merma",
    }

    respuestas = iter(["750123", "no-numérico", "", "750123", "11", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.registrar_entrada()
    interfaz.registrar_salida()
    assert "Entrada inválida" in capsys.readouterr().out
    assert interfaz.inventario.registrar_movimiento.call_count == 2


def test_busqueda_inexistente_cancelaciones_y_consultas_de_inventario(
    monkeypatch, capsys
):
    interfaz = crear_interfaz()
    interfaz.inventario.obtener_producto_por_gtin.return_value = None
    monkeypatch.setattr("builtins.input", lambda *_: "")
    interfaz.registrar_entrada()
    interfaz.registrar_salida()
    interfaz.ver_historial()
    assert "Producto no encontrado" in capsys.readouterr().out

    interfaz.inventario.obtener_productos_stock_bajo.return_value = [
        {
            "nombre": "Leche",
            "presentacion": "botella",
            "stock_actual": 1,
            "stock_minimo": 4,
            "urgencia": "CRÍTICO",
        }
    ]
    interfaz.ver_stock_bajo()
    interfaz.inventario.obtener_productos_stock_bajo.return_value = []
    interfaz.ver_stock_bajo()

    producto = SimpleNamespace(id=2, nombre="Leche")
    interfaz.inventario.obtener_producto_por_gtin.return_value = producto
    interfaz.inventario.historial_movimientos.return_value = [
        {"fecha": "hoy", "tipo": "entrada", "cantidad": 4, "razon": "Compra", "usuario": "Ana"}
    ]
    respuestas = iter(["750123", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.ver_historial()
    assert "CRÍTICO" in capsys.readouterr().out


def test_carrito_pos_cubre_agregar_ver_y_eliminar(monkeypatch, capsys):
    interfaz = crear_interfaz()
    producto = SimpleNamespace(
        id=2,
        nombre="Jugo",
        presentaciones=[
            SimpleNamespace(
                id=8,
                tipo=SimpleNamespace(value="botella"),
                precio_venta=30,
                stock_actual=5,
            )
        ],
    )
    interfaz.inventario.obtener_producto_por_gtin.return_value = producto
    interfaz.seleccionar_opcion = Mock(return_value=0)
    interfaz.pos.carrito.obtener_items.return_value = [
        {
            "producto_id": 2,
            "presentacion_id": 8,
            "cantidad": 2,
            "precio_unitario": 30,
            "subtotal": 60,
        }
    ]
    interfaz.pos.carrito.obtener_resumen.return_value = {
        "cantidad_items": 1,
        "subtotal": 60,
        "total": 60,
    }
    respuestas = iter(["750123", "2", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))

    interfaz.agregar_a_carrito()
    interfaz.ver_carrito()
    interfaz.eliminar_del_carrito()

    interfaz.pos.carrito.agregar_item.assert_called_once_with(
        producto_id=2,
        presentacion_id=8,
        cantidad=2,
        precio_unitario=30,
    )
    interfaz.pos.carrito.eliminar_item.assert_called_once_with(8)
    assert "Jugo" in capsys.readouterr().out


def test_pago_en_efectivo_reintenta_y_cierra_carrito(monkeypatch, capsys):
    interfaz = crear_interfaz()
    interfaz.pos.carrito.obtener_resumen.return_value = {
        "cantidad_items": 1,
        "subtotal": 80,
        "total": 80,
    }
    interfaz.pos.generar_numero_ticket.return_value = "TK-1"
    interfaz.pos.crear_venta.return_value = SimpleNamespace(
        numero_ticket="TK-1",
        total=80,
        metodo_pago="efectivo",
        fecha="hoy",
    )
    monkeypatch.setattr(terminal_ui, "obtener_metodos_pago_disponibles", lambda: ("efectivo",))
    interfaz.seleccionar_opcion = Mock(return_value=0)
    monkeypatch.setattr(
        terminal_ui,
        "calcular_vuelto",
        lambda total, recibido: recibido - total
        if recibido >= total
        else (_ for _ in ()).throw(ValueError()),
    )
    respuestas = iter(["abc", "50", "100", "Ana", "Nota", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))

    interfaz.procesar_pago()

    interfaz.pos.crear_venta.assert_called_once_with(
        numero_ticket="TK-1",
        metodo_pago="efectivo",
        usuario="Ana",
        notas="Nota",
    )
    salida = capsys.readouterr().out
    assert "Pago insuficiente" in salida
    assert "VENTA COMPLETADA" in salida
    assert "Vuelto: $20" in salida


def test_menu_pos_reportes_y_ejecucion_de_salida(monkeypatch):
    interfaz = crear_interfaz()
    monkeypatch.setattr("builtins.input", lambda *_: "")
    interfaz.pos.carrito.obtener_resumen.return_value = {
        "cantidad_items": 0,
        "total": 0,
    }
    respuestas = iter([0, 1, 2, 3, 4, 5])
    monkeypatch.setattr(interfaz, "seleccionar_opcion", lambda *_args, **_kwargs: next(respuestas))
    interfaz.agregar_a_carrito = Mock()
    interfaz.eliminar_del_carrito = Mock()
    interfaz.ver_carrito = Mock()
    interfaz.procesar_pago = Mock()
    interfaz.menu_pos()

    interfaz.agregar_a_carrito.assert_called_once_with()
    interfaz.eliminar_del_carrito.assert_called_once_with()
    interfaz.ver_carrito.assert_called_once_with()
    interfaz.procesar_pago.assert_called_once_with()
    interfaz.pos.carrito.vaciar_carrito.assert_called_once_with()

    interfaz.inventario.reporte_general.return_value = {
        "fecha": "hoy",
        "total_productos": 3,
        "total_stock": 8,
        "valor_inventario": 90,
        "productos_sin_stock": 1,
        "productos_alerta": 2,
    }
    monkeypatch.setattr("builtins.input", lambda *_: "")
    interfaz.menu_reportes()

    interfaz.db = SimpleNamespace(close=Mock())
    interfaz.mostrar_menu_principal = Mock()
    interfaz.seleccionar_opcion = Mock(return_value=4)
    interfaz.ejecutar()
    interfaz.db.close.assert_called_once_with()


def test_inicializacion_limpieza_menu_inventario_y_menu_principal(monkeypatch, capsys):
    session = Mock()
    monkeypatch.setattr(terminal_ui, "init_db", Mock())
    monkeypatch.setattr(terminal_ui, "SessionLocal", Mock(return_value=session))
    monkeypatch.setattr(terminal_ui, "GestorInventario", Mock())
    monkeypatch.setattr(terminal_ui, "GestorPOS", Mock())
    monkeypatch.setattr(terminal_ui, "EscanerProducto", Mock())
    monkeypatch.setattr(terminal_ui, "GTINBuscador", Mock())
    interfaz = InterfazTerminal()
    terminal_ui.init_db.assert_called_once_with()
    assert interfaz.db is session

    comando = Mock()
    monkeypatch.setattr(terminal_ui.os, "system", comando)
    interfaz.limpiar_pantalla()
    comando.assert_called_once()

    interfaz.mostrar_menu_principal()
    assert "sistema de inventario" in capsys.readouterr().out.lower()

    interfaz.limpiar_pantalla = Mock()
    for metodo in (
        "registrar_producto",
        "buscar_producto",
        "registrar_entrada",
        "registrar_salida",
        "ver_stock_bajo",
        "ver_historial",
    ):
        setattr(interfaz, metodo, Mock())
    respuestas = iter(["1", "2", "3", "4", "5", "6", "7"])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.menu_inventario()
    for metodo in (
        "registrar_producto",
        "buscar_producto",
        "registrar_entrada",
        "registrar_salida",
        "ver_stock_bajo",
        "ver_historial",
    ):
        getattr(interfaz, metodo).assert_called_once_with()


def test_cancelacion_y_limites_de_entrada_en_acciones_de_inventario(monkeypatch, capsys):
    interfaz = crear_interfaz()
    interfaz.buscador = Mock()
    interfaz.buscador.buscar.return_value = {
        "encontrado": True,
        "datos": {"nombre": "Té", "fuente": "test"},
    }
    interfaz.inventario.registrar_producto.return_value = None
    respuestas = iter(["7501234567890", "Detalle", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.registrar_producto()
    assert "Error al registrar producto" in capsys.readouterr().out

    producto = SimpleNamespace(
        id=1,
        nombre="Té",
        presentaciones=[
            SimpleNamespace(
                id=2,
                tipo=SimpleNamespace(value="bolsa"),
                stock_actual=2,
            )
        ],
    )
    interfaz.inventario.obtener_producto_por_gtin.return_value = producto
    interfaz.seleccionar_opcion = Mock(side_effect=[None, 0])
    respuestas = iter(["750123", "", "750123", "3", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.registrar_entrada()
    interfaz.registrar_salida()
    assert interfaz.inventario.registrar_movimiento.call_count == 0
    assert "Stock insuficiente" in capsys.readouterr().out

    interfaz.inventario.obtener_productos_stock_bajo.return_value = []
    monkeypatch.setattr("builtins.input", lambda *_: "")
    interfaz.ver_stock_bajo()
    interfaz.inventario.historial_movimientos.return_value = []
    interfaz.seleccionar_opcion = Mock(return_value=0)
    interfaz.ver_historial()
    assert "No hay movimientos registrados" in capsys.readouterr().out


def test_acciones_carrito_cubren_cancelacion_y_sin_stock(monkeypatch, capsys):
    interfaz = crear_interfaz()
    interfaz.inventario.obtener_producto_por_gtin.return_value = None
    interfaz.pos.carrito.obtener_items.return_value = []
    interfaz.pos.carrito.obtener_resumen.return_value = {
        "cantidad_items": 0,
        "total": 0,
    }
    monkeypatch.setattr("builtins.input", lambda *_: "")
    interfaz.agregar_a_carrito()
    interfaz.ver_carrito()
    interfaz.pos.carrito.obtener_items.return_value = []
    interfaz.eliminar_del_carrito()
    interfaz.procesar_pago()

    producto = SimpleNamespace(
        id=3,
        nombre="Cuaderno",
        presentaciones=[
            SimpleNamespace(
                id=4,
                tipo=SimpleNamespace(value="unidad"),
                precio_venta=10,
                stock_actual=1,
            )
        ],
    )
    interfaz.inventario.obtener_producto_por_gtin.return_value = producto
    interfaz.seleccionar_opcion = Mock(return_value=0)
    respuestas = iter(["750123", "2", "750123", ""]);
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.agregar_a_carrito()
    interfaz.seleccionar_opcion = Mock(return_value=None)
    interfaz.pos.carrito.obtener_items.return_value = [
        {"producto_id": 3, "presentacion_id": 4, "cantidad": 1}
    ]
    interfaz.eliminar_del_carrito()
    assert "Stock insuficiente" in capsys.readouterr().out
    interfaz.pos.carrito.agregar_item.assert_not_called()
    interfaz.pos.carrito.eliminar_item.assert_not_called()


def test_pago_por_transferencia_y_cancelacion_de_menu(monkeypatch, capsys):
    interfaz = crear_interfaz()
    interfaz.pos.carrito.obtener_resumen.return_value = {
        "cantidad_items": 1,
        "subtotal": 35,
        "total": 35,
    }
    interfaz.pos.generar_numero_ticket.return_value = "TK-2"
    interfaz.pos.crear_venta.return_value = None
    monkeypatch.setattr(
        terminal_ui,
        "obtener_metodos_pago_disponibles",
        lambda: ("efectivo", "transferencia"),
    )
    interfaz.seleccionar_opcion = Mock(return_value=1)
    respuestas = iter(["Ana", "", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    interfaz.procesar_pago()
    interfaz.pos.crear_venta.assert_called_once_with(
        numero_ticket="TK-2",
        metodo_pago="transferencia",
        usuario="Ana",
        notas="",
    )
    assert "Error al procesar la venta" in capsys.readouterr().out

    interfaz.pos.carrito.obtener_resumen.return_value = {
        "cantidad_items": 0,
        "total": 0,
    }
    interfaz.seleccionar_opcion = Mock(side_effect=[None, 5])
    interfaz.limpiar_pantalla = Mock()
    interfaz.menu_pos()
    assert interfaz.seleccionar_opcion.call_count == 2


def test_punto_entrada_terminal_cierra_sesion_tras_interrupcion(monkeypatch, capsys):
    interfaz = crear_interfaz()
    interfaz.db = SimpleNamespace(close=Mock())
    interfaz.mostrar_menu_principal = Mock(side_effect=KeyboardInterrupt)
    interfaz.ejecutar()
    interfaz.db.close.assert_called_once_with()
    assert "Aplicación interrumpida" in capsys.readouterr().out
