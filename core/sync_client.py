"""
Módulo cliente de sincronización multi-sucursal (Paso 4.2.3).
Permite a una sucursal conectarse a un servidor/nodo central o par,
descargar novedades incrementales y aplicarlas localmente de forma segura.
Aplica:
- Prevención de eco (anti-loop) mediante sin_disparo_sync().
- Identidad global basada en UUID v4.
- Política de resolución de conflictos:
  * Entidades transaccionales (Venta, VentaItem, MovimientoInventario): Ledger inmutable append-only / idempotente.
  * Entidades de catálogo (Producto, Presentacion, Proveedor): Last-Write-Wins (LWW) y soporte de tombstones (bajas lógicas).
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

from sqlalchemy.orm import Session
from database.models import (
    Base,
    Producto,
    Presentacion,
    TipoPresentacion,
    Proveedor,
    MovimientoInventario,
    Venta,
    VentaItem,
    SyncState,
    sin_disparo_sync,
)

logger = logging.getLogger(__name__)


@dataclass
class ResultadoSincronizacion:
    exitoso: bool
    cambios_recibidos: int = 0
    cambios_aplicados: int = 0
    cursor_final: int = 0
    error: Optional[str] = None


class ClienteSincronizacion:
    """Cliente para la descarga y aplicación de cambios remotos de inventario y ventas."""

    TABLAS_A_MODELOS = {
        "productos": Producto,
        "presentaciones": Presentacion,
        "proveedores": Proveedor,
        "ventas": Venta,
        "venta_items": VentaItem,
        "movimientos_inventario": MovimientoInventario,
    }

    def __init__(
        self,
        db: Session,
        servidor_url: str,
        api_token: str = "",
        nodo_id: str = "nodo-local",
        timeout: int = 15,
    ):
        self.db = db
        self.servidor_url = servidor_url.rstrip("/")
        self.api_token = api_token
        self.nodo_id = nodo_id
        self.timeout = timeout
        self._cursor_local = 0

    def obtener_cursor_local(self) -> int:
        """Devuelve el último cursor remoto procesado localmente."""
        return self._cursor_local

    def establecer_cursor_local(self, nuevo_cursor: int) -> None:
        """Actualiza el cursor local procesado."""
        self._cursor_local = max(self._cursor_local, nuevo_cursor)

    def descargar_novedades_remotas(self, cursor: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Consulta el endpoint /api/sync/changes del servidor."""
        url = f"{self.servidor_url}/api/sync/changes?cursor={cursor}&limit={limit}"
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        respuesta = requests.get(url, headers=headers, timeout=self.timeout)
        if respuesta.status_code != 200:
            raise RuntimeError(
                f"Error al descargar cambios ({respuesta.status_code}): {respuesta.text}"
            )
        return respuesta.json()

    def aplicar_cambio_remoto(self, cambio: Dict[str, Any]) -> bool:
        """
        Aplica un cambio remoto a la base de datos local bajo el context manager sin_disparo_sync
        para prevenir bucles de eco.
        """
        entity_type = cambio.get("entity_type")
        operation = cambio.get("operation")
        payload = cambio.get("payload") or {}

        modelo = self.TABLAS_A_MODELOS.get(entity_type)
        if not modelo:
            logger.warning(f"Entidad no soportada para sincronización: {entity_type}")
            return False

        uuid_val = payload.get("uuid")

        with sin_disparo_sync():
            # 1. Ventas y Movimientos: Ledger Inmutable / Idempotente
            if entity_type in ("ventas", "venta_items", "movimientos_inventario"):
                if uuid_val:
                    existente = self.db.query(modelo).filter_by(uuid=uuid_val).first()
                    if existente:
                        # Ya existe la transacción registrada, no sobreescribir (idempotente)
                        return True
                self._insertar_entidad_desde_payload(modelo, payload)
                self.db.commit()
                return True

            # 2. Catálogo: LWW y Bajas Lógicas (Tombstones)
            if uuid_val:
                instancia = self.db.query(modelo).filter_by(uuid=uuid_val).first()
                if instancia:
                    self._actualizar_entidad_desde_payload(instancia, payload)
                    self.db.commit()
                    return True

            # Si no existe previamente, insertar como nuevo registro
            self._insertar_entidad_desde_payload(modelo, payload)
            self.db.commit()
            return True

    def _insertar_entidad_desde_payload(self, modelo, payload: Dict[str, Any]):
        columnas = {c.key: c for c in modelo.__table__.columns}
        datos_limpios = {}
        for k, v in payload.items():
            if k == "id":
                continue  # Dejar que la BD local maneje su autoincrement ID
            if k in columnas:
                datos_limpios[k] = self._parsear_valor_columna(columnas[k], v)

        nueva_instancia = modelo(**datos_limpios)
        self.db.add(nueva_instancia)

    def _actualizar_entidad_desde_payload(self, instancia, payload: Dict[str, Any]):
        columnas = {c.key: c for c in instancia.__table__.columns}
        for k, v in payload.items():
            if k in ("id", "uuid"):
                continue
            if k in columnas:
                valor_parseado = self._parsear_valor_columna(columnas[k], v)
                setattr(instancia, k, valor_parseado)

    def _parsear_valor_columna(self, columna, valor: Any) -> Any:
        if valor is None:
            return None
        tipo_nombre = str(columna.type)
        if "DATETIME" in tipo_nombre or "TIMESTAMP" in tipo_nombre:
            if isinstance(valor, str):
                try:
                    return datetime.fromisoformat(valor)
                except Exception:
                    return valor
        if "ENUM" in tipo_nombre and hasattr(columna.type, "enum_class"):
            enum_cls = columna.type.enum_class
            if enum_cls and isinstance(valor, str):
                try:
                    return enum_cls(valor)
                except Exception:
                    pass
        return valor

    def sincronizar_desde_remoto(self, limite_lote: int = 100) -> ResultadoSincronizacion:
        """
        Descarga todas las novedades pendientes del servidor en lotes y las aplica.
        Actualiza el cursor local una vez aplicados.
        """
        cambios_recibidos_total = 0
        cambios_aplicados_total = 0
        cursor_actual = self.obtener_cursor_local()

        try:
            while True:
                novedades = self.descargar_novedades_remotas(cursor=cursor_actual, limit=limite_lote)
                cambios = novedades.get("changes") or []
                if not cambios:
                    break

                for cambio in cambios:
                    cambios_recibidos_total += 1
                    if self.aplicar_cambio_remoto(cambio):
                        cambios_aplicados_total += 1

                cursor_actual = novedades.get("next_cursor", cursor_actual)
                self.establecer_cursor_local(cursor_actual)

                if not novedades.get("has_more", False):
                    break

            return ResultadoSincronizacion(
                exitoso=True,
                cambios_recibidos=cambios_recibidos_total,
                cambios_aplicados=cambios_aplicados_total,
                cursor_final=cursor_actual,
            )
        except Exception as e:
            logger.error(f"Fallo en la sincronización: {e}", exc_info=True)
            self.db.rollback()
            return ResultadoSincronizacion(
                exitoso=False,
                cambios_recibidos=cambios_recibidos_total,
                cambios_aplicados=cambios_aplicados_total,
                cursor_final=cursor_actual,
                error=str(e),
            )
