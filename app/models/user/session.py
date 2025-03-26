from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta

from app.models.base import Base, TimeStampMixin

class UserSession(Base, TimeStampMixin):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True, nullable=True)
    ip_address = Column(String(45), nullable=True)  # Pour IPv6
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, nullable=True)
    device_info = Column(String(255), nullable=True)  # Info sur le dispositif (mobile, desktop, etc.)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('ix_user_sessions_token', 'token'),
        Index('ix_user_sessions_expires_is_active', 'expires_at', 'is_active'),
    )
    
    @property
    def is_expired(self):
        """Vérifie si la session est expirée."""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, is_active={self.is_active})>"

class PasswordReset(Base, TimeStampMixin):
    __tablename__ = 'password_resets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    token = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="password_resets")
    
    # Indexes
    __table_args__ = (
        Index('ix_password_resets_token', 'token'),
        Index('ix_password_resets_expires_is_used', 'expires_at', 'is_used'),
    )
    
    @property
    def is_expired(self):
        """Vérifie si le token de réinitialisation est expiré."""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<PasswordReset(user_id={self.user_id}, is_used={self.is_used})>"