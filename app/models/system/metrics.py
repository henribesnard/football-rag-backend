from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base

class AppMetrics(Base):
    """
    Métriques générales de l'application pour le monitoring.
    """
    __tablename__ = 'app_metrics'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metric_type = Column(String(50), index=True)  # Type de métrique (api_calls, db_queries, cache_hits, etc.)
    value = Column(Float, nullable=False)  # Valeur de la métrique
    dimensions = Column(JSON, nullable=True)  # Dimensions supplémentaires (endpoint, méthode, etc.)
    
    # Indexes
    __table_args__ = (
        Index('ix_app_metrics_timestamp_type', 'timestamp', 'metric_type'),
    )
    
    def __repr__(self):
        return f"<AppMetrics(type='{self.metric_type}', value={self.value})>"

class PerformanceLog(Base):
    """
    Logs de performance détaillés pour l'analyse et le débogage.
    """
    __tablename__ = 'performance_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    component = Column(String(100), index=True)  # Composant concerné (api, db, cache, etc.)
    operation = Column(String(100), index=True)  # Opération effectuée (requête spécifique, endpoint, etc.)
    duration_ms = Column(Float, nullable=False)  # Durée en millisecondes
    status = Column(String(20), index=True)  # success, error, warning
    details = Column(JSON, nullable=True)  # Détails supplémentaires (paramètres, contexte, etc.)
    trace_id = Column(String(100), nullable=True, index=True)  # ID de trace pour le suivi des requêtes
    error_message = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_performance_logs_component_operation', 'component', 'operation'),
        Index('ix_performance_logs_timestamp_status', 'timestamp', 'status'),
    )
    
    def __repr__(self):
        return f"<PerformanceLog(component='{self.component}', operation='{self.operation}', duration={self.duration_ms}ms)>"