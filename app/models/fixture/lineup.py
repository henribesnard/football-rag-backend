from sqlalchemy import Column, Integer, String, SmallInteger, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class FixtureLineup(Base, TimeStampMixin):
    """Représente la composition d'une équipe pour un match."""
    __tablename__ = 'fixture_lineups'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    formation = Column(String(10))  # Ex: "4-3-3" ou "4-3-1-2"
    
    # Couleurs de l'équipe pour ce match
    player_primary_color = Column(String(6), nullable=True)
    player_number_color = Column(String(6), nullable=True)
    player_border_color = Column(String(6), nullable=True)
    goalkeeper_primary_color = Column(String(6), nullable=True)
    goalkeeper_number_color = Column(String(6), nullable=True)
    goalkeeper_border_color = Column(String(6), nullable=True)
    
    # Relationships
    fixture = relationship("Fixture", back_populates="lineups")
    team = relationship("Team")
    players = relationship("FixtureLineupPlayer", back_populates="lineup")
    
    # Indexes
    __table_args__ = (
        Index('ix_fixture_lineups_fixture_team', 'fixture_id', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FixtureLineup(fixture_id={self.fixture_id}, team_id={self.team_id}, formation='{self.formation}')>"

class FixtureLineupPlayer(Base, TimeStampMixin):
    """Représente un joueur dans la composition d'équipe."""
    __tablename__ = 'fixture_lineup_players'
    
    id = Column(Integer, primary_key=True)
    lineup_id = Column(Integer, ForeignKey('fixture_lineups.id'), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    number = Column(SmallInteger, nullable=False)
    position = Column(String(2), nullable=False)  # GK, DF, MF, FW
    grid = Column(String(5), nullable=True)  # Format "x:y" pour la position sur le terrain
    is_substitute = Column(Boolean, default=False, index=True)
    
    # Relationships
    lineup = relationship("FixtureLineup", back_populates="players")
    player = relationship("Player")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_fixture_lineup_players_lineup_position', 'lineup_id', 'position'),
    )
    
    def __repr__(self):
        return f"<FixtureLineupPlayer(lineup_id={self.lineup_id}, player_id={self.player_id}, position='{self.position}')>"

class FixtureCoach(Base, TimeStampMixin):
    """Représente l'entraîneur d'une équipe pour un match."""
    __tablename__ = 'fixture_coaches'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'), nullable=False, index=True)
    
    # Relationships
    fixture = relationship("Fixture")
    team = relationship("Team")
    coach = relationship("Coach")
    
    # Indexes
    __table_args__ = (
        Index('ix_fixture_coaches_fixture_team', 'fixture_id', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FixtureCoach(fixture_id={self.fixture_id}, team_id={self.team_id}, coach_id={self.coach_id})>"