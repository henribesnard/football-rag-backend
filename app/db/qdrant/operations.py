import logging
from typing import Dict, List, Optional, Union, Any
import datetime

import numpy as np
from qdrant_client.http import models as rest
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, PointIdsList

from .client import get_qdrant_client
from .collections import get_collection_name

logger = logging.getLogger(__name__)

# Dimension d'embedding par défaut (à remplacer par settings.EMBEDDING_DIM lorsque disponible)
DEFAULT_EMBEDDING_DIM = 1024

def search_collection(
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
    client = get_qdrant_client()
    
    # Convertir les conditions de filtrage en objet Filter de Qdrant
    qdrant_filter = None
    if filter_conditions:
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
        
        qdrant_filter = Filter(must=filter_clauses)
    
    try:
        # Effectuer la recherche
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            offset=offset,
            with_payload=with_payload,
            score_threshold=score_threshold
        )
        
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
        logger.error(f"Erreur lors de la recherche dans la collection {collection_name}: {str(e)}")
        raise

def upsert_vectors(
    collection_name: str,
    points: List[Dict],
    batch_size: int = 100
) -> bool:
    """
    Insère ou met à jour des vecteurs dans une collection Qdrant.
    
    Args:
        collection_name: Nom de la collection Qdrant
        points: Liste de dictionnaires avec les champs 'id', 'vector' et 'payload'
        batch_size: Taille de lot pour les insertions par lots
    
    Returns:
        True si l'opération est réussie, False sinon
    """
    client = get_qdrant_client()
    
    try:
        # Traitement par lots pour éviter les requêtes trop volumineuses
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            
            # Préparer les points pour l'insertion
            qdrant_points = []
            for point in batch:
                qdrant_points.append(
                    rest.PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point.get("payload", {})
                    )
                )
            
            # Insérer le lot
            client.upsert(
                collection_name=collection_name,
                points=qdrant_points
            )
            
            logger.debug(f"Lot {i//batch_size + 1} de {len(points)//batch_size + 1} inséré dans {collection_name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion de vecteurs dans la collection {collection_name}: {str(e)}")
        return False

def delete_vectors(
    collection_name: str,
    ids: List[Union[str, int]]
) -> bool:
    """
    Supprime des vecteurs d'une collection Qdrant par leurs identifiants.
    
    Args:
        collection_name: Nom de la collection Qdrant
        ids: Liste des identifiants des points à supprimer
    
    Returns:
        True si l'opération est réussie, False sinon
    """
    client = get_qdrant_client()
    
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(
                points=ids
            )
        )
        
        logger.info(f"{len(ids)} vecteurs supprimés de la collection {collection_name}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de vecteurs dans la collection {collection_name}: {str(e)}")
        return False
    
def search_fixtures_by_date(date: datetime.date, limit: int = 20) -> List[Dict]:
    """
    Recherche les matchs pour une date spécifique.
    
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
        results = search_collection(
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

def get_fixture_odds(fixture_id: int) -> List[Dict]:
    """
    Récupère les cotes pour un match spécifique.
    
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
        results = search_collection(
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

def get_fixture_prediction(fixture_id: int) -> Optional[Dict]:
    """
    Récupère la prédiction pour un match spécifique.
    
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
        results = search_collection(
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

def search_team_fixtures(team_id: int, upcoming: bool = True, limit: int = 10) -> List[Dict]:
    """
    Recherche les matchs d'une équipe.
    
    Args:
        team_id: ID de l'équipe
        upcoming: Si True, recherche les matchs à venir, sinon les matchs passés
        limit: Nombre maximum de résultats
    
    Returns:
        Liste des matchs pour cette équipe
    """
    collection_name = "fixtures"
    
    # Filtrer par équipe (domicile ou extérieur)
    team_filter = {
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
    
    filter_conditions = {
        "$and": [team_filter, date_condition]
    }
    
    # Générer un vecteur aléatoire pour une recherche par filtres uniquement
    random_vector = np.zeros(DEFAULT_EMBEDDING_DIM).tolist()
    
    try:
        results = search_collection(
            collection_name=collection_name,
            query_vector=random_vector,
            filter_conditions=filter_conditions,
            limit=limit,
            with_payload=True,
            score_threshold=0  # Pas de seuil pour les recherches par filtres
        )
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la recherche des matchs pour l'équipe {team_id}: {str(e)}")
        return []