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
