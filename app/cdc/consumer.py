"""
Consommateur Kafka pour le système CDC.
"""
import json
import logging
import time
import threading
from typing import Callable, Dict, List, Any, Optional
from confluent_kafka import Consumer, KafkaError, KafkaException

from app.config import settings
from app.cdc.buffer import CircularBuffer

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.CDC_LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CDCConsumer:
    """
    Consommateur Kafka pour les événements CDC de Debezium.
    """
    
    def __init__(self):
        """Initialise le consommateur Kafka avec les paramètres de configuration."""
        self.config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': settings.KAFKA_GROUP_ID,
            'auto.offset.reset': settings.KAFKA_AUTO_OFFSET_RESET,
            'enable.auto.commit': False  # Désactiver la validation automatique pour un contrôle précis
        }
        self.consumer = Consumer(self.config)
        self.topics = settings.CDC_KAFKA_TOPICS
        
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
            self.consumer_thread.join(timeout=10)
        
        for thread in self.processor_threads.values():
            thread.join(timeout=10)
        
        # Fermer le consommateur Kafka
        self.consumer.close()
        logger.info("Consommateur CDC arrêté")
    
    def _consume_loop(self) -> None:
        """Boucle principale pour consommer les messages Kafka."""
        logger.info("Démarrage du thread de consommation Kafka")
        try:
            while not self.stop_event.is_set():
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # Fin de partition, pas une erreur
                        continue
                    else:
                        # Erreur réelle
                        logger.error(f"Erreur Kafka: {msg.error()}")
                        continue
                
                try:
                    # Décoder le message
                    value = json.loads(msg.value().decode('utf-8'))
                    topic = msg.topic()
                    partition = msg.partition()
                    offset = msg.offset()
                    
                    # Déterminer la catégorie du topic
                    category = self.topic_category_mapping.get(topic)
                    if not category:
                        logger.warning(f"Topic {topic} non associé à une catégorie. Message ignoré.")
                        self.consumer.commit(msg)
                        continue
                    
                    # Préparer l'événement avec des métadonnées
                    event = {
                        'topic': topic,
                        'partition': partition,
                        'offset': offset,
                        'value': value,
                        # Extraire le nom de la table de la source
                        'table': value.get('source', {}).get('table') if 'source' in value else None,
                        # Extraire l'opération (c=create, u=update, d=delete)
                        'operation': value.get('op') if 'op' in value else None
                    }
                    
                    # Ajouter l'événement au tampon approprié
                    self.buffers[category].add(event)
                    
                    # Valider l'offset pour marquer le message comme traité
                    self.consumer.commit(msg)
                    
                    logger.debug(f"Événement de {topic} ajouté au tampon de la catégorie {category}")
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du message: {str(e)}")
                    # Valider quand même pour éviter de bloquer sur un message problématique
                    self.consumer.commit(msg)
        
        except KafkaException as e:
            logger.error(f"Erreur Kafka critique: {str(e)}")
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle de consommation: {str(e)}")
        finally:
            logger.info("Thread de consommation Kafka terminé")
    
    def _category_processing_loop(self, category: str, batch_processor: Callable) -> None:
        """
        Boucle de traitement pour une catégorie spécifique.
        
        Args:
            category: Catégorie de modèles
            batch_processor: Fonction de traitement des lots
        """
        logger.info(f"Démarrage du thread de traitement pour la catégorie: {category}")
        buffer = self.buffers[category]
        
        try:
            while not self.stop_event.is_set():
                # Obtenir le timeout spécifique à la catégorie
                timeout = settings.CDC_PROCESSING_TIMEOUTS.get(category, settings.CDC_PROCESSING_BATCH_TIMEOUT)
                
                # Vérifier si le tampon est prêt pour le traitement
                if buffer.is_ready_for_processing(timeout):
                    with threading.Lock():  # Verrouiller pour éviter les problèmes de concurrence
                        # Récupérer tous les événements du tampon
                        batch = buffer.get_batch()
                        if not batch:
                            time.sleep(0.1)
                            continue
                        
                        batch_size = len(batch)
                        try:
                            # Traiter le lot avec la catégorie
                            batch_processor(batch, category)
                            # Vider le tampon des événements traités
                            buffer.clear_batch(batch_size)
                            logger.info(f"Lot de {batch_size} événements de la catégorie {category} traité avec succès")
                        except Exception as e:
                            logger.error(f"Erreur lors du traitement du lot pour la catégorie {category}: {str(e)}")
                            # Ne pas vider le tampon en cas d'erreur pour permettre une nouvelle tentative
                else:
                    # Attendre un peu avant de vérifier à nouveau
                    time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle de traitement de la catégorie {category}: {str(e)}")
        finally:
            logger.info(f"Thread de traitement pour la catégorie {category} terminé")
    
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
                "max_size": buffer.max_size
            }
        return stats