"""Exportación de reportes del dashboard a PDF."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLOR_PRIMARIO = colors.HexColor("#1d4ed8")
COLOR_OSCURO = colors.HexColor("#0f172a")
COLOR_ENCABEZADO = colors.HexColor("#1e293b")
COLOR_BORDE = colors.HexColor("#cbd5e1")
COLOR_FILA_ALT = colors.HexColor("#f1f5f9")

REPORT_SECTIONS = (
    ("ventas", "Ventas", ("Ticket", "FechaHora", "MetodoPago", "Usuario", "Total")),
    (
        "presentaciones",
        "Inventario",
        ("GTIN", "Producto", "TipoPresentacion", "StockActual", "StockMinimo", "PrecioCosto", "PrecioVenta"),
    ),
    (
        "items",
        "Detalle de ventas",
        ("Ticket", "Producto", "Presentacion", "Cantidad", "PrecioUnitario", "Subtotal"),
    ),
    (
        "movimientos",
        "Movimientos de inventario",
        ("FechaHora", "Producto", "TipoMovimiento", "Cantidad", "Razon", "Usuario"),
    ),
)

COLUMNAS_NUMERICAS = {
    "Total",
    "StockActual",
    "StockMinimo",
    "PrecioCosto",
    "PrecioVenta",
    "Cantidad",
    "PrecioUnitario",
    "Subtotal",
    "ValorTotalCosto",
}


def _decorar_pagina(canvas, document):
    """Dibuja franja superior y pie de página con numeración."""
    ancho, alto = landscape(letter)
    canvas.saveState()

    canvas.setFillColor(COLOR_PRIMARIO)
    canvas.rect(0, alto - 6 * mm, ancho, 6 * mm, stroke=0, fill=1)

    canvas.setStrokeColor(COLOR_BORDE)
    canvas.setLineWidth(0.5)
    canvas.line(12 * mm, 11 * mm, ancho - 12 * mm, 11 * mm)

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(12 * mm, 7 * mm, "Sistema de Inventario · Reporte confidencial")
    canvas.drawRightString(ancho - 12 * mm, 7 * mm, f"Página {document.page}")

    canvas.restoreState()


def _tarjeta_kpi(etiqueta: str, valor: str, estilo_etiqueta, estilo_valor, ancho) -> Table:
    tarjeta = Table(
        [[Paragraph(escape(etiqueta), estilo_etiqueta)], [Paragraph(escape(valor), estilo_valor)]],
        colWidths=[ancho],
    )
    tarjeta.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDE),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEABOVE", (0, 0), (-1, 0), 2.5, COLOR_PRIMARIO),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tarjeta


def generar_reporte_pdf(datos: Dict[str, pd.DataFrame]) -> bytes:
    """Genera un PDF multipágina con los datos filtrados del dashboard."""
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Reporte de inventario y ventas",
        author="Sistema de Inventario",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=COLOR_OSCURO,
        fontSize=20,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"),
        fontSize=9,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        textColor=COLOR_PRIMARIO,
        fontSize=13,
        spaceBefore=6,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        wordWrap="CJK",
    )
    cell_right_style = ParagraphStyle("ReportCellRight", parent=cell_style, alignment=TA_RIGHT)
    header_style = ParagraphStyle(
        "ReportHeader",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    header_right_style = ParagraphStyle("ReportHeaderRight", parent=header_style, alignment=TA_RIGHT)
    kpi_label_style = ParagraphStyle(
        "KpiLabel", parent=styles["Normal"], fontSize=7.5, textColor=colors.HexColor("#64748b")
    )
    kpi_value_style = ParagraphStyle(
        "KpiValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=14, textColor=COLOR_OSCURO
    )

    story = [
        Paragraph("Reporte de inventario y ventas", title_style),
        Paragraph(f"Generado: {datetime.now():%Y-%m-%d %H:%M}", subtitle_style),
        Spacer(1, 6 * mm),
    ]

    ventas = datos.get("ventas", pd.DataFrame())
    presentaciones = datos.get("presentaciones", pd.DataFrame())

    indicadores = [
        ("Ventas incluidas", str(len(ventas))),
        ("Ingresos totales", f"{ventas['Total'].sum():,.2f}" if "Total" in ventas else "0.00"),
        ("Presentaciones incluidas", str(len(presentaciones))),
        (
            "Unidades en stock",
            str(presentaciones["StockActual"].sum()) if "StockActual" in presentaciones else "0",
        ),
        (
            "Valor del inventario a costo",
            f"{presentaciones['ValorTotalCosto'].sum():,.2f}"
            if "ValorTotalCosto" in presentaciones
            else "No disponible",
        ),
    ]

    gap = 3 * mm
    ancho_kpi = (document.width - gap * (len(indicadores) - 1)) / len(indicadores)
    fila_kpi = []
    anchos = []
    for indice, (etiqueta, valor) in enumerate(indicadores):
        fila_kpi.append(_tarjeta_kpi(etiqueta, valor, kpi_label_style, kpi_value_style, ancho_kpi))
        anchos.append(ancho_kpi)
        if indice < len(indicadores) - 1:
            fila_kpi.append("")
            anchos.append(gap)
    kpi_table = Table([fila_kpi], colWidths=anchos)
    kpi_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 0)]))

    story.extend([Paragraph("Resumen", section_style), kpi_table, Spacer(1, 7 * mm)])

    available_width = document.width
    for key, title, columns in REPORT_SECTIONS:
        dataframe = datos.get(key, pd.DataFrame())
        story.append(Paragraph(escape(title), section_style))
        if dataframe.empty:
            story.extend([Paragraph("Sin registros para los filtros seleccionados.", styles["Normal"]), Spacer(1, 4 * mm)])
            continue

        visible_columns = [column for column in columns if column in dataframe.columns]
        if not visible_columns:
            story.extend([Paragraph("No hay columnas exportables para esta sección.", styles["Normal"]), Spacer(1, 4 * mm)])
            continue

        rows = [
            [
                Paragraph(
                    escape(column),
                    header_right_style if column in COLUMNAS_NUMERICAS else header_style,
                )
                for column in visible_columns
            ]
        ]
        for values in dataframe[visible_columns].itertuples(index=False, name=None):
            rows.append(
                [
                    Paragraph(
                        escape("" if pd.isna(value) else str(value)),
                        cell_right_style if column in COLUMNAS_NUMERICAS else cell_style,
                    )
                    for column, value in zip(visible_columns, values)
                ]
            )

        table = Table(
            rows,
            colWidths=[available_width / len(visible_columns)] * len(visible_columns),
            repeatRows=1,
            splitByRow=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_ENCABEZADO),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, COLOR_BORDE),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FILA_ALT]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([table, Spacer(1, 6 * mm)])

    document.build(story, onFirstPage=_decorar_pagina, onLaterPages=_decorar_pagina)
    return buffer.getvalue()
