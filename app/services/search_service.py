# app/services/search_service.py
"""
Service pour la recherche sémantique dans Qdrant.
"""
import logging
from typing import List, Dict, Any, Optional, Union
import asyncio

from app.db.qdrant.operations import search_collection
from app.db.qdrant.collections import get_collection_name
from app.embedding.vectorize import get_embedding_for_text

logger = logging.getLogger(__name__)

class SearchService:
    """
    Service pour la recherche sémantique basée sur Qdrant.
    """
    
    @staticmethod
    async def search_by_text(
        text: str,
        entity_types: List[str] = None,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Recherche des entités par texte en utilisant la recherche sémantique.
        
        Args:
            text: Texte de recherche
            entity_types: Liste des types d'entités à rechercher (si None, recherche dans tous les types)
            filters: Filtres additionnels (champ: valeur)
            limit: Nombre maximum de résultats par type d'entité
            score_threshold: Seuil de score minimum pour les résultats
            
        Returns:
            Résultats de recherche regroupés par type d'entité
        """
        if not text:
            return {"error": "Le texte de recherche ne peut pas être vide"}
        
        # Générer l'embedding pour le texte de recherche
        query_vector = await get_embedding_for_text(text)
        
        if not query_vector:
            return {"error": "Impossible de générer un embedding pour le texte de recherche"}
        
        # Si aucun type n'est spécifié, utiliser tous les types disponibles
        if not entity_types:
            from app.db.postgres.models import ENTITY_MODEL_MAP
            entity_types = list(ENTITY_MODEL_MAP.keys())
        
        results = {}
        
        # Rechercher dans chaque type d'entité
        for entity_type in entity_types:
            collection_name = get_collection_name(entity_type)
            
            try:
                # Effectuer la recherche dans Qdrant
                search_results = search_collection(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    filter_conditions=filters,
                    limit=limit,
                    with_payload=True,
                    score_threshold=score_threshold
                )
                
                results[entity_type] = search_results
                
            except Exception as e:
                logger.error(f"Erreur lors de la recherche dans {collection_name}: {str(e)}")
                results[entity_type] = {"error": str(e)}
        
        return results
    
    @staticmethod
    async def get_similar_entities(
        entity_type: str,
        entity_id: int,
        limit: int = 10,
        exclude_self: bool = True,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Trouve des entités similaires à une entité donnée.
        
        Args:
            entity_type: Type de l'entité de référence
            entity_id: ID de l'entité de référence
            limit: Nombre maximum de résultats
            exclude_self: Si True, exclut l'entité de référence des résultats
            score_threshold: Seuil de score minimum pour les résultats
            
        Returns:
            Liste des entités similaires
        """
        collection_name = get_collection_name(entity_type)
        
        try:
            # Récupérer l'entité de référence depuis Qdrant
            from app.db.qdrant.client import get_qdrant_client
            client = get_qdrant_client()
            
            # Récupérer le vecteur de l'entité de référence
            entity_points = client.retrieve(
                collection_name=collection_name,
                ids=[entity_id],
                with_vectors=True
            )
            
            if not entity_points:
                return []
            
            entity_vector = entity_points[0].vector
            
            # Filtres pour exclure l'entité elle-même si nécessaire
            filter_conditions = None
            if exclude_self:
                filter_conditions = {"id": {"$ne": entity_id}}
            
            # Rechercher des entités similaires
            similar_entities = search_collection(
                collection_name=collection_name,
                query_vector=entity_vector,
                filter_conditions=filter_conditions,
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold
            )
            
            return similar_entities
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'entités similaires: {str(e)}")
            return []
    
    @staticmethod
    async def advanced_search(
        text: str = None,
        entity_types: List[str] = None,
        filters: Dict[str, Any] = None,
        sort_by: str = None,
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        score_threshold: float = 0.6,
        combine_results: bool = True
    ) -> Dict[str, Any]:
        """
        Recherche avancée avec filtres, tri et pagination.
        
        Args:
            text: Texte de recherche (si None, utilise uniquement les filtres)
            entity_types: Liste des types d'entités à rechercher
            filters: Filtres additionnels (champ: valeur)
            sort_by: Champ pour le tri des résultats
            sort_order: Ordre de tri ('asc' ou 'desc')
            limit: Nombre maximum de résultats
            offset: Offset pour la pagination
            score_threshold: Seuil de score minimum pour les résultats
            combine_results: Si True, combine les résultats de tous les types
            
        Returns:
            Résultats de recherche
        """
        # Validation des paramètres
        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"
            
        if text:
            # Recherche sémantique par texte
            query_vector = await get_embedding_for_text(text)
            if not query_vector:
                return {"error": "Impossible de générer un embedding pour le texte de recherche"}
        else:
            # Recherche uniquement par filtres
            query_vector = None
            
        # Si aucun type n'est spécifié, utiliser tous les types disponibles
        if not entity_types:
            from app.db.postgres.models import ENTITY_MODEL_MAP
            entity_types = list(ENTITY_MODEL_MAP.keys())
            
        all_results = []
        results_by_type = {}
        
        # Rechercher dans chaque type d'entité
        for entity_type in entity_types:
            collection_name = get_collection_name(entity_type)
            
            try:
                if query_vector:
                    # Recherche sémantique
                    search_results = search_collection(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        filter_conditions=filters,
                        limit=limit,
                        offset=offset,
                        with_payload=True,
                        score_threshold=score_threshold
                    )
                else:
                    # Recherche par filtres uniquement (utiliser un vecteur aléatoire avec score_threshold=0)
                    # Cette approche est discutable et pourrait être remplacée par une recherche directe dans PostgreSQL
                    import numpy as np
                    random_vector = np.random.rand(1536).tolist()  # Ajuster la dimension selon votre modèle
                    
                    search_results = search_collection(
                        collection_name=collection_name,
                        query_vector=random_vector,
                        filter_conditions=filters,
                        limit=limit,
                        offset=offset,
                        with_payload=True,
                        score_threshold=0  # Pas de seuil pour les recherches par filtres
                    )
                
                # Ajouter le type d'entité à chaque résultat
                for result in search_results:
                    result["entity_type"] = entity_type
                
                results_by_type[entity_type] = search_results
                all_results.extend(search_results)
                
            except Exception as e:
                logger.error(f"Erreur lors de la recherche dans {collection_name}: {str(e)}")
                results_by_type[entity_type] = []
        
        # Tri des résultats
        if sort_by:
            # Fonction de tri qui gère les cas où l'attribut n'existe pas
            def sort_key(item):
                payload = item.get("payload", {})
                if sort_by in payload:
                    return payload[sort_by] if payload[sort_by] is not None else (0 if sort_order == "asc" else float('inf'))
                return 0 if sort_order == "asc" else float('inf')
            
            all_results.sort(
                key=sort_key,
                reverse=(sort_order == "desc")
            )
        else:
            # Par défaut, trier par score de similitude
            all_results.sort(
                key=lambda x: x.get("score", 0),
                reverse=True
            )
        
        # Limiter les résultats
        all_results = all_results[offset:offset+limit]
        
        # Retourner les résultats au format approprié
        if combine_results:
            return {
                "total": len(all_results),
                "results": all_results
            }
        else:
            return {
                "total": sum(len(results) for results in results_by_type.values()),
                "results_by_type": results_by_type
            }
    
    @staticmethod
    async def entity_attribute_search(
        entity_type: str,
        attribute: str,
        value: Any,
        limit: int = 10,
        exact_match: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recherche des entités par valeur d'attribut.
        
        Args:
            entity_type: Type d'entité à rechercher
            attribute: Nom de l'attribut
            value: Valeur à rechercher
            limit: Nombre maximum de résultats
            exact_match: Si True, recherche une correspondance exacte
            
        Returns:
            Liste des entités correspondantes
        """
        collection_name = get_collection_name(entity_type)
        
        # Construire les filtres
        if exact_match:
            filter_conditions = {
                attribute: value
            }
        else:
            # Pour les correspondances partielles, utiliser une recherche sémantique
            # sur l'attribut text_content avec un score_threshold bas
            text_value = str(value)
            vector = await get_embedding_for_text(text_value)
            
            if not vector:
                return []
                
            return search_collection(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit,
                with_payload=True,
                score_threshold=0.5  # Seuil bas pour les correspondances partielles
            )
        
        # Utiliser un vecteur aléatoire avec score_threshold=0 pour les recherches par attribut exact
        import numpy as np
        random_vector = np.random.rand(1536).tolist()  # Ajuster la dimension selon votre modèle
        
        return search_collection(
            collection_name=collection_name,
            query_vector=random_vector,
            filter_conditions=filter_conditions,
            limit=limit,
            with_payload=True,
            score_threshold=0  # Pas de seuil pour les recherches par attribut
        )