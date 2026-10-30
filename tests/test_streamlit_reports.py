from contextlib import nullcontext
from datetime import datetime
import io
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import plotly.graph_objects as go
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from reporting import streamlit_reports
from reporting.streamlit_reports import (
    aplicar_filtros,
    cargar_datos_completos,
    generar_excel_completo,
    nombre_archivo_exportacion,
    preparar_datos_dashboard,
    preparar_rendimiento_cajeros,
)
from database.connection import Base
from database.models import (
    EstadoMovimiento,
    EstadoVenta,
    MovimientoInventario,
    Presentacion,
    Producto,
    TipoPresentacion,
    Venta,
    VentaItem,
)


def test_preparar_datos_dashboard_generates_graph_data():
    productos = [
        {"nombre": "Galletas", "stock_total": 12},
        {"nombre": "Cuaderno", "stock_total": 5},
        {"nombre": "Agua", "stock_total": 20},
    ]
    ventas = [
        {"metodo_pago": "efectivo", "total": 120.0},
        {"metodo_pago": "tarjeta", "total": 80.0},
        {"metodo_pago": "efectivo", "total": 50.0},
    ]

    dashboard = preparar_datos_dashboard(productos, ventas)

    assert dashboard["stock"]["Producto"].tolist() == ["Agua", "Galletas", "Cuaderno"]
    assert dashboard["stock"]["Stock"].tolist() == [20, 12, 5]
    assert dashboard["ventas"]["MetodoPago"].tolist() == ["efectivo", "tarjeta"]
    assert dashboard["ventas"]["Total"].tolist() == [170.0, 80.0]


def test_grafica_dashboard_incluye_alternativa_tabular(monkeypatch):
    plotly_chart = Mock()
    dataframe = Mock()
    monkeypatch.setattr(streamlit_reports.st, "plotly_chart", plotly_chart)
    monkeypatch.setattr(streamlit_reports.st, "dataframe", dataframe)
    monkeypatch.setattr(
        streamlit_reports.st,
        "expander",
        lambda *args, **kwargs: nullcontext(),
    )

    datos = pd.DataFrame({"Producto": ["Cuaderno"], "Stock": [4]})
    figura = go.Figure()

    streamlit_reports.mostrar_grafica_accesible(figura, datos, "Stock")

    assert plotly_chart.call_args.kwargs["config"]["displayModeBar"] is True
    dataframe.assert_called_once()
    assert dataframe.call_args.args[0].equals(datos)


def test_preparar_rendimiento_cajeros_calcula_kpis_y_velocidad():
    ventas = pd.DataFrame([
        {"VentaID": 1, "Usuario": "Ana", "Total": 200, "FechaHora": "2026-10-20 10:00"},
        {"VentaID": 2, "Usuario": "Ana", "Total": 300, "FechaHora": "2026-10-20 10:30"},
        {"VentaID": 3, "Usuario": None, "Total": 90, "FechaHora": "2026-10-20 11:00"},
    ])

    resultado = preparar_rendimiento_cajeros(ventas).set_index("Cajero")

    assert resultado.loc["Ana", "TotalVendido"] == 500
    assert resultado.loc["Ana", "Transacciones"] == 2
    assert resultado.loc["Ana", "TicketPromedio"] == 250
    assert resultado.loc["Ana", "TicketsPorHora"] == 4
    assert resultado.loc["Sistema", "TicketsPorHora"] == 0


def test_rendimiento_cajeros_vacio_y_exportaciones_sin_filas():
    rendimiento = preparar_rendimiento_cajeros(pd.DataFrame())
    assert rendimiento.empty
    assert list(rendimiento.columns) == [
        "Cajero", "TotalVendido", "Transacciones", "TicketPromedio", "TicketsPorHora"
    ]

    vacios = {
        "ventas": pd.DataFrame(),
        "presentaciones": pd.DataFrame(),
        "items": pd.DataFrame(),
        "movimientos": pd.DataFrame(),
    }
    excel = generar_excel_completo(vacios)
    assert excel.startswith(b"PK")


def test_nombre_exportacion_incluye_filtros_y_timestamp_iso_seguro():
    filtros = {
        "periodo_opcion": "Rango Personalizado",
        "fecha_inicio": pd.Timestamp("2026-10-01"),
        "fecha_fin": pd.Timestamp("2026-10-20 23:59:59"),
        "metodo_pago": "Transferencia",
        "producto": "Producto/Especial",
    }

    nombre = nombre_archivo_exportacion(
        "Reporte Ventas",
        "csv",
        filtros,
        pd.Timestamp("2026-10-20T15:30:00-05:00").to_pydatetime(),
    )

    assert "2026-10-01_2026-10-20" in nombre
    assert "pago-Transferencia" in nombre
    assert "producto-Producto_Especial" in nombre
    assert "20261020T153000-0500" in nombre
    assert "/" not in nombre and ":" not in nombre


def test_cargar_datos_completos_serializa_entidades_y_estados():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        producto = Producto(gtin="750000000007", nombre="Leche")
        db.add(producto)
        db.flush()
        presentacion = Presentacion(
            producto_id=producto.id,
            tipo=TipoPresentacion.BOTELLA,
            cantidad=1,
            precio_unitario=12,
            precio_venta=20,
            stock_actual=0,
            stock_minimo=4,
        )
        venta = Venta(
            numero_ticket="TK-20261030-000007",
            estado=EstadoVenta.COMPLETADA,
            subtotal=20,
            total=20,
            metodo_pago="efectivo",
            usuario="Ana",
            fecha=datetime(2026, 10, 30, 12, 0),
        )
        db.add_all([presentacion, venta])
        db.flush()
        db.add(
            VentaItem(
                venta_id=venta.id,
                producto_id=producto.id,
                presentacion_id=presentacion.id,
                cantidad=1,
                precio_unitario=20,
                descuento=0,
                subtotal=20,
            )
        )
        db.add(
            MovimientoInventario(
                producto_id=producto.id,
                presentacion_id=presentacion.id,
                tipo_movimiento=EstadoMovimiento.ENTRADA,
                cantidad=4,
                razon="Compra",
                usuario="Ana",
                referencia_externa="F-1",
                fecha=datetime(2026, 10, 30, 11, 0),
            )
        )
        db.commit()

        datos = cargar_datos_completos(db)

    engine.dispose()
    assert datos["productos"].iloc[0]["TotalStock"] == 0
    assert datos["presentaciones"].iloc[0]["EstadoStock"] == "Sin Stock"
    assert datos["ventas"].iloc[0]["MetodoPago"] == "Efectivo"
    assert datos["ventas"].iloc[0]["CantidadItems"] == 1
    assert datos["items"].iloc[0]["Producto"] == "Leche"
    assert datos["movimientos"].iloc[0]["Referencia"] == "F-1"


def test_cargar_datos_completos_vacio_y_aplicar_filtros():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        vacios = cargar_datos_completos(db)
    engine.dispose()
    assert all(frame.empty for frame in vacios.values())

    fecha = pd.Timestamp("2026-10-30")
    datos = {
        "ventas": pd.DataFrame([
            {"VentaID": 1, "Fecha": fecha, "MetodoPago": "Efectivo", "Total": 20},
            {"VentaID": 2, "Fecha": fecha, "MetodoPago": "Transferencia", "Total": 30},
        ]),
        "items": pd.DataFrame([
            {"VentaID": 1, "Producto": "Leche"},
            {"VentaID": 2, "Producto": "Pan"},
        ]),
        "presentaciones": pd.DataFrame([
            {"Producto": "Leche", "StockActual": 2, "StockMinimo": 4, "EstadoStock": "Normal"},
            {"Producto": "Pan", "StockActual": 10, "StockMinimo": 4, "EstadoStock": "Normal"},
        ]),
        "productos": pd.DataFrame([
            {"Nombre": "Leche"}, {"Nombre": "Pan"},
        ]),
        "movimientos": pd.DataFrame([
            {"Producto": "Leche"}, {"Producto": "Pan"},
        ]),
    }

    filtrados = aplicar_filtros(datos, {
        "periodo_opcion": "Rango Personalizado",
        "fecha_inicio": fecha,
        "fecha_fin": fecha,
        "metodo_pago": "Efectivo",
        "producto": "Leche",
        "umbral_alerta": 3,
    })

    assert filtrados["ventas"]["VentaID"].tolist() == [1]
    assert filtrados["items"]["Producto"].tolist() == ["Leche"]
    assert filtrados["presentaciones"]["EstadoStock"].tolist() == ["Crítico / Bajo"]
    assert filtrados["productos"]["Nombre"].tolist() == ["Leche"]
    assert filtrados["movimientos"]["Producto"].tolist() == ["Leche"]


def test_render_kpis_cubre_metricas_con_y_sin_datos(monkeypatch):
    monkeypatch.setattr(streamlit_reports.st, "columns", lambda count: [nullcontext() for _ in range(count)])
    markdown = Mock()
    monkeypatch.setattr(streamlit_reports.st, "markdown", markdown)
    vacios = {
        "ventas": pd.DataFrame(),
        "presentaciones": pd.DataFrame(),
    }
    streamlit_reports.render_kpis_principales(vacios)
    assert "Stock óptimo" in markdown.call_args.args[0]

    markdown.reset_mock()
    datos = {
        "ventas": pd.DataFrame([{"Total": 30}]),
        "presentaciones": pd.DataFrame([{
            "StockActual": 0,
            "ValorTotalCosto": 10,
            "ValorTotalVenta": 30,
            "EstadoStock": "Sin Stock",
        }]),
    }
    streamlit_reports.render_kpis_principales(datos)
    assert "Requiere reposición" in markdown.call_args.args[0]


def test_configurar_pagina_y_filtros_sidebar(monkeypatch):
    set_page_config = Mock()
    markdown = Mock()
    monkeypatch.setattr(streamlit_reports.st, "set_page_config", set_page_config)
    monkeypatch.setattr(streamlit_reports.st, "markdown", markdown)
    streamlit_reports.configurar_pagina()
    set_page_config.assert_called_once_with(
        page_title="Dashboard de Inventario & Reportes",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    assert markdown.call_args.kwargs["unsafe_allow_html"] is True

    sidebar = Mock()
    sidebar.selectbox.side_effect = ["Rango Personalizado", "Efectivo", "Leche"]
    sidebar.date_input.return_value = (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-30"))
    sidebar.slider.return_value = 5
    sidebar.button.return_value = True
    monkeypatch.setattr(streamlit_reports.st, "sidebar", sidebar)
    cache_data = SimpleNamespace(clear=Mock())
    monkeypatch.setattr(streamlit_reports.st, "cache_data", cache_data)
    rerun = Mock()
    monkeypatch.setattr(streamlit_reports.st, "rerun", rerun)
    filtros = streamlit_reports.render_sidebar_filtros({
        "ventas": pd.DataFrame({"MetodoPago": ["Efectivo", "Transferencia"]}),
        "presentaciones": pd.DataFrame({"Producto": ["Leche", "Pan"]}),
    })

    assert filtros["periodo_opcion"] == "Rango Personalizado"
    assert filtros["metodo_pago"] == "Efectivo"
    assert filtros["producto"] == "Leche"
    assert filtros["umbral_alerta"] == 5
    assert filtros["fecha_inicio"] == pd.Timestamp("2026-10-01")
    cache_data.clear.assert_called_once_with()
    rerun.assert_called_once_with()


def test_sidebar_filtros_rangos_predefinidos_y_datos_vacios(monkeypatch):
    sidebar = Mock()
    sidebar.selectbox.side_effect = ["Hoy", "Todos", "Todos"]
    sidebar.slider.return_value = 10
    sidebar.button.return_value = False
    monkeypatch.setattr(streamlit_reports.st, "sidebar", sidebar)
    filtros = streamlit_reports.render_sidebar_filtros({
        "ventas": pd.DataFrame(),
        "presentaciones": pd.DataFrame(),
    })
    assert filtros["fecha_inicio"] == filtros["fecha_fin"].normalize()
    assert filtros["metodo_pago"] == "Todos"
    assert filtros["producto"] == "Todos"
    assert sidebar.date_input.called is False


def test_exportacion_excel_incluye_todas_las_hojas():
    datos = {
        "ventas": pd.DataFrame([{"Total": 20}]),
        "presentaciones": pd.DataFrame([{"StockActual": 2}]),
        "items": pd.DataFrame([{"Cantidad": 1}]),
        "movimientos": pd.DataFrame([{"TipoMovimiento": "Entrada"}]),
    }

    contenido = generar_excel_completo(datos)

    assert contenido.startswith(b"PK")
    with pd.ExcelFile(io.BytesIO(contenido)) as libro:
        assert libro.sheet_names == ["Ventas", "Inventario", "Detalle_Ventas", "Movimientos"]


def test_modulo_ventas_renderiza_graficas_y_detalles(monkeypatch):
    st = streamlit_reports.st
    for nombre in ("subheader", "markdown", "info", "dataframe", "caption", "plotly_chart"):
        monkeypatch.setattr(st, nombre, Mock())
    monkeypatch.setattr(
        st,
        "columns",
        lambda cantidad: [
            nullcontext() for _ in range(cantidad if isinstance(cantidad, int) else len(cantidad))
        ],
    )
    monkeypatch.setattr(st, "radio", Mock(return_value="Líneas"))
    monkeypatch.setattr(
        st,
        "selectbox",
        Mock(side_effect=["Día", "Gráfico de Dona"]),
    )
    monkeypatch.setattr(st, "expander", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(
        st,
        "column_config",
        SimpleNamespace(NumberColumn=Mock(side_effect=lambda *args, **kwargs: (args, kwargs))),
    )
    monkeypatch.setattr(
        streamlit_reports,
        "mostrar_grafica_accesible",
        Mock(),
    )
    ventas = pd.DataFrame([{
        "VentaID": 1,
        "Ticket": "TK-1",
        "Fecha": pd.Timestamp("2026-10-30"),
        "FechaHora": pd.Timestamp("2026-10-30 10:00"),
        "Hora": "10:00",
        "DiaSemana": "Friday",
        "Mes": "2026-10",
        "Total": 20,
        "MetodoPago": "Efectivo",
        "Usuario": "Ana",
        "CantidadItems": 1,
    }])
    items = pd.DataFrame([{
        "Producto": "Leche",
        "Subtotal": 20,
        "Cantidad": 1,
    }])

    streamlit_reports.render_modulo_ventas({"ventas": ventas, "items": items})

    assert st.plotly_chart.call_count == 0
    assert streamlit_reports.mostrar_grafica_accesible.call_count == 5
    assert st.dataframe.called


def test_modulos_de_reporte_manejan_ventas_vacias(monkeypatch):
    info = Mock()
    monkeypatch.setattr(streamlit_reports.st, "subheader", Mock())
    monkeypatch.setattr(streamlit_reports.st, "info", info)

    streamlit_reports.render_modulo_ventas({
        "ventas": pd.DataFrame(),
        "items": pd.DataFrame(),
    })

    info.assert_called_once()


def test_modulos_de_inventario_y_movimientos_renderizan_tablas(monkeypatch):
    st = streamlit_reports.st
    for nombre in ("subheader", "markdown", "info", "dataframe", "warning", "success", "write"):
        monkeypatch.setattr(st, nombre, Mock())
    monkeypatch.setattr(
        st,
        "columns",
        lambda cantidad: [nullcontext() for _ in range(len(cantidad) if isinstance(cantidad, list) else cantidad)],
    )
    monkeypatch.setattr(st, "radio", Mock(side_effect=["Barras Horizontales", "Líneas de Flujo"]))
    monkeypatch.setattr(st, "expander", lambda *_args, **_kwargs: nullcontext())
    graficas = Mock()
    monkeypatch.setattr(streamlit_reports, "mostrar_grafica_accesible", graficas)

    presentaciones = pd.DataFrame([{
        "Producto": "Leche",
        "TipoPresentacion": "Botella",
        "StockActual": 2,
        "EstadoStock": "Crítico / Bajo",
        "ValorTotalVenta": 40,
        "GTIN": "7500000000001",
        "StockMinimo": 4,
        "PrecioCosto": 10,
        "PrecioVenta": 20,
        "MargenUnitario": 10,
        "MargenPorcentaje": 50,
    }])
    streamlit_reports.render_modulo_inventario({
        "presentaciones": presentaciones,
        "productos": pd.DataFrame(),
    })
    assert st.warning.called

    movimientos = pd.DataFrame([{
        "Fecha": pd.Timestamp("2026-10-30"),
        "FechaHora": pd.Timestamp("2026-10-30 10:00"),
        "TipoMovimiento": "Entrada",
        "Cantidad": 3,
        "Producto": "Leche",
        "Razon": "Compra",
        "Usuario": "Ana",
        "Referencia": "F-1",
    }])
    streamlit_reports.render_modulo_movimientos({"movimientos": movimientos})
    assert graficas.call_count == 4
    assert st.dataframe.call_count == 3


def test_modulos_inventario_y_movimientos_informan_si_no_hay_filas(monkeypatch):
    info = Mock()
    monkeypatch.setattr(streamlit_reports.st, "subheader", Mock())
    monkeypatch.setattr(streamlit_reports.st, "info", info)

    streamlit_reports.render_modulo_inventario({
        "presentaciones": pd.DataFrame(),
        "productos": pd.DataFrame(),
    })
    streamlit_reports.render_modulo_movimientos({"movimientos": pd.DataFrame()})

    assert info.call_count == 2


@pytest.mark.parametrize(
    "tipo_grafica",
    [
        "📊 Barras Verticales (Bar)",
        "📊 Barras Horizontales (Horizontal Bar)",
        "📈 Líneas (Line)",
        "🌊 Áreas (Area)",
        "🍩 Dona / Circular (Pie/Donut)",
        "🌲 Treemap (Mapa de Árbol)",
        "🔴 Dispersión (Scatter)",
        "📦 Diagrama de Cajas (Box Plot)",
        "📉 Histograma (Histogram)",
    ],
)
def test_explorador_personalizado_genera_tipos_de_grafica(
    monkeypatch, tipo_grafica
):
    st = streamlit_reports.st
    monkeypatch.setattr(st, "subheader", Mock())
    monkeypatch.setattr(st, "caption", Mock())
    monkeypatch.setattr(st, "markdown", Mock())
    monkeypatch.setattr(st, "columns", lambda cantidad: [nullcontext() for _ in range(cantidad)])
    monkeypatch.setattr(st, "selectbox", Mock(side_effect=[
        "Productos e Inventario",
        tipo_grafica,
        "Producto",
        "StockActual",
        "TipoPresentacion",
    ]))
    monkeypatch.setattr(st, "expander", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(st, "dataframe", Mock())
    mostrar = Mock()
    monkeypatch.setattr(streamlit_reports, "mostrar_grafica_accesible", mostrar)

    datos = {
        "ventas": pd.DataFrame(),
        "presentaciones": pd.DataFrame({
            "Producto": ["Leche", "Pan", "Arroz"],
            "StockActual": [2, 8, 4],
            "TipoPresentacion": ["Botella", "Unidad", "Bolsa"],
        }),
        "items": pd.DataFrame(),
        "movimientos": pd.DataFrame(),
    }

    streamlit_reports.render_explorador_personalizado(datos)

    mostrar.assert_called_once()
    assert mostrar.call_args.args[1].equals(datos["presentaciones"])


def test_explorador_personalizado_maneja_fuente_vacia_y_error_grafico(monkeypatch):
    st = streamlit_reports.st
    monkeypatch.setattr(st, "subheader", Mock())
    monkeypatch.setattr(st, "caption", Mock())
    warning = Mock()
    error = Mock()
    monkeypatch.setattr(st, "warning", warning)
    monkeypatch.setattr(st, "error", error)
    monkeypatch.setattr(
        st,
        "selectbox",
        Mock(side_effect=[
            "Ventas (Transacciones)",
            "📊 Barras Verticales (Bar)",
            "Categoria",
            "Total",
            "Ninguno",
        ]),
    )
    monkeypatch.setattr(st, "columns", lambda cantidad: [nullcontext() for _ in range(cantidad)])
    monkeypatch.setattr(st, "expander", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(st, "dataframe", Mock())
    vacios = {
        "ventas": pd.DataFrame(),
        "presentaciones": pd.DataFrame(),
        "items": pd.DataFrame(),
        "movimientos": pd.DataFrame(),
    }
    streamlit_reports.render_explorador_personalizado(vacios)
    warning.assert_called_once()

    datos = dict(vacios)
    datos["ventas"] = pd.DataFrame({"Categoria": ["A"], "Total": [1]})
    st.selectbox.side_effect = [
        "Ventas (Transacciones)",
        "📊 Barras Verticales (Bar)",
        "Categoria",
        "Total",
        "Ninguno",
    ]
    monkeypatch.setattr(streamlit_reports.px, "bar", Mock(side_effect=RuntimeError("datos inválidos")))
    streamlit_reports.render_explorador_personalizado(datos)
    error.assert_called_once()


def test_centro_exportacion_prepara_descargas_pdf_excel_y_csv(monkeypatch):
    st = streamlit_reports.st
    for nombre in ("subheader", "caption", "markdown", "download_button"):
        monkeypatch.setattr(st, nombre, Mock())
    monkeypatch.setattr(st, "columns", lambda cantidad: [nullcontext() for _ in range(cantidad)])
    monkeypatch.setattr(streamlit_reports, "generar_reporte_pdf", Mock(return_value=b"%PDF-test"))
    datos = {
        "ventas": pd.DataFrame([{"Total": 20}]),
        "presentaciones": pd.DataFrame([{"StockActual": 2}]),
        "items": pd.DataFrame([{"Cantidad": 1}]),
        "movimientos": pd.DataFrame([{"TipoMovimiento": "Entrada"}]),
    }

    streamlit_reports.render_modulo_exportacion(
        datos,
        {"periodo_opcion": "Hoy", "metodo_pago": "Efectivo", "producto": "Leche"},
    )

    assert st.download_button.call_count == 4
    assert any("xlsx" in llamada.kwargs["file_name"] for llamada in st.download_button.call_args_list)
    assert any("csv" in llamada.kwargs["file_name"] for llamada in st.download_button.call_args_list)
    assert any("pdf" in llamada.kwargs["file_name"] for llamada in st.download_button.call_args_list)


def test_main_dashboard_conecta_carga_filtros_modulos_y_exportacion(monkeypatch):
    llamadas = {}

    def stub(nombre, resultado=None):
        def ejecutar(*args, **kwargs):
            llamadas[nombre] = (args, kwargs)
            return resultado
        return ejecutar

    for nombre in (
        "configurar_pagina",
        "render_kpis_principales",
        "render_modulo_ventas",
        "render_modulo_inventario",
        "render_modulo_movimientos",
        "render_explorador_personalizado",
        "render_modulo_exportacion",
    ):
        monkeypatch.setattr(streamlit_reports, nombre, stub(nombre))
    datos = {"ventas": pd.DataFrame(), "items": pd.DataFrame()}
    filtros = {"periodo_opcion": "Hoy"}
    monkeypatch.setattr(streamlit_reports, "cargar_datos_completos", stub("cargar", datos))
    monkeypatch.setattr(streamlit_reports, "render_sidebar_filtros", stub("sidebar", filtros))
    monkeypatch.setattr(streamlit_reports, "aplicar_filtros", stub("filtrar", datos))
    st = streamlit_reports.st
    monkeypatch.setattr(st, "title", Mock())
    monkeypatch.setattr(st, "caption", Mock())
    monkeypatch.setattr(st, "tabs", lambda _labels: [nullcontext() for _ in range(5)])

    streamlit_reports.main()

    assert llamadas["configurar_pagina"] == ((), {})
    assert llamadas["filtrar"] == ((datos, filtros), {})
    assert llamadas["render_modulo_exportacion"] == ((datos, filtros), {})
