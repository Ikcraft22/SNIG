"""Migraciones pequeñas y compatibles para bases de datos existentes."""

import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


_COLUMNAS_FARMACEUTICAS = (
    "cum",
    "principio_activo",
    "laboratorio",
    "registro_sanitario",
)


def asegurar_columna_password_hash(engine: Engine) -> bool:
    """Añade password_hash a usuarios sin reemplazar ni modificar sus datos."""
    inspector = inspect(engine)
    if "usuarios" not in inspector.get_table_names():
        return False
    if "password_hash" in {columna["name"] for columna in inspector.get_columns("usuarios")}:
        return False

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255) NULL")
        )

    if "password_hash" not in {
        columna["name"] for columna in inspect(engine).get_columns("usuarios")
    }:
        raise RuntimeError("No se pudo aplicar la migración password_hash")
    return True


def eliminar_datos_farmaceuticos(engine: Engine) -> bool:
    """Elimina campos farmacéuticos obsoletos y los datos del feed de productos."""
    inspector = inspect(engine)
    if "productos" not in inspector.get_table_names():
        return False

    columnas = {
        columna["name"] for columna in inspector.get_columns("productos")
    }
    columnas_a_eliminar = [
        columna for columna in _COLUMNAS_FARMACEUTICAS if columna in columnas
    ]
    if not columnas_a_eliminar:
        return False

    preparador = engine.dialect.identifier_preparer
    tabla_productos = preparador.quote("productos")
    indices_a_eliminar = [
        indice
        for indice in inspector.get_indexes("productos")
        if any(columna in columnas_a_eliminar for columna in indice["column_names"])
    ]

    with engine.begin() as connection:
        for indice in indices_a_eliminar:
            nombre_indice = preparador.quote(indice["name"])
            if engine.dialect.name == "mysql":
                connection.exec_driver_sql(
                    f"DROP INDEX {nombre_indice} ON {tabla_productos}"
                )
            else:
                connection.exec_driver_sql(f"DROP INDEX {nombre_indice}")

        for columna in columnas_a_eliminar:
            columna_sql = preparador.quote(columna)
            connection.exec_driver_sql(
                f"ALTER TABLE {tabla_productos} DROP COLUMN {columna_sql}"
            )

        tablas = set(inspect(connection).get_table_names())
        if "sync_changes" in tablas:
            columnas_sync = {
                columna["name"]
                for columna in inspect(connection).get_columns("sync_changes")
            }
            if {"id", "entity_type", "payload"}.issubset(columnas_sync):
                cambios = connection.execute(
                    text(
                        "SELECT id, payload FROM sync_changes "
                        "WHERE entity_type = 'productos'"
                    )
                ).all()
                for cambio_id, payload in cambios:
                    datos = json.loads(payload)
                    if not isinstance(datos, dict):
                        continue
                    modificado = False
                    for columna in _COLUMNAS_FARMACEUTICAS:
                        if columna in datos:
                            del datos[columna]
                            modificado = True
                    if modificado:
                        connection.execute(
                            text(
                                "UPDATE sync_changes SET payload = :payload "
                                "WHERE id = :id"
                            ),
                            {
                                "payload": json.dumps(
                                    datos, ensure_ascii=False, allow_nan=False
                                ),
                                "id": cambio_id,
                            },
                        )

    columnas_finales = {
        columna["name"] for columna in inspect(engine).get_columns("productos")
    }
    if any(columna in columnas_finales for columna in _COLUMNAS_FARMACEUTICAS):
        raise RuntimeError("No se pudieron eliminar todos los campos farmacéuticos")
    return True
