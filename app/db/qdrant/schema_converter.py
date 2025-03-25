# app/db/qdrant/schema_converter.py
"""
Utilitaire pour convertir entre les modèles Django et les formats de données Qdrant.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app.models.database import Country, Venue, League, Team, Player, Fixture
from app.utils.text_processing import create_entity_text

def model_to_vector_payload(
    model_instance: Any,
    entity_type: str,
    vector: List[float]
) -> Dict[str, Any]:
    """
    Convertit une instance de modèle Django en format compatible avec Qdrant.
    
    Args:
        model_instance: Instance du modèle Django
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        vector: Vecteur d'embedding
    
    Returns:
        Dictionnaire formaté pour l'insertion dans Qdrant
    """
    # Identifiant et vecteur communs à tous les types
    result = {
        "id": model_instance.id,
        "vector": vector
    }
    
    # Construire le payload en fonction du type d'entité
    if entity_type == 'country':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "name": model_instance.name,
            "code": model_instance.code,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'venue':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "name": model_instance.name,
            "city": model_instance.city,
            "country_id": model_instance.country_id,
            "capacity": model_instance.capacity,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'league':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "name": model_instance.name,
            "type": model_instance.type,
            "country_id": model_instance.country_id,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'team':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "name": model_instance.name,
            "code": model_instance.code,
            "country_id": model_instance.country_id,
            "founded": model_instance.founded,
            "is_national": model_instance.is_national,
            "venue_id": model_instance.venue_id,
            "total_matches": model_instance.total_matches,
            "total_wins": model_instance.total_wins,
            "total_draws": model_instance.total_draws,
            "total_losses": model_instance.total_losses,
            "total_goals_scored": model_instance.total_goals_scored,
            "total_goals_conceded": model_instance.total_goals_conceded,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'player':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "name": model_instance.name,
            "firstname": model_instance.firstname,
            "lastname": model_instance.lastname,
            "birth_date": model_instance.birth_date.isoformat() if model_instance.birth_date else None,
            "nationality_id": model_instance.nationality_id,
            "height": model_instance.height,
            "weight": model_instance.weight,
            "team_id": model_instance.team_id,
            "position": model_instance.position,
            "number": model_instance.number,
            "injured": model_instance.injured,
            "season_goals": model_instance.season_goals,
            "season_assists": model_instance.season_assists,
            "season_yellow_cards": model_instance.season_yellow_cards,
            "season_red_cards": model_instance.season_red_cards,
            "total_appearances": model_instance.total_appearances,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'fixture':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "league_id": model_instance.league_id,
            "season_id": model_instance.season_id,
            "round": model_instance.round,
            "home_team_id": model_instance.home_team_id,
            "away_team_id": model_instance.away_team_id,
            "date": model_instance.date.isoformat(),
            "venue_id": model_instance.venue_id,
            "referee": model_instance.referee,
            "status_id": model_instance.status_id,
            "elapsed_time": model_instance.elapsed_time,
            "home_score": model_instance.home_score,
            "away_score": model_instance.away_score,
            "is_finished": model_instance.is_finished,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'coach':
        result["payload"] = {
            "id": model_instance.id,
            "external_id": model_instance.external_id,
            "name": model_instance.name,
            "firstname": model_instance.firstname,
            "lastname": model_instance.lastname,
            "nationality_id": model_instance.nationality_id,
            "birth_date": model_instance.birth_date.isoformat() if model_instance.birth_date else None,
            "team_id": model_instance.team_id,
            "career_matches": model_instance.career_matches,
            "career_wins": model_instance.career_wins,
            "career_draws": model_instance.career_draws,
            "career_losses": model_instance.career_losses,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'fixture_event':
        result["payload"] = {
            "id": model_instance.id,
            "fixture_id": model_instance.fixture_id,
            "time_elapsed": model_instance.time_elapsed,
            "event_type": model_instance.event_type,
            "detail": model_instance.detail,
            "player_id": model_instance.player_id,
            "assist_id": model_instance.assist_id,
            "team_id": model_instance.team_id,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'player_statistic':
        result["payload"] = {
            "id": model_instance.id,
            "player_id": model_instance.player_id,
            "fixture_id": model_instance.fixture_id,
            "team_id": model_instance.team_id,
            "minutes_played": model_instance.minutes_played,
            "goals": model_instance.goals,
            "assists": model_instance.assists,
            "shots_total": model_instance.shots_total,
            "shots_on_target": model_instance.shots_on_target,
            "passes": model_instance.passes,
            "key_passes": model_instance.key_passes,
            "pass_accuracy": float(model_instance.pass_accuracy) if model_instance.pass_accuracy else None,
            "rating": float(model_instance.rating) if model_instance.rating else None,
            "is_substitute": model_instance.is_substitute,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'standing':
        result["payload"] = {
            "id": model_instance.id,
            "season_id": model_instance.season_id,
            "team_id": model_instance.team_id,
            "rank": model_instance.rank,
            "points": model_instance.points,
            "goals_diff": model_instance.goals_diff,
            "form": model_instance.form,
            "played": model_instance.played,
            "won": model_instance.won,
            "drawn": model_instance.drawn,
            "lost": model_instance.lost,
            "goals_for": model_instance.goals_for,
            "goals_against": model_instance.goals_against,
            "update_at": model_instance.update_at.isoformat()
        }
    
    elif entity_type == 'team_statistic':
        result["payload"] = {
            "id": model_instance.id,
            "team_id": model_instance.team_id,
            "league_id": model_instance.league_id,
            "season_id": model_instance.season_id,
            "form": model_instance.form,
            "matches_played_total": model_instance.matches_played_total,
            "wins_total": model_instance.wins_total,
            "draws_total": model_instance.draws_total,
            "losses_total": model_instance.losses_total,
            "goals_for_total": model_instance.goals_for_total,
            "goals_against_total": model_instance.goals_against_total,
            "clean_sheets_total": model_instance.clean_sheets_total,
            "update_at": model_instance.update_at.isoformat()
        }
    
    # Ajouter du texte enrichi pour améliorer la recherche sémantique
    rich_text = create_entity_text(model_instance, entity_type)
    if rich_text:
        result["payload"]["text_content"] = rich_text
    
    return result

def get_entity_by_id(entity_type: str, entity_id: int) -> Optional[Any]:
    """
    Récupère une instance de modèle par son ID et type d'entité.
    
    Args:
        entity_type: Type d'entité (ex: 'country', 'team', etc.)
        entity_id: ID de l'entité
    
    Returns:
        Instance du modèle ou None si non trouvée
    """
    entity_models = {
        'country': Country,
        'venue': Venue,
        'league': League,
        'team': Team,
        'player': Player,
        'fixture': Fixture,
        # Ajouter les autres modèles au besoin
    }
    
    model_class = entity_models.get(entity_type)
    if not model_class:
        return None
    
    try:
        return model_class.objects.get(id=entity_id)
    except model_class.DoesNotExist:
        return None