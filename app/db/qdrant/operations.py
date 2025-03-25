import logging
from typing import Dict, List, Optional, Union, Any

import numpy as np
from qdrant_client.http import models as rest
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, PointIdsList

from .client import get_qdrant_client
from .collections import get_collection_name

logger = logging.getLogger(__name__)

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