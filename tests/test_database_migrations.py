import json

from sqlalchemy import create_engine, inspect, text

from database.migrations import eliminar_datos_farmaceuticos


def test_eliminar_datos_farmaceuticos_conserva_inventario_y_limpia_sync():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE productos (
                id INTEGER PRIMARY KEY,
                gtin VARCHAR(20) NOT NULL UNIQUE,
                cum VARCHAR(50),
                nombre VARCHAR(255) NOT NULL,
                descripcion TEXT,
                principio_activo VARCHAR(255),
                laboratorio VARCHAR(255),
                registro_sanitario VARCHAR(100),
                fecha_creacion DATETIME
            )
            """
        )
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX ix_productos_cum ON productos (cum)"
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE presentaciones (
                id INTEGER PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                stock_actual INTEGER NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE sync_changes (
                id INTEGER PRIMARY KEY,
                entity_type VARCHAR(50) NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        connection.execute(
            text(
                """
                INSERT INTO productos
                    (id, gtin, cum, nombre, descripcion, principio_activo,
                     laboratorio, registro_sanitario, fecha_creacion)
                VALUES
                    (1, '1234567890123', 'cum-confidencial', 'Producto',
                     'Descripción', 'principio-confidencial', 'laboratorio-confidencial',
                     'registro-confidencial', CURRENT_TIMESTAMP)
                """
            )
        )
        connection.exec_driver_sql(
            "INSERT INTO presentaciones (id, producto_id, stock_actual) VALUES (1, 1, 7)"
        )
        connection.execute(
            text(
                "INSERT INTO sync_changes (id, entity_type, payload) "
                "VALUES (1, 'productos', :payload)"
            ),
            {
                "payload": json.dumps(
                    {
                        "id": 1,
                        "gtin": "1234567890123",
                        "nombre": "Producto",
                        "cum": "cum-confidencial",
                        "principio_activo": "principio-confidencial",
                        "laboratorio": "laboratorio-confidencial",
                        "registro_sanitario": "registro-confidencial",
                    }
                )
            },
        )
        connection.execute(
            text(
                "INSERT INTO sync_changes (id, entity_type, payload) "
                "VALUES (2, 'ventas', :payload)"
            ),
            {"payload": '{"id": 2, "total": 25}'},
        )

    assert eliminar_datos_farmaceuticos(engine)
    assert not eliminar_datos_farmaceuticos(engine)

    columnas = {columna["name"] for columna in inspect(engine).get_columns("productos")}
    assert not columnas.intersection(
        {"cum", "principio_activo", "laboratorio", "registro_sanitario"}
    )
    with engine.connect() as connection:
        producto = connection.execute(
            text("SELECT id, gtin, nombre, descripcion FROM productos")
        ).one()
        assert tuple(producto) == (
            1,
            "1234567890123",
            "Producto",
            "Descripción",
        )
        assert connection.execute(
            text("SELECT producto_id, stock_actual FROM presentaciones")
        ).one() == (1, 7)
        datos_sync = json.loads(
            connection.execute(
                text("SELECT payload FROM sync_changes WHERE id = 1")
            ).scalar_one()
        )
        assert datos_sync == {
            "id": 1,
            "gtin": "1234567890123",
            "nombre": "Producto",
        }
        assert connection.execute(
            text("SELECT payload FROM sync_changes WHERE id = 2")
        ).scalar_one() == '{"id": 2, "total": 25}'
    engine.dispose()
