"""Fusion d'événements CDC consécutifs pour optimiser le traitement."""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def merge_consecutive_events(events: List[Dict[str, Any]], entity_id_key: str = 'id') -> List[Dict[str, Any]]:
    """
    Fusionne les événements consécutifs concernant la même entité.
    Conserve uniquement l'événement le plus récent pour chaque entité.
    
    Args:
        events: Liste d'événements CDC
        entity_id_key: Clé pour identifier l'ID de l'entité
        
    Returns:
        Liste d'événements fusionnés
    """
    if not events:
        return []
        
    merged_events = {}
    for event in events:
        # Vérifier si l'événement contient les données attendues
        if 'value' not in event or 'after' not in event['value']:
            logger.warning(f"Format d'événement inattendu: {event}")
            continue
            
        # Récupérer l'ID de l'entité
        entity_id = event['value']['after'].get(entity_id_key)
        if not entity_id:
            logger.warning(f"ID d'entité non trouvé pour l'événement: {event}")
            continue
            
        # Conserver uniquement l'événement le plus récent pour chaque entité
        merged_events[entity_id] = event
    
    return list(merged_events.values())