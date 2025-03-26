from sqlalchemy import Column, Integer, String, SmallInteger, ForeignKey, Index, DECIMAL
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class TeamStatistics(Base, TimeStampMixin):
    """
    Statistiques globales d'une équipe pour une saison dans une ligue
    """
    __tablename__ = 'team_statistics'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False, index=True)

    # Forme actuelle
    form = Column(String(100), nullable=True)  # Ex: "WDLDW"

    # Matches joués
    matches_played_home = Column(SmallInteger, default=0)
    matches_played_away = Column(SmallInteger, default=0)
    matches_played_total = Column(SmallInteger, default=0)

    # Victoires
    wins_home = Column(SmallInteger, default=0)
    wins_away = Column(SmallInteger, default=0)
    wins_total = Column(SmallInteger, default=0)

    # Nuls
    draws_home = Column(SmallInteger, default=0)
    draws_away = Column(SmallInteger, default=0)
    draws_total = Column(SmallInteger, default=0)

    # Défaites
    losses_home = Column(SmallInteger, default=0)
    losses_away = Column(SmallInteger, default=0)
    losses_total = Column(SmallInteger, default=0)

    # Buts marqués
    goals_for_home = Column(SmallInteger, default=0)
    goals_for_away = Column(SmallInteger, default=0)
    goals_for_total = Column(SmallInteger, default=0)

    # Buts encaissés
    goals_against_home = Column(SmallInteger, default=0)
    goals_against_away = Column(SmallInteger, default=0)
    goals_against_total = Column(SmallInteger, default=0)

    # Moyennes de buts
    goals_for_average_home = Column(DECIMAL(4, 2), default=0)
    goals_for_average_away = Column(DECIMAL(4, 2), default=0)
    goals_for_average_total = Column(DECIMAL(4, 2), default=0)
    goals_against_average_home = Column(DECIMAL(4, 2), default=0)
    goals_against_average_away = Column(DECIMAL(4, 2), default=0)
    goals_against_average_total = Column(DECIMAL(4, 2), default=0)

    # Séries
    streak_wins = Column(SmallInteger, default=0)
    streak_draws = Column(SmallInteger, default=0)
    streak_losses = Column(SmallInteger, default=0)

    # Plus grandes victoires
    biggest_win_home = Column(String(10), nullable=True)  # Ex: "4-0"
    biggest_win_away = Column(String(10), nullable=True)  # Ex: "0-3"
    biggest_loss_home = Column(String(10), nullable=True)  # Ex: "0-2"
    biggest_loss_away = Column(String(10), nullable=True)  # Ex: "2-0"

    # Clean sheets
    clean_sheets_home = Column(SmallInteger, default=0)
    clean_sheets_away = Column(SmallInteger, default=0)
    clean_sheets_total = Column(SmallInteger, default=0)

    # Failed to score
    failed_to_score_home = Column(SmallInteger, default=0)
    failed_to_score_away = Column(SmallInteger, default=0)
    failed_to_score_total = Column(SmallInteger, default=0)

    # Penalties
    penalties_scored = Column(SmallInteger, default=0)
    penalties_missed = Column(SmallInteger, default=0)
    penalties_total = Column(SmallInteger, default=0)
    
    # Relationships
    team = relationship("Team", back_populates="team_statistics")
    league = relationship("League", back_populates="team_statistics")
    season = relationship("Season", back_populates="team_statistics")
    
    # Indexes
    __table_args__ = (
        Index('ix_team_stats_team_season', 'team_id', 'season_id'),
        Index('ix_team_stats_league_season', 'league_id', 'season_id'),
    )
    
    def __repr__(self):
        return f"<TeamStatistics(team_id={self.team_id}, league_id={self.league_id}, season_id={self.season_id})>"