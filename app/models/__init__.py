from app.models.base import Base
from app.models.constants import *

# CORE
from app.models.core.country import Country
from app.models.core.venue import Venue
from app.models.core.media import MediaAsset

# TEAM
from app.models.team.team import Team, TeamPlayer
from app.models.team.player import Player, PlayerTransfer, PlayerTeam, PlayerInjury
from app.models.team.coach import Coach, CoachCareer

# COMPETITION
from app.models.competition.league import League, Season
from app.models.competition.standing import Standing
from app.models.competition.stats import TeamStatistics

# FIXTURE
from app.models.fixture.fixture import Fixture, FixtureStatus, FixtureScore
from app.models.fixture.event import FixtureEvent
from app.models.fixture.statistic import FixtureStatistic, PlayerStatistics
from app.models.fixture.lineup import FixtureLineup, FixtureLineupPlayer, FixtureCoach
from app.models.fixture.h2h import FixtureH2H

# BETTING
from app.models.betting.bookmaker import Bookmaker
from app.models.betting.odds import OddsType, OddsValue, Odds
from app.models.betting.history import OddsHistory

# USER
from app.models.user.user import User, UserProfile
from app.models.user.role import Role, Permission, RolePermission
from app.models.user.session import UserSession, PasswordReset

# SYSTEM
from app.models.system.updatelog import UpdateLog
from app.models.system.metrics import AppMetrics, PerformanceLog

# Dictionnaire de tous les modèles par type d'entité pour un accès facile
ENTITY_MODELS = {
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

# Fonction helper pour obtenir un modèle par type d'entité
def get_model_by_entity_type(entity_type):
    return ENTITY_MODELS.get(entity_type)