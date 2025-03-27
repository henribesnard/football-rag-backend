from app.models.base import Base
from app.models.constants import *

# CORE
from app.models.core.country import Country
from app.models.core.venue import Venue
from app.models.core.media import MediaAsset

# TEAM
from app.models.team.team import Team

# COMPETITION
from app.models.competition.league import League, Season

# FIXTURE
from app.models.fixture.fixture import Fixture, FixtureStatus, FixtureScore

# BETTING
from app.models.betting.bookmaker import Bookmaker
from app.models.betting.odds import OddsType, OddsValue, Odds


# USER
from app.models.user.user import User, UserProfile
from app.models.user.role import Role, Permission, RolePermission
from app.models.user.session import UserSession, PasswordReset

# SYSTEM
from app.models.system.updatelog import UpdateLog

# Dictionnaire de tous les modèles par type d'entité pour un accès facile
ENTITY_MODELS = {
    # CORE
    'country': Country,
    'venue': Venue,
    'media_asset': MediaAsset,
    
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
}

# Fonction helper pour obtenir un modèle par type d'entité
def get_model_by_entity_type(entity_type):
    return ENTITY_MODELS.get(entity_type)