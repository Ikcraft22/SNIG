"""
Módulo de Gestión de Inventario.
Maneja:
- Stock de productos
- Movimientos de inventario
- Alertas de stock bajo
- Reportes
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import (
    Producto, Presentacion, MovimientoInventario, VentaItem,
    EstadoMovimiento, TipoPresentacion
)
from api.gtin_lookup import GTINBuscador

logger = logging.getLogger(__name__)

class GestorInventario:
    """Gestor de inventario de medicamentos"""
    
    def __init__(self, db: Session):
        """
        Inicializa el gestor de inventario.
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.buscador = GTINBuscador()
    
    def registrar_producto(
        self,
        gtin: str,
        nombre: str,
        laboratorio: str = None,
        descripcion: str = None
    ) -> Optional[Producto]:
        """
        Registra un nuevo producto en el sistema.
        
        Args:
            gtin: Código GTIN del producto
            nombre: Nombre del producto
            laboratorio: Laboratorio fabricante
            descripcion: Descripción del producto
            
        Returns:
            Objeto Producto creado
        """
        try:
            # Verificar si ya existe
            producto_existente = self.db.query(Producto).filter(Producto.gtin == gtin).first()
            if producto_existente:
                logger.warning(f"⚠️ Producto ya existe: {gtin}")
                return producto_existente
            
            # Crear nuevo producto
            producto = Producto(
                gtin=gtin,
                nombre=nombre,
                laboratorio=laboratorio,
                descripcion=descripcion
            )
            
            self.db.add(producto)
            self.db.commit()
            self.db.refresh(producto)
            
            logger.info(f"✅ Producto registrado: {gtin} - {nombre}")
            return producto
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al registrar producto: {e}")
            return None
    
    def agregar_presentacion(
        self,
        producto_id: int,
        tipo_presentacion: str,
        cantidad: int,
        precio_unitario: float,
        precio_venta: float,
        stock_inicial: int = 0
    ) -> Optional[Presentacion]:
        """
        Agrega una presentación a un producto.
        
        Args:
            producto_id: ID del producto
            tipo_presentacion: Tipo de presentación (unidad, bolsa, botella)
            cantidad: Cantidad de unidades por envase
            precio_unitario: Precio de costo unitario
            precio_venta: Precio de venta
            stock_inicial: Stock inicial
            
        Returns:
            Objeto Presentacion creado
        """
        try:
            presentacion = Presentacion(
                producto_id=producto_id,
                tipo=TipoPresentacion(tipo_presentacion),
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                precio_venta=precio_venta,
                stock_actual=stock_inicial
            )
            
            self.db.add(presentacion)
            self.db.commit()
            self.db.refresh(presentacion)
            
            logger.info(f"✅ Presentación agregada: {tipo_presentacion} - Stock: {stock_inicial}")
            return presentacion
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al agregar presentación: {e}")
            return None
    
    def registrar_movimiento(
        self,
        producto_id: int,
        presentacion_id: int,
        tipo: str,
        cantidad: int,
        razon: str = None,
        usuario: str = "sistema",
        referencia: str = None
    ) -> Optional[MovimientoInventario]:
        """
        Registra un movimiento de inventario (entrada, salida, ajuste).
        
        Args:
            producto_id: ID del producto
            presentacion_id: ID de la presentación
            tipo: Tipo de movimiento (entrada, salida, ajuste, devolucion)
            cantidad: Cantidad movida
            razon: Razón del movimiento
            usuario: Usuario que realiza el movimiento
            referencia: Referencia externa (factura, remisión, etc.)
            
        Returns:
            Objeto MovimientoInventario creado
        """
        try:
            # Obtener presentación
            presentacion = self.db.query(Presentacion).filter(
                Presentacion.id == presentacion_id
            ).first()
            
            if not presentacion:
                logger.error(f"❌ Presentación no encontrada: {presentacion_id}")
                return None
            
            # Crear movimiento
            movimiento = MovimientoInventario(
                producto_id=producto_id,
                presentacion_id=presentacion_id,
                tipo_movimiento=EstadoMovimiento(tipo),
                cantidad=cantidad,
                razon=razon,
                usuario=usuario,
                referencia_externa=referencia
            )
            
            # Actualizar stock
            if tipo in ["entrada", "devolucion"]:
                presentacion.stock_actual += cantidad
            elif tipo == "salida":
                if presentacion.stock_actual < cantidad:
                    logger.error(f"❌ Stock insuficiente para {presentacion.tipo}")
                    return None
                presentacion.stock_actual -= cantidad
            elif tipo == "ajuste":
                # ajuste puede ser positivo o negativo
                presentacion.stock_actual += cantidad
            
            self.db.add(movimiento)
            self.db.commit()
            self.db.refresh(movimiento)
            
            logger.info(f"✅ Movimiento registrado: {tipo} - Cantidad: {cantidad}")
            return movimiento
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al registrar movimiento: {e}")
            return None
    
    def eliminar_producto(self, producto_id: int) -> bool:
        """Elimina un producto y sus datos relacionados del inventario."""
        try:
            producto = self.db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                logger.warning(f"⚠️ Producto no encontrado para eliminar: {producto_id}")
                return False

            self.db.query(VentaItem).filter(VentaItem.producto_id == producto_id).delete(synchronize_session=False)
            self.db.delete(producto)
            self.db.commit()
            logger.info(f"✅ Producto eliminado: {producto_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al eliminar producto: {e}")
            return False

    def obtener_producto_por_gtin(self, gtin: str) -> Optional[Producto]:
        """Obtiene un producto por su GTIN"""
        return self.db.query(Producto).filter(Producto.gtin == gtin).first()

    def obtener_productos(self) -> List[Producto]:
        """Obtiene todos los productos registrados"""
        return self.db.query(Producto).all()
    
    def obtener_stock(self, producto_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene el stock de todas las presentaciones de un producto.
        
        Args:
            producto_id: ID del producto
            
        Returns:
            Lista de diccionarios con información de stock
        """
        presentaciones = self.db.query(Presentacion).filter(
            Presentacion.producto_id == producto_id
        ).all()
        
        return [
            {
                "id": p.id,
                "tipo": p.tipo.value,
                "stock": p.stock_actual,
                "stock_minimo": p.stock_minimo,
                "alerta": p.stock_actual <= p.stock_minimo,
                "precio_venta": p.precio_venta
            }
            for p in presentaciones
        ]
    
    def obtener_productos_stock_bajo(self, umbral_porcentaje: float = 0.2) -> List[Dict[str, Any]]:
        """
        Obtiene productos con stock bajo.
        
        Args:
            umbral_porcentaje: Porcentaje del stock mínimo (0.2 = 20%)
            
        Returns:
            Lista de productos con stock bajo
        """
        presentaciones = self.db.query(Presentacion).all()
        
        productos_alerta = []
        for p in presentaciones:
            if p.stock_actual <= (p.stock_minimo * (1 - umbral_porcentaje)):
                producto = self.db.query(Producto).filter(
                    Producto.id == p.producto_id
                ).first()
                
                productos_alerta.append({
                    "producto_id": p.producto_id,
                    "gtin": producto.gtin,
                    "nombre": producto.nombre,
                    "presentacion": p.tipo.value,
                    "stock_actual": p.stock_actual,
                    "stock_minimo": p.stock_minimo,
                    "urgencia": "CRÍTICO" if p.stock_actual == 0 else "BAJO"
                })
        
        return productos_alerta
    
    def historial_movimientos(
        self,
        producto_id: int,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de movimientos de un producto.
        
        Args:
            producto_id: ID del producto
            limite: Número máximo de movimientos a retornar
            
        Returns:
            Lista de movimientos
        """
        movimientos = self.db.query(MovimientoInventario).filter(
            MovimientoInventario.producto_id == producto_id
        ).order_by(MovimientoInventario.fecha.desc()).limit(limite).all()
        
        return [
            {
                "fecha": m.fecha.isoformat(),
                "tipo": m.tipo_movimiento.value,
                "cantidad": m.cantidad,
                "razon": m.razon,
                "usuario": m.usuario,
                "referencia": m.referencia_externa
            }
            for m in movimientos
        ]
    
    def reporte_general(self) -> Dict[str, Any]:
        """Genera un reporte general del inventario"""
        productos = self.db.query(Producto).all()
        total_productos = len(productos)
        
        presentaciones = self.db.query(Presentacion).all()
        total_stock = sum(p.stock_actual for p in presentaciones)
        valor_inventario = sum(p.stock_actual * p.precio_unitario for p in presentaciones)
        
        productos_sin_stock = len([p for p in presentaciones if p.stock_actual == 0])
        
        return {
            "fecha": datetime.now().isoformat(),
            "total_productos": total_productos,
            "total_stock": total_stock,
            "valor_inventario": valor_inventario,
            "productos_sin_stock": productos_sin_stock,
            "productos_alerta": len(self.obtener_productos_stock_bajo())
        }
