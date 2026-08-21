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
    """Crea un usuario administrador por defecto"""
    print("\n" + "=" * 70)
    print("👤 CREAR USUARIO ADMINISTRADOR".center(70))
    print("=" * 70 + "\n")
    
    try:
        from database.connection import SessionLocal
        from database.models import Usuario
        
        db = SessionLocal()
        
        # Verificar si ya existe admin
        admin = db.query(Usuario).filter(Usuario.rol == "admin").first()
        if admin:
            print("⚠️ Usuario administrador ya existe")
            db.close()
            return True
        
        # Crear admin
        admin = Usuario(
            nombre="Administrador",
            email="admin@tienda.local",
            rol="admin",
            activo=True
        )
        
        db.add(admin)
        db.commit()
        
        print("✅ Usuario administrador creado:")
        print(f"   Nombre: {admin.nombre}")
        print(f"   Email: {admin.email}")
        print(f"   Rol: {admin.rol}")
        
        db.close()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error al crear usuario: {e}")
        return False

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
        productos_prueba = [
            {
                'gtin': '7501001234567',
                'nombre': 'Paracetamol 500mg',
                'laboratorio': 'Lab Genérico',
                'presentaciones': [
                    {'tipo': 'unidad', 'cantidad': 1, 'precio_unitario': 30, 'precio_venta': 50, 'stock': 50}
                ]
            },
            {
                'gtin': '7501001234568',
                'nombre': 'Ibupirac 400mg',
                'laboratorio': 'Lab Genérico',
                'presentaciones': [
                    {'tipo': 'bolsa', 'cantidad': 10, 'precio_unitario': 120, 'precio_venta': 260, 'stock': 30}
                ]
            },
            {
                'gtin': '7501001234569',
                'nombre': 'Vitamina C 1000mg',
                'laboratorio': 'Lab Salud',
                'presentaciones': [
                    {'tipo': 'botella', 'cantidad': 1, 'precio_unitario': 90, 'precio_venta': 190, 'stock': 100}
                ]
            }
        ]
        
        for prod in productos_prueba:
            producto = gestor.registrar_producto(
                gtin=prod['gtin'],
                nombre=prod['nombre'],
                laboratorio=prod['laboratorio']
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
    print("1. Ejecuta: python main.py")
    print("2. Selecciona tu interfaz preferida:")
    print("   - Terminal (1): Para escaneo rápido")
    print("   - GUI (2): Para interfaz visual")
    print("   - Web (3): Para múltiples usuarios")
    
    print("\n📚 Documentación:")
    print("- README.md: Guía general")
    print("- FAQ.md: Preguntas frecuentes")
    
    print("\n💡 Consejos:")
    print("- Ten XAMPP corriendo con MySQL activo")
    print("- Personaliza .env según tu configuración")
    print("- Haz backups regularmente")
    
    print("\n" + "=" * 70 + "\n")

def main():
    """Función principal"""
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
    
    # Crear usuario admin
    crear_usuario_administrador()
    
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
