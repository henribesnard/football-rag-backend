# Import et expose tous les modèles pour faciliter l'accès
from app.models.base import Base
from app.models.core.country import Country
from app.models.core.venue import Venue
from app.models.team.team import Team
from app.models.team.player import Player, PlayerTransfer, PlayerTeam
from app.models.team.coach import Coach, CoachCareer
from app.models.competition.league import League, Season
from app.models.competition.standing import Standing
from app.models.fixture.fixture import Fixture, FixtureStatus
from app.models.fixture.event import FixtureEvent
from app.models.fixture.statistic import FixtureStatistic, PlayerStatistics
# ... autres imports

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
    # ... autres mappings
}

# Fonction helper pour obtenir un modèle par type d'entité
def get_model_by_entity_type(entity_type):
    return ENTITY_MODELS.get(entity_type)