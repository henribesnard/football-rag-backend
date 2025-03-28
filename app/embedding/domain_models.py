"""Support pour les modèles d'embedding spécifiques au domaine du football."""
import os
import logging
from typing import Dict, Any, Optional, List

from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModel

from app.config import settings

logger = logging.getLogger(__name__)

# Dictionnaire global des modèles chargés
_models = {}

def get_football_embedding_model(model_name: str = None):
    """
    Récupère un modèle d'embedding spécifique au domaine du football.
    
    Args:
        model_name: Nom du modèle (None = utilise le modèle par défaut)
        
    Returns:
        Instance du modèle d'embedding
    """
    global _models
    
    # Utiliser le modèle spécifié ou le modèle par défaut
    model_name = model_name or settings.FOOTBALL_EMBEDDING_MODEL or settings.EMBEDDING_MODEL
    
    # Vérifier si le modèle est déjà chargé
    if model_name in _models:
        return _models[model_name]
    
    logger.info(f"Chargement du modèle d'embedding pour le football: {model_name}")
    
    try:
        # Charger le modèle
        model = SentenceTransformer(model_name)
        _models[model_name] = model
        
        logger.info(f"Modèle d'embedding pour le football chargé avec succès: {model_name}")
        return model
    except Exception as e:
        logger.error(f"Erreur lors du chargement du modèle d'embedding pour le football: {str(e)}")
        # Fallback sur le modèle standard en cas d'erreur
        return SentenceTransformer(settings.EMBEDDING_MODEL)

async def get_football_embedding(text: str, model_name: str = None) -> List[float]:
    """
    Génère un embedding pour du texte lié au football.
    
    Args:
        text: Texte à encoder
        model_name: Nom du modèle à utiliser (None = modèle par défaut)
        
    Returns:
        Embedding sous forme de liste de flottants
    """
    if not text:
        return []
    
    model = get_football_embedding_model(model_name)
    
    # Créer l'embedding de manière asynchrone
    import asyncio
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, lambda: model.encode(text, normalize_embeddings=True))
    
    return embedding.tolist()