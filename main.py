#!/usr/bin/env python3
"""
Punto de entrada principal del Sistema de Inventario.
Permite seleccionar entre diferentes interfaces de usuario.
"""

import sys
import json
import time
import logging
import os
from datetime import date
from pathlib import Path

if getattr(sys, "frozen", False):
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            setattr(sys, stream_name, open(os.devnull, "w", encoding="utf-8"))
        elif hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

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

        datos = {}
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

        datos["last_run_date"] = hoy
        estado_archivo.write_text(json.dumps(datos, indent=2), encoding="utf-8")

        interfaz = InterfazGUI(app)
        interfaz.ejecutar()
    except ImportError:
        print("\n❌ PyQt5 no está instalado.")
        print("Instálalo con: pip install PyQt5")
    except Exception as e:
        logger.error(f"❌ Error al ejecutar interfaz gráfica: {e}")
        print(f"❌ Error: {e}")

def ejecutar_reportes_streamlit():
    """Ejecuta el servidor de reportes interactivos con Streamlit."""
    import subprocess
    script_path = Path(__file__).resolve().parent / "reporting" / "streamlit_reports.py"
    print("\n🚀 Iniciando servidor de reportes interactivos con Streamlit...")
    if getattr(sys, "frozen", False):
        from streamlit.web.cli import main as streamlit_main

        sys.argv = [
            "streamlit",
            "run",
            str(script_path),
            "--server.headless",
            "true",
        ]
        streamlit_main()
        return

    cmd = [sys.executable, "-m", "streamlit", "run", str(script_path)]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Servidor de Streamlit detenido.")

def main():
    """Función principal"""
    try:
        if len(sys.argv) > 1 and sys.argv[1].lower() in ["--streamlit", "--reportes", "-r", "reportes"]:
            ejecutar_reportes_streamlit()
            return

        # Arrancar siempre la interfaz gráfica por defecto
        ejecutar_interfaz_gui()
    
    except KeyboardInterrupt:
        print("\n\n👋 Aplicación interrumpida")
    except Exception as e:
        logger.error(f"Error no controlado: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
