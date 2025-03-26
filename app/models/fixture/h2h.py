from sqlalchemy import Column, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class FixtureH2H(Base, TimeStampMixin):
    """Modèle pour stocker les relations entre un match de référence et ses confrontations directes."""
    __tablename__ = 'fixture_h2h'
    
    id = Column(Integer, primary_key=True)
    reference_fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    related_fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    
    # Relationships
    reference_fixture = relationship("Fixture", foreign_keys=[reference_fixture_id], back_populates="h2h_references")
    related_fixture = relationship("Fixture", foreign_keys=[related_fixture_id], back_populates="h2h_related")
    
    # Indexes
    __table_args__ = (
        Index('ix_fixture_h2h_reference_related', 'reference_fixture_id', 'related_fixture_id', unique=True),
    )
    
    def __repr__(self):
        return f"<FixtureH2H(reference_id={self.reference_fixture_id}, related_id={self.related_fixture_id})>"