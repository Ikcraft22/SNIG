import pytest
from core.barcode_scanner import BarcodeLector


def test_generar_gtin13_con_checksum():
    # Probar con prefijo de 12 dígitos
    prefijo = "750123456789"
    gtin = BarcodeLector.generar_gtin13_con_checksum(prefijo)
    assert len(gtin) == 13
    assert gtin.startswith(prefijo)
    assert BarcodeLector.verificar_digito(gtin) is True

    es_valido, tipo = BarcodeLector.validar_gtin(gtin)
    assert es_valido is True
    assert tipo == "GTIN-13"


def test_generar_gtin13_con_prefijo_corto():
    # Si el prefijo tiene menos de 12 dígitos, debe completarse o validarse
    prefijo = "7501"
    gtin = BarcodeLector.generar_gtin13_con_checksum(prefijo)
    assert len(gtin) == 13
    assert BarcodeLector.verificar_digito(gtin) is True
