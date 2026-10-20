import tempfile
import os
import csv
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Producto, Presentacion, TipoPresentacion, MovimientoInventario, EstadoMovimiento
from core.inventory_manager import GestorInventario


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos en memoria para pruebas."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_busqueda_inteligente_productos(db_session):
    gestor = GestorInventario(db_session)
    p1 = gestor.registrar_producto(gtin="750100000001", nombre="Cuaderno Profesional Rayado", laboratorio="Scribe", descripcion="100 hojas cuadricula")
    p2 = gestor.registrar_producto(gtin="750100000002", nombre="Lápiz de Grafito HB", laboratorio="Dixon", descripcion="Madera de cedro")
    p3 = gestor.registrar_producto(gtin="750100000003", nombre="Bolígrafo Azul Punto Medio", laboratorio="BIC", descripcion="Tinta indeleble")

    # Búsqueda por parte del nombre sin distinción de mayúsculas/minúsculas
    resultados = gestor.buscar_productos("cuaderno")
    assert len(resultados) == 1
    assert resultados[0].id == p1.id

    # Búsqueda por laboratorio
    resultados_lab = gestor.buscar_productos("dixon")
    assert len(resultados_lab) == 1
    assert resultados_lab[0].id == p2.id

    # Búsqueda por GTIN parcial o completo
    resultados_gtin = gestor.buscar_productos("000003")
    assert len(resultados_gtin) == 1
    assert resultados_gtin[0].id == p3.id

    # Búsqueda vacía retorna todos
    assert len(gestor.buscar_productos("")) == 3


def test_calcular_valor_inventario_y_rentabilidad(db_session):
    gestor = GestorInventario(db_session)
    p1 = gestor.registrar_producto(gtin="750100000010", nombre="Regla 30cm", laboratorio="Baco")
    gestor.agregar_presentacion(
        producto_id=p1.id,
        tipo_presentacion="unidad",
        cantidad=1,
        precio_unitario=10.0,
        precio_venta=25.0,
        stock_inicial=20
    )

    p2 = gestor.registrar_producto(gtin="750100000020", nombre="Goma de borrar", laboratorio="Pelikan")
    gestor.agregar_presentacion(
        producto_id=p2.id,
        tipo_presentacion="unidad",
        cantidad=1,
        precio_unitario=5.0,
        precio_venta=12.0,
        stock_inicial=10
    )

    valoracion = gestor.calcular_valor_inventario()
    # Costo: (20 * 10) + (10 * 5) = 200 + 50 = 250
    assert valoracion["valor_costo_total"] == 250
    # Venta potencial: (20 * 25) + (10 * 12) = 500 + 120 = 620
    assert valoracion["valor_venta_potencial"] == 620
    # Ganancia proyectada: 620 - 250 = 370
    assert valoracion["ganancia_proyectada"] == 370
    assert valoracion["margen_promedio_porcentaje"] > 0


def test_obtener_sugerencias_reabastecimiento(db_session):
    gestor = GestorInventario(db_session)
    p = gestor.registrar_producto(gtin="750100000030", nombre="Sacapuntas metálico", laboratorio="Maped")
    # Stock mínimo 15, stock actual 3 -> en alerta
    pres = gestor.agregar_presentacion(
        producto_id=p.id,
        tipo_presentacion="unidad",
        cantidad=1,
        precio_unitario=3.0,
        precio_venta=8.0,
        stock_inicial=3
    )
    pres.stock_minimo = 15
    db_session.commit()

    sugerencias = gestor.obtener_sugerencias_reabastecimiento()
    assert len(sugerencias) >= 1
    sug = next(s for s in sugerencias if s["gtin"] == "750100000030")
    assert sug["stock_actual"] == 3
    assert sug["stock_minimo"] == 15
    # Sugerido debe ser al menos la diferencia para llegar o superar el mínimo
    assert sug["unidades_sugeridas"] >= 12


def test_exportar_e_importar_catalogo_csv(db_session):
    gestor = GestorInventario(db_session)
    p = gestor.registrar_producto(gtin="750100000040", nombre="Pegamento en Barra", laboratorio="Pritt", descripcion="22g no tóxico")
    gestor.agregar_presentacion(
        producto_id=p.id,
        tipo_presentacion="unidad",
        cantidad=1,
        precio_unitario=15.0,
        precio_venta=30.0,
        stock_inicial=50
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "catalogo.csv")
        export_res = gestor.exportar_catalogo_csv(csv_path)
        assert export_res is True
        assert os.path.exists(csv_path)

        # Crear nueva base de datos limpia para importar
        engine2 = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine2)
        Session2 = sessionmaker(bind=engine2)
        session2 = Session2()
        gestor2 = GestorInventario(session2)

        resultado_import = gestor2.importar_catalogo_csv(csv_path)
        assert resultado_import["exitosos"] == 1
        assert resultado_import["errores"] == 0

        prod_importado = gestor2.obtener_producto_por_gtin("750100000040")
        assert prod_importado is not None
        assert prod_importado.nombre == "Pegamento en Barra"
        assert len(prod_importado.presentaciones) == 1
        assert prod_importado.presentaciones[0].stock_actual == 50
        session2.close()


def test_crear_backup_database():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "inventario_test.db")
        # Crear un archivo de BD sqlite válido
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        gestor = GestorInventario(session)
        gestor.registrar_producto(gtin="750199999999", nombre="Item de prueba backup")

        backup_dir = os.path.join(tmpdir, "backups")
        archivo_backup = gestor.crear_backup(sqlite_file_path=db_path, backup_dir=backup_dir)
        assert archivo_backup is not None
        assert os.path.exists(archivo_backup)
        assert "backup_inventario_" in os.path.basename(archivo_backup)

        backups = gestor.listar_backups(backup_dir=backup_dir)
        assert len(backups) == 1
        assert backups[0]["archivo"] == os.path.basename(archivo_backup)
        session.close()
        engine.dispose()
