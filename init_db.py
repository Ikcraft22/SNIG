#!/usr/bin/env python3
"""
Script de inicialización de la base de datos.
Ejecutar antes de usar la aplicación por primera vez.
"""

import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validar_ambiente():
    """Valida que el ambiente esté configurado correctamente"""
    print("\n" + "=" * 70)
    print("🔍 VALIDANDO AMBIENTE".center(70))
    print("=" * 70 + "\n")
    
    # Verificar .env
    if not Path('.env').exists():
        logger.warning("⚠️ Archivo .env no encontrado. Creando desde .env.example...")
        # Crear .env por defecto
        return False
    
    # Verificar imports
    try:
        import flask
        print("✅ Flask instalado")
    except ImportError:
        logger.error("❌ Flask no está instalado")
        print("   Instálalo con: pip install flask")
        return False
    
    try:
        import sqlalchemy
        print("✅ SQLAlchemy instalado")
    except ImportError:
        logger.error("❌ SQLAlchemy no está instalado")
        print("   Instálalo con: pip install sqlalchemy")
        return False

    try:
        from config.settings import DB_ENGINE
    except Exception:
        DB_ENGINE = "sqlite"

    if DB_ENGINE == "mysql":
        try:
            import mysql.connector
            print("✅ MySQL Connector instalado")
        except ImportError:
            logger.error("❌ MySQL Connector no está instalado")
            print("   Instálalo con: pip install mysql-connector-python")
            return False
    else:
        print("✅ SQLite será usado como base de datos local")
    
    try:
        import pandas
        print("✅ Pandas instalado")
    except ImportError:
        logger.warning("⚠️ Pandas no instalado (opcional)")
    
    print("\n✅ Todos los requisitos están instalados\n")
    return True

def crear_tablas():
    """Crea las tablas en la base de datos"""
    print("=" * 70)
    print("📊 CREANDO TABLAS DE BASE DE DATOS".center(70))
    print("=" * 70 + "\n")
    
    try:
        from database.connection import init_db
        
        print("Conectando a la base de datos...")
        init_db()
        
        print("\n✅ Tablas creadas exitosamente")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        print("\n⚠️ Posibles soluciones:")
        print("1. Verifica que MySQL esté corriendo en XAMPP")
        print("2. Verifica la configuración en .env")
        print("3. Asegúrate de que la base de datos existe:")
        print("   CREATE DATABASE inventario_general;")
        return False

def crear_usuario_administrador():
    """Configura el primer administrador sin credenciales predeterminadas."""
    print("\n" + "=" * 70)
    print("👤 CREAR USUARIO ADMINISTRADOR".center(70))
    print("=" * 70 + "\n")
    
    try:
        from database.connection import SessionLocal
        from database.models import Usuario

        db = SessionLocal()
        admin = db.query(Usuario).filter(
            Usuario.rol == "admin",
            Usuario.activo.is_(True),
            Usuario.password_hash.isnot(None),
        ).first()
        db.close()
        if admin:
            print("⚠️ Ya existe un administrador con contraseña configurada")
            return True

        from core.auth import configurar_administrador_interactivo

        configurar_administrador_interactivo()
        return True

    except (ValueError, RuntimeError) as e:
        logger.error("❌ No se pudo configurar el administrador: %s", e)
        return False
    except Exception as e:
        logger.error(f"❌ Error al configurar usuario administrador: {e}")
        return False

def obtener_productos_demo_tienda_escolar():
    """Retorna una lista de productos demo orientados a tienda escolar y minorista."""
    return [
        {
            "gtin": "750100010001",
            "nombre": "Paleta de fresa",
            "categoria": "dulces",
            "caracteristicas": "Caramelo macizo sabor fresa 20g",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 5, "precio_venta": 10, "stock": 80}
            ]
        },
        {
            "gtin": "750100010002",
            "nombre": "Chocolate con leche 30g",
            "categoria": "dulces",
            "caracteristicas": "Tableta de chocolate con leche",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 12, "precio_venta": 22, "stock": 50}
            ]
        },
        {
            "gtin": "750100010003",
            "nombre": "Gomitas frutales 50g",
            "categoria": "dulces",
            "caracteristicas": "Gomitas surtidas de frutas",
            "presentaciones": [
                {"tipo": "bolsa", "cantidad": 1, "precio_unitario": 8, "precio_venta": 15, "stock": 60}
            ]
        },
        {
            "gtin": "750100010004",
            "nombre": "Cuaderno Profesional 100 Hojas",
            "categoria": "papeleria",
            "caracteristicas": "Cuadrícula chica pasta dura",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 20, "precio_venta": 45, "stock": 40}
            ]
        },
        {
            "gtin": "750100010005",
            "nombre": "Lápiz Grafito 2B",
            "categoria": "papeleria",
            "caracteristicas": "Madera reforestada grafito HB",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 4, "precio_venta": 10, "stock": 100}
            ]
        },
        {
            "gtin": "750100010006",
            "nombre": "Bolígrafo Tinta Negra",
            "categoria": "papeleria",
            "caracteristicas": "Punto mediano 1.0mm",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 5, "precio_venta": 12, "stock": 120}
            ]
        },
        {
            "gtin": "750100010007",
            "nombre": "Goma de borrar blanca",
            "categoria": "papeleria",
            "caracteristicas": "Libre de látex no mancha",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 6, "precio_venta": 15, "stock": 70}
            ]
        },
        {
            "gtin": "750100010008",
            "nombre": "Regla flexible 30cm",
            "categoria": "papeleria",
            "caracteristicas": "Plástico flexible graduado",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 8, "precio_venta": 18, "stock": 35}
            ]
        },
        {
            "gtin": "750100010009",
            "nombre": "Sacapuntas con depósito",
            "categoria": "papeleria",
            "caracteristicas": "Cuchilla de acero con depósito",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 7, "precio_venta": 16, "stock": 45}
            ]
        },
        {
            "gtin": "750100010010",
            "nombre": "Pegamento adhesivo en barra 22g",
            "categoria": "papeleria",
            "caracteristicas": "Fórmula lavable no tóxica",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 14, "precio_venta": 28, "stock": 50}
            ]
        },
        {
            "gtin": "750100010011",
            "nombre": "Tijeras escolares punta roma",
            "categoria": "papeleria",
            "caracteristicas": "Acero inoxidable seguras",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 12, "precio_venta": 25, "stock": 30}
            ]
        },
        {
            "gtin": "750100010012",
            "nombre": "Agua purificada 500ml",
            "categoria": "bebidas",
            "caracteristicas": "Botella de agua purificada",
            "presentaciones": [
                {"tipo": "botella", "cantidad": 1, "precio_unitario": 6, "precio_venta": 12, "stock": 90}
            ]
        },
        {
            "gtin": "750100010013",
            "nombre": "Jugo de manzana 200ml",
            "categoria": "bebidas",
            "caracteristicas": "Jugo natural sin azúcar añadida",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 9, "precio_venta": 18, "stock": 60}
            ]
        },
        {
            "gtin": "750100010014",
            "nombre": "Papas fritas con sal 45g",
            "categoria": "snacks",
            "caracteristicas": "Papas crujientes saladas",
            "presentaciones": [
                {"tipo": "bolsa", "cantidad": 1, "precio_unitario": 13, "precio_venta": 24, "stock": 40}
            ]
        },
        {
            "gtin": "750100010015",
            "nombre": "Galletas con chispas de chocolate",
            "categoria": "snacks",
            "caracteristicas": "Paquete con 6 galletas",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 10, "precio_venta": 20, "stock": 55}
            ]
        },
        {
            "gtin": "750100010016",
            "nombre": "Barra de cereal con avena",
            "categoria": "snacks",
            "caracteristicas": "Avena y miel 38g",
            "presentaciones": [
                {"tipo": "unidad", "cantidad": 1, "precio_unitario": 8, "precio_venta": 16, "stock": 40}
            ]
        }
    ]

def cargar_datos_iniciales():
    """Opcionalmente carga datos de prueba"""
    print("\n" + "=" * 70)
    print("📦 CARGAR DATOS DE PRUEBA (OPCIONAL)".center(70))
    print("=" * 70 + "\n")
    
    respuesta = input("¿Deseas cargar datos de prueba? (s/n): ").strip().lower()
    
    if respuesta != 's':
        print("Saltando datos de prueba...")
        return True
    
    try:
        from database.connection import SessionLocal
        from core.inventory_manager import GestorInventario
        
        db = SessionLocal()
        gestor = GestorInventario(db)
        
        # Productos de prueba
        productos_prueba = obtener_productos_demo_tienda_escolar()
        
        for prod in productos_prueba:
            producto = gestor.registrar_producto(
                gtin=prod['gtin'],
                nombre=prod['nombre'],
                descripcion=prod.get('caracteristicas')
            )
            
            if producto:
                for pres in prod['presentaciones']:
                    gestor.agregar_presentacion(
                        producto_id=producto.id,
                        tipo_presentacion=pres['tipo'],
                        cantidad=pres['cantidad'],
                        precio_unitario=pres['precio_unitario'],
                        precio_venta=pres['precio_venta'],
                        stock_inicial=pres['stock']
                    )
                    print(f"✅ Producto registrado: {prod['nombre']}")
        
        db.close()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error al cargar datos: {e}")
        return False

def mostrar_resumen():
    """Muestra un resumen final"""
    print("\n" + "=" * 70)
    print("✅ INICIALIZACIÓN COMPLETADA".center(70))
    print("=" * 70)
    
    print("\n📋 Próximos pasos:")
    print("1. Ejecuta 'python main.py' para abrir la interfaz gráfica.")
    print("2. Otras interfaces:")
    print("   - Terminal: python -m ui.terminal_ui")
    print("   - Dashboard: python main.py --reportes")
    print("   - Web: python -m web.app (http://localhost:5000)")
    
    print("\n📚 Documentación:")
    print("- README.md: Guía general")
    print("- FAQ.md: Preguntas frecuentes")
    
    print("\n💡 Consejos:")
    print("- SQLite es la base de datos predeterminada; MySQL es opcional.")
    print("- Personaliza .env según tu configuración.")
    print("- Haz backups regularmente")
    
    print("\n" + "=" * 70 + "\n")

def main():
    """Función principal"""
    from config.settings import AUTENTICACION_HABILITADA

    print("\n📦 INICIALIZADOR DEL SISTEMA DE INVENTARIO GENERAL\n")
    
    # Validar ambiente
    if not validar_ambiente():
        print("\n❌ Por favor instala las dependencias faltantes:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Crear tablas
    if not crear_tablas():
        print("\n❌ Fallo la creación de tablas. Verifica tu configuración.")
        sys.exit(1)
    
    if AUTENTICACION_HABILITADA:
        crear_usuario_administrador()
    else:
        print("Autenticación desactivada; se omite la configuración de usuarios.")
    
    # Cargar datos iniciales
    cargar_datos_iniciales()
    
    # Resumen
    mostrar_resumen()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Inicialización cancelada")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
