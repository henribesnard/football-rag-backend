import logging
import time
from typing import Dict, List, Optional, Union, Any, Tuple
import datetime
import asyncio

import numpy as np
from qdrant_client.http import models as rest
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, PointIdsList

from .client import get_qdrant_client
from .collections import get_collection_name
from app.monitoring.metrics import metrics, timed
from app.utils.circuit_breaker import circuit
from app.utils.resilience import with_retry

logger = logging.getLogger(__name__)

# Dimension d'embedding par défaut (à remplacer par settings.EMBEDDING_DIM lorsque disponible)
DEFAULT_EMBEDDING_DIM = 1024

# Métriques
search_latency = metrics.histogram(
    "qdrant_search_latency",
    "Temps de recherche dans Qdrant (secondes)",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

search_count = metrics.counter(
    "qdrant_search_total",
    "Nombre total de recherches dans Qdrant"
)

vectorstore_operations = metrics.counter(
    "qdrant_operations_total",
    "Nombre total d'opérations sur Qdrant",
    ["operation"]  # Label pour différencier search/upsert/delete
)

@timed("qdrant_search_time", "Temps de recherche Qdrant")
@circuit(name="qdrant_search", failure_threshold=5, recovery_timeout=30)
async def search_collection(
    collection_name: str,
    query_vector: List[float],
    filter_conditions: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    offset: int = 0,
    with_payload: bool = True,
    score_threshold: Optional[float] = None
) -> List[Dict]:
    """
    Recherche dans une collection Qdrant en utilisant un vecteur de requête et des filtres optionnels.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        collection_name: Nom de la collection Qdrant
        query_vector: Vecteur d'embedding pour la recherche
        filter_conditions: Conditions de filtrage (dictionnaire)
        limit: Nombre maximum de résultats à retourner
        offset: Décalage pour la pagination
        with_payload: Si True, inclut le payload des points
        score_threshold: Seuil de score minimum pour les résultats
    
    Returns:
        Liste de dictionnaires contenant les résultats de recherche
    """
    # Incrémenter les compteurs de métriques
    search_count.inc()
    vectorstore_operations.labels(operation="search").inc()
    
    start_time = time.time()
    client = get_qdrant_client()
    
    # Convertir les conditions de filtrage en objet Filter de Qdrant
    qdrant_filter = _build_qdrant_filter(filter_conditions)
    
    try:
        # Utiliser le retry pour plus de résilience
        search_result = await with_retry(
            lambda: client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                score_threshold=score_threshold
            ),
            retries=2,
            delay=0.5,
            backoff_factor=2.0,
            jitter=0.1
        )
        
        # Calculer et observer la latence
        latency = time.time() - start_time
        search_latency.observe(latency)
        
        # Convertir les résultats en liste de dictionnaires
        results = []
        for scored_point in search_result:
            result = {
                "id": scored_point.id,
                "score": scored_point.score
            }
            
            if with_payload and scored_point.payload:
                result["payload"] = scored_point.payload
                
            results.append(result)
            
        return results
    
    except Exception as e:
        # Observer la latence même en cas d'erreur
        latency = time.time() - start_time
        search_latency.observe(latency)
        
        logger.error(f"Erreur lors de la recherche dans la collection {collection_name}: {str(e)}")
        raise

def _build_qdrant_filter(filter_conditions: Optional[Dict[str, Any]]) -> Optional[Filter]:
    """
    Construit un filtre Qdrant à partir de conditions de filtrage.
    
    Args:
        filter_conditions: Conditions de filtrage
        
    Returns:
        Filtre Qdrant ou None
    """
    if not filter_conditions:
        return None
        
    filter_clauses = []
    
    for field, value in filter_conditions.items():
        # Gestion des différents types de conditions
        if isinstance(value, list):
            # Liste de valeurs possibles (OR)
            filter_clauses.append(
                FieldCondition(
                    key=field,
                    match=MatchValue(any=value)
                )
            )
        elif isinstance(value, dict) and ('min' in value or 'max' in value):
            # Plage de valeurs
            range_params = {}
            if 'min' in value:
                range_params['gte'] = value['min']
            if 'max' in value:
                range_params['lte'] = value['max']
            
            filter_clauses.append(
                FieldCondition(
                    key=field,
                    range=Range(**range_params)
                )
            )
        else:
            # Valeur exacte
            filter_clauses.append(
                FieldCondition(
                    key=field,
                    match=MatchValue(value=value)
                )
            )
    
    return Filter(must=filter_clauses)

@timed("qdrant_upsert_time", "Temps d'insertion/mise à jour Qdrant")
@circuit(name="qdrant_upsert", failure_threshold=3, recovery_timeout=60)
async def upsert_vectors(
    collection_name: str,
    points: List[Dict],
    batch_size: int = 100
) -> bool:
    """
    Insère ou met à jour des vecteurs dans une collection Qdrant.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        collection_name: Nom de la collection Qdrant
        points: Liste de dictionnaires avec les champs 'id', 'vector' et 'payload'
        batch_size: Taille de lot pour les insertions par lots
    
    Returns:
        True si l'opération est réussie, False sinon
    """
    if not points:
        return True
        
    # Incrémenter le compteur d'opérations
    vectorstore_operations.labels(operation="upsert").inc(len(points))
    
    client = get_qdrant_client()
    
    try:
        # Traitement par lots pour éviter les requêtes trop volumineuses
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            
            # Préparer les points pour l'insertion
            qdrant_points = []
            for point in batch:
                if 'id' not in point or 'vector' not in point:
                    logger.warning(f"Point invalide ignoré: {point}")
                    continue
                    
                qdrant_points.append(
                    rest.PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point.get("payload", {})
                    )
                )
            
            if not qdrant_points:
                continue
                
            # Insérer le lot avec retry pour plus de résilience
            await with_retry(
                lambda: client.upsert(
                    collection_name=collection_name,
                    points=qdrant_points
                ),
                retries=2,
                delay=1.0,
                backoff_factor=2.0,
                jitter=0.1
            )
            
            logger.debug(f"Lot {i//batch_size + 1} de {len(points)//batch_size + 1} inséré dans {collection_name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion de vecteurs dans la collection {collection_name}: {str(e)}")
        return False

@timed("qdrant_delete_time", "Temps de suppression Qdrant")
@circuit(name="qdrant_delete", failure_threshold=3, recovery_timeout=60)
async def delete_vectors(
    collection_name: str,
    ids: List[Union[str, int]]
) -> bool:
    """
    Supprime des vecteurs d'une collection Qdrant par leurs identifiants.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        collection_name: Nom de la collection Qdrant
        ids: Liste des identifiants des points à supprimer
    
    Returns:
        True si l'opération est réussie, False sinon
    """
    if not ids:
        return True
        
    # Incrémenter le compteur d'opérations
    vectorstore_operations.labels(operation="delete").inc(len(ids))
    
    client = get_qdrant_client()
    
    try:
        # Utiliser le retry pour plus de résilience
        await with_retry(
            lambda: client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(
                    points=ids
                )
            ),
            retries=2,
            delay=1.0,
            backoff_factor=2.0,
            jitter=0.1
        )
        
        logger.info(f"{len(ids)} vecteurs supprimés de la collection {collection_name}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de vecteurs dans la collection {collection_name}: {str(e)}")
        return False

@timed("qdrant_fixtures_by_date_time", "Temps de recherche des matchs par date")
async def search_fixtures_by_date(date: datetime.date, limit: int = 20) -> List[Dict]:
    """
    Recherche les matchs pour une date spécifique.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        date: Date des matchs à rechercher
        limit: Nombre maximum de résultats
    
    Returns:
        Liste des matchs pour cette date
    """
    collection_name = "fixtures"
    
    # Convertir la date en timestamps pour la recherche
    start_of_day = datetime.datetime.combine(date, datetime.time.min).isoformat()
    end_of_day = datetime.datetime.combine(date, datetime.time.max).isoformat()
    
    # Filtrer par date
    filter_conditions = {
        "date": {
            "gte": start_of_day,
            "lte": end_of_day
        }
    }
    
    # Générer un vecteur aléatoire pour une recherche par filtres uniquement
    random_vector = np.zeros(DEFAULT_EMBEDDING_DIM).tolist()
    
    try:
        results = await search_collection(
            collection_name=collection_name,
            query_vector=random_vector,
            filter_conditions=filter_conditions,
            limit=limit,
            with_payload=True,
            score_threshold=0  # Pas de seuil pour les recherches par filtres
        )
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la recherche des matchs pour la date {date}: {str(e)}")
        return []

@timed("qdrant_get_fixture_odds_time", "Temps de récupération des cotes")
async def get_fixture_odds(fixture_id: int) -> List[Dict]:
    """
    Récupère les cotes pour un match spécifique.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        fixture_id: ID du match
    
    Returns:
        Liste des cotes disponibles pour ce match
    """
    collection_name = "odds"
    
    # Filtrer par fixture_id
    filter_conditions = {
        "fixture_id": fixture_id
    }
    
    # Générer un vecteur aléatoire pour une recherche par filtres uniquement
    random_vector = np.zeros(DEFAULT_EMBEDDING_DIM).tolist()
    
    try:
        results = await search_collection(
            collection_name=collection_name,
            query_vector=random_vector,
            filter_conditions=filter_conditions,
            limit=100,  # Récupérer toutes les cotes pertinentes
            with_payload=True,
            score_threshold=0  # Pas de seuil pour les recherches par filtres
        )
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des cotes pour le match {fixture_id}: {str(e)}")
        return []

@timed("qdrant_get_fixture_prediction_time", "Temps de récupération des prédictions")
async def get_fixture_prediction(fixture_id: int) -> Optional[Dict]:
    """
    Récupère la prédiction pour un match spécifique.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        fixture_id: ID du match
    
    Returns:
        Prédiction pour ce match ou None si non trouvée
    """
    collection_name = "predictions"
    
    # Filtrer par fixture_id
    filter_conditions = {
        "fixture_id": fixture_id
    }
    
    # Générer un vecteur aléatoire pour une recherche par filtres uniquement
    random_vector = np.zeros(DEFAULT_EMBEDDING_DIM).tolist()
    
    try:
        results = await search_collection(
            collection_name=collection_name,
            query_vector=random_vector,
            filter_conditions=filter_conditions,
            limit=1,
            with_payload=True,
            score_threshold=0  # Pas de seuil pour les recherches par filtres
        )
        
        if results and len(results) > 0:
            return results[0]
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la prédiction pour le match {fixture_id}: {str(e)}")
        return None

@timed("qdrant_search_team_fixtures_time", "Temps de recherche des matchs par équipe")
async def search_team_fixtures(team_id: int, upcoming: bool = True, limit: int = 10) -> List[Dict]:
    """
    Recherche les matchs d'une équipe.
    Version optimisée avec métriques, retry et circuit breaker.
    
    Args:
        team_id: ID de l'équipe
        upcoming: Si True, recherche les matchs à venir, sinon les matchs passés
        limit: Nombre maximum de résultats
    
    Returns:
        Liste des matchs pour cette équipe
    """
    collection_name = "fixtures"
    
    # Construire un filtre pour chercher l'équipe à domicile ou à l'extérieur
    filter_conditions = {
        "$or": [
            {"home_team_id": team_id},
            {"away_team_id": team_id}
        ]
    }
    
    # Ajouter la condition de date
    now = datetime.datetime.now().isoformat()
    if upcoming:
        date_condition = {"date": {"gte": now}}
    else:
        date_condition = {"date": {"lt": now}}
    
    combined_filter = {"$and": [filter_conditions, date_condition]}
    
    # Générer un vecteur aléatoire pour une recherche par filtres uniquement
    random_vector = np.zeros(DEFAULT_EMBEDDING_DIM).tolist()
    
    try:
        results = await search_collection(
            collection_name=collection_name,
            query_vector=random_vector,
            filter_conditions=combined_filter,
            limit=limit,
            with_payload=True,
            score_threshold=0  # Pas de seuil pour les recherches par filtres
        )
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la recherche des matchs pour l'équipe {team_id}: {str(e)}")
        return []

@circuit(name="qdrant_mmr_search", failure_threshold=3, recovery_timeout=60)
async def search_with_mmr(
    collection_name: str,
    query_vector: List[float],
    filter_conditions: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    lambda_mult: float = 0.5,  # Facteur de diversité (0-1)
    score_threshold: Optional[float] = None
) -> List[Dict]:
    """
    Recherche avec l'algorithme MMR (Maximal Marginal Relevance) pour la diversité des résultats.
    
    Args:
        collection_name: Nom de la collection Qdrant
        query_vector: Vecteur d'embedding pour la recherche
        filter_conditions: Conditions de filtrage (dictionnaire)
        limit: Nombre maximum de résultats à retourner
        lambda_mult: Facteur de diversité (0 = max diversité, 1 = max pertinence)
        score_threshold: Seuil de score minimum pour les résultats
    
    Returns:
        Liste de dictionnaires contenant les résultats de recherche
    """
    # D'abord, récupérer plus de résultats que demandé
    larger_limit = min(limit * 3, 100)  # Prudence pour ne pas surcharger
    
    try:
        # Effectuer la recherche initiale
        initial_results = await search_collection(
            collection_name=collection_name,
            query_vector=query_vector,
            filter_conditions=filter_conditions,
            limit=larger_limit,
            with_payload=True,
            score_threshold=score_threshold
        )
        
        if not initial_results or len(initial_results) <= limit:
            return initial_results
        
        # Appliquer l'algorithme MMR
        selected_results = []
        remaining_results = initial_results.copy()
        
        # Sélectionner le premier résultat (le plus pertinent)
        selected_results.append(remaining_results.pop(0))
        
        # Sélectionner les résultats suivants avec MMR
        while len(selected_results) < limit and remaining_results:
            max_mmr_score = -float('inf')
            max_mmr_idx = -1
            
            for i, result in enumerate(remaining_results):
                # Pertinence vis-à-vis de la requête
                relevance = result['score']
                
                # Diversité vis-à-vis des résultats déjà sélectionnés
                max_similarity = 0
                for selected in selected_results:
                    # Calculer la similarité cosinus entre les vecteurs
                    # En pratique, on récupérerait les vecteurs depuis Qdrant
                    # Pour simplifier, nous utilisons une approximation basée sur les scores
                    similarity = min(relevance, selected['score']) / max(relevance, selected['score'])
                    max_similarity = max(max_similarity, similarity)
                
                # Calcul du score MMR
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_similarity
                
                if mmr_score > max_mmr_score:
                    max_mmr_score = mmr_score
                    max_mmr_idx = i
            
            if max_mmr_idx != -1:
                selected_results.append(remaining_results.pop(max_mmr_idx))
            else:
                break
        
        return selected_results
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche MMR dans {collection_name}: {str(e)}")
        # En cas d'erreur, revenir à la recherche standard
        return await search_collection(
            collection_name=collection_name,
            query_vector=query_vector,
            filter_conditions=filter_conditions,
            limit=limit,
            with_payload=True,
            score_threshold=score_threshold
        )

async def get_collection_stats_async(collection_name: str) -> Dict[str, Any]:
    """
    Version asynchrone de get_collection_stats pour récupérer les statistiques d'une collection.
    
    Args:
        collection_name: Nom de la collection
        
    Returns:
        Statistiques de la collection
    """
    client = get_qdrant_client()
    
    try:
        loop = asyncio.get_event_loop()
        collection_info = await loop.run_in_executor(
            None, lambda: client.get_collection(collection_name)
        )
        
        stats = {
            "name": collection_name,
            "vectors_count": collection_info.vectors_count,
            "points_count": collection_info.points_count,
            "segments_count": collection_info.segments_count,
            "status": collection_info.status,
            "vector_size": collection_info.config.params.vectors.size,
            "distance": collection_info.config.params.vectors.distance
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques pour {collection_name}: {str(e)}")
        return {
            "name": collection_name,
            "error": str(e),
            "status": "error"
        }