from app.models import (
    Country, Venue, League, Team, Season, FixtureStatus, Fixture, FixtureScore,
    FixtureEvent, FixtureStatistic, FixtureLineup, FixtureLineupPlayer,
    Player, PlayerStatistics, PlayerInjury, Coach, CoachCareer, Bookmaker,
    OddsType, OddsValue, Odds, OddsHistory, Standing, FixtureH2H, PlayerTransfer,
    PlayerTeam, TeamStatistics, UpdateLog
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
    'country': Country,
    'venue': Venue,
    'league': League,
    'team': Team,
    'season': Season,
    'fixture': Fixture,
    'fixture_event': FixtureEvent,
    'fixture_statistic': FixtureStatistic,
    'player': Player,
    'player_statistics': PlayerStatistics,
    'coach': Coach,
    'coach_career': CoachCareer,
    'standing': Standing,
    'team_statistics': TeamStatistics,
    'player_transfer': PlayerTransfer,
    'player_team': PlayerTeam,
    'fixture_h2h': FixtureH2H,
    'odds': Odds,
    'bookmaker': Bookmaker,
    'update_log': UpdateLog,
    'fixture_lineup': FixtureLineup,
    'fixture_lineup_player': FixtureLineupPlayer,
    'fixture_score': FixtureScore,
    'player_injury': PlayerInjury,
    'odds_type': OddsType,
    'odds_value': OddsValue,
    'odds_history': OddsHistory,
    'fixture_status': FixtureStatus
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