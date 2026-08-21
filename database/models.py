from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from datetime import datetime
import enum

# ============== ENUMS ==============
class TipoPresentacion(str, enum.Enum):
    UNIDAD = "unidad"
    BOLSA = "bolsa"
    BOTELLA = "botella"

class EstadoMovimiento(str, enum.Enum):
    ENTRADA = "entrada"
    SALIDA = "salida"
    AJUSTE = "ajuste"
    DEVOLUCION = "devolucion"

class EstadoVenta(str, enum.Enum):
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"

# ============== MODELOS ==============

class Producto(Base):
    """Modelo de Producto"""
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True)
    gtin = Column(String(20), unique=True, nullable=False, index=True)
    cum = Column(String(50), unique=True, nullable=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    descripcion = Column(Text)
    principio_activo = Column(String(255))
    laboratorio = Column(String(255))
    registro_sanitario = Column(String(100))
    
    # Relaciones
    presentaciones = relationship("Presentacion", back_populates="producto", cascade="all, delete-orphan")
    movimientos = relationship("MovimientoInventario", back_populates="producto", cascade="all, delete-orphan")
    ventas_items = relationship("VentaItem", back_populates="producto")
    
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Producto(gtin={self.gtin}, nombre={self.nombre})>"


class Presentacion(Base):
    """Modelo de Presentación (Unidad, Bolsa, Botella)."""
    __tablename__ = "presentaciones"
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tipo = Column(Enum(TipoPresentacion), nullable=False)
    cantidad = Column(Integer, default=1)  # Ej: 1 unidad por envase
    precio_unitario = Column(Float, nullable=False)
    precio_venta = Column(Float, nullable=False)
    stock_actual = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=10)
    codigo_interno = Column(String(50), unique=True, nullable=True)
    
    # Relaciones
    producto = relationship("Producto", back_populates="presentaciones")
    
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Presentacion(tipo={self.tipo}, stock={self.stock_actual})>"


class MovimientoInventario(Base):
    """Modelo de Movimiento de Inventario (Entrada, Salida, Ajuste)"""
    __tablename__ = "movimientos_inventario"
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    presentacion_id = Column(Integer, ForeignKey("presentaciones.id"), nullable=False)
    tipo_movimiento = Column(Enum(EstadoMovimiento), nullable=False)
    cantidad = Column(Integer, nullable=False)
    razon = Column(String(255))
    usuario = Column(String(100))
    referencia_externa = Column(String(100))  # Número de factura, remisión, etc.
    
    # Relaciones
    producto = relationship("Producto", back_populates="movimientos")
    
    fecha = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<MovimientoInventario(tipo={self.tipo_movimiento}, cantidad={self.cantidad})>"


class Venta(Base):
    """Modelo de Venta (Ticket de caja)"""
    __tablename__ = "ventas"
    
    id = Column(Integer, primary_key=True)
    numero_ticket = Column(String(50), unique=True, nullable=False, index=True)
    estado = Column(Enum(EstadoVenta), default=EstadoVenta.COMPLETADA)
    
    subtotal = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    
    metodo_pago = Column(String(50))  # "efectivo", "tarjeta", "transferencia"
    usuario = Column(String(100))
    notas = Column(Text)
    
    # Relaciones
    items = relationship("VentaItem", back_populates="venta", cascade="all, delete-orphan")
    
    fecha = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<Venta(numero={self.numero_ticket}, total={self.total})>"


class VentaItem(Base):
    """Modelo de Item en una Venta"""
    __tablename__ = "venta_items"
    
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    presentacion_id = Column(Integer, ForeignKey("presentaciones.id"), nullable=False)
    
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    descuento = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)
    
    # Relaciones
    venta = relationship("Venta", back_populates="items")
    producto = relationship("Producto", back_populates="ventas_items")
    
    def __repr__(self):
        return f"<VentaItem(cantidad={self.cantidad}, subtotal={self.subtotal})>"


class Usuario(Base):
    """Modelo de Usuario/Cajero"""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    rol = Column(String(50), default="cajero")  # "admin", "cajero", "inventario"
    activo = Column(Boolean, default=True)
    
    fecha_creacion = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<Usuario(nombre={self.nombre}, rol={self.rol})>"
