"""
Service RAG (Retrieval-Augmented Generation) pour répondre aux questions sur le football.
Version avancée avec intégration LLM et reranking spécifique au football.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
import time
from datetime import datetime

from app.services.search_service import SearchService
from app.services.reranking_service import reranking_service
from app.services.llm_service import llm_service
from app.services.cache_service import cache_service
from app.embedding.vectorize import get_embedding_for_text
from app.monitoring.metrics import metrics, timed
from app.config import settings
from app.utils.circuit_breaker import circuit

logger = logging.getLogger(__name__)

# Métriques
rag_processing_time = metrics.histogram(
    "rag_processing_time",
    "Temps de traitement RAG (secondes)",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
)

rag_request_counter = metrics.counter(
    "rag_requests_total",
    "Nombre total de requêtes RAG"
)

rag_cache_hit_counter = metrics.counter(
    "rag_cache_hits_total",
    "Nombre total de hits sur le cache RAG"
)

rag_cache_miss_counter = metrics.counter(
    "rag_cache_misses_total",
    "Nombre total de miss sur le cache RAG"
)

rag_error_counter = metrics.counter(
    "rag_errors_total",
    "Nombre total d'erreurs RAG"
)

class RagService:
    """
    Service RAG pour répondre aux questions sur le football.
    """
    
    @staticmethod
    @timed("rag_answer_question_time", "Temps pour répondre à une question")
    @circuit(name="rag_answer_question", failure_threshold=3, recovery_timeout=60)
    async def answer_question(
        question: str,
        max_context_items: int = None,
        score_threshold: float = None,
        use_reranking: bool = None,
        use_llm: bool = True,
        use_cache: bool = True,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Répond à une question en utilisant le RAG.
        
        Args:
            question: Question posée
            max_context_items: Nombre maximum d'éléments à inclure dans le contexte
            score_threshold: Seuil de score minimum pour les résultats de recherche
            use_reranking: Si True, utilise le reranking pour améliorer les résultats
            use_llm: Si True, utilise un LLM pour générer la réponse
            use_cache: Si True, utilise le cache pour les réponses
            user_id: ID de l'utilisateur (pour personnaliser les réponses)
            
        Returns:
            Réponse avec contexte et sources
        """
        if not question:
            return {"error": "La question ne peut pas être vide"}
        
        # Incrémenter le compteur de requêtes
        rag_request_counter.inc()
        
        # Utiliser les valeurs par défaut de configuration si non spécifiées
        max_context_items = max_context_items or settings.RAG_MAX_CONTEXT_ITEMS
        score_threshold = score_threshold or settings.RAG_MIN_SCORE_THRESHOLD
        use_reranking = use_reranking if use_reranking is not None else settings.RAG_USE_RERANKING
        
        # Vérifier le cache si activé
        if use_cache:
            cache_key = f"rag:answer:{hash(question)}:{max_context_items}:{score_threshold}:{use_reranking}:{use_llm}"
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                rag_cache_hit_counter.inc()
                logger.debug(f"Réponse trouvée dans le cache pour la question: {question[:50]}...")
                return cached_result
            rag_cache_miss_counter.inc()
        
        start_time = time.time()
        
        try:
            # 1. Recherche sémantique
            entity_types = ['country', 'team', 'player', 'fixture', 'league', 'coach', 'standing']
            search_results = await SearchService.search_by_text(
                text=question,
                entity_types=entity_types,
                limit=max_context_items * 2,  # Récupérer plus de résultats pour le reranking
                score_threshold=score_threshold
            )
            
            # 2. Consolidation des résultats
            consolidated_results = []
            for entity_type, results in search_results.get("results", {}).items():
                if isinstance(results, list):
                    for result in results:
                        if 'payload' in result:
                            # Enrichir le résultat avec le type d'entité
                            result['entity_type'] = entity_type
                            consolidated_results.append(result)
            
            # 3. Reranking si activé
            if use_reranking and consolidated_results:
                # Utiliser le reranking spécifique au football
                reranked_results = await reranking_service.rerank(
                    query=question,
                    results=consolidated_results,
                    max_results=max_context_items
                )
                context_items = reranked_results
            else:
                # Trier par score de similarité et limiter
                consolidated_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                context_items = consolidated_results[:max_context_items]
            
            # 4. Construction du contexte
            context, sources = await RagService._build_context_and_sources(context_items)
            
            # 5. Analyse de la complexité de la question pour déterminer le modèle à utiliser
            complexity_analysis = None
            if use_llm:
                try:
                    complexity_analysis = await llm_service.analyze_question_complexity(question)
                    logger.debug(f"Analyse de complexité: {complexity_analysis}")
                except Exception as e:
                    logger.warning(f"Erreur lors de l'analyse de complexité: {str(e)}")
            
            # 6. Construction de la réponse
            if use_llm and llm_service is not None:
                # Déterminer si on utilise le modèle de raisonnement
                use_reasoner = complexity_analysis.get("use_reasoner", False) if complexity_analysis else False
                
                answer = await llm_service.generate_response(
                    question=question,
                    context=context,
                    use_reasoner=use_reasoner,
                    max_tokens=settings.OPENAI_MAX_TOKENS
                )
            else:
                # Réponse simple sans LLM
                answer = RagService._generate_fallback_response(question, context)
            
            # 7. Préparation du résultat final
            result = {
                "question": question,
                "answer": answer,
                "sources": sources,
                "context_items_count": len(context_items),
                "processing_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # Ajouter l'analyse de complexité si disponible
            if complexity_analysis:
                result["complexity"] = {
                    "score": complexity_analysis.get("complexity", 0),
                    "reasoning_required": complexity_analysis.get("reasoning_required", False),
                    "reasoning_type": complexity_analysis.get("reasoning_type", "none")
                }
            
            # Mettre en cache le résultat
            if use_cache:
                await cache_service.set(cache_key, result, ttl=settings.CACHE_TTL)
            
            return result
        
        except Exception as e:
            # Incrémenter le compteur d'erreurs
            rag_error_counter.inc()
            
            logger.error(f"Erreur lors de la réponse à la question '{question}': {str(e)}")
            return {
                "question": question,
                "error": f"Erreur lors de la génération de la réponse: {str(e)}",
                "processing_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    async def _build_context_and_sources(
        context_items: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Construit le contexte et les sources pour la génération de réponse.
        
        Args:
            context_items: Éléments de contexte (résultats de recherche)
            
        Returns:
            Tuple (contexte formaté, liste des sources)
        """
        context_texts = []
        sources = []
        
        for item in context_items:
            payload = item.get('payload', {})
            entity_type = item.get('entity_type', 'unknown')
            
            # Récupérer le contenu textuel
            if 'text_content' in payload:
                context_text = payload['text_content']
            else:
                # Construire un texte à partir des attributs disponibles
                context_text = f"Type: {entity_type}\n"
                
                for key, value in payload.items():
                    if key not in ['id', 'external_id', 'update_at', 'created_at'] and value is not None:
                        context_text += f"{key}: {value}\n"
            
            context_texts.append(context_text)
            
            # Construction de la source
            source = {
                "id": payload.get('id'),
                "type": entity_type,
                "name": payload.get('name', f"ID:{payload.get('id', 'unknown')}"),
                "relevance_score": item.get('rerank_score') or item.get('score', 0)
            }
            sources.append(source)
        
        # Fusion des textes de contexte
        full_context = "\n\n".join(context_texts)
        
        return full_context, sources
    
    @staticmethod
    def _generate_fallback_response(question: str, context: str) -> str:
        """
        Génère une réponse de secours si le LLM n'est pas disponible.
        
        Args:
            question: Question posée
            context: Contexte pour la génération de réponse
            
        Returns:
            Réponse générée
        """
        # Version simple de réponse en cas d'indisponibilité du LLM
        context_summary = context[:500] + "..." if len(context) > 500 else context
        
        answer = (
            "Voici les informations pertinentes que j'ai trouvées en réponse à votre question:\n\n"
            f"{context_summary}\n\n"
            "Note: Cette réponse est générée automatiquement à partir des informations disponibles."
        )
        
        return answer
    
    @staticmethod
    @timed("rag_entity_details_time", "Temps pour récupérer les détails d'une entité")
    @circuit(name="rag_entity_details", failure_threshold=3, recovery_timeout=60)
    async def get_entity_details(
        entity_type: str,
        entity_id: int,
        include_related: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Récupère les détails d'une entité spécifique et les entités associées.
        
        Args:
            entity_type: Type d'entité
            entity_id: ID de l'entité
            include_related: Si True, inclut les entités liées
            use_cache: Si True, utilise le cache
            
        Returns:
            Détails de l'entité et entités associées
        """
        # Vérifier le cache si activé
        if use_cache:
            cache_key = f"rag:entity:{entity_type}:{entity_id}:{include_related}"
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                rag_cache_hit_counter.inc()
                return cached_result
            rag_cache_miss_counter.inc()
        
        try:
            from app.db.qdrant.client import get_qdrant_client
            from app.db.qdrant.collections import get_collection_name
            
            collection_name = get_collection_name(entity_type)
            client = get_qdrant_client()
            
            # Récupérer l'entité depuis Qdrant
            entity_points = client.retrieve(
                collection_name=collection_name,
                ids=[entity_id],
                with_vectors=False,
                with_payload=True
            )
            
            if not entity_points:
                return {"error": f"Entité {entity_type} avec ID {entity_id} non trouvée"}
            
            entity_data = entity_points[0].payload
            
            result = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "data": entity_data
            }
# Récupérer les entités associées si demandé
            if include_related:
                related_entities = await RagService._get_related_entities(entity_type, entity_id, entity_data)
                result["related_entities"] = related_entities
                
                # Récupérer les entités similaires
                similar_entities = await SearchService.get_similar_entities(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    limit=5,
                    exclude_self=True
                )
                result["similar_entities"] = similar_entities
            
            # Mettre en cache le résultat
            if use_cache:
                await cache_service.set(f"rag:entity:{entity_type}:{entity_id}:{include_related}", result, ttl=settings.CACHE_TTL)
            
            return result
            
        except Exception as e:
            # Incrémenter le compteur d'erreurs
            rag_error_counter.inc()
            
            logger.error(f"Erreur lors de la récupération des détails de l'entité: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    async def _get_related_entities(
        entity_type: str,
        entity_id: int,
        entity_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Récupère les entités associées à l'entité spécifiée.
        
        Args:
            entity_type: Type d'entité
            entity_id: ID de l'entité
            entity_data: Données de l'entité
            
        Returns:
            Dictionnaire des entités associées par type
        """
        related = {}
        
        # Analyse des champs pour identifier les relations
        for key, value in entity_data.items():
            # Chercher les clés qui ressemblent à des relations
            if key.endswith('_id') and isinstance(value, int) and value > 0:
                relation_type = key[:-3]  # Retirer '_id'
                
                # Vérifier si le type de relation est valide
                if relation_type in ['team', 'player', 'league', 'country', 'coach']:
                    # Récupérer l'entité associée
                    from app.db.qdrant.client import get_qdrant_client
                    from app.db.qdrant.collections import get_collection_name
                    
                    try:
                        collection_name = get_collection_name(relation_type)
                        client = get_qdrant_client()
                        related_points = client.retrieve(
                            collection_name=collection_name,
                            ids=[value],
                            with_vectors=False,
                            with_payload=True
                        )
                        
                        if related_points:
                            if relation_type not in related:
                                related[relation_type] = []
                            
                            related_entity = {
                                "id": value,
                                "data": related_points[0].payload
                            }
                            related[relation_type].append(related_entity)
                    except Exception as e:
                        logger.warning(f"Erreur lors de la récupération de l'entité associée {relation_type} (ID: {value}): {str(e)}")
        
        # Cas spécifiques selon le type d'entité
        if entity_type == 'team':
            # Récupérer les joueurs de l'équipe
            try:
                players = await SearchService.entity_attribute_search(
                    entity_type='player',
                    attribute='team_id',
                    value=entity_id,
                    limit=20
                )
                if players:
                    related['players'] = players
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des joueurs de l'équipe: {str(e)}")
                
        elif entity_type == 'player':
            # Récupérer les statistiques du joueur
            try:
                stats = await SearchService.entity_attribute_search(
                    entity_type='player_statistics',
                    attribute='player_id',
                    value=entity_id,
                    limit=10
                )
                if stats:
                    related['statistics'] = stats
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des statistiques du joueur: {str(e)}")
        
        elif entity_type == 'league':
            # Récupérer les équipes de la ligue
            try:
                standings = await SearchService.entity_attribute_search(
                    entity_type='standing',
                    attribute='league_id',
                    value=entity_id,
                    limit=30
                )
                if standings:
                    related['standings'] = standings
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des classements de la ligue: {str(e)}")
        
        return related
    
    @staticmethod
    @timed("rag_analyze_content_time", "Temps d'analyse de contenu")
    @circuit(name="rag_analyze_content", failure_threshold=3, recovery_timeout=60)
    async def analyze_football_content(
        content: str,
        identify_entities: bool = True,
        extract_facts: bool = True,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Analyse un contenu textuel lié au football pour identifier les entités et extraire des faits.
        
        Args:
            content: Contenu textuel à analyser
            identify_entities: Si True, identifie les entités mentionnées
            extract_facts: Si True, extrait des faits du contenu
            use_llm: Si True, utilise un LLM pour l'extraction des faits
            
        Returns:
            Résultats de l'analyse
        """
        if not content:
            return {"error": "Le contenu ne peut pas être vide"}
        
        results = {
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        }
        
        # Identifier les entités mentionnées
        if identify_entities:
            # Vectoriser le contenu
            content_vector = await get_embedding_for_text(content)
            
            if content_vector:
                # Rechercher dans les collections principales
                entity_types = ['team', 'player', 'league', 'country', 'coach']
                identified_entities = {}
                
                for entity_type in entity_types:
                    try:
                        from app.db.qdrant.operations import search_collection
                        from app.db.qdrant.collections import get_collection_name
                        
                        collection_name = get_collection_name(entity_type)
                        search_results = await search_collection(
                            collection_name=collection_name,
                            query_vector=content_vector,
                            limit=5,
                            with_payload=True,
                            score_threshold=0.75  # Seuil assez élevé pour éviter les faux positifs
                        )
                        
                        if search_results:
                            identified_entities[entity_type] = search_results
                    except Exception as e:
                        logger.warning(f"Erreur lors de la recherche d'entités de type {entity_type}: {str(e)}")
                
                results["identified_entities"] = identified_entities
        
        # Extraire des faits avec un LLM
        if extract_facts and use_llm and llm_service is not None:
            try:
                # Utiliser le LLM pour extraire des faits
                extraction_prompt = (
                    "Analyze this football text and extract key facts and insights. "
                    "Focus on player performances, match results, team statistics, and tactical observations. "
                    "Return a JSON array of facts with format: [{\"fact\": \"...\", \"category\": \"...\"}]"
                )
                
                extracted_text = await llm_service.generate_response(
                    question="Extract key football facts from this text",
                    context=content,
                    system_prompt=extraction_prompt,
                    use_reasoner=False
                )
                
                # Tenter de parser le JSON retourné
                try:
                    facts = json.loads(extracted_text)
                    results["extracted_facts"] = facts
                except json.JSONDecodeError:
                    # Si le format n'est pas un JSON valide, utiliser le texte brut
                    results["extracted_facts_text"] = extracted_text
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'extraction des faits: {str(e)}")
                results["extracted_facts"] = [
                    "Une erreur s'est produite lors de l'extraction des faits."
                ]
        elif extract_facts:
            # Simulation d'extraction sans LLM
            results["extracted_facts"] = [
                "Cette fonction simule l'extraction de faits.",
                "Dans une implémentation réelle, un LLM analyserait le contenu pour identifier les faits importants."
            ]
        
        return results
    
    @staticmethod
    @timed("rag_get_football_stats_time", "Temps de récupération des statistiques")
    @circuit(name="rag_get_football_stats", failure_threshold=3, recovery_timeout=60)
    async def get_football_stats(
        entity_type: str,
        entity_id: int,
        stat_type: str = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques liées au football pour une entité donnée.
        
        Args:
            entity_type: Type d'entité (team, player, league)
            entity_id: ID de l'entité
            stat_type: Type de statistique spécifique (optionnel)
            use_cache: Si True, utilise le cache
            
        Returns:
            Statistiques formatées
        """
        # Vérifier les types d'entités supportés
        if entity_type not in ['team', 'player', 'league']:
            return {"error": f"Type d'entité non supporté pour les statistiques: {entity_type}"}
        
        # Vérifier le cache si activé
        if use_cache:
            cache_key = f"rag:stats:{entity_type}:{entity_id}:{stat_type or 'all'}"
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                rag_cache_hit_counter.inc()
                return cached_result
            rag_cache_miss_counter.inc()
        
        # Récupérer l'entité principale
        entity_details = await RagService.get_entity_details(
            entity_type=entity_type,
            entity_id=entity_id,
            include_related=False
        )
        
        if "error" in entity_details:
            return entity_details
        
        entity_data = entity_details.get("data", {})
        
        # Initialiser les résultats
        stats_results = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_data.get("name", f"ID:{entity_id}"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Cas spécifiques selon le type d'entité
        if entity_type == 'player':
            # Récupérer les statistiques du joueur
            player_stats = await SearchService.entity_attribute_search(
                entity_type='player_statistics',
                attribute='player_id',
                value=entity_id,
                limit=50
            )
            
            if player_stats:
                # Agréger les statistiques
                aggregated_stats = {
                    "matches_played": len(player_stats),
                    "goals": sum(stat.get("payload", {}).get("goals", 0) for stat in player_stats),
                    "assists": sum(stat.get("payload", {}).get("assists", 0) for stat in player_stats),
                    "total_minutes": sum(stat.get("payload", {}).get("minutes_played", 0) for stat in player_stats),
                    "yellow_cards": sum(stat.get("payload", {}).get("yellow_cards", 0) for stat in player_stats),
                    "red_cards": sum(stat.get("payload", {}).get("red_cards", 0) for stat in player_stats),
                    "average_rating": sum(float(stat.get("payload", {}).get("rating", 0) or 0) for stat in player_stats) / len(player_stats) if player_stats else 0
                }
                
                stats_results["aggregated_stats"] = aggregated_stats
                
                # Ajouter les statistiques détaillées (uniquement si demandées spécifiquement)
                if stat_type == "detailed":
                    stats_results["detailed_stats"] = player_stats
            else:
                stats_results["message"] = "Aucune statistique trouvée pour ce joueur"
        
        elif entity_type == 'team':
            # Récupérer les statistiques de l'équipe
            team_stats = await SearchService.entity_attribute_search(
                entity_type='team_statistics',
                attribute='team_id',
                value=entity_id,
                limit=10
            )
            
            if team_stats:
                # Prendre les statistiques les plus récentes
                latest_stats = max(team_stats, key=lambda x: x.get("payload", {}).get("update_at", ""))
                
                # Formater les statistiques
                stats_data = latest_stats.get("payload", {})
                
                formatted_stats = {
                    "matches_played_total": stats_data.get("matches_played_total", 0),
                    "wins_total": stats_data.get("wins_total", 0),
                    "draws_total": stats_data.get("draws_total", 0),
                    "losses_total": stats_data.get("losses_total", 0),
                    "goals_for_total": stats_data.get("goals_for_total", 0),
                    "goals_against_total": stats_data.get("goals_against_total", 0),
                    "clean_sheets_total": stats_data.get("clean_sheets_total", 0),
                    "form": stats_data.get("form", "")
                }
                
                stats_results["team_stats"] = formatted_stats
                
                # Récupérer les standings si disponibles
                standings = await SearchService.entity_attribute_search(
                    entity_type='standing',
                    attribute='team_id',
                    value=entity_id,
                    limit=5
                )
                
                if standings:
                    stats_results["standings"] = standings
            else:
                stats_results["message"] = "Aucune statistique trouvée pour cette équipe"
        
        elif entity_type == 'league':
            # Récupérer les standings de la ligue
            standings = await SearchService.entity_attribute_search(
                entity_type='standing',
                attribute='league_id',
                value=entity_id,
                limit=30
            )
            
            if standings:
                # Trier par rang
                sorted_standings = sorted(standings, key=lambda x: x.get("payload", {}).get("rank", 999))
                
                # Formater les standings
                formatted_standings = []
                for standing in sorted_standings:
                    payload = standing.get("payload", {})
                    
                    # Récupérer le nom de l'équipe
                    team_name = "Équipe inconnue"
                    team_id = payload.get("team_id")
                    if team_id:
                        from app.db.postgres.models import get_model_by_entity_type
                        from app.db.postgres.connection import get_db_session
                        
                        session = get_db_session()
                        try:
                            Team = get_model_by_entity_type('team')
                            team = session.query(Team).filter(Team.id == team_id).first()
                            if team:
                                team_name = team.name
                        except Exception as e:
                            logger.warning(f"Erreur lors de la récupération du nom de l'équipe: {str(e)}")
                        finally:
                            session.close()
                    
                    formatted_standing = {
                        "rank": payload.get("rank", 0),
                        "team_id": team_id,
                        "team_name": team_name,
                        "points": payload.get("points", 0),
                        "played": payload.get("played", 0),
                        "won": payload.get("won", 0),
                        "drawn": payload.get("drawn", 0),
                        "lost": payload.get("lost", 0),
                        "goals_for": payload.get("goals_for", 0),
                        "goals_against": payload.get("goals_against", 0),
                        "goal_diff": payload.get("goals_diff", 0)
                    }
                    
                    formatted_standings.append(formatted_standing)
                
                stats_results["standings"] = formatted_standings
            else:
                stats_results["message"] = "Aucun classement trouvé pour cette ligue"
        
        # Mettre en cache le résultat
        if use_cache:
            await cache_service.set(
                f"rag:stats:{entity_type}:{entity_id}:{stat_type or 'all'}", 
                stats_results, 
                ttl=settings.CACHE_TTL
            )
        
        return stats_results