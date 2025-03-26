"""
Gestionnaire principal du système CDC qui coordonne les consommateurs et processeurs.
"""
import logging
import signal
import time
import threading
from typing import Optional

from app.config import settings
from app.cdc.consumer import CDCConsumer
from app.cdc.processor import CDCProcessor
from app.db.qdrant.collections import initialize_collections

logger = logging.getLogger(__name__)

class CDCManager:
    """
    Gestionnaire global du système CDC.
    """
    
    def __init__(self):
        """Initialise le gestionnaire CDC."""
        self.consumer = CDCConsumer()
        self.processor = CDCProcessor()
        self.running = False
        self._stop_event = threading.Event()
        
        # Configuration du gestionnaire de signaux pour arrêt propre
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Gestionnaire CDC initialisé")
    
    def start(self) -> None:
        """Démarre tous les composants du système CDC."""
        if self.running:
            logger.warning("Le gestionnaire CDC est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du gestionnaire CDC")
        
        # S'assurer que les collections Qdrant sont initialisées
        initialize_collections()
        
        # Démarrer le consommateur CDC
        self.consumer.start(self.processor.run_batch_processor)
        
        self.running = True
        logger.info("Gestionnaire CDC démarré avec succès")
        
        # Boucle principale pour maintenir le programme en vie
        while not self._stop_event.is_set():
            try:
                time.sleep(1)
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale du gestionnaire CDC: {str(e)}")
                self.stop()
                break
    
    def stop(self) -> None:
        """Arrête tous les composants du système CDC."""
        if not self.running:
            logger.warning("Le gestionnaire CDC n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du gestionnaire CDC")
        
        # Arrêter le consommateur
        self.consumer.stop()
        
        # Arrêter le processeur
        self.processor.shutdown()
        
        self.running = False
        self._stop_event.set()
        
        logger.info("Gestionnaire CDC arrêté avec succès")
    
    def _signal_handler(self, sig, frame) -> None:
        """Gestionnaire de signaux pour arrêt propre."""
        logger.info(f"Signal {sig} reçu, arrêt du gestionnaire CDC")
        self.stop()
    
    @property
    def is_running(self) -> bool:
        """Retourne l'état d'exécution du gestionnaire."""
        return self.running
    
    def get_status(self) -> dict:
        """
        Retourne le statut actuel du système CDC.
        
        Returns:
            Dictionnaire avec les informations de statut
        """
        status = {
            "running": self.running,
            "consumer": {
                "active": self.running,
                "buffers": self.consumer.get_buffer_stats() if self.running else {}
            },
            "processor": {
                "active": self.running
            }
        }
        return status