import pytest
import json
from io import BytesIO
from datetime import date, datetime
from unittest.mock import Mock
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Presentacion, Producto, TipoPresentacion, Venta
from web import app as web_app
from web.app import app


@pytest.fixture
def client(tmp_path):
    test_db_path = tmp_path / "test_inventario.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(test_engine)
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    app.config["TESTING"] = True
    app.config["DB_SESSION_FACTORY"] = test_session_factory
    with app.test_client() as client:
        yield client
    app.config.pop("DB_SESSION_FACTORY", None)
    test_engine.dispose()


def test_api_productos_get(client):
    response = client.get("/api/productos")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_api_productos_no_expone_campos_de_fabricante_ni_farmaceuticos(client):
    crear = client.post(
        "/api/productos",
        json={
            "gtin": f"api-{uuid4().hex}",
            "nombre": "Producto general",
            "descripcion": "Descripción",
            "laboratorio": "dato legado",
            "cum": "dato legado",
            "principio_activo": "dato legado",
            "registro_sanitario": "dato legado",
        },
    )
    assert crear.status_code == 201

    productos = client.get("/api/productos").get_json()
    producto = next(item for item in productos if item["id"] == crear.get_json()["id"])
    assert set(producto) == {"id", "gtin", "nombre", "presentaciones"}


def test_interfaz_web_muestra_barcode_y_no_gtin(client):
    for path in ("/inventario", "/pos"):
        response = client.get(path)

        assert response.status_code == 200
        assert b"Barcode" in response.data
        assert b"GTIN" not in response.data


def test_tarjeta_esta_oculta_en_web_y_se_muestra_al_habilitarla(client, monkeypatch):
    from config import settings

    assert b'data-method="tarjeta"' not in client.get("/pos").data

    monkeypatch.setattr(settings, "PAGO_TARJETA_HABILITADO", True)

    assert b'data-method="tarjeta"' in client.get("/pos").data


def test_api_checkout_rechaza_tarjeta_mientras_esta_deshabilitada(client):
    response = client.post(
        "/api/ventas/checkout",
        json={"metodo_pago": "tarjeta", "items": []},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "El método de pago seleccionado no está habilitado"


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


def test_api_sync_cursor_y_feed_incremental(client, monkeypatch):
    monkeypatch.setattr(web_app, "SYNC_API_TOKEN", "test-sync-token")
    headers = {"Authorization": "Bearer test-sync-token"}
    cursor_response = client.get("/api/sync/cursor", headers=headers)
    assert cursor_response.status_code == 200
    cursor = cursor_response.get_json()["cursor"]

    create_response = client.post(
        "/api/productos",
        json={"gtin": f"sync-{uuid4().hex}", "nombre": "Producto sincronizable"},
    )
    assert create_response.status_code == 201

    changes_response = client.get(
        f"/api/sync/changes?cursor={cursor}&limit=10",
        headers=headers,
    )
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
def test_api_sync_rechaza_parametros_invalidos(client, monkeypatch, query):
    monkeypatch.setattr(web_app, "SYNC_API_TOKEN", "test-sync-token")
    response = client.get(
        f"/api/sync/changes?{query}",
        headers={"Authorization": "Bearer test-sync-token"},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("path", "token", "expected_status"),
    [
        ("/api/sync/cursor", None, 401),
        ("/api/sync/cursor", "Bearer incorrecto", 401),
        ("/api/sync/cursor", "Basic test-sync-token", 401),
        ("/api/sync/changes", None, 401),
        ("/api/sync/changes", "Bearer incorrecto", 401),
    ],
)
def test_api_sync_requiere_bearer_token(client, monkeypatch, path, token, expected_status):
    monkeypatch.setattr(web_app, "SYNC_API_TOKEN", "test-sync-token")
    headers = {"Authorization": token} if token else {}
    response = client.get(path, headers=headers)

    assert response.status_code == expected_status


def test_api_sync_se_desactiva_si_no_hay_token_configurado(client, monkeypatch):
    monkeypatch.setattr(web_app, "SYNC_API_TOKEN", "")
    response = client.get("/api/sync/cursor")

    assert response.status_code == 503


@pytest.mark.parametrize("ruta", ["/api/sync/cursor", "/api/sync/changes"])
def test_api_sync_informa_error_de_base_de_datos(client, monkeypatch, ruta):
    db = Mock()
    db.query.side_effect = RuntimeError("base no disponible")
    db.close = Mock()
    monkeypatch.setattr(web_app, "SYNC_API_TOKEN", "test-sync-token")
    monkeypatch.setattr(web_app, "obtener_db", Mock(return_value=db))

    response = client.get(ruta, headers={"Authorization": "Bearer test-sync-token"})

    assert response.status_code == 500
    assert response.get_json()["error"] == "base no disponible"
    db.close.assert_called_once_with()


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


def test_api_reportes_exporta_formatos_y_valida_filtros(client):
    for formato, firma in (("pdf", b"%PDF-"), ("xlsx", b"PK")):
        response = client.get(f"/api/reportes/exportar?formato={formato}")
        assert response.status_code == 200
        assert response.data.startswith(firma)
        assert formato in response.headers["Content-Disposition"]

    assert client.get("/api/reportes/exportar?formato=xml").status_code == 400
    assert client.get("/api/reportes/exportar?fecha_inicio=2026-10-01").status_code == 400
    assert client.get(
        "/api/reportes/exportar?fecha_inicio=2026-10-30&fecha_fin=2026-10-01"
    ).status_code == 400


def test_api_reportes_csv_respeta_filtros_y_nombre_seguro(client):
    factory = app.config["DB_SESSION_FACTORY"]
    db = factory()
    db.add_all([
        Venta(
            numero_ticket="TK-FILTRO-1",
            total=100,
            subtotal=100,
            metodo_pago="efectivo",
            usuario="Ana",
            fecha=datetime(2026, 10, 20, 10, 0),
        ),
        Venta(
            numero_ticket="TK-FILTRO-2",
            total=200,
            subtotal=200,
            metodo_pago="transferencia",
            usuario="Luis",
            fecha=datetime(2026, 10, 21, 10, 0),
        ),
    ])
    db.commit()
    db.close()

    response = client.get(
        "/api/reportes/exportar?formato=csv&dataset=ventas"
        "&fecha_inicio=2026-10-20&fecha_fin=2026-10-20&metodo_pago=Efectivo"
    )

    contenido = response.data.decode("utf-8-sig")
    assert response.status_code == 200
    assert "TK-FILTRO-1" in contenido
    assert "TK-FILTRO-2" not in contenido
    assert "2026-10-20_2026-10-20" in response.headers["Content-Disposition"]
    assert ":" not in response.headers["Content-Disposition"]


def crear_presentacion_prueba():
    factory = app.config["DB_SESSION_FACTORY"]
    db = factory()
    producto = Producto(gtin=f"web-{uuid4().hex}", nombre="Producto web")
    db.add(producto)
    db.flush()
    presentacion = Presentacion(
        producto_id=producto.id,
        tipo=TipoPresentacion.UNIDAD,
        cantidad=1,
        precio_unitario=10,
        precio_venta=20,
        stock_actual=3,
        stock_minimo=4,
    )
    db.add(presentacion)
    db.commit()
    ids = producto.id, presentacion.id, producto.gtin
    db.close()
    return ids


def test_api_creacion_y_consulta_producto_valida_errores(client):
    assert client.post("/api/productos", json=[]).status_code == 400
    assert client.post(
        "/api/productos", json={"gtin": "", "nombre": ""}
    ).status_code == 400

    gtin = f"api-{uuid4().hex}"
    creado = client.post(
        "/api/productos",
        json={"gtin": gtin, "nombre": "Producto de prueba", "descripcion": "Detalle"},
    )
    assert creado.status_code == 201
    assert client.get(f"/api/productos/{gtin}").get_json()["nombre"] == "Producto de prueba"
    assert client.get("/api/productos/no-existe").status_code == 404
    assert client.get("/inventario").status_code == 200
    assert client.get("/pos").status_code == 200


def test_api_busqueda_externa_valida_gtin_y_consulta_resultado(client, monkeypatch):
    assert client.get("/api/buscar-gtin/invalido").status_code == 400
    monkeypatch.setattr(
        web_app.GTINBuscador,
        "buscar",
        lambda _self, gtin: {"encontrado": True, "datos": {"gtin": gtin}},
    )

    response = client.get("/api/buscar-gtin/7501234567890")

    assert response.status_code == 200
    assert response.get_json()["datos"]["gtin"] == "7501234567890"

    monkeypatch.setattr(
        web_app.GTINBuscador,
        "buscar",
        Mock(side_effect=RuntimeError("servicio externo no disponible")),
    )
    assert client.get("/api/buscar-gtin/7501234567890").status_code == 500


def test_api_movimientos_stock_bajo_y_reportes(client):
    producto_id, presentacion_id, _ = crear_presentacion_prueba()
    assert client.get("/api/inventario/stock-bajo").get_json()[0]["producto_id"] == producto_id
    assert client.get("/api/inventario/reabastecimiento").get_json()[0]["producto_id"] == producto_id
    assert client.get("/api/inventario/reporte").status_code == 200

    assert client.post("/api/inventario/movimiento", json=[]).status_code == 400
    movimiento = client.post(
        "/api/inventario/movimiento",
        json={
            "producto_id": producto_id,
            "presentacion_id": presentacion_id,
            "tipo": "entrada",
            "cantidad": 2,
            "razon": "Compra",
            "usuario": "Ana",
            "referencia": "F-10",
        },
    )
    assert movimiento.status_code == 201
    assert client.post(
        "/api/inventario/movimiento",
        json={
            "producto_id": producto_id,
            "presentacion_id": presentacion_id,
            "tipo": "salida",
            "cantidad": 100,
        },
    ).status_code == 400


def test_api_checkout_confirma_venta_y_rechaza_items_incompletos(client):
    producto_id, presentacion_id, _ = crear_presentacion_prueba()
    incompleta = client.post(
        "/api/ventas/checkout",
        json={"items": [{"producto_id": producto_id}]},
    )
    assert incompleta.status_code == 400
    assert client.post(
        "/api/ventas/checkout",
        json={"items": ["no es un objeto"]},
    ).status_code == 400

    response = client.post(
        "/api/ventas/checkout",
        json={
            "metodo_pago": "efectivo",
            "usuario": "Ana",
            "items": [{
                "producto_id": producto_id,
                "presentacion_id": presentacion_id,
                "cantidad": 1,
                "precio_unitario": 20,
            }],
        },
    )
    assert response.status_code == 201
    assert response.get_json()["success"] is True
    assert response.get_json()["items"] == 1


@pytest.mark.parametrize(
    ("metodo", "ruta", "gestor", "datos", "estado"),
    [
        ("get", "/api/productos/7501234567890", "inventario", None, 500),
        ("post", "/api/productos", "inventario", {"gtin": "750", "nombre": "Test"}, 500),
        ("get", "/api/inventario/stock-bajo", "inventario", None, 500),
        ("post", "/api/inventario/movimiento", "inventario", {"tipo": "entrada"}, 500),
        ("get", "/api/inventario/reporte", "inventario", None, 500),
        ("get", "/api/inventario/resumen-financiero", "inventario", None, 500),
        ("get", "/api/inventario/reabastecimiento", "inventario", None, 500),
        ("get", "/api/inventario/backup", "inventario", None, 500),
        ("get", "/api/ventas/reporte/2026-10-30", "pos", None, 500),
        ("get", "/api/pos/cierre-caja", "pos", None, 500),
        ("post", "/api/ventas/checkout", "pos", {"items": [{"producto_id": 1}]}, 400),
    ],
)
def test_api_expone_error_si_falla_el_gestor(
    client, monkeypatch, metodo, ruta, gestor, datos, estado
):
    clase = "GestorInventario" if gestor == "inventario" else "GestorPOS"
    monkeypatch.setattr(
        web_app,
        clase,
        Mock(side_effect=RuntimeError("fallo controlado")),
    )
    response = getattr(client, metodo)(
        ruta,
        json=datos if metodo == "post" else None,
    )

    assert response.status_code == estado
    assert "error" in response.get_json()


def test_api_exportar_reportes_responde_error_de_generacion(client, monkeypatch):
    from reporting import streamlit_reports

    monkeypatch.setattr(
        streamlit_reports,
        "cargar_datos_completos",
        Mock(side_effect=RuntimeError("fallo controlado")),
    )
    response = client.get("/api/reportes/exportar?formato=csv")

    assert response.status_code == 500
    assert response.get_json()["error"] == "No se pudo generar la exportación"


def test_api_ventas_listado_y_reporte_diario(client):
    producto_id, presentacion_id, _ = crear_presentacion_prueba()
    factory = app.config["DB_SESSION_FACTORY"]
    db = factory()
    db.add(
        Venta(
            numero_ticket=f"TK-{date.today():%Y%m%d}-000001",
            total=40,
            subtotal=40,
            metodo_pago="efectivo",
            usuario="Ana",
            fecha=datetime.now(),
        )
    )
    db.commit()
    db.close()

    assert client.get("/api/ventas").get_json()[0]["usuario"] == "Ana"
    reporte = client.get(f"/api/ventas/reporte/{date.today().isoformat()}")
    assert reporte.status_code == 200
    assert client.get("/api/inventario/resumen-financiero").get_json()["total_unidades"] == 3


def test_api_importacion_catalogo_valida_archivo_y_procesa_csv(client):
    assert client.post("/api/inventario/importar").status_code == 400
    assert client.post(
        "/api/inventario/importar",
        data={"archivo": (BytesIO(b"datos"), "datos.txt")},
        content_type="multipart/form-data",
    ).status_code == 400

    contenido = (
        "gtin,nombre,descripcion,tipo_presentacion,cantidad,precio_costo,"
        "precio_venta,stock_actual,stock_minimo,codigo_interno\n"
        f"csv-{uuid4().hex},Producto CSV,Detalle,unidad,1,10,20,5,2,C-1\n"
    )
    response = client.post(
        "/api/inventario/importar",
        data={"archivo": (BytesIO(contenido.encode("utf-8")), "catalogo.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200, response.get_json()


def test_api_exportacion_backup_y_pagina_no_encontrada(client, monkeypatch):
    assert client.get("/").status_code == 200
    assert client.get("/reportes").status_code == 200
    assert client.get("/ruta-inexistente").status_code == 404

    exportacion = client.get("/api/inventario/exportar")
    assert exportacion.status_code == 200
    assert b"gtin,nombre" in exportacion.data

    monkeypatch.setattr(
        web_app.GestorInventario,
        "crear_backup",
        lambda _self: "C:\\temp\\inventario-backup.db",
    )
    backup = client.get("/api/inventario/backup")
    assert backup.status_code == 200
    assert backup.get_json()["archivo"] == "inventario-backup.db"
