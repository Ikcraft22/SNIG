#!/usr/bin/env python3
"""
Punto de entrada principal del Sistema de Inventario de Medicamentos.
Permite seleccionar entre diferentes interfaces de usuario.
"""

import sys
import json
import time
import logging
from datetime import date
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def mostrar_menu_principal():
    """Muestra el menú principal de selección de interfaz"""
    print("\n" + "=" * 70)
    print("🏥 SISTEMA DE INVENTARIO DE MEDICAMENTOS".center(70))
    print("=" * 70)
    print("\nSelecciona la interfaz a utilizar:\n")
    print("1. 💻 Terminal (CLI) - Interfaz de línea de comandos")
    print("2. 🖥️  Interfaz Gráfica (GUI) - Interfaz visual con PyQt5")
    print("3. 🌐 Web - Interfaz web con Flask")
    print("4. ⚙️  Configuración (crear base de datos MySQL)")
    print("5. 🚪 Salir")
    print("\n" + "=" * 70)

def ejecutar_interfaz_terminal():
    """Ejecuta la interfaz de terminal"""
    try:
        from ui.terminal_ui import ejecutar_interfaz_terminal as ejecutar
        print("\n✅ Iniciando interfaz de terminal...")
        ejecutar()
    except Exception as e:
        logger.error(f"❌ Error al ejecutar interfaz de terminal: {e}")
        print(f"❌ Error: {e}")

def ejecutar_interfaz_gui():
    """Ejecuta la interfaz gráfica con una pantalla de bienvenida inicial."""
    try:
        from PyQt5.QtWidgets import QApplication, QSplashScreen
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPixmap
        from ui.gui_ui import InterfazGUI

        print("\n✅ Iniciando interfaz gráfica...")

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        estado_archivo = Path(__file__).resolve().parent / ".startup_state.json"
        hoy = date.today().isoformat()
        mostrar_splash = True

        if estado_archivo.exists():
            try:
                datos = json.loads(estado_archivo.read_text(encoding="utf-8"))
                mostrar_splash = datos.get("last_run_date") != hoy
            except Exception:
                mostrar_splash = True

        if mostrar_splash:
            icono = Path(__file__).resolve().parent / "Icono.jpeg"
            splash = None
            if icono.exists():
                pixmap = QPixmap(str(icono))
                if not pixmap.isNull():
                    splash = QSplashScreen(
                        pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                    splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
                    splash.show()
                    app.processEvents()
                    time.sleep(2.5)
                    splash.close()
            else:
                time.sleep(2.5)

        estado_archivo.write_text(json.dumps({"last_run_date": hoy}), encoding="utf-8")

        interfaz = InterfazGUI(app)
        interfaz.ejecutar()
    except ImportError:
        print("\n❌ PyQt5 no está instalado.")
        print("Instálalo con: pip install PyQt5")
    except Exception as e:
        logger.error(f"❌ Error al ejecutar interfaz gráfica: {e}")
        print(f"❌ Error: {e}")

def ejecutar_interfaz_web():
    """Ejecuta la interfaz web"""
    try:
        from web.app import app
        from config.settings import FLASK_HOST, FLASK_PORT
        
        print(f"\n✅ Iniciando servidor web...")
        print(f"🌐 Abre en tu navegador: http://{FLASK_HOST}:{FLASK_PORT}")
        print("⏹️  Presiona Ctrl+C para detener el servidor\n")
        
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
    except Exception as e:
        logger.error(f"❌ Error al ejecutar servidor web: {e}")
        print(f"❌ Error: {e}")

def configurar_base_datos():
    """Guía para configurar la base de datos"""
    print("\n" + "=" * 70)
    print("⚙️  CONFIGURACIÓN DE BASE DE DATOS".center(70))
    print("=" * 70)
    
    print("\n📋 Opción recomendada: usa SQLite local sin XAMPP")
    print("   - En el archivo .env configura:")
    print("     DB_ENGINE=sqlite")
    print("     SQLITE_FILE=./inventario.db")
    print("   - La base de datos se guarda en un solo archivo local")
    
    print("\n📋 Si prefieres MySQL con XAMPP, usa:")
    print("     DB_ENGINE=mysql")
    print("     MYSQL_HOST=localhost")
    print("     MYSQL_PORT=3306")
    print("     MYSQL_USER=root")
    print("     MYSQL_PASSWORD=(dejalo vacío si no has configurado contraseña)")
    print("     MYSQL_DATABASE=inventario_medicamentos")
    
    print("\n📋 Paso final: instala dependencias")
    print("   pip install -r requirements.txt")
    
    print("\n✅ Listo para usar el sistema")
    input("\nPresiona Enter para volver al menú principal...")

def main():
    """Función principal"""
    try:
        # Arrancar siempre la interfaz gráfica (equivalente a seleccionar la opción 2)
        ejecutar_interfaz_gui()
        # Si en algún caso se desea el menú interactivo, descomentar el bloque siguiente
        # while True:
        #     mostrar_menu_principal()
        #     opcion = input("\nSelecciona una opción (1-5): ").strip()
        #     if opcion == "1":
        #         ejecutar_interfaz_terminal()
        #     elif opcion == "2":
        #         ejecutar_interfaz_gui()
        #     elif opcion == "3":
        #         ejecutar_interfaz_web()
        #     elif opcion == "4":
        #         configurar_base_datos()
        #     elif opcion == "5":
        #         print("\n👋 ¡Hasta luego!")
        #         break
        #     else:
        #         print("\n❌ Opción inválida. Intenta de nuevo.")
    
    except KeyboardInterrupt:
        print("\n\n👋 Aplicación interrumpida")
    except Exception as e:
        logger.error(f"Error no controlado: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
