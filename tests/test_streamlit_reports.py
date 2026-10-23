from contextlib import nullcontext
from unittest.mock import Mock

import pandas as pd
import plotly.graph_objects as go

from reporting import streamlit_reports
from reporting.streamlit_reports import preparar_datos_dashboard


def test_preparar_datos_dashboard_generates_graph_data():
    productos = [
        {"nombre": "Paracetamol", "stock_total": 12},
        {"nombre": "Ibuprofeno", "stock_total": 5},
        {"nombre": "Vitamina C", "stock_total": 20},
    ]
    ventas = [
        {"metodo_pago": "efectivo", "total": 120.0},
        {"metodo_pago": "tarjeta", "total": 80.0},
        {"metodo_pago": "efectivo", "total": 50.0},
    ]

    dashboard = preparar_datos_dashboard(productos, ventas)

    assert dashboard["stock"]["Producto"].tolist() == ["Vitamina C", "Paracetamol", "Ibuprofeno"]
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
