"""
Module CDC (Change Data Capture) pour la synchronisation des données entre PostgreSQL et Qdrant.
"""
from app.cdc.manager import CDCManager
from app.cdc.consumer import CDCConsumer
from app.cdc.processor import CDCProcessor
from app.cdc.buffer import CircularBuffer

# Instance singleton du gestionnaire CDC
cdc_manager = None

def get_cdc_manager() -> CDCManager:
    """
    Obtient ou crée l'instance du gestionnaire CDC.
    
    Returns:
        Instance du gestionnaire CDC
    """
    global cdc_manager
    if cdc_manager is None:
        cdc_manager = CDCManager()
    return cdc_manager

__all__ = [
    'CDCManager',
    'CDCConsumer',
    'CDCProcessor',
    'CircularBuffer',
    'get_cdc_manager'
]