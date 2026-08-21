#!/usr/bin/env python3
"""
Punto de entrada principal del Sistema de Inventario.
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
