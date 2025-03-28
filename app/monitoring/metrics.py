"""Service de collecte de métriques pour le monitoring."""
import time
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Callable
from threading import Lock
import functools

logger = logging.getLogger(__name__)

class MetricsRegistry:
    """Registre central des métriques."""
    
    def __init__(self):
        self.counters = {}
        self.histograms = {}
        self.gauges = {}
        self._lock = Lock()
    
    def counter(self, name: str, description: str = "") -> 'Counter':
        """
        Crée ou récupère un compteur.
        
        Args:
            name: Nom du compteur
            description: Description du compteur
            
        Returns:
            Instance de Counter
        """
        with self._lock:
            if name not in self.counters:
                self.counters[name] = Counter(name, description)
            return self.counters[name]
    
    def histogram(self, name: str, description: str = "", buckets: List[float] = None) -> 'Histogram':
        """
        Crée ou récupère un histogramme.
        
        Args:
            name: Nom de l'histogramme
            description: Description de l'histogramme
            buckets: Liste des seuils pour les buckets
            
        Returns:
            Instance de Histogram
        """
        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = Histogram(name, description, buckets)
            return self.histograms[name]
    
    def gauge(self, name: str, description: str = "") -> 'Gauge':
        """
        Crée ou récupère une jauge.
        
        Args:
            name: Nom de la jauge
            description: Description de la jauge
            
        Returns:
            Instance de Gauge
        """
        with self._lock:
            if name not in self.gauges:
                self.gauges[name] = Gauge(name, description)
            return self.gauges[name]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Récupère toutes les métriques enregistrées.
        
        Returns:
            Dictionnaire des métriques
        """
        metrics = {}
        
        with self._lock:
            # Collecter les compteurs
            for name, counter in self.counters.items():
                metrics[name] = {
                    "type": "counter",
                    "description": counter.description,
                    "value": counter.value,
                    "labels": counter.labels
                }
            
            # Collecter les histogrammes
            for name, histogram in self.histograms.items():
                metrics[name] = {
                    "type": "histogram",
                    "description": histogram.description,
                    "count": histogram.count,
                    "sum": histogram.sum,
                    "buckets": histogram.buckets,
                    "values": histogram.values,
                    "labels": histogram.labels
                }
            
            # Collecter les jauges
            for name, gauge in self.gauges.items():
                metrics[name] = {
                    "type": "gauge",
                    "description": gauge.description,
                    "value": gauge.value,
                    "labels": gauge.labels
                }
        
        return metrics
    
    def reset(self) -> None:
        """Réinitialise toutes les métriques."""
        with self._lock:
            for counter in self.counters.values():
                counter.reset()
            
            for histogram in self.histograms.values():
                histogram.reset()
            
            for gauge in self.gauges.values():
                gauge.reset()

class Counter:
    """Compteur incrémental."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.value = 0
        self.labels = {}
        self._lock = Lock()
    
    def inc(self, value: int = 1) -> None:
        """Incrémente le compteur."""
        with self._lock:
            self.value += value
    
    def reset(self) -> None:
        """Réinitialise le compteur."""
        with self._lock:
            self.value = 0
    
    def with_labels(self, **labels) -> 'Counter':
        """
        Crée une instance spécifique avec des labels.
        
        Args:
            **labels: Labels sous forme de paires clé-valeur
            
        Returns:
            Instance de Counter avec labels
        """
        with self._lock:
            counter = Counter(self.name, self.description)
            counter.labels = labels
            return counter

class Histogram:
    """Histogramme pour distribution de valeurs."""
    
    def __init__(self, name: str, description: str = "", buckets: List[float] = None):
        self.name = name
        self.description = description
        self.buckets = buckets or [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10]
        self.values = []
        self.count = 0
        self.sum = 0
        self.labels = {}
        self._lock = Lock()
    
    def observe(self, value: float) -> None:
        """
        Enregistre une observation.
        
        Args:
            value: Valeur à enregistrer
        """
        with self._lock:
            self.values.append(value)
            self.count += 1
            self.sum += value
    
    @contextmanager
    def time(self):
        """
        Mesure le temps d'exécution d'un bloc de code.
        
        Yields:
            None
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe(duration)
    
    def reset(self) -> None:
        """Réinitialise l'histogramme."""
        with self._lock:
            self.values = []
            self.count = 0
            self.sum = 0
    
    def with_labels(self, **labels) -> 'Histogram':
        """
        Crée une instance spécifique avec des labels.
        
        Args:
            **labels: Labels sous forme de paires clé-valeur
            
        Returns:
            Instance de Histogram avec labels
        """
        with self._lock:
            histogram = Histogram(self.name, self.description, self.buckets)
            histogram.labels = labels
            return histogram

class Gauge:
    """Jauge pour valeurs variables."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.value = 0
        self.labels = {}
        self._lock = Lock()
    
    def set(self, value: float) -> None:
        """
        Définit la valeur de la jauge.
        
        Args:
            value: Nouvelle valeur
        """
        with self._lock:
            self.value = value
    
    def inc(self, value: float = 1) -> None:
        """
        Incrémente la jauge.
        
        Args:
            value: Valeur d'incrémentation
        """
        with self._lock:
            self.value += value
    
    def dec(self, value: float = 1) -> None:
        """
        Décrémente la jauge.
        
        Args:
            value: Valeur de décrémentation
        """
        with self._lock:
            self.value -= value
    
    def reset(self) -> None:
        """Réinitialise la jauge."""
        with self._lock:
            self.value = 0
    
    def with_labels(self, **labels) -> 'Gauge':
        """
        Crée une instance spécifique avec des labels.
        
        Args:
            **labels: Labels sous forme de paires clé-valeur
            
        Returns:
            Instance de Gauge avec labels
        """
        with self._lock:
            gauge = Gauge(self.name, self.description)
            gauge.labels = labels
            return gauge

# Instance singleton pour utilisation dans toute l'application
metrics = MetricsRegistry()

def timed(metric_name: str, description: str = ""):
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction.
    
    Args:
        metric_name: Nom de la métrique
        description: Description de la métrique
        
    Returns:
        Fonction décorée
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            histogram = metrics.histogram(metric_name, description)
            with histogram.time():
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            histogram = metrics.histogram(metric_name, description)
            with histogram.time():
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator