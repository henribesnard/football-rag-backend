from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, DateTime, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class OddsHistory(Base, TimeStampMixin):
    __tablename__ = 'odds_history'
    
    id = Column(Integer, primary_key=True)
    odds_id = Column(Integer, ForeignKey('odds.id'), nullable=False, index=True)
    old_value = Column(DECIMAL(7, 2), nullable=False)
    new_value = Column(DECIMAL(7, 2), nullable=False)
    change_time = Column(DateTime, nullable=False, index=True)
    movement = Column(String(10))  # up, down, stable
    
    # Relationships
    odds = relationship("Odds", back_populates="history")
    
    # Indexes
    __table_args__ = (
        Index('ix_odds_history_odds_change_time', 'odds_id', 'change_time'),
    )
    
    def __repr__(self):
        return f"<OddsHistory(odds_id={self.odds_id}, old={self.old_value}, new={self.new_value})>"