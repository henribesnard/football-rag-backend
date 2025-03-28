"""Service de vérification de l'état de santé du système."""
import logging
from typing import Dict, Any, List
import time
import asyncio

from app.config import settings
from app.db.postgres.connection import get_db_session
from app.db.qdrant.client import get_qdrant_client

logger = logging.getLogger(__name__)

class HealthCheck:
    """Service de vérification de l'état de santé."""
    
    async def check_system_health(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé de tous les composants du système.
        
        Returns:
            État de santé du système
        """
        start_time = time.time()
        
        # Vérifier tous les services en parallèle
        db_task = asyncio.create_task(self.check_database())
        qdrant_task = asyncio.create_task(self.check_qdrant())
        cdc_task = asyncio.create_task(self.check_cdc())
        redis_task = asyncio.create_task(self.check_redis())
        
        # Attendre tous les résultats
        db_health = await db_task
        qdrant_health = await qdrant_task
        cdc_health = await cdc_task
        redis_health = await redis_task
        
        # Déterminer l'état global
        all_healthy = all([
            db_health["status"] == "healthy",
            qdrant_health["status"] == "healthy",
            cdc_health["status"] == "healthy",
            redis_health["status"] == "healthy"
        ])
        
        elapsed_time = time.time() - start_time
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": time.time(),
            "check_duration_ms": round(elapsed_time * 1000, 2),
            "services": {
                "database": db_health,
                "qdrant": qdrant_health,
                "cdc": cdc_health,
                "redis": redis_health
            }
        }
    
    async def check_database(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé de la base de données.
        
        Returns:
            État de santé de la base de données
        """
        start_time = time.time()
        
        try:
            # Exécuter une requête simple
            session = get_db_session()
            result = session.execute("SELECT 1").scalar()
            session.close()
            
            if result == 1:
                return {
                    "status": "healthy",
                    "response_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Résultat inattendu de la requête de test"
                }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la base de données: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_qdrant(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé de Qdrant.
        
        Returns:
            État de santé de Qdrant
        """
        start_time = time.time()
        
        try:
            # Vérifier la connexion à Qdrant
            client = get_qdrant_client()
            collections = client.get_collections()
            
            return {
                "status": "healthy",
                "collections_count": len(collections.collections),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de Qdrant: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_cdc(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé du système CDC.
        
        Returns:
            État de santé du CDC
        """
        try:
            # Récupérer le statut du CDC
            from app.cdc import get_cdc_manager
            cdc_manager = get_cdc_manager()
            status = cdc_manager.get_status()
            
            return {
                "status": "healthy" if status.get("running", False) else "stopped",
                "details": status
            }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du CDC: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé de Redis.
        
        Returns:
            État de santé de Redis
        """
        start_time = time.time()
        
        try:
            import redis
            from app.config import settings
            
            # Vérifier la connexion à Redis
            client = redis.Redis.from_url(
                settings.REDIS_URL, 
                password=settings.REDIS_PASSWORD,
                socket_connect_timeout=2
            )
            result = client.ping()
            
            if result:
                return {
                    "status": "healthy",
                    "response_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Ping Redis a échoué"
                }
        except ImportError:
            return {
                "status": "unknown",
                "error": "Package redis non installé"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de Redis: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Instance singleton pour utilisation dans toute l'application
health_check = HealthCheck()