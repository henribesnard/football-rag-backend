"""
Module de gestion du tampon circulaire pour le système CDC.
"""
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from collections import deque

from app.config import settings

logger = logging.getLogger(__name__)

class CircularBuffer:
    """
    Tampon circulaire thread-safe pour stocker les événements CDC avant traitement par lots.
    """
    
    def __init__(self, max_size: int = None, category: str = None):
        """
        Initialise un tampon circulaire avec une taille maximale.
        
        Args:
            max_size: Taille maximale du tampon. Si None, utilise la valeur par défaut
            category: Catégorie de modèles. Si spécifiée, utilise la taille configurée pour cette catégorie
        """
        if category and category in settings.CDC_BUFFER_SIZES:
            self.max_size = settings.CDC_BUFFER_SIZES[category]
        else:
            self.max_size = max_size or settings.CDC_BUFFER_SIZE
            
        self.buffer = deque(maxlen=self.max_size)
        self.lock = threading.Lock()
        self.last_batch_time = time.time()
        self.category = category
        
        logger.debug(f"Tampon circulaire initialisé avec une taille maximale de {self.max_size}")
        if category:
            logger.debug(f"Tampon pour la catégorie: {category}")
    
    def add(self, event: Dict[str, Any]) -> None:
        """
        Ajoute un événement au tampon de manière thread-safe.
        
        Args:
            event: Événement CDC à ajouter
        """
        with self.lock:
            self.buffer.append(event)
            logger.debug(f"Événement ajouté au tampon. Taille actuelle: {len(self.buffer)}/{self.max_size}")
    
    def get_batch(self, max_batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère un lot d'événements du tampon de manière thread-safe.
        Ne vide pas le tampon.
        
        Args:
            max_batch_size: Nombre maximum d'événements à récupérer (par défaut, tous les événements)
            
        Returns:
            Liste des événements du lot
        """
        with self.lock:
            if max_batch_size is None or max_batch_size >= len(self.buffer):
                return list(self.buffer)
            else:
                return [self.buffer[i] for i in range(max_batch_size)]
    
    def clear_batch(self, batch_size: int) -> None:
        """
        Supprime un nombre spécifié d'événements du tampon de manière thread-safe.
        
        Args:
            batch_size: Nombre d'événements à supprimer
        """
        with self.lock:
            for _ in range(min(batch_size, len(self.buffer))):
                self.buffer.popleft()
            logger.debug(f"Lot supprimé du tampon. Taille actuelle: {len(self.buffer)}/{self.max_size}")
    
    def is_ready_for_processing(self, timeout: Optional[int] = None) -> bool:
        """
        Vérifie si le tampon est prêt pour le traitement, soit parce qu'il est plein,
        soit parce que le délai d'attente est écoulé.
        
        Args:
            timeout: Délai en secondes avant traitement forcé (par défaut: valeur configurée)
            
        Returns:
            True si le tampon est prêt à être traité, False sinon
        """
        # Déterminer le timeout à utiliser
        if timeout is None:
            if self.category and self.category in settings.CDC_PROCESSING_TIMEOUTS:
                timeout = settings.CDC_PROCESSING_TIMEOUTS[self.category]
            else:
                timeout = settings.CDC_PROCESSING_BATCH_TIMEOUT
        
        with self.lock:
            # Tampon plein
            if len(self.buffer) >= self.max_size:
                logger.debug("Tampon plein, prêt pour le traitement")
                return True
            
            # Tampon vide
            if len(self.buffer) == 0:
                self.last_batch_time = time.time()  # Réinitialiser le minuteur
                return False
            
            # Vérifier le timeout
            current_time = time.time()
            if current_time - self.last_batch_time >= timeout:
                logger.debug(f"Timeout écoulé ({timeout}s), tampon prêt pour le traitement")
                return True
            
            return False
    
    def process_batch_when_ready(self, processor: Callable[[List[Dict[str, Any]]], None], 
                                timeout: Optional[int] = None, block: bool = True) -> bool:
        """
        Traite un lot lorsque le tampon est prêt, soit en bloquant soit en retournant immédiatement.
        
        Args:
            processor: Fonction de traitement du lot
            timeout: Délai en secondes avant traitement forcé
            block: Si True, bloque jusqu'à ce que le tampon soit prêt; sinon retourne immédiatement
            
        Returns:
            True si un lot a été traité, False sinon
        """
        if not block and not self.is_ready_for_processing(timeout):
            return False
        
        # Si block=True, attendre que le tampon soit prêt
        while block and not self.is_ready_for_processing(timeout):
            time.sleep(0.1)
        
        with self.lock:
            # Double vérification en cas de concurrence
            if len(self.buffer) == 0:
                return False
            
            # Récupérer et traiter le lot
            batch = list(self.buffer)
            batch_size = len(batch)
            
            try:
                processor(batch)
                self.clear_batch(batch_size)
                self.last_batch_time = time.time()  # Réinitialiser le minuteur
                logger.info(f"Lot de {batch_size} événements traité avec succès")
                return True
            except Exception as e:
                logger.error(f"Erreur lors du traitement du lot: {str(e)}")
                # Ne pas vider le tampon en cas d'erreur
                return False
    
    def __len__(self) -> int:
        """Retourne la taille actuelle du tampon."""
        with self.lock:
            return len(self.buffer)