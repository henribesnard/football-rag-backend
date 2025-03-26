"""
Utilitaire pour convertir entre les modèles SQLAlchemy et les formats de données Qdrant.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app.models import (
    Country, Venue, League, Team, Player, Fixture, Coach, FixtureEvent,
    PlayerStatistics, Standing, TeamStatistics
)
from app.utils.text_processing import create_entity_text
from app.db.postgres.models import model_to_dict, get_model_by_entity_type
from app.db.postgres.connection import get_db_session

def model_to_vector_payload(
    model_instance: Any,
    entity_type: str,
    vector: List[float]
) -> Dict[str, Any]:
    """
    Convertit une instance de modèle SQLAlchemy en format compatible avec Qdrant.
    
    Args:
        model_instance: Instance du modèle SQLAlchemy
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        vector: Vecteur d'embedding
    
    Returns:
        Dictionnaire formaté pour l'insertion dans Qdrant
    """
    # Identifiant et vecteur communs à tous les types
    result = {
        "id": model_instance.id,
        "vector": vector
    }
    
    # Convertir l'objet modèle en dictionnaire
    model_dict = model_to_dict(model_instance)
    
    # Traiter les timestamps pour qu'ils soient JSON-serializable
    for key, value in model_dict.items():
        if isinstance(value, datetime):
            model_dict[key] = value.isoformat()
    
    # Ajouter le dictionnaire comme payload
    result["payload"] = model_dict
    
    # Ajouter du texte enrichi pour améliorer la recherche sémantique
    rich_text = create_entity_text(model_instance, entity_type)
    if rich_text:
        result["payload"]["text_content"] = rich_text
    
    return result

def get_entity_by_id(entity_type: str, entity_id: int) -> Optional[Any]:
    """
    Récupère une instance de modèle par son ID et type d'entité.
    
    Args:
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        entity_id: ID de l'entité
    
    Returns:
        Instance du modèle ou None si non trouvée
    """
    model_class = get_model_by_entity_type(entity_type)
    if not model_class:
        return None
    
    session = get_db_session()
    try:
        return session.query(model_class).filter(model_class.id == entity_id).first()
    except Exception:
        return None
    finally:
        session.close()