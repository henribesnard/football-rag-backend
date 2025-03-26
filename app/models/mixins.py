"""
Mixins réutilisables pour les modèles SQLAlchemy.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, event
from sqlalchemy.ext.declarative import declared_attr
from typing import Optional, Any

class TimestampMixin:
    """
    Mixin ajoutant des champs de timestamp pour le suivi des modifications.
    """
    created_at = Column(DateTime, default=func.now(), nullable=False)
    update_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    update_by = Column(String(50), default="system")

class AuditMixin:
    """
    Mixin ajoutant des fonctionnalités d'audit complètes.
    Étend TimestampMixin avec des champs supplémentaires.
    """
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String(50), default="system", nullable=False)
    update_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    update_by = Column(String(50), default="system")
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(50), nullable=True)

class ExternalSourceMixin:
    """
    Mixin pour les entités qui sont synchronisées depuis des sources externes.
    """
    external_id = Column(Integer, index=True, nullable=True)
    external_source = Column(String(50), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="pending", nullable=False)  # pending, success, error
    sync_error = Column(String(255), nullable=True)  # Message d'erreur si sync_status="error"

class NameMixin:
    """
    Mixin pour les entités qui ont un nom et un code.
    """
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), nullable=True, index=True)
    slug = Column(String(255), nullable=True, index=True)
    description = Column(String(500), nullable=True)

class TableNameMixin:
    """
    Mixin pour générer automatiquement le nom de table à partir du nom de classe.
    Convertit CamelCase en snake_case et ajoute un 's' pour le pluriel.
    """
    @declared_attr
    def __tablename__(cls) -> str:
        name = cls.__name__
        # CamelCase to snake_case
        result = name[0].lower()
        for c in name[1:]:
            if c.isupper():
                result += '_' + c.lower()
            else:
                result += c
        # Add 's' for plural if not already ending with 's'
        if not result.endswith('s'):
            result += 's'
        return result

class SoftDeleteMixin:
    """
    Mixin pour implémentation de la suppression logique (soft delete).
    """
    is_deleted = Column(Boolean, default=False, index=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(50), nullable=True)

    @classmethod
    def __declare_last__(cls):
        """
        Hook appelé après la création de la classe.
        Utilisé pour configurer les événements de requête.
        """
        @event.listens_for(cls.query, "before_compile", retval=True)
        def _before_compile(query: Any) -> Any:
            """
            Filtre les objets supprimés logiquement automatiquement.
            """
            for ent in query._entities:
                if hasattr(ent.entity_zero, "entity"):
                    entity = ent.entity_zero.entity
                    if hasattr(entity, "is_deleted"):
                        query = query.enable_assertions(False).filter(entity.is_deleted == False)
            return query

    def soft_delete(self, deleted_by: Optional[str] = None) -> None:
        """
        Effectue une suppression logique de l'objet.
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if deleted_by:
            self.deleted_by = deleted_by