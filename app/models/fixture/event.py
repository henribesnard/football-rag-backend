from sqlalchemy import Column, Integer, String, SmallInteger, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin

class FixtureEvent(Base, TimeStampMixin):
    __tablename__ = 'fixture_events'
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey('fixtures.id'), nullable=False, index=True)
    time_elapsed = Column(SmallInteger, nullable=False)
    event_type = Column(String(50), index=True)  # Goal, Card, Substitution, etc.
    detail = Column(String(100))
    player_id = Column(Integer, ForeignKey('players.id'), nullable=True, index=True)
    assist_id = Column(Integer, ForeignKey('players.id'), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    comments = Column(Text, nullable=True)
    
    # Relationships
    fixture = relationship("Fixture", back_populates="events")
    player = relationship("Player", foreign_keys=[player_id], back_populates="events")
    assist = relationship("Player", foreign_keys=[assist_id], back_populates="assists")
    team = relationship("Team")
    
    # Indexes
    __table_args__ = (
        Index('ix_fixture_events_fixture_time', 'fixture_id', 'time_elapsed'),
        Index('ix_fixture_events_event_type_team', 'event_type', 'team_id'),
    )
    
    def __repr__(self):
        return f"<FixtureEvent(fixture_id={self.fixture_id}, event_type='{self.event_type}')>"