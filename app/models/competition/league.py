from sqlalchemy import Column, Integer, String, Date, ForeignKey, Boolean, SmallInteger, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class League(Base, TimeStampMixin):
    __tablename__ = 'leagues'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    type = Column(String(50))  # League, Cup, Other
    logo_url = Column(String(255), nullable=True)
    country_id = Column(Integer, ForeignKey('countries.id'))
    
    # Relationships
    country = relationship("Country", back_populates="leagues")
    seasons = relationship("Season", back_populates="league")
    fixtures = relationship("Fixture", back_populates="league")
    team_statistics = relationship("TeamStatistics", back_populates="league")
    
    # Indexes
    __table_args__ = (
        Index('ix_leagues_name_country', 'name', 'country_id'),
    )
    
    def __repr__(self):
        return f"<League(name='{self.name}', country_id={self.country_id})>"

class Season(Base, TimeStampMixin):
    __tablename__ = 'seasons'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=True, index=True)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False)
    year = Column(SmallInteger, index=True)
    start_date = Column(Date)
    end_date = Column(Date)
    is_current = Column(Boolean, default=False, index=True)
    
    # Relationships
    league = relationship("League", back_populates="seasons")
    fixtures = relationship("Fixture", back_populates="season")
    standings = relationship("Standing", back_populates="season")
    team_statistics = relationship("TeamStatistics", back_populates="season")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_seasons_league_year', 'league_id', 'year'),
        CheckConstraint('end_date >= start_date', name='end_date_after_start_date')
    )
    
    def __repr__(self):
        return f"<Season(league_id={self.league_id}, year={self.year})>"