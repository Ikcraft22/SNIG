import json
from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Boolean,
    event,
    insert,
    select,
    update,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
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

productos_proveedores = Table(
    "productos_proveedores",
    Base.metadata,
    Column("producto_id", Integer, ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True),
    Column("proveedor_id", Integer, ForeignKey("proveedores.id", ondelete="CASCADE"), primary_key=True),
)


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
    proveedores = relationship(
        "Proveedor", secondary=productos_proveedores, back_populates="productos"
    )
    
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Producto(gtin={self.gtin}, nombre={self.nombre})>"


class Proveedor(Base):
    """Proveedor de productos del inventario."""

    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False, index=True)
    contacto = Column(String(255))
    telefono = Column(String(50))
    email = Column(String(255))
    direccion = Column(Text)
    notas = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())

    productos = relationship(
        "Producto", secondary=productos_proveedores, back_populates="proveedores"
    )

    def __repr__(self):
        return f"<Proveedor(nombre={self.nombre}, activo={self.activo})>"


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
    presentacion = relationship("Presentacion")
    
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


class SyncState(Base):
    """Secuencia global que mantiene ordenadas las transacciones del feed de sync."""

    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True)
    last_sequence = Column(Integer, nullable=False, default=0)


class SyncChange(Base):
    """Cambio persistente disponible para clientes que consumen la API de sync."""

    __tablename__ = "sync_changes"

    id = Column(Integer, primary_key=True, autoincrement=False)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    operation = Column(String(10), nullable=False)
    payload = Column(Text, nullable=False)
    occurred_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


def serializar_entidad_sync(modelo, entidad, connection=None):
    """Convierte las columnas escalares de una entidad en un payload JSON seguro."""
    valores = None
    if connection is not None:
        primary_key = modelo.__mapper__.primary_key[0]
        entity_id = getattr(entidad, primary_key.key)
        row = connection.execute(
            select(modelo.__table__).where(primary_key == entity_id)
        ).mappings().one_or_none()
        if row is not None:
            valores = row

    payload = {}
    for columna in modelo.__table__.columns:
        valor = (
            valores[columna.key]
            if valores is not None
            else getattr(entidad, columna.key)
        )
        if isinstance(valor, PythonEnum):
            valor = valor.value
        elif isinstance(valor, datetime):
            valor = valor.isoformat()
        payload[columna.key] = valor
    return payload


def registrar_evento_sync(connection, entity_type, entity_id, operation, payload):
    """Inserta un cambio en la misma transacción que modifica la entidad."""
    dialect = connection.dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert

        seed = dialect_insert(SyncState).values(id=1, last_sequence=0).on_conflict_do_nothing(
            index_elements=["id"]
        )
    elif dialect == "mysql":
        from sqlalchemy.dialects.mysql import insert as dialect_insert

        seed = dialect_insert(SyncState).values(id=1, last_sequence=0).on_duplicate_key_update(
            id=SyncState.id
        )
    else:
        seed = insert(SyncState).values(id=1, last_sequence=0)
    connection.execute(seed)

    secuencia = connection.execute(
        select(SyncState.last_sequence)
        .where(SyncState.id == 1)
        .with_for_update()
    ).scalar_one()
    secuencia += 1
    connection.execute(
        update(SyncState)
        .where(SyncState.id == 1)
        .values(last_sequence=secuencia)
    )
    connection.execute(
        insert(SyncChange).values(
            id=secuencia,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=json.dumps(payload, ensure_ascii=False, allow_nan=False),
        )
    )


def _registrar_cambio_mapeado(mapper, connection, entidad, operation):
    modelo = mapper.class_
    primary_key = mapper.primary_key[0].key
    payload = serializar_entidad_sync(
        modelo,
        entidad,
        connection if operation == "upsert" else None,
    )
    registrar_evento_sync(
        connection,
        mapper.local_table.name,
        getattr(entidad, primary_key),
        operation,
        payload,
    )


def _registrar_alta_o_actualizacion(mapper, connection, entidad):
    _registrar_cambio_mapeado(mapper, connection, entidad, "upsert")


def _registrar_eliminacion(mapper, connection, entidad):
    _registrar_cambio_mapeado(mapper, connection, entidad, "delete")


for _modelo_sync in (Producto, Presentacion, MovimientoInventario, Venta, VentaItem):
    event.listen(_modelo_sync, "after_insert", _registrar_alta_o_actualizacion)
    event.listen(_modelo_sync, "after_update", _registrar_alta_o_actualizacion)
    event.listen(_modelo_sync, "after_delete", _registrar_eliminacion)
