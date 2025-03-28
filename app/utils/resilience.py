"""Utilitaires pour améliorer la résilience du système."""
import time
import random
import asyncio
import logging
from typing import TypeVar, Callable, Any, Optional, Dict

from app.utils.circuit_breaker import circuit

logger = logging.getLogger(__name__)

T = TypeVar('T')

async def with_retry(
    func: Callable[..., T],
    retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Exécute une fonction avec retry et backoff exponentiel.
    
    Args:
        func: Fonction à exécuter
        retries: Nombre maximum de tentatives
        delay: Délai initial entre les tentatives (secondes)
        backoff_factor: Facteur de multiplication du délai entre tentatives
        jitter: Facteur de variation aléatoire du délai (0-1)
        exceptions: Exceptions à intercepter pour retry
        
    Returns:
        Résultat de la fonction
        
    Raises:
        Dernière exception rencontrée après épuisement des tentatives
    """
    last_exception = None
    
    for attempt in range(retries):
        try:
            # Appel de la fonction (synchrone ou asynchrone)
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except exceptions as e:
            last_exception = e
            
            if attempt < retries - 1:
                # Calculer le délai avec backoff exponentiel et jitter
                sleep_time = delay * (backoff_factor ** attempt)
                jitter_amount = jitter * sleep_time
                adjusted_sleep = sleep_time + random.uniform(-jitter_amount, jitter_amount)
                
                logger.warning(
                    f"Tentative {attempt + 1}/{retries} échouée pour {func.__name__}. "
                    f"Nouvelle tentative dans {adjusted_sleep:.2f}s. Erreur: {str(e)}"
                )
                
                await asyncio.sleep(adjusted_sleep)
            else:
                logger.error(
                    f"Toutes les tentatives ont échoué pour {func.__name__}. "
                    f"Dernière erreur: {str(e)}"
                )
    
    # Si on arrive ici, toutes les tentatives ont échoué
    if last_exception:
        raise last_exception

class Bulkhead:
    """
    Implémentation du pattern Bulkhead pour limiter la concurrence.
    Limite le nombre d'exécutions concurrentes pour protéger les ressources.
    """
    
    def __init__(self, name: str, max_concurrent: int, queue_size: int = 0):
        """
        Initialise un bulkhead.
        
        Args:
            name: Nom pour l'identification
            max_concurrent: Nombre maximum d'exécutions concurrentes
            queue_size: Taille de la file d'attente (0 = pas de file)
        """
        self.name = name
        self.max_concurrent = max_concurrent
        self.queue_size = queue_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
        
        if queue_size > 0:
            self.queue = asyncio.Queue(queue_size)
        else:
            self.queue = None
            
        logger.info(f"Bulkhead '{name}' initialisé (max_concurrent={max_concurrent}, queue_size={queue_size})")
    
    async def execute(self, func, *args, **kwargs):
        """
        Exécute une fonction dans les limites du bulkhead.
        
        Args:
            func: Fonction à exécuter
            *args, **kwargs: Arguments pour la fonction
            
        Returns:
            Résultat de la fonction
            
        Raises:
            BulkheadFullError: Si pas de place disponible
        """
        async with self.semaphore:
            self.active_count += 1
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            finally:
                self.active_count -= 1

class BulkheadFullError(Exception):
    """Exception levée lorsqu'un bulkhead est plein."""
    pass