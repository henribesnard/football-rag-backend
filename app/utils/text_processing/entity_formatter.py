# app/utils/text_processing/entity_formatter.py
"""
Fonctions pour formater les différentes entités en représentations textuelles.
Ce module est le point d'entrée principal pour créer du texte riche à partir des modèles.
"""
from typing import Any, Dict, Optional, Union
from datetime import datetime, date

from .team_formatter import format_team_data
from .player_formatter import format_player_data
from .match_formatter import format_match_data
from .competition_formatter import format_league_data, format_standing_data
from .utils import format_date

def create_entity_text(entity: Any, entity_type: str) -> Optional[str]:
    """
    Crée une représentation textuelle riche d'une entité pour l'embedding.
    Cette fonction enrichit les entités avec du contexte pour améliorer la recherche sémantique.
    
    Args:
        entity: L'instance de l'entité
        entity_type: Le type d'entité (ex: 'country', 'team', etc.)
        
    Returns:
        Une chaîne de texte enrichie ou None si le type n'est pas pris en charge
    """
    # Redirection vers les fonctions spécialisées selon le type
    formatters = {
        'country': _format_country_text,
        'team': format_team_data,
        'player': format_player_data,
        'fixture': format_match_data,
        'league': format_league_data,
        'standing': format_standing_data,
        'coach': _format_coach_text,
        'venue': _format_venue_text,
        'season': _format_season_text,
    }
    
    formatter = formatters.get(entity_type)
    if formatter:
        return formatter(entity)
    
    # Cas générique pour les types non spécifiés
    return _format_generic_entity(entity, entity_type)

def format_entity_for_display(entity: Any, entity_type: str, detail_level: str = "standard") -> Dict[str, Any]:
    """
    Formate une entité en un dictionnaire structuré pour affichage dans une interface utilisateur.
    
    Args:
        entity: L'instance de l'entité
        entity_type: Le type d'entité
        detail_level: Niveau de détail ("minimal", "standard", "complet")
        
    Returns:
        Dictionnaire formaté pour l'affichage
    """
    # Création du dictionnaire de base avec les informations communes
    result = {
        "type": entity_type,
        "id": getattr(entity, "id", None),
    }
    
    # Ajout des attributs de base communs à la plupart des entités
    if hasattr(entity, "name"):
        result["name"] = entity.name
    if hasattr(entity, "update_at"):
        result["last_updated"] = entity.update_at.isoformat() if entity.update_at else None
    
    # Appel des fonctions spécialisées selon le type
    if entity_type == "country":
        result.update(_format_country_display(entity, detail_level))
    elif entity_type == "team":
        result.update(_format_team_display(entity, detail_level))
    elif entity_type == "player":
        result.update(_format_player_display(entity, detail_level))
    elif entity_type == "fixture":
        result.update(_format_fixture_display(entity, detail_level))
    elif entity_type == "league":
        result.update(_format_league_display(entity, detail_level))
    elif entity_type == "coach":
        result.update(_format_coach_display(entity, detail_level))
    elif entity_type == "venue":
        result.update(_format_venue_display(entity, detail_level))
    else:
        # Cas générique pour les types non spécifiés
        result.update(_format_generic_display(entity, detail_level))
    
    return result

def _format_country_text(country: Any) -> str:
    """
    Formate un pays en texte riche.
    
    Args:
        country: L'instance du pays
        
    Returns:
        Texte formaté du pays
    """
    return f"""
Pays: {country.name}
Code: {country.code or 'N/A'}
"""

def _format_venue_text(venue: Any) -> str:
    """
    Formate un stade en texte riche.
    
    Args:
        venue: L'instance du stade
        
    Returns:
        Texte formaté du stade
    """
    # Récupérer le nom du pays de manière sécurisée
    country_name = venue.country.name if hasattr(venue, 'country') and venue.country else 'N/A'
    
    return f"""
Stade: {venue.name}
Ville: {venue.city or 'N/A'}
Pays: {country_name}
Capacité: {venue.capacity or 'N/A'} spectateurs
Surface: {venue.surface or 'N/A'}
Adresse: {venue.address or 'N/A'}
"""

def _format_coach_text(coach: Any) -> str:
    """
    Formate un entraîneur en texte riche.
    
    Args:
        coach: L'instance de l'entraîneur
        
    Returns:
        Texte formaté de l'entraîneur
    """
    # Récupération sécurisée des attributs
    nationality_name = coach.nationality.name if hasattr(coach, 'nationality') and coach.nationality else 'N/A'
    team_name = coach.team.name if hasattr(coach, 'team') and coach.team else 'N/A'
    birth_date_str = coach.birth_date.strftime('%d/%m/%Y') if hasattr(coach, 'birth_date') and coach.birth_date else 'N/A'
    
    # Calcul de l'âge si la date de naissance est disponible
    age = 'N/A'
    if hasattr(coach, 'birth_date') and coach.birth_date:
        today = date.today()
        age = today.year - coach.birth_date.year - ((today.month, today.day) < (coach.birth_date.month, coach.birth_date.day))
    
    # Statistiques de carrière
    win_percentage = 0
    if hasattr(coach, 'career_matches') and coach.career_matches and coach.career_matches > 0:
        win_percentage = (coach.career_wins / coach.career_matches) * 100
    
    return f"""
Entraîneur: {coach.name}
Prénom: {coach.firstname or 'N/A'}
Nom: {coach.lastname or 'N/A'}
Date de naissance: {birth_date_str}
Âge: {age} ans
Nationalité: {nationality_name}
Équipe actuelle: {team_name}

Statistiques de carrière:
- Matchs dirigés: {coach.career_matches or 0}
- Victoires: {coach.career_wins or 0}
- Nuls: {coach.career_draws or 0}
- Défaites: {coach.career_losses or 0}
- Pourcentage de victoires: {win_percentage:.1f}%
"""

def _format_season_text(season: Any) -> str:
    """
    Formate une saison en texte riche.
    
    Args:
        season: L'instance de la saison
        
    Returns:
        Texte formaté de la saison
    """
    # Récupération sécurisée des attributs
    league_name = season.league.name if hasattr(season, 'league') and season.league else 'N/A'
    
    # Formatage des dates
    start_date = season.start_date.strftime('%d/%m/%Y') if hasattr(season, 'start_date') and season.start_date else 'N/A'
    end_date = season.end_date.strftime('%d/%m/%Y') if hasattr(season, 'end_date') and season.end_date else 'N/A'
    
    status = "En cours" if hasattr(season, 'is_current') and season.is_current else "Terminée"
    
    return f"""
Saison: {season.year} - {season.year + 1 if hasattr(season, 'year') else '?'}
Compétition: {league_name}
Période: {start_date} - {end_date}
Statut: {status}
"""

def _format_generic_entity(entity: Any, entity_type: str) -> str:
    """
    Formate une entité générique en texte.
    Fonction de secours pour les types d'entités non spécifiquement gérés.
    
    Args:
        entity: L'instance de l'entité
        entity_type: Le type de l'entité
        
    Returns:
        Texte formaté de l'entité
    """
    result = f"Type d'entité: {entity_type}\n"
    
    if hasattr(entity, 'name'):
        result += f"Nom: {entity.name}\n"
    
    if hasattr(entity, 'id'):
        result += f"ID: {entity.id}\n"
    
    # Ajouter d'autres attributs génériques si disponibles
    for attr_name in ['description', 'code', 'type', 'status']:
        if hasattr(entity, attr_name):
            value = getattr(entity, attr_name)
            if value is not None:
                result += f"{attr_name.capitalize()}: {value}\n"
    
    # Dates importantes si disponibles
    for date_attr in ['date', 'created_at', 'update_at', 'start_date', 'end_date']:
        if hasattr(entity, date_attr):
            date_value = getattr(entity, date_attr)
            if date_value and isinstance(date_value, (datetime, date)):
                formatted_date = date_value.strftime('%d/%m/%Y')
                result += f"{date_attr.replace('_', ' ').capitalize()}: {formatted_date}\n"
    
    return result

# Fonctions de formatage pour l'affichage (retournent des dictionnaires)

def _format_country_display(country: Any, detail_level: str) -> Dict[str, Any]:
    """Formate un pays pour l'affichage"""
    result = {
        "name": country.name,
        "code": country.code
    }
    
    if detail_level in ["standard", "complet"]:
        result["flag_url"] = getattr(country, "flag_url", None)
    
    return result

def _format_team_display(team: Any, detail_level: str) -> Dict[str, Any]:
    """Formate une équipe pour l'affichage"""
    # Déléguer à la fonction spécialisée dans team_formatter.py
    from .team_formatter import format_team_display
    return format_team_display(team, detail_level)

def _format_player_display(player: Any, detail_level: str) -> Dict[str, Any]:
    """Formate un joueur pour l'affichage"""
    # Déléguer à la fonction spécialisée dans player_formatter.py
    from .player_formatter import format_player_display
    return format_player_display(player, detail_level)

def _format_fixture_display(fixture: Any, detail_level: str) -> Dict[str, Any]:
    """Formate un match pour l'affichage"""
    # Déléguer à la fonction spécialisée dans match_formatter.py
    from .match_formatter import format_match_display
    return format_match_display(fixture, detail_level)

def _format_league_display(league: Any, detail_level: str) -> Dict[str, Any]:
    """Formate une ligue pour l'affichage"""
    # Déléguer à la fonction spécialisée dans competition_formatter.py
    from .competition_formatter import format_league_display
    return format_league_display(league, detail_level)

def _format_coach_display(coach: Any, detail_level: str) -> Dict[str, Any]:
    """Formate un entraîneur pour l'affichage"""
    result = {
        "name": coach.name,
        "firstname": coach.firstname,
        "lastname": coach.lastname,
    }
    
    if detail_level in ["standard", "complet"]:
        result.update({
            "nationality": getattr(coach.nationality, "name", None) if hasattr(coach, "nationality") else None,
            "team": getattr(coach.team, "name", None) if hasattr(coach, "team") else None,
            "birth_date": format_date(coach.birth_date) if hasattr(coach, "birth_date") else None,
            "photo_url": getattr(coach, "photo_url", None),
        })
    
    if detail_level == "complet":
        result.update({
            "career_matches": getattr(coach, "career_matches", 0),
            "career_wins": getattr(coach, "career_wins", 0),
            "career_draws": getattr(coach, "career_draws", 0),
            "career_losses": getattr(coach, "career_losses", 0),
            "win_percentage": round((coach.career_wins / coach.career_matches) * 100, 1) if hasattr(coach, "career_matches") and coach.career_matches > 0 else 0
        })
    
    return result

def _format_venue_display(venue: Any, detail_level: str) -> Dict[str, Any]:
    """Formate un stade pour l'affichage"""
    result = {
        "name": venue.name,
        "city": venue.city
    }
    
    if detail_level in ["standard", "complet"]:
        result.update({
            "country": getattr(venue.country, "name", None) if hasattr(venue, "country") else None,
            "capacity": getattr(venue, "capacity", None),
            "image_url": getattr(venue, "image_url", None)
        })
    
    if detail_level == "complet":
        result.update({
            "address": getattr(venue, "address", None),
            "surface": getattr(venue, "surface", None)
        })
    
    return result

def _format_generic_display(entity: Any, detail_level: str) -> Dict[str, Any]:
    """Formate une entité générique pour l'affichage"""
    result = {}
    
    # Attributs de base pour tous les niveaux de détail
    basic_attrs = ["name", "id", "code", "type"]
    for attr in basic_attrs:
        if hasattr(entity, attr):
            result[attr] = getattr(entity, attr)
    
    # Attributs supplémentaires pour les niveaux standard et complet
    if detail_level in ["standard", "complet"]:
        std_attrs = ["description", "status"]
        for attr in std_attrs:
            if hasattr(entity, attr):
                result[attr] = getattr(entity, attr)
        
        # Dates formatées
        for date_attr in ["date", "created_at", "update_at"]:
            if hasattr(entity, date_attr):
                date_value = getattr(entity, date_attr)
                if date_value:
                    result[date_attr] = format_date(date_value)
    
    # Tous les attributs restants pour le niveau complet
    if detail_level == "complet":
        # Ajouter tous les attributs non encore inclus
        for attr_name in dir(entity):
            # Ignorer les attributs privés, méthodes et attributs déjà inclus
            if not attr_name.startswith('_') and attr_name not in result and not callable(getattr(entity, attr_name)):
                attr_value = getattr(entity, attr_name)
                
                # Gestion spéciale pour les dates et les relations
                if isinstance(attr_value, (datetime, date)):
                    result[attr_name] = format_date(attr_value)
                elif attr_value is not None and not hasattr(attr_value, '__table__'):  # Éviter les objets SQLAlchemy liés
                    result[attr_name] = attr_value
    
    return result