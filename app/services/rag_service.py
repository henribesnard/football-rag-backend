"""
Service RAG (Retrieval-Augmented Generation) pour répondre aux questions sur le football.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
from datetime import datetime

from app.services.search_service import SearchService
from app.embedding.vectorize import get_embedding_for_text

logger = logging.getLogger(__name__)

class RagService:
    """
    Service RAG pour répondre aux questions sur le football.
    """
    
    @staticmethod
    async def answer_question(
        question: str,
        max_context_items: int = 5,
        score_threshold: float = 0.7,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        Répond à une question en utilisant le RAG.
        
        Args:
            question: Question posée
            max_context_items: Nombre maximum d'éléments à inclure dans le contexte
            score_threshold: Seuil de score minimum pour les résultats de recherche
            use_reranking: Si True, utilise le reranking pour améliorer les résultats
            
        Returns:
            Réponse avec contexte et sources
        """
        if not question:
            return {"error": "La question ne peut pas être vide"}
        
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
        for entity_type, results in search_results.items():
            if isinstance(results, list):
                for result in results:
                    if 'payload' in result:
                        # Enrichir le résultat avec le type d'entité
                        result['entity_type'] = entity_type
                        consolidated_results.append(result)
        
        # 3. Reranking (si activé)
        if use_reranking and consolidated_results:
            reranked_results = await RagService._rerank_results(question, consolidated_results)
            # Limiter le nombre de résultats après reranking
            context_items = reranked_results[:max_context_items]
        else:
            # Trier par score de similarité et limiter
            consolidated_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            context_items = consolidated_results[:max_context_items]
        
        # 4. Construction du contexte
        context, sources = RagService._build_context_and_sources(context_items)
        
        # 5. Construction de la réponse
        answer = RagService._generate_answer(question, context)
        
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "context_items_count": len(context_items),
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    async def _rerank_results(
        question: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reranke les résultats de recherche en fonction de leur pertinence pour la question.
        
        Args:
            question: Question posée
            results: Résultats de la recherche sémantique
            
        Returns:
            Résultats reranked
        """
        # Note: Pour un reranking avancé, intégrer un modèle cross-encoder
        # Ici, nous utilisons une heuristique simplifiée basée sur le type d'entité et le contenu
        
        # 1. Identifier les mots clés de la question
        question_lower = question.lower()
        keywords = set(question_lower.split())
        
        # 2. Calcul d'un score de pertinence pour chaque résultat
        for result in results:
            relevance_score = result.get('score', 0)  # Score de similarité initial
            
            # Boosting en fonction du type d'entité (ajuster selon les besoins)
            entity_boosts = {
                'player': 1.2,      # Boost pour les joueurs
                'team': 1.1,        # Boost pour les équipes
                'fixture': 1.15,    # Boost pour les matchs
                'league': 1.05,     # Boost pour les ligues
                'coach': 1.1,       # Boost pour les entraîneurs
                'standing': 1.0,    # Pas de boost pour les classements
                'country': 0.9      # Légère pénalité pour les pays
            }
            
            entity_type = result.get('entity_type', '')
            entity_boost = entity_boosts.get(entity_type, 1.0)
            
            # Analyse du contenu pour correspondance avec les mots-clés
            payload = result.get('payload', {})
            content_text = ""
            
            # Extraire le texte du contenu
            if 'text_content' in payload:
                content_text = payload['text_content']
            elif 'name' in payload:
                content_text = payload['name']
            
            content_lower = content_text.lower()
            
            # Compter les occurrences de mots-clés
            keyword_count = sum(1 for keyword in keywords if keyword in content_lower)
            keyword_boost = 1 + (keyword_count * 0.05)  # +5% par mot-clé trouvé
            
            # Score final combiné
            final_score = relevance_score * entity_boost * keyword_boost
            
            # Mettre à jour le score dans le résultat
            result['reranked_score'] = final_score
        
        # 3. Trier les résultats par score de pertinence
        results.sort(key=lambda x: x.get('reranked_score', 0), reverse=True)
        
        return results
    
    @staticmethod
    def _build_context_and_sources(
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
                "relevance_score": item.get('score') or item.get('reranked_score', 0)
            }
            sources.append(source)
        
        # Fusion des textes de contexte
        full_context = "\n\n".join(context_texts)
        
        return full_context, sources
    
    @staticmethod
    def _generate_answer(question: str, context: str) -> str:
        """
        Génère une réponse à partir de la question et du contexte récupéré.
        
        Args:
            question: Question posée
            context: Contexte pour la génération de réponse
            
        Returns:
            Réponse générée
        """
        # Note: Dans une implémentation complète, cette méthode utiliserait un LLM.
        # Pour cette version, nous retournons une réponse formatée qui inclut le contexte.
        
        # Dans un système réel, vous intégreriez ici un appel à un LLM comme OpenAI, Claude, etc.
        # Exemple fictif:
        # response = openai.ChatCompletion.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "You are a football expert assistant..."},
        #         {"role": "user", "content": f"Question: {question}\n\nContext: {context}"}
        #     ]
        # )
        # return response.choices[0].message.content
        
        # Pour cette version simplifiée:
        answer = f"Voici les informations trouvées en réponse à votre question:\n\n"
        answer += "Basé sur les données disponibles, "
        
        # Analyser le contexte pour générer une réponse simple
        if "joueur" in question.lower() or "player" in question.lower():
            answer += "le joueur mentionné "
        elif "équipe" in question.lower() or "team" in question.lower():
            answer += "l'équipe mentionnée "
        elif "match" in question.lower() or "fixture" in question.lower():
            answer += "le match mentionné "
        else:
            answer += "les informations demandées "
        
        answer += "sont disponibles dans notre base de connaissances."
        
        # Ajouter un message sur l'utilisation d'un LLM dans un système réel
        answer += "\n\nNote: Dans une implémentation complète, cette réponse serait générée par un LLM en utilisant le contexte récupéré."
        
        return answer
    
    @staticmethod
    async def get_entity_details(
        entity_type: str,
        entity_id: int,
        include_related: bool = True
    ) -> Dict[str, Any]:
        """
        Récupère les détails d'une entité spécifique et les entités associées.
        
        Args:
            entity_type: Type d'entité
            entity_id: ID de l'entité
            include_related: Si True, inclut les entités liées
            
        Returns:
            Détails de l'entité et entités associées
        """
        from app.db.qdrant.client import get_qdrant_client
        from app.db.qdrant.collections import get_collection_name
        
        collection_name = get_collection_name(entity_type)
        client = get_qdrant_client()
        
        try:
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
            
            return result
            
        except Exception as e:
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
    async def analyze_football_content(
        content: str,
        identify_entities: bool = True,
        extract_facts: bool = True
    ) -> Dict[str, Any]:
        """
        Analyse un contenu textuel lié au football pour identifier les entités et extraire des faits.
        
        Args:
            content: Contenu textuel à analyser
            identify_entities: Si True, identifie les entités mentionnées
            extract_facts: Si True, extrait des faits du contenu
            
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
                        search_results = search_collection(
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
        
        # Extraire des faits (dans une version réelle, utiliser un LLM pour cette tâche)
        if extract_facts:
            # Simuler l'extraction de faits
            # Note: Dans une implémentation réelle, utiliser un LLM comme GPT pour cette tâche
            results["extracted_facts"] = [
                "Cette fonction simule l'extraction de faits.",
                "Dans une implémentation réelle, un LLM analyserait le contenu pour identifier les faits importants."
            ]
        
        return results
    
    @staticmethod
    async def get_football_stats(
        entity_type: str,
        entity_id: int,
        stat_type: str = None
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques liées au football pour une entité donnée.
        
        Args:
            entity_type: Type d'entité (team, player, league)
            entity_id: ID de l'entité
            stat_type: Type de statistique spécifique (optionnel)
            
        Returns:
            Statistiques formatées
        """
        # Vérifier les types d'entités supportés
        if entity_type not in ['team', 'player', 'league']:
            return {"error": f"Type d'entité non supporté pour les statistiques: {entity_type}"}
        
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
        
        return stats_results