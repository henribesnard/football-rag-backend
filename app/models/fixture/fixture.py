from sqlalchemy import Column, Integer, String, DateTime, SmallInteger, ForeignKey, Boolean, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class FixtureStatus(Base):
    __tablename__ = 'fixture_statuses'
    
    id = Column(Integer, primary_key=True)
    short_code = Column(String(10), unique=True)
    long_description = Column(String(100))
    status_type = Column(String(20), index=True)  # scheduled, in_play, finished, etc.
    description = Column(String(255), nullable=True)
    
    # Relationships
    fixtures = relationship("Fixture", back_populates="status")
    
    # Indexes
    __table_args__ = (
        Index('ix_fixture_statuses_short_code_type', 'short_code', 'status_type'),
    )
    
    def __repr__(self):
        return f"<FixtureStatus(short_code='{self.short_code}', type='{self.status_type}')>"

class Fixture(Base, TimeStampMixin):
    __tablename__ = 'fixtures'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False, index=True)
    round = Column(String(100), nullable=True)
    home_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    away_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    date = Column(DateTime, index=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=True)
    referee = Column(String(100), nullable=True)
    status_id = Column(Integer, ForeignKey('fixture_statuses.id'), nullable=True, index=True)
    elapsed_time = Column(SmallInteger, nullable=True)
    timezone = Column(String(50), default="UTC")
    
    # Champs dénormalisés pour les performances
    home_score = Column(SmallInteger, nullable=True)
    away_score = Column(SmallInteger, nullable=True)
    is_finished = Column(Boolean, default=False)
    
    # Relationships
    league = relationship("League", back_populates="fixtures")
    season = relationship("Season", back_populates="fixtures")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_fixtures")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_fixtures")
    venue = relationship("Venue", back_populates="fixtures")
    status = relationship("FixtureStatus", back_populates="fixtures")
    scores = relationship("FixtureScore", back_populates="fixture")
    #events = relationship("FixtureEvent", back_populates="fixture")
    #statistics = relationship("FixtureStatistic", back_populates="fixture")
    #player_statistics = relationship("PlayerStatistics", back_populates="fixture")
    #lineups = relationship("FixtureLineup", back_populates="fixture")
    #h2h_references = relationship("FixtureH2H", foreign_keys="FixtureH2H.reference_fixture_id", back_populates="reference_fixture")
    #h2h_related = relationship("FixtureH2H", foreign_keys="FixtureH2H.related_fixture_id", back_populates="related_fixture")
    #injuries = relationship("PlayerInjury", back_populates="fixture")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_fixtures_date_status', 'date', 'status_id'),
        Index('ix_fixtures_league_season_date', 'league_id', 'season_id', 'date'),
        Index('ix_fixtures_home_away_season', 'home_team_id', 'away_team_id', 'season_id'),
        CheckConstraint('home_team_id != away_team_id', name='home_away_teams_different')
    )
    
    def __repr__(self):
        return f"<Fixture(id={self.id}, home_team_id={self.home_team_id}, away_team_id={self.away_team_id})>"

class FixtureScore(Base, TimeStampMixin):
    __tablename__ = 'fixture_scores'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    halftime = Column(SmallInteger, nullable=True)
    fulltime = Column(SmallInteger, nullable=True)
    extratime = Column(SmallInteger, nullable=True)
    penalty = Column(SmallInteger, nullable=True)
    
    # Relationships
    fixture = relationship("Fixture", back_populates="scores")
    team = relationship("Team")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_fixture_scores_fixture_team', 'fixture_id', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FixtureScore(fixture_id={self.fixture_id}, team_id={self.team_id})>"