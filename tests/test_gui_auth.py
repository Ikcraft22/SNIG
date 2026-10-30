from types import SimpleNamespace
from unittest.mock import Mock

from PyQt5.QtWidgets import QApplication
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import ui.gui_ui as gui_ui
from core.auth import crear_usuario
from database.connection import Base
from database.models import Presentacion, Producto, TipoPresentacion, Usuario


def test_dialogo_login_autentica_y_no_acepta_contrasena_incorrecta(monkeypatch):
    app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        usuario = crear_usuario(db, "Ana", "cajero", "Contraseña-Segura-2026")
        dialogo = gui_ui.DialogoLogin(db)
        monkeypatch.setattr(
            gui_ui,
            "QMessageBox",
            SimpleNamespace(warning=Mock(), critical=Mock()),
        )

        dialogo.entrada_password.setText("incorrecta")
        dialogo._autenticar()
        assert dialogo.result() != gui_ui.QDialog.Accepted
        assert dialogo.usuario is None

        dialogo.entrada_password.setText("Contraseña-Segura-2026")
        dialogo._autenticar()
        assert dialogo.result() == gui_ui.QDialog.Accepted
        assert dialogo.usuario.id == usuario.id
        dialogo.close()
    engine.dispose()


def test_dialogo_configura_primer_admin_sin_password_predeterminada():
    app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        dialogo = gui_ui.DialogoLogin(db)
        assert dialogo.configuracion_inicial
        dialogo.entrada_nombre.setText("Dueña")
        dialogo.entrada_password.setText("Contraseña-Segura-2026")
        dialogo.entrada_confirmacion.setText("Contraseña-Segura-2026")
        dialogo._autenticar()

        admin = db.query(Usuario).one()
        assert dialogo.result() == gui_ui.QDialog.Accepted
        assert admin.nombre == "Dueña"
        assert admin.rol == "admin"
        assert admin.password_hash != "Contraseña-Segura-2026"
        dialogo.close()
    engine.dispose()


def test_permisos_ocultan_secciones_y_accesos_no_autorizados(monkeypatch):
    monkeypatch.setattr(gui_ui, "AUTENTICACION_HABILITADA", True)

    class Tabs:
        def __init__(self):
            self.visibilidad = {}
            self.indice = 0

        def count(self):
            return 7

        def tabBar(self):
            return self

        def setTabVisible(self, indice, visible):
            self.visibilidad[indice] = visible

        def currentIndex(self):
            return self.indice

        def setCurrentIndex(self, indice):
            self.indice = indice

    class Control:
        def __init__(self):
            self.visible = None

        def setVisible(self, visible):
            self.visible = visible

    tabs = Tabs()
    nav = [Control() for _ in range(7)]
    tarjetas = [(Control(), indice) for indice in (1, 2, 3)]
    ventana = SimpleNamespace(
        usuario_actual=SimpleNamespace(nombre="Ana", rol="cajero"),
        pestanas=tabs,
        _nav_buttons=nav,
        _boton_inicio_pos=Control(),
        _home_financial_cards=[Control()],
        _home_access_buttons=tarjetas,
        etiqueta_usuario=SimpleNamespace(setText=Mock()),
        _actualizar_navegacion=Mock(),
    )

    gui_ui.VentanaPrincipal._aplicar_permisos_rol(ventana)

    assert {indice for indice, visible in tabs.visibilidad.items() if visible} == {0, 2}
    assert nav[0].visible and nav[2].visible
    assert not nav[1].visible and not nav[3].visible and not nav[4].visible
    assert ventana._boton_inicio_pos.visible
    assert not ventana._home_financial_cards[0].visible
    assert [card.visible for card, _ in tarjetas] == [False, True, False]
    assert "Ana (cajero)" in ventana.etiqueta_usuario.setText.call_args.args[0]


def test_init_db_migra_usuarios_existentes_sin_borrar_registros(monkeypatch):
    from database import connection

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as db:
        db.execute(text(
            "CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nombre VARCHAR(255) NOT NULL)"
        ))
        db.execute(text("INSERT INTO usuarios (id, nombre) VALUES (1, 'Legacy')"))
    monkeypatch.setattr(connection, "engine", engine)

    connection.create_tables()

    with engine.connect() as db:
        row = db.execute(
            text("SELECT id, nombre, password_hash FROM usuarios")
        ).one()
    assert row == (1, "Legacy", None)
    engine.dispose()


def test_ventana_aplica_roles_reales_al_iniciar(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui_ui, "AUTENTICACION_HABILITADA", True)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        producto = Producto(gtin="750000000003", nombre="Demo")
        db.add(producto)
        db.flush()
        db.add(Presentacion(
            producto_id=producto.id,
            tipo=TipoPresentacion.UNIDAD,
            cantidad=1,
            precio_unitario=10,
            precio_venta=20,
            stock_actual=5,
            stock_minimo=2,
        ))
        db.commit()

        esperados = {
            "cajero": {0, 2},
            "inventario": {0, 1, 4},
            "admin": {0, 1, 2, 3, 4, 5, 6},
        }
        for rol, visibles in esperados.items():
            ventana = gui_ui.VentanaPrincipal(
                Usuario(nombre="Prueba", rol=rol, activo=True),
                db,
            )
            actuales = {
                indice
                for indice in range(ventana.pestanas.count())
                if ventana.pestanas.tabBar().isTabVisible(indice)
            }
            assert actuales == visibles
            assert ventana._home_financial_cards[0].isHidden() is (rol != "admin")
            ventana.close()
    engine.dispose()


def test_acceso_sin_autenticacion_oculta_usuarios_y_permite_navegacion():
    assert gui_ui.AUTENTICACION_HABILITADA is False

    class Tabs:
        def __init__(self):
            self.visibilidad = {}
            self.indice = 0

        def count(self):
            return 7

        def tabBar(self):
            return self

        def setTabVisible(self, indice, visible):
            self.visibilidad[indice] = visible

        def currentIndex(self):
            return self.indice

        def setCurrentIndex(self, indice):
            self.indice = indice

    class Control:
        def __init__(self):
            self.visible = None

        def setVisible(self, visible):
            self.visible = visible

        def hide(self):
            self.visible = False

    ventana = SimpleNamespace(
        pestanas=Tabs(),
        _nav_buttons=[Control() for _ in range(7)],
        _boton_inicio_pos=Control(),
        _home_financial_cards=[Control()],
        _home_access_buttons=[
            (Control(), indice) for indice in range(1, 7)
        ],
        etiqueta_usuario=Control(),
        boton_cambiar_usuario=Control(),
        _actualizar_navegacion=Mock(),
    )

    gui_ui.VentanaPrincipal._aplicar_permisos_rol(ventana)

    assert {indice for indice, visible in ventana.pestanas.visibilidad.items() if visible} == {
        0, 1, 2, 3, 4, 5
    }
    assert not ventana._nav_buttons[6].visible
    assert not ventana._home_access_buttons[-1][0].visible
    assert all(tarjeta.visible for tarjeta, _ in ventana._home_access_buttons[:-1])
    assert ventana._home_financial_cards[0].visible
    assert not ventana.etiqueta_usuario.visible
    assert not ventana.boton_cambiar_usuario.visible


def test_ventana_principal_desactiva_usuario_y_restricciones_por_rol(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui_ui.QMessageBox, "information", Mock())
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        ventana = gui_ui.VentanaPrincipal(None, db)

        assert ventana.usuario_actual is None
        assert not hasattr(ventana, "tabla_usuarios")
        assert not ventana.pestanas.tabBar().isTabVisible(6)
        assert all(
            ventana.pestanas.tabBar().isTabVisible(indice)
            for indice in range(6)
        )
        assert ventana._nav_buttons[6].isHidden()
        assert ventana.etiqueta_usuario.isHidden()
        assert ventana.boton_cambiar_usuario.isHidden()
        assert not ventana._home_financial_cards[0].isHidden()
        ventana.close()
    engine.dispose()


def test_interfaz_inicia_sin_mostrar_login(monkeypatch):
    app = QApplication.instance() or QApplication([])
    estado = {}

    class Ventana:
        def __init__(self, usuario, db):
            estado["usuario"] = usuario

        def setWindowIcon(self, icono):
            pass

        def configurar_logger_grafico(self):
            pass

    class LoginNoEsperado:
        def __init__(self, *args, **kwargs):
            raise AssertionError("El diálogo de acceso debe estar desactivado")

    monkeypatch.setattr(gui_ui, "AUTENTICACION_HABILITADA", False)
    monkeypatch.setattr(gui_ui, "init_db", lambda: None)
    monkeypatch.setattr(gui_ui, "SessionLocal", lambda: object())
    monkeypatch.setattr(gui_ui, "VentanaPrincipal", Ventana)
    monkeypatch.setattr(gui_ui, "DialogoLogin", LoginNoEsperado)
    monkeypatch.setattr(gui_ui.InterfazGUI, "_configurar_alertas_bandeja", lambda *args: None)

    interfaz = gui_ui.InterfazGUI(app)

    assert not interfaz.cancelado
    assert estado["usuario"] is None
