from sqlalchemy import Column, Integer, String, Date, SmallInteger, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Player(Base, TimeStampMixin):
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    nationality_id = Column(Integer, ForeignKey('countries.id'), nullable=True)
    height = Column(SmallInteger, nullable=True)  # Stocké en cm
    weight = Column(SmallInteger, nullable=True)  # Stocké en kg
    team_id = Column(Integer, ForeignKey('teams.id'), index=True)
    position = Column(String(2), nullable=False)
    number = Column(SmallInteger, nullable=True)
    injured = Column(Boolean, default=False)
    photo_url = Column(String(255), nullable=True)
    
    # Champs dénormalisés pour les performances
    season_goals = Column(Integer, default=0)
    season_assists = Column(Integer, default=0)
    season_yellow_cards = Column(SmallInteger, default=0)
    season_red_cards = Column(SmallInteger, default=0)
    total_appearances = Column(Integer, default=0)
    
    # Relationships
    nationality = relationship("Country", back_populates="players")
    team = relationship("Team", back_populates="players")
    events = relationship("FixtureEvent", foreign_keys="FixtureEvent.player_id", back_populates="player")
    assists = relationship("FixtureEvent", foreign_keys="FixtureEvent.assist_id", back_populates="assist")
    statistics = relationship("PlayerStatistics", back_populates="player")
    injuries = relationship("PlayerInjury", back_populates="player")
    transfers = relationship("PlayerTransfer", back_populates="player")
    teams_history = relationship("PlayerTeam", back_populates="player")
    current_squad = relationship("TeamPlayer", back_populates="player")
    
    # Indexes
    __table_args__ = (
        Index('ix_players_name_team', 'name', 'team_id'),
        Index('ix_players_position_team', 'position', 'team_id'),
        Index('ix_players_injured', 'injured'),
    )
    
    def __repr__(self):
        return f"<Player(name='{self.name}', team_id={self.team_id})>"

class PlayerTransfer(Base, TimeStampMixin):
    """
    Historique des transferts des joueurs entre équipes
    """
    __tablename__ = 'player_transfers'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    date = Column(Date, index=True)
    type = Column(String(20), nullable=True)
    team_in_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    team_out_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    
    # Relationships
    player = relationship("Player", back_populates="transfers")
    team_in = relationship("Team", foreign_keys=[team_in_id], back_populates="transfers_in")
    team_out = relationship("Team", foreign_keys=[team_out_id], back_populates="transfers_out")
    
    # Indexes
    __table_args__ = (
        Index('ix_player_transfers_player_date', 'player_id', 'date'),
        Index('ix_player_transfers_team_in_date', 'team_in_id', 'date'),
        Index('ix_player_transfers_team_out_date', 'team_out_id', 'date'),
        Index('ix_player_transfers_type', 'type'),
    )
    
    def __repr__(self):
        return f"<PlayerTransfer(player_id={self.player_id}, team_out_id={self.team_out_id}, team_in_id={self.team_in_id})>"

class PlayerTeam(Base, TimeStampMixin):
    """
    Historique des équipes dans lesquelles un joueur a évolué par saison
    """
    __tablename__ = 'player_teams'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False, index=True)
    
    # Relationships
    player = relationship("Player", back_populates="teams_history")
    team = relationship("Team", back_populates="player_history")
    season = relationship("Season")
    
    # Indexes
    __table_args__ = (
        Index('ix_player_teams_player_team', 'player_id', 'team_id'),
        Index('ix_player_teams_player_season', 'player_id', 'season_id'),
        Index('ix_player_teams_team_season', 'team_id', 'season_id'),
    )
    
    def __repr__(self):
        return f"<PlayerTeam(player_id={self.player_id}, team_id={self.team_id}, season_id={self.season_id})>"

class PlayerInjury(Base, TimeStampMixin):
    __tablename__ = 'player_injuries'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=True, index=True)
    type = Column(String(100))
    severity = Column(String(20))  # minor, moderate, severe, season_ending
    status = Column(String(20))    # recovering, training, available, doubtful
    start_date = Column(Date, index=True)
    end_date = Column(Date, nullable=True)
    expected_return_date = Column(Date, nullable=True)
    recovery_time = Column(SmallInteger, nullable=True)  # Stocké en jours
    
    # Relationships
    player = relationship("Player", back_populates="injuries")
    fixture = relationship("Fixture", back_populates="injuries")
    
    # Indexes
    __table_args__ = (
        Index('ix_player_injuries_player_start_date', 'player_id', 'start_date'),
        Index('ix_player_injuries_status_end_date', 'status', 'end_date'),
    )
    
    def __repr__(self):
        return f"<PlayerInjury(player_id={self.player_id}, type='{self.type}')>"