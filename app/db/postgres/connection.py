# app/db/postgres/connection.py
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings, POSTGRES_URI

logger = logging.getLogger(__name__)

# Créer l'engine SQLAlchemy avec connection pooling
engine = create_engine(
    POSTGRES_URI,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800  # Recycler les connexions après 30 minutes
)

# Créer une factory de session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles SQLAlchemy
Base = declarative_base()

def get_db_session() -> Session:
    """
    Obtient une session de base de données.
    À utiliser directement quand le contexte manager n'est pas pratique.
    """
    return SessionLocal()

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager pour obtenir une session de base de données.
    Gère automatiquement le commit/rollback et la fermeture de session.
    
    Exemple:
    ```
    with get_db() as db:
        result = db.query(SomeModel).filter(SomeModel.id == 1).first()
    ```
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()