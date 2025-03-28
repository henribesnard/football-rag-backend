"""Service de reranking spécifique au domaine du football."""
import logging
import asyncio
from typing import List, Dict, Any, Tuple

import numpy as np

from app.config import settings
from app.utils.circuit_breaker import circuit

logger = logging.getLogger(__name__)

class RerankingService:
    """Service pour le reranking des résultats de recherche."""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.enabled = settings.get("ENABLE_RERANKING", True)
        
        # Tenter de charger le modèle de reranking
        if self.enabled:
            asyncio.create_task(self._load_model())
    
    async def _load_model(self) -> None:
        """Charge le modèle de reranking."""
        try:
            from sentence_transformers import CrossEncoder
            
            model_name = settings.get("RERANKING_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            self.model = CrossEncoder(model_name)
            self.model_loaded = True
            
            logger.info(f"Modèle de reranking chargé avec succès: {model_name}")
        except ImportError:
            logger.error("Package 'sentence-transformers' non installé. Exécutez 'pip install sentence-transformers'")
            self.enabled = False
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle de reranking: {str(e)}")
            self.enabled = False
    
    @circuit(name="reranking", failure_threshold=3, recovery_timeout=30)
    async def rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Reranke les résultats de recherche en fonction de leur pertinence pour la question.
        
        Args:
            query: Question posée
            results: Résultats de la recherche sémantique
            max_results: Nombre maximum de résultats à retourner
            
        Returns:
            Résultats reranked
        """
        if not self.enabled or not self.model_loaded or not results:
            # Si le reranking est désactivé ou le modèle non chargé, retourner les résultats d'origine
            logger.debug("Reranking non disponible, utilisation des scores d'origine")
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:max_results]
        
        try:
            # Préparer les paires pour le reranking
            pairs = []
            payload_texts = []
            
            for idx, result in enumerate(results):
                payload = result.get("payload", {})
                
                # Extraire le texte du contenu
                if "text_content" in payload:
                    text = payload["text_content"]
                elif "name" in payload:
                    text = payload["name"]
                else:
                    text = str(payload)
                
                # Limiter la taille du texte pour éviter les problèmes
                text = text[:2000]
                pairs.append([query, text])
                payload_texts.append((idx, text))
            
            # Exécuter le reranking
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, lambda: self.model.predict(pairs))
            
            # Ajouter les scores aux résultats
            for i, score in enumerate(scores):
                if i < len(results):
                    results[i]["rerank_score"] = float(score)
            
            # Trier par score de reranking
            reranked_results = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
            
            # Football-specific boosts
            reranked_results = self._apply_domain_boosts(query, reranked_results)
            
            return reranked_results[:max_results]
            
        except Exception as e:
            logger.error(f"Erreur lors du reranking: {str(e)}")
            # En cas d'erreur, revenir aux scores d'origine
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:max_results]
    
    def _apply_domain_boosts(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applique des boosts spécifiques au domaine du football.
        
        Args:
            query: Question posée
            results: Résultats reranked
            
        Returns:
            Résultats avec boosts appliqués
        """
        query_lower = query.lower()
        
        # Mots-clés par catégorie
        player_keywords = {"joueur", "buteur", "gardien", "défenseur", "milieu", "attaquant", "capitaine", "carrière"}
        team_keywords = {"équipe", "club", "sélection", "formation", "effectif"}
        match_keywords = {"match", "rencontre", "confrontation", "derby", "classique"}
        competition_keywords = {"compétition", "ligue", "championnat", "coupe", "trophée", "tournoi"}
        stat_keywords = {"statistique", "stats", "buts", "passes", "cartons", "classement"}
        
        # Vérifier les correspondances
        has_player_keywords = any(kw in query_lower for kw in player_keywords)
        has_team_keywords = any(kw in query_lower for kw in team_keywords)
        has_match_keywords = any(kw in query_lower for kw in match_keywords)
        has_competition_keywords = any(kw in query_lower for kw in competition_keywords)
        has_stat_keywords = any(kw in query_lower for kw in stat_keywords)
        
        # Appliquer des boosts basés sur le type d'entité et les mots-clés
        for result in results:
            score = result.get("rerank_score", result.get("score", 0))
            entity_type = result.get("entity_type", "")
            
            # Boosts basés sur le type d'entité et les mots-clés
            if entity_type == "player" and has_player_keywords:
                score *= 1.2
            elif entity_type == "team" and has_team_keywords:
                score *= 1.15
            elif entity_type == "fixture" and has_match_keywords:
                score *= 1.2
            elif entity_type == "league" and has_competition_keywords:
                score *= 1.15
            elif (entity_type == "standing" or entity_type == "team_statistics") and has_stat_keywords:
                score *= 1.25
            
            # Récence (si disponible)
            payload = result.get("payload", {})
            if "update_at" in payload:
                try:
                    import datetime
                    from dateutil import parser
                    
                    update_date = parser.parse(payload["update_at"])
                    now = datetime.datetime.now()
                    days_diff = (now - update_date).days
                    
                    # Boost pour les données récentes
                    if days_diff < 7:  # Moins d'une semaine
                        score *= 1.1
                except Exception:
                    pass
            
            # Mettre à jour le score
            result["boosted_score"] = score
        
        # Trier par score boosté
        return sorted(results, key=lambda x: x.get("boosted_score", 0), reverse=True)

# Instance singleton pour utilisation dans toute l'application
reranking_service = RerankingService()