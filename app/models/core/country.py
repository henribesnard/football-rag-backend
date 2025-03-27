from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import relationship, validates

from app.models.base import Base, TimeStampMixin

class Country(Base, TimeStampMixin):
    __tablename__ = 'countries'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    code = Column(String(20), nullable=True, index=True)
    flag_url = Column(String(255), nullable=True)
    
    # Relationships (declarés ici mais définis dans les classes respectives)
    venues = relationship("Venue", back_populates="country")
    leagues = relationship("League", back_populates="country")
    teams = relationship("Team", back_populates="country")
    #players = relationship("Player", back_populates="nationality")
    #coaches = relationship("Coach", back_populates="nationality")
    
    @validates('code')
    def validate_code(self, key, code):
        if code and not code.isalpha() and not all(c.isupper() or c == '-' for c in code):
            raise ValueError("Le code doit contenir uniquement des lettres majuscules ou des tirets")
        if code and (len(code) < 2 or len(code) > 10):
            raise ValueError("Le code doit avoir entre 2 et 10 caractères")
        return code
    
    def __repr__(self):
        return f"<Country(name='{self.name}')>"