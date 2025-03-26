from app.models import (
    # CORE
    Country, Venue, MediaAsset,
    
    # TEAM
    Team, TeamPlayer, Player, PlayerTransfer, PlayerTeam, PlayerInjury, 
    Coach, CoachCareer,
    
    # COMPETITION
    League, Season, Standing, TeamStatistics,
    
    # FIXTURE
    Fixture, FixtureStatus, FixtureScore, FixtureEvent, FixtureStatistic, 
    PlayerStatistics, FixtureLineup, FixtureLineupPlayer, FixtureCoach, FixtureH2H,
    
    # BETTING
    Bookmaker, OddsType, OddsValue, Odds, OddsHistory,
    
    # USER
    User, UserProfile, Role, Permission, RolePermission, UserSession, PasswordReset,
    
    # SYSTEM
    UpdateLog, AppMetrics, PerformanceLog
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
    'media_asset': MediaAsset,
    
    # TEAM
    'team': Team,
    'team_player': TeamPlayer,
    'player': Player,
    'player_transfer': PlayerTransfer,
    'player_team': PlayerTeam,
    'player_injury': PlayerInjury,
    'coach': Coach,
    'coach_career': CoachCareer,
    
    # COMPETITION
    'league': League,
    'season': Season,
    'standing': Standing,
    'team_statistics': TeamStatistics,
    
    # FIXTURE
    'fixture': Fixture,
    'fixture_status': FixtureStatus,
    'fixture_score': FixtureScore,
    'fixture_event': FixtureEvent,
    'fixture_statistic': FixtureStatistic,
    'player_statistics': PlayerStatistics,
    'fixture_lineup': FixtureLineup,
    'fixture_lineup_player': FixtureLineupPlayer,
    'fixture_coach': FixtureCoach,
    'fixture_h2h': FixtureH2H,
    
    # BETTING
    'bookmaker': Bookmaker,
    'odds_type': OddsType,
    'odds_value': OddsValue,
    'odds': Odds,
    'odds_history': OddsHistory,
    
    # USER
    'user': User,
    'user_profile': UserProfile,
    'role': Role,
    'permission': Permission,
    'role_permission': RolePermission,
    'user_session': UserSession,
    'password_reset': PasswordReset,
    
    # SYSTEM
    'update_log': UpdateLog,
    'app_metrics': AppMetrics,
    'performance_log': PerformanceLog
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