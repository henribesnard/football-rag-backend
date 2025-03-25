# app/db/postgres/models.py
import sys
import os
from pathlib import Path
import importlib.util
from contextlib import contextmanager

from app.config import settings

# Ajouter le chemin des modèles Django au sys.path pour l'importation
sys.path.append(str(settings.DJANGO_MODELS_PATH))

# Importer les modèles et constantes Django
def import_module_from_path(module_name, file_path):
    """Importe un module Python à partir d'un chemin de fichier."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Could not find module {module_name} at {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

try:
    # Importer les constantes
    constants = import_module_from_path("constants", settings.DJANGO_MODELS_PATH / "constants.py")
    
    # Importer les modèles
    django_models = import_module_from_path("models", settings.DJANGO_MODELS_PATH / "models.py")
    
    # Exposer les classes de modèles importantes
    Country = django_models.Country
    Venue = django_models.Venue
    League = django_models.League
    Team = django_models.Team
    Season = django_models.Season
    FixtureStatus = django_models.FixtureStatus
    Fixture = django_models.Fixture
    FixtureScore = django_models.FixtureScore
    FixtureEvent = django_models.FixtureEvent
    FixtureStatistic = django_models.FixtureStatistic
    FixtureLineup = django_models.FixtureLineup
    FixtureLineupPlayer = django_models.FixtureLineupPlayer
    FixtureCoach = django_models.FixtureCoach
    Player = django_models.Player
    FixturePlayerStatistic = django_models.FixturePlayerStatistic
    PlayerStatistics = django_models.PlayerStatistics
    PlayerInjury = django_models.PlayerInjury
    Coach = django_models.Coach
    CoachCareer = django_models.CoachCareer
    Bookmaker = django_models.Bookmaker
    OddsType = django_models.OddsType
    OddsValue = django_models.OddsValue
    Odds = django_models.Odds
    OddsHistory = django_models.OddsHistory
    Standing = django_models.Standing
    FixtureH2H = django_models.FixtureH2H
    PlayerSideline = django_models.PlayerSideline
    PlayerTransfer = django_models.PlayerTransfer
    PlayerTeam = django_models.PlayerTeam
    TeamPlayer = django_models.TeamPlayer
    TeamStatistics = django_models.TeamStatistics
    UpdateLog = django_models.UpdateLog
    
    # Exposer les constantes importantes
    PlayerPosition = constants.PlayerPosition
    LeagueType = constants.LeagueType
    FixtureStatusType = constants.FixtureStatusType
    EventType = constants.EventType
    StatType = constants.StatType
    InjurySeverity = constants.InjurySeverity
    InjuryStatus = constants.InjuryStatus
    CoachRole = constants.CoachRole
    OddsCategory = constants.OddsCategory
    OddsStatus = constants.OddsStatus
    TransferType = constants.TransferType
    UpdateType = constants.UpdateType
    OddsMovement = constants.OddsMovement
    
except ImportError as e:
    raise ImportError(f"Erreur lors de l'importation des modèles Django: {str(e)}")

# Function to access Django models using SQLAlchemy session
def map_django_model_to_dict(django_obj):
    """
    Convertit un objet modèle Django en dictionnaire.
    Ignore les champs de relations pour éviter les dépendances circulaires.
    """
    result = {}
    for field in django_obj._meta.fields:
        field_name = field.name
        if field_name not in ["id", "pk"] and not field_name.endswith("_id"):
            result[field_name] = getattr(django_obj, field_name)
    return result