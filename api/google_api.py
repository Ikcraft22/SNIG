"""
Módulo específico para Google Custom Search API.
Proporciona funciones avanzadas de búsqueda.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from config.settings import GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID

logger = logging.getLogger(__name__)

class GoogleSearchAPI:
    """Cliente para Google Custom Search API"""
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, api_key: str = GOOGLE_API_KEY, search_engine_id: str = GOOGLE_SEARCH_ENGINE_ID):
        """
        Inicializa el cliente de Google Search.
        
        Args:
            api_key: Clave API de Google
            search_engine_id: ID del motor de búsqueda personalizado
        """
        self.api_key = api_key
        self.search_engine_id = search_engine_id
    
    def validar_credenciales(self) -> bool:
        """Valida si las credenciales están configuradas"""
        if not self.api_key or not self.search_engine_id:
            logger.error("❌ Google API no está configurada correctamente")
            return False
        return True
    
    def buscar(
        self, 
        query: str, 
        num_results: int = 5,
        start_index: int = 1,
        search_type: str = "image"
    ) -> List[Dict[str, Any]]:
        """
        Realiza una búsqueda en Google.
        
        Args:
            query: Término de búsqueda
            num_results: Número de resultados (1-10)
            start_index: Índice de inicio para paginación
            search_type: Tipo de búsqueda ("web" o "image")
            
        Returns:
            Lista de resultados
        """
        if not self.validar_credenciales():
            return []
        
        try:
            params = {
                "q": query,
                "key": self.api_key,
                "cx": self.search_engine_id,
                "num": min(num_results, 10),
                "start": start_index
            }
            
            if search_type == "image":
                params["searchType"] = "image"
            
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                resultados = []
                
                for item in data.get("items", []):
                    resultado = {
                        "titulo": item.get("title", ""),
                        "enlace": item.get("link", ""),
                        "descripcion": item.get("snippet", ""),
                    }
                    
                    if search_type == "image":
                        resultado["imagen"] = item.get("image", {}).get("thumbnailLink", "")
                    
                    resultados.append(resultado)
                
                logger.info(f"✅ Búsqueda completada: {len(resultados)} resultados")
                return resultados
            else:
                error_data = response.json().get("error", {})
                logger.error(f"❌ Error en Google API ({response.status_code}): {error_data.get('message', 'Sin mensaje')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error al conectar con Google: {e}")
            return []
    
    def buscar_producto_imagen(self, gtin: str) -> Optional[str]:
        """
        Busca la imagen de un producto por GTIN.
        
        Args:
            gtin: Código GTIN del producto
            
        Returns:
            URL de la imagen o None
        """
        resultados = self.buscar(f"{gtin} medicamento", num_results=1, search_type="image")
        
        if resultados:
            return resultados[0].get("imagen")
        return None
    
    def buscar_informacion_producto(self, nombre: str) -> Dict[str, Any]:
        """
        Busca información detallada de un producto.
        
        Args:
            nombre: Nombre del medicamento
            
        Returns:
            Diccionario con información del producto
        """
        resultados = self.buscar(nombre, num_results=3)
        
        if resultados:
            return {
                "encontrado": True,
                "principal": resultados[0],
                "resultados_adicionales": resultados[1:],
                "total_resultados": len(resultados)
            }
        
        return {
            "encontrado": False,
            "mensaje": f"No se encontró información sobre: {nombre}"
        }


def obtener_cliente_google() -> GoogleSearchAPI:
    """Factory function para obtener cliente de Google"""
    return GoogleSearchAPI()


def buscar_producto_google(gtin: str) -> Optional[Dict[str, Any]]:
    """
    Función simplificada para buscar producto en Google.
    
    Args:
        gtin: Código GTIN del producto
        
    Returns:
        Información del producto o None
    """
    cliente = obtener_cliente_google()
    
    if not cliente.validar_credenciales():
        logger.warning("⚠️ Google API no configurada")
        return None
    
    resultados = cliente.buscar(f"{gtin} medicamento", num_results=1)
    
    if resultados:
        return resultados[0]
    return None
