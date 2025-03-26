"""
Processeur des événements CDC qui gère la transformation des données et l'ingestion vers Qdrant.
"""
import logging
import time
from typing import Dict, List, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.db.postgres.models import get_model_by_entity_type, model_to_dict
from app.db.postgres.connection import get_db_session
from app.embedding.vectorize import get_embedding_for_entity
from app.db.qdrant.operations import upsert_vectors, delete_vectors
from app.db.qdrant.collections import get_collection_name
from app.db.qdrant.schema_converter import model_to_vector_payload

logger = logging.getLogger(__name__)

class CDCProcessor:
    """
    Processeur des événements CDC pour transformation et ingestion vers Qdrant.
    """
    
    def __init__(self):
        """Initialise le processeur CDC."""
        # Pool d'exécuteurs pour les opérations parallèles
        self.executor = ThreadPoolExecutor(max_workers=10)
        # Event loop pour les opérations asynchrones
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        logger.info("Processeur CDC initialisé")
    
    async def process_batch(self, batch: List[Dict[str, Any]], category: str) -> None:
        """
        Traite un lot d'événements CDC de manière asynchrone.
        
        Args:
            batch: Liste des événements CDC à traiter
            category: Catégorie des modèles dans ce lot
        """
        logger.info(f"Traitement d'un lot de {len(batch)} événements de la catégorie {category}")
        
        # Regrouper les événements par table pour un traitement efficace
        events_by_table = {}
        for event in batch:
            table = event.get('table')
            if table:
                if table not in events_by_table:
                    events_by_table[table] = []
                events_by_table[table].append(event)
        
        # Traiter chaque table séparément
        for table, events in events_by_table.items():
            try:
                # Obtenir le modèle correspondant à la table
                model_name = settings.CDC_TABLE_MODEL_MAPPING.get(table)
                if not model_name:
                    logger.warning(f"Pas de modèle associé à la table {table}. Événements ignorés.")
                    continue
                
                # Obtenir la priorité du modèle
                model_priority = settings.CDC_MODEL_PRIORITY.get(model_name, 999)
                
                logger.info(f"Traitement de {len(events)} événements pour la table {table}, modèle {model_name}, priorité {model_priority}")
                
                # Traiter les événements pour cette table
                await self._process_table_events(table, model_name, events)
            
            except Exception as e:
                logger.error(f"Erreur lors du traitement des événements pour la table {table}: {str(e)}")
    
    async def _process_table_events(self, table: str, model_name: str, events: List[Dict[str, Any]]) -> None:
        """
        Traite les événements CDC pour une table spécifique.
        
        Args:
            table: Nom de la table
            model_name: Nom du modèle correspondant
            events: Liste des événements CDC pour cette table
        """
        # Séparer les événements par type d'opération
        create_update_events = []
        delete_events = []
        
        for event in events:
            operation = event.get('operation')
            if operation == 'd':
                delete_events.append(event)
            elif operation in ('c', 'u'):  # Create ou Update
                create_update_events.append(event)
            else:
                logger.warning(f"Opération inconnue {operation} pour l'événement {event.get('topic')}:{event.get('offset')}")
        
        # Traiter les suppressions
        if delete_events:
            await self._process_delete_events(table, model_name, delete_events)
        
        # Traiter les créations et mises à jour
        if create_update_events:
            await self._process_create_update_events(table, model_name, create_update_events)
    
    async def _process_delete_events(self, table: str, model_name: str, events: List[Dict[str, Any]]) -> None:
        """
        Traite les événements de suppression CDC.
        
        Args:
            table: Nom de la table
            model_name: Nom du modèle correspondant
            events: Liste des événements de suppression
        """
        collection_name = get_collection_name(model_name.lower())
        ids_to_delete = []
        
        # Extraire les IDs à supprimer
        for event in events:
            event_data = event.get('value', {})
            # Dans Debezium, l'ID se trouve généralement dans 'before' pour les suppressions
            before_data = event_data.get('before', {})
            entity_id = before_data.get('id')
            
            if entity_id:
                ids_to_delete.append(entity_id)
            else:
                logger.warning(f"Impossible de trouver l'ID dans l'événement de suppression: {event}")
        
        if ids_to_delete:
            # Supprimer les vecteurs de Qdrant
            logger.info(f"Suppression de {len(ids_to_delete)} vecteurs de la collection {collection_name}")
            success = delete_vectors(collection_name, ids_to_delete)
            
            if success:
                logger.info(f"Suppression réussie de {len(ids_to_delete)} vecteurs dans {collection_name}")
            else:
                logger.error(f"Échec de la suppression des vecteurs dans {collection_name}")
    
    async def _process_create_update_events(self, table: str, model_name: str, events: List[Dict[str, Any]]) -> None:
        """
        Traite les événements de création et mise à jour CDC.
        
        Args:
            table: Nom de la table
            model_name: Nom du modèle correspondant
            events: Liste des événements de création/mise à jour
        """
        # Obtenir le modèle SQLAlchemy
        model_class = get_model_by_entity_type(model_name.lower())
        if not model_class:
            logger.error(f"Modèle {model_name} non trouvé")
            return
        
        collection_name = get_collection_name(model_name.lower())
        
        # Extraire les IDs à mettre à jour
        entity_ids = []
        for event in events:
            event_data = event.get('value', {})
            # Pour les créations et mises à jour, l'ID se trouve dans 'after'
            after_data = event_data.get('after', {})
            entity_id = after_data.get('id')
            
            if entity_id:
                entity_ids.append(entity_id)
        
        if not entity_ids:
            logger.warning(f"Aucun ID valide trouvé dans les événements {model_name}")
            return
        
        # Récupérer les entités complètes depuis la base de données
        session = get_db_session()
        try:
            entities = session.query(model_class).filter(model_class.id.in_(entity_ids)).all()
            
            if not entities:
                logger.warning(f"Aucune entité {model_name} trouvée pour les IDs {entity_ids}")
                return
            
            # Préparer les points pour Qdrant
            points = []
            for entity in entities:
                # Générer le vecteur d'embedding pour l'entité
                vector = await get_embedding_for_entity(entity, model_name.lower())
                
                if vector:
                    # Convertir l'entité en format Qdrant
                    point = model_to_vector_payload(entity, model_name.lower(), vector)
                    points.append(point)
                else:
                    logger.warning(f"Impossible de générer un vecteur pour {model_name} ID {entity.id}")
            
            # Insérer/mettre à jour les vecteurs dans Qdrant
            if points:
                batch_size = settings.CDC_QDRANT_SETTINGS.get('upsert_batch_size', 100)
                
                # Traiter par lots pour les grandes quantités
                for i in range(0, len(points), batch_size):
                    batch_points = points[i:i+batch_size]
                    success = upsert_vectors(collection_name, batch_points)
                    
                    if success:
                        logger.info(f"Lot {i//batch_size + 1}/{(len(points)-1)//batch_size + 1} inséré avec succès dans {collection_name}")
                    else:
                        logger.error(f"Échec de l'insertion du lot {i//batch_size + 1}/{(len(points)-1)//batch_size + 1} dans {collection_name}")
                
                logger.info(f"Traitement terminé pour {len(points)} entités {model_name}")
            else:
                logger.warning(f"Aucun point valide généré pour les entités {model_name}")
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement des entités {model_name}: {str(e)}")
        finally:
            session.close()
    
    def run_batch_processor(self, batch: List[Dict[str, Any]], category: str) -> None:
        """
        Point d'entrée pour le traitement synchrone d'un lot d'événements.
        Cette méthode est appelée directement par le consommateur CDC.
        
        Args:
            batch: Liste des événements à traiter
            category: Catégorie des modèles dans ce lot
        """
        try:
            # Exécuter le traitement asynchrone dans l'event loop
            asyncio.run_coroutine_threadsafe(self.process_batch(batch, category), self.loop)
        except Exception as e:
            logger.error(f"Erreur lors du lancement du traitement du lot: {str(e)}")
    
    def shutdown(self) -> None:
        """Arrête proprement le processeur."""
        self.executor.shutdown(wait=True)
        self.loop.stop()
        logger.info("Processeur CDC arrêté")