# app/embedding/vectorize.py
import logging
from typing import List, Dict, Any, Optional
import asyncio

from sentence_transformers import SentenceTransformer
import numpy as np

from app.config import settings
from app.utils.text_processing import create_entity_text, clean_text_for_embedding

logger = logging.getLogger(__name__)

# Modèle d'embedding global
_model = None

def get_embedding_model():
    """
    Retourne l'instance du modèle d'embedding, en le chargeant si nécessaire.
    Implémente un pattern singleton pour éviter des chargements multiples.
    """
    global _model
    if _model is None:
        logger.info(f"Chargement du modèle d'embedding {settings.EMBEDDING_MODEL}...")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(f"Modèle d'embedding chargé avec succès")
    return _model

async def get_embedding_for_text(text: str) -> List[float]:
    """
    Génère un vecteur d'embedding pour un texte donné.
    
    Args:
        text: Le texte à vectoriser
        
    Returns:
        Vecteur d'embedding
    """
    if not text:
        return []
    
    # Nettoyer le texte
    cleaned_text = clean_text_for_embedding(text)
    
    # Obtenir le modèle
    model = get_embedding_model()
    
    # Exécuter l'embedding dans un thread séparé pour éviter le blocage
    loop = asyncio.get_event_loop()
    try:
        # Génération asynchrone de l'embedding
        embedding = await loop.run_in_executor(None, lambda: model.encode(cleaned_text, normalize_embeddings=True))
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'embedding: {str(e)}")
        return []

async def get_embedding_for_entity(entity: Any, entity_type: str) -> Optional[List[float]]:
    """
    Génère un vecteur d'embedding pour une entité.
    
    Args:
        entity: L'instance de l'entité
        entity_type: Le type d'entité (ex: 'country', 'team', etc.)
        
    Returns:
        Vecteur d'embedding ou None en cas d'erreur
    """
    try:
        # Créer une représentation textuelle de l'entité
        entity_text = create_entity_text(entity, entity_type)
        
        if not entity_text:
            logger.warning(f"Impossible de créer une représentation textuelle pour {entity_type} ID {entity.id}")
            return None
        
        # Générer l'embedding
        return await get_embedding_for_text(entity_text)
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'embedding pour {entity_type} ID {entity.id}: {str(e)}")
        return None

async def batch_generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Génère des embeddings pour une liste de textes.
    
    Args:
        texts: Liste de textes à vectoriser
        
    Returns:
        Liste de vecteurs d'embedding
    """
    if not texts:
        return []
    
    # Nettoyer les textes
    cleaned_texts = [clean_text_for_embedding(text) for text in texts]
    
    # Obtenir le modèle
    model = get_embedding_model()
    
    # Exécuter l'embedding dans un thread séparé pour éviter le blocage
    loop = asyncio.get_event_loop()
    try:
        # Génération asynchrone des embeddings
        embeddings = await loop.run_in_executor(None, lambda: model.encode(cleaned_texts, normalize_embeddings=True))
        return [embedding.tolist() for embedding in embeddings]
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'embeddings par lot: {str(e)}")
        return []