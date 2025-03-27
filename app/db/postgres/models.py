from app.models import (
    # CORE
    Country, Venue,
    
    # TEAM
    Team,
    
    # COMPETITION
    League, Season,
    
    # FIXTURE
    Fixture, FixtureStatus, FixtureScore,
    
    # BETTING
    Bookmaker, OddsType, OddsValue, Odds, Prediction
)

# Fonction pour convertir un objet modèle en dictionnaire
def model_to_dict(model_obj):
    """
    Convertit un objet modèle SQLAlchemy en dictionnaire.
    Ignore les relations pour éviter les dépendances circulaires.
    """
    if model_obj is None:
        return None
        
    result = {}
    for column in model_obj.__table__.columns:
        result[column.name] = getattr(model_obj, column.name)
    return result

# Dictionnaire pour mapper les types d'entités aux classes de modèles
ENTITY_MODEL_MAP = {
    # CORE
    'country': Country,
    'venue': Venue,
    
    # TEAM
    'team': Team,
    
    # COMPETITION
    'league': League,
    'season': Season,
    
    # FIXTURE
    'fixture': Fixture,
    'fixture_status': FixtureStatus,
    'fixture_score': FixtureScore,
    
    # BETTING
    'bookmaker': Bookmaker,
    'odds_type': OddsType,
    'odds_value': OddsValue,
    'odds': Odds,
    'prediction': Prediction
}

def get_model_by_entity_type(entity_type):
    """
    Récupère la classe de modèle correspondant à un type d'entité.
    
    Args:
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        
    Returns:
        Classe de modèle SQLAlchemy correspondante ou None si non trouvée
    """
    return ENTITY_MODEL_MAP.get(entity_type)