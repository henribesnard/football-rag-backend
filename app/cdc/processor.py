"""
Processeur des événements CDC qui gère la transformation des données et l'ingestion vers Qdrant.
"""
import logging
import time
import os
from typing import Dict, List, Any, Optional, Set
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from app.config import settings
from app.db.postgres.models import get_model_by_entity_type, model_to_dict
from app.db.postgres.connection import get_db_session
from app.embedding.vectorize import get_embedding_for_entity, batch_generate_embeddings
from app.db.qdrant.operations import upsert_vectors, delete_vectors
from app.db.qdrant.collections import get_collection_name
from app.db.qdrant.schema_converter import model_to_vector_payload
from app.monitoring.metrics import metrics, timed
from app.utils.circuit_breaker import circuit
from app.utils.resilience import with_retry, Bulkhead

logger = logging.getLogger(__name__)

class CDCProcessor:
    """
    Processeur des événements CDC pour transformation et ingestion vers Qdrant.
    Fonctionnalités améliorées:
    - Priorisation dynamique des catégories
    - Mécanisme robuste de reprise après erreur
    - Traitement parallèle optimisé
    - Métriques détaillées
    """
    
    def __init__(self):
        """Initialise le processeur CDC."""
        # Pool d'exécuteurs pour les opérations parallèles
        self.executor = ThreadPoolExecutor(
            max_workers=settings.get("CDC_MAX_WORKERS", 10),
            thread_name_prefix="cdc-worker"
        )
        
        # Event loop pour les opérations asynchrones
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Configuration de priorisation
        self.priority_config = settings.CDC_MODEL_PRIORITY
        
        # Cache des dernières priorités dynamiques pour les catégories
        self.dynamic_priorities = {}
        self._priority_lock = threading.Lock()
        
        # Suivi des entités à traiter
        self.pending_entities = {}
        self._pending_lock = threading.Lock()
        
        # Journal des erreurs pour la reprise
        self.error_log = {}
        self._error_log_lock = threading.Lock()
        
        # Limites de concurrence par catégorie (pattern Bulkhead)
        self.bulkheads = {}
        for category in settings.CDC_MODEL_CATEGORIES.keys():
            max_concurrent = settings.get(f"CDC_CONCURRENCY_{category.upper()}", 5)
            self.bulkheads[category] = Bulkhead(
                name=f"cdc-{category}",
                max_concurrent=max_concurrent
            )
        
        # Initialiser les métriques
        self._initialize_metrics()
        
        logger.info("Processeur CDC initialisé")
    
    def _initialize_metrics(self):
        """Initialise les métriques pour le monitoring."""
        # Compteurs d'événements traités
        self.processed_counter = metrics.counter(
            "cdc_processed_total",
            "Nombre total d'événements CDC traités"
        )
        self.success_counter = metrics.counter(
            "cdc_success_total",
            "Nombre total d'événements CDC traités avec succès"
        )
        self.error_counter = metrics.counter(
            "cdc_error_total",
            "Nombre total d'erreurs lors du traitement"
        )
        self.retry_counter = metrics.counter(
            "cdc_retry_total",
            "Nombre total de réessais"
        )
        
        # Histogrammes pour les temps de traitement
        self.processing_time = metrics.histogram(
            "cdc_processor_time",
            "Temps de traitement global (secondes)",
            buckets=[0.01, 0.1, 0.5, 1, 5, 10, 30, 60, 120]
        )
        
        # Histogrammes et compteurs par type d'opération
        for op_type in ['create', 'update', 'delete']:
            setattr(self, f"{op_type}_counter", metrics.counter(
                f"cdc_{op_type}_total",
                f"Nombre total d'opérations {op_type}"
            ))
            setattr(self, f"{op_type}_time", metrics.histogram(
                f"cdc_{op_type}_time",
                f"Temps de traitement des opérations {op_type} (secondes)",
                buckets=[0.01, 0.1, 0.5, 1, 5, 10, 30, 60]
            ))
        
        # Métriques par catégorie
        self.category_counters = {}
        self.category_times = {}
        
        for category in settings.CDC_MODEL_CATEGORIES.keys():
            self.category_counters[category] = metrics.counter(
                f"cdc_processed_{category}_total",
                f"Nombre total d'événements traités pour la catégorie {category}"
            )
            self.category_times[category] = metrics.histogram(
                f"cdc_processing_time_{category}",
                f"Temps de traitement pour la catégorie {category} (secondes)",
                buckets=[0.01, 0.1, 0.5, 1, 5, 10, 30, 60]
            )
    
    def update_dynamic_priorities(self):
        """
        Met à jour les priorités dynamiques des catégories en fonction de la charge et de l'importance.
        Cela permet d'ajuster la priorisation des catégories en temps réel.
        """
        with self._priority_lock:
            # Base: priorités statiques
            priorities = self.priority_config.copy()
            
            # Facteurs d'ajustement
            pending_factor = 0.3  # Influence du nombre d'entités en attente
            error_factor = 0.4   # Influence du nombre d'erreurs
            time_factor = 0.3    # Influence du temps écoulé depuis le dernier traitement
            
            for category in settings.CDC_MODEL_CATEGORIES.keys():
                base_priority = priorities.get(category, 5)  # Priorité par défaut: 5
                # Nombre d'entités en attente (plus il y en a, plus la priorité augmente)

                pending_count = len(self.pending_entities.get(category, {}))
                pending_boost = min(pending_count / 10, 5)  # Max +5 boost
                
                # Nombre d'erreurs (plus il y en a, plus la priorité augmente)
                error_count = len([e for e in self.error_log.values() if e.get('category') == category])
                error_boost = min(error_count, 3)  # Max +3 boost
                
                # Temps écoulé depuis le dernier traitement réussi
                last_processed = self.dynamic_priorities.get(f"{category}_last_processed", 0)
                current_time = time.time()
                time_since_last = current_time - last_processed
                time_boost = min(time_since_last / 60, 4)  # Max +4 boost (après 4 minutes)
                
                # Calculer la priorité dynamique
                dynamic_priority = (
                    base_priority +
                    (pending_boost * pending_factor) +
                    (error_boost * error_factor) +
                    (time_boost * time_factor)
                )
                
                # Mettre à jour la priorité dynamique
                self.dynamic_priorities[category] = dynamic_priority
                
                # Logger les changements significatifs
                if abs(dynamic_priority - base_priority) > 2:
                    logger.info(f"Priorité de la catégorie {category} ajustée: {base_priority} → {dynamic_priority:.1f}")
    
    async def process_batch(self, batch: List[Dict[str, Any]], category: str) -> None:
        """
        Traite un lot d'événements CDC de manière asynchrone.
        
        Args:
            batch: Liste des événements CDC à traiter
            category: Catégorie des modèles dans ce lot
        """
        if not batch:
            return
        
        # Mettre à jour les priorités dynamiques
        self.update_dynamic_priorities()
        
        # Marquer le début du traitement pour cette catégorie
        self.dynamic_priorities[f"{category}_last_processed"] = time.time()
        
        # Mesurer le temps de traitement
        start_time = time.time()
        
        # Incrémenter le compteur de traitement
        self.processed_counter.inc(len(batch))
        self.category_counters[category].inc(len(batch))
        
        logger.info(f"Traitement d'un lot de {len(batch)} événements de la catégorie {category}")
        
        try:
            # Regrouper les événements par table pour un traitement efficace
            events_by_table = {}
            for event in batch:
                table = event.get('table')
                if table:
                    if table not in events_by_table:
                        events_by_table[table] = []
                    events_by_table[table].append(event)
            
            # Traiter chaque table en fonction de sa priorité
            tables_by_priority = self._sort_tables_by_priority(events_by_table.keys(), category)
            
            # Traiter les tables de manière séquentielle par ordre de priorité
            for table in tables_by_priority:
                events = events_by_table.get(table, [])
                if events:
                    await self._process_table_events(table, events, category)
            
            # Mesurer le temps de traitement
            elapsed_time = time.time() - start_time
            self.processing_time.observe(elapsed_time)
            self.category_times[category].observe(elapsed_time)
            
            logger.info(f"Lot de {len(batch)} événements de la catégorie {category} traité en {elapsed_time:.2f}s")
            
            # Incrémenter le compteur de succès
            self.success_counter.inc(len(batch))
            
        except Exception as e:
            # Mesurer le temps même en cas d'erreur
            elapsed_time = time.time() - start_time
            self.processing_time.observe(elapsed_time)
            self.category_times[category].observe(elapsed_time)
            
            # Incrémenter le compteur d'erreurs
            self.error_counter.inc()
            
            logger.error(f"Erreur lors du traitement du lot pour la catégorie {category}: {str(e)}")
            
            # Stocker les événements en erreur pour réessai
            self._store_failed_events(batch, category, str(e))
            raise
    
    def _sort_tables_by_priority(self, tables: List[str], category: str) -> List[str]:
        """
        Trie les tables par priorité pour optimiser l'ordre de traitement.
        
        Args:
            tables: Liste des tables à trier
            category: Catégorie des modèles
            
        Returns:
            Liste des tables triées par priorité
        """
        # Convertir les tables en modèles
        table_model_map = {}
        for table in tables:
            model_name = settings.CDC_TABLE_MODEL_MAPPING.get(table)
            if model_name:
                table_model_map[table] = model_name
        
        # Trier les tables en fonction de la priorité des modèles
        def get_priority(table):
            model_name = table_model_map.get(table)
            if not model_name:
                return 999  # Priorité la plus basse pour les tables inconnues
            
            base_priority = self.priority_config.get(model_name, 5)
            
            # Appliquer les priorités dynamiques
            if category in self.dynamic_priorities:
                # Ajuster la priorité en fonction de la catégorie
                category_boost = self.dynamic_priorities[category] - sum(self.priority_config.values()) / len(self.priority_config)
                return base_priority - (category_boost / 10)  # Effet plus subtil
            
            return base_priority
        
        return sorted(tables, key=get_priority)
    
    async def _process_table_events(self, table: str, events: List[Dict[str, Any]], category: str) -> None:
        """
        Traite les événements CDC pour une table spécifique.
        
        Args:
            table: Nom de la table
            events: Liste des événements CDC pour cette table
            category: Catégorie des modèles
        """
        if not events:
            return
        
        # Obtenir le nom du modèle correspondant à la table
        model_name = settings.CDC_TABLE_MODEL_MAPPING.get(table)
        if not model_name:
            logger.warning(f"Pas de modèle associé à la table {table}. Événements ignorés.")
            return
        
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
        
        # Utiliser le Bulkhead pour limiter la concurrence
        async with self.bulkheads[category].execute():
            # Traiter les suppressions
            if delete_events:
                await self._process_delete_events(table, model_name, delete_events, category)
            
            # Traiter les créations et mises à jour
            if create_update_events:
                await self._process_create_update_events(table, model_name, create_update_events, category)
    
    @timed("cdc_delete_time", "Temps pour traiter les événements de suppression")
    async def _process_delete_events(
        self, 
        table: str, 
        model_name: str, 
        events: List[Dict[str, Any]], 
        category: str
    ) -> None:
        """
        Traite les événements de suppression CDC.
        
        Args:
            table: Nom de la table
            model_name: Nom du modèle correspondant
            events: Liste des événements de suppression
            category: Catégorie des modèles
        """
        # Incrémenter le compteur de suppressions
        self.delete_counter.inc(len(events))
        
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
            # Utiliser le retry pour plus de résilience
            try:
                await with_retry(
                    lambda: delete_vectors(collection_name, ids_to_delete),
                    retries=3,
                    delay=1.0,
                    backoff_factor=2.0,
                    jitter=0.1
                )
                
                logger.info(f"Suppression réussie de {len(ids_to_delete)} vecteurs dans {collection_name}")
                
                # Nettoyer ces IDs des entités en attente
                self._remove_from_pending_entities(ids_to_delete, model_name)
                
            except Exception as e:
                logger.error(f"Échec de la suppression des vecteurs dans {collection_name}: {str(e)}")
                
                # Stocker les événements en erreur pour réessai
                self._store_failed_delete_events(events, model_name, category, str(e))
                raise
    
    @timed("cdc_create_update_time", "Temps pour traiter les événements de création/mise à jour")
    async def _process_create_update_events(
        self, 
        table: str, 
        model_name: str, 
        events: List[Dict[str, Any]], 
        category: str
    ) -> None:
        """
        Traite les événements de création et mise à jour CDC.
        
        Args:
            table: Nom de la table
            model_name: Nom du modèle correspondant
            events: Liste des événements de création/mise à jour
            category: Catégorie des modèles
        """
        # Incrémenter les compteurs appropriés
        create_count = sum(1 for e in events if e.get('operation') == 'c')
        update_count = sum(1 for e in events if e.get('operation') == 'u')
        
        if create_count > 0:
            self.create_counter.inc(create_count)
        
        if update_count > 0:
            self.update_counter.inc(update_count)
        
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
                
                # Ajouter à la liste des entités en attente
                self._add_to_pending_entities(entity_id, model_name, category)
        
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
            
            # Utiliser l'approche par lots pour la vectorisation
            points = await self._create_vector_points_batch(entities, model_name.lower())
            
            # Insérer/mettre à jour les vecteurs dans Qdrant
            if points:
                batch_size = settings.get("CDC_QDRANT_BATCH_SIZE", 100)
                
                # Traiter par lots pour les grandes quantités
                for i in range(0, len(points), batch_size):
                    batch_points = points[i:i+batch_size]
                    
                    # Utiliser le retry pour plus de résilience
                    try:
                        await with_retry(
                            lambda: upsert_vectors(collection_name, batch_points),
                            retries=3,
                            delay=1.0,
                            backoff_factor=2.0,
                            jitter=0.1
                        )
                        
                        logger.info(f"Lot {i//batch_size + 1}/{(len(points)-1)//batch_size + 1} inséré avec succès dans {collection_name}")
                        
                        # Supprimer ces IDs des entités en attente
                        processed_ids = [point["id"] for point in batch_points]
                        self._remove_from_pending_entities(processed_ids, model_name)
                        
                    except Exception as e:
                        logger.error(f"Échec de l'insertion du lot {i//batch_size + 1}/{(len(points)-1)//batch_size + 1} dans {collection_name}: {str(e)}")
                        
                        # Stocker les entités en erreur pour réessai
                        affected_ids = [point["id"] for point in batch_points]
                        affected_entities = [e for e in entities if e.id in affected_ids]
                        
                        self._store_failed_entities(affected_entities, model_name, category, str(e))
                        raise
                
                logger.info(f"Traitement terminé pour {len(points)} entités {model_name}")
            else:
                logger.warning(f"Aucun point valide généré pour les entités {model_name}")
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement des entités {model_name}: {str(e)}")
            raise
        
        finally:
            session.close()
    
    async def _create_vector_points_batch(self, entities: List[Any], entity_type: str) -> List[Dict[str, Any]]:
        """
        Crée des points vectoriels pour un lot d'entités de manière optimisée.
        
        Args:
            entities: Liste d'entités
            entity_type: Type des entités
            
        Returns:
            Liste des points vectoriels
        """
        if not entities:
            return []
        
        # Préparer les textes pour la vectorisation par lots
        entities_dict = {}
        for entity in entities:
            entities_dict[entity.id] = entity
        
        # Vectoriser par lots avec l'approach optimisée
        try:
            # Extraire les IDs
            entity_ids = list(entities_dict.keys())
            
            # Générer les vecteurs d'embedding en mode optimisé par lots
            vectors_by_id = await batch_generate_embeddings(entities_dict, entity_type)
            
            # Préparer les points pour Qdrant
            points = []
            for entity_id, vector in vectors_by_id.items():
                entity = entities_dict.get(entity_id)
                if entity and vector:
                    # Convertir l'entité en format Qdrant
                    point = model_to_vector_payload(entity, entity_type, vector)
                    points.append(point)
                elif entity:
                    logger.warning(f"Impossible de générer un vecteur pour {entity_type} ID {entity_id}")
            
            return points
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération vectorielle par lots pour {entity_type}: {str(e)}")
            
            # En cas d'erreur, revenir à l'approche séquentielle plus fiable
            logger.info(f"Retour à la vectorisation séquentielle pour {len(entities)} entités")
            
            points = []
            for entity in entities:
                try:
                    # Générer le vecteur d'embedding
                    vector = await get_embedding_for_entity(entity, entity_type)
                    
                    if vector:
                        # Convertir en format Qdrant
                        point = model_to_vector_payload(entity, entity_type, vector)
                        points.append(point)
                    else:
                        logger.warning(f"Impossible de générer un vecteur pour {entity_type} ID {entity.id}")
                except Exception as e:
                    logger.error(f"Erreur lors de la génération d'un vecteur pour {entity_type} ID {entity.id}: {str(e)}")
            
            return points
    
    def _add_to_pending_entities(self, entity_id: int, model_name: str, category: str) -> None:
        """
        Ajoute une entité à la liste des entités en attente de traitement.
        
        Args:
            entity_id: ID de l'entité
            model_name: Nom du modèle
            category: Catégorie des modèles
        """
        with self._pending_lock:
            if category not in self.pending_entities:
                self.pending_entities[category] = {}
            
            self.pending_entities[category][f"{model_name}:{entity_id}"] = {
                "id": entity_id,
                "model": model_name,
                "timestamp": time.time()
            }
    
    def _remove_from_pending_entities(self, entity_ids: List[int], model_name: str) -> None:
        """
        Supprime des entités de la liste des entités en attente.
        
        Args:
            entity_ids: Liste des IDs d'entités
            model_name: Nom du modèle
        """
        with self._pending_lock:
            for category, entities in self.pending_entities.items():
                for entity_id in entity_ids:
                    key = f"{model_name}:{entity_id}"
                    if key in entities:
                        del entities[key]
    
    def _store_failed_entities(
        self, 
        entities: List[Any], 
        model_name: str, 
        category: str, 
        error: str
    ) -> None:
        """
        Stocke les entités qui ont échoué pour un réessai ultérieur.
        
        Args:
            entities: Liste des entités
            model_name: Nom du modèle
            category: Catégorie des modèles
            error: Message d'erreur
        """
        with self._error_log_lock:
            for entity in entities:
                error_id = f"{model_name}:{entity.id}"
                
                # Stocker les informations d'erreur
                self.error_log[error_id] = {
                    "id": entity.id,
                    "model": model_name,
                    "category": category,
                    "error": error,
                    "timestamp": time.time(),
                    "retry_count": self.error_log.get(error_id, {}).get("retry_count", 0) + 1
                }
    
    def _store_failed_delete_events(
        self, 
        events: List[Dict[str, Any]], 
        model_name: str, 
        category: str, 
        error: str
    ) -> None:
        """
        Stocke les événements de suppression qui ont échoué pour un réessai ultérieur.
        
        Args:
            events: Liste des événements
            model_name: Nom du modèle
            category: Catégorie des modèles
            error: Message d'erreur
        """
        with self._error_log_lock:
            for event in events:
                event_data = event.get('value', {})
                before_data = event_data.get('before', {})
                entity_id = before_data.get('id')
                
                if entity_id:
                    error_id = f"{model_name}:{entity_id}"
                    
                    # Stocker les informations d'erreur
                    self.error_log[error_id] = {
                        "id": entity_id,
                        "model": model_name,
                        "category": category,
                        "operation": "delete",
                        "error": error,
                        "timestamp": time.time(),
                        "retry_count": self.error_log.get(error_id, {}).get("retry_count", 0) + 1
                    }
    
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
            future = asyncio.run_coroutine_threadsafe(self.process_batch(batch, category), self.loop)
            
            # Attendre le résultat pour s'assurer que les exceptions sont propagées
            future.result()
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du lot pour la catégorie {category}: {str(e)}")
            # Incrémenter le compteur d'erreurs
            self.error_counter.inc()
            raise
    
    @circuit(name="process_error_retry", failure_threshold=3, recovery_timeout=300)
    async def process_error_retries(self) -> Dict[str, Any]:
        """
        Tente de retraiter les entités en erreur.
        Méthode périodique pour la reprise après erreur.
        
        Returns:
            Statistiques sur les réessais
        """
        start_time = time.time()
        stats = {"processed": 0, "success": 0, "failed": 0}
        
        # Copier la liste des erreurs pour éviter les modifications pendant le traitement
        with self._error_log_lock:
            error_entries = list(self.error_log.items())
        
        if not error_entries:
            return stats
        
        logger.info(f"Tentative de retraitement de {len(error_entries)} entités en erreur")
        
        # Regrouper par modèle et catégorie pour un traitement efficace
        retry_groups = {}
        
        for error_id, error_info in error_entries:
            model = error_info.get("model")
            category = error_info.get("category")
            operation = error_info.get("operation", "update")
            
            if not model or not category:
                continue
            
            # Ignorer les entités avec trop de tentatives
            if error_info.get("retry_count", 0) >= settings.get("CDC_MAX_RETRY_COUNT", 5):
                logger.warning(f"Entité {error_id} ignorée après {error_info['retry_count']} tentatives")
                continue
            
            # Clé de groupe pour traitement par lots
            group_key = f"{model}:{category}:{operation}"
            
            if group_key not in retry_groups:
                retry_groups[group_key] = []
            
            retry_groups[group_key].append(error_info)
            stats["processed"] += 1
        
        # Traiter chaque groupe d'entités en erreur
        for group_key, error_infos in retry_groups.items():
            model, category, operation = group_key.split(":")
            
            try:
                # Incrémenter le compteur de réessais
                self.retry_counter.inc(len(error_infos))
                
                if operation == "delete":
                    # Retraiter les suppressions
                    ids = [info["id"] for info in error_infos]
                    collection_name = get_collection_name(model.lower())
                    
                    success = await with_retry(
                        lambda: delete_vectors(collection_name, ids),
                        retries=2,
                        delay=2.0,
                        backoff_factor=2.0
                    )
                    
                    if success:
                        logger.info(f"Réessai réussi pour {len(ids)} suppressions dans {collection_name}")
                        stats["success"] += len(ids)
                        
                        # Supprimer les entrées d'erreur
                        with self._error_log_lock:
                            for info in error_infos:
                                error_id = f"{model}:{info['id']}"
                                if error_id in self.error_log:
                                    del self.error_log[error_id]
                    else:
                        logger.error(f"Échec du réessai pour {len(ids)} suppressions dans {collection_name}")
                        stats["failed"] += len(ids)
                else:
                    # Retraiter les créations/mises à jour
                    model_class = get_model_by_entity_type(model.lower())
                    if not model_class:
                        logger.error(f"Modèle {model} non trouvé pour le réessai")
                        stats["failed"] += len(error_infos)
                        continue
                    
                    # Récupérer les entités depuis la base de données
                    session = get_db_session()
                    try:
                        entity_ids = [info["id"] for info in error_infos]
                        entities = session.query(model_class).filter(model_class.id.in_(entity_ids)).all()
                        
                        if entities:
                            # Vectoriser et insérer
                            points = await self._create_vector_points_batch(entities, model.lower())
                            
                            if points:
                                collection_name = get_collection_name(model.lower())
                                success = await with_retry(
                                    lambda: upsert_vectors(collection_name, points),
                                    retries=2,
                                    delay=2.0,
                                    backoff_factor=2.0
                                )
                                
                                if success:
                                    logger.info(f"Réessai réussi pour {len(points)} entités dans {collection_name}")
                                    stats["success"] += len(points)
                                    
                                    # Supprimer les entrées d'erreur pour les entités réussies
                                    with self._error_log_lock:
                                        for point in points:
                                            error_id = f"{model}:{point['id']}"
                                            if error_id in self.error_log:
                                                del self.error_log[error_id]
                                else:
                                    logger.error(f"Échec du réessai pour {len(points)} entités dans {collection_name}")
                                    stats["failed"] += len(points)
                            else:
                                logger.warning(f"Aucun point généré lors du réessai pour {len(entities)} entités {model}")
                                stats["failed"] += len(entities)
                        else:
                            logger.warning(f"Aucune entité {model} trouvée pour les IDs {entity_ids}")
                            
                            # Supprimer les entrées d'erreur pour les entités inexistantes
                            with self._error_log_lock:
                                for info in error_infos:
                                    error_id = f"{model}:{info['id']}"
                                    if error_id in self.error_log:
                                        del self.error_log[error_id]
                            
                            stats["failed"] += len(entity_ids)
                    finally:
                        session.close()
            except Exception as e:
                logger.error(f"Erreur lors du réessai pour le groupe {group_key}: {str(e)}")
                stats["failed"] += len(error_infos)
        
        # Mettre à jour les statistiques
        stats["duration"] = time.time() - start_time
        logger.info(f"Réessai terminé: {stats['success']} succès, {stats['failed']} échecs en {stats['duration']:.2f}s")
        
        return stats
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les erreurs enregistrées.
        
        Returns:
            Statistiques sur les erreurs
        """
        with self._error_log_lock:
            total_errors = len(self.error_log)
            errors_by_category = {}
            errors_by_model = {}
            
            for error_id, info in self.error_log.items():
                category = info.get("category")
                model = info.get("model")
                
                if category:
                    errors_by_category[category] = errors_by_category.get(category, 0) + 1
                
                if model:
                    errors_by_model[model] = errors_by_model.get(model, 0) + 1
            
            return {
                "total_errors": total_errors,
                "by_category": errors_by_category,
                "by_model": errors_by_model
            }
    
    def shutdown(self) -> None:
        """Arrête proprement le processeur."""
        self.executor.shutdown(wait=True)
        
        # Arrêter l'event loop s'il est en cours d'exécution
        if self.loop.is_running():
            self.loop.stop()
        
        logger.info("Processeur CDC arrêté")