# app/models/betting/prediction.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Text, JSON, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Prediction(Base, TimeStampMixin):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    
    # Données du vainqueur prédit
    winner_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    winner_name = Column(String(255), nullable=True)
    winner_comment = Column(String(255), nullable=True)
    
    # Prédictions générales
    win_or_draw = Column(Boolean, default=False)
    under_over = Column(String(10), nullable=True)
    advice = Column(Text, nullable=True)
    
    # Prédictions de buts
    goals_home = Column(String(10), nullable=True)
    goals_away = Column(String(10), nullable=True)
    
    # Pourcentages de prédiction
    percent_home = Column(String(10), nullable=True)
    percent_draw = Column(String(10), nullable=True)
    percent_away = Column(String(10), nullable=True)
    
    # Données sur la ligue
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=True)
    league_season = Column(Integer, nullable=True)
    
    # Statistiques de l'équipe domicile
    home_form = Column(String(10), nullable=True)
    home_att = Column(String(10), nullable=True)
    home_def = Column(String(10), nullable=True)
    home_goals_for_total = Column(Integer, nullable=True)
    home_goals_for_average = Column(Float, nullable=True)
    home_goals_against_total = Column(Integer, nullable=True)
    home_goals_against_average = Column(Float, nullable=True)
    home_fixtures_played_home = Column(Integer, nullable=True)
    home_fixtures_played_away = Column(Integer, nullable=True)
    home_fixtures_played_total = Column(Integer, nullable=True)
    home_fixtures_wins_home = Column(Integer, nullable=True)
    home_fixtures_wins_away = Column(Integer, nullable=True)
    home_fixtures_wins_total = Column(Integer, nullable=True)
    home_fixtures_draws_home = Column(Integer, nullable=True)
    home_fixtures_draws_away = Column(Integer, nullable=True)
    home_fixtures_draws_total = Column(Integer, nullable=True)
    home_fixtures_loses_home = Column(Integer, nullable=True)
    home_fixtures_loses_away = Column(Integer, nullable=True)
    home_fixtures_loses_total = Column(Integer, nullable=True)
    home_league_form = Column(String(100), nullable=True)
    
    # Statistiques de l'équipe extérieure
    away_form = Column(String(10), nullable=True)
    away_att = Column(String(10), nullable=True)
    away_def = Column(String(10), nullable=True)
    away_goals_for_total = Column(Integer, nullable=True)
    away_goals_for_average = Column(Float, nullable=True)
    away_goals_against_total = Column(Integer, nullable=True)
    away_goals_against_average = Column(Float, nullable=True)
    away_fixtures_played_home = Column(Integer, nullable=True)
    away_fixtures_played_away = Column(Integer, nullable=True)
    away_fixtures_played_total = Column(Integer, nullable=True)
    away_fixtures_wins_home = Column(Integer, nullable=True)
    away_fixtures_wins_away = Column(Integer, nullable=True)
    away_fixtures_wins_total = Column(Integer, nullable=True)
    away_fixtures_draws_home = Column(Integer, nullable=True)
    away_fixtures_draws_away = Column(Integer, nullable=True)
    away_fixtures_draws_total = Column(Integer, nullable=True)
    away_fixtures_loses_home = Column(Integer, nullable=True)
    away_fixtures_loses_away = Column(Integer, nullable=True)
    away_fixtures_loses_total = Column(Integer, nullable=True)
    away_league_form = Column(String(100), nullable=True)
    
    # Données de comparaison
    comparison_form_home = Column(String(10), nullable=True)
    comparison_form_away = Column(String(10), nullable=True)
    comparison_att_home = Column(String(10), nullable=True)
    comparison_att_away = Column(String(10), nullable=True)
    comparison_def_home = Column(String(10), nullable=True)
    comparison_def_away = Column(String(10), nullable=True)
    comparison_poisson_distribution_home = Column(String(10), nullable=True)
    comparison_poisson_distribution_away = Column(String(10), nullable=True)
    comparison_h2h_home = Column(String(10), nullable=True)
    comparison_h2h_away = Column(String(10), nullable=True)
    comparison_goals_home = Column(String(10), nullable=True)
    comparison_goals_away = Column(String(10), nullable=True)
    comparison_total_home = Column(String(10), nullable=True)
    comparison_total_away = Column(String(10), nullable=True)
    
    # Données supplémentaires stockées en JSON
    h2h_data = Column(JSON, nullable=True)  # Pour stocker l'historique des confrontations
    
    # Relationships
    fixture = relationship("Fixture", back_populates="predictions")
    winner = relationship("Team", foreign_keys=[winner_id])
    league = relationship("League", foreign_keys=[league_id])
    
    # Indexes
    __table_args__ = (
        Index('ix_predictions_fixture_id', 'fixture_id'),
        Index('ix_predictions_winner_id', 'winner_id'),
        Index('ix_predictions_league_id', 'league_id'),
    )
    
    def __repr__(self):
        return f"<Prediction(fixture_id={self.fixture_id}, winner_id={self.winner_id})>"