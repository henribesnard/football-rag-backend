# app/db/qdrant/monitoring.py
"""
Utilitaires pour surveiller la santé et les performances de Qdrant.
"""
import logging
from typing import Dict, Any, List, Optional
import time

from .client import get_qdrant_client
from .collections import COLLECTIONS

logger = logging.getLogger(__name__)

def get_collection_stats(collection_name: str) -> Dict[str, Any]:
    """
    Récupère les statistiques d'une collection Qdrant.
    
    Args:
        collection_name: Nom de la collection
        
    Returns:
        Dictionnaire contenant les statistiques de la collection
    """
    client = get_qdrant_client()
    
    try:
        collection_info = client.get_collection(collection_name)
        
        stats = {
            "name": collection_name,
            "vectors_count": collection_info.vectors_count,
            "points_count": collection_info.points_count,
            "segments_count": collection_info.segments_count,
            "status": collection_info.status,
            "vector_size": collection_info.config.params.vectors.size,
            "distance": collection_info.config.params.vectors.distance
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques pour {collection_name}: {str(e)}")
        return {
            "name": collection_name,
            "error": str(e),
            "status": "error"
        }

def get_all_collections_stats() -> List[Dict[str, Any]]:
    """
    Récupère les statistiques de toutes les collections Qdrant.
    
    Returns:
        Liste de dictionnaires contenant les statistiques de chaque collection
    """
    client = get_qdrant_client()
    
    try:
        collections_list = client.get_collections().collections
        collection_names = [coll.name for coll in collections_list]
        
        stats = []
        for name in collection_names:
            collection_stats = get_collection_stats(name)
            stats.append(collection_stats)
        
        return stats
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques des collections: {str(e)}")
        return []

def measure_search_latency(
    collection_name: str,
    num_queries: int = 10,
    vector_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Mesure la latence de recherche sur une collection Qdrant.
    
    Args:
        collection_name: Nom de la collection
        num_queries: Nombre de requêtes à exécuter
        vector_size: Taille du vecteur (si None, utilise la taille de la collection)
        
    Returns:
        Dictionnaire contenant les métriques de latence
    """
    client = get_qdrant_client()
    
    try:
        # Déterminer la taille du vecteur
        if vector_size is None:
            collection_info = client.get_collection(collection_name)
            vector_size = collection_info.config.params.vectors.size
        
        # Générer un vecteur aléatoire pour la recherche
        import numpy as np
        random_vector = np.random.rand(vector_size).tolist()
        
        # Mesurer le temps de recherche
        latencies = []
        for _ in range(num_queries):
            start_time = time.time()
            _ = client.search(
                collection_name=collection_name,
                query_vector=random_vector,
                limit=10
            )
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convertir en ms
            latencies.append(latency)
        
        # Calculer les statistiques
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        
        return {
            "collection_name": collection_name,
            "num_queries": num_queries,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "p95_latency_ms": p95_latency
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de la mesure de latence pour {collection_name}: {str(e)}")
        return {
            "collection_name": collection_name,
            "error": str(e)
        }

def check_qdrant_health() -> Dict[str, Any]:
    """
    Vérifie l'état de santé de Qdrant.
    
    Returns:
        Dictionnaire contenant l'état de santé
    """
    client = get_qdrant_client()
    
    try:
        start_time = time.time()
        collections = client.get_collections()
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convertir en ms
        
        return {
            "status": "healthy",
            "collections_count": len(collections.collections),
            "response_time_ms": response_time
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de l'état de santé de Qdrant: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }