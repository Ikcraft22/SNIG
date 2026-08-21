"""
Aplicación Web Flask para el sistema de inventario.
Proporciona:
- API REST para gestión de inventario
- Interfaz web responsiva
- Reportes en tiempo real
- Panel de administración
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import logging

from database.connection import SessionLocal, init_db
from database.models import Producto, Presentacion, Venta
from core.barcode_scanner import BarcodeLector
from core.inventory_manager import GestorInventario
from core.pos_manager import GestorPOS
from api.gtin_lookup import GTINBuscador
from config.settings import MONEDA, DEBUG

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación Flask
app = Flask(__name__)
CORS(app)

# Inicializar base de datos
init_db()

# ============== INICIALIZADORES ==============

def obtener_db():
    """Obtiene una sesión de BD"""
    return SessionLocal()

def crear_gestores():
    """Crea las instancias de gestores"""
    db = obtener_db()
    return GestorInventario(db), GestorPOS(db), db

# ============== RUTAS - PÁGINA PRINCIPAL ==============

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html', moneda=MONEDA)

@app.route('/inventario')
def inventario():
    """Página de inventario"""
    return render_template('inventario.html', moneda=MONEDA)

@app.route('/pos')
def pos():
    """Página de punto de venta"""
    return render_template('pos.html', moneda=MONEDA)

@app.route('/reportes')
def reportes():
    """Página de reportes"""
    return render_template('reportes.html', moneda=MONEDA)

# ============== API - PRODUCTOS ==============

@app.route('/api/productos', methods=['GET'])
def listar_productos():
    """Lista todos los productos"""
    try:
        db = obtener_db()
        productos = db.query(Producto).all()
        
        data = []
        for p in productos:
            data.append({
                'id': p.id,
                'gtin': p.gtin,
                'nombre': p.nombre,
                'laboratorio': p.laboratorio,
                'presentaciones': [
                    {
                        'id': pres.id,
                        'tipo': pres.tipo.value,
                        'stock': pres.stock_actual,
                        'precio_venta': pres.precio_venta
                    }
                    for pres in p.presentaciones
                ]
            })
        
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error al listar productos: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/productos/<gtin>', methods=['GET'])
def obtener_producto(gtin):
    """Obtiene un producto por GTIN"""
    try:
        db = obtener_db()
        inventario, _, _ = crear_gestores()
        
        producto = inventario.obtener_producto_por_gtin(gtin)
        
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        data = {
            'id': producto.id,
            'gtin': producto.gtin,
            'nombre': producto.nombre,
            'laboratorio': producto.laboratorio,
            'descripcion': producto.descripcion,
            'presentaciones': [
                {
                    'id': pres.id,
                    'tipo': pres.tipo.value,
                    'stock': pres.stock_actual,
                    'precio_venta': pres.precio_venta,
                    'stock_minimo': pres.stock_minimo
                }
                for pres in producto.presentaciones
            ]
        }
        
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error al obtener producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/productos', methods=['POST'])
def crear_producto():
    """Crea un nuevo producto"""
    try:
        db = obtener_db()
        inventario = GestorInventario(db)
        
        datos = request.json
        
        producto = inventario.registrar_producto(
            gtin=datos.get('gtin'),
            nombre=datos.get('nombre'),
            laboratorio=datos.get('laboratorio'),
            descripcion=datos.get('descripcion')
        )
        
        if producto:
            return jsonify({
                'id': producto.id,
                'gtin': producto.gtin,
                'nombre': producto.nombre
            }), 201
        else:
            return jsonify({'error': 'Error al crear producto'}), 400
    
    except Exception as e:
        logger.error(f"Error al crear producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ============== API - BÚSQUEDA POR GTIN (APIs externas) ==============

@app.route('/api/buscar-gtin/<gtin>', methods=['GET'])
def buscar_gtin(gtin):
    """Busca información del producto en APIs externas"""
    try:
        # Validar GTIN
        es_valido, tipo = BarcodeLector.validar_gtin(gtin)
        if not es_valido:
            return jsonify({'error': 'GTIN inválido'}), 400
        
        # Buscar en APIs
        buscador = GTINBuscador()
        resultado = buscador.buscar(gtin)
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error al buscar GTIN: {e}")
        return jsonify({'error': str(e)}), 500

# ============== API - INVENTARIO ==============

@app.route('/api/inventario/stock-bajo', methods=['GET'])
def obtener_stock_bajo():
    """Obtiene productos con stock bajo"""
    try:
        db = obtener_db()
        inventario = GestorInventario(db)
        
        productos = inventario.obtener_productos_stock_bajo()
        
        return jsonify(productos), 200
    
    except Exception as e:
        logger.error(f"Error al obtener stock bajo: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/inventario/movimiento', methods=['POST'])
def registrar_movimiento():
    """Registra un movimiento de inventario"""
    try:
        db = obtener_db()
        inventario = GestorInventario(db)
        
        datos = request.json
        
        movimiento = inventario.registrar_movimiento(
            producto_id=datos.get('producto_id'),
            presentacion_id=datos.get('presentacion_id'),
            tipo=datos.get('tipo'),
            cantidad=datos.get('cantidad'),
            razon=datos.get('razon'),
            usuario=datos.get('usuario'),
            referencia=datos.get('referencia')
        )
        
        if movimiento:
            return jsonify({'mensaje': 'Movimiento registrado'}), 201
        else:
            return jsonify({'error': 'Error al registrar movimiento'}), 400
    
    except Exception as e:
        logger.error(f"Error al registrar movimiento: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/inventario/reporte', methods=['GET'])
def reporte_inventario():
    """Obtiene reporte general de inventario"""
    try:
        db = obtener_db()
        inventario = GestorInventario(db)
        
        reporte = inventario.reporte_general()
        
        return jsonify(reporte), 200
    
    except Exception as e:
        logger.error(f"Error al generar reporte: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ============== API - VENTAS ==============

@app.route('/api/ventas', methods=['GET'])
def listar_ventas():
    """Lista todas las ventas"""
    try:
        db = obtener_db()
        ventas = db.query(Venta).order_by(Venta.fecha.desc()).limit(50).all()
        
        data = [
            {
                'numero_ticket': v.numero_ticket,
                'total': v.total,
                'metodo_pago': v.metodo_pago,
                'usuario': v.usuario,
                'fecha': v.fecha.isoformat()
            }
            for v in ventas
        ]
        
        return jsonify(data), 200
    
    except Exception as e:
        logger.error(f"Error al listar ventas: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/ventas/reporte/<fecha>', methods=['GET'])
def reporte_ventas(fecha):
    """Obtiene reporte de ventas de una fecha"""
    try:
        db = obtener_db()
        pos = GestorPOS(db)
        
        reporte = pos.reporte_ventas_diario(fecha)
        
        return jsonify(reporte), 200
    
    except Exception as e:
        logger.error(f"Error al generar reporte de ventas: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ============== MANEJO DE ERRORES ==============

@app.errorhandler(404)
def no_encontrado(e):
    """Manejador para páginas no encontradas"""
    return jsonify({'error': 'Recurso no encontrado'}), 404

@app.errorhandler(500)
def error_servidor(e):
    """Manejador para errores del servidor"""
    return jsonify({'error': 'Error interno del servidor'}), 500

# ============== CONTEXTO ==============

@app.context_processor
def inyectar_configuracion():
    """Inyecta configuración en templates"""
    return {'moneda': MONEDA}

if __name__ == '__main__':
    from config.settings import FLASK_HOST, FLASK_PORT, DEBUG
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG)
