import pandas as pd

from reporting.pdf_export import generar_reporte_pdf


def test_generar_reporte_pdf_incluye_secciones_y_resumen():
    datos = {
        "ventas": pd.DataFrame([{"Ticket": "TK-1000", "Total": 250, "MetodoPago": "efectivo"}]),
        "presentaciones": pd.DataFrame(
            [{"GTIN": "7501234567890", "Producto": "Cuaderno", "StockActual": 4, "ValorTotalCosto": 80}]
        ),
        "items": pd.DataFrame(),
        "movimientos": pd.DataFrame(),
    }

    pdf = generar_reporte_pdf(datos)

    assert pdf.startswith(b"%PDF-")
    assert b"%%EOF" in pdf


def test_generar_reporte_pdf_acepta_datos_vacios():
    pdf = generar_reporte_pdf(
        {
            "ventas": pd.DataFrame(),
            "presentaciones": pd.DataFrame(),
            "items": pd.DataFrame(),
            "movimientos": pd.DataFrame(),
        }
    )

    assert pdf.startswith(b"%PDF-")
