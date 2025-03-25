"""
Base de définition pour les modèles SQLAlchemy.
Contient la classe Base et les fonctions communes utilisées par les modèles.
"""
from typing import Any, Dict, Type, List, Optional, TypeVar, cast
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, Query
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import SQLAlchemyError
import logging

# Création de la classe de base pour tous les modèles
Base = declarative_base()

# TypeVar pour les annotations de type - définition corrigée
Model = TypeVar('Model')

logger = logging.getLogger(__name__)

class ModelOperationsMixin:
    """
    Mixin ajoutant des opérations CRUD communes à tous les modèles.
    """

    @classmethod
    def get_by_id(cls, session: Session, id: int) -> Optional[Any]:
        """
        Récupère une instance par son ID.
        
        Args:
            session: Session SQLAlchemy
            id: ID de l'instance à récupérer
            
        Returns:
            L'instance ou None si elle n'existe pas
        """
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all(cls, session: Session, **filters) -> List[Any]:
        """
        Récupère toutes les instances avec filtres optionnels.
        
        Args:
            session: Session SQLAlchemy
            **filters: Filtres à appliquer (attribut=valeur)
            
        Returns:
            Liste d'instances
        """
        query = session.query(cls)
        for attr, value in filters.items():
            if hasattr(cls, attr):
                query = query.filter(getattr(cls, attr) == value)
        return query.all()

    @classmethod
    def create(cls, session: Session, **kwargs) -> Any:
        """
        Crée une nouvelle instance.
        
        Args:
            session: Session SQLAlchemy
            **kwargs: Attributs pour l'instance
            
        Returns:
            Nouvelle instance
        """
        instance = cls(**kwargs)
        session.add(instance)
        session.flush()  # Pour obtenir l'ID sans commit
        return instance

    def update(self, session: Session, **kwargs) -> Any:
        """
        Met à jour l'instance avec les valeurs fournies.
        
        Args:
            session: Session SQLAlchemy
            **kwargs: Attributs à mettre à jour
            
        Returns:
            Instance mise à jour
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        session.flush()
        return self

    def delete(self, session: Session) -> bool:
        """
        Supprime l'instance.
        
        Args:
            session: Session SQLAlchemy
            
        Returns:
            True si supprimé avec succès
        """
        try:
            session.delete(self)
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la suppression: {str(e)}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire des attributs (sans les relations)
        """
        return {c.key: getattr(self, c.key)
                for c in inspect(self.__class__).mapper.column_attrs}

def get_or_create(session: Session, model: Type[Any], **kwargs) -> tuple[Any, bool]:
    """
    Récupère une instance existante ou en crée une nouvelle.
    
    Args:
        session: Session SQLAlchemy
        model: Classe du modèle
        **kwargs: Attributs pour la recherche et la création
        
    Returns:
        Tuple (instance, created) où created est True si l'instance a été créée
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.flush()
        return instance, True