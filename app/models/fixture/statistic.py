from sqlalchemy import Column, Integer, String, SmallInteger, ForeignKey, DECIMAL, Boolean, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class FixtureStatistic(Base, TimeStampMixin):
    __tablename__ = 'fixture_statistics'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    stat_type = Column(String(50), index=True)  # shots_on_goal, possession, etc.
    value = Column(DECIMAL(7, 2), nullable=False)
    
    # Relationships
    fixture = relationship("Fixture", back_populates="statistics")
    team = relationship("Team")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_fixture_statistics_fixture_team_type', 'fixture_id', 'team_id', 'stat_type'),
    )
    
    def __repr__(self):
        return f"<FixtureStatistic(fixture_id={self.fixture_id}, team_id={self.team_id}, stat_type='{self.stat_type}')>"

class PlayerStatistics(Base, TimeStampMixin):
    __tablename__ = 'player_statistics'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    
    # Données de jeu
    minutes_played = Column(SmallInteger, nullable=True)
    position = Column(String(2), nullable=True)
    number = Column(SmallInteger, nullable=True)
    rating = Column(DECIMAL(3, 1), nullable=True)
    is_captain = Column(Boolean, default=False)
    is_substitute = Column(Boolean, default=False)
    
    # Statistiques offensives
    shots_total = Column(SmallInteger, default=0)
    shots_on_target = Column(SmallInteger, default=0)
    goals = Column(SmallInteger, default=0)
    assists = Column(SmallInteger, default=0)
    
    # Passes
    passes = Column(SmallInteger, default=0)
    key_passes = Column(SmallInteger, default=0)
    pass_accuracy = Column(DECIMAL(5, 2), nullable=True)
    
    # Défense
    tackles = Column(SmallInteger, default=0)
    interceptions = Column(SmallInteger, default=0)
    
    # Duels
    duels_total = Column(SmallInteger, default=0)
    duels_won = Column(SmallInteger, default=0)
    
    # Dribbles
    dribbles_success = Column(SmallInteger, default=0)
    
    # Fautes
    fouls_committed = Column(SmallInteger, default=0)
    fouls_drawn = Column(SmallInteger, default=0)
    
    # Cartons
    yellow_cards = Column(SmallInteger, default=0)
    red_cards = Column(SmallInteger, default=0)
    
    # Relationships
    player = relationship("Player", back_populates="statistics")
    fixture = relationship("Fixture", back_populates="player_statistics")
    team = relationship("Team")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_player_statistics_player_fixture', 'player_id', 'fixture_id'),
        Index('ix_player_statistics_rating', 'rating'),
        Index('ix_player_statistics_goals', 'goals'),
        Index('ix_player_statistics_assists', 'assists'),
        CheckConstraint('shots_on_target <= shots_total', name='shots_on_target_lte_total'),
        CheckConstraint('duels_won <= duels_total', name='duels_won_lte_total')
    )
    
    def __repr__(self):
        return f"<PlayerStatistics(player_id={self.player_id}, fixture_id={self.fixture_id})>"