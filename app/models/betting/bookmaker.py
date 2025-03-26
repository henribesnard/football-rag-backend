from sqlalchemy import Column, Integer, String, Boolean, SmallInteger, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Bookmaker(Base, TimeStampMixin):
    __tablename__ = 'bookmakers'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    name = Column(String(100), index=True)
    logo_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    priority = Column(SmallInteger, default=0)  # Pour ordonner les bookmakers
    
    # Relationships
    odds = relationship("Odds", back_populates="bookmaker")
    
    # Indexes
    __table_args__ = (
        Index('ix_bookmakers_is_active_priority', 'is_active', 'priority'),
    )
    
    def __repr__(self):
        return f"<Bookmaker(id={self.id}, name='{self.name}')>"