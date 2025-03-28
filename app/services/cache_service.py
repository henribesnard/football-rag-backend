"""Service de mise en cache avec invalidation intelligente."""
import json
import hashlib
import logging
import redis
from typing import Dict, Any, Optional, List, Union
from datetime import timedelta

from app.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Service de mise en cache pour les requêtes fréquentes."""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            settings.REDIS_URL, password=settings.REDIS_PASSWORD, decode_responses=True
        )
        self.default_ttl = 300  # 5 minutes par défaut
        
    def get_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Génère une clé de cache cohérente basée sur les paramètres.
        
        Args:
            prefix: Préfixe pour la clé (ex: "search", "entity")
            params: Paramètres de la requête
            
        Returns:
            Clé de cache unique
        """
        # Trier les paramètres pour garantir la cohérence des clés
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params)
        
        # Générer un hash pour éviter les clés trop longues
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        
        return f"{prefix}:{param_hash}"
        
    async def get_cached(self, prefix: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Récupère une valeur du cache.
        
        Args:
            prefix: Préfixe pour la clé
            params: Paramètres de la requête
            
        Returns:
            Valeur mise en cache ou None
        """
        cache_key = self.get_cache_key(prefix, params)
        cached = self.redis_client.get(cache_key)
        
        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return json.loads(cached)
        
        logger.debug(f"Cache miss for {cache_key}")
        return None
        
    async def set_cached(self, prefix: str, params: Dict[str, Any], value: Any, ttl: int = None) -> bool:
        """
        Met une valeur en cache.
        
        Args:
            prefix: Préfixe pour la clé
            params: Paramètres de la requête
            value: Valeur à mettre en cache
            ttl: Durée de vie en secondes (None = valeur par défaut)
            
        Returns:
            True si mise en cache réussie
        """
        cache_key = self.get_cache_key(prefix, params)
        expiry = ttl if ttl is not None else self.default_ttl
        
        try:
            result = self.redis_client.set(
                cache_key, 
                json.dumps(value), 
                ex=expiry
            )
            logger.debug(f"Cached {cache_key} for {expiry} seconds")
            return bool(result)
        except Exception as e:
            logger.error(f"Error caching {cache_key}: {str(e)}")
            return False
            
    async def invalidate(self, prefix: str, params: Dict[str, Any] = None) -> int:
        """
        Invalide une ou plusieurs entrées du cache.
        
        Args:
            prefix: Préfixe pour la clé
            params: Paramètres spécifiques à invalider (None = tous les préfixes)
            
        Returns:
            Nombre d'entrées invalidées
        """
        try:
            if params:
                # Invalider une entrée spécifique
                cache_key = self.get_cache_key(prefix, params)
                result = self.redis_client.delete(cache_key)
                logger.debug(f"Invalidated cache key: {cache_key}")
                return result
            else:
                # Invalider tous les préfixes correspondants
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    result = self.redis_client.delete(*keys)
                    logger.debug(f"Invalidated {result} cache keys with prefix: {prefix}")
                    return result
                return 0
        except Exception as e:
            logger.error(f"Error invalidating cache for {prefix}: {str(e)}")
            return 0

# Instance singleton pour utilisation dans toute l'application
cache_service = CacheService()