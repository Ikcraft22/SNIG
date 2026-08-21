"""
Módulo de Gestión de Punto de Venta (POS).
Maneja:
- Carritos de compra
- Procesamiento de ventas
- Métodos de pago
- Generación de tickets
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import (
    Venta, VentaItem, Presentacion, Producto,
    EstadoVenta, MovimientoInventario, EstadoMovimiento
)

logger = logging.getLogger(__name__)

class CarritoCompra:
    """Carrito de compras temporal"""
    
    def __init__(self):
        """Inicializa un carrito vacío"""
        self.items = []
        self.subtotal = 0.0
        self.total = 0.0
    
    def agregar_item(
        self,
        producto_id: int,
        presentacion_id: int,
        cantidad: int,
        precio_unitario: float,
        descuento: float = 0.0,
        producto_nombre: str = None,
        presentacion_nombre: str = None
    ) -> bool:
        """
        Agrega un item al carrito.
        
        Args:
            producto_id: ID del producto
            presentacion_id: ID de la presentación
            cantidad: Cantidad a agregar
            precio_unitario: Precio unitario
            descuento: Descuento en porcentaje (0-100)
            
        Returns:
            True si se agregó exitosamente
        """
        if cantidad <= 0:
            logger.warning("⚠️ Cantidad debe ser mayor a 0")
            return False
        
        if descuento < 0 or descuento > 100:
            logger.warning("⚠️ Descuento debe estar entre 0 y 100")
            return False
        
        # Verificar si el producto ya está en el carrito
        for item in self.items:
            if item["presentacion_id"] == presentacion_id:
                item["cantidad"] += cantidad
                item["subtotal"] = item["cantidad"] * item["precio_unitario"] - item["descuento_cantidad"]
                self._recalcular()
                return True
        
        # Crear nuevo item
        subtotal_item = cantidad * precio_unitario
        descuento_cantidad = (subtotal_item * descuento) / 100
        subtotal_final = subtotal_item - descuento_cantidad
        
        item = {
            "producto_id": producto_id,
            "presentacion_id": presentacion_id,
            "producto_nombre": producto_nombre,
            "presentacion_nombre": presentacion_nombre,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "descuento_porcentaje": descuento,
            "descuento_cantidad": descuento_cantidad,
            "subtotal": subtotal_final
        }
        
        self.items.append(item)
        self._recalcular()
        
        logger.info(f"✅ Item agregado al carrito: {cantidad}x ${precio_unitario}")
        return True
    
    def eliminar_item(self, presentacion_id: int) -> bool:
        """Elimina un item del carrito"""
        for i, item in enumerate(self.items):
            if item["presentacion_id"] == presentacion_id:
                self.items.pop(i)
                self._recalcular()
                return True
        return False
    
    def vaciar_carrito(self):
        """Vacía el carrito completamente"""
        self.items = []
        self._recalcular()
        logger.info("✅ Carrito vaciado")
    
    def _recalcular(self):
        """Recalcula totales del carrito"""
        self.subtotal = sum(item["subtotal"] for item in self.items)
        self.total = self.subtotal
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene el resumen del carrito"""
        return {
            "cantidad_items": len(self.items),
            "cantidad_productos": sum(item["cantidad"] for item in self.items),
            "subtotal": round(self.subtotal, 2),
            "total": round(self.total, 2)
        }
    
    def obtener_items(self) -> List[Dict[str, Any]]:
        """Obtiene los items del carrito"""
        return self.items.copy()


class GestorPOS:
    """Gestor del Punto de Venta"""
    
    def __init__(self, db: Session):
        """
        Inicializa el gestor POS.
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.carrito = CarritoCompra()
        self.numero_ticket_contador = self._obtener_proximo_numero_ticket()
    
    def _obtener_proximo_numero_ticket(self) -> int:
        """Obtiene el próximo número de ticket"""
        ultima_venta = self.db.query(Venta).order_by(
            Venta.id.desc()
        ).first()
        
        if ultima_venta:
            # Extraer número del ticket y sumar 1
            numero_str = ultima_venta.numero_ticket.split("-")[-1]
            return int(numero_str) + 1
        return 1000
    
    def generar_numero_ticket(self) -> str:
        """Genera un número de ticket único"""
        numero = self.numero_ticket_contador
        self.numero_ticket_contador += 1
        return f"TK-{datetime.now().strftime('%Y%m%d')}-{numero:06d}"
    
    def crear_venta(
        self,
        numero_ticket: str,
        metodo_pago: str,
        usuario: str,
        notas: str = None
    ) -> Optional[Venta]:
        """
        Crea una venta a partir del carrito actual.
        
        Args:
            numero_ticket: Número único del ticket
            metodo_pago: Método de pago (efectivo, tarjeta, etc.)
            usuario: Usuario/cajero que realiza la venta
            notas: Notas adicionales
            
        Returns:
            Objeto Venta creado
        """
        if not self.carrito.items:
            logger.error("❌ El carrito está vacío")
            return None
        
        try:
            # Crear venta
            venta = Venta(
                numero_ticket=numero_ticket,
                subtotal=self.carrito.subtotal,
                total=self.carrito.total,
                metodo_pago=metodo_pago,
                usuario=usuario,
                notas=notas,
                estado=EstadoVenta.COMPLETADA
            )
            
            # Crear items de venta y actualizar stock
            for item in self.carrito.items:
                venta_item = VentaItem(
                    venta=venta,
                    producto_id=item["producto_id"],
                    presentacion_id=item["presentacion_id"],
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio_unitario"],
                    descuento=item["descuento_cantidad"],
                    subtotal=item["subtotal"]
                )
                venta.items.append(venta_item)
                
                # Registrar movimiento de inventario (salida)
                self._registrar_salida_inventario(
                    item["producto_id"],
                    item["presentacion_id"],
                    item["cantidad"],
                    usuario,
                    numero_ticket
                )
            
            self.db.add(venta)
            self.db.commit()
            self.db.refresh(venta)
            
            # Vaciar carrito después de crear la venta
            self.carrito.vaciar_carrito()
            
            logger.info(f"✅ Venta completada: {numero_ticket} - Total: ${venta.total}")
            return venta
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al crear venta: {e}")
            return None
    
    def _registrar_salida_inventario(
        self,
        producto_id: int,
        presentacion_id: int,
        cantidad: int,
        usuario: str,
        numero_ticket: str
    ):
        """Registra la salida de inventario por venta"""
        try:
            presentacion = self.db.query(Presentacion).filter(
                Presentacion.id == presentacion_id
            ).first()
            
            if presentacion:
                presentacion.stock_actual -= cantidad
                
                movimiento = MovimientoInventario(
                    producto_id=producto_id,
                    presentacion_id=presentacion_id,
                    tipo_movimiento=EstadoMovimiento.SALIDA,
                    cantidad=cantidad,
                    razon="Venta POS",
                    usuario=usuario,
                    referencia_externa=numero_ticket
                )
                
                self.db.add(movimiento)
        
        except Exception as e:
            logger.error(f"❌ Error al registrar salida de inventario: {e}")
    
    def obtener_venta(self, numero_ticket: str) -> Optional[Venta]:
        """Obtiene una venta por su número de ticket"""
        return self.db.query(Venta).filter(
            Venta.numero_ticket == numero_ticket
        ).first()
    
    def obtener_ventas_por_fecha(self, fecha: str) -> List[Dict[str, Any]]:
        """
        Obtiene ventas de una fecha específica.
        
        Args:
            fecha: Fecha en formato YYYY-MM-DD
            
        Returns:
            Lista de ventas
        """
        from datetime import date
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        
        ventas = self.db.query(Venta).filter(
            Venta.fecha >= datetime.combine(fecha_obj, datetime.min.time()),
            Venta.fecha < datetime.combine(fecha_obj, datetime.max.time())
        ).all()
        
        return [
            {
                "numero_ticket": v.numero_ticket,
                "total": v.total,
                "metodo_pago": v.metodo_pago,
                "usuario": v.usuario,
                "fecha": v.fecha.isoformat()
            }
            for v in ventas
        ]
    
    def reporte_ventas_diario(self, fecha: str) -> Dict[str, Any]:
        """Genera reporte de ventas del día"""
        ventas = self.db.query(Venta).filter(
            Venta.fecha >= datetime.strptime(fecha, "%Y-%m-%d")
        ).all()
        
        total_ventas = sum(v.total for v in ventas)
        cantidad_ventas = len(ventas)
        
        metodos_pago = {}
        for v in ventas:
            metodos_pago[v.metodo_pago] = metodos_pago.get(v.metodo_pago, 0) + v.total
        
        return {
            "fecha": fecha,
            "cantidad_ventas": cantidad_ventas,
            "total_ventas": round(total_ventas, 2),
            "promedio_venta": round(total_ventas / cantidad_ventas, 2) if cantidad_ventas > 0 else 0,
            "metodos_pago": {k: round(v, 2) for k, v in metodos_pago.items()}
        }
