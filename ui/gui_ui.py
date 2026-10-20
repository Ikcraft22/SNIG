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
            QSizePolicy, QHeaderView, QSlider
    )
    from PyQt5.QtCore import Qt, QSize, QTimer, QEvent
    from PyQt5.QtGui import QIcon, QFont, QColor
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    print("⚠️ PyQt5 no está instalado. Use: pip install PyQt5")

from database.connection import SessionLocal, init_db
from core.barcode_scanner import EscanerProducto
from core.inventory_manager import GestorInventario
from core.pos_manager import GestorPOS, calcular_vuelto
from config.settings import PRESENTACIONES, MONEDA
from ui.switch_dia_noche import SwitchDiaNoche

logger = logging.getLogger(__name__)

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
        QTimer.singleShot(0, self.ventana_principal._enfocar_gtin_pos)
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
        self._indice_pestana_activa = 1
        self.proceso_streamlit = None
        
        # Crear interfaz
        self.crear_ui()

    def crear_ui(self):
        """Crea la interfaz de usuario"""
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        modo_oscuro = self.modo_oscuro

        if modo_oscuro:
            self.setStyleSheet(
                "QMainWindow { background-color: #121722; }"
                "QStatusBar { background-color: #1a1f2e; color: #e7ebf5; }"
            )
        else:
            self.setStyleSheet(
                "QMainWindow { background-color: #f2f3f5; }"
                "QStatusBar { background-color: #f2f3f5; color: #2c3e50; }"
            )
        
        # Selector manual de tema animado (Día / Noche)
        barra_superior = QHBoxLayout()
        barra_superior.setContentsMargins(0, 0, 8, 6)
        barra_superior.addStretch(1)
        self.interruptor_tema = SwitchDiaNoche(checked=modo_oscuro, width=96, height=42)
        self.interruptor_tema.toggled.connect(self.cambiar_tema)
        barra_superior.addWidget(self.interruptor_tema)

        # Crear pestañas
        self.pestanas = QTabWidget()
        if modo_oscuro:
            self.pestanas.setStyleSheet(
                "QTabBar::tab {"
                "min-height: 52px;"
                "padding: 12px 22px;"
                "font-size: 16px;"
                "font-weight: 700;"
                "min-width: 150px;"
                "width: 150px;"
                "color: #eaf2ff;"
                "background: #1c2434;"
                "border: 1px solid #2d3a4d;"
                "border-bottom: none;"
                "border-top-left-radius: 8px;"
                "border-top-right-radius: 8px;"
                "margin-right: 2px;"
                "}"
                "QTabBar::tab:selected {"
                "background: #2a3b57;"
                "color: #ffffff;"
                "border-color: #4a6488;"
                "}"
                "QTabBar {"
                "background: #141b27;"
                "alignment: center;"
                "}"
            )
        else:
            self.pestanas.setStyleSheet(
                "QTabBar::tab {"
                "min-height: 52px;"
                "padding: 12px 22px;"
                "font-size: 16px;"
                "font-weight: 700;"
                "min-width: 150px;"
                "width: 150px;"
                "}"
                "QTabBar {"
                "alignment: center;"
                "}"
            )
        self.pestanas.tabBar().installEventFilter(self)
        
        # Pestaña de Inventario
        self.pestanas.addTab(self.crear_pestaña_inventario(), "📦 Inventario")
        
        # Pestaña de POS
        self.pestanas.addTab(self.crear_pestaña_pos(), "🛒 POS")
        
        # Pestaña de Reportes
        self.pestana_reportes = self.crear_pestaña_reportes()
        self.pestanas.addTab(self.pestana_reportes, "📊 Reportes")
        
        # Pestaña de Logs (oculta hasta que se solicite)
        self.pestana_logs = self.crear_pestaña_logs()
        self.pestanas.addTab(self.pestana_logs, "📝 Logs")
        self.pestanas.tabBar().setTabVisible(self.pestanas.indexOf(self.pestana_logs), False)
        
        # Mostrar POS como primera pestaña activa
        self.pestanas.setCurrentIndex(self._indice_pestana_activa)
        self.pestanas.currentChanged.connect(self._enfocar_gtin_pos_si_corresponde)
        
        layout = QVBoxLayout()
        layout.addLayout(barra_superior)
        layout.addWidget(self.pestanas)
        widget_central.setLayout(layout)
        
        # Barra de estado
        self.statusBar().showMessage("Listo")
        QTimer.singleShot(0, self.showMaximized)

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
        self.tabla_inventario.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla_inventario.setColumnCount(4)
        self.tabla_inventario.setHorizontalHeaderLabels(
            ["GTIN", "Nombre", "Stock", "Precio"]
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
            f"QLabel {{ font-size: 12px; color: {texto}; }}"
            f"QLineEdit {{ padding: 8px; font-size: 13px; background-color: {superficie}; color: {texto}; border: 1px solid {borde}; }}"
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
        self.label_subtotal = QLabel(f"Subtotal: {MONEDA}0")
        self.label_total = QLabel(f"Total: {MONEDA}0")
        self.label_subtotal.setStyleSheet(f"font-size: 13px; color: {texto};")
        self.label_total.setStyleSheet("font-size: 14px; font-weight: bold; color: #27ae60;")
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
        btn_pagar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 15px;")
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
        if index == 1:
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
            f"QLabel {{ font-size: 13px; color: {texto}; }}"
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
        self.texto_reporte.setWordWrap(True)
        self.texto_reporte.setStyleSheet(
            f"background-color: {superficie}; border: 1px solid {borde}; border-radius: 8px; padding: 12px; color: {texto}; font-size: 13px;"
        )
        self.texto_reporte.setMinimumHeight(180)
        layout.addWidget(self.texto_reporte)

        widget.setLayout(layout)
        return widget

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
                    self.tabla_inventario.setItem(fila, 3, QTableWidgetItem(f"{MONEDA}{presentacion.precio_venta:.0f}"))
        else:
            QMessageBox.information(self, "Información", f"No se encontraron productos para: {termino}")

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
            f"• Inversión Total (Costo): {MONEDA}{datos['valor_costo_total']:,}\n"
            f"• Venta Potencial Total: {MONEDA}{datos['valor_venta_potencial']:,}\n"
            f"• Ganancia Proyectada: {MONEDA}{datos['ganancia_proyectada']:,}\n"
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
                self.tabla_inventario.setItem(fila, 3, QTableWidgetItem(f"{MONEDA}{presentacion.precio_venta:.0f}"))

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

        opciones = [
            "[1] Efectivo",
            "[2] Tarjeta",
            "[3] Transferencia",
        ]
        texto, ok = QInputDialog.getText(
            self,
            "Método de pago",
            "Selecciona una opción:\n" + "\n".join(opciones)
        )
        if not ok:
            return

        texto = texto.strip()
        mapa = {
            "1": "efectivo",
            "2": "tarjeta",
            "3": "transferencia",
        }
        metodo = mapa.get(texto)
        if metodo is None:
            QMessageBox.warning(self, "Error", "Selecciona una opción válida: 1, 2 o 3")
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
                f"Total: {MONEDA}{venta.total:.0f}"
            )
            if metodo == "efectivo":
                mensaje += (
                    f"\nEfectivo recibido: {MONEDA}{efectivo_recibido:.0f}"
                    f"\nVuelto: {MONEDA}{vuelto:.0f}"
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
        self.label_subtotal.setText(f"Subtotal: {MONEDA}{resumen['subtotal']:.0f}")
        self.label_total.setText(f"Total: {MONEDA}{resumen['total']:.0f}")

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
            self.tabla_carrito.setItem(fila, 2, QTableWidgetItem(f"{MONEDA}{it['precio_unitario']:.0f}"))
            # Columna 3: Subtotal
            self.tabla_carrito.setItem(fila, 3, QTableWidgetItem(f"{MONEDA}{it['subtotal']:.0f}"))
    
    def generar_reporte_inventario(self):
        """Genera reporte de inventario"""
        reporte = self.inventario.reporte_general()
        texto = f"""
        Reporte de Inventario
        Fecha: {reporte['fecha']}
        
        Total de Productos: {reporte['total_productos']}
        Stock Total: {reporte['total_stock']} unidades
        Valor Inventario: {MONEDA}{reporte['valor_inventario']:.0f}
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
        Total de Ventas: {MONEDA}{reporte['total_ventas']:.0f}
        Promedio por Venta: {MONEDA}{reporte['promedio_venta']:.0f}

        Métodos de Pago:
        {chr(10).join([f"  {k}: {MONEDA}{v:.0f}" for k, v in reporte['metodos_pago'].items()])}
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
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.campo_gtin = QLineEdit()
        self.campo_nombre = QLineEdit()
        self.campo_descripcion = QLineEdit()
        self.campo_precio = QDoubleSpinBox()
        self.campo_precio.setRange(0.0, 1000000.0)
        self.campo_precio.setDecimals(0)
        self.campo_precio.setValue(0.0)
        self.campo_stock_inicial = QSpinBox()
        self.campo_stock_inicial.setRange(0, 10000)
        self.campo_stock_inicial.setValue(0)

        form.addRow("GTIN:", self.campo_gtin)
        form.addRow("Nombre:", self.campo_nombre)
        form.addRow("Descripción:", self.campo_descripcion)
        form.addRow("Precio:", self.campo_precio)
        form.addRow("Stock inicial:", self.campo_stock_inicial)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.validar_y_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self.setLayout(layout)

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
            'descripcion': self.campo_descripcion.text().strip(),
            'precio': self.campo_precio.value(),
            'stock_inicial': self.campo_stock_inicial.value(),
        }


class DialogoEditarProducto(QDialog):
    """Diálogo para editar un producto y el precio de una presentación."""

    def __init__(self, producto, presentacion, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar producto")
        self.setMinimumWidth(420)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.campo_gtin = QLineEdit(producto.gtin or "")
        self.campo_nombre = QLineEdit(producto.nombre or "")
        self.campo_descripcion = QLineEdit(producto.descripcion or "")
        self.campo_laboratorio = QLineEdit(producto.laboratorio or "")
        self.campo_precio_venta = QDoubleSpinBox()
        self.campo_precio_venta.setRange(1, 1000000)
        self.campo_precio_venta.setDecimals(0)
        self.campo_precio_venta.setValue(presentacion.precio_venta)

        form.addRow("GTIN:", self.campo_gtin)
        form.addRow("Nombre:", self.campo_nombre)
        form.addRow("Descripción:", self.campo_descripcion)
        form.addRow("Laboratorio:", self.campo_laboratorio)
        form.addRow(f"Precio de venta ({presentacion.tipo.value}):", self.campo_precio_venta)
        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.validar_y_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        self.setLayout(layout)

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
            "descripcion": self.campo_descripcion.text().strip(),
            "laboratorio": self.campo_laboratorio.text().strip() or None,
            "precio_venta": self.campo_precio_venta.value(),
        }


def ejecutar_interfaz_gui():
    """Punto de entrada para la interfaz gráfica"""
    try:
        interfaz = InterfazGUI()
        interfaz.ejecutar()
    except ImportError as e:
        print(f"❌ Error: {e}")
