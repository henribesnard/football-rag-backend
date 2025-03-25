from sqlalchemy import Column, Integer, String, Boolean, SmallInteger, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin

class Team(Base, TimestampMixin):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    code = Column(String(5), nullable=True, index=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    founded = Column(SmallInteger, nullable=True)
    is_national = Column(Boolean, default=False)
    logo_url = Column(String(255), nullable=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=True)
    
    # Champs dénormalisés pour les performances
    total_matches = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_draws = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    total_goals_scored = Column(Integer, default=0)
    total_goals_conceded = Column(Integer, default=0)
    
    # Relationships
    country = relationship("Country", back_populates="teams")
    venue = relationship("Venue", back_populates="teams")
    players = relationship("Player", back_populates="team")
    home_fixtures = relationship("Fixture", foreign_keys="Fixture.home_team_id", back_populates="home_team")
    away_fixtures = relationship("Fixture", foreign_keys="Fixture.away_team_id", back_populates="away_team")
    current_coach = relationship("Coach", uselist=False, back_populates="team")
    coach_history = relationship("CoachCareer", back_populates="team")
    squad = relationship("TeamPlayer", back_populates="team")
    standings = relationship("Standing", back_populates="team")
    team_statistics = relationship("TeamStatistics", back_populates="team")
    transfers_in = relationship("PlayerTransfer", foreign_keys="PlayerTransfer.team_in_id", back_populates="team_in")
    transfers_out = relationship("PlayerTransfer", foreign_keys="PlayerTransfer.team_out_id", back_populates="team_out")
    player_history = relationship("PlayerTeam", back_populates="team")
    
    # Indexes et validations
    __table_args__ = (
        Index('ix_teams_name_country_id', 'name', 'country_id'),
        Index('ix_teams_external_id', 'external_id'),
        CheckConstraint('founded >= 1800 AND founded <= 2100', name='check_founded_range'),
    )
    
    def __repr__(self):
        return f"<Team(name='{self.name}')>"