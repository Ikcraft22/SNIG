import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from init_db import obtener_productos_demo_tienda_escolar


def test_obtener_productos_demo_tienda_escolar():
    productos = obtener_productos_demo_tienda_escolar()

    assert len(productos) >= 15
    assert any(prod["nombre"] == "Paleta de fresa" for prod in productos)
    assert any(prod["categoria"] == "dulces" for prod in productos)
    assert any(prod["caracteristicas"] for prod in productos)
    assert all("presentaciones" in prod for prod in productos)
