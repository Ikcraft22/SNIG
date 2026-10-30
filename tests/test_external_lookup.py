from unittest.mock import Mock

import pytest
import requests

from api.gtin_lookup import GTINBuscador, GTINLookup
from core.barcode_scanner import BarcodeLector, EscanerProducto


def test_busqueda_openfoodfacts_mapea_producto_y_ignora_no_encontrado(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {
        "status": 1,
        "product": {
            "product_name": "Avena",
            "ingredients_text": "Avena",
            "categories": "Cereales",
            "url": "https://example.test/avena",
        },
    }
    request = Mock(return_value=response)
    monkeypatch.setattr("api.gtin_lookup.requests.get", request)

    resultado = GTINLookup.buscar_por_openfoodfacts("7500000000000")

    assert resultado["nombre"] == "Avena"
    assert resultado["fuente"] == "OpenFoodFacts"
    assert resultado["url"].endswith("/avena")
    request.assert_called_once()

    response.json.return_value = {"status": 0}
    assert GTINLookup.buscar_por_openfoodfacts("7500000000000") is None


def test_busqueda_openfoodfacts_y_google_manejan_fallos_de_red(monkeypatch):
    monkeypatch.setattr("api.gtin_lookup.GOOGLE_API_KEY", "clave-prueba")
    monkeypatch.setattr("api.gtin_lookup.GOOGLE_SEARCH_ENGINE_ID", "motor-prueba")
    monkeypatch.setattr(
        "api.gtin_lookup.requests.get",
        Mock(side_effect=requests.exceptions.Timeout("timeout")),
    )
    assert GTINLookup.buscar_por_openfoodfacts("7500000000000") is None
    assert GTINLookup.buscar_por_google("7500000000000") is None


def test_google_busqueda_sin_credenciales_con_resultados_y_sin_resultados(monkeypatch):
    cliente = GTINLookup
    monkeypatch.setattr("api.gtin_lookup.GOOGLE_API_KEY", "")
    monkeypatch.setattr("api.gtin_lookup.GOOGLE_SEARCH_ENGINE_ID", "")
    assert cliente.buscar_por_google("7500000000000") is None

    monkeypatch.setattr("api.gtin_lookup.GOOGLE_API_KEY", "clave-prueba")
    monkeypatch.setattr("api.gtin_lookup.GOOGLE_SEARCH_ENGINE_ID", "motor-prueba")
    response = Mock(status_code=200)
    response.json.return_value = {
        "items": [{
            "title": "Café",
            "snippet": "Café molido",
            "link": "https://example.test/cafe",
        }]
    }
    monkeypatch.setattr("api.gtin_lookup.requests.get", Mock(return_value=response))
    resultado = cliente.buscar_por_google("7500000000000")
    assert resultado["nombre"] == "Café"
    assert resultado["fuente"] == "Google Custom Search"

    response.json.return_value = {}
    assert cliente.buscar_por_google("7500000000000") is None
    response.status_code = 403
    assert cliente.buscar_por_google("7500000000000") is None


def test_busqueda_combinada_usa_google_como_respaldo(monkeypatch):
    monkeypatch.setattr(GTINLookup, "buscar_por_openfoodfacts", Mock(return_value=None))
    monkeypatch.setattr(
        GTINLookup,
        "buscar_por_google",
        Mock(return_value={"fuente": "Google Custom Search"}),
    )
    resultado = GTINLookup.buscar_gtin("7500000000000")
    assert resultado["fuente"] == "Google Custom Search"

    monkeypatch.setattr(GTINLookup, "buscar_por_google", Mock(return_value=None))
    assert GTINLookup.buscar_gtin("7500000000000") is None

    monkeypatch.setattr(
        GTINLookup,
        "buscar_por_openfoodfacts",
        Mock(return_value={"fuente": "OpenFoodFacts"}),
    )
    assert GTINLookup.buscar_gtin("7500000000000")["fuente"] == "OpenFoodFacts"

    buscador = GTINBuscador()
    monkeypatch.setattr(buscador.lookup, "buscar_gtin", Mock(return_value=None))
    assert buscador.buscar("7500000000000")["encontrado"] is False


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ("12345670", (True, "GTIN-8")),
        ("123456789012", (True, "GTIN-12")),
        ("1234567890123", (True, "GTIN-13")),
        ("12345678901234", (True, "GTIN-14")),
        ("1234", (False, None)),
        ("1234567x", (False, None)),
    ],
)
def test_barcode_valida_longitudes_y_limpia_caracteres(codigo, esperado):
    assert BarcodeLector.validar_gtin(codigo) == esperado
    assert BarcodeLector.limpiar_codigo(" 75-0123  ") == "750123"


def test_barcode_checksum_scanner_y_escaner_simplificado(monkeypatch):
    codigo = BarcodeLector.generar_gtin13_con_checksum("750")
    assert len(codigo) == 13
    assert BarcodeLector.verificar_digito(codigo)
    assert not BarcodeLector.verificar_digito("123")
    assert not BarcodeLector.verificar_digito(codigo[:-1] + str((int(codigo[-1]) + 1) % 10))

    monkeypatch.setattr("builtins.input", lambda *_: f"{codigo[:4]}-{codigo[4:]}")
    assert BarcodeLector.escanear_terminal() == codigo
    assert EscanerProducto().validar(codigo)

    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert BarcodeLector.escanear_terminal() is None
    monkeypatch.setattr("builtins.input", lambda *_: "abc")
    assert BarcodeLector.escanear_terminal() is None
    monkeypatch.setattr("builtins.input", Mock(side_effect=KeyboardInterrupt))
    assert BarcodeLector.escanear_terminal() is None


def test_barcode_lee_archivo_y_devuelve_lista_vacia_ante_errores(tmp_path):
    archivo = tmp_path / "codigos.txt"
    archivo.write_text("12345670\ninvalid\n", encoding="utf-8")
    assert BarcodeLector.leer_archivo_codigos(str(archivo)) == ["12345670"]
    assert BarcodeLector.leer_archivo_codigos(str(tmp_path / "no-existe.txt")) == []
