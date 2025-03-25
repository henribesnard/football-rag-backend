# app/db/qdrant/indexing.py
"""
Gestion des index de payload pour optimiser les requêtes de filtrage dans Qdrant.
"""
import logging
from typing import Dict, Any, List, Optional

from qdrant_client.http import models as rest
from .client import get_qdrant_client
from .collections import COLLECTIONS

logger = logging.getLogger(__name__)

def optimize_collection_indexes(collection_name: str) -> bool:
    """
    Optimise les index d'une collection Qdrant pour améliorer les performances.
    
    Args:
        collection_name: Nom de la collection
        
    Returns:
        True si l'optimisation est réussie, False sinon
    """
    client = get_qdrant_client()
    
    # Vérifier si la collection existe
    try:
        all_collections = client.get_collections().collections
        if collection_name not in [coll.name for coll in all_collections]:
            logger.error(f"Collection {collection_name} n'existe pas")
            return False
        
        # Déclencher l'optimisation des index
        client.update_collection(
            collection_name=collection_name,
            optimizers_config=rest.OptimizersConfigDiff(
                indexing_threshold=20000,  # Seuil pour déclencher l'indexation
                memmap_threshold=50000     # Seuil pour utiliser mmap
            )
        )
        
        # Récupérer la configuration de la collection
        collection_config = COLLECTIONS.get(collection_name, {})
        payload_schema = collection_config.get("payload_schema", {})
        
        # Créer ou mettre à jour les index de payload
        for field_name, field_type in payload_schema.items():
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                logger.info(f"Index créé/mis à jour pour {field_name} dans {collection_name}")
            except Exception as e:
                logger.warning(f"Impossible de créer l'index pour {field_name}: {str(e)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation des index pour {collection_name}: {str(e)}")
        return False

def get_collection_indexes(collection_name: str) -> List[Dict[str, Any]]:
    """
    Récupère la liste des index d'une collection Qdrant.
    
    Args:
        collection_name: Nom de la collection
        
    Returns:
        Liste des index configurés pour la collection
    """
    client = get_qdrant_client()
    
    try:
        collection_info = client.get_collection(collection_name)
        indexes = []
        
        for field_name, index_info in collection_info.payload_schema.items():
            indexes.append({
                "field_name": field_name,
                "field_schema": index_info.field_schema
            })
        
        return indexes
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des index pour {collection_name}: {str(e)}")
        return []

def optimize_all_collections() -> Dict[str, bool]:
    """
    Optimise les index de toutes les collections Qdrant.
    
    Returns:
        Dictionnaire avec le résultat pour chaque collection
    """
    client = get_qdrant_client()
    
    try:
        collections = client.get_collections().collections
        results = {}
        
        for collection in collections:
            collection_name = collection.name
            result = optimize_collection_indexes(collection_name)
            results[collection_name] = result
        
        return results
    
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation des collections: {str(e)}")
        return {}