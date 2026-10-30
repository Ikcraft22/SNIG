import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from core.auth import (
    crear_administrador_inicial,
    crear_usuario,
    hash_password,
    verificar_password,
)
from database.connection import Base
from database.migrations import asegurar_columna_password_hash
from database.models import Usuario


@pytest.fixture
def auth_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_hash_password_uses_salt_and_verifies():
    primero = hash_password("Contraseña-Segura-2026")
    segundo = hash_password("Contraseña-Segura-2026")

    assert primero.startswith("pbkdf2_sha256$600000$")
    assert primero != segundo
    assert verificar_password("Contraseña-Segura-2026", primero)
    assert not verificar_password("incorrecta", primero)
    assert not verificar_password("Contraseña-Segura-2026", "malformado")
    assert not verificar_password("anything", None)


def test_password_minimo_y_roles_se_validan(auth_db):
    with pytest.raises(ValueError, match="12 caracteres"):
        hash_password("corta")
    with pytest.raises(ValueError, match="rol"):
        crear_usuario(auth_db, "Ana", "superuser", "Contraseña-Segura-2026")
    with pytest.raises(ValueError, match="nombre"):
        crear_usuario(auth_db, " ", "cajero", "Contraseña-Segura-2026")


def test_administrador_inicial_habilita_admin_legacy_y_bloquea_repeticion(auth_db):
    legacy = Usuario(nombre="Administrador", rol="admin", activo=True)
    auth_db.add(legacy)
    auth_db.commit()

    admin = crear_administrador_inicial(
        auth_db,
        "Nuevo nombre no reemplaza al existente",
        "Contraseña-Segura-2026",
    )

    assert admin.id == legacy.id
    assert admin.nombre == "Administrador"
    assert verificar_password("Contraseña-Segura-2026", admin.password_hash)
    with pytest.raises(ValueError, match="credenciales configuradas"):
        crear_administrador_inicial(auth_db, "Otro", "Otra-Contraseña-Segura")


def test_crear_usuario_persiste_hash_y_rol(auth_db):
    usuario = crear_usuario(
        auth_db,
        "Cajero 1",
        "cajero",
        "Contraseña-Segura-2026",
    )

    assert usuario.rol == "cajero"
    assert usuario.password_hash != "Contraseña-Segura-2026"
    assert verificar_password("Contraseña-Segura-2026", usuario.password_hash)


def test_migracion_password_hash_es_aditiva_e_idempotente():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nombre VARCHAR(255) NOT NULL)"
        ))
        connection.execute(text(
            "INSERT INTO usuarios (id, nombre) VALUES (1, 'Legacy')"
        ))

    assert asegurar_columna_password_hash(engine)
    assert not asegurar_columna_password_hash(engine)
    columnas = {columna["name"] for columna in inspect(engine).get_columns("usuarios")}
    with engine.connect() as connection:
        usuario = connection.execute(
            text("SELECT id, nombre, password_hash FROM usuarios WHERE id = 1")
        ).one()

    assert "password_hash" in columnas
    assert usuario == (1, "Legacy", None)
    engine.dispose()
