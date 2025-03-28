"""
Consommateur Kafka pour le système CDC.
"""
import json
import logging
import time
import threading
from typing import Callable, Dict, List, Any, Optional, Set
from confluent_kafka import Consumer, KafkaError, KafkaException
import redis

from app.config import settings
from app.cdc.buffer import CircularBuffer
from app.cdc.offset_store import OffsetStore
from app.cdc.event_merger import merge_consecutive_events
from app.monitoring.metrics import metrics

# Configuration du logging
logger = logging.getLogger(__name__)

class CDCConsumer:
    """
    Consommateur Kafka pour les événements CDC de Debezium.
    Inclut des fonctionnalités améliorées:
    - Suivi persistant des offsets
    - Fusion des événements consécutifs
    - Métriques détaillées
    - Gestion améliorée des erreurs
    """
    
    def __init__(self):
        """Initialise le consommateur Kafka avec les paramètres de configuration."""
        self.config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': settings.KAFKA_GROUP_ID,
            'auto.offset.reset': settings.KAFKA_AUTO_OFFSET_RESET,
            'enable.auto.commit': False,  # Désactiver la validation automatique pour un contrôle précis
            # Paramètres de performance
            'fetch.min.bytes': 1,
            'fetch.max.wait.ms': 500,
            'max.poll.interval.ms': 300000  # 5 minutes
        }
        self.consumer = Consumer(self.config)
        self.topics = settings.CDC_KAFKA_TOPICS
        
        # Offset store pour la reprise après panne
        self.offset_store = OffsetStore()
        
        # Créer des tampons circulaires pour chaque catégorie de modèles
        self.buffers = {
            category: CircularBuffer(category=category)
            for category in settings.CDC_MODEL_CATEGORIES.keys()
        }
        
        # Mapper les topics aux catégories pour le routage des événements
        self.topic_category_mapping = self._create_topic_category_mapping()
        
        # Événement d'arrêt
        self.stop_event = threading.Event()
        
        # Threads des processeurs par catégorie
        self.processor_threads = {}
        
        # Métriques pour le monitoring
        self.events_counter = metrics.counter(
            "cdc_events_total",
            "Nombre total d'événements CDC traités"
        )
        self.events_error_counter = metrics.counter(
            "cdc_events_error_total",
            "Nombre total d'erreurs lors du traitement des événements CDC"
        )
        self.events_merged_counter = metrics.counter(
            "cdc_events_merged_total",
            "Nombre total d'événements CDC fusionnés"
        )
        self.processing_time = metrics.histogram(
            "cdc_processing_time",
            "Temps de traitement des événements CDC (secondes)",
            buckets=[0.001, 0.01, 0.1, 0.5, 1, 5, 10, 30, 60]
        )
        self.category_counters = {
            category: metrics.counter(
                f"cdc_events_{category}_total",
                f"Nombre total d'événements CDC pour la catégorie {category}"
            )
            for category in settings.CDC_MODEL_CATEGORIES.keys()
        }
        
        # Suivi des événements en erreur pour la reprise
        self.error_events = {}
        self.max_retry_count = 3
        
        logger.info(f"CDC Consumer initialisé pour {len(self.topics)} topics")
    
    def _create_topic_category_mapping(self) -> Dict[str, str]:
        """
        Crée un mapping des topics Kafka vers les catégories de modèles.
        
        Returns:
            Dictionnaire {topic: catégorie}
        """
        mapping = {}
        model_categories = settings.CDC_MODEL_CATEGORIES
        model_topic_mapping = settings.CDC_MODEL_TOPIC_MAPPING
        
        # Pour chaque catégorie et ses modèles
        for category, models in model_categories.items():
            # Pour chaque modèle dans cette catégorie
            for model in models:
                # Si le modèle a un topic associé
                if model in model_topic_mapping:
                    topic = model_topic_mapping[model]
                    mapping[topic] = category
        
        return mapping
    
    def start(self, batch_processor: Callable[[List[Dict[str, Any]], str], None]) -> None:
        """
        Démarre le consommateur et les processeurs de lot.
        
        Args:
            batch_processor: Fonction appelée pour traiter chaque lot d'événements.
                             Doit accepter un lot et une catégorie.
        """
        # Restaurer les offsets si disponibles
        self._restore_offsets()
        
        # S'abonner aux topics
        self.consumer.subscribe(self.topics)
        
        # Démarrer le thread de consommation
        self.consumer_thread = threading.Thread(
            target=self._consume_loop,
            daemon=True
        )
        self.consumer_thread.start()
        
        # Démarrer les threads de traitement par catégorie
        for category in self.buffers.keys():
            thread = threading.Thread(
                target=self._category_processing_loop,
                args=(category, batch_processor),
                daemon=True
            )
            self.processor_threads[category] = thread
            thread.start()
        
        logger.info("Consommateur CDC démarré avec succès")
    
    def stop(self) -> None:
        """Arrête le consommateur et les processeurs de manière propre."""
        self.stop_event.set()
        
        # Attendre que les threads se terminent
        if hasattr(self, 'consumer_thread'):
            logger.info("Arrêt du thread de consommation...")
            self.consumer_thread.join(timeout=10)
        
        for category, thread in self.processor_threads.items():
            logger.info(f"Arrêt du thread de traitement pour la catégorie {category}...")
            thread.join(timeout=10)
        
        # Sauvegarder les offsets
        self._save_offsets()
        
        # Fermer le consommateur Kafka
        self.consumer.close()
        logger.info("Consommateur CDC arrêté")
    
    def _restore_offsets(self) -> None:
        """Restaure les offsets précédemment sauvegardés pour une reprise après panne."""
        try:
            offsets = self.offset_store.get_offsets(settings.KAFKA_GROUP_ID)
            if offsets:
                logger.info(f"Restauration des offsets pour {len(offsets)} topics")
                
                for topic, partitions in offsets.items():
                    for partition, offset in partitions.items():
                        self.consumer.assign([{"topic": topic, "partition": int(partition), "offset": int(offset)}])
                        logger.info(f"Offset restauré pour {topic}:{partition} à {offset}")
            else:
                logger.info("Aucun offset précédent à restaurer")
        except Exception as e:
            logger.error(f"Erreur lors de la restauration des offsets: {str(e)}")
    
    def _save_offsets(self) -> None:
        """Sauvegarde les offsets actuels pour une reprise ultérieure."""
        try:
            current_offsets = {}
            
            for topic_partition in self.consumer.assignment():
                topic = topic_partition.topic
                partition = topic_partition.partition
                
                # Obtenir la position actuelle
                position = self.consumer.position([topic_partition])
                
                if topic not in current_offsets:
                    current_offsets[topic] = {}
                
                # Sauvegarder la position
                if position and len(position) > 0:
                    current_offsets[topic][partition] = position[0].offset
            
            if current_offsets:
                self.offset_store.save_offsets(settings.KAFKA_GROUP_ID, current_offsets)
                logger.info(f"Offsets sauvegardés pour {len(current_offsets)} topics")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des offsets: {str(e)}")
    
    def _consume_loop(self) -> None:
        """Boucle principale pour consommer les messages Kafka."""
        logger.info("Démarrage du thread de consommation Kafka")
        try:
            # Liste des messages pour fusion éventuelle
            batch_messages = {}
            batch_timeout = 5  # secondes avant traitement forcé
            last_batch_time = time.time()
            
            while not self.stop_event.is_set():
                try:
                    # Polling avec un timeout court pour réagir rapidement à l'arrêt
                    msg = self.consumer.poll(1.0)
                    
                    if msg is None:
                        # Vérifier si on doit traiter un lot existant par timeout
                        if batch_messages and (time.time() - last_batch_time) > batch_timeout:
                            # Traiter les messages accumulés
                            self._process_message_batch(batch_messages)
                            batch_messages = {}
                            last_batch_time = time.time()
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # Fin de partition, pas une erreur
                            continue
                        else:
                            # Erreur réelle
                            logger.error(f"Erreur Kafka: {msg.error()}")
                            self.events_error_counter.inc()
                            continue
                    
                    # Obtenir les métadonnées du message
                    topic = msg.topic()
                    partition = msg.partition()
                    offset = msg.offset()
                    timestamp = msg.timestamp()[1]
                    
                    # Ajouter le message au batch temporaire pour fusion éventuelle
                    key = (topic, partition)
                    if key not in batch_messages:
                        batch_messages[key] = []
                    
                    try:
                        # Décoder le message
                        value = json.loads(msg.value().decode('utf-8'))
                        
                        # Préparer l'événement avec des métadonnées
                        event = {
                            'topic': topic,
                            'partition': partition,
                            'offset': offset,
                            'timestamp': timestamp,
                            'value': value,
                            # Extraire le nom de la table de la source
                            'table': value.get('source', {}).get('table') if 'source' in value else None,
                            # Extraire l'opération (c=create, u=update, d=delete)
                            'operation': value.get('op') if 'op' in value else None
                        }
                        
                        batch_messages[key].append(event)
                        
                        # Valider l'offset immédiatement après le traitement
                        self.consumer.commit(msg)
                        
                        # Incrémenter le compteur d'événements
                        self.events_counter.inc()
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement du message: {str(e)}")
                        self.events_error_counter.inc()
                        # Valider quand même pour éviter de bloquer sur un message problématique
                        self.consumer.commit(msg)
                    
                    # Traiter le batch si suffisamment grand ou si timeout atteint
                    if (len(batch_messages) >= 100 or  # Au moins 100 clés (topic, partition)
                        sum(len(msgs) for msgs in batch_messages.values()) >= 1000 or  # Au moins 1000 messages au total
                        (time.time() - last_batch_time) > batch_timeout):  # Timeout atteint
                        
                        self._process_message_batch(batch_messages)
                        batch_messages = {}
                        last_batch_time = time.time()
                
                except Exception as e:
                    logger.error(f"Erreur dans la boucle de consommation: {str(e)}")
                    self.events_error_counter.inc()
                    # Pause courte pour éviter une boucle d'erreurs trop rapide
                    time.sleep(1)
            
            # Traiter les derniers messages avant de terminer
            if batch_messages:
                self._process_message_batch(batch_messages)
        
        except KafkaException as e:
            logger.error(f"Erreur Kafka critique: {str(e)}")
            self.events_error_counter.inc()
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle de consommation: {str(e)}")
            self.events_error_counter.inc()
        finally:
            logger.info("Thread de consommation Kafka terminé")
    
    def _process_message_batch(self, batch_messages: Dict[tuple, List[Dict[str, Any]]]) -> None:
        """
        Traite et fusionne un lot de messages groupés par (topic, partition).
        
        Args:
            batch_messages: Dictionnaire {(topic, partition): [événements]}
        """
        start_time = time.time()
        
        # Fusionner et traiter les messages par topic/partition
        all_events_by_table = {}
        
        # Étape 1: Fusionner les événements consécutifs sur la même entité
        for key, events in batch_messages.items():
            if not events:
                continue
            
            topic = key[0]
            
            # Déterminer la catégorie du topic
            category = self.topic_category_mapping.get(topic)
            if not category:
                logger.warning(f"Topic {topic} non associé à une catégorie. Messages ignorés.")
                continue
            
            # Grouper par table pour la fusion
            for event in events:
                table = event.get('table')
                if not table:
                    continue
                
                if table not in all_events_by_table:
                    all_events_by_table[table] = []
                
                all_events_by_table[table].append(event)
        
        # Étape 2: Fusionner les événements par table
        merged_events_by_category = {}
        
        for table, events in all_events_by_table.items():
            # Fusionner les événements consécutifs sur la même entité
            original_count = len(events)
            merged_events = merge_consecutive_events(events)
            merged_count = len(merged_events)
            
            # Compter les événements fusionnés
            if original_count > merged_count:
                self.events_merged_counter.inc(original_count - merged_count)
                logger.debug(f"Fusion de {original_count} à {merged_count} événements pour la table {table}")
            
            # Ajouter les événements fusionnés à la catégorie appropriée
            for event in merged_events:
                topic = event.get('topic')
                category = self.topic_category_mapping.get(topic)
                
                if not category:
                    continue
                
                if category not in merged_events_by_category:
                    merged_events_by_category[category] = []
                
                merged_events_by_category[category].append(event)
        
        # Étape 3: Ajouter les événements aux tampons appropriés
        for category, events in merged_events_by_category.items():
            buffer = self.buffers[category]
            for event in events:
                buffer.add(event)
            
            # Incrémenter les compteurs par catégorie
            if category in self.category_counters:
                self.category_counters[category].inc(len(events))
            
            logger.debug(f"Ajout de {len(events)} événements au tampon de la catégorie {category}")
        
        # Mesurer le temps de traitement
        processing_time = time.time() - start_time
        self.processing_time.observe(processing_time)
        
        # Sauvegarder les offsets périodiquement
        if time.time() % 60 < 1:  # Environ une fois par minute
            self._save_offsets()
    
    def _category_processing_loop(self, category: str, batch_processor: Callable) -> None:
        """
        Boucle de traitement pour une catégorie spécifique.
        
        Args:
            category: Catégorie de modèles
            batch_processor: Fonction de traitement des lots
        """
        logger.info(f"Démarrage du thread de traitement pour la catégorie: {category}")
        buffer = self.buffers[category]
        
        # Histogramme pour mesurer le temps de traitement des lots
        batch_processing_time = metrics.histogram(
            f"cdc_batch_processing_time_{category}",
            f"Temps de traitement des lots pour la catégorie {category} (secondes)",
            buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120]
        )
        
        try:
            while not self.stop_event.is_set():
                # Obtenir le timeout spécifique à la catégorie
                timeout = settings.CDC_PROCESSING_TIMEOUTS.get(category, settings.CDC_PROCESSING_BATCH_TIMEOUT)
                
                # Vérifier si le tampon est prêt pour le traitement
                if buffer.is_ready_for_processing(timeout):
                    # Verrouiller pour éviter les problèmes de concurrence
                    with threading.Lock():
                        # Récupérer tous les événements du tampon
                        batch = buffer.get_batch()
                        if not batch:
                            time.sleep(0.1)
                            continue
                        
                        batch_size = len(batch)
                        logger.info(f"Traitement d'un lot de {batch_size} événements pour la catégorie {category}")
                        
                        # Mesurer le temps de traitement
                        start_time = time.time()
                        
                        try:
                            # Traiter le lot avec la catégorie
                            batch_processor(batch, category)
                            
                            # Vider le tampon des événements traités
                            buffer.clear_batch(batch_size)
                            
                            # Mesurer et enregistrer le temps de traitement
                            elapsed_time = time.time() - start_time
                            batch_processing_time.observe(elapsed_time)
                            
                            logger.info(f"Lot de {batch_size} événements de la catégorie {category} traité en {elapsed_time:.2f}s")
                            
                            # Supprimer les événements en erreur qui ont été traités avec succès
                            successful_ids = self._get_event_ids(batch)
                            for event_id in successful_ids:
                                if event_id in self.error_events:
                                    del self.error_events[event_id]
                            
                        except Exception as e:
                            # Mesurer et enregistrer le temps même en cas d'erreur
                            elapsed_time = time.time() - start_time
                            batch_processing_time.observe(elapsed_time)
                            
                            logger.error(f"Erreur lors du traitement du lot pour la catégorie {category}: {str(e)}")
                            self.events_error_counter.inc()
                            
                            # Réessayer pour les petits lots ou pour les lots avec peu de tentatives
                            if batch_size <= 10 or self._should_retry_batch(batch):
                                # Marquer les événements comme étant en erreur
                                self._mark_events_as_error(batch)
                                
                                # Ne pas vider le tampon pour permettre une nouvelle tentative
                                logger.info(f"Le lot sera réessayé lors du prochain cycle de traitement")
                            else:
                                # Pour les grands lots avec trop de tentatives, les diviser
                                logger.info(f"Division du lot de {batch_size} événements pour retraitement")
                                buffer.clear_batch(batch_size)
                                
                                # Diviser le lot en plus petits lots et les remettre dans le tampon
                                half_size = batch_size // 2
                                first_half = batch[:half_size]
                                second_half = batch[half_size:]
                                
                                for event in first_half:
                                    buffer.add(event)
                                
                                # Attendre un peu avant d'ajouter la seconde moitié
                                time.sleep(1)
                                
                                for event in second_half:
                                    buffer.add(event)
                else:
                    # Attendre un peu avant de vérifier à nouveau
                    time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle de traitement de la catégorie {category}: {str(e)}")
        finally:
            logger.info(f"Thread de traitement pour la catégorie {category} terminé")
    
    def _get_event_ids(self, events: List[Dict[str, Any]]) -> Set[str]:
        """
        Extrait les identifiants uniques des événements.
        
        Args:
            events: Liste d'événements
            
        Returns:
            Ensemble d'identifiants uniques
        """
        event_ids = set()
        for event in events:
            # Créer un ID unique basé sur topic + table + operation + entity_id
            table = event.get('table', '')
            operation = event.get('operation', '')
            
            # Tenter d'extraire l'ID de l'entité
            entity_id = None
            value = event.get('value', {})
            
            # Pour les créations et mises à jour, l'ID est dans 'after'
            if operation in ('c', 'u') and 'after' in value:
                entity_id = value['after'].get('id')
            # Pour les suppressions, l'ID est dans 'before'
            elif operation == 'd' and 'before' in value:
                entity_id = value['before'].get('id')
            
            if entity_id:
                event_id = f"{table}:{operation}:{entity_id}"
                event_ids.add(event_id)
        
        return event_ids
    
    def _mark_events_as_error(self, events: List[Dict[str, Any]]) -> None:
        """
        Marque les événements comme étant en erreur pour le suivi des tentatives.
        
        Args:
            events: Liste d'événements
        """
        for event_id in self._get_event_ids(events):
            if event_id in self.error_events:
                self.error_events[event_id] += 1
            else:
                self.error_events[event_id] = 1
    
    def _should_retry_batch(self, batch: List[Dict[str, Any]]) -> bool:
        """
        Détermine si un lot doit être réessayé en fonction du nombre de tentatives précédentes.
        
        Args:
            batch: Lot d'événements
            
        Returns:
            True si le lot doit être réessayé
        """
        event_ids = self._get_event_ids(batch)
        
        # Vérifier si tous les événements ont dépassé le nombre maximum de tentatives
        for event_id in event_ids:
            # Si un événement n'a pas été essayé assez de fois, réessayer le lot
            if event_id not in self.error_events or self.error_events[event_id] < self.max_retry_count:
                return True
        
        # Tous les événements ont dépassé le nombre maximum de tentatives
        return False
    
    def get_buffer_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Retourne des statistiques sur l'état des tampons circulaires.
        
        Returns:
            Dictionnaire contenant les statistiques des tampons par catégorie
        """
        stats = {}
        for category, buffer in self.buffers.items():
            stats[category] = {
                "current_size": len(buffer),
                "max_size": buffer.max_size,
                "error_count": sum(1 for event_id in self.error_events if event_id.startswith(f"{category}:"))
            }
        return stats