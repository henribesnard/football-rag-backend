"""Implémentation du pattern Circuit Breaker pour protéger les services externes."""
import time
import logging
import functools
import asyncio
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """États possibles d'un disjoncteur."""
    CLOSED = "closed"      # Fonctionnement normal, requêtes autorisées
    OPEN = "open"          # Circuit ouvert, requêtes bloquées
    HALF_OPEN = "half_open"  # En période de test, quelques requêtes autorisées

class CircuitBreaker:
    """
    Implémentation du pattern Circuit Breaker.
    Protège les services contre les défaillances en cascade.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exceptions: tuple = (Exception,),
    ):
        """
        Initialise un disjoncteur.
        
        Args:
            name: Nom unique du disjoncteur
            failure_threshold: Nombre d'échecs avant ouverture
            recovery_timeout: Temps en secondes avant test de fermeture
            expected_exceptions: Exceptions à considérer comme des échecs
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.success_count = 0
        
        logger.info(f"Circuit Breaker '{name}' initialisé")
    
    def can_execute(self) -> bool:
        """
        Vérifie si l'exécution est autorisée.
        Gère la transition entre les états.
        
        Returns:
            True si l'exécution est autorisée
        """
        now = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
            
        elif self.state == CircuitState.OPEN:
            # Vérifier si le temps de récupération est écoulé
            if now - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"Circuit Breaker '{self.name}' passant à l'état HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
            
        elif self.state == CircuitState.HALF_OPEN:
            # En demi-ouvert, nous autorisons un test
            return True
            
        return False
    
    def record_success(self) -> None:
        """Enregistre un appel réussi."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            # Après quelques succès en demi-ouvert, on ferme le circuit
            if self.success_count >= 2:
                logger.info(f"Circuit Breaker '{self.name}' passant à l'état CLOSED après récupération")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        
        # En fermé, on réinitialise le compteur d'échecs après un certain nombre de succès
        elif self.state == CircuitState.CLOSED and self.failure_count > 0:
            self.success_count += 1
            if self.success_count >= 5:
                self.failure_count = 0
                self.success_count = 0
    
    def record_failure(self) -> None:
        """Enregistre un échec."""
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit Breaker '{self.name}' échec pendant la période de test, retour à OPEN")
            self.state = CircuitState.OPEN
            self.success_count = 0
            return
            
        self.failure_count += 1
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit Breaker '{self.name}' passant à l'état OPEN après {self.failure_count} échecs")
            self.state = CircuitState.OPEN
            self.success_count = 0

def circuit(
    name: str = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    expected_exceptions: tuple = (Exception,),
    fallback_function: Callable = None
):
    """
    Décorateur pour appliquer un Circuit Breaker à une fonction.
    
    Args:
        name: Nom du disjoncteur (utilise le nom de la fonction si None)
        failure_threshold: Nombre d'échecs avant ouverture
        recovery_timeout: Temps en secondes avant test de fermeture
        expected_exceptions: Exceptions à considérer comme des échecs
        fallback_function: Fonction à appeler si le circuit est ouvert
        
    Returns:
        Fonction décorée
    """
    circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create_breaker(breaker_name: str) -> CircuitBreaker:
        if breaker_name not in circuit_breakers:
            circuit_breakers[breaker_name] = CircuitBreaker(
                name=breaker_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exceptions=expected_exceptions
            )
        return circuit_breakers[breaker_name]
    
    def decorator(func):
        breaker_name = name or func.__qualname__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            breaker = get_or_create_breaker(breaker_name)
            
            if not breaker.can_execute():
                logger.warning(f"Circuit ouvert pour {breaker_name}, requête rejetée")
                if fallback_function:
                    return fallback_function(*args, **kwargs)
                raise CircuitBreakerError(f"Circuit {breaker_name} est ouvert")
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except expected_exceptions as e:
                breaker.record_failure()
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = get_or_create_breaker(breaker_name)
            
            if not breaker.can_execute():
                logger.warning(f"Circuit ouvert pour {breaker_name}, requête rejetée")
                if fallback_function:
                    if asyncio.iscoroutinefunction(fallback_function):
                        return await fallback_function(*args, **kwargs)
                    return fallback_function(*args, **kwargs)
                raise CircuitBreakerError(f"Circuit {breaker_name} est ouvert")
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except expected_exceptions as e:
                breaker.record_failure()
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator

class CircuitBreakerError(Exception):
    """Exception levée lorsqu'un circuit est ouvert."""
    pass