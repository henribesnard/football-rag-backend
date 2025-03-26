from sqlalchemy import Column, Integer, String, Text, ForeignKey, DECIMAL, Boolean, DateTime, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class OddsType(Base, TimeStampMixin):
    __tablename__ = 'odds_types'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    name = Column(String(100))  # Ex: "Match Winner", "Both Teams Score"
    key = Column(String(50), index=True)  # Ex: "match_winner", "btts"
    description = Column(Text, nullable=True)
    category = Column(String(50), index=True)  # main, goals, halves, specials
    display_order = Column(Integer, default=0)
    
    # Relationships
    values = relationship("OddsValue", back_populates="odds_type")
    odds = relationship("Odds", back_populates="odds_type")
    
    # Indexes
    __table_args__ = (
        Index('ix_odds_types_category_order', 'category', 'display_order'),
    )
    
    def __repr__(self):
        return f"<OddsType(id={self.id}, name='{self.name}')>"

class OddsValue(Base, TimeStampMixin):
    __tablename__ = 'odds_values'
    
    id = Column(Integer, primary_key=True)
    odds_type_id = Column(Integer, ForeignKey('odds_types.id'), nullable=False, index=True)
    name = Column(String(100), index=True)  # Ex: "Home", "Away", "Over 2.5"
    key = Column(String(50))  # Ex: "home", "away", "over_2_5"
    display_order = Column(Integer, default=0)
    
    # Relationships
    odds_type = relationship("OddsType", back_populates="values")
    odds = relationship("Odds", back_populates="odds_value")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_odds_values_type_key', 'odds_type_id', 'key', unique=True),
        Index('ix_odds_values_type_order', 'odds_type_id', 'display_order'),
    )
    
    def __repr__(self):
        return f"<OddsValue(id={self.id}, name='{self.name}')>"

class Odds(Base, TimeStampMixin):
    __tablename__ = 'odds'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    bookmaker_id = Column(Integer, ForeignKey('bookmakers.id'), nullable=False, index=True)
    odds_type_id = Column(Integer, ForeignKey('odds_types.id'), nullable=False, index=True)
    odds_value_id = Column(Integer, ForeignKey('odds_values.id'), nullable=False, index=True)
    value = Column(DECIMAL(7, 2), nullable=False)
    is_main = Column(Boolean, default=False)  # Pour identifier les cotes principales
    probability = Column(DECIMAL(5, 2), nullable=True)  # Probabilité calculée (1/cote)
    status = Column(String(20), default='active', index=True)  # active, suspended, settled, cancelled
    last_update = Column(DateTime, index=True)
    
    # Relationships
    fixture = relationship("Fixture")
    bookmaker = relationship("Bookmaker", back_populates="odds")
    odds_type = relationship("OddsType", back_populates="odds")
    odds_value = relationship("OddsValue", back_populates="odds")
    history = relationship("OddsHistory", back_populates="odds")
    
    # Indexes & Constraints
    __table_args__ = (
        Index('ix_odds_fixture_bookmaker_type', 'fixture_id', 'bookmaker_id', 'odds_type_id'),
        Index('ix_odds_fixture_status', 'fixture_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Odds(fixture_id={self.fixture_id}, type_id={self.odds_type_id}, value_id={self.odds_value_id})>"