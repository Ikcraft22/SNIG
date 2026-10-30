"""Autenticación local y configuración segura de cuentas SNIG."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from database.connection import SessionLocal, init_db
from database.models import Usuario

logger = logging.getLogger(__name__)
HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 600_000
SALT_BYTES = 16
PASSWORD_MIN_LENGTH = 12
ROLES_VALIDOS = {"admin", "inventario", "cajero"}


def hash_password(password: str) -> str:
    """Genera un hash PBKDF2-SHA256 con salt aleatorio."""
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres")
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt_text}${digest_text}"


def verificar_password(password: str, password_hash: Optional[str]) -> bool:
    """Verifica un hash versionado; los formatos inválidos nunca autentican."""
    if not password or not password_hash:
        return False
    try:
        algoritmo, iteraciones_texto, salt_texto, digest_esperado = password_hash.split("$")
        iteraciones = int(iteraciones_texto)
        if algoritmo != HASH_ALGORITHM or not 100_000 <= iteraciones <= 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_texto + "=" * (-len(salt_texto) % 4))
        esperado = base64.urlsafe_b64decode(
            digest_esperado + "=" * (-len(digest_esperado) % 4)
        )
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iteraciones,
        )
        return hmac.compare_digest(actual, esperado)
    except (AttributeError, ValueError, TypeError):
        return False


def crear_administrador_inicial(
    db: Session,
    nombre: str,
    password: str,
    email: Optional[str] = None,
) -> Usuario:
    """Configura el primer administrador cuando la base aún no tiene credenciales."""
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de usuario es obligatorio")
    if db.query(Usuario).filter(Usuario.password_hash.isnot(None)).first():
        raise ValueError("Ya hay credenciales configuradas; inicia sesión con un administrador")

    nuevo_hash = hash_password(password)
    administrador = (
        db.query(Usuario)
        .filter(Usuario.rol == "admin", Usuario.activo.is_(True))
        .order_by(Usuario.id)
        .first()
    )
    if administrador is None:
        administrador = Usuario(
            nombre=nombre,
            email=email.strip() if email and email.strip() else None,
            rol="admin",
            activo=True,
        )
        db.add(administrador)
    administrador.password_hash = nuevo_hash
    db.commit()
    db.refresh(administrador)
    return administrador


def crear_usuario(
    db: Session,
    nombre: str,
    rol: str,
    password: str,
    email: Optional[str] = None,
) -> Usuario:
    """Crea una cuenta activa con rol validado y contraseña protegida."""
    nombre = nombre.strip()
    rol = rol.strip().lower()
    if not nombre:
        raise ValueError("El nombre de usuario es obligatorio")
    if rol not in ROLES_VALIDOS:
        raise ValueError("El rol debe ser admin, inventario o cajero")
    usuario = Usuario(
        nombre=nombre,
        email=email.strip() if email and email.strip() else None,
        rol=rol,
        activo=True,
        password_hash=hash_password(password),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def configurar_administrador_interactivo(nombre: str = "Administrador"):
    """Inicializa o habilita el primer administrador desde una terminal local."""
    init_db()
    password = getpass.getpass("Nueva contraseña (mínimo 12 caracteres): ")
    confirmacion = getpass.getpass("Confirma la contraseña: ")
    if password != confirmacion:
        raise ValueError("Las contraseñas no coinciden")
    db = SessionLocal()
    try:
        usuario = crear_administrador_inicial(db, nombre, password)
        print(f"Administrador configurado: {usuario.nombre}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Configuración segura de usuarios SNIG")
    parser.add_argument(
        "--crear-admin",
        metavar="NOMBRE",
        help="Configura la primera cuenta administradora (solicita la contraseña sin mostrarla)",
    )
    argumentos = parser.parse_args()
    if not argumentos.crear_admin:
        parser.print_help()
        return
    try:
        configurar_administrador_interactivo(argumentos.crear_admin)
    except (ValueError, RuntimeError) as error:
        logger.error("%s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
