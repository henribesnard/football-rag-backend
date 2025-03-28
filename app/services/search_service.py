# app/services/search_service.py
"""
Service pour la recherche sémantique dans Qdrant.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Union
import asyncio
from functools import lru_cache
import hashlib
import json

from app.db.qdrant.operations import search_collection
from app.db.qdrant.collections import get_collection_name
from app.embedding.vectorize import get_embedding_for_text
from app.monitoring.metrics import metrics, timed
from app.utils.circuit_breaker import circuit
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

# Métriques pour le monitoring
search_time = metrics.histogram(
    "search_time_seconds",
    "Temps de recherche (secondes)",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)

search_count = metrics.counter(
    "search_total",
    "Nombre total de recherches"
)

search_error_count = metrics.counter(
    "search_error_total",
    "Nombre total d'erreurs de recherche"
)

search_results_histogram = metrics.histogram(
    "search_results_count",
    "Nombre de résultats par recherche",
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

search_cache_hit = metrics.counter(
    "search_cache_hit_total",
    "Nombre total de hits dans le cache"
)

search_cache_miss = metrics.counter(
    "search_cache_miss_total",
    "Nombre total de miss dans le cache"
)

class SearchService:
    """
    Service pour la recherche sémantique basée sur Qdrant.
    Fonctionnalités améliorées:
    - Cache Redis pour les requêtes fréquentes
    - Stratégie de recherche hybride optimisée
    - Métriques détaillées
    - Protection par circuit breaker
    """
    
    @staticmethod
    @timed("search_by_text_time", "Temps de recherche par texte")
    @circuit(name="search_by_text", failure_threshold=5, recovery_timeout=60)
    async def search_by_text(
        text: str,
        entity_types: List[str] = None,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
        use_cache: bool = True,
        cache_ttl: int = 300  # 5 minutes par défaut
    ) -> Dict[str, Any]:
        """
        Recherche des entités par texte en utilisant la recherche sémantique.
        
        Args:
            text: Texte de recherche
            entity_types: Liste des types d'entités à rechercher (si None, recherche dans tous les types)
            filters: Filtres additionnels (champ: valeur)
            limit: Nombre maximum de résultats par type d'entité
            score_threshold: Seuil de score minimum pour les résultats
            use_cache: Si True, utilise le cache Redis pour les requêtes fréquentes
            cache_ttl: Durée de vie du cache en secondes
            
        Returns:
            Résultats de recherche regroupés par type d'entité
        """
        if not text:
            return {"error": "Le texte de recherche ne peut pas être vide"}
        
        # Incrémenter le compteur de recherches
        search_count.inc()
        
        # Vérifier le cache si activé
        if use_cache:
            cache_key = SearchService._generate_cache_key(
                "search_by_text",
                text=text,
                entity_types=entity_types,
                filters=filters,
                limit=limit,
                score_threshold=score_threshold
            )
            
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                # Incrémenter le compteur de hits de cache
                search_cache_hit.inc()
                logger.debug(f"Résultat trouvé dans le cache pour '{text}'")
                return cached_result
            
            # Incrémenter le compteur de miss de cache
            search_cache_miss.inc()
        
        start_time = time.time()
        
        try:
            # Générer l'embedding pour le texte de recherche
            query_vector = await get_embedding_for_text(
                text, 
                use_openai=True,  # Utiliser OpenAI pour une meilleure qualité
                domain_specific=True  # Utiliser le modèle spécifique au football
            )
            
            if not query_vector:
                logger.error(f"Impossible de générer un embedding pour le texte de recherche: '{text}'")
                return {"error": "Impossible de générer un embedding pour le texte de recherche"}
            
            # Si aucun type n'est spécifié, utiliser tous les types disponibles
            if not entity_types:
                from app.db.postgres.models import ENTITY_MODEL_MAP
                entity_types = list(ENTITY_MODEL_MAP.keys())
            
            results = {}
            total_results_count = 0
            
            # Rechercher dans chaque type d'entité en parallèle
            search_tasks = []
            for entity_type in entity_types:
                task = asyncio.create_task(
                    SearchService._search_single_collection(
                        entity_type=entity_type,
                        query_vector=query_vector,
                        filters=filters,
                        limit=limit,
                        score_threshold=score_threshold
                    )
                )
                search_tasks.append((entity_type, task))
            
            # Attendre que toutes les recherches soient terminées
            for entity_type, task in search_tasks:
                try:
                    search_results = await task
                    results[entity_type] = search_results
                    total_results_count += len(search_results)
                except Exception as e:
                    logger.error(f"Erreur lors de la recherche dans {entity_type}: {str(e)}")
                    results[entity_type] = {"error": str(e)}
                    search_error_count.inc()
            
            # Mesurer le nombre de résultats
            search_results_histogram.observe(total_results_count)
            
            # Ajouter des métadonnées au résultat
            final_result = {
                "query": text,
                "results": results,
                "total_results": total_results_count,
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            # Mettre en cache le résultat si demandé
            if use_cache and total_results_count > 0:
                await cache_service.set(cache_key, final_result, cache_ttl)
            
            return final_result
            
        except Exception as e:
            # Incrémenter le compteur d'erreurs
            search_error_count.inc()
            
            logger.error(f"Erreur lors de la recherche pour '{text}': {str(e)}")
            return {"error": f"Erreur lors de la recherche: {str(e)}"}
    
    @staticmethod
    async def _search_single_collection(
        entity_type: str,
        query_vector: List[float],
        filters: Dict[str, Any] = None,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Recherche dans une seule collection Qdrant.
        
        Args:
            entity_type: Type d'entité à rechercher
            query_vector: Vecteur de requête
            filters: Filtres additionnels
            limit: Nombre maximum de résultats
            score_threshold: Seuil de score minimum
            
        Returns:
            Liste des résultats de recherche
        """
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
            
            # Enrichir les résultats avec le type d'entité
            for result in search_results:
                result["entity_type"] = entity_type
            
            return search_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche dans {collection_name}: {str(e)}")
            raise
    
    @staticmethod
    @timed("search_get_similar_entities_time", "Temps de recherche d'entités similaires")
    @circuit(name="get_similar_entities", failure_threshold=3, recovery_timeout=60)
    async def get_similar_entities(
        entity_type: str,
        entity_id: int,
        limit: int = 10,
        exclude_self: bool = True,
        score_threshold: float = 0.7,
        use_cache: bool = True,
        cache_ttl: int = 1800  # 30 minutes par défaut (les entités similaires changent moins souvent)
    ) -> List[Dict[str, Any]]:
        """
        Trouve des entités similaires à une entité donnée.
        
        Args:
            entity_type: Type de l'entité de référence
            entity_id: ID de l'entité de référence
            limit: Nombre maximum de résultats
            exclude_self: Si True, exclut l'entité de référence des résultats
            score_threshold: Seuil de score minimum pour les résultats
            use_cache: Si True, utilise le cache Redis
            cache_ttl: Durée de vie du cache en secondes
            
        Returns:
            Liste des entités similaires
        """
        # Incrémenter le compteur de recherches
        search_count.inc()
        
        # Vérifier le cache si activé
        if use_cache:
            cache_key = SearchService._generate_cache_key(
                "similar_entities",
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
                exclude_self=exclude_self,
                score_threshold=score_threshold
            )
            
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                search_cache_hit.inc()
                return cached_result
            
            search_cache_miss.inc()
        
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
                logger.warning(f"Entité {entity_type} avec ID {entity_id} non trouvée")
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
            
            # Enrichir les résultats avec le type d'entité
            for entity in similar_entities:
                entity["entity_type"] = entity_type
            
            # Mettre en cache le résultat
            if use_cache:
                await cache_service.set(cache_key, similar_entities, cache_ttl)
            
            return similar_entities
            
        except Exception as e:
            # Incrémenter le compteur d'erreurs
            search_error_count.inc()
            
            logger.error(f"Erreur lors de la recherche d'entités similaires pour {entity_type} ID {entity_id}: {str(e)}")
            return []
    
    @staticmethod
    @timed("search_advanced_time", "Temps de recherche avancée")
    @circuit(name="advanced_search", failure_threshold=3, recovery_timeout=60)
    async def advanced_search(
        text: str = None,
        entity_types: List[str] = None,
        filters: Dict[str, Any] = None,
        sort_by: str = None,
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        score_threshold: float = 0.6,
        combine_results: bool = True,
        use_cache: bool = True,
        cache_ttl: int = 300
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
            use_cache: Si True, utilise le cache Redis
            cache_ttl: Durée de vie du cache en secondes
            
        Returns:
            Résultats de recherche
        """
        # Incrémenter le compteur de recherches
        search_count.inc()
        
        # Vérifier le cache si activé
        if use_cache:
            cache_key = SearchService._generate_cache_key(
                "advanced_search",
                text=text,
                entity_types=entity_types,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
                score_threshold=score_threshold,
                combine_results=combine_results
            )
            
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                search_cache_hit.inc()
                return cached_result
            
            search_cache_miss.inc()
        
        # Validation des paramètres
        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"
        
        start_time = time.time()
        
        try:
            # Générer l'embedding si un texte est fourni
            query_vector = None
            if text:
                query_vector = await get_embedding_for_text(
                    text, 
                    use_openai=True, 
                    domain_specific=True
                )
                
                if not query_vector:
                    return {"error": "Impossible de générer un embedding pour le texte de recherche"}
            
            # Si aucun type n'est spécifié, utiliser tous les types disponibles
            if not entity_types:
                from app.db.postgres.models import ENTITY_MODEL_MAP
                entity_types = list(ENTITY_MODEL_MAP.keys())
            
            all_results = []
            results_by_type = {}
            
            # Rechercher dans chaque type d'entité en parallèle
            search_tasks = []
            for entity_type in entity_types:
                task = asyncio.create_task(
                    SearchService._search_single_collection_advanced(
                        entity_type=entity_type,
                        query_vector=query_vector,
                        filters=filters,
                        limit=limit if not combine_results else limit * 2,  # Récupérer plus si on combine
                        offset=offset if not combine_results else 0,  # Offset après combinaison
                        score_threshold=score_threshold if query_vector else 0
                    )
                )
                search_tasks.append((entity_type, task))
            
            # Attendre que toutes les recherches soient terminées
            for entity_type, task in search_tasks:
                try:
                    search_results = await task
                    
                    # Ajouter le type d'entité à chaque résultat
                    for result in search_results:
                        result["entity_type"] = entity_type
                    
                    results_by_type[entity_type] = search_results
                    all_results.extend(search_results)
                except Exception as e:
                    logger.error(f"Erreur lors de la recherche avancée dans {entity_type}: {str(e)}")
                    results_by_type[entity_type] = []
                    search_error_count.inc()
            
            # Trier les résultats
            if combine_results:
                # Trier tous les résultats ensemble
                if sort_by:
                    # Fonction de tri qui gère les cas où l'attribut n'existe pas
                    def sort_key(item):
                        payload = item.get("payload", {})
                        if sort_by in payload:
                            value = payload[sort_by]
                            if value is None:
                                return 0 if sort_order == "asc" else float('inf')
                            return value
                        return 0 if sort_order == "asc" else float('inf')
                    
                    all_results.sort(
                        key=sort_key,
                        reverse=(sort_order == "desc")
                    )
                else:
                    # Par défaut, trier par score de similarité
                    all_results.sort(
                        key=lambda x: x.get('score', 0),
                        reverse=True
                    )
                
                # Appliquer la pagination
                paginated_results = all_results[offset:offset + limit]
                
                result = {
                    "total": len(all_results),
                    "offset": offset,
                    "limit": limit,
                    "results": paginated_results,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            else:
                # Garder les résultats séparés par type
                result = {
                    "total": sum(len(results) for results in results_by_type.values()),
                    "results_by_type": results_by_type,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            
            # Mesurer le nombre de résultats
            search_results_histogram.observe(result["total"])
            
            # Mettre en cache le résultat
            if use_cache:
                await cache_service.set(cache_key, result, cache_ttl)
            
            return result
            
        except Exception as e:
            # Incrémenter le compteur d'erreurs
            search_error_count.inc()
            
            logger.error(f"Erreur lors de la recherche avancée: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    async def _search_single_collection_advanced(
        entity_type: str,
        query_vector: List[float] = None,
        filters: Dict[str, Any] = None,
        limit: int = 20,
        offset: int = 0,
        score_threshold: float = 0
    ) -> List[Dict[str, Any]]:
        """
        Recherche avancée dans une seule collection Qdrant.
        
        Args:
            entity_type: Type d'entité à rechercher
            query_vector: Vecteur de requête (None pour recherche par filtres uniquement)
            filters: Filtres additionnels
            limit: Nombre maximum de résultats
            offset: Offset pour la pagination
            score_threshold: Seuil de score minimum
            
        Returns:
            Liste des résultats de recherche
        """
        collection_name = get_collection_name(entity_type)
        
        try:
            # Si pas de vecteur de requête, générer un vecteur aléatoire
            # pour permettre la recherche par filtres uniquement
            if query_vector is None:
                import numpy as np
                # Déterminer la dimension du vecteur (en fonction du modèle d'embedding)
                from app.config import settings
                vector_size = settings.EMBEDDING_DIM
                query_vector = np.random.rand(vector_size).tolist()
                score_threshold = 0  # Ignorer le score pour les recherches par filtres
            
            # Effectuer la recherche dans Qdrant
            search_results = search_collection(
                collection_name=collection_name,
                query_vector=query_vector,
                filter_conditions=filters,
                limit=limit,
                offset=offset,
                with_payload=True,
                score_threshold=score_threshold
            )
            
            return search_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche avancée dans {collection_name}: {str(e)}")
            raise
    
    @staticmethod
    @timed("search_entity_attribute_time", "Temps de recherche par attribut d'entité")
    async def entity_attribute_search(
        entity_type: str,
        attribute: str,
        value: Any,
        limit: int = 10,
        exact_match: bool = True,
        use_cache: bool = True,
        cache_ttl: int = 600  # 10 minutes par défaut
    ) -> List[Dict[str, Any]]:
        """
        Recherche des entités par valeur d'attribut.
        
        Args:
            entity_type: Type d'entité à rechercher
            attribute: Nom de l'attribut
            value: Valeur à rechercher
            limit: Nombre maximum de résultats
            exact_match: Si True, recherche une correspondance exacte
            use_cache: Si True, utilise le cache Redis
            cache_ttl: Durée de vie du cache en secondes
            
        Returns:
            Liste des entités correspondantes
        """
        # Incrémenter le compteur de recherches
        search_count.inc()
        
        # Vérifier le cache si activé
        if use_cache:
            cache_key = SearchService._generate_cache_key(
                "entity_attribute_search",
                entity_type=entity_type,
                attribute=attribute,
                value=value,
                limit=limit,
                exact_match=exact_match
            )
            
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                search_cache_hit.inc()
                return cached_result
            
            search_cache_miss.inc()
        
        collection_name = get_collection_name(entity_type)
        
        try:
            # Construire les filtres
            if exact_match:
                filter_conditions = {
                    attribute: value
                }
                
                # Générer un vecteur aléatoire pour les recherches par attribut
                import numpy as np
                from app.config import settings
                vector_size = settings.EMBEDDING_DIM
                random_vector = np.random.rand(vector_size).tolist()
                
                search_results = search_collection(
                    collection_name=collection_name,
                    query_vector=random_vector,
                    filter_conditions=filter_conditions,
                    limit=limit,
                    with_payload=True,
                    score_threshold=0  # Pas de seuil pour les recherches par attribut
                )
            else:
                # Pour les correspondances partielles, utiliser une recherche sémantique
                text_value = str(value)
                vector = await get_embedding_for_text(text_value)
                
                if not vector:
                    logger.error(f"Impossible de générer un embedding pour la valeur d'attribut: {text_value}")
                    return []
                
                search_results = search_collection(
                    collection_name=collection_name,
                    query_vector=vector,
                    limit=limit,
                    with_payload=True,
                    score_threshold=0.5  # Seuil bas pour les correspondances partielles
                )
            
            # Ajouter le type d'entité à chaque résultat
            for result in search_results:
                result["entity_type"] = entity_type
            
            # Mettre en cache le résultat
            if use_cache:
                await cache_service.set(cache_key, search_results, cache_ttl)
            
            return search_results
            
        except Exception as e:
            # Incrémenter le compteur d'erreurs
            search_error_count.inc()
            
            logger.error(f"Erreur lors de la recherche par attribut {attribute}={value} dans {entity_type}: {str(e)}")
            return []
    
    @staticmethod
    def _generate_cache_key(prefix: str, **kwargs) -> str:
        """
        Génère une clé de cache cohérente à partir des paramètres de recherche.
        
        Args:
            prefix: Préfixe pour la clé
            **kwargs: Paramètres de la recherche
            
        Returns:
            Clé de cache unique
        """
        # Normaliser les paramètres pour assurer la cohérence
        normalized_params = {}
        for key, value in kwargs.items():
            if isinstance(value, (list, tuple)):
                # Trier les listes pour assurer la cohérence
                normalized_params[key] = sorted(value) if value else None
            elif isinstance(value, dict):
                # Convertir les dictionnaires en chaînes JSON triées
                normalized_params[key] = json.dumps(value, sort_keys=True) if value else None
            else:
                normalized_params[key] = value
        
        # Trier les paramètres par clé
        sorted_params = sorted([(k, v) for k, v in normalized_params.items() if v is not None])
        
        # Générer une chaîne de paramètres
        param_str = ",".join(f"{k}:{v}" for k, v in sorted_params)
        
        # Générer un hash pour éviter les clés trop longues
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        
        return f"search:{prefix}:{param_hash}"
    
    @staticmethod
    async def invalidate_cache(entity_type: str = None, entity_id: int = None) -> int:
        """
        Invalide le cache de recherche pour une entité spécifique ou un type d'entité.
        
        Args:
            entity_type: Type d'entité (None pour invalider tous les types)
            entity_id: ID de l'entité (None pour invalider tout le type)
            
        Returns:
            Nombre d'entrées de cache invalidées
        """
        patterns = []
        
        if entity_type and entity_id:
            # Invalider le cache pour une entité spécifique
            patterns.append(f"search:*{entity_type}*{entity_id}*")
        elif entity_type:
            # Invalider le cache pour un type d'entité
            patterns.append(f"search:*{entity_type}*")
        else:
            # Invalider tout le cache de recherche
            patterns.append("search:*")
        
        total_invalidated = 0
        for pattern in patterns:
            count = await cache_service.delete_pattern(pattern)
            total_invalidated += count
        
        logger.info(f"Cache de recherche invalidé: {total_invalidated} entrées supprimées")
        return total_invalidated