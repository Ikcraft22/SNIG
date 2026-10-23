import pytest
import json
from uuid import uuid4
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


def test_api_productos_paginacion_opcional(client):
    response = client.get("/api/productos?page=1&per_page=1")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 1
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 1
    assert data["pagination"]["total"] >= len(data["items"])


@pytest.mark.parametrize(
    "query",
    ["page=abc", "page=0", "per_page=0", "per_page=101"],
)
def test_api_productos_rechaza_paginacion_invalida(client, query):
    response = client.get(f"/api/productos?{query}")

    assert response.status_code == 400


def test_api_sync_cursor_y_feed_incremental(client):
    cursor_response = client.get("/api/sync/cursor")
    assert cursor_response.status_code == 200
    cursor = cursor_response.get_json()["cursor"]

    create_response = client.post(
        "/api/productos",
        json={"gtin": f"sync-{uuid4().hex}", "nombre": "Producto sincronizable"},
    )
    assert create_response.status_code == 201

    changes_response = client.get(f"/api/sync/changes?cursor={cursor}&limit=10")
    assert changes_response.status_code == 200
    data = changes_response.get_json()
    assert data["changes"]
    assert data["changes"][0]["entity_type"] == "productos"
    assert data["changes"][0]["operation"] == "upsert"
    assert data["changes"][0]["payload"]["nombre"] == "Producto sincronizable"
    assert data["changes"][0]["cursor"] > cursor
    assert data["next_cursor"] >= data["changes"][0]["cursor"]


@pytest.mark.parametrize(
    "query",
    ["cursor=abc", "cursor=-1", "limit=0", "limit=501"],
)
def test_api_sync_rechaza_parametros_invalidos(client, query):
    response = client.get(f"/api/sync/changes?{query}")

    assert response.status_code == 400


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
