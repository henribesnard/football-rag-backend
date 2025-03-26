# app/services/indexation_service.py
"""
Service pour l'indexation des entités dans Qdrant.
Ce service gère l'indexation initiale et les mises à jour incrémentielles.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.db.postgres.connection import get_db_session
from app.db.postgres.models import get_model_by_entity_type, ENTITY_MODEL_MAP
from app.db.qdrant.collections import initialize_collections, get_collection_name
from app.db.qdrant.incremental_updater import update_entity_vectors, handle_deleted_entities
from app.embedding.vectorize import get_embedding_for_entity, batch_generate_embeddings

logger = logging.getLogger(__name__)

class IndexationService:
    """
    Service pour l'indexation des entités dans Qdrant.
    """
    
    @staticmethod
    async def index_entity(entity: Any, entity_type: str) -> bool:
        """
        Indexe une entité spécifique dans Qdrant.
        
        Args:
            entity: Instance de l'entité
            entity_type: Type d'entité
            
        Returns:
            True si l'indexation a réussi, False sinon
        """
        try:
            # Indexer l'entité
            return await update_entity_vectors(entity_type, [entity.id])
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation de {entity_type} (ID: {entity.id}): {str(e)}")
            return False
    
    @staticmethod
    async def index_entities_by_type(entity_type: str, limit: int = 1000, batch_size: int = 100) -> Dict[str, Any]:
        """
        Indexe toutes les entités d'un type spécifique.
        
        Args:
            entity_type: Type d'entité
            limit: Nombre maximum d'entités à indexer
            batch_size: Taille des lots pour l'indexation
            
        Returns:
            Dictionnaire avec les statistiques d'indexation
        """
        model_class = get_model_by_entity_type(entity_type)
        if not model_class:
            logger.error(f"Type d'entité inconnu: {entity_type}")
            return {"success": False, "message": f"Type d'entité inconnu: {entity_type}"}
        
        collection_name = get_collection_name(entity_type)
        
        session = get_db_session()
        try:
            # Récupérer les entités
            entities = session.query(model_class).limit(limit).all()
            total_entities = len(entities)
            
            if total_entities == 0:
                return {"success": True, "indexed": 0, "total": 0, "message": f"Aucune entité {entity_type} trouvée"}
            
            # Indexer par lots
            success_count = 0
            error_count = 0
            
            for i in range(0, total_entities, batch_size):
                batch = entities[i:i+batch_size]
                batch_ids = [entity.id for entity in batch]
                
                # Indexer le lot
                result = await update_entity_vectors(entity_type, batch_ids)
                
                if result:
                    success_count += len(batch)
                else:
                    error_count += len(batch)
                    
                # Log d'avancement
                logger.info(f"Progression indexation {entity_type}: {i+len(batch)}/{total_entities}")
            
            return {
                "success": error_count == 0,
                "indexed": success_count,
                "errors": error_count,
                "total": total_entities,
                "collection": collection_name,
                "message": f"Indexation terminée: {success_count} entités indexées, {error_count} erreurs"
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation des entités {entity_type}: {str(e)}")
            return {"success": False, "message": str(e)}
        
        finally:
            session.close()
    
    @staticmethod
    async def index_all_entities(batch_size: int = 100) -> Dict[str, Any]:
        """
        Indexe toutes les entités de tous les types.
        
        Args:
            batch_size: Taille des lots pour l'indexation
            
        Returns:
            Dictionnaire avec les statistiques d'indexation par type d'entité
        """
        # Initialiser les collections Qdrant
        initialize_collections()
        
        results = {}
        
        # Indexer chaque type d'entité
        for entity_type in ENTITY_MODEL_MAP.keys():
            logger.info(f"Démarrage de l'indexation des entités de type {entity_type}")
            result = await IndexationService.index_entities_by_type(entity_type, batch_size=batch_size)
            results[entity_type] = result
            
        return results
    
    @staticmethod
    async def incremental_update(
        since_hours: int = 24,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Met à jour l'index de manière incrémentielle pour les entités modifiées récemment.
        
        Args:
            since_hours: Nombre d'heures à remonter pour les mises à jour
            batch_size: Taille des lots pour l'indexation
            
        Returns:
            Dictionnaire avec les statistiques de mise à jour par type d'entité
        """
        since_timestamp = datetime.now() - timedelta(hours=since_hours)
        results = {}
        
        # Mettre à jour chaque type d'entité
        for entity_type in ENTITY_MODEL_MAP.keys():
            try:
                # Récupérer le modèle
                model_class = get_model_by_entity_type(entity_type)
                
                # Récupérer les entités mises à jour
                session = get_db_session()
                entities = session.query(model_class)\
                                 .filter(model_class.update_at >= since_timestamp)\
                                 .all()
                
                total_entities = len(entities)
                
                if total_entities == 0:
                    results[entity_type] = {"success": True, "updated": 0, "total": 0}
                    continue
                
                # Indexer par lots
                success_count = 0
                error_count = 0
                
                for i in range(0, total_entities, batch_size):
                    batch = entities[i:i+batch_size]
                    batch_ids = [entity.id for entity in batch]
                    
                    # Mettre à jour les vecteurs
                    result = await update_entity_vectors(entity_type, batch_ids)
                    
                    if result:
                        success_count += len(batch)
                    else:
                        error_count += len(batch)
                
                results[entity_type] = {
                    "success": error_count == 0,
                    "updated": success_count,
                    "errors": error_count,
                    "total": total_entities
                }
                
                session.close()
                
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour incrémentielle pour {entity_type}: {str(e)}")
                results[entity_type] = {"success": False, "error": str(e)}
        
        return results