"""
Módulo de Gestión de Inventario.
Maneja:
- Stock de productos
- Movimientos de inventario
- Alertas de stock bajo
- Reportes
"""

import logging
import os
import shutil
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database.models import (
    Producto, Presentacion, MovimientoInventario, VentaItem,
    EstadoMovimiento, TipoPresentacion
)
from api.gtin_lookup import GTINBuscador
from config.settings import SQLITE_FILE, BASE_DIR

logger = logging.getLogger(__name__)

class GestorInventario:
    """Gestor de inventario general de productos"""
    
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
                precio_unitario=round(precio_unitario),
                precio_venta=round(precio_venta),
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

    def actualizar_producto(
        self,
        producto_id: int,
        gtin: str,
        nombre: str,
        laboratorio: Optional[str] = None,
        descripcion: Optional[str] = None,
        presentacion_id: Optional[int] = None,
        precio_venta: Optional[float] = None,
    ) -> bool:
        """Actualiza los datos de un producto y, opcionalmente, su precio de venta."""
        gtin = gtin.strip()
        nombre = nombre.strip()
        if not gtin or not nombre:
            logger.warning("⚠️ GTIN y nombre son obligatorios para actualizar el producto")
            return False
        if precio_venta is not None and round(precio_venta) <= 0:
            logger.warning("⚠️ El precio de venta debe ser mayor que cero")
            return False

        try:
            producto = self.db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                logger.warning(f"⚠️ Producto no encontrado para actualizar: {producto_id}")
                return False

            producto_existente = self.db.query(Producto).filter(
                Producto.gtin == gtin,
                Producto.id != producto_id
            ).first()
            if producto_existente:
                logger.warning(f"⚠️ GTIN ya registrado en otro producto: {gtin}")
                return False

            if precio_venta is not None:
                if presentacion_id is None:
                    logger.warning("⚠️ Se requiere una presentación para actualizar el precio")
                    return False
                presentacion = self.db.query(Presentacion).filter(
                    Presentacion.id == presentacion_id,
                    Presentacion.producto_id == producto_id
                ).first()
                if not presentacion:
                    logger.warning(
                        f"⚠️ Presentación {presentacion_id} no pertenece al producto {producto_id}"
                    )
                    return False
                presentacion.precio_venta = round(precio_venta)

            producto.gtin = gtin
            producto.nombre = nombre
            producto.laboratorio = laboratorio.strip() if laboratorio else None
            producto.descripcion = descripcion.strip() if descripcion else None
            self.db.commit()
            logger.info(f"✅ Producto actualizado: {producto_id} - {nombre}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error al actualizar producto: {e}")
            return False

    def obtener_producto_por_gtin(self, gtin: str) -> Optional[Producto]:
        """Obtiene un producto por su GTIN"""
        return self.db.query(Producto).filter(Producto.gtin == gtin).first()

    def obtener_productos(self) -> List[Producto]:
        """Obtiene todos los productos registrados"""
        return self.db.query(Producto).all()

    def buscar_productos(self, termino: str) -> List[Producto]:
        """
        Realiza una búsqueda inteligente e insensible a mayúsculas/minúsculas.
        Busca por nombre, GTIN, laboratorio o descripción.

        Args:
            termino: Texto de búsqueda

        Returns:
            Lista de productos que coinciden con el término
        """
        if not termino or not termino.strip():
            return self.obtener_productos()

        t = f"%{termino.strip()}%"
        return self.db.query(Producto).filter(
            or_(
                Producto.nombre.ilike(t),
                Producto.gtin.ilike(t),
                Producto.laboratorio.ilike(t),
                Producto.descripcion.ilike(t),
                Producto.principio_activo.ilike(t),
            )
        ).all()
    
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
            "valor_inventario": round(valor_inventario),
            "productos_sin_stock": productos_sin_stock,
            "productos_alerta": len(self.obtener_productos_stock_bajo())
        }

    def calcular_valor_inventario(self) -> Dict[str, Any]:
        """
        Calcula el valor total del inventario a precio de costo y venta,
        así como la ganancia y margen proyectado.
        """
        presentaciones = self.db.query(Presentacion).all()
        valor_costo_total = sum(p.stock_actual * p.precio_unitario for p in presentaciones)
        valor_venta_potencial = sum(p.stock_actual * p.precio_venta for p in presentaciones)
        ganancia_proyectada = valor_venta_potencial - valor_costo_total
        margen = round((ganancia_proyectada / valor_venta_potencial * 100), 2) if valor_venta_potencial > 0 else 0.0
        total_unidades = sum(p.stock_actual for p in presentaciones)

        return {
            "valor_costo_total": round(valor_costo_total),
            "valor_venta_potencial": round(valor_venta_potencial),
            "ganancia_proyectada": round(ganancia_proyectada),
            "margen_promedio_porcentaje": margen,
            "total_unidades": total_unidades,
            "total_presentaciones": len(presentaciones)
        }

    def obtener_sugerencias_reabastecimiento(self) -> List[Dict[str, Any]]:
        """
        Identifica productos cuyo stock actual está en o por debajo del mínimo,
        y calcula las unidades sugeridas a pedir.
        """
        presentaciones = self.db.query(Presentacion).all()
        sugerencias = []
        for p in presentaciones:
            if p.stock_actual <= p.stock_minimo:
                prod = self.db.query(Producto).filter(Producto.id == p.producto_id).first()
                if not prod:
                    continue
                deficit = p.stock_minimo - p.stock_actual
                unidades_sugeridas = max((p.stock_minimo * 2) - p.stock_actual, deficit + 5)
                sugerencias.append({
                    "producto_id": prod.id,
                    "presentacion_id": p.id,
                    "gtin": prod.gtin,
                    "nombre": prod.nombre,
                    "presentacion": p.tipo.value,
                    "stock_actual": p.stock_actual,
                    "stock_minimo": p.stock_minimo,
                    "unidades_sugeridas": unidades_sugeridas,
                    "costo_unitario": p.precio_unitario,
                    "inversion_estimada": round(unidades_sugeridas * p.precio_unitario)
                })
        return sugerencias

    def exportar_catalogo_csv(self, ruta_archivo: str) -> bool:
        """
        Exporta el catálogo completo de productos y presentaciones a un archivo CSV.
        """
        try:
            productos = self.db.query(Producto).all()
            with open(ruta_archivo, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "gtin", "nombre", "laboratorio", "descripcion",
                    "tipo_presentacion", "cantidad", "precio_costo",
                    "precio_venta", "stock_actual", "stock_minimo", "codigo_interno"
                ])
                for p in productos:
                    if p.presentaciones:
                        for pres in p.presentaciones:
                            writer.writerow([
                                p.gtin, p.nombre, p.laboratorio or "", p.descripcion or "",
                                pres.tipo.value, pres.cantidad, pres.precio_unitario,
                                pres.precio_venta, pres.stock_actual, pres.stock_minimo,
                                pres.codigo_interno or ""
                            ])
                    else:
                        writer.writerow([
                            p.gtin, p.nombre, p.laboratorio or "", p.descripcion or "",
                            "", "", "", "", "", "", ""
                        ])
            logger.info(f"✅ Catálogo exportado exitosamente a CSV: {ruta_archivo}")
            return True
        except Exception as e:
            logger.error(f"❌ Error al exportar catálogo CSV: {e}")
            return False

    def exportar_catalogo_excel(self, ruta_archivo: str) -> bool:
        """
        Exporta el catálogo completo de productos y presentaciones a un archivo Excel (.xlsx).
        """
        try:
            import pandas as pd
            productos = self.db.query(Producto).all()
            filas = []
            for p in productos:
                if p.presentaciones:
                    for pres in p.presentaciones:
                        filas.append({
                            "GTIN": p.gtin,
                            "Producto": p.nombre,
                            "Laboratorio / Marca": p.laboratorio or "",
                            "Descripción": p.descripcion or "",
                            "Presentación": pres.tipo.value,
                            "Unidades x Envase": pres.cantidad,
                            "Precio Costo": pres.precio_unitario,
                            "Precio Venta": pres.precio_venta,
                            "Stock Actual": pres.stock_actual,
                            "Stock Mínimo": pres.stock_minimo,
                            "Código Interno": pres.codigo_interno or ""
                        })
                else:
                    filas.append({
                        "GTIN": p.gtin,
                        "Producto": p.nombre,
                        "Laboratorio / Marca": p.laboratorio or "",
                        "Descripción": p.descripcion or "",
                        "Presentación": "",
                        "Unidades x Envase": "",
                        "Precio Costo": "",
                        "Precio Venta": "",
                        "Stock Actual": "",
                        "Stock Mínimo": "",
                        "Código Interno": ""
                    })
            df = pd.DataFrame(filas)
            df.to_excel(ruta_archivo, index=False)
            logger.info(f"✅ Catálogo exportado exitosamente a Excel: {ruta_archivo}")
            return True
        except Exception as e:
            logger.error(f"❌ Error al exportar catálogo Excel: {e}")
            return False

    def importar_catalogo_csv(self, ruta_archivo: str) -> Dict[str, Any]:
        """
        Importa productos y presentaciones desde un archivo CSV.
        """
        exitosos = 0
        errores = 0
        detalles_errores = []

        if not os.path.exists(ruta_archivo):
            return {"exitosos": 0, "errores": 1, "detalles_errores": ["Archivo no encontrado"]}

        try:
            with open(ruta_archivo, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for num_fila, row in enumerate(reader, start=2):
                    try:
                        gtin = row.get("gtin", "").strip()
                        nombre = row.get("nombre", "").strip()
                        if not gtin or not nombre:
                            errores += 1
                            detalles_errores.append(f"Fila {num_fila}: GTIN o nombre vacío")
                            continue

                        laboratorio = row.get("laboratorio", "").strip() or None
                        descripcion = row.get("descripcion", "").strip() or None

                        # Buscar o registrar producto
                        producto = self.obtener_producto_por_gtin(gtin)
                        if not producto:
                            producto = self.registrar_producto(
                                gtin=gtin,
                                nombre=nombre,
                                laboratorio=laboratorio,
                                descripcion=descripcion
                            )
                        else:
                            producto.nombre = nombre
                            if laboratorio:
                                producto.laboratorio = laboratorio
                            if descripcion:
                                producto.descripcion = descripcion
                            self.db.commit()

                        # Presentación
                        tipo_str = row.get("tipo_presentacion", "").strip().lower()
                        if tipo_str:
                            cantidad = int(row.get("cantidad", 1) or 1)
                            precio_costo = float(row.get("precio_costo", 0.0) or 0.0)
                            precio_venta = float(row.get("precio_venta", 0.0) or 0.0)
                            stock_actual = int(row.get("stock_actual", 0) or 0)
                            stock_minimo = int(row.get("stock_minimo", 10) or 10)
                            codigo_interno = row.get("codigo_interno", "").strip() or None

                            if tipo_str in [t.value for t in TipoPresentacion]:
                                pres_existente = self.db.query(Presentacion).filter(
                                    Presentacion.producto_id == producto.id,
                                    Presentacion.tipo == TipoPresentacion(tipo_str)
                                ).first()

                                if pres_existente:
                                    pres_existente.precio_unitario = round(precio_costo)
                                    pres_existente.precio_venta = round(precio_venta)
                                    pres_existente.stock_actual = stock_actual
                                    pres_existente.stock_minimo = stock_minimo
                                    if codigo_interno:
                                        pres_existente.codigo_interno = codigo_interno
                                else:
                                    self.agregar_presentacion(
                                        producto_id=producto.id,
                                        tipo_presentacion=tipo_str,
                                        cantidad=cantidad,
                                        precio_unitario=precio_costo,
                                        precio_venta=precio_venta,
                                        stock_inicial=stock_actual
                                    )
                                    if codigo_interno:
                                        nueva_pres = self.db.query(Presentacion).filter(
                                            Presentacion.producto_id == producto.id,
                                            Presentacion.tipo == TipoPresentacion(tipo_str)
                                        ).first()
                                        if nueva_pres:
                                            nueva_pres.codigo_interno = codigo_interno
                                self.db.commit()

                        exitosos += 1
                    except Exception as err_fila:
                        self.db.rollback()
                        errores += 1
                        detalles_errores.append(f"Fila {num_fila}: {err_fila}")

            return {
                "exitosos": exitosos,
                "errores": errores,
                "detalles_errores": detalles_errores
            }
        except Exception as e:
            logger.error(f"❌ Error al procesar archivo CSV: {e}")
            return {
                "exitosos": exitosos,
                "errores": errores + 1,
                "detalles_errores": [str(e)]
            }

    def crear_backup(self, sqlite_file_path: Optional[str] = None, backup_dir: Optional[str] = None) -> Optional[str]:
        """
        Crea una copia de seguridad con fecha y hora de la base de datos SQLite.
        """
        try:
            if sqlite_file_path is None:
                sqlite_file_path = os.getenv("SQLITE_FILE", "inventario.db")
                if not os.path.isabs(sqlite_file_path):
                    sqlite_file_path = os.path.join(BASE_DIR, sqlite_file_path)

            if not os.path.exists(sqlite_file_path):
                logger.error(f"❌ Archivo de BD no encontrado para backup: {sqlite_file_path}")
                return None

            if backup_dir is None:
                backup_dir = os.path.join(BASE_DIR, "backups")

            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_backup = f"backup_inventario_{timestamp}.db"
            destino = os.path.join(backup_dir, nombre_backup)

            shutil.copy2(sqlite_file_path, destino)
            logger.info(f"✅ Backup creado exitosamente: {destino}")
            return destino
        except Exception as e:
            logger.error(f"❌ Error al crear backup de la base de datos: {e}")
            return None

    def listar_backups(self, backup_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista las copias de seguridad disponibles ordenadas de más reciente a más antigua.
        """
        if backup_dir is None:
            backup_dir = os.path.join(BASE_DIR, "backups")

        if not os.path.exists(backup_dir):
            return []

        archivos = []
        for f in os.listdir(backup_dir):
            if f.endswith(".db"):
                ruta_completa = os.path.join(backup_dir, f)
                stat = os.stat(ruta_completa)
                archivos.append({
                    "archivo": f,
                    "ruta": ruta_completa,
                    "tamano_bytes": stat.st_size,
                    "tamano_kb": round(stat.st_size / 1024, 2),
                    "fecha": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        archivos.sort(key=lambda x: x["fecha"], reverse=True)
        return archivos

    def restaurar_backup(self, archivo_backup: str, sqlite_file_path: Optional[str] = None) -> bool:
        """
        Restaura la base de datos desde un archivo de respaldo.
        """
        try:
            if not os.path.exists(archivo_backup):
                logger.error(f"❌ Archivo de backup no existe: {archivo_backup}")
                return False

            if sqlite_file_path is None:
                sqlite_file_path = os.getenv("SQLITE_FILE", "inventario.db")
                if not os.path.isabs(sqlite_file_path):
                    sqlite_file_path = os.path.join(BASE_DIR, sqlite_file_path)

            shutil.copy2(archivo_backup, sqlite_file_path)
            logger.info(f"✅ Base de datos restaurada desde: {archivo_backup}")
            return True
        except Exception as e:
            logger.error(f"❌ Error al restaurar base de datos: {e}")
            return False
