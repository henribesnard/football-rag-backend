from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimeStampMixin

class MediaType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"

class MediaAsset(Base, TimeStampMixin):
    """
    Modèle pour gérer les ressources média (images, vidéos, documents).
    """
    __tablename__ = 'media_assets'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(20), nullable=False, index=True)  # Type de média (image, vidéo, document)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=True)  # Chemin relatif si stocké localement
    mime_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=True)  # Taille en octets
    width = Column(Integer, nullable=True)  # Pour les images et vidéos
    height = Column(Integer, nullable=True)  # Pour les images et vidéos
    duration = Column(Integer, nullable=True)  # Pour les vidéos (en secondes)
    is_public = Column(Boolean, default=True)
    
    # Métadonnées pour le référencement
    alt_text = Column(String(255), nullable=True)
    tags = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<MediaAsset(id={self.id}, type='{self.type}', title='{self.title}')>"