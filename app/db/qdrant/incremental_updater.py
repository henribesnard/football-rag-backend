"""
Gestion des mises à jour incrémentielles des vecteurs dans Qdrant.
Permet de ne mettre à jour que les entités modifiées pour optimiser les performances.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.db.postgres.connection import get_db_session
from app.db.postgres.models import get_model_by_entity_type
from app.embedding.vectorize import get_embedding_for_entity
from .schema_converter import model_to_vector_payload
from .collections import get_collection_name
from .operations import upsert_vectors, delete_vectors

logger = logging.getLogger(__name__)

def get_updated_entities(
    entity_type: str,
    since_timestamp: Optional[datetime] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Récupère les entités de type donné qui ont été mises à jour depuis le timestamp fourni.
    
    Args:
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        since_timestamp: Date/heure à partir de laquelle rechercher les mises à jour
        limit: Nombre maximum d'entités à récupérer
        
    Returns:
        Liste des entités mises à jour avec leurs IDs et timestamps
    """
    # Si pas de timestamp fourni, utiliser 24h par défaut
    if not since_timestamp:
        since_timestamp = datetime.now() - timedelta(hours=24)
    
    # Récupérer la classe de modèle correspondant au type d'entité
    model_class = get_model_by_entity_type(entity_type)
    if not model_class:
        logger.error(f"Modèle introuvable pour {entity_type}")
        return []
    
    session = get_db_session()
    try:
        # Utiliser SQLAlchemy pour la requête
        entities = session.query(model_class.id, model_class.update_at)\
                         .filter(model_class.update_at >= since_timestamp)\
                         .order_by(model_class.update_at.desc())\
                         .limit(limit)\
                         .all()
        return [{"id": entity.id, "update_at": entity.update_at} for entity in entities]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des entités mises à jour pour {entity_type}: {str(e)}")
        return []
    finally:
        session.close()

async def update_entity_vectors(
    entity_type: str,
    entity_ids: List[int]
) -> bool:
    """
    Met à jour les vecteurs pour une liste d'entités dans Qdrant.
    
    Args:
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        entity_ids: Liste des IDs des entités à mettre à jour
        
    Returns:
        True si la mise à jour est réussie, False sinon
    """
    # Récupérer la classe de modèle correspondant au type d'entité
    model_class = get_model_by_entity_type(entity_type)
    
    if not model_class:
        logger.error(f"Classe de modèle introuvable pour {entity_type}")
        return False
    
    collection_name = get_collection_name(entity_type)
    
    # Récupérer les entités à mettre à jour
    session = get_db_session()
    try:
        entities = session.query(model_class).filter(model_class.id.in_(entity_ids)).all()
        
        if not entities:
            logger.warning(f"Aucune entité trouvée pour {entity_type} avec les IDs {entity_ids}")
            return True
        
        # Générer les vecteurs et préparer les points pour Qdrant
        points = []
        for entity in entities:
            # Générer le vecteur d'embedding
            vector = await get_embedding_for_entity(entity, entity_type)
            
            if vector:
                # Convertir en format Qdrant
                point = model_to_vector_payload(entity, entity_type, vector)
                points.append(point)
            else:
                logger.warning(f"Impossible de générer un vecteur pour {entity_type} ID {entity.id}")
        
        # Mettre à jour les vecteurs dans Qdrant
        if points:
            success = upsert_vectors(collection_name, points)
            if success:
                logger.info(f"{len(points)} vecteurs mis à jour dans {collection_name}")
            else:
                logger.error(f"Échec de la mise à jour des vecteurs dans {collection_name}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des vecteurs pour {entity_type}: {str(e)}")
        return False
    
    finally:
        session.close()

async def handle_deleted_entities(
    entity_type: str,
    entity_ids: List[int]
) -> bool:
    """
    Supprime les vecteurs des entités supprimées dans Qdrant.
    
    Args:
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        entity_ids: Liste des IDs des entités supprimées
        
    Returns:
        True si la suppression est réussie, False sinon
    """
    collection_name = get_collection_name(entity_type)
    
    try:
        success = delete_vectors(collection_name, entity_ids)
        if success:
            logger.info(f"{len(entity_ids)} vecteurs supprimés de {collection_name}")
        else:
            logger.error(f"Échec de la suppression des vecteurs dans {collection_name}")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la suppression des vecteurs pour {entity_type}: {str(e)}")
        return False