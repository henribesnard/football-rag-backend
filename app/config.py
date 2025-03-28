import os
import multiprocessing
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Charger les variables d'environnement du fichier .env
load_dotenv()

class Settings(BaseSettings):
    # Informations de base de l'application
    APP_NAME: str = "Football RAG API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Configuration du serveur
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=int(multiprocessing.cpu_count() * 1.5), env="WORKERS")
    MAX_CONCURRENT_CONNECTIONS: int = Field(default=1000, env="MAX_CONCURRENT_CONNECTIONS")
    FORWARDED_ALLOW_IPS: str = Field(default="*", env="FORWARDED_ALLOW_IPS")
    
    # Configuration CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # PostgreSQL
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: str = Field(default="5432", env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=1800, env="DB_POOL_RECYCLE")  # 30 minutes
    
    # Qdrant
    QDRANT_URL: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    QDRANT_API_KEY: str = Field(default=None, env="QDRANT_API_KEY")
    QDRANT_TIMEOUT: int = Field(default=30, env="QDRANT_TIMEOUT")
    QDRANT_CONNECTION_POOL_SIZE: int = Field(default=10, env="QDRANT_CONNECTION_POOL_SIZE")
    QDRANT_MAX_RETRIES: int = Field(default=3, env="QDRANT_MAX_RETRIES")
    QDRANT_RETRY_DELAY: float = Field(default=0.5, env="QDRANT_RETRY_DELAY")
    
    # Redis et Cache
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: str = Field(default=None, env="REDIS_PASSWORD")
    REDIS_POOL_SIZE: int = Field(default=20, env="REDIS_POOL_SIZE")
    REDIS_TIMEOUT: int = Field(default=5, env="REDIS_TIMEOUT")
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # 5 minutes par défaut
    CACHE_WARMUP_ENABLED: bool = Field(default=False, env="CACHE_WARMUP_ENABLED")
    
    # Embedding
    EMBEDDING_MODEL: str = Field(default="e5-large-v2", env="EMBEDDING_MODEL")
    EMBEDDING_DIM: int = Field(default=1024, env="EMBEDDING_DIM")
    FOOTBALL_EMBEDDING_MODEL: str = Field(default=None, env="FOOTBALL_EMBEDDING_MODEL")
    
    # LLM - OpenAI pour embeddings et génération
    OPENAI_API_KEY: str = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    OPENAI_CHAT_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_CHAT_MODEL")
    OPENAI_MAX_TOKENS: int = Field(default=1024, env="OPENAI_MAX_TOKENS")
    
    # DeepSeek pour génération spécifique football
    DEEPSEEK_API_KEY: str = Field(default=None, env="DEEPSEEK_API_KEY")
    
    # Circuit Breaker et Résilience
    CIRCUIT_BREAKER_DEFAULT_THRESHOLD: int = Field(default=5, env="CIRCUIT_BREAKER_DEFAULT_THRESHOLD")
    CIRCUIT_BREAKER_DEFAULT_TIMEOUT: int = Field(default=60, env="CIRCUIT_BREAKER_DEFAULT_TIMEOUT")
    RETRY_DEFAULT_ATTEMPTS: int = Field(default=3, env="RETRY_DEFAULT_ATTEMPTS")
    RETRY_DEFAULT_DELAY: float = Field(default=1.0, env="RETRY_DEFAULT_DELAY")
    RETRY_DEFAULT_BACKOFF: float = Field(default=2.0, env="RETRY_DEFAULT_BACKOFF")
    BULKHEAD_DEFAULT_MAX_CONCURRENT: int = Field(default=10, env="BULKHEAD_DEFAULT_MAX_CONCURRENT")
    
    # JWT Auth
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Chemin pour les modèles Django importés
    DJANGO_MODELS_PATH: Path = Path(os.getenv("DJANGO_MODELS_PATH", "./django_models"))
    
    # Ingestion de données
    API_FOOTBALL_KEY: str = Field(default=None, env="API_FOOTBALL_KEY")
    
    # Logs
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # CDC (Change Data Capture) Configuration
    CDC_ENABLED: bool = Field(default=True, env="CDC_ENABLED")
    CDC_AUTO_START: bool = Field(default=False, env="CDC_AUTO_START")
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_GROUP_ID: str = Field(default="football-cdc-consumer", env="KAFKA_GROUP_ID")
    KAFKA_AUTO_OFFSET_RESET: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")
    CDC_BUFFER_SIZE: int = Field(default=100, env="CDC_BUFFER_SIZE")
    CDC_PROCESSING_BATCH_TIMEOUT: int = Field(default=60, env="CDC_PROCESSING_BATCH_TIMEOUT")
    CDC_LOG_LEVEL: str = Field(default="INFO", env="CDC_LOG_LEVEL")
    CDC_MAX_WORKERS: int = Field(default=10, env="CDC_MAX_WORKERS")
    CDC_MAX_RETRY_COUNT: int = Field(default=5, env="CDC_MAX_RETRY_COUNT")
    CDC_RETRY_INTERVAL: int = Field(default=300, env="CDC_RETRY_INTERVAL")  # 5 minutes
    CDC_HEALTH_CHECK_INTERVAL: int = Field(default=60, env="CDC_HEALTH_CHECK_INTERVAL")  # 1 minute
    CDC_AUTO_RECOVERY: bool = Field(default=True, env="CDC_AUTO_RECOVERY")
    CDC_MAX_TOLERATED_ERRORS: int = Field(default=100, env="CDC_MAX_TOLERATED_ERRORS")
    
    # Configuration des files d'attente par catégorie
    CDC_BUFFER_SIZES: Dict[str, int] = {
        'high_priority': 50,
        'reference_data': 100,
        'auxiliary_data': 150,
        'betting_data': 200,
        'user_data': 100,
        'system_data': 300
    }
    
    # Configuration des timeouts de traitement spécifiques par catégorie (en secondes)
    CDC_PROCESSING_TIMEOUTS: Dict[str, int] = {
        'high_priority': 30,
        'reference_data': 60,
        'auxiliary_data': 120,
        'betting_data': 180,
        'user_data': 60,
        'system_data': 300
    }
    
    # Limites de concurrence par catégorie pour CDC
    CDC_CONCURRENCY: Dict[str, int] = {
        'high_priority': 5,
        'reference_data': 4,
        'auxiliary_data': 3,
        'betting_data': 3,
        'user_data': 3,
        'system_data': 2
    }
    
    # Configurations de performances pour Qdrant
    QDRANT_SETTINGS: Dict[str, Any] = {
        'indexing_threshold': 20000,
        'upsert_batch_size': 100,
        'max_retries': 3,
        'retry_delay': 5
    }
    
    # Configuration RAG
    RAG_MAX_CONTEXT_ITEMS: int = Field(default=5, env="RAG_MAX_CONTEXT_ITEMS")
    RAG_MIN_SCORE_THRESHOLD: float = Field(default=0.7, env="RAG_MIN_SCORE_THRESHOLD")
    RAG_USE_RERANKING: bool = Field(default=True, env="RAG_USE_RERANKING")
    RAG_DEFAULT_MODEL: str = Field(default="deepseek-chat", env="RAG_DEFAULT_MODEL")
    
    # Configuration du webhook pour les notifications
    LOW_RATING_WEBHOOK_URL: Optional[str] = Field(default=None, env="LOW_RATING_WEBHOOK_URL")
    
    # Configuration du monitoring
    MONITORING_ENABLED: bool = Field(default=True, env="MONITORING_ENABLED")
    
    # Liste complète des topics à suivre pour CDC
    @property
    def CDC_KAFKA_TOPICS(self) -> list:
        """Liste des topics Kafka à surveiller pour CDC."""
        return [
            "football.public.countries",
            "football.public.venues",
            "football.public.leagues",
            "football.public.seasons",
            "football.public.teams",
            "football.public.fixtures",
            "football.public.players",
            "football.public.standings",
            "football.public.bookmakers",
            "football.public.odds",
            "football.public.odds_types",
            "football.public.predictions"
        ]
    
    @property
    def CDC_MODEL_CATEGORIES(self) -> Dict[str, List[str]]:
        """Catégorisation des modèles pour CDC."""
        return {
            # Modèles prioritaires pour la recherche
            'high_priority': [
                'Country', 'Team', 'Player', 'League', 'Fixture', 'Coach',
                'Venue', 'Standing', 'FixtureEvent'
            ],
            
            # Modèles avec données de référence
            'reference_data': [
                'Season', 'TeamStatistics', 'PlayerStatistics', 'FixtureStatistic',
                'FixtureLineup', 'FixtureLineupPlayer', 'FixtureScore'
            ],
            
            # Modèles avec données auxiliaires
            'auxiliary_data': [
                'CoachCareer', 'PlayerTransfer', 'PlayerTeam', 'TeamPlayer',
                'PlayerInjury', 'FixtureH2H', 'FixtureCoach', 'MediaAsset'
            ],
            
            # Modèles liés aux paris
            'betting_data': [
                'Bookmaker', 'OddsType', 'OddsValue', 'Odds', 'OddsHistory'
            ],
            
            # Modèles liés aux utilisateurs
            'user_data': [
                'User', 'UserProfile', 'Role', 'Permission', 'RolePermission',
                'UserSession', 'PasswordReset'
            ],
            
            # Modèles de logging et métriques
            'system_data': [
                'AppMetrics', 'PerformanceLog', 'UpdateLog'
            ]
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Créer une instance des paramètres
settings = Settings()

# Configuration de la base de données PostgreSQL
POSTGRES_URI = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"