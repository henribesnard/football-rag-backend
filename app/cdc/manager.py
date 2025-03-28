"""
Gestionnaire principal du système CDC qui coordonne les consommateurs et processeurs.
"""
import logging
import signal
import time
import threading
import asyncio
from typing import Optional, Dict, Any
import os
import sys

from app.config import settings
from app.cdc.consumer import CDCConsumer
from app.cdc.processor import CDCProcessor
from app.db.qdrant.collections import initialize_collections
from app.monitoring.metrics import metrics
from app.monitoring.logger import get_logger

logger = get_logger(__name__)

class CDCManager:
    """
    Gestionnaire global du système CDC avec fonctionnalités améliorées:
    - Métriques détaillées
    - Gestion avancée du cycle de vie
    - Récupération automatique après erreur
    - Monitoring de santé
    """
    
    def __init__(self):
        """Initialise le gestionnaire CDC."""
        self.consumer = CDCConsumer()
        self.processor = CDCProcessor()
        self.running = False
        self._stop_event = threading.Event()
        
        # Métriques pour le monitoring
        self._initialize_metrics()
        
        # Thread pour le retry périodique des erreurs
        self.retry_thread = None
        self.retry_interval = settings.get("CDC_RETRY_INTERVAL", 300)  # 5 minutes par défaut
        
        # Thread pour le monitoring de santé
        self.health_check_thread = None
        self.health_check_interval = settings.get("CDC_HEALTH_CHECK_INTERVAL", 60)  # 1 minute par défaut
        
        # État de santé global
        self.health_status = {
            "status": "stopped",
            "last_check": time.time(),
            "components": {
                "consumer": {"status": "stopped"},
                "processor": {"status": "stopped"}
            }
        }
        
        # Configuration du gestionnaire de signaux pour arrêt propre
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Gestionnaire CDC initialisé")
    
    def _initialize_metrics(self):
        """Initialise les métriques pour le monitoring."""
        self.uptime_gauge = metrics.gauge(
            "cdc_uptime_seconds",
            "Temps écoulé depuis le démarrage du CDC"
        )
        
        self.health_status_gauge = metrics.gauge(
            "cdc_health_status",
            "État de santé du système CDC (1=healthy, 0=unhealthy)"
        )
        
        self.error_backlog_gauge = metrics.gauge(
            "cdc_error_backlog",
            "Nombre d'erreurs en attente de reprise"
        )
        
        self.start_time = None
    
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
        
        # Marquer le système comme en cours d'exécution
        self.running = True
        self.start_time = time.time()
        
        # Démarrer le thread de retry
        self.retry_thread = threading.Thread(
            target=self._retry_loop,
            daemon=True,
            name="cdc-retry-thread"
        )
        self.retry_thread.start()
        
        # Démarrer le thread de monitoring de santé
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="cdc-health-check-thread"
        )
        self.health_check_thread.start()
        
        # Mettre à jour l'état de santé
        self.health_status["status"] = "starting"
        self.health_status["components"]["consumer"]["status"] = "running"
        self.health_status["components"]["processor"]["status"] = "running"
        
        logger.info("Gestionnaire CDC démarré avec succès")
        
        # Boucle principale pour maintenir le programme en vie
        while not self._stop_event.is_set():
            try:
                # Mettre à jour la métrique de uptime
                if self.start_time:
                    uptime = time.time() - self.start_time
                    self.uptime_gauge.set(uptime)
                
                # Mettre à jour le nombre d'erreurs en attente
                error_stats = self.processor.get_error_stats()
                self.error_backlog_gauge.set(error_stats.get("total_errors", 0))
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale du gestionnaire CDC: {str(e)}")
                
                # Tenter de récupérer automatiquement
                if self._can_recover_from_error(e):
                    logger.info("Tentative de récupération automatique...")
                    self._attempt_recovery()
                else:
                    self.stop()
                    break
    
    def stop(self) -> None:
        """Arrête tous les composants du système CDC."""
        if not self.running:
            logger.warning("Le gestionnaire CDC n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du gestionnaire CDC")
        
        # Mettre à jour l'état de santé
        self.health_status["status"] = "stopping"
        
        # Arrêter le consommateur
        try:
            self.consumer.stop()
            self.health_status["components"]["consumer"]["status"] = "stopped"
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du consommateur: {str(e)}")
        
        # Arrêter le processeur
        try:
            self.processor.shutdown()
            self.health_status["components"]["processor"]["status"] = "stopped"
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du processeur: {str(e)}")
        
        # Marquer le système comme arrêté
        self.running = False
        self._stop_event.set()
        self.health_status["status"] = "stopped"
        
        # Attendre la fin des threads
        if self.retry_thread and self.retry_thread.is_alive():
            self.retry_thread.join(timeout=5)
        
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)
        
        logger.info("Gestionnaire CDC arrêté avec succès")
    
    def _signal_handler(self, sig, frame) -> None:
        """Gestionnaire de signaux pour arrêt propre."""
        logger.info(f"Signal {sig} reçu, arrêt du gestionnaire CDC")
        self.stop()
    
    def _retry_loop(self) -> None:
        """Boucle de retry pour les erreurs en attente."""
        logger.info(f"Thread de retry démarré (intervalle: {self.retry_interval}s)")
        
        # Attendre un peu pour laisser le système démarrer complètement
        time.sleep(settings.get("CDC_RETRY_INITIAL_DELAY", 30))
        
        while not self._stop_event.is_set():
            try:
                # Vérifier s'il y a des erreurs à réessayer
                error_stats = self.processor.get_error_stats()
                total_errors = error_stats.get("total_errors", 0)
                
                if total_errors > 0:
                    logger.info(f"Réessai des {total_errors} erreurs en attente")
                    
                    # Créer une boucle asyncio temporaire
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # Exécuter le traitement des erreurs
                        retry_result = loop.run_until_complete(
                            self.processor.process_error_retries()
                        )
                        
                        logger.info(f"Réessai terminé: {retry_result}")
                    finally:
                        loop.close()
                
                # Attendre jusqu'au prochain intervalle
                for _ in range(self.retry_interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"Erreur dans la boucle de retry: {str(e)}")
                
                # Attendre un peu avant de réessayer
                time.sleep(10)
    
    def _health_check_loop(self) -> None:
        """Boucle de vérification de l'état de santé."""
        logger.info(f"Thread de monitoring de santé démarré (intervalle: {self.health_check_interval}s)")
        
        while not self._stop_event.is_set():
            try:
                # Vérifier l'état de santé des composants
                self._update_health_status()
                
                # Attendre jusqu'au prochain intervalle
                for _ in range(self.health_check_interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring de santé: {str(e)}")
                
                # Attendre un peu avant de réessayer
                time.sleep(5)
    
    def _update_health_status(self) -> None:
        """Met à jour l'état de santé global du système."""
        self.health_status["last_check"] = time.time()
        
        # Vérifier le consommateur
        consumer_stats = self.consumer.get_buffer_stats()
        consumer_healthy = all(
            stats.get("current_size", 0) < stats.get("max_size", 100) * 0.9
            for stats in consumer_stats.values()
        )
        
        self.health_status["components"]["consumer"] = {
            "status": "healthy" if consumer_healthy else "degraded",
            "buffer_stats": consumer_stats
        }
        
        # Vérifier le processeur
        error_stats = self.processor.get_error_stats()
        processor_healthy = error_stats.get("total_errors", 0) < settings.get("CDC_MAX_TOLERATED_ERRORS", 100)
        
        self.health_status["components"]["processor"] = {
            "status": "healthy" if processor_healthy else "degraded",
            "error_stats": error_stats
        }
        
        # Déterminer l'état global
        if consumer_healthy and processor_healthy:
            global_status = "healthy"
        elif not consumer_healthy and not processor_healthy:
            global_status = "unhealthy"
        else:
            global_status = "degraded"
        
        self.health_status["status"] = global_status
        
        # Mettre à jour la métrique de santé
        self.health_status_gauge.set(1 if global_status == "healthy" else 0)
        
        # Log si l'état a changé
        if global_status != self.health_status.get("previous_status"):
            logger.info(f"État de santé CDC: {global_status}")
            self.health_status["previous_status"] = global_status
            
            # Si l'état est unhealthy, tenter une récupération automatique
            if global_status == "unhealthy" and settings.get("CDC_AUTO_RECOVERY", True):
                logger.warning("État de santé critique détecté, tentative de récupération automatique")
                self._attempt_recovery()
    
    def _attempt_recovery(self) -> None:
        """Tente de récupérer le système après une erreur critique."""
        logger.info("Tentative de récupération du système CDC")
        
        # Recomptage des erreurs et purge des anciennes
        self._purge_old_errors()
        
        # Si les tampons sont trop pleins, essayer de les traiter manuellement
        buffer_stats = self.consumer.get_buffer_stats()
        for category, stats in buffer_stats.items():
            if stats.get("current_size", 0) > stats.get("max_size", 100) * 0.8:
                logger.warning(f"Tampon {category} presque plein ({stats['current_size']}/{stats['max_size']})")
                
                # Trigger un traitement forcé si possible
                # Cette logique dépend de l'implémentation spécifique de CircularBuffer
                # et n'est pas incluse dans cet exemple
        
        logger.info("Tentative de récupération terminée")
    
    def _purge_old_errors(self) -> None:
        """Purge les erreurs trop anciennes du journal d'erreurs."""
        # Cette méthode serait implémentée pour nettoyer les erreurs très anciennes
        # qui pourraient encombrer le système
        pass
    
    def _can_recover_from_error(self, error: Exception) -> bool:
        """
        Détermine si une erreur peut faire l'objet d'une récupération automatique.
        
        Args:
            error: L'exception à analyser
            
        Returns:
            True si l'erreur peut faire l'objet d'une récupération
        """
        # Liste des exceptions récupérables
        recoverable_exceptions = [
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            # Ajouter d'autres exceptions spécifiques au besoin
        ]
        
        # Vérifier si l'erreur est d'un type récupérable
        for exception_type in recoverable_exceptions:
            if isinstance(error, exception_type):
                return True
        
        # Vérifier le message d'erreur pour des patterns connus
        error_str = str(error).lower()
        recoverable_patterns = [
            "timeout",
            "connection reset",
            "temporarily unavailable",
            "too many connections",
            "resource temporarily unavailable",
            "network unreachable"
        ]
        
        for pattern in recoverable_patterns:
            if pattern in error_str:
                return True
        
        return False
    
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
        # Mettre à jour l'état de santé avant de le retourner
        self._update_health_status()
        
        status = {
            "running": self.running,
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "health": self.health_status,
            "consumer": {
                "active": self.running,
                "buffers": self.consumer.get_buffer_stats() if self.running else {}
            },
            "processor": {
                "active": self.running,
                "errors": self.processor.get_error_stats() if self.running else {"total_errors": 0}
            },
            "system_info": {
                "pid": os.getpid(),
                "thread_count": threading.active_count(),
                "python_version": ".".join(map(str, sys.version_info[:3])) if 'sys' in globals() else "unknown"
            }
        }
        
        return status