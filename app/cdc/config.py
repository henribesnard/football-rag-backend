"""
Configuration complète pour l'application football RAG avec intégration CDC.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Charger les variables d'environnement du fichier .env
load_dotenv()

class Settings(BaseSettings):
    # Informations de base de l'application
    APP_NAME: str = "Football RAG API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # PostgreSQL
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: str = Field(default="5432", env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    
    # Qdrant
    QDRANT_URL: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    QDRANT_API_KEY: str = Field(default=None, env="QDRANT_API_KEY")
    QDRANT_TIMEOUT: int = Field(default=30, env="QDRANT_TIMEOUT")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: str = Field(default=None, env="REDIS_PASSWORD")
    
    # Embedding
    EMBEDDING_MODEL: str = Field(default="e5-large-v2", env="EMBEDDING_MODEL")
    EMBEDDING_DIM: int = Field(default=1024, env="EMBEDDING_DIM")
    
    # JWT Auth
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Chemin pour les modèles Django importés
    DJANGO_MODELS_PATH: Path = Path(os.getenv("DJANGO_MODELS_PATH", "./django_models"))
    
    # Ingestion de données
    API_FOOTBALL_KEY: str = Field(default=None, env="API_FOOTBALL_KEY")
    
    # CDC (Change Data Capture) Configuration
    CDC_ENABLED: bool = Field(default=True, env="CDC_ENABLED")
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_GROUP_ID: str = Field(default="football-cdc-consumer", env="KAFKA_GROUP_ID")
    KAFKA_AUTO_OFFSET_RESET: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")
    CDC_BUFFER_SIZE: int = Field(default=100, env="CDC_BUFFER_SIZE")
    CDC_PROCESSING_BATCH_TIMEOUT: int = Field(default=60, env="CDC_PROCESSING_BATCH_TIMEOUT")
    CDC_LOG_LEVEL: str = Field(default="INFO", env="CDC_LOG_LEVEL")
    
    # Mapping des topics Kafka pour chaque table (préfixe : "football.public.")
    # BETTING
    KAFKA_TOPIC_BOOKMAKERS: str = "football.public.bookmakers"
    KAFKA_TOPIC_ODDS_HISTORY: str = "football.public.odds_history"
    KAFKA_TOPIC_ODDS_TYPES: str = "football.public.odds_types"
    KAFKA_TOPIC_ODDS_VALUES: str = "football.public.odds_values"
    KAFKA_TOPIC_ODDS: str = "football.public.odds"
    
    # COMPETITION
    KAFKA_TOPIC_LEAGUES: str = "football.public.leagues"
    KAFKA_TOPIC_SEASONS: str = "football.public.seasons"
    KAFKA_TOPIC_STANDINGS: str = "football.public.standings"
    KAFKA_TOPIC_TEAM_STATISTICS: str = "football.public.team_statistics"
    
    # CORE
    KAFKA_TOPIC_COUNTRIES: str = "football.public.countries"
    KAFKA_TOPIC_MEDIA_ASSETS: str = "football.public.media_assets"
    KAFKA_TOPIC_VENUES: str = "football.public.venues"
    
    # FIXTURE
    KAFKA_TOPIC_FIXTURE_EVENTS: str = "football.public.fixture_events"
    KAFKA_TOPIC_FIXTURE_STATUSES: str = "football.public.fixture_statuses"
    KAFKA_TOPIC_FIXTURES: str = "football.public.fixtures"
    KAFKA_TOPIC_FIXTURE_SCORES: str = "football.public.fixture_scores"
    KAFKA_TOPIC_FIXTURE_H2H: str = "football.public.fixture_h2h"
    KAFKA_TOPIC_FIXTURE_LINEUPS: str = "football.public.fixture_lineups"
    KAFKA_TOPIC_FIXTURE_LINEUP_PLAYERS: str = "football.public.fixture_lineup_players"
    KAFKA_TOPIC_FIXTURE_COACHES: str = "football.public.fixture_coaches"
    KAFKA_TOPIC_FIXTURE_STATISTICS: str = "football.public.fixture_statistics"
    KAFKA_TOPIC_PLAYER_STATISTICS: str = "football.public.player_statistics"
    
    # SYSTEM
    KAFKA_TOPIC_APP_METRICS: str = "football.public.app_metrics"
    KAFKA_TOPIC_PERFORMANCE_LOGS: str = "football.public.performance_logs"
    KAFKA_TOPIC_UPDATE_LOGS: str = "football.public.update_logs"
    
    # TEAM
    KAFKA_TOPIC_COACHES: str = "football.public.coaches"
    KAFKA_TOPIC_COACH_CAREERS: str = "football.public.coach_careers"
    KAFKA_TOPIC_PLAYERS: str = "football.public.players"
    KAFKA_TOPIC_PLAYER_TRANSFERS: str = "football.public.player_transfers"
    KAFKA_TOPIC_PLAYER_TEAMS: str = "football.public.player_teams"
    KAFKA_TOPIC_PLAYER_INJURIES: str = "football.public.player_injuries"
    KAFKA_TOPIC_TEAMS: str = "football.public.teams"
    KAFKA_TOPIC_TEAM_PLAYERS: str = "football.public.team_players"
    
    # USER
    KAFKA_TOPIC_ROLES: str = "football.public.roles"
    KAFKA_TOPIC_PERMISSIONS: str = "football.public.permissions"
    KAFKA_TOPIC_ROLE_PERMISSIONS: str = "football.public.role_permissions"
    KAFKA_TOPIC_USER_SESSIONS: str = "football.public.user_sessions"
    KAFKA_TOPIC_PASSWORD_RESETS: str = "football.public.password_resets"
    KAFKA_TOPIC_USERS: str = "football.public.users"
    KAFKA_TOPIC_USER_PROFILES: str = "football.public.user_profiles"
    
    # Mapping modèle-à-topic pour le système CDC
    @property
    def CDC_MODEL_TOPIC_MAPPING(self) -> dict:
        return {
            # BETTING
            'Bookmaker': self.KAFKA_TOPIC_BOOKMAKERS,
            'OddsHistory': self.KAFKA_TOPIC_ODDS_HISTORY,
            'OddsType': self.KAFKA_TOPIC_ODDS_TYPES,
            'OddsValue': self.KAFKA_TOPIC_ODDS_VALUES,
            'Odds': self.KAFKA_TOPIC_ODDS,
            
            # COMPETITION
            'League': self.KAFKA_TOPIC_LEAGUES,
            'Season': self.KAFKA_TOPIC_SEASONS,
            'Standing': self.KAFKA_TOPIC_STANDINGS,
            'TeamStatistics': self.KAFKA_TOPIC_TEAM_STATISTICS,
            
            # CORE
            'Country': self.KAFKA_TOPIC_COUNTRIES,
            'MediaAsset': self.KAFKA_TOPIC_MEDIA_ASSETS,
            'Venue': self.KAFKA_TOPIC_VENUES,
            
            # FIXTURE
            'FixtureEvent': self.KAFKA_TOPIC_FIXTURE_EVENTS,
            'FixtureStatus': self.KAFKA_TOPIC_FIXTURE_STATUSES,
            'Fixture': self.KAFKA_TOPIC_FIXTURES,
            'FixtureScore': self.KAFKA_TOPIC_FIXTURE_SCORES,
            'FixtureH2H': self.KAFKA_TOPIC_FIXTURE_H2H,
            'FixtureLineup': self.KAFKA_TOPIC_FIXTURE_LINEUPS,
            'FixtureLineupPlayer': self.KAFKA_TOPIC_FIXTURE_LINEUP_PLAYERS,
            'FixtureCoach': self.KAFKA_TOPIC_FIXTURE_COACHES,
            'FixtureStatistic': self.KAFKA_TOPIC_FIXTURE_STATISTICS,
            'PlayerStatistics': self.KAFKA_TOPIC_PLAYER_STATISTICS,
            
            # SYSTEM
            'AppMetrics': self.KAFKA_TOPIC_APP_METRICS,
            'PerformanceLog': self.KAFKA_TOPIC_PERFORMANCE_LOGS,
            'UpdateLog': self.KAFKA_TOPIC_UPDATE_LOGS,
            
            # TEAM
            'Coach': self.KAFKA_TOPIC_COACHES,
            'CoachCareer': self.KAFKA_TOPIC_COACH_CAREERS,
            'Player': self.KAFKA_TOPIC_PLAYERS,
            'PlayerTransfer': self.KAFKA_TOPIC_PLAYER_TRANSFERS,
            'PlayerTeam': self.KAFKA_TOPIC_PLAYER_TEAMS,
            'PlayerInjury': self.KAFKA_TOPIC_PLAYER_INJURIES,
            'Team': self.KAFKA_TOPIC_TEAMS,
            'TeamPlayer': self.KAFKA_TOPIC_TEAM_PLAYERS,
            
            # USER
            'Role': self.KAFKA_TOPIC_ROLES,
            'Permission': self.KAFKA_TOPIC_PERMISSIONS,
            'RolePermission': self.KAFKA_TOPIC_ROLE_PERMISSIONS,
            'UserSession': self.KAFKA_TOPIC_USER_SESSIONS,
            'PasswordReset': self.KAFKA_TOPIC_PASSWORD_RESETS,
            'User': self.KAFKA_TOPIC_USERS,
            'UserProfile': self.KAFKA_TOPIC_USER_PROFILES,
        }
    
    # Liste complète des topics à suivre
    @property
    def CDC_KAFKA_TOPICS(self) -> list:
        return list(self.CDC_MODEL_TOPIC_MAPPING.values())
    
    # Mapping table PostgreSQL à modèle
    @property
    def CDC_TABLE_MODEL_MAPPING(self) -> dict:
        return {
            # BETTING
            'bookmakers': 'Bookmaker',
            'odds_history': 'OddsHistory',
            'odds_types': 'OddsType',
            'odds_values': 'OddsValue',
            'odds': 'Odds',
            
            # COMPETITION
            'leagues': 'League',
            'seasons': 'Season',
            'standings': 'Standing',
            'team_statistics': 'TeamStatistics',
            
            # CORE
            'countries': 'Country',
            'media_assets': 'MediaAsset',
            'venues': 'Venue',
            
            # FIXTURE
            'fixture_events': 'FixtureEvent',
            'fixture_statuses': 'FixtureStatus',
            'fixtures': 'Fixture',
            'fixture_scores': 'FixtureScore',
            'fixture_h2h': 'FixtureH2H',
            'fixture_lineups': 'FixtureLineup',
            'fixture_lineup_players': 'FixtureLineupPlayer',
            'fixture_coaches': 'FixtureCoach',
            'fixture_statistics': 'FixtureStatistic',
            'player_statistics': 'PlayerStatistics',
            
            # SYSTEM
            'app_metrics': 'AppMetrics',
            'performance_logs': 'PerformanceLog',
            'update_logs': 'UpdateLog',
            
            # TEAM
            'coaches': 'Coach',
            'coach_careers': 'CoachCareer',
            'players': 'Player',
            'player_transfers': 'PlayerTransfer',
            'player_teams': 'PlayerTeam',
            'player_injuries': 'PlayerInjury',
            'teams': 'Team',
            'team_players': 'TeamPlayer',
            
            # USER
            'roles': 'Role',
            'permissions': 'Permission',
            'role_permissions': 'RolePermission',
            'user_sessions': 'UserSession',
            'password_resets': 'PasswordReset',
            'users': 'User',
            'user_profiles': 'UserProfile',
        }
    
    # Configuration des priorités de traitement des modèles (ordre d'importance pour les dépendances)
    @property
    def CDC_MODEL_PRIORITY(self) -> dict:
        return {
            # Niveau 1 - Modèles fondamentaux sans dépendances
            'Country': 1,
            'Permission': 1,
            'Role': 1,
            'Bookmaker': 1,
            'FixtureStatus': 1,
            'MediaAsset': 1,
            'OddsType': 1,
            
            # Niveau 2 - Modèles avec dépendances simples
            'Venue': 2,
            'League': 2,
            'OddsValue': 2,
            'RolePermission': 2,
            'User': 2,
            
            # Niveau 3 - Modèles avec plusieurs dépendances
            'Season': 3,
            'Team': 3,
            'UserProfile': 3,
            'UserSession': 3,
            'PasswordReset': 3,
            
            # Niveau 4 - Modèles dépendant de modèles de niveau 3
            'Coach': 4,
            'Player': 4,
            'TeamStatistics': 4,
            'Standing': 4,
            
            # Niveau 5 - Modèles avec dépendances complexes
            'CoachCareer': 5,
            'PlayerTransfer': 5,
            'PlayerTeam': 5, 
            'TeamPlayer': 5,
            'Fixture': 5,
            
            # Niveau 6 - Modèles dépendant de Fixture
            'FixtureScore': 6,
            'FixtureEvent': 6,
            'FixtureLineup': 6,
            'FixtureCoach': 6,
            'FixtureH2H': 6,
            'FixtureStatistic': 6,
            'PlayerStatistics': 6,
            'PlayerInjury': 6,
            'Odds': 6,
            
            # Niveau 7 - Modèles avec dépendances très spécifiques
            'FixtureLineupPlayer': 7,
            'OddsHistory': 7,
            
            # Niveau 8 - Logs et métriques (peuvent dépendre de tout)
            'AppMetrics': 8,
            'PerformanceLog': 8,
            'UpdateLog': 8
        }
    
    # Catégorisation des modèles pour le traitement des événements CDC
    @property
    def CDC_MODEL_CATEGORIES(self) -> dict:
        return {
            # Modèles prioritaires pour la recherche (à traiter immédiatement)
            'high_priority': [
                'Country', 'Team', 'Player', 'League', 'Fixture', 'Coach',
                'Venue', 'Standing', 'FixtureEvent'
            ],
            
            # Modèles avec données de référence (statistiques, métadonnées)
            'reference_data': [
                'Season', 'TeamStatistics', 'PlayerStatistics', 'FixtureStatistic',
                'FixtureLineup', 'FixtureLineupPlayer', 'FixtureScore'
            ],
            
            # Modèles avec données auxiliaires (moins critiques pour la recherche)
            'auxiliary_data': [
                'CoachCareer', 'PlayerTransfer', 'PlayerTeam', 'TeamPlayer',
                'PlayerInjury', 'FixtureH2H', 'FixtureCoach', 'MediaAsset'
            ],
            
            # Modèles liés aux paris (peuvent être traités séparément)
            'betting_data': [
                'Bookmaker', 'OddsType', 'OddsValue', 'Odds', 'OddsHistory'
            ],
            
            # Modèles liés aux utilisateurs et à la gestion des accès
            'user_data': [
                'User', 'UserProfile', 'Role', 'Permission', 'RolePermission',
                'UserSession', 'PasswordReset'
            ],
            
            # Modèles de logging et métriques (peuvent être traités en dernier)
            'system_data': [
                'AppMetrics', 'PerformanceLog', 'UpdateLog'
            ]
        }
    
    # Configuration des tampons circulaires spécifiques par catégorie
    @property
    def CDC_BUFFER_SIZES(self) -> dict:
        return {
            'high_priority': int(os.getenv("CDC_BUFFER_HIGH_PRIORITY", "50")),
            'reference_data': int(os.getenv("CDC_BUFFER_REFERENCE_DATA", "100")),
            'auxiliary_data': int(os.getenv("CDC_BUFFER_AUXILIARY_DATA", "150")),
            'betting_data': int(os.getenv("CDC_BUFFER_BETTING_DATA", "200")),
            'user_data': int(os.getenv("CDC_BUFFER_USER_DATA", "100")),
            'system_data': int(os.getenv("CDC_BUFFER_SYSTEM_DATA", "300"))
        }
    
    # Configuration des timeouts de traitement spécifiques par catégorie (en secondes)
    @property
    def CDC_PROCESSING_TIMEOUTS(self) -> dict:
        return {
            'high_priority': int(os.getenv("CDC_TIMEOUT_HIGH_PRIORITY", "30")),
            'reference_data': int(os.getenv("CDC_TIMEOUT_REFERENCE_DATA", "60")),
            'auxiliary_data': int(os.getenv("CDC_TIMEOUT_AUXILIARY_DATA", "120")),
            'betting_data': int(os.getenv("CDC_TIMEOUT_BETTING_DATA", "180")),
            'user_data': int(os.getenv("CDC_TIMEOUT_USER_DATA", "60")),
            'system_data': int(os.getenv("CDC_TIMEOUT_SYSTEM_DATA", "300"))
        }
    
    # Configuration de Qdrant pour le CDC (collections et indexation)
    @property
    def CDC_QDRANT_SETTINGS(self) -> dict:
        return {
            # Seuil pour déclencher l'optimisation des index
            'indexing_threshold': int(os.getenv("QDRANT_INDEXING_THRESHOLD", "20000")),
            
            # Taille des lots pour les opérations d'upsert
            'upsert_batch_size': int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "100")),
            
            # Nombre maximum de tentatives pour les opérations Qdrant
            'max_retries': int(os.getenv("QDRANT_MAX_RETRIES", "3")),
            
            # Délai entre les tentatives (en secondes)
            'retry_delay': int(os.getenv("QDRANT_RETRY_DELAY", "5"))
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Créer une instance des paramètres
settings = Settings()

# Configuration de la base de données PostgreSQL
POSTGRES_URI = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"