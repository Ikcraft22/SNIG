"""
Módulo de búsqueda de GTIN usando múltiples APIs.
Intenta primero OpenFoodFacts (gratuita) y luego Google.
"""

import requests
import logging
from typing import Optional, Dict, Any
from config.settings import (
    OPENFOODFACTS_API_URL,
    GOOGLE_API_KEY,
    GOOGLE_SEARCH_ENGINE_ID
)

logger = logging.getLogger(__name__)

class GTINLookup:
    """Clase para buscar información de productos por GTIN"""
    
    @staticmethod
    def buscar_por_openfoodfacts(gtin: str) -> Optional[Dict[str, Any]]:
        """
        Busca información del producto en OpenFoodFacts (API gratuita).
        
        Args:
            gtin: Código GTIN del producto
            
        Returns:
            Diccionario con información del producto o None
        """
        try:
            url = f"{OPENFOODFACTS_API_URL}/product/{gtin}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:  # Producto encontrado
                    return {
                        "gtin": gtin,
                        "nombre": data.get("product", {}).get("product_name", "Desconocido"),
                        "marca": data.get("product", {}).get("brands", "Desconocida"),
                        "descripcion": data.get("product", {}).get("ingredients_text", ""),
                        "categoria": data.get("product", {}).get("categories", ""),
                        "fuente": "OpenFoodFacts",
                        "url": data.get("product", {}).get("url", "")
                    }
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Error al consultar OpenFoodFacts: {e}")
        
        return None
    
    @staticmethod
    def buscar_por_google(gtin: str) -> Optional[Dict[str, Any]]:
        """
        Busca información del producto en Google Custom Search.
        REQUIERE: GOOGLE_API_KEY y GOOGLE_SEARCH_ENGINE_ID configurados.
        
        Args:
            gtin: Código GTIN del producto
            
        Returns:
            Diccionario con información del producto o None
        """
        if not GOOGLE_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
            logger.warning("⚠️ Google API no configurada. Configure GOOGLE_API_KEY y GOOGLE_SEARCH_ENGINE_ID")
            return None
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": f"{gtin} medicamento",
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_SEARCH_ENGINE_ID,
                "num": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data and len(data["items"]) > 0:
                    item = data["items"][0]
                    return {
                        "gtin": gtin,
                        "nombre": item.get("title", "Desconocido"),
                        "descripcion": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "fuente": "Google Custom Search"
                    }
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Error al consultar Google: {e}")
        
        return None
    
    @staticmethod
    def buscar_gtin(gtin: str) -> Optional[Dict[str, Any]]:
        """
        Búsqueda combinada: Intenta OpenFoodFacts primero, luego Google.
        
        Args:
            gtin: Código GTIN del producto
            
        Returns:
            Diccionario con información del producto
        """
        # Intenta primero OpenFoodFacts (gratuita y sin límite de rate)
        resultado = GTINLookup.buscar_por_openfoodfacts(gtin)
        if resultado:
            logger.info(f"✅ Producto encontrado en OpenFoodFacts: {gtin}")
            return resultado
        
        # Si no encuentra, intenta Google
        resultado = GTINLookup.buscar_por_google(gtin)
        if resultado:
            logger.info(f"✅ Producto encontrado en Google: {gtin}")
            return resultado
        
        logger.warning(f"⚠️ Producto no encontrado: {gtin}")
        return None


class GTINBuscador:
    """Clase simplificada para búsquedas de GTIN"""
    
    def __init__(self):
        self.lookup = GTINLookup()
    
    def buscar(self, gtin: str) -> Dict[str, Any]:
        """Busca un producto por GTIN y retorna los datos"""
        resultado = self.lookup.buscar_gtin(gtin)
        
        if resultado:
            return {
                "encontrado": True,
                "datos": resultado
            }
        else:
            return {
                "encontrado": False,
                "datos": None,
                "mensaje": f"Producto con GTIN {gtin} no encontrado"
            }
