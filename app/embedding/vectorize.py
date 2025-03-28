# app/embedding/vectorize.py
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import asyncio
import time

from sentence_transformers import SentenceTransformer
import numpy as np
from openai import AsyncOpenAI

from app.config import settings
from app.utils.text_processing import create_entity_text, clean_text_for_embedding
from app.monitoring.metrics import metrics, timed
from app.utils.circuit_breaker import circuit

logger = logging.getLogger(__name__)

# Métriques pour le monitoring
vectorization_time = metrics.histogram(
    "embedding_vectorization_time",
    "Temps de génération des embeddings (secondes)",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)

vectorization_counter = metrics.counter(
    "embedding_total",
    "Nombre total d'embeddings générés"
)

vectorization_error_counter = metrics.counter(
    "embedding_errors_total",
    "Nombre total d'erreurs de génération d'embeddings"
)

batch_size_histogram = metrics.histogram(
    "embedding_batch_size",
    "Taille des lots pour la génération d'embeddings",
    buckets=[1, 2, 5, 10, 20, 50, 100]
)

# Modèles d'embedding globaux
_standard_model = None
_football_model = None
_openai_client = None

def get_embedding_model(domain_specific: bool = False):
    """
    Retourne l'instance du modèle d'embedding approprié, en le chargeant si nécessaire.
    Implémente un pattern singleton pour éviter des chargements multiples.
    
    Args:
        domain_specific: Si True, utilise le modèle spécifique au football si disponible
    
    Returns:
        Instance du modèle SentenceTransformer
    """
    global _standard_model, _football_model
    
    if domain_specific and settings.get("FOOTBALL_EMBEDDING_MODEL"):
        # Utiliser le modèle spécifique au domaine du football
        if _football_model is None:
            model_name = settings.FOOTBALL_EMBEDDING_MODEL
            logger.info(f"Chargement du modèle d'embedding spécifique au football {model_name}...")
            _football_model = SentenceTransformer(model_name)
            logger.info(f"Modèle d'embedding spécifique au football chargé avec succès")
        return _football_model
    else:
        # Utiliser le modèle standard
        if _standard_model is None:
            logger.info(f"Chargement du modèle d'embedding standard {settings.EMBEDDING_MODEL}...")
            _standard_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"Modèle d'embedding standard chargé avec succès")
        return _standard_model

def get_openai_client():
    """
    Retourne le client OpenAI pour les embeddings, en l'initialisant si nécessaire.
    
    Returns:
        Instance du client OpenAI
    """
    global _openai_client
    
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY n'est pas configurée")
        
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Client OpenAI initialisé avec succès")
    
    return _openai_client

@timed("embedding_single_time", "Temps de génération d'un embedding")
@circuit(name="embedding_generation", failure_threshold=5, recovery_timeout=60)
async def get_embedding_for_text(text: str, use_openai: bool = False, domain_specific: bool = False) -> List[float]:
    """
    Génère un vecteur d'embedding pour un texte donné.
    
    Args:
        text: Le texte à vectoriser
        use_openai: Si True, utilise l'API OpenAI au lieu du modèle local
        domain_specific: Si True, utilise le modèle spécifique au football
        
    Returns:
        Vecteur d'embedding
    """
    if not text:
        return []
    
    # Nettoyer le texte
    cleaned_text = clean_text_for_embedding(text)
    
    start_time = time.time()
    
    try:
        if use_openai:
            # Utiliser l'API OpenAI
            client = get_openai_client()
            response = await client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=cleaned_text
            )
            embedding = response.data[0].embedding
        else:
            # Utiliser le modèle local
            model = get_embedding_model(domain_specific)
            
            # Exécuter l'embedding dans un thread séparé pour éviter le blocage
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: model.encode(cleaned_text, normalize_embeddings=True)
            )
            embedding = embedding.tolist()
        
        # Incrémenter le compteur de succès
        vectorization_counter.inc()
        
        return embedding
    
    except Exception as e:
        # Incrémenter le compteur d'erreurs
        vectorization_error_counter.inc()
        
        logger.error(f"Erreur lors de la génération d'embedding: {str(e)}")
        return []
    
    finally:
        # Mesurer le temps d'exécution
        elapsed = time.time() - start_time
        vectorization_time.observe(elapsed)

@timed("embedding_entity_time", "Temps de génération d'embedding pour une entité")
async def get_embedding_for_entity(entity: Any, entity_type: str, use_openai: bool = False) -> Optional[List[float]]:
    """
    Génère un vecteur d'embedding pour une entité.
    
    Args:
        entity: L'instance de l'entité
        entity_type: Le type d'entité (ex: 'country', 'team', etc.)
        use_openai: Si True, utilise l'API OpenAI au lieu du modèle local
        
    Returns:
        Vecteur d'embedding ou None en cas d'erreur
    """
    try:
        # Créer une représentation textuelle de l'entité
        entity_text = create_entity_text(entity, entity_type)
        
        if not entity_text:
            logger.warning(f"Impossible de créer une représentation textuelle pour {entity_type} ID {entity.id}")
            return None
        
        # Utiliser le modèle spécifique au football pour les entités liées au football
        domain_specific = entity_type in {'team', 'player', 'fixture', 'league', 'coach', 'venue'}
        
        # Générer l'embedding
        return await get_embedding_for_text(entity_text, use_openai, domain_specific)
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'embedding pour {entity_type} ID {entity.id}: {str(e)}")
        return None

@timed("embedding_batch_time", "Temps de génération d'embeddings par lot")
@circuit(name="embedding_batch_generation", failure_threshold=3, recovery_timeout=60)
async def batch_generate_embeddings(
    texts: List[str], 
    use_openai: bool = False,
    domain_specific: bool = False,
    batch_size: int = 32  # Taille de lot optimale pour équilibrer performance et mémoire
) -> List[List[float]]:
    """
    Génère des embeddings pour une liste de textes, avec traitement par lots.
    
    Args:
        texts: Liste de textes à vectoriser
        use_openai: Si True, utilise l'API OpenAI au lieu du modèle local
        domain_specific: Si True, utilise le modèle spécifique au football
        batch_size: Taille maximale des lots
        
    Returns:
        Liste de vecteurs d'embedding
    """
    if not texts:
        return []
    
    # Nettoyer les textes
    cleaned_texts = [clean_text_for_embedding(text) for text in texts]
    
    # Tracking des métriques
    batch_size_histogram.observe(len(cleaned_texts))
    start_time = time.time()
    
    # Préparer le résultat
    all_embeddings = []
    
    try:
        if use_openai:
            # Traitement par lots avec OpenAI
            client = get_openai_client()
            
            # Traiter par lots pour éviter les limites d'API
            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i+batch_size]
                
                # Appel à l'API OpenAI
                response = await client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=batch
                )
                
                # Extraire les embeddings
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Pause brève pour éviter de surcharger l'API
                if i + batch_size < len(cleaned_texts):
                    await asyncio.sleep(0.5)
        else:
            # Traitement par lots avec le modèle local
            model = get_embedding_model(domain_specific)
            loop = asyncio.get_event_loop()
            
            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i+batch_size]
                
                # Exécuter l'embedding dans un thread séparé
                batch_embeddings = await loop.run_in_executor(
                    None,
                    lambda b=batch: model.encode(b, normalize_embeddings=True)
                )
                
                # Convertir en liste
                batch_embeddings = [embedding.tolist() for embedding in batch_embeddings]
                all_embeddings.extend(batch_embeddings)
        
        # Incrémenter le compteur de succès
        vectorization_counter.inc(len(cleaned_texts))
        
        return all_embeddings
    
    except Exception as e:
        # Incrémenter le compteur d'erreurs
        vectorization_error_counter.inc()
        
        logger.error(f"Erreur lors de la génération d'embeddings par lot: {str(e)}")
        
        # Revenir à une approche séquentielle en cas d'erreur
        logger.info("Tentative de repli sur l'approche séquentielle...")
        
        sequential_embeddings = []
        for text in cleaned_texts:
            try:
                embedding = await get_embedding_for_text(text, use_openai, domain_specific)
                sequential_embeddings.append(embedding)
            except Exception as inner_e:
                logger.error(f"Erreur lors de la génération séquentielle: {str(inner_e)}")
                sequential_embeddings.append([])  # Ajouter un vecteur vide en cas d'erreur
        
        return sequential_embeddings
    
    finally:
        # Mesurer le temps d'exécution
        elapsed = time.time() - start_time
        vectorization_time.observe(elapsed)

async def batch_generate_embeddings_for_entities(
    entities_dict: Dict[int, Any], 
    entity_type: str,
    use_openai: bool = False
) -> Dict[int, List[float]]:
    """
    Génère des embeddings pour un dictionnaire d'entités de manière optimisée.
    
    Args:
        entities_dict: Dictionnaire {id: entité}
        entity_type: Type d'entité
        use_openai: Si True, utilise l'API OpenAI
        
    Returns:
        Dictionnaire {id: vecteur d'embedding}
    """
    if not entities_dict:
        return {}
    
    # Créer des représentations textuelles pour chaque entité
    entity_texts = {}
    for entity_id, entity in entities_dict.items():
        text = create_entity_text(entity, entity_type)
        if text:
            entity_texts[entity_id] = text
    
    # Utiliser le modèle spécifique au football pour les entités liées au football
    domain_specific = entity_type in {'team', 'player', 'fixture', 'league', 'coach', 'venue'}
    
    # Préparer les textes et IDs correspondants
    ids = list(entity_texts.keys())
    texts = [entity_texts[id] for id in ids]
    
    # Générer les embeddings par lot
    embeddings = await batch_generate_embeddings(texts, use_openai, domain_specific)
    
    # Associer les embeddings aux IDs
    result = {}
    for i, entity_id in enumerate(ids):
        if i < len(embeddings):
            result[entity_id] = embeddings[i]
    
    return result