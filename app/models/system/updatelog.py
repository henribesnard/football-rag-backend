from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

class UpdateLog(Base):
    __tablename__ = 'update_logs'
    
    id = Column(Integer, primary_key=True)
    table_name = Column(String(100), index=True)
    record_id = Column(Integer, index=True)
    update_type = Column(String(20), index=True)  # create, update, delete, bulk_update, bulk_create
    update_by = Column(String(50), index=True)
    update_at = Column(DateTime, index=True)
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_update_logs_table_record', 'table_name', 'record_id'),
        Index('ix_update_logs_update_at_type', 'update_at', 'update_type'),
    )
    
    def __repr__(self):
        return f"<UpdateLog(id={self.id}, table='{self.table_name}', type='{self.update_type}')>"