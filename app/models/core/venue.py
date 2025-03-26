from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class Venue(Base, TimeStampMixin):
    __tablename__ = 'venues'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), index=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    capacity = Column(Integer, nullable=True)
    surface = Column(String(50), nullable=True)
    image_url = Column(String(255), nullable=True)
    
    # Relationships
    country = relationship("Country", back_populates="venues")
    teams = relationship("Team", back_populates="venue")
    fixtures = relationship("Fixture", back_populates="venue")
    
    # Indexes
    __table_args__ = (
        Index('ix_venues_name_city', 'name', 'city'),
        Index('ix_venues_external_id', 'external_id'),
    )
    
    def __repr__(self):
        return f"<Venue(name='{self.name}', city='{self.city}')>"