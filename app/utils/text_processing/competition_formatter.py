"""
Fonctions pour formater les données relatives aux compétitions de football.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from .utils import format_date, format_percentage

def format_league_data(league: Any) -> str:
    """
    Crée une représentation textuelle riche d'une ligue pour l'embedding.
    
    Args:
        league: L'instance de la ligue
        
    Returns:
        Texte formaté de la ligue
    """
    # Récupération sécurisée des attributs relationnels
    country_name = league.country.name if hasattr(league, 'country') and league.country else 'N/A'
    
    # Type de compétition
    league_type_map = {
        'League': 'Championnat',
        'Cup': 'Coupe',
        'Other': 'Autre'
    }
    competition_type = league_type_map.get(league.type, league.type) if hasattr(league, 'type') else 'N/A'
    
    # Saisons disponibles
    seasons_info = ""
    if hasattr(league, 'seasons') and league.seasons:
        current_season = next((s for s in league.seasons if hasattr(s, 'is_current') and s.is_current), None)
        if current_season:
            current_year = current_season.year if hasattr(current_season, 'year') else 'N/A'
            seasons_info = f"\nSaison en cours: {current_year}"
    
    return f"""
Compétition: {league.name}
Type: {competition_type}
Pays: {country_name}{seasons_info}
"""

def format_league_display(league: Any, detail_level: str) -> Dict[str, Any]:
    """
    Formate une ligue pour l'affichage.
    
    Args:
        league: L'instance de la ligue
        detail_level: Niveau de détail ("minimal", "standard", "complet")
        
    Returns:
        Dictionnaire formaté pour l'affichage
    """
    # Attributs de base pour tous les niveaux
    result = {
        "name": league.name,
        "type": league.type if hasattr(league, "type") else None
    }
    
    # Niveau standard: ajouter plus d'informations
    if detail_level in ["standard", "complet"]:
        result.update({
            "country": getattr(league.country, "name", None) if hasattr(league, "country") else None,
            "logo_url": getattr(league, "logo_url", None)
        })
    
    # Niveau complet: ajouter les saisons et détails avancés
    if detail_level == "complet" and hasattr(league, "seasons"):
        seasons = []
        for season in league.seasons:
            if hasattr(season, "year") and hasattr(season, "start_date") and hasattr(season, "end_date"):
                season_info = {
                    "year": season.year,
                    "start_date": format_date(season.start_date),
                    "end_date": format_date(season.end_date),
                    "is_current": getattr(season, "is_current", False)
                }
                seasons.append(season_info)
        
        if seasons:
            result["seasons"] = seasons
    
    return result

def format_standing_data(standing: Any) -> str:
    """
    Crée une représentation textuelle riche d'un classement pour l'embedding.
    
    Args:
        standing: L'instance du classement
        
    Returns:
        Texte formaté du classement
    """
    # Récupération sécurisée des attributs relationnels
    team_name = standing.team.name if hasattr(standing, 'team') and standing.team else 'Équipe'
    
    # Information sur la ligue et la saison
    league_name = 'N/A'
    season_year = 'N/A'
    
    if hasattr(standing, 'season') and standing.season:
        season_year = standing.season.year if hasattr(standing.season, 'year') else 'N/A'
        if hasattr(standing.season, 'league') and standing.season.league:
            league_name = standing.season.league.name
    
    # Déterminer la tendance
    trend = "stable"
    if hasattr(standing, 'status'):
        trend = standing.status
    
    trend_map = {
        'up': 'En progression',
        'down': 'En régression',
        'same': 'Stable'
    }
    trend_desc = trend_map.get(trend, 'Tendance inconnue')
    
    # Analyser la forme récente
    form_desc = "N/A"
    if hasattr(standing, 'form') and standing.form:
        form = standing.form
        wins = form.count('W')
        draws = form.count('D')
        losses = form.count('L')
        
        form_translations = {'W': 'V', 'D': 'N', 'L': 'D'}
        translated_form = ''.join(form_translations.get(c, c) for c in form)
        
        if wins >= len(form) * 0.7:
            form_desc = f"Excellente ({translated_form})"
        elif wins > losses:
            form_desc = f"Bonne ({translated_form})"
        elif wins == losses:
            form_desc = f"Moyenne ({translated_form})"
        else:
            form_desc = f"Mauvaise ({translated_form})"
    
    return f"""
Classement de {team_name}
Compétition: {league_name} - Saison {season_year}
Position: {standing.rank}
Points: {standing.points}
Forme récente: {form_desc}
Tendance: {trend_desc}
Description: {standing.description or 'N/A'}

Statistiques:
- Matchs joués: {standing.played}
- Victoires: {standing.won} ({format_percentage(standing.won, standing.played)})
- Nuls: {standing.drawn} ({format_percentage(standing.drawn, standing.played)})
- Défaites: {standing.lost} ({format_percentage(standing.lost, standing.played)})
- Buts marqués: {standing.goals_for}
- Buts encaissés: {standing.goals_against}
- Différence de buts: {standing.goals_diff}

Statistiques à domicile:
- Matchs joués: {standing.home_played or 0}
- Victoires: {standing.home_won or 0} ({format_percentage(standing.home_won, standing.home_played)})
- Buts marqués: {standing.home_goals_for or 0}
- Buts encaissés: {standing.home_goals_against or 0}

Statistiques à l'extérieur:
- Matchs joués: {standing.away_played or 0}
- Victoires: {standing.away_won or 0} ({format_percentage(standing.away_won, standing.away_played)})
- Buts marqués: {standing.away_goals_for or 0}
- Buts encaissés: {standing.away_goals_against or 0}
"""

def format_standing_display(standing: Any, detail_level: str) -> Dict[str, Any]:
    """
    Formate un classement pour l'affichage.
    
    Args:
        standing: L'instance du classement
        detail_level: Niveau de détail ("minimal", "standard", "complet")
        
    Returns:
        Dictionnaire formaté pour l'affichage
    """
    # Attributs de base pour tous les niveaux
    result = {
        "rank": standing.rank,
        "team": getattr(standing.team, "name", None) if hasattr(standing, "team") else None,
        "points": standing.points,
        "played": standing.played
    }
    
    # Niveau standard: ajouter plus d'informations
    if detail_level in ["standard", "complet"]:
        result.update({
            "won": standing.won,
            "drawn": standing.drawn,
            "lost": standing.lost,
            "goals_for": standing.goals_for,
            "goals_against": standing.goals_against,
            "goals_diff": standing.goals_diff,
            "form": standing.form if hasattr(standing, "form") else None
        })
    
    # Niveau complet: ajouter les statistiques détaillées
    if detail_level == "complet":
        result.update({
            "home_played": getattr(standing, "home_played", None),
            "home_won": getattr(standing, "home_won", None),
            "home_drawn": getattr(standing, "home_drawn", None),
            "home_lost": getattr(standing, "home_lost", None),
            "home_goals_for": getattr(standing, "home_goals_for", None),
            "home_goals_against": getattr(standing, "home_goals_against", None),
            
            "away_played": getattr(standing, "away_played", None),
            "away_won": getattr(standing, "away_won", None),
            "away_drawn": getattr(standing, "away_drawn", None),
            "away_lost": getattr(standing, "away_lost", None),
            "away_goals_for": getattr(standing, "away_goals_for", None),
            "away_goals_against": getattr(standing, "away_goals_against", None),
            
            "status": getattr(standing, "status", None),
            "description": getattr(standing, "description", None)
        })
    
    return result

def describe_competition_format(league: Any) -> str:
    """
    Génère une description du format de la compétition.
    
    Args:
        league: Instance de la ligue
        
    Returns:
        Description textuelle du format de la compétition
    """
    league_name = league.name if hasattr(league, 'name') else "Compétition"
    league_type = league.type if hasattr(league, 'type') else None
    
    # Format de description selon le type de compétition
    description = f"Format de la compétition {league_name}\n\n"
    
    if league_type == "League":
        description += (
            "Format de championnat: les équipes s'affrontent en matchs aller-retour. "
            "Chaque équipe joue donc deux fois contre chaque adversaire (une fois à domicile, une fois à l'extérieur). "
            "Le classement est établi selon les points obtenus (3 pour une victoire, 1 pour un match nul, 0 pour une défaite). "
            "En cas d'égalité de points, les critères habituels sont la différence de buts, puis le nombre de buts marqués."
        )
        
        # Information sur la relégation/promotion si disponible
        # Normalement ces informations pourraient être extraites des metadata de la ligue
        # ou des descriptions des équipes dans le classement
        description += (
            "\n\nLes meilleures équipes en fin de saison peuvent se qualifier pour des compétitions internationales, "
            "tandis que les dernières peuvent être reléguées en division inférieure, "
            "selon les règles spécifiques à cette compétition."
        )
    
    elif league_type == "Cup":
        description += (
            "Format de coupe: compétition à élimination directe. "
            "Les équipes s'affrontent en un ou plusieurs matchs, et le vainqueur se qualifie pour le tour suivant. "
            "Le perdant est éliminé de la compétition. "
            "La compétition se poursuit jusqu'à la finale qui détermine le vainqueur du tournoi."
        )
    
    else:
        description += (
            "Cette compétition peut suivre un format spécifique, possiblement une combinaison "
            "de phase de groupes et de phase à élimination directe. Les détails exacts peuvent "
            "varier selon les règles spécifiques établies par l'organisateur."
        )
    
    return description