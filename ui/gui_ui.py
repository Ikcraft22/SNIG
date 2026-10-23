"""
Interfaz Gráfica (GUI) con PyQt5 para el sistema de inventario.
Proporciona una interfaz visual profesional con:
- Gestión de inventario
- Punto de venta (POS)
- Reportes en tiempo real
"""

import sys
import json
import subprocess
import webbrowser
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import random

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
        QComboBox, QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox,
            QInputDialog, QAction, QMenu,
        QMessageBox, QTabWidget, QListWidget, QListWidgetItem,
        QPlainTextEdit, QSplitter, QStatusBar, QFormLayout, QStackedWidget,
            QSizePolicy, QHeaderView, QSlider, QFrame, QGridLayout, QButtonGroup
    )
    from PyQt5.QtCore import Qt, QSize, QTimer, QEvent
    from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    print("⚠️ PyQt5 no está instalado. Use: pip install PyQt5")

from database.connection import SessionLocal, init_db
from database.models import Producto, Proveedor
from core.barcode_scanner import EscanerProducto
from core.inventory_manager import GestorInventario
from core.pos_manager import GestorPOS, calcular_vuelto
from config.settings import PRESENTACIONES, MONEDA
from ui.switch_dia_noche import SwitchDiaNoche

logger = logging.getLogger(__name__)


def formatear_numero(valor, decimales=0):
    """Devuelve el número con separador de miles en formato latino."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "0"
    formato = f"{numero:,.{decimales}f}"
    return formato.replace(",", "X").replace(".", ",").replace("X", ".")


def formatear_moneda(valor, decimales=0):
    """Devuelve el monto formateado con símbolo y separadores."""
    return f"{MONEDA}{formatear_numero(valor, decimales=decimales)}"


def _estilo_formularios(modo_oscuro):
    """Devuelve colores consistentes para los formularios del tema activo."""
    if modo_oscuro:
        fondo, superficie, texto, texto_secundario, borde, seleccion = (
            "#101827", "#182438", "#f3f6fb", "#a9b8cc", "#2b3b52", "#263b59"
        )
    else:
        fondo, superficie, texto, texto_secundario, borde, seleccion = (
            "#f3f6fb", "#ffffff", "#202938", "#667085", "#dce3ed", "#e8f0fe"
        )
    return (
        f"QDialog, QWidget {{ background-color: {fondo}; color: {texto}; }}"
        f"QLabel {{ color: {texto}; }}"
        f"QLineEdit, QPlainTextEdit, QListWidget {{ background-color: {superficie}; "
        f"color: {texto}; border: 1px solid {borde}; border-radius: 6px; padding: 6px; }}"
        f"QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus {{ border: 2px solid #2563eb; }}"
        f"QListWidget::item:selected {{ background-color: {seleccion}; color: {texto}; }}"
        f"QPushButton {{ background-color: {superficie}; color: {texto}; border: 1px solid {borde}; "
        "border-radius: 6px; padding: 8px 12px; min-height: 24px; }"
        "QPushButton:hover { border-color: #2563eb; }"
        "QPushButton:default { background-color: #2563eb; color: #ffffff; border: none; }"
        f"QHeaderView::section {{ background-color: {superficie}; color: {texto}; "
        f"border: 1px solid {borde}; padding: 6px; font-weight: 700; }}"
        f"QTableWidget {{ background-color: {superficie}; alternate-background-color: "
        f"{seleccion}; color: {texto}; gridline-color: {borde}; border: 1px solid {borde}; }}"
        f"QTableWidget::item {{ color: {texto}; padding: 5px; }}"
        "QTableWidget::item:selected { background-color: #2563eb; color: #ffffff; }"
    )


class QtLogHandler(logging.Handler):
    """Handler de logging que escribe mensajes en un widget Qt."""

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    def emit(self, record):
        msg = self.format(record)
        if self.widget is not None:
            self.widget.appendPlainText(msg)

class InterfazGUI:
    """Interfaz Gráfica del Sistema de Inventario"""
    
    def __init__(self, app=None):
        """Inicializa la interfaz gráfica"""
        if not PYQT5_AVAILABLE:
            raise ImportError("PyQt5 es requerido para la interfaz gráfica")
        
        self.app = app or QApplication.instance() or QApplication([])
        init_db()
        self.ventana_principal = VentanaPrincipal()
        self.db = SessionLocal()
        self.ventana_principal.configurar_logger_grafico()
    
    def ejecutar(self):
        """Ejecuta la aplicación"""
        self.ventana_principal.show()
        self.app.exec_()


class VentanaPrincipal(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        """Inicializa la ventana principal"""
        super().__init__()
        
        self.setWindowTitle("Sistema de Inventario General")
        
        # Inicializar gestores
        self.db = SessionLocal()
        self.inventario = GestorInventario(self.db)
        self.pos = GestorPOS(self.db)
        self.escaneo = EscanerProducto()
        self._ultimo_producto_carrito_key = None
        self._repeticiones_mismo_producto = 0
        self.archivo_estado = Path(__file__).resolve().parent.parent / ".startup_state.json"
        self.modo_oscuro = self._cargar_modo_oscuro()
        self._indice_pestana_activa = 0
        self.proceso_streamlit = None
        
        # Crear interfaz
        self.crear_ui()

    def crear_ui(self):
        """Crea la interfaz de usuario"""
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        modo_oscuro = self.modo_oscuro

        if modo_oscuro:
            fondo, superficie, texto, texto_secundario, borde = (
                "#101827", "#182438", "#f3f6fb", "#a9b8cc", "#2b3b52"
            )
            self.setStyleSheet(
                "QMainWindow { background-color: #101827; }"
                "QStatusBar { background-color: #182438; color: #e7ebf5; border-top: 1px solid #2b3b52; }"
                "QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #f59e0b; }"
                "QPushButton:focus { border: 2px solid #f59e0b; }"
            )
        else:
            fondo, superficie, texto, texto_secundario, borde = (
                "#f3f6fb", "#ffffff", "#202938", "#667085", "#dce3ed"
            )
            self.setStyleSheet(
                "QMainWindow { background-color: #f3f6fb; }"
                "QStatusBar { background-color: #ffffff; color: #2c3e50; border-top: 1px solid #dce3ed; }"
                "QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #9a5b00; }"
                "QPushButton:focus { border: 2px solid #9a5b00; }"
            )

        self.pestanas = QTabWidget()
        self.pestanas.setAccessibleName("Secciones principales")
        self.pestanas.tabBar().hide()
        self.pestanas.setStyleSheet(
            "QTabWidget::pane { border: none; background: transparent; }"
        )
        self.pestanas.tabBar().installEventFilter(self)

        self.pestanas.addTab(self.crear_pestaña_inicio(), "Inicio")
        self.pestanas.addTab(self.crear_pestaña_inventario(), "📦 Inventario")
        self.pestana_pos = self.crear_pestaña_pos()
        self.pestanas.addTab(self.pestana_pos, "🛒 POS")
        self.pestana_reportes = self.crear_pestaña_reportes()
        self.pestanas.addTab(self.pestana_reportes, "📊 Reportes")
        self.pestana_proveedores = self.crear_pestaña_proveedores()
        self.pestanas.addTab(self.pestana_proveedores, "🏭 Proveedores")
        self.pestana_logs = self.crear_pestaña_logs()
        self.pestanas.addTab(self.pestana_logs, "📝 Logs")
        logs_index = self.pestanas.indexOf(self.pestana_logs)
        self.pestanas.tabBar().setTabVisible(logs_index, False)

        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        barra_lateral = QFrame()
        barra_lateral.setObjectName("sidebar")
        barra_lateral.setFixedWidth(238)
        barra_lateral.setStyleSheet(
            f"QFrame#sidebar {{ background-color: {superficie}; border-right: 1px solid {borde}; }}"
            f"QLabel {{ color: {texto}; }}"
            "QPushButton#navButton { text-align: left; padding: 12px 14px; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: 600; }"
            f"QPushButton#navButton {{ color: {texto_secundario}; background: transparent; }}"
            f"QPushButton#navButton:hover {{ background-color: {'#24344b' if modo_oscuro else '#eef3fa'}; color: {texto}; }}"
            f"QPushButton#navButton:checked {{ background-color: {'#263b59' if modo_oscuro else '#e8f0fe'}; color: {'#ffffff' if modo_oscuro else '#1d4ed8'}; }}"
        )
        sidebar_layout = QVBoxLayout(barra_lateral)
        sidebar_layout.setContentsMargins(18, 24, 18, 18)
        sidebar_layout.setSpacing(8)

        encabezado_marca = QHBoxLayout()
        encabezado_marca.setSpacing(10)
        logo = QLabel()
        logo.setAccessibleName("Logotipo de SNIG")
        logo.setFixedSize(44, 44)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background-color: #ffffff; border-radius: 9px;")
        ruta_logo = Path(__file__).resolve().parent.parent / "Icono.jpeg"
        pixmap_logo = QPixmap(str(ruta_logo))
        if pixmap_logo.isNull():
            logger.warning("No se pudo cargar el logotipo: %s", ruta_logo)
        else:
            simbolo_logo = pixmap_logo.copy(145, 175, 490, 315)
            logo.setPixmap(
                simbolo_logo.scaled(
                    38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        encabezado_marca.addWidget(logo)

        textos_marca = QVBoxLayout()
        textos_marca.setSpacing(1)
        marca = QLabel("SNIG")
        marca.setStyleSheet("font-size: 24px; font-weight: 900; letter-spacing: 2px; color: #2563eb;")
        subtitulo_marca = QLabel("Sistema de gestión")
        subtitulo_marca.setStyleSheet(f"font-size: 12px; color: {texto_secundario};")
        textos_marca.addWidget(marca)
        textos_marca.addWidget(subtitulo_marca)
        encabezado_marca.addLayout(textos_marca)
        encabezado_marca.addStretch(1)
        sidebar_layout.addLayout(encabezado_marca)
        sidebar_layout.addSpacing(26)

        etiqueta_menu = QLabel("MENÚ PRINCIPAL")
        etiqueta_menu.setStyleSheet(
            f"font-size: 10px; font-weight: 800; letter-spacing: 1px; color: {texto_secundario};"
        )
        sidebar_layout.addWidget(etiqueta_menu)

        self._nav_buttons = []
        grupo_navegacion = QButtonGroup(self)
        grupo_navegacion.setExclusive(True)
        elementos_nav = [
            ("⌂   Inicio", 0),
            ("▦   Inventario", 1),
            ("🛒  Punto de venta", 2),
            ("▤   Reportes", 3),
            ("♙   Proveedores", 4),
            ("☷   Registros", 5),
        ]
        for texto_boton, indice in elementos_nav:
            boton = QPushButton(texto_boton)
            boton.setObjectName("navButton")
            boton.setCheckable(True)
            boton.setAccessibleName(texto_boton.strip())
            boton.clicked.connect(
                lambda checked=False, page=indice: self.pestanas.setCurrentIndex(page)
            )
            grupo_navegacion.addButton(boton, indice)
            sidebar_layout.addWidget(boton)
            self._nav_buttons.append(boton)
        self._nav_buttons[5].hide()
        sidebar_layout.addStretch(1)

        estado_local = QLabel("●  Sistema operativo")
        estado_local.setStyleSheet("font-size: 12px; color: #16a34a; font-weight: 700;")
        version = QLabel("Inventario · Escritorio")
        version.setStyleSheet(f"font-size: 11px; color: {texto_secundario};")
        sidebar_layout.addWidget(estado_local)
        sidebar_layout.addWidget(version)

        area_contenido = QWidget()
        area_layout = QVBoxLayout(area_contenido)
        area_layout.setContentsMargins(28, 18, 28, 18)
        area_layout.setSpacing(18)

        barra_superior = QHBoxLayout()
        self.titulo_seccion = QLabel()
        self.titulo_seccion.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {texto};"
        )
        barra_superior.addWidget(self.titulo_seccion)
        barra_superior.addStretch(1)
        self.interruptor_tema = SwitchDiaNoche(checked=modo_oscuro, width=96, height=42)
        self.interruptor_tema.setAccessibleName("Cambiar modo de color")
        self.interruptor_tema.animationFinished.connect(self.cambiar_tema)
        barra_superior.addWidget(self.interruptor_tema)
        area_layout.addLayout(barra_superior)
        area_layout.addWidget(self.pestanas, 1)

        layout_principal.addWidget(barra_lateral)
        layout_principal.addWidget(area_contenido, 1)
        self.pestanas.currentChanged.connect(self._actualizar_navegacion)
        self.pestanas.currentChanged.connect(self._enfocar_gtin_pos_si_corresponde)
        self.pestanas.setCurrentIndex(self._indice_pestana_activa)
        self._actualizar_navegacion(self._indice_pestana_activa)

        self.statusBar().showMessage("Listo")
        if not getattr(self, "_ui_inicializada", False):
            self.resize(1440, 900)
            QTimer.singleShot(0, self.showMaximized)
            self._ui_inicializada = True

    def crear_pestaña_inicio(self) -> QWidget:
        """Crea el panel principal de escritorio con resumen y accesos rápidos."""
        widget = QWidget()
        oscuro = self.modo_oscuro
        texto = "#f3f6fb" if oscuro else "#202938"
        muted = "#a9b8cc" if oscuro else "#667085"
        superficie = "#182438" if oscuro else "#ffffff"
        borde = "#2b3b52" if oscuro else "#dce3ed"
        fondo_hero = "#1d2e47" if oscuro else "#eaf1ff"
        reporte = self.inventario.reporte_general()

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setStyleSheet(
            f"QFrame {{ background-color: {fondo_hero}; border: 1px solid {borde}; border-radius: 14px; }}"
            f"QLabel {{ color: {texto}; border: none; background: transparent; }}"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        bienvenida = QVBoxLayout()
        etiqueta = QLabel("SNIG  ·  CONTROL OPERATIVO")
        etiqueta.setStyleSheet("font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #2563eb;")
        titulo = QLabel("Panel principal")
        titulo.setStyleSheet("font-size: 28px; font-weight: 900;")
        descripcion = QLabel("Administra inventario, ventas y reportes desde una sola aplicación.")
        descripcion.setStyleSheet(f"font-size: 14px; color: {muted};")
        bienvenida.addWidget(etiqueta)
        bienvenida.addWidget(titulo)
        bienvenida.addWidget(descripcion)
        hero_layout.addLayout(bienvenida, 1)
        boton_pos = QPushButton("Abrir punto de venta")
        boton_pos.setMinimumHeight(46)
        boton_pos.setStyleSheet(
            "QPushButton { background: #2563eb; color: white; border: none; border-radius: 8px; "
            "padding: 10px 18px; font-weight: 700; } QPushButton:hover { background: #1d4ed8; }"
        )
        boton_pos.clicked.connect(lambda: self.pestanas.setCurrentIndex(2))
        hero_layout.addWidget(boton_pos)
        layout.addWidget(hero)

        tarjetas = QGridLayout()
        tarjetas.setHorizontalSpacing(14)
        tarjetas.setVerticalSpacing(14)
        metricas = [
            ("PRODUCTOS", formatear_numero(reporte["total_productos"]), "#2563eb"),
            ("STOCK TOTAL", formatear_numero(reporte["total_stock"]), "#0891b2"),
            ("VALOR DEL INVENTARIO", formatear_moneda(reporte["valor_inventario"]), "#16a34a"),
            ("ALERTAS DE STOCK", formatear_numero(reporte["productos_alerta"]), "#ea580c"),
        ]
        for columna, (nombre, valor, color) in enumerate(metricas):
            tarjeta = QFrame()
            tarjeta.setStyleSheet(
                f"QFrame {{ background-color: {superficie}; border: 1px solid {borde}; border-radius: 12px; }}"
                f"QLabel {{ border: none; background: transparent; }}"
            )
            tarjeta_layout = QVBoxLayout(tarjeta)
            tarjeta_layout.setContentsMargins(18, 16, 18, 16)
            label_nombre = QLabel(nombre)
            label_nombre.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {muted};")
            label_valor = QLabel(valor)
            label_valor.setStyleSheet(f"font-size: 23px; font-weight: 900; color: {color};")
            tarjeta_layout.addWidget(label_nombre)
            tarjeta_layout.addWidget(label_valor)
            tarjetas.addWidget(tarjeta, 0, columna)
        layout.addLayout(tarjetas)

        etiqueta_accesos = QLabel("Accesos rápidos")
        etiqueta_accesos.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {texto};")
        layout.addWidget(etiqueta_accesos)

        accesos = QGridLayout()
        accesos.setHorizontalSpacing(14)
        accesos.setVerticalSpacing(14)
        datos_accesos = [
            ("Inventario", "Consulta productos, precios y existencias.", "Ver inventario", 1, "#2563eb"),
            ("Punto de venta", "Agrega productos al carrito y registra ventas.", "Abrir POS", 2, "#16a34a"),
            ("Reportes", "Revisa indicadores de inventario y ventas.", "Ver reportes", 3, "#7c3aed"),
        ]
        for columna, (nombre, descripcion, accion, indice, color) in enumerate(datos_accesos):
            tarjeta = QFrame()
            tarjeta.setStyleSheet(
                f"QFrame {{ background-color: {superficie}; border: 1px solid {borde}; border-radius: 12px; }}"
                f"QLabel {{ border: none; background: transparent; }}"
            )
            tarjeta_layout = QVBoxLayout(tarjeta)
            tarjeta_layout.setContentsMargins(18, 18, 18, 18)
            label_nombre = QLabel(nombre)
            label_nombre.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {texto};")
            label_descripcion = QLabel(descripcion)
            label_descripcion.setWordWrap(True)
            label_descripcion.setStyleSheet(f"font-size: 13px; color: {muted};")
            boton = QPushButton(accion)
            boton.setMinimumHeight(40)
            boton.setStyleSheet(
                f"QPushButton {{ color: {color}; background: transparent; border: 1px solid {color}; "
                "border-radius: 7px; padding: 8px 12px; font-weight: 700; text-align: left; }"
                f"QPushButton:hover {{ background: {color}; color: white; }}"
            )
            boton.clicked.connect(lambda checked=False, page=indice: self.pestanas.setCurrentIndex(page))
            tarjeta_layout.addWidget(label_nombre)
            tarjeta_layout.addWidget(label_descripcion, 1)
            tarjeta_layout.addWidget(boton)
            accesos.addWidget(tarjeta, 0, columna)
        layout.addLayout(accesos)
        layout.addStretch(1)
        return widget

    def _actualizar_navegacion(self, indice: int):
        """Sincroniza el menú lateral y el encabezado con la sección activa."""
        if not hasattr(self, "_nav_buttons"):
            return
        titulos = ["Panel principal", "Inventario", "Punto de venta", "Reportes", "Proveedores", "Registros"]
        if 0 <= indice < len(self._nav_buttons):
            self._nav_buttons[indice].setChecked(True)
            self.titulo_seccion.setText(titulos[indice])

    def _cargar_modo_oscuro(self) -> bool:
        """Carga la preferencia de modo oscuro/claro guardada."""
        if hasattr(self, "archivo_estado") and self.archivo_estado.exists():
            try:
                datos = json.loads(self.archivo_estado.read_text(encoding="utf-8"))
                return bool(datos.get("modo_oscuro", False))
            except Exception as e:
                logger.warning(f"No se pudo cargar la preferencia de tema: {e}")
        return False

    def _guardar_modo_oscuro(self, modo_oscuro: bool):
        """Guarda la preferencia de modo oscuro/claro en el archivo de estado."""
        try:
            datos = {}
            if hasattr(self, "archivo_estado") and self.archivo_estado.exists():
                try:
                    datos = json.loads(self.archivo_estado.read_text(encoding="utf-8"))
                except Exception:
                    datos = {}
            datos["modo_oscuro"] = bool(modo_oscuro)
            self.archivo_estado.write_text(json.dumps(datos, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error al guardar preferencia de tema: {e}")

    def cambiar_tema(self, estado):
        """Cambia manualmente entre tema claro y oscuro y persiste la preferencia."""
        nuevo_modo_oscuro = bool(estado)
        if nuevo_modo_oscuro == self.modo_oscuro:
            return

        self._indice_pestana_activa = self.pestanas.currentIndex()
        self.modo_oscuro = nuevo_modo_oscuro
        self._guardar_modo_oscuro(nuevo_modo_oscuro)
        self.crear_ui()
        self.actualizar_tabla_carrito()
        self.actualizar_resumen_carrito()
        self.configurar_logger_grafico()
    
    def crear_pestaña_inventario(self) -> QWidget:
        """Crea la pestaña de inventario"""
        widget = QWidget()
        if self.modo_oscuro:
            fondo = "#121722"
            superficie = "#1c2434"
            campo = "#202b3d"
            texto = "#f3f6fb"
            texto_secundario = "#c5cfdd"
            borde = "#40506a"
            encabezado = "#26344a"
            alterno = "#182233"
        else:
            fondo = "#f2f3f5"
            superficie = "#ffffff"
            campo = "#ffffff"
            texto = "#202938"
            texto_secundario = "#344054"
            borde = "#c8ccd1"
            encabezado = "#f4f6f8"
            alterno = "#f8fafc"

        widget.setStyleSheet(
            f"QWidget {{ background-color: {fondo}; color: {texto}; }}"
            f"QLabel {{ font-size: 15px; color: {texto}; }}"
            f"QLineEdit {{ padding: 12px; font-size: 15px; min-height: 46px; background-color: {campo}; color: {texto}; border: 1px solid {borde}; border-radius: 8px; }}"
            f"QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {'#f59e0b' if self.modo_oscuro else '#9a5b00'}; }}"
            f"QLineEdit::placeholder {{ color: {texto_secundario}; }}"
            "QPushButton { padding: 10px 16px; font-size: 15px; min-height: 46px; border-radius: 8px; text-align: center; }"
            "QPushButton#primaryButton { background-color: #49689b; color: #ffffff; border: none; }"
            "QPushButton#primaryButton:hover { background-color: #5b7db5; }"
            f"QPushButton#secondaryButton {{ background-color: {superficie}; border: 1px solid {borde}; color: {texto}; }}"
            f"QHeaderView::section {{ background-color: {encabezado}; color: {texto}; font-weight: bold; font-size: 15px; border: none; }}"
            f"QTableWidget {{ background-color: {superficie}; alternate-background-color: {alterno}; color: {texto}; gridline-color: {borde}; border: 1px solid {borde}; }}"
            f"QTableWidget::item {{ color: {texto}; }}"
            "QTableWidget::item:selected { background-color: #49689b; color: #ffffff; }"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        cabecera = QWidget()
        cabecera.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 12px;"
        )
        layout_cabecera = QHBoxLayout(cabecera)
        layout_cabecera.setContentsMargins(16, 14, 16, 14)
        layout_cabecera.setSpacing(12)

        label_gtin = QLabel("GTIN:")
        layout_cabecera.addWidget(label_gtin)

        self.entrada_gtin = QLineEdit()
        label_gtin.setBuddy(self.entrada_gtin)
        self.entrada_gtin.setAccessibleName("Buscar productos")
        self.entrada_gtin.setAccessibleDescription(
            "Busca en el inventario por nombre, GTIN, laboratorio o descripción."
        )
        self.entrada_gtin.setPlaceholderText("Buscar por nombre, GTIN, laboratorio...")
        self.entrada_gtin.setMinimumHeight(42)
        self.entrada_gtin.returnPressed.connect(self.buscar_producto)
        layout_cabecera.addWidget(self.entrada_gtin, 1)

        _btn_style = "padding: 10px 16px; font-size: 15px; min-height: 46px; border-radius: 8px;"
        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setFixedWidth(240)
        btn_buscar.setMinimumHeight(48)
        btn_buscar.setStyleSheet(_btn_style + "background-color: #49689b; color: #ffffff; border: none;")
        btn_buscar.clicked.connect(self.buscar_producto)
        layout_cabecera.addWidget(btn_buscar)

        btn_ver_todos = QPushButton("📋  Ver todos")
        btn_ver_todos.setFixedWidth(240)
        btn_ver_todos.setMinimumHeight(48)
        btn_ver_todos.setStyleSheet(_btn_style + f"background-color: {superficie}; border: 1px solid {borde}; color: {texto};")
        btn_ver_todos.clicked.connect(self.ver_todos_productos)
        layout_cabecera.addWidget(btn_ver_todos)

        layout.addWidget(cabecera)

        contenido = QHBoxLayout()
        contenido.setSpacing(14)

        panel_tabla = QWidget()
        panel_tabla.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_tabla.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 12px;"
        )
        layout_panel_tabla = QVBoxLayout(panel_tabla)
        layout_panel_tabla.setContentsMargins(16, 16, 16, 16)
        layout_panel_tabla.setSpacing(12)

        self.tabla_inventario = QTableWidget()
        self.tabla_inventario.setAccessibleName("Productos del inventario")
        self.tabla_inventario.setAccessibleDescription(
            "Tabla de productos y stock. Usa las flechas para recorrer filas y columnas."
        )
        self.tabla_inventario.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla_inventario.setColumnCount(5)
        self.tabla_inventario.setHorizontalHeaderLabels(
            ["GTIN", "Nombre", "Stock", "Precio", "Proveedor"]
        )
        self.tabla_inventario.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabla_inventario.customContextMenuRequested.connect(self.mostrar_menu_contextual_inventario)
        self.tabla_inventario.setAlternatingRowColors(True)
        self.tabla_inventario.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_inventario.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_inventario.setMinimumHeight(560)
        self.tabla_inventario.setMinimumWidth(0)
        self.tabla_inventario.verticalHeader().setDefaultSectionSize(58)
        self.tabla_inventario.setStyleSheet(
            "QTableWidget { font-size: 17px; }"
            "QHeaderView::section { font-size: 16px; height: 40px; }"
        )
        self.tabla_inventario.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_inventario.horizontalHeader().setStretchLastSection(True)
        layout_panel_tabla.addWidget(self.tabla_inventario)

        contenido.addWidget(panel_tabla, 3)

        panel_acciones = QWidget()
        panel_acciones.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 12px;"
        )
        panel_acciones.setFixedWidth(240)
        layout_panel_acciones = QVBoxLayout(panel_acciones)
        layout_panel_acciones.setContentsMargins(16, 16, 16, 16)
        layout_panel_acciones.setSpacing(14)

        label_acciones = QLabel("Acciones rápidas")
        label_acciones.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout_panel_acciones.addWidget(label_acciones)

        _panel_btn_base = "padding: 10px 14px; font-size: 14px; min-height: 44px; border-radius: 8px; text-align: left;"
        btn_nuevo = QPushButton("➕  Agregar producto")
        btn_nuevo.setMinimumWidth(180)
        btn_nuevo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_nuevo.setStyleSheet(_panel_btn_base + "background-color: #49689b; color: #ffffff; border: none;")
        btn_nuevo.clicked.connect(self.abrir_dialogo_nuevo_producto)
        layout_panel_acciones.addWidget(btn_nuevo)

        btn_entrada = QPushButton("➡️ Entrada de Stock")
        btn_entrada.setMinimumWidth(180)
        btn_entrada.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_entrada.setStyleSheet(_panel_btn_base + f"background-color: {superficie}; border: 1px solid {borde}; color: {texto};")
        btn_entrada.clicked.connect(self.registrar_entrada)
        layout_panel_acciones.addWidget(btn_entrada)

        btn_salida = QPushButton("⬅️ Salida de Stock")
        btn_salida.setMinimumWidth(180)
        btn_salida.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_salida.setStyleSheet(_panel_btn_base + f"background-color: {superficie}; border: 1px solid {borde}; color: {texto};")
        btn_salida.clicked.connect(self.registrar_salida)
        layout_panel_acciones.addWidget(btn_salida)

        btn_exportar = QPushButton("📥 Exportar Catálogo")
        btn_exportar.setMinimumWidth(180)
        btn_exportar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_exportar.setStyleSheet(_panel_btn_base + f"background-color: {superficie}; border: 1px solid {borde}; color: {texto};")
        btn_exportar.clicked.connect(self.exportar_catalogo_gui)
        layout_panel_acciones.addWidget(btn_exportar)

        btn_resumen_fin = QPushButton("💰 Valor Inventario")
        btn_resumen_fin.setMinimumWidth(180)
        btn_resumen_fin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_resumen_fin.setStyleSheet(_panel_btn_base + f"background-color: {superficie}; border: 1px solid {borde}; color: {texto};")
        btn_resumen_fin.clicked.connect(self.mostrar_resumen_financiero_gui)
        layout_panel_acciones.addWidget(btn_resumen_fin)

        layout_panel_acciones.addStretch(1)
        contenido.addWidget(panel_acciones, 1)

        layout.addLayout(contenido)

        self.ver_todos_productos()
        widget.setLayout(layout)
        return widget
    
    def crear_pestaña_pos(self) -> QWidget:
        """Crea la pestaña de punto de venta"""
        widget = QWidget()
        if self.modo_oscuro:
            fondo, superficie, texto, borde = "#121722", "#1c2434", "#f3f6fb", "#40506a"
        else:
            fondo, superficie, texto, borde = "#f7f7f7", "#ffffff", "#202938", "#d0d0d0"
        widget.setStyleSheet(
            f"QWidget {{ background-color: {fondo}; color: {texto}; }}"
            f"QLabel {{ font-size: 15px; color: {texto}; }}"
            f"QLineEdit {{ padding: 8px; font-size: 16px; background-color: {superficie}; color: {texto}; border: 1px solid {borde}; }}"
            f"QLineEdit:focus {{ border: 2px solid {'#f59e0b' if self.modo_oscuro else '#9a5b00'}; }}"
            "QPushButton { padding: 8px 10px; }"
        )
        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(12, 12, 12, 12)
        layout_principal.setSpacing(10)

        # Barra superior: escáner / GTIN
        contenedor_busqueda = QWidget()
        contenedor_busqueda.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 6px; padding: 8px;"
        )
        layout_busqueda = QVBoxLayout(contenedor_busqueda)
        layout_busqueda.setContentsMargins(10, 10, 10, 10)
        layout_busqueda.setSpacing(6)

        label_busqueda = QLabel("Escanea o ingresa el GTIN")
        label_busqueda.setStyleSheet(f"font-weight: bold; color: {texto};")
        layout_busqueda.addWidget(label_busqueda)

        self.entrada_gtin_pos = QLineEdit()
        label_busqueda.setBuddy(self.entrada_gtin_pos)
        self.entrada_gtin_pos.setAccessibleName("Escanear o buscar GTIN")
        self.entrada_gtin_pos.setPlaceholderText("Código")
        self.entrada_gtin_pos.setFixedHeight(36)
        self.entrada_gtin_pos.returnPressed.connect(self.agregar_a_carrito_gui)
        layout_busqueda.addWidget(self.entrada_gtin_pos)

        self.entrada_gtin_pos.setFocus()
        self.entrada_gtin_pos.setFocusPolicy(Qt.StrongFocus)

        layout_principal.addWidget(contenedor_busqueda)

        # Área inferior: carrito y resumen
        layout_contenido = QHBoxLayout()
        layout_contenido.setSpacing(12)

        layout_derecha = QVBoxLayout()
        layout_derecha.setSpacing(8)

        label_carrito = QLabel("Carrito de Compra")
        label_carrito.setStyleSheet(f"font-weight: bold; color: {texto};")
        layout_derecha.addWidget(label_carrito)

        self.tabla_carrito = QTableWidget()
        self.tabla_carrito.setAccessibleName("Carrito de compra")
        self.tabla_carrito.setAccessibleDescription(
            "Productos seleccionados, cantidades, precios y subtotales."
        )
        self.tabla_carrito.setColumnCount(4)
        self.tabla_carrito.setHorizontalHeaderLabels(
            ["Producto", "Cantidad", "Precio", "Subtotal"]
        )
        self.tabla_carrito.setAlternatingRowColors(True)
        self.tabla_carrito.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_carrito.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_carrito.setMinimumHeight(260)
        self.tabla_carrito.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Columnas reactivas al ancho de la ventana
        self.tabla_carrito.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_carrito.horizontalHeader().setStretchLastSection(True)
        # Estilo con soporte para modo oscuro / claro
        if self.modo_oscuro:
            alt_bg = "#1e2d45"
            sel_bg = "#2563eb"
            header_bg = "#1c2434"
            header_text = "#f3f6fb"
            grid_color = "#40506a"
        else:
            alt_bg = "#f0f4ff"
            sel_bg = "#dbeafe"
            header_bg = "#e8edf5"
            header_text = "#202938"
            grid_color = "#d0d0d0"
        self.tabla_carrito.setStyleSheet(
            f"QTableWidget {{ background-color: {superficie}; color: {texto}; "
            f"  gridline-color: {grid_color}; font-size: 13px; border: none; }}"
            f"QTableWidget::item {{ padding: 6px; }}"
            f"QTableWidget::item:alternate {{ background-color: {alt_bg}; }}"
            f"QTableWidget::item:selected {{ background-color: {sel_bg}; color: {texto}; }}"
            f"QHeaderView::section {{ background-color: {header_bg}; color: {header_text}; "
            f"  font-size: 13px; font-weight: bold; padding: 6px; "
            f"  border: 1px solid {grid_color}; }}"
        )
        layout_derecha.addWidget(self.tabla_carrito)

        layout_resumen = QVBoxLayout()
        self.label_subtotal = QLabel(f"Subtotal: {formatear_moneda(0)}")
        self.label_total = QLabel(f"Total: {MONEDA}0")
        self.label_subtotal.setStyleSheet(f"font-size: 13px; color: {texto};")
        self.label_total.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {'#86efac' if self.modo_oscuro else '#166534'};"
        )
        layout_resumen.addWidget(self.label_subtotal)
        layout_resumen.addWidget(self.label_total)
        layout_derecha.addLayout(layout_resumen)

        layout_botones_pos = QHBoxLayout()
        layout_botones_pos.setSpacing(10)

        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.setMinimumHeight(58)
        btn_eliminar.setMinimumWidth(150)
        btn_eliminar.setStyleSheet("font-size: 15px; font-weight: 700;")
        btn_eliminar.clicked.connect(self.eliminar_del_carrito_gui)
        layout_botones_pos.addWidget(btn_eliminar)

        btn_vaciar = QPushButton("🗑️ Vaciar")
        btn_vaciar.setMinimumHeight(58)
        btn_vaciar.setMinimumWidth(150)
        btn_vaciar.setStyleSheet("font-size: 15px; font-weight: 700;")
        btn_vaciar.clicked.connect(self.vaciar_carrito_gui)
        layout_botones_pos.addWidget(btn_vaciar)

        btn_pagar = QPushButton("💳 Procesar Pago")
        btn_pagar.setMinimumHeight(62)
        btn_pagar.setMinimumWidth(220)
        btn_pagar.setStyleSheet(
            "background-color: #166534; color: white; font-weight: bold; font-size: 15px;"
            "QPushButton:focus { border: 3px solid #f59e0b; }"
        )
        btn_pagar.clicked.connect(self.procesar_pago_gui)
        layout_botones_pos.addWidget(btn_pagar)

        layout_derecha.addLayout(layout_botones_pos)

        layout_contenido.addLayout(layout_derecha, 2)
        layout_principal.addLayout(layout_contenido)

        widget.setLayout(layout_principal)
        return widget

    def _enfocar_gtin_pos(self):
        """Enfoca automáticamente el campo GTIN del POS si existe."""
        if hasattr(self, "entrada_gtin_pos") and self.entrada_gtin_pos is not None:
            self.entrada_gtin_pos.setFocus()
            self.entrada_gtin_pos.selectAll()

    def _enfocar_gtin_pos_si_corresponde(self, index):
        """Enfoca el campo GTIN del POS cuando la pestaña activa es la de POS."""
        if self.pestanas.widget(index) is self.pestana_pos:
            QTimer.singleShot(0, self._enfocar_gtin_pos)
    
    def crear_pestaña_reportes(self) -> QWidget:
        """Crea la pestaña de reportes con integración a Streamlit"""
        widget = QWidget()
        if self.modo_oscuro:
            fondo, superficie, texto, borde = "#121722", "#1c2434", "#f3f6fb", "#40506a"
        else:
            fondo, superficie, texto, borde = "#f7f7f7", "#ffffff", "#202938", "#d0d0d0"
        widget.setStyleSheet(
            f"QWidget {{ background-color: {fondo}; color: {texto}; }}"
            f"QLabel {{ font-size: 15px; color: {texto}; }}"
            "QPushButton { padding: 10px 12px; font-size: 13px; min-height: 38px; border-radius: 6px; }"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        encabezado = QLabel("📊 Reportes y Analítica del Sistema")
        encabezado.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {texto};")
        layout.addWidget(encabezado)

        # Botón destacado para Dashboard de Streamlit
        btn_streamlit = QPushButton("🚀 Abrir Dashboard Gráfico en Streamlit (Múltiples Gráficas)")
        btn_streamlit.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; font-size: 14px; min-height: 46px; border: none; border-radius: 8px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:pressed { background-color: #1e40af; }"
        )
        btn_streamlit.clicked.connect(self.abrir_dashboard_streamlit)
        layout.addWidget(btn_streamlit)

        contenedor_botones = QWidget()
        contenedor_botones.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 8px; padding: 8px;"
        )
        botones_layout = QVBoxLayout(contenedor_botones)
        botones_layout.setSpacing(8)

        btn_reporte_inventario = QPushButton("📦 Resumen Rápido de Inventario")
        btn_reporte_inventario.clicked.connect(self.generar_reporte_inventario)
        botones_layout.addWidget(btn_reporte_inventario)

        btn_reporte_ventas = QPushButton("💳 Resumen Rápido de Ventas")
        btn_reporte_ventas.clicked.connect(self.generar_reporte_ventas)
        botones_layout.addWidget(btn_reporte_ventas)

        btn_logs = QPushButton("📝 Ver Logs del Sistema")
        btn_logs.clicked.connect(self.abrir_logs_desde_reportes)
        botones_layout.addWidget(btn_logs)

        layout.addWidget(contenedor_botones)

        self.texto_reporte = QLabel("Selecciona un reporte rápido o abre el Dashboard en Streamlit para gráficos interactivos.")
        self.texto_reporte.setAccessibleName("Resultado del reporte")
        self.texto_reporte.setAccessibleDescription("El contenido se actualiza al generar un reporte.")
        self.texto_reporte.setWordWrap(True)
        self.texto_reporte.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 8px; padding: 12px; color: {texto}; font-size: 13px;"
        )
        self.texto_reporte.setMinimumHeight(180)
        layout.addWidget(self.texto_reporte)

        widget.setLayout(layout)
        return widget

    def crear_pestaña_proveedores(self) -> QWidget:
        """Crea el catálogo de proveedores y sus relaciones con productos."""
        widget = QWidget()
        widget.setStyleSheet(_estilo_formularios(self.modo_oscuro))
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        encabezado = QHBoxLayout()
        descripcion = QLabel("Administra los contactos y los productos que suministra cada proveedor.")
        descripcion.setWordWrap(True)
        descripcion.setStyleSheet(
            f"color: {'#a9b8cc' if self.modo_oscuro else '#667085'}; font-size: 14px;"
        )
        encabezado.addWidget(descripcion, 1)

        self.tabla_proveedores = QTableWidget()
        self.tabla_proveedores.setColumnCount(5)
        self.tabla_proveedores.setHorizontalHeaderLabels(
            ["Proveedor", "Contacto", "Teléfono", "Correo", "Productos"]
        )
        self.tabla_proveedores.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_proveedores.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_proveedores.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_proveedores.setAlternatingRowColors(True)
        self.tabla_proveedores.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_proveedores.verticalHeader().setVisible(False)
        self.tabla_proveedores.setMinimumHeight(300)
        layout.addLayout(encabezado)
        layout.addWidget(self.tabla_proveedores, 1)

        acciones = QHBoxLayout()
        acciones.setSpacing(8)
        btn_nuevo = QPushButton("＋ Nuevo proveedor")
        btn_nuevo.setDefault(True)
        btn_nuevo.clicked.connect(self.crear_proveedor)
        acciones.addWidget(btn_nuevo)

        btn_editar = QPushButton("Editar")
        btn_editar.clicked.connect(self.editar_proveedor)
        acciones.addWidget(btn_editar)

        btn_asignar = QPushButton("Asignar productos")
        btn_asignar.clicked.connect(self.asignar_productos_proveedor)
        acciones.addWidget(btn_asignar)

        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.clicked.connect(self.eliminar_proveedor)
        acciones.addWidget(btn_eliminar)

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.clicked.connect(self.cargar_proveedores)
        acciones.addWidget(btn_actualizar)
        layout.addLayout(acciones)

        self.cargar_proveedores()
        return widget

    def cargar_proveedores(self):
        """Actualiza la tabla del catálogo de proveedores."""
        if not hasattr(self, "tabla_proveedores"):
            return
        try:
            proveedores = (
                self.db.query(Proveedor)
                .order_by(Proveedor.nombre)
                .all()
            )
            self.tabla_proveedores.setRowCount(0)
            for proveedor in proveedores:
                fila = self.tabla_proveedores.rowCount()
                self.tabla_proveedores.insertRow(fila)
                datos = (
                    proveedor.nombre,
                    proveedor.contacto or "—",
                    proveedor.telefono or "—",
                    proveedor.email or "—",
                    str(len(proveedor.productos)),
                )
                for columna, valor in enumerate(datos):
                    item = QTableWidgetItem(valor)
                    if columna == 0:
                        item.setData(Qt.UserRole, proveedor.id)
                    self.tabla_proveedores.setItem(fila, columna, item)
        except Exception as error:
            logger.exception("No se pudo cargar el catálogo de proveedores")
            QMessageBox.warning(
                self, "Error", f"No se pudo cargar el catálogo de proveedores: {error}"
            )

    def _proveedor_seleccionado(self):
        """Devuelve el proveedor seleccionado o informa que hace falta elegir uno."""
        fila = self.tabla_proveedores.currentRow()
        item = self.tabla_proveedores.item(fila, 0) if fila >= 0 else None
        if item is None:
            QMessageBox.information(
                self, "Selecciona un proveedor", "Selecciona un proveedor de la tabla."
            )
            return None
        proveedor = self.db.get(Proveedor, item.data(Qt.UserRole))
        if proveedor is None:
            QMessageBox.warning(self, "Proveedor no encontrado", "Actualiza la lista e inténtalo de nuevo.")
        return proveedor

    def crear_proveedor(self):
        """Registra un proveedor nuevo."""
        dialogo = DialogoProveedor(parent=self)
        if dialogo.exec_() != QDialog.Accepted:
            return
        proveedor = Proveedor(**dialogo.obtener_datos())
        try:
            self.db.add(proveedor)
            self.db.commit()
            self.cargar_proveedores()
            self.statusBar().showMessage("Proveedor registrado correctamente", 5000)
        except Exception as error:
            self.db.rollback()
            logger.exception("No se pudo registrar el proveedor")
            QMessageBox.warning(self, "Error al guardar", f"No se pudo registrar el proveedor: {error}")

    def editar_proveedor(self):
        """Edita los datos de contacto del proveedor seleccionado."""
        proveedor = self._proveedor_seleccionado()
        if proveedor is None:
            return
        dialogo = DialogoProveedor(proveedor=proveedor, parent=self)
        if dialogo.exec_() != QDialog.Accepted:
            return
        for campo, valor in dialogo.obtener_datos().items():
            setattr(proveedor, campo, valor)
        try:
            self.db.commit()
            self.cargar_proveedores()
            self.statusBar().showMessage("Proveedor actualizado correctamente", 5000)
        except Exception as error:
            self.db.rollback()
            logger.exception("No se pudo actualizar el proveedor")
            QMessageBox.warning(self, "Error al guardar", f"No se pudo actualizar el proveedor: {error}")

    def asignar_productos_proveedor(self):
        """Asigna al proveedor seleccionado los productos marcados."""
        proveedor = self._proveedor_seleccionado()
        if proveedor is None:
            return
        productos = self.db.query(Producto).order_by(Producto.nombre).all()
        dialogo = DialogoAsignarProductos(proveedor, productos, self)
        if dialogo.exec_() != QDialog.Accepted:
            return
        ids_seleccionados = set(dialogo.productos_seleccionados())
        proveedor.productos = [producto for producto in productos if producto.id in ids_seleccionados]
        try:
            self.db.commit()
            self.cargar_proveedores()
            self.statusBar().showMessage("Productos del proveedor actualizados", 5000)
        except Exception as error:
            self.db.rollback()
            logger.exception("No se pudieron actualizar los productos del proveedor")
            QMessageBox.warning(
                self, "Error al guardar", f"No se pudieron actualizar los productos: {error}"
            )

    def eliminar_proveedor(self):
        """Elimina el proveedor seleccionado sin afectar los productos del inventario."""
        proveedor = self._proveedor_seleccionado()
        if proveedor is None:
            return
        respuesta = QMessageBox.question(
            self,
            "Eliminar proveedor",
            f"¿Deseas eliminar a «{proveedor.nombre}»? Sus productos permanecerán en el inventario.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        try:
            self.db.delete(proveedor)
            self.db.commit()
            self.cargar_proveedores()
            self.statusBar().showMessage("Proveedor eliminado", 5000)
        except Exception as error:
            self.db.rollback()
            logger.exception("No se pudo eliminar el proveedor")
            QMessageBox.warning(self, "Error al eliminar", f"No se pudo eliminar el proveedor: {error}")

    def eventFilter(self, obj, event):
        """Muestra Logs al hacer Shift+clic sobre la pestaña de Reportes."""
        if (
            obj is self.pestanas.tabBar()
            and event.type() == QEvent.MouseButtonPress
            and event.button() == Qt.LeftButton
            and bool(event.modifiers() & Qt.ShiftModifier)
        ):
            index = self.pestanas.tabBar().tabAt(event.pos())
            if index == self.pestanas.indexOf(self.pestana_reportes):
                self._mostrar_logs()
                return True
        return super().eventFilter(obj, event)

    def _mostrar_logs(self):
        """Hace visible la pestaña de Logs y la activa."""
        if not hasattr(self, "pestanas") or not hasattr(self, "pestana_logs"):
            return
        self.pestanas.tabBar().setTabVisible(self.pestanas.indexOf(self.pestana_logs), True)
        self._nav_buttons[self.pestanas.indexOf(self.pestana_logs)].show()
        self.pestanas.setCurrentWidget(self.pestana_logs)

    def abrir_logs_desde_reportes(self):
        """Abre la vista de logs cuando se solicita desde Reportes."""
        self._mostrar_logs()
    
    def crear_pestaña_logs(self) -> QWidget:
        """Crea la pestaña de logs de la aplicación"""
        widget = QWidget()
        if self.modo_oscuro:
            fondo, superficie, texto, borde = "#121722", "#1c2434", "#f3f6fb", "#40506a"
        else:
            fondo, superficie, texto, borde = "#f7f7f7", "#ffffff", "#202938", "#d0d0d0"
        widget.setStyleSheet(
            f"QWidget {{ background-color: {fondo}; color: {texto}; }}"
            f"QLabel {{ font-size: 13px; color: {texto}; }}"
            f"QPlainTextEdit {{ font-size: 12px; padding: 8px; background-color: {superficie}; color: {texto}; border: 1px solid {borde}; }}"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        encabezado = QLabel("📘 Registro de actividad")
        encabezado.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {texto};")
        layout.addWidget(encabezado)

        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_widget.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 8px; padding: 8px; color: {texto};"
        )
        self.log_widget.setMinimumHeight(360)
        layout.addWidget(self.log_widget)

        widget.setLayout(layout)
        return widget

    def configurar_logger_grafico(self):
        """Configura el logging para que los mensajes aparezcan en la GUI."""
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        root_logger.addHandler(QtLogHandler(self.log_widget))
        root_logger.setLevel(logging.INFO)

    def buscar_producto(self):
        """Busca productos por nombre, GTIN, laboratorio o descripción"""
        termino = self.entrada_gtin.text().strip()
        if not termino:
            QMessageBox.warning(self, "Advertencia", "Ingresa un GTIN o término de búsqueda")
            return
        
        productos = self.inventario.buscar_productos(termino)
        
        if productos:
            self.tabla_inventario.setRowCount(0)
            for producto in productos:
                for presentacion in producto.presentaciones:
                    fila = self.tabla_inventario.rowCount()
                    self.tabla_inventario.insertRow(fila)

                    item_gtin = QTableWidgetItem(producto.gtin)
                    item_gtin.setData(Qt.UserRole, presentacion.id)
                    self.tabla_inventario.setItem(fila, 0, item_gtin)
                    self.tabla_inventario.setItem(fila, 1, QTableWidgetItem(producto.nombre))
                    self.tabla_inventario.setItem(fila, 2, QTableWidgetItem(str(presentacion.stock_actual)))
                    self.tabla_inventario.setItem(fila, 3, QTableWidgetItem(formatear_moneda(presentacion.precio_venta)))
                    self.tabla_inventario.setItem(
                        fila, 4, QTableWidgetItem(self._nombres_proveedores(producto))
                    )
        else:
            QMessageBox.information(self, "Información", f"No se encontraron productos para: {termino}")

    @staticmethod
    def _nombres_proveedores(producto):
        """Devuelve los proveedores asociados al producto para la tabla."""
        nombres = sorted(
            proveedor.nombre
            for proveedor in getattr(producto, "proveedores", [])
            if proveedor.nombre
        )
        return ", ".join(nombres) if nombres else "Sin proveedor"

    def exportar_catalogo_gui(self):
        """Exporta el catálogo actual a un archivo CSV seleccionado por el usuario"""
        from PyQt5.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Catálogo de Inventario",
            "catalogo_inventario.csv",
            "Archivos CSV (*.csv)"
        )
        if ruta:
            if self.inventario.exportar_catalogo_csv(ruta):
                QMessageBox.information(self, "Éxito", f"Catálogo exportado exitosamente a:\n{ruta}")
            else:
                QMessageBox.critical(self, "Error", "No se pudo exportar el catálogo.")

    def mostrar_resumen_financiero_gui(self):
        """Muestra una ventana modal con el resumen de valorización y rentabilidad del inventario"""
        datos = self.inventario.calcular_valor_inventario()
        msg = (
            f"💰 RESUMEN FINANCIERO DEL INVENTARIO\n\n"
            f"• Inversión Total (Costo): {formatear_moneda(datos['valor_costo_total'])}\n"
            f"• Venta Potencial Total: {formatear_moneda(datos['valor_venta_potencial'])}\n"
            f"• Ganancia Proyectada: {formatear_moneda(datos['ganancia_proyectada'])}\n"
            f"• Margen Promedio: {datos['margen_promedio_porcentaje']}%\n"
            f"• Total Unidades en Stock: {datos['total_unidades']:,}\n"
            f"• Presentaciones Registradas: {datos['total_presentaciones']}"
        )
        QMessageBox.information(self, "Valorización del Inventario", msg)

    def ver_todos_productos(self):
        """Carga todos los productos en la tabla de inventario"""
        productos = self.inventario.obtener_productos()
        self.tabla_inventario.setRowCount(0)

        if not productos:
            QMessageBox.information(self, "Información", "No hay productos registrados.")
            return

        for producto in productos:
            for presentacion in producto.presentaciones:
                fila = self.tabla_inventario.rowCount()
                self.tabla_inventario.insertRow(fila)
                item_gtin = QTableWidgetItem(producto.gtin)
                item_gtin.setData(Qt.UserRole, presentacion.id)
                self.tabla_inventario.setItem(fila, 0, item_gtin)
                self.tabla_inventario.setItem(fila, 1, QTableWidgetItem(producto.nombre))
                self.tabla_inventario.setItem(fila, 2, QTableWidgetItem(str(presentacion.stock_actual)))
                self.tabla_inventario.setItem(fila, 3, QTableWidgetItem(formatear_moneda(presentacion.precio_venta)))
                self.tabla_inventario.setItem(
                    fila, 4, QTableWidgetItem(self._nombres_proveedores(producto))
                )

    def obtener_producto_y_presentacion_desde_fila(self, fila=None):
        """Obtiene el producto y la presentación asociados a una fila de la tabla."""
        if fila is None:
            fila = self.tabla_inventario.currentRow()

        if fila < 0:
            return None, None

        item_gtin = self.tabla_inventario.item(fila, 0)
        if item_gtin is None:
            return None, None

        gtin = item_gtin.text().strip()
        producto = self.inventario.obtener_producto_por_gtin(gtin)
        if not producto:
            return None, None

        presentacion_id = item_gtin.data(Qt.UserRole)
        presentacion = next(
            (p for p in producto.presentaciones if p.id == presentacion_id),
            None,
        )
        if presentacion is None and presentacion_id is None and producto.presentaciones:
            presentacion = producto.presentaciones[0]
        return producto, presentacion

    def mostrar_menu_contextual_inventario(self, posicion):
        """Muestra un menú contextual al hacer clic derecho sobre un producto del inventario."""
        fila = self.tabla_inventario.rowAt(posicion.y())
        if fila < 0:
            return

        self.tabla_inventario.setCurrentCell(fila, 0)
        producto, presentacion = self.obtener_producto_y_presentacion_desde_fila(fila)
        if producto is None or presentacion is None:
            return

        shift_presionado = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)

        if shift_presionado:
            menu = QMenu(self.tabla_inventario)
            accion_eliminar = QAction("🗑️ Eliminar producto", self.tabla_inventario)
            accion_eliminar.triggered.connect(lambda: self.eliminar_producto_contextual(producto, presentacion))
            menu.addAction(accion_eliminar)
            menu.exec_(self.tabla_inventario.viewport().mapToGlobal(posicion))
            return

        menu = QMenu(self.tabla_inventario)
        accion_entrada = QAction("➕ Registrar entrada", self.tabla_inventario)
        accion_entrada.triggered.connect(lambda: self.registrar_movimiento_contextual("entrada", producto, presentacion))
        menu.addAction(accion_entrada)

        accion_salida = QAction("➖ Registrar salida", self.tabla_inventario)
        accion_salida.triggered.connect(lambda: self.registrar_movimiento_contextual("salida", producto, presentacion))
        menu.addAction(accion_salida)

        accion_editar = QAction("✏️ Editar producto", self.tabla_inventario)
        accion_editar.triggered.connect(
            lambda: self.editar_producto_contextual(producto, presentacion)
        )
        menu.addAction(accion_editar)

        accion_detalle = QAction("ℹ️ Ver detalles", self.tabla_inventario)
        accion_detalle.triggered.connect(lambda: self.mostrar_detalle_producto(producto, presentacion))
        menu.addAction(accion_detalle)

        menu.exec_(self.tabla_inventario.viewport().mapToGlobal(posicion))

    def editar_producto_contextual(self, producto, presentacion):
        """Edita los datos del producto y el precio de la presentación seleccionada."""
        dialogo = DialogoEditarProducto(producto, presentacion, self)
        if dialogo.exec_() != QDialog.Accepted:
            return

        datos = dialogo.obtener_datos()
        actualizado = self.inventario.actualizar_producto(
            producto_id=producto.id,
            gtin=datos["gtin"],
            nombre=datos["nombre"],
            laboratorio=datos["laboratorio"],
            descripcion=datos["descripcion"],
            presentacion_id=presentacion.id,
            precio_venta=datos["precio_venta"],
        )
        if not actualizado:
            QMessageBox.warning(
                self,
                "Error",
                "No se pudo actualizar el producto. Verifica que el GTIN no esté en uso.",
            )
            return

        QMessageBox.information(self, "Éxito", "Producto actualizado correctamente.")
        self.ver_todos_productos()

    def registrar_movimiento_contextual(self, tipo, producto, presentacion):
        """Registra un movimiento de stock usando la selección del menú contextual."""
        if tipo not in {"entrada", "salida"}:
            return

        if tipo == "salida" and presentacion.stock_actual <= 0:
            QMessageBox.warning(self, "Stock insuficiente", "No hay stock disponible para registrar una salida.")
            return

        cantidad, ok = QInputDialog.getInt(self, "Cantidad", f"Cantidad a {tipo}:", 1, 1, 100000)
        if not ok:
            return

        if tipo == "salida" and cantidad > presentacion.stock_actual:
            QMessageBox.warning(self, "Stock insuficiente", f"Stock disponible: {presentacion.stock_actual}")
            return

        razon, _ = QInputDialog.getText(self, "Razón", "Razón del movimiento:")
        referencia, _ = QInputDialog.getText(self, "Referencia", "Referencia (opcional):")

        movimiento = self.inventario.registrar_movimiento(
            producto_id=producto.id,
            presentacion_id=presentacion.id,
            tipo=tipo,
            cantidad=cantidad,
            razon=razon or "Sin razón",
            referencia=referencia or None
        )

        if movimiento:
            QMessageBox.information(self, "Éxito", f"{tipo.title()} registrada correctamente")
            self.ver_todos_productos()
        else:
            QMessageBox.warning(self, "Error", f"No se pudo registrar la {tipo}")

    def mostrar_detalle_producto(self, producto, presentacion):
        """Muestra un detalle del producto seleccionado desde el menú contextual."""
        mensaje = (
            f"GTIN: {producto.gtin}\n"
            f"Nombre: {producto.nombre}\n"
            f"Presentación: {presentacion.tipo.value}\n"
            f"Stock actual: {presentacion.stock_actual}\n"
            f"Precio de venta: {MONEDA}{presentacion.precio_venta:.0f}"
        )
        QMessageBox.information(self, "Detalle del producto", mensaje)

    def eliminar_producto_contextual(self, producto, presentacion):
        """Elimina un producto desde el menú contextual, con confirmación o sin ella según Shift."""
        shift_presionado = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)

        if not shift_presionado:
            respuesta = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Deseas eliminar el producto '{producto.nombre}' y todas sus presentaciones?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if respuesta != QMessageBox.Yes:
                return

        if self.inventario.eliminar_producto(producto.id):
            QMessageBox.information(self, "Éxito", "Producto eliminado correctamente")
            self.ver_todos_productos()
        else:
            QMessageBox.warning(self, "Error", "No se pudo eliminar el producto")

    def abrir_dialogo_nuevo_producto(self):
        """Abre el diálogo para crear un nuevo producto"""
        dialogo = DialogoNuevoProducto(self)
        if dialogo.exec_() == QDialog.Accepted:
            datos = dialogo.obtener_datos()
            producto = self.inventario.registrar_producto(
                gtin=datos['gtin'],
                nombre=datos['nombre'],
                laboratorio=None,
                descripcion=datos['descripcion']
            )

            if not producto:
                QMessageBox.warning(self, "Error", "No se pudo crear el producto. Verifica los datos e inténtalo de nuevo.")
                return

            presentacion = self.inventario.agregar_presentacion(
                producto_id=producto.id,
                tipo_presentacion="unidad",
                cantidad=1,
                precio_unitario=datos['precio'],
                precio_venta=datos['precio'],
                stock_inicial=datos['stock_inicial']
            )

            if not presentacion:
                QMessageBox.warning(self, "Error", "El producto se creó, pero no se pudo agregar la presentación.")
                return

            QMessageBox.information(self, "Éxito", "Producto creado correctamente.")
            self.entrada_gtin.setText(producto.gtin)
            self.buscar_producto()
    
    def registrar_entrada(self):
        """Registra una entrada de stock desde la GUI"""
        gtin, ok = QInputDialog.getText(self, "Entrada de Stock", "Ingresa GTIN del producto:")
        if not ok or not gtin.strip():
            return
        producto = self.inventario.obtener_producto_por_gtin(gtin.strip())
        if not producto:
            QMessageBox.warning(self, "No encontrado", f"Producto no encontrado: {gtin}")
            return

        presentaciones = producto.presentaciones
        if not presentaciones:
            QMessageBox.information(self, "Sin presentaciones", "El producto no tiene presentaciones.")
            return

        presentacion = presentaciones[0]
        cantidad, ok = QInputDialog.getInt(self, "Cantidad", "Cantidad a ingresar:", 1, 1, 100000)
        if not ok:
            return

        movimiento = self.inventario.registrar_movimiento(
            producto_id=producto.id,
            presentacion_id=presentacion.id,
            tipo="entrada",
            cantidad=cantidad,
            razon="Ingreso directo",
            referencia=""
        )

        if movimiento:
            QMessageBox.information(self, "Éxito", f"Entrada registrada: {cantidad} unidades")
            self.ver_todos_productos()
        else:
            QMessageBox.warning(self, "Error", "No se pudo registrar la entrada")
    
    def registrar_salida(self):
        """Registra una salida de stock desde la GUI"""
        gtin, ok = QInputDialog.getText(self, "Salida de Stock", "Ingresa GTIN del producto:")
        if not ok or not gtin.strip():
            return
        producto = self.inventario.obtener_producto_por_gtin(gtin.strip())
        if not producto:
            QMessageBox.warning(self, "No encontrado", f"Producto no encontrado: {gtin}")
            return

        presentaciones = producto.presentaciones
        if not presentaciones:
            QMessageBox.information(self, "Sin presentaciones", "El producto no tiene presentaciones.")
            return

        presentacion = presentaciones[0]
        cantidad, ok = QInputDialog.getInt(self, "Cantidad", "Cantidad a retirar:", 1, 1, 100000)
        if not ok:
            return

        if cantidad > presentacion.stock_actual:
            QMessageBox.warning(self, "Stock insuficiente", f"Stock disponible: {presentacion.stock_actual}")
            return

        movimiento = self.inventario.registrar_movimiento(
            producto_id=producto.id,
            presentacion_id=presentacion.id,
            tipo="salida",
            cantidad=cantidad,
            razon="Salida directa"
        )

        if movimiento:
            QMessageBox.information(self, "Éxito", f"Salida registrada: {cantidad} unidades")
            self.ver_todos_productos()
        else:
            QMessageBox.warning(self, "Error", "No se pudo registrar la salida")
    
    def agregar_a_carrito_gui(self):
        """Agrega un producto al carrito desde GUI"""
        gtin = self.entrada_gtin_pos.text().strip()
        if not gtin:
            QMessageBox.warning(self, "Validación", "Ingresa un GTIN")
            return

        producto = self.inventario.obtener_producto_por_gtin(gtin)
        if not producto:
            QMessageBox.warning(self, "No encontrado", f"Producto no encontrado: {gtin}")
            return

        presentaciones = producto.presentaciones
        if not presentaciones:
            QMessageBox.information(self, "Sin presentaciones", "El producto no tiene presentaciones")
            return

        presentacion = next((p for p in presentaciones if p.stock_actual > 0), presentaciones[0])
        if presentacion.stock_actual < 1:
            QMessageBox.warning(self, "Stock insuficiente", f"Stock disponible: {presentacion.stock_actual}")
            return

        cantidad = 1

        agregado = self.pos.carrito.agregar_item(
            producto_id=producto.id,
            presentacion_id=presentacion.id,
            cantidad=cantidad,
            precio_unitario=presentacion.precio_venta,
            producto_nombre=producto.nombre,
            presentacion_nombre=presentacion.tipo.value
        )

        if agregado:
            self._registrar_repeticion_carrito(producto.id, presentacion.id, producto.nombre)
            self.actualizar_tabla_carrito()
            self.actualizar_resumen_carrito()
            self.entrada_gtin_pos.clear()
            self.entrada_gtin_pos.setFocus()
        else:
            QMessageBox.warning(self, "Error", "No se pudo agregar al carrito")
    
    def _registrar_repeticion_carrito(self, producto_id, presentacion_id, producto_nombre):
        """Controla repeticiones del mismo producto para mostrar una alerta de compra masiva."""
        clave = (producto_id, presentacion_id)
        if self._ultimo_producto_carrito_key == clave:
            self._repeticiones_mismo_producto += 1
        else:
            self._ultimo_producto_carrito_key = clave
            self._repeticiones_mismo_producto = 1

        if self._repeticiones_mismo_producto == 10:
            QMessageBox.information(
                self,
                "Compra masiva detectada",
                f"Compra masiva detectada\nIngrese el total de {producto_nombre} a vender"
            )
            total, ok = QInputDialog.getInt(
                self,
                "Compra masiva detectada",
                f"Ingrese el total de {producto_nombre} a vender:",
                1,
                1,
                1000000,
            )
            if ok:
                for item in self.pos.carrito.items:
                    if item["presentacion_id"] == presentacion_id:
                        item["cantidad"] = total
                        item["subtotal"] = total * item["precio_unitario"]
                        break
                self.pos.carrito._recalcular()
                self.actualizar_tabla_carrito()
                self.actualizar_resumen_carrito()
                self.statusBar().showMessage(f"Total de {producto_nombre} actualizado a {total}")

    def eliminar_del_carrito_gui(self):
        """Elimina un producto del carrito"""
        sel = self.tabla_carrito.currentRow()
        if sel < 0:
            QMessageBox.information(self, "Información", "Selecciona un item en el carrito para eliminar")
            return

        item_producto = self.tabla_carrito.item(sel, 0)
        presentacion_id = item_producto.data(Qt.UserRole) if item_producto is not None else None
        if presentacion_id is None:
            QMessageBox.warning(self, "Error", "No se pudo identificar la presentación seleccionada")
            return

        eliminado = self.pos.carrito.eliminar_item(presentacion_id)
        if eliminado:
            QMessageBox.information(self, "Éxito", "Item eliminado del carrito")
            self.actualizar_tabla_carrito()
            self.actualizar_resumen_carrito()
        else:
            QMessageBox.warning(self, "Error", "No se pudo eliminar el item")
    
    def vaciar_carrito_gui(self):
        """Vacía el carrito"""
        self.pos.carrito.vaciar_carrito()
        self.tabla_carrito.setRowCount(0)
        self.actualizar_resumen_carrito()
    
    def procesar_pago_gui(self):
        """Procesa el pago desde la GUI"""
        resumen = self.pos.carrito.obtener_resumen()
        if resumen['cantidad_items'] == 0:
            QMessageBox.information(self, "Información", "El carrito está vacío")
            return

        dialogo = QDialog(self)
        dialogo.setWindowTitle("Método de pago")
        dialogo.setModal(True)
        dialogo.setWindowFlags(dialogo.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialogo.metodo_seleccionado = None

        def seleccionar_metodo(metodo):
            dialogo.metodo_seleccionado = metodo
            dialogo.accept()

        dialogo.keyPressEvent = lambda event: (
            seleccionar_metodo("efectivo") if event.key() == Qt.Key_1 else (
                seleccionar_metodo("transferencia") if event.key() == Qt.Key_2 else QDialog.keyPressEvent(dialogo, event)
            )
        )

        layout = QVBoxLayout(dialogo)
        label = QLabel("Selecciona una opción:")
        layout.addWidget(label)

        botones_layout = QHBoxLayout()
        for metodo, texto in [("efectivo", "[1] Efectivo"), ("transferencia", "[2] Transferencia")]:
            boton = QPushButton(texto)
            boton.clicked.connect(lambda checked=False, m=metodo: seleccionar_metodo(m))
            botones_layout.addWidget(boton)

        layout.addLayout(botones_layout)
        dialogo.resize(320, 120)

        if dialogo.exec_() != QDialog.Accepted:
            return

        metodo = dialogo.metodo_seleccionado
        if metodo is None:
            QMessageBox.warning(self, "Error", "Selecciona una opción válida: 1 o 2")
            return

        efectivo_recibido = None
        vuelto = None
        if metodo == "efectivo":
            total = round(resumen["total"])
            efectivo_recibido, ok = QInputDialog.getInt(
                self,
                "Pago en efectivo",
                f"Total a pagar: {MONEDA}{total}\nEfectivo recibido:",
                total,
                total,
                2_147_483_647,
            )
            if not ok:
                return
            try:
                vuelto = calcular_vuelto(total, efectivo_recibido)
            except ValueError as error:
                QMessageBox.warning(self, "Pago insuficiente", str(error))
                return

        usuario = "Sistema"

        numero_ticket = self.pos.generar_numero_ticket()
        venta = self.pos.crear_venta(
            numero_ticket=numero_ticket,
            metodo_pago=metodo,
            usuario=usuario,
            notas=None
        )

        if venta:
            mensaje = (
                f"Ticket: {venta.numero_ticket}\n"
                f"Total: {formatear_moneda(venta.total)}"
            )
            if metodo == "efectivo":
                mensaje += (
                    f"\nEfectivo recibido: {formatear_moneda(efectivo_recibido)}"
                    f"\nVuelto: {formatear_moneda(vuelto)}"
                )
            QMessageBox.information(self, "Venta completada", mensaje)
            self.actualizar_tabla_carrito()
            self.actualizar_resumen_carrito()
            self.ver_todos_productos()
        else:
            QMessageBox.warning(self, "Error", "No se pudo procesar la venta")
    
    def actualizar_resumen_carrito(self):
        """Actualiza el resumen del carrito"""
        resumen = self.pos.carrito.obtener_resumen()
        self.label_subtotal.setText(f"Subtotal: {formatear_moneda(resumen['subtotal'])}")
        self.label_total.setText(f"Total: {formatear_moneda(resumen['total'])}")

    def actualizar_tabla_carrito(self):
        """Actualiza la tabla de carrito con los items actuales"""
        items = self.pos.carrito.obtener_items()
        self.tabla_carrito.setRowCount(0)
        for it in items:
            fila = self.tabla_carrito.rowCount()
            self.tabla_carrito.insertRow(fila)
            # Columna 0: Producto (guardar presentacion_id en UserRole)
            item_prod = QTableWidgetItem(it.get('producto_nombre', str(it['producto_id'])))
            item_prod.setData(Qt.UserRole, it['presentacion_id'])
            self.tabla_carrito.setItem(fila, 0, item_prod)
            # Columna 1: Cantidad
            self.tabla_carrito.setItem(fila, 1, QTableWidgetItem(str(it['cantidad'])))
            # Columna 2: Precio
            self.tabla_carrito.setItem(fila, 2, QTableWidgetItem(formatear_moneda(it['precio_unitario'])))
            # Columna 3: Subtotal
            self.tabla_carrito.setItem(fila, 3, QTableWidgetItem(formatear_moneda(it['subtotal'])))
    
    def generar_reporte_inventario(self):
        """Genera reporte de inventario"""
        reporte = self.inventario.reporte_general()
        texto = f"""
        Reporte de Inventario
        Fecha: {reporte['fecha']}
        
        Total de Productos: {reporte['total_productos']}
        Stock Total: {reporte['total_stock']} unidades
        Valor Inventario: {formatear_moneda(reporte['valor_inventario'])}
        Productos sin Stock: {reporte['productos_sin_stock']}
        Productos en Alerta: {reporte['productos_alerta']}
        """
        self.texto_reporte.setText(texto)
    
    def generar_reporte_ventas(self):
        """Genera reporte de ventas"""
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        reporte = self.pos.reporte_ventas_diario(fecha_hoy)
        texto = f"""
        Reporte de Ventas del {fecha_hoy}

        Cantidad de Ventas: {reporte['cantidad_ventas']}
        Total de Ventas: {formatear_moneda(reporte['total_ventas'])}
        Promedio por Venta: {formatear_moneda(reporte['promedio_venta'])}

        Métodos de Pago:
        {chr(10).join([f"  {k}: {formatear_moneda(v)}" for k, v in reporte['metodos_pago'].items()])}
        """
        self.texto_reporte.setText(texto)

    def abrir_dashboard_streamlit(self):
        """Inicia el servidor Streamlit en segundo plano y abre el navegador web."""
        url = "http://localhost:8501"
        try:
            import urllib.request
            try:
                urllib.request.urlopen(url, timeout=0.6)
                webbrowser.open(url)
                self.statusBar().showMessage("✅ Dashboard de Streamlit abierto en el navegador")
                return
            except Exception:
                pass

            script_path = Path(__file__).resolve().parent.parent / "reporting" / "streamlit_reports.py"
            if not script_path.exists():
                QMessageBox.warning(self, "Error", f"No se encontró el script de reportes en: {script_path}")
                return

            cmd = [
                sys.executable, "-m", "streamlit", "run",
                str(script_path),
                "--server.headless", "true",
                "--server.port", "8501"
            ]
            self.proceso_streamlit = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.statusBar().showMessage("🚀 Iniciando servidor de reportes en Streamlit...")
            QTimer.singleShot(2000, lambda: webbrowser.open(url))
        except Exception as e:
            logger.error(f"❌ Error al iniciar Streamlit: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo iniciar el dashboard de Streamlit: {e}")


class DialogoNuevoProducto(QDialog):
    """Diálogo para crear un nuevo producto y su presentación"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Producto")
        self.setMinimumWidth(500)
        self.setStyleSheet(_estilo_formularios(bool(getattr(parent, "modo_oscuro", False))))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        titulo = QLabel("Registra un producto")
        titulo.setStyleSheet("font-size: 21px; font-weight: 800;")
        ayuda = QLabel("Completa los datos básicos. Los campos marcados con * son obligatorios.")
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet(
            f"color: {'#a9b8cc' if getattr(parent, 'modo_oscuro', False) else '#667085'};"
        )
        layout.addWidget(titulo)
        layout.addWidget(ayuda)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.campo_gtin = QLineEdit()
        self.campo_gtin.setPlaceholderText("Escanea o escribe el código de barras")
        self.campo_gtin.setAccessibleName("GTIN obligatorio")
        self.campo_nombre = QLineEdit()
        self.campo_nombre.setPlaceholderText("Ej. Jabón líquido")
        self.campo_nombre.setAccessibleName("Nombre del producto obligatorio")
        self.campo_descripcion = QPlainTextEdit()
        self.campo_descripcion.setPlaceholderText("Detalles adicionales (opcional)")
        self.campo_descripcion.setMaximumHeight(76)
        self.campo_precio = QDoubleSpinBox()
        self.campo_precio.setRange(0.0, 1000000.0)
        self.campo_precio.setDecimals(0)
        self.campo_precio.setValue(0.0)
        self.campo_precio.setPrefix(f"{MONEDA} ")
        self.campo_precio.setToolTip("Precio de venta por unidad")
        self.campo_stock_inicial = QSpinBox()
        self.campo_stock_inicial.setRange(0, 10000)
        self.campo_stock_inicial.setValue(0)
        self.campo_stock_inicial.setSuffix(" unidades")
        self.campo_stock_inicial.setToolTip("Cantidad disponible al registrar el producto")

        form.addRow("GTIN *", self.campo_gtin)
        form.addRow("Nombre *", self.campo_nombre)
        form.addRow("Descripción:", self.campo_descripcion)
        form.addRow("Precio de venta *:", self.campo_precio)
        form.addRow("Stock inicial:", self.campo_stock_inicial)

        layout.addLayout(form)

        botones = QDialogButtonBox()
        guardar = botones.addButton("Guardar producto", QDialogButtonBox.AcceptRole)
        cancelar = botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        guardar.setDefault(True)
        guardar.clicked.connect(self.validar_y_aceptar)
        cancelar.clicked.connect(self.reject)
        layout.addWidget(botones)
        self.setTabOrder(self.campo_gtin, self.campo_nombre)
        self.setTabOrder(self.campo_nombre, self.campo_descripcion)
        self.setTabOrder(self.campo_descripcion, self.campo_precio)
        self.setTabOrder(self.campo_precio, self.campo_stock_inicial)
        self.setTabOrder(self.campo_stock_inicial, guardar)
        self.campo_gtin.setFocus()

    def validar_y_aceptar(self):
        if not self.campo_gtin.text().strip():
            QMessageBox.warning(self, "Validación", "El GTIN es obligatorio.")
            return
        if not self.campo_nombre.text().strip():
            QMessageBox.warning(self, "Validación", "El nombre del producto es obligatorio.")
            return
        if self.campo_precio.value() <= 0:
            QMessageBox.warning(self, "Validación", "El precio debe ser mayor que 0.")
            return
        self.accept()

    def obtener_datos(self):
        return {
            'gtin': self.campo_gtin.text().strip(),
            'nombre': self.campo_nombre.text().strip(),
            'descripcion': self.campo_descripcion.toPlainText().strip(),
            'precio': self.campo_precio.value(),
            'stock_inicial': self.campo_stock_inicial.value(),
        }


class DialogoEditarProducto(QDialog):
    """Diálogo para editar un producto y el precio de una presentación."""

    def __init__(self, producto, presentacion, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar producto")
        self.setMinimumWidth(500)
        self.setStyleSheet(_estilo_formularios(bool(getattr(parent, "modo_oscuro", False))))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        titulo = QLabel("Actualiza el producto")
        titulo.setStyleSheet("font-size: 21px; font-weight: 800;")
        ayuda = QLabel("Modifica la información necesaria y guarda los cambios.")
        ayuda.setStyleSheet(
            f"color: {'#a9b8cc' if getattr(parent, 'modo_oscuro', False) else '#667085'};"
        )
        layout.addWidget(titulo)
        layout.addWidget(ayuda)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.campo_gtin = QLineEdit(producto.gtin or "")
        self.campo_gtin.setPlaceholderText("Código de barras")
        self.campo_nombre = QLineEdit(producto.nombre or "")
        self.campo_nombre.setPlaceholderText("Nombre del producto")
        self.campo_descripcion = QPlainTextEdit(producto.descripcion or "")
        self.campo_descripcion.setPlaceholderText("Detalles adicionales (opcional)")
        self.campo_descripcion.setMaximumHeight(76)
        self.campo_laboratorio = QLineEdit(producto.laboratorio or "")
        self.campo_laboratorio.setPlaceholderText("Laboratorio o fabricante (opcional)")
        self.campo_precio_venta = QDoubleSpinBox()
        self.campo_precio_venta.setRange(1, 1000000)
        self.campo_precio_venta.setDecimals(0)
        self.campo_precio_venta.setValue(presentacion.precio_venta)
        self.campo_precio_venta.setPrefix(f"{MONEDA} ")

        form.addRow("GTIN *", self.campo_gtin)
        form.addRow("Nombre *", self.campo_nombre)
        form.addRow("Descripción:", self.campo_descripcion)
        form.addRow("Laboratorio:", self.campo_laboratorio)
        form.addRow(f"Precio de venta ({presentacion.tipo.value}):", self.campo_precio_venta)
        layout.addLayout(form)

        botones = QDialogButtonBox()
        guardar = botones.addButton("Guardar cambios", QDialogButtonBox.AcceptRole)
        cancelar = botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        guardar.setDefault(True)
        guardar.clicked.connect(self.validar_y_aceptar)
        cancelar.clicked.connect(self.reject)
        layout.addWidget(botones)

    def validar_y_aceptar(self):
        if not self.campo_gtin.text().strip():
            QMessageBox.warning(self, "Validación", "El GTIN es obligatorio.")
            return
        if not self.campo_nombre.text().strip():
            QMessageBox.warning(self, "Validación", "El nombre del producto es obligatorio.")
            return
        self.accept()

    def obtener_datos(self):
        return {
            "gtin": self.campo_gtin.text().strip(),
            "nombre": self.campo_nombre.text().strip(),
            "descripcion": self.campo_descripcion.toPlainText().strip(),
            "laboratorio": self.campo_laboratorio.text().strip() or None,
            "precio_venta": self.campo_precio_venta.value(),
        }


class DialogoProveedor(QDialog):
    """Formulario para crear o editar los datos de un proveedor."""

    def __init__(self, proveedor=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar proveedor" if proveedor else "Nuevo proveedor")
        self.setMinimumWidth(500)
        self.setStyleSheet(_estilo_formularios(bool(getattr(parent, "modo_oscuro", False))))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        titulo = QLabel("Datos del proveedor")
        titulo.setStyleSheet("font-size: 21px; font-weight: 800;")
        ayuda = QLabel("Registra cómo contactar al proveedor. Solo el nombre es obligatorio.")
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet(
            f"color: {'#a9b8cc' if getattr(parent, 'modo_oscuro', False) else '#667085'};"
        )
        layout.addWidget(titulo)
        layout.addWidget(ayuda)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.campo_nombre = QLineEdit(proveedor.nombre if proveedor else "")
        self.campo_nombre.setPlaceholderText("Ej. Distribuidora Central")
        self.campo_contacto = QLineEdit(proveedor.contacto or "" if proveedor else "")
        self.campo_contacto.setPlaceholderText("Nombre de la persona de contacto")
        self.campo_telefono = QLineEdit(proveedor.telefono or "" if proveedor else "")
        self.campo_telefono.setPlaceholderText("Teléfono de contacto")
        self.campo_email = QLineEdit(proveedor.email or "" if proveedor else "")
        self.campo_email.setPlaceholderText("correo@empresa.com")
        self.campo_direccion = QLineEdit(proveedor.direccion or "" if proveedor else "")
        self.campo_direccion.setPlaceholderText("Dirección (opcional)")
        self.campo_notas = QPlainTextEdit(proveedor.notas or "" if proveedor else "")
        self.campo_notas.setMaximumHeight(90)
        self.campo_notas.setPlaceholderText("Horarios, condiciones de entrega, etc.")

        form.addRow("Nombre *:", self.campo_nombre)
        form.addRow("Persona de contacto:", self.campo_contacto)
        form.addRow("Teléfono:", self.campo_telefono)
        form.addRow("Correo electrónico:", self.campo_email)
        form.addRow("Dirección:", self.campo_direccion)
        form.addRow("Notas:", self.campo_notas)
        layout.addLayout(form)

        botones = QDialogButtonBox()
        guardar = botones.addButton(
            "Guardar proveedor", QDialogButtonBox.AcceptRole
        )
        cancelar = botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        guardar.setDefault(True)
        guardar.clicked.connect(self.validar_y_aceptar)
        cancelar.clicked.connect(self.reject)
        layout.addWidget(botones)
        self.campo_nombre.setFocus()

    def validar_y_aceptar(self):
        if not self.campo_nombre.text().strip():
            QMessageBox.warning(self, "Dato obligatorio", "El nombre del proveedor es obligatorio.")
            return
        correo = self.campo_email.text().strip()
        if correo and ("@" not in correo or "." not in correo.rsplit("@", 1)[-1]):
            QMessageBox.warning(self, "Correo inválido", "Ingresa un correo electrónico válido.")
            return
        self.accept()

    def obtener_datos(self):
        """Entrega datos normalizados y listos para persistir."""
        return {
            "nombre": self.campo_nombre.text().strip(),
            "contacto": self.campo_contacto.text().strip() or None,
            "telefono": self.campo_telefono.text().strip() or None,
            "email": self.campo_email.text().strip() or None,
            "direccion": self.campo_direccion.text().strip() or None,
            "notas": self.campo_notas.toPlainText().strip() or None,
        }


class DialogoAsignarProductos(QDialog):
    """Selector de los productos que suministra un proveedor."""

    def __init__(self, proveedor, productos, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Productos de {proveedor.nombre}")
        self.setMinimumSize(480, 520)
        self.setStyleSheet(_estilo_formularios(bool(getattr(parent, "modo_oscuro", False))))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        titulo = QLabel("Selecciona sus productos")
        titulo.setStyleSheet("font-size: 21px; font-weight: 800;")
        layout.addWidget(titulo)
        indicacion = QLabel("Marca los productos que suministra este proveedor:")
        indicacion.setWordWrap(True)
        layout.addWidget(indicacion)

        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar por nombre o GTIN...")
        self.busqueda.setClearButtonEnabled(True)
        layout.addWidget(self.busqueda)

        self.lista_productos = QListWidget()
        productos_actuales = {producto.id for producto in proveedor.productos}
        for producto in productos:
            elemento = QListWidgetItem(f"{producto.nombre}  ·  GTIN {producto.gtin}")
            elemento.setData(Qt.UserRole, producto.id)
            elemento.setFlags(elemento.flags() | Qt.ItemIsUserCheckable)
            elemento.setCheckState(
                Qt.Checked if producto.id in productos_actuales else Qt.Unchecked
            )
            self.lista_productos.addItem(elemento)
        self.busqueda.textChanged.connect(self._filtrar_productos)
        self.resumen_seleccion = QLabel()
        self._actualizar_resumen()
        self.lista_productos.itemChanged.connect(lambda _item: self._actualizar_resumen())
        layout.addWidget(self.lista_productos, 1)
        layout.addWidget(self.resumen_seleccion)

        botones = QDialogButtonBox()
        guardar = botones.addButton("Guardar asignación", QDialogButtonBox.AcceptRole)
        cancelar = botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        guardar.setDefault(True)
        guardar.clicked.connect(self.accept)
        cancelar.clicked.connect(self.reject)
        layout.addWidget(botones)

    def _filtrar_productos(self, termino):
        termino = termino.strip().casefold()
        for indice in range(self.lista_productos.count()):
            elemento = self.lista_productos.item(indice)
            elemento.setHidden(termino not in elemento.text().casefold())

    def _actualizar_resumen(self):
        total = sum(
            self.lista_productos.item(indice).checkState() == Qt.Checked
            for indice in range(self.lista_productos.count())
        )
        self.resumen_seleccion.setText(f"{total} producto(s) seleccionado(s)")

    def productos_seleccionados(self):
        return [
            self.lista_productos.item(indice).data(Qt.UserRole)
            for indice in range(self.lista_productos.count())
            if self.lista_productos.item(indice).checkState() == Qt.Checked
        ]


def ejecutar_interfaz_gui():
    """Punto de entrada para la interfaz gráfica"""
    try:
        interfaz = InterfazGUI()
        interfaz.ejecutar()
    except ImportError as e:
        print(f"❌ Error: {e}")
