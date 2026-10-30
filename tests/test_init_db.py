import pytest

import init_db
from config import settings


@pytest.mark.parametrize(
    ("autenticacion_habilitada", "espera_configuracion"),
    [(False, False), (True, True)],
)
def test_init_db_configura_usuario_solo_con_autenticacion_habilitada(
    monkeypatch,
    autenticacion_habilitada,
    espera_configuracion,
):
    configurar_admin = []
    monkeypatch.setattr(settings, "AUTENTICACION_HABILITADA", autenticacion_habilitada)
    monkeypatch.setattr(init_db, "validar_ambiente", lambda: True)
    monkeypatch.setattr(init_db, "crear_tablas", lambda: True)
    monkeypatch.setattr(
        init_db,
        "crear_usuario_administrador",
        lambda: configurar_admin.append(True),
    )
    monkeypatch.setattr(init_db, "cargar_datos_iniciales", lambda: True)
    monkeypatch.setattr(init_db, "mostrar_resumen", lambda: None)

    init_db.main()

    assert bool(configurar_admin) is espera_configuracion
