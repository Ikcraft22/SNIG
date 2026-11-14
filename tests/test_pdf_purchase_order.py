"""Pruebas TDD para generación de órdenes de compra en PDF a proveedores (Paso 6.1)."""

import io
import pytest
from reporting.pdf_export import generar_orden_compra_pdf


def test_generar_orden_compra_pdf_valido():
    proveedor = {
        "nombre": "Distribuidora Mayorista SAS",
        "contacto": "Carlos Gómez",
        "telefono": "+57 300 123 4567",
        "email": "ventas@mayorista.com",
    }
    items = [
        {
            "producto": "Arroz Diana 1kg",
            "presentacion": "Bolsa x 1kg",
            "cantidad": 20,
            "costo_unitario": 3500.0,
            "subtotal": 70000.0,
        },
        {
            "producto": "Aceite Premier 900ml",
            "presentacion": "Botella",
            "cantidad": 12,
            "costo_unitario": 8000.0,
            "subtotal": 96000.0,
        },
    ]

    pdf_bytes = generar_orden_compra_pdf(
        numero_orden="OC-2026-0001",
        proveedor=proveedor,
        items=items,
        notas="Entrega antes del mediodía en bodega principal.",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_generar_orden_compra_pdf_items_vacios_genera_documento_valido():
    proveedor = {"nombre": "Proveedor General"}
    pdf_bytes = generar_orden_compra_pdf(
        numero_orden="OC-2026-0002",
        proveedor=proveedor,
        items=[],
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
