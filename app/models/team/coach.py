from sqlalchemy import Column, Integer, String, Date, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Coach(Base, TimeStampMixin):
    __tablename__ = 'coaches'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    nationality_id = Column(Integer, ForeignKey('countries.id'), nullable=True)
    birth_date = Column(Date, nullable=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True, unique=True)
    photo_url = Column(String(255), nullable=True)
    
    # Champs dénormalisés pour les performances
    career_matches = Column(Integer, default=0)
    career_wins = Column(Integer, default=0)
    career_draws = Column(Integer, default=0)
    career_losses = Column(Integer, default=0)
    
    # Relationships
    nationality = relationship("Country", back_populates="coaches")
    team = relationship("Team", back_populates="current_coach")
    career_entries = relationship("CoachCareer", back_populates="coach")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_coaches_name_nationality', 'name', 'nationality_id'),
    )
    
    def __repr__(self):
        return f"<Coach(name='{self.name}', team_id={self.team_id})>"

class CoachCareer(Base, TimeStampMixin):
    __tablename__ = 'coach_careers'
    
    id = Column(Integer, primary_key=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True, index=True)
    role = Column(String(20))  # head_coach, assistant, youth_coach, interim
    start_date = Column(Date, index=True)
    end_date = Column(Date, nullable=True)
    matches = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    
    # Relationships
    coach = relationship("Coach", back_populates="career_entries")
    team = relationship("Team", back_populates="coach_history")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_coach_careers_coach_team', 'coach_id', 'team_id'),
        Index('ix_coach_careers_start_end_date', 'start_date', 'end_date'),
    )
    
    def __repr__(self):
        return f"<CoachCareer(coach_id={self.coach_id}, team_id={self.team_id})>"