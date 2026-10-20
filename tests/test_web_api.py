import pytest
import json
from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_productos_get(client):
    response = client.get("/api/productos")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_api_inventario_resumen_financiero(client):
    response = client.get("/api/inventario/resumen-financiero")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "valor_costo_total" in data
    assert "valor_venta_potencial" in data
    assert "ganancia_proyectada" in data


def test_api_inventario_reabastecimiento(client):
    response = client.get("/api/inventario/reabastecimiento")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_api_inventario_exportar_csv(client):
    response = client.get("/api/inventario/exportar")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("Content-Type", "")


def test_api_pos_cierre_caja(client):
    response = client.get("/api/pos/cierre-caja")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "total_ingresos" in data
    assert "metodos_pago" in data
