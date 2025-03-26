from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base, TimeStampMixin

# Table d'association entre User et Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class User(Base, TimeStampMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(100), nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship("UserSession", back_populates="user")
    password_resets = relationship("PasswordReset", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('ix_users_is_active', 'is_active'),
        Index('ix_users_email_username', 'email', 'username'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class UserProfile(Base, TimeStampMixin):
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    display_name = Column(String(100), nullable=True)
    language = Column(String(10), default='en')
    timezone = Column(String(50), default='UTC')
    
    # Préférences
    email_notifications = Column(Boolean, default=True)
    favorite_team_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    country = relationship("Country")
    favorite_team = relationship("Team")
    
    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id})>"