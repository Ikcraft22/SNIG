"""
Aplicación Web Flask para el sistema de inventario.
Proporciona:
- API REST para gestión de inventario
- Interfaz web responsiva
- Reportes en tiempo real
- Panel de administración
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_cors import CORS
from datetime import datetime, date
import json
import logging
import os
import tempfile
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from database.connection import SessionLocal, init_db
from database.models import Producto, Presentacion, Venta, SyncChange, SyncState
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


@app.route('/api/sync/cursor', methods=['GET'])
def obtener_cursor_sync():
    """Devuelve el cursor de referencia antes de que un cliente descargue el estado inicial."""
    db = obtener_db()
    try:
        cursor = db.query(SyncState.last_sequence).filter(SyncState.id == 1).scalar() or 0
        return jsonify({'cursor': cursor}), 200
    except Exception as e:
        logger.error(f"Error al obtener cursor de sincronización: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/sync/changes', methods=['GET'])
def listar_cambios_sync():
    """Entrega cambios incrementales en orden de cursor."""
    try:
        cursor = int(request.args.get("cursor", "0"))
        limit = int(request.args.get("limit", "100"))
    except ValueError:
        return jsonify({'error': 'cursor y limit deben ser enteros'}), 400
    if cursor < 0 or limit < 1 or limit > 500:
        return jsonify({'error': 'cursor debe ser no negativo y limit debe estar entre 1 y 500'}), 400

    db = obtener_db()
    try:
        rows = (
            db.query(SyncChange)
            .filter(SyncChange.id > cursor)
            .order_by(SyncChange.id)
            .limit(limit + 1)
            .all()
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = rows[-1].id if rows else cursor
        return jsonify({
            'changes': [
                {
                    'cursor': row.id,
                    'entity_type': row.entity_type,
                    'entity_id': row.entity_id,
                    'operation': row.operation,
                    'payload': json.loads(row.payload),
                    'occurred_at': row.occurred_at.isoformat() if row.occurred_at else None,
                }
                for row in rows
            ],
            'next_cursor': next_cursor,
            'has_more': has_more,
        }), 200
    except Exception as e:
        logger.error(f"Error al listar cambios de sincronización: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

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
    """Lista productos; admite paginación opcional mediante page y per_page."""
    paginada = "page" in request.args or "per_page" in request.args
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
    except ValueError:
        return jsonify({'error': 'page y per_page deben ser enteros'}), 400
    if page < 1 or per_page < 1 or per_page > 100:
        return jsonify({'error': 'page debe ser positivo y per_page debe estar entre 1 y 100'}), 400

    try:
        db = obtener_db()
        query = db.query(Producto).options(selectinload(Producto.presentaciones)).order_by(Producto.id)
        total = db.query(func.count(Producto.id)).scalar() if paginada else None
        if paginada:
            productos = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            productos = query.all()
        
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
        
        if paginada:
            return jsonify({
                'items': data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page if total else 0,
                },
            }), 200
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
        
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({'error': 'El cuerpo debe ser un objeto JSON'}), 400
        
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
        
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({'error': 'El cuerpo debe ser un objeto JSON'}), 400
        
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

# ============== API - FUNCIONES AVANZADAS DE INVENTARIO & POS ==============

@app.route('/api/inventario/resumen-financiero', methods=['GET'])
def api_inventario_resumen_financiero():
    """Obtiene el resumen financiero de valorización y rentabilidad del inventario"""
    try:
        db = obtener_db()
        gestor = GestorInventario(db)
        resumen = gestor.calcular_valor_inventario()
        return jsonify(resumen), 200
    except Exception as e:
        logger.error(f"Error al obtener resumen financiero: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/inventario/reabastecimiento', methods=['GET'])
def api_inventario_reabastecimiento():
    """Obtiene la lista de sugerencias de reabastecimiento para productos en nivel crítico/bajo"""
    try:
        db = obtener_db()
        gestor = GestorInventario(db)
        sugerencias = gestor.obtener_sugerencias_reabastecimiento()
        return jsonify(sugerencias), 200
    except Exception as e:
        logger.error(f"Error al obtener sugerencias de reabastecimiento: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/inventario/exportar', methods=['GET'])
def api_inventario_exportar():
    """Exporta y descarga el catálogo completo en formato CSV"""
    db = obtener_db()
    try:
        gestor = GestorInventario(db)
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8') as temp_file:
            temp_path = temp_file.name

        exito = gestor.exportar_catalogo_csv(temp_path)
        if not exito or not os.path.exists(temp_path):
            return jsonify({'error': 'No se pudo generar el archivo de exportación'}), 500

        with open(temp_path, 'r', encoding='utf-8') as f:
            contenido = f.read()

        os.remove(temp_path)
        return Response(
            contenido,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=catalogo_inventario.csv'}
        )
    except Exception as e:
        logger.error(f"Error al exportar catálogo: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/inventario/importar', methods=['POST'])
def api_inventario_importar():
    """Importa productos y presentaciones desde un archivo CSV cargado"""
    db = obtener_db()
    try:
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo con el campo "archivo"'}), 400

        archivo = request.files['archivo']
        if not archivo.filename.endswith('.csv'):
            return jsonify({'error': 'El archivo debe tener extensión .csv'}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            archivo.save(temp_file.name)
            temp_path = temp_file.name

        gestor = GestorInventario(db)
        resultado = gestor.importar_catalogo_csv(temp_path)
        os.remove(temp_path)

        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error al importar catálogo: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/inventario/backup', methods=['GET', 'POST'])
def api_inventario_backup():
    """Genera una copia de seguridad timestamped de la base de datos"""
    db = obtener_db()
    try:
        gestor = GestorInventario(db)
        archivo_backup = gestor.crear_backup()
        if archivo_backup:
            return jsonify({
                'mensaje': 'Copia de seguridad creada exitosamente',
                'archivo': os.path.basename(archivo_backup),
                'ruta': archivo_backup
            }), 200
        return jsonify({'error': 'No se pudo generar la copia de seguridad'}), 500
    except Exception as e:
        logger.error(f"Error al generar backup: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/pos/cierre-caja', methods=['GET'])
def api_pos_cierre_caja():
    """Obtiene el cuadre y cierre de caja del día o de la fecha especificada"""
    fecha = request.args.get('fecha', date.today().isoformat())
    db = obtener_db()
    try:
        pos = GestorPOS(db)
        cierre = pos.obtener_metricas_cierre_caja(fecha)
        return jsonify(cierre), 200
    except Exception as e:
        logger.error(f"Error al generar cierre de caja: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ============== MANEJO DE ERRORES ==============

@app.errorhandler(404)
def no_encontrado(e):
    """Manejador para páginas no encontradas"""
    return jsonify({'error': 'Recurso no encontrado'}), 404

@app.route('/api/ventas/checkout', methods=['POST'])
def checkout_venta():
    """Procesa la venta del carrito actual usando el gestor POS real."""
    datos = request.get_json(silent=True) or {}
    items = datos.get('items') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'El carrito está vacío'}), 400
    db = obtener_db()
    try:
        gestor = GestorPOS(db)
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Cada ítem del carrito debe ser un objeto JSON válido')
            producto_id = item.get('producto_id')
            presentacion_id = item.get('presentacion_id')
            cantidad = item.get('cantidad', 1)
            precio_unitario = item.get('precio_unitario')
            descuento = item.get('descuento', 0)
            producto_nombre = item.get('producto_nombre')
            presentacion_nombre = item.get('presentacion_nombre')
            if producto_id is None or presentacion_id is None or precio_unitario is None:
                raise ValueError('Cada ítem requiere producto_id, presentacion_id y precio_unitario')
            ok = gestor.carrito.agregar_item(
                producto_id=int(producto_id),
                presentacion_id=int(presentacion_id),
                cantidad=int(cantidad),
                precio_unitario=float(precio_unitario),
                descuento=float(descuento),
                producto_nombre=producto_nombre,
                presentacion_nombre=presentacion_nombre,
            )
            if not ok:
                raise ValueError(f'No se pudo agregar el producto {producto_id} al carrito')

        venta = gestor.crear_venta(
            numero_ticket=gestor.generar_numero_ticket(),
            metodo_pago=str(datos.get('metodo_pago', 'efectivo')).lower(),
            usuario=str(datos.get('usuario', 'cajero')).strip() or 'cajero',
            notas=datos.get('notas'),
        )
        if not venta:
            return jsonify({'error': 'No se pudo procesar la venta'}), 400
        return jsonify({
            'success': True,
            'ticket': venta.numero_ticket,
            'total': float(venta.total),
            'metodo_pago': venta.metodo_pago,
            'usuario': venta.usuario,
            'items': len(venta.items),
        }), 201
    except Exception as e:
        logger.error(f'Error al procesar la venta: {e}')
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()

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
