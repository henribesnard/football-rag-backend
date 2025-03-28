"""Service de journalisation structurée."""
import os
import sys
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from app.config import settings

class StructuredFormatter(logging.Formatter):
    """Formatteur pour journalisation structurée en JSON."""
    
    def __init__(self, fmt=None, datefmt=None, style='%', service_name="football-rag-api"):
        super().__init__(fmt, datefmt, style)
        self.service_name = service_name
    
    def format(self, record):
        """
        Formate l'enregistrement en JSON structuré.
        
        Args:
            record: Enregistrement à formater
            
        Returns:
            Chaîne JSON formatée
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Ajouter les exceptions si présentes
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Ajouter les attributs supplémentaires
        if hasattr(record, "extras") and record.extras:
            log_data.update(record.extras)
        
        return json.dumps(log_data)

def configure_logging():
    """Configure la journalisation structurée."""
    level = getattr(logging, settings.CDC_LOG_LEVEL, logging.INFO)
    
    # Configurer le handler principal
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(service_name=settings.APP_NAME))
    
    # Configurer la journalisation racine
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []  # Supprimer les handlers existants
    root_logger.addHandler(handler)
    
    # Configurer un handler de fichier si nécessaire
    if log_file := settings.get("LOG_FILE"):
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter(service_name=settings.APP_NAME))
        root_logger.addHandler(file_handler)
    
    # Ajuster les niveaux de journalisation des bibliothèques tierces
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("kafka").setLevel(logging.WARNING)

class StructuredLogger:
    """Logger avec support pour la journalisation structurée."""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def _add_extras(self, extras):
        """Ajoute des extras au LogRecord."""
        return {"extras": extras} if extras else {}
    
    def debug(self, msg, *args, **kwargs):
        """Journalise un message de niveau DEBUG."""
        extras = kwargs.pop("extras", {})
        kwargs.update(self._add_extras(extras))
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        """Journalise un message de niveau INFO."""
        extras = kwargs.pop("extras", {})
        kwargs.update(self._add_extras(extras))
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """Journalise un message de niveau WARNING."""
        extras = kwargs.pop("extras", {})
        kwargs.update(self._add_extras(extras))
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """Journalise un message de niveau ERROR."""
        extras = kwargs.pop("extras", {})
        kwargs.update(self._add_extras(extras))
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """Journalise un message de niveau CRITICAL."""
        extras = kwargs.pop("extras", {})
        kwargs.update(self._add_extras(extras))
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        """Journalise une exception avec traceback."""
        extras = kwargs.pop("extras", {})
        kwargs.update(self._add_extras(extras))
        self.logger.exception(msg, *args, **kwargs)

def get_logger(name):
    """
    Récupère un logger structuré.
    
    Args:
        name: Nom du logger
        
    Returns:
        Instance de StructuredLogger
    """
    return StructuredLogger(name)