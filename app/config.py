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
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Créer une instance des paramètres
settings = Settings()

# Configuration de la base de données PostgreSQL
POSTGRES_URI = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"