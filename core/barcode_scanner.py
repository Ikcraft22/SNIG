"""
Módulo para escaneo y lectura de códigos de barras.
Soporta:
- Escaneo directo (teclado)
- Lectura de archivos
- Validación de GTIN
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class BarcodeLector:
    """Lector de códigos de barras"""
    
    # Patrones válidos de GTIN
    PATRON_GTIN_8 = r'^\d{8}$'
    PATRON_GTIN_12 = r'^\d{12}$'
    PATRON_GTIN_13 = r'^\d{13}$'
    PATRON_GTIN_14 = r'^\d{14}$'
    
    @staticmethod
    def validar_gtin(codigo: str) -> Tuple[bool, Optional[str]]:
        """
        Valida si el código es un GTIN válido.
        
        Args:
            codigo: Código a validar
            
        Returns:
            Tupla (es_válido, tipo_gtin)
        """
        codigo_limpio = codigo.strip()
        
        if re.match(BarcodeLector.PATRON_GTIN_8, codigo_limpio):
            return True, "GTIN-8"
        elif re.match(BarcodeLector.PATRON_GTIN_12, codigo_limpio):
            return True, "GTIN-12"
        elif re.match(BarcodeLector.PATRON_GTIN_13, codigo_limpio):
            return True, "GTIN-13"
        elif re.match(BarcodeLector.PATRON_GTIN_14, codigo_limpio):
            return True, "GTIN-14"
        
        return False, None
    
    @staticmethod
    def limpiar_codigo(codigo: str) -> str:
        """
        Limpia y normaliza un código de barras.
        
        Args:
            codigo: Código a limpiar
            
        Returns:
            Código normalizado
        """
        # Elimina espacios y caracteres especiales
        codigo_limpio = re.sub(r'[^\d]', '', codigo.strip())
        return codigo_limpio
    
    @staticmethod
    def verificar_digito(gtin: str) -> bool:
        """
        Verifica el dígito de control de un GTIN.
        Algoritmo estándar: suma ponderada mod 10
        
        Args:
            gtin: Código GTIN (sin dígito de control)
            
        Returns:
            True si es válido, False en caso contrario
        """
        if not gtin or len(gtin) < 8:
            return False
        
        # Extraer dígito de control (último dígito)
        digito_control = int(gtin[-1])
        codigo_sin_digito = gtin[:-1]
        
        # Calcular suma ponderada
        suma = 0
        peso = 3
        
        for i, digito in enumerate(reversed(codigo_sin_digito)):
            suma += int(digito) * peso
            peso = 3 if peso == 1 else 1
        
        digito_calculado = (10 - (suma % 10)) % 10
        
        return digito_control == digito_calculado
    
    @staticmethod
    def escanear_terminal() -> Optional[str]:
        """
        Lee un código de barras desde la terminal/teclado.
        
        Returns:
            Código de barras limpio o None
        """
        try:
            codigo = input("📱 Escanea el código de barras: ").strip()
            
            if not codigo:
                return None
            
            codigo_limpio = BarcodeLector.limpiar_codigo(codigo)
            es_valido, tipo = BarcodeLector.validar_gtin(codigo_limpio)
            
            if es_valido:
                logger.info(f"✅ Código válido ({tipo}): {codigo_limpio}")
                return codigo_limpio
            else:
                logger.warning(f"⚠️ Código inválido: {codigo_limpio}")
                return None
        
        except KeyboardInterrupt:
            logger.info("⏹️ Escaneo cancelado")
            return None
        except Exception as e:
            logger.error(f"❌ Error al escanear: {e}")
            return None
    
    @staticmethod
    def leer_archivo_codigos(ruta: str) -> list:
        """
        Lee múltiples códigos desde un archivo (uno por línea).
        
        Args:
            ruta: Ruta del archivo
            
        Returns:
            Lista de códigos válidos
        """
        codigos_validos = []
        
        try:
            with open(ruta, 'r') as archivo:
                for linea in archivo:
                    codigo = BarcodeLector.limpiar_codigo(linea)
                    es_valido, _ = BarcodeLector.validar_gtin(codigo)
                    
                    if es_valido:
                        codigos_validos.append(codigo)
                    else:
                        logger.warning(f"⚠️ Código inválido en archivo: {linea.strip()}")
            
            logger.info(f"✅ Se leyeron {len(codigos_validos)} códigos válidos")
            return codigos_validos
        
        except FileNotFoundError:
            logger.error(f"❌ Archivo no encontrado: {ruta}")
            return []
        except Exception as e:
            logger.error(f"❌ Error al leer archivo: {e}")
            return []


class EscanerProducto:
    """Clase simplificada para escaneo de productos"""
    
    def __init__(self):
        self.lector = BarcodeLector()
    
    def escanear(self) -> Optional[str]:
        """Escanea un producto y retorna el GTIN válido"""
        return self.lector.escanear_terminal()
    
    def validar(self, codigo: str) -> bool:
        """Valida un código"""
        es_valido, _ = self.lector.validar_gtin(self.lector.limpiar_codigo(codigo))
        return es_valido
