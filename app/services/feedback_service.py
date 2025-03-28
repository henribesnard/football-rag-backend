"""Service pour la collecte et l'analyse des feedbacks utilisateurs."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from app.db.postgres.connection import get_db
from app.config import settings

logger = logging.getLogger(__name__)

class FeedbackService:
    """Service pour gérer les feedbacks des utilisateurs sur les réponses."""
    
    async def record_feedback(
        self,
        question_id: str,
        response_id: str,
        user_id: Optional[int],
        rating: int,
        comment: Optional[str] = None,
        feedback_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Enregistre le feedback d'un utilisateur.
        
        Args:
            question_id: ID unique de la question
            response_id: ID unique de la réponse
            user_id: ID de l'utilisateur (None si anonyme)
            rating: Note de 1 à 5
            comment: Commentaire optionnel
            feedback_type: Type de feedback (general, accuracy, helpfulness, etc.)
            
        Returns:
            Dictionnaire avec statut et message
        """
        if rating < 1 or rating > 5:
            return {"status": "error", "message": "La note doit être entre 1 et 5"}
        
        feedback_data = {
            "id": str(uuid.uuid4()),
            "question_id": question_id,
            "response_id": response_id,
            "user_id": user_id,
            "rating": rating,
            "comment": comment,
            "feedback_type": feedback_type,
            "created_at": datetime.now().isoformat()
        }
        
        with get_db() as db:
            try:
                # Insérer le feedback dans la base de données
                db.execute(
                    """
                    INSERT INTO user_feedback 
                    (id, question_id, response_id, user_id, rating, comment, feedback_type, created_at)
                    VALUES (:id, :question_id, :response_id, :user_id, :rating, :comment, :feedback_type, :created_at)
                    """,
                    feedback_data
                )
                
                # Si la note est basse, notifier l'équipe
                if rating <= 2:
                    await self._notify_low_rating(feedback_data)
                
                return {"status": "success", "message": "Feedback enregistré avec succès", "feedback_id": feedback_data["id"]}
            
            except Exception as e:
                logger.error(f"Erreur lors de l'enregistrement du feedback: {str(e)}")
                return {"status": "error", "message": f"Erreur lors de l'enregistrement du feedback: {str(e)}"}
    
    async def get_feedback_stats(self, period: str = "week") -> Dict[str, Any]:
        """
        Récupère les statistiques sur les feedbacks.
        
        Args:
            period: Période d'analyse (day, week, month, all)
            
        Returns:
            Statistiques sur les feedbacks
        """
        period_clause = ""
        if period == "day":
            period_clause = "WHERE created_at >= NOW() - INTERVAL '1 day'"
        elif period == "week":
            period_clause = "WHERE created_at >= NOW() - INTERVAL '7 days'"
        elif period == "month":
            period_clause = "WHERE created_at >= NOW() - INTERVAL '30 days'"
        
        with get_db() as db:
            try:
                # Récupérer les statistiques générales
                stats = db.execute(
                    f"""
                    SELECT 
                        COUNT(*) as total_feedbacks,
                        AVG(rating) as average_rating,
                        COUNT(*) FILTER (WHERE rating >= 4) as positive_count,
                        COUNT(*) FILTER (WHERE rating <= 2) as negative_count
                    FROM user_feedback
                    {period_clause}
                    """
                ).fetchone()
                
                # Récupérer la distribution des notes
                distribution = db.execute(
                    f"""
                    SELECT 
                        rating,
                        COUNT(*) as count
                    FROM user_feedback
                    {period_clause}
                    GROUP BY rating
                    ORDER BY rating
                    """
                ).fetchall()
                
                # Récupérer les commentaires récents négatifs
                negative_comments = db.execute(
                    f"""
                    SELECT 
                        id,
                        question_id,
                        rating,
                        comment,
                        created_at
                    FROM user_feedback
                    WHERE rating <= 2 AND comment IS NOT NULL {period_clause.replace('WHERE', 'AND') if period_clause else 'WHERE comment IS NOT NULL'}
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                ).fetchall()
                
                return {
                    "period": period,
                    "stats": dict(stats) if stats else {},
                    "distribution": [dict(row) for row in distribution],
                    "negative_comments": [dict(row) for row in negative_comments]
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des statistiques de feedback: {str(e)}")
                return {"status": "error", "message": str(e)}
    
    async def _notify_low_rating(self, feedback_data: Dict[str, Any]) -> None:
        """
        Notifie l'équipe en cas de feedback négatif.
        
        Args:
            feedback_data: Données du feedback
        """
        # Implémenter la notification (email, webhook, etc.)
        logger.warning(
            f"Feedback négatif (note: {feedback_data['rating']}) pour la question {feedback_data['question_id']}. "
            f"Commentaire: {feedback_data['comment'] or 'Aucun commentaire'}"
        )
        
        # Si un webhook est configuré, envoyer une notification
        if webhook_url := settings.get("LOW_RATING_WEBHOOK_URL"):
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        webhook_url,
                        json={
                            "type": "low_rating_alert",
                            "data": feedback_data
                        }
                    )
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de la notification de feedback négatif: {str(e)}")

# Instance singleton pour utilisation dans toute l'application
feedback_service = FeedbackService()