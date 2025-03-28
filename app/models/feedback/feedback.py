"""
Modèle pour la gestion des feedbacks utilisateurs sur les réponses du système RAG.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class UserFeedback(Base, TimeStampMixin):
    __tablename__ = 'user_feedback'
    
    id = Column(String(36), primary_key=True)  # UUID
    question_id = Column(String(36), nullable=False, index=True)  # UUID de la question
    response_id = Column(String(36), nullable=False, index=True)  # UUID de la réponse
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Nullable pour les feedbacks anonymes
    rating = Column(Integer, nullable=False)  # Note de 1 à 5
    comment = Column(Text, nullable=True)  # Commentaire optionnel
    feedback_type = Column(String(50), default='general', index=True)  # Type de feedback (general, accuracy, helpfulness, etc.)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="feedbacks")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_user_feedback_rating', 'rating'),
        Index('ix_user_feedback_created_at', 'created_at'),
        Index('ix_user_feedback_user_id_created_at', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UserFeedback(id='{self.id}', rating={self.rating}, user_id={self.user_id})>"