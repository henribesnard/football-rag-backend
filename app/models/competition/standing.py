from sqlalchemy import Column, Integer, String, SmallInteger, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Standing(Base, TimeStampMixin):
    """Représente une entrée dans le classement d'une ligue pour une saison."""
    __tablename__ = 'standings'
    
    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    
    # Position au classement
    rank = Column(SmallInteger, nullable=False)
    points = Column(SmallInteger, default=0)
    goals_diff = Column(SmallInteger, default=0)
    
    # Form et Status
    form = Column(String(10), nullable=True)  # Ex: "WWWLD"
    status = Column(String(20), nullable=True)  # Ex: "same", "up", "down"
    description = Column(String(100), nullable=True)  # Ex: "Promotion - Champions League"
    
    # Statistiques globales
    played = Column(SmallInteger, default=0)
    won = Column(SmallInteger, default=0)
    drawn = Column(SmallInteger, default=0)
    lost = Column(SmallInteger, default=0)
    goals_for = Column(SmallInteger, default=0)
    goals_against = Column(SmallInteger, default=0)
    
    # Statistiques à domicile
    home_played = Column(SmallInteger, default=0)
    home_won = Column(SmallInteger, default=0)
    home_drawn = Column(SmallInteger, default=0)
    home_lost = Column(SmallInteger, default=0)
    home_goals_for = Column(SmallInteger, default=0)
    home_goals_against = Column(SmallInteger, default=0)
    
    # Statistiques à l'extérieur
    away_played = Column(SmallInteger, default=0)
    away_won = Column(SmallInteger, default=0)
    away_drawn = Column(SmallInteger, default=0)
    away_lost = Column(SmallInteger, default=0)
    away_goals_for = Column(SmallInteger, default=0)
    away_goals_against = Column(SmallInteger, default=0)
    
    # Relationships
    season = relationship("Season", back_populates="standings")
    team = relationship("Team", back_populates="standings")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_standings_season_rank', 'season_id', 'rank'),
        Index('ix_standings_season_points', 'season_id', 'points'),
        Index('ix_standings_update_at', 'update_at'),
        # Vérification de la cohérence des matchs joués
        CheckConstraint('played = won + drawn + lost', name='total_matches_check'),
        CheckConstraint('home_played = home_won + home_drawn + home_lost', name='home_matches_check'),
        CheckConstraint('away_played = away_won + away_drawn + away_lost', name='away_matches_check'),
        # Vérification de la cohérence entre total et home/away
        CheckConstraint('played = home_played + away_played', name='total_vs_home_away_matches_check'),
        CheckConstraint('goals_for = home_goals_for + away_goals_for', name='total_vs_home_away_goals_for_check'),
        CheckConstraint('goals_against = home_goals_against + away_goals_against', 
                        name='total_vs_home_away_goals_against_check')
    )
    
    def __repr__(self):
        return f"<Standing(team_id={self.team_id}, season_id={self.season_id}, rank={self.rank})>"