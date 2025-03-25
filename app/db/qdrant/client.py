from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from app.config import settings

_client = None

def get_qdrant_client():
    """
    Singleton pattern pour récupérer ou créer une instance du client Qdrant.
    Retourne une instance partagée du client QdrantClient.
    """
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.QDRANT_TIMEOUT
        )
    return _client