# Import et expose tous les modèles pour faciliter l'accès
from app.models.base import Base
from app.models.core.country import Country
from app.models.core.venue import Venue
from app.models.team.team import Team
from app.models.team.player import Player, PlayerTransfer, PlayerTeam
from app.models.team.coach import Coach, CoachCareer
from app.models.competition.league import League, Season
from app.models.competition.standing import Standing
from app.models.competition.stats import TeamStatistics
from app.models.fixture.fixture import Fixture, FixtureStatus
from app.models.fixture.event import FixtureEvent
from app.models.fixture.statistic import FixtureStatistic, PlayerStatistics
from app.models.fixture.lineup import FixtureLineup, FixtureLineupPlayer
from app.models.fixture.h2h import FixtureH2H
from app.models.betting.bookmaker import Bookmaker
from app.models.betting.odds import OddsType, OddsValue, Odds
from app.models.betting.history import OddsHistory
from app.models.system.updatelog import UpdateLog

# Dictionnaire de tous les modèles par type d'entité pour un accès facile
ENTITY_MODELS = {
    'country': Country,
    'venue': Venue,
    'team': Team,
    'player': Player,
    'coach': Coach,
    'league': League,
    'season': Season,
    'fixture': Fixture,
    'fixture_event': FixtureEvent,
    'fixture_lineup': FixtureLineup,
    'fixture_statistic': FixtureStatistic,
    'player_statistics': PlayerStatistics,
    'standing': Standing,
    'team_statistics': TeamStatistics,
    'bookmaker': Bookmaker,
    'odds': Odds,
    'odds_type': OddsType,
    'odds_value': OddsValue,
    'odds_history': OddsHistory,
    'player_transfer': PlayerTransfer,
    'player_team': PlayerTeam,
    'fixture_h2h': FixtureH2H,
    'update_log': UpdateLog
}

# Fonction helper pour obtenir un modèle par type d'entité
def get_model_by_entity_type(entity_type):
    return ENTITY_MODELS.get(entity_type)