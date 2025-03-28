"""Gestion des offsets Kafka pour reprise après panne."""
import json
import redis
from typing import Dict, Any

from app.config import settings

class OffsetStore:
    """Stockage persistant des offsets Kafka."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or redis.Redis.from_url(
            settings.REDIS_URL, password=settings.REDIS_PASSWORD, decode_responses=True
        )
        self.prefix = "kafka_offsets:"
        
    def save_offsets(self, consumer_group: str, offsets: Dict[str, Dict[int, int]]) -> bool:
        """
        Sauvegarde les offsets pour un groupe de consommateurs.
        
        Args:
            consumer_group: ID du groupe de consommateurs
            offsets: Dictionnaire {topic: {partition: offset}}
        """
        key = f"{self.prefix}{consumer_group}"
        return self.redis_client.set(key, json.dumps(offsets))
        
    def get_offsets(self, consumer_group: str) -> Dict[str, Dict[int, int]]:
        """
        Récupère les offsets pour un groupe de consommateurs.
        
        Args:
            consumer_group: ID du groupe de consommateurs
            
        Returns:
            Dictionnaire {topic: {partition: offset}}
        """
        key = f"{self.prefix}{consumer_group}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else {}