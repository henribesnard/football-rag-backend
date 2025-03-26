"""
Fonctions pour formater les données relatives aux équipes de football.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from .utils import format_date, format_percentage

def format_team_data(team: Any) -> str:
    """
    Crée une représentation textuelle riche d'une équipe pour l'embedding.
    
    Args:
        team: L'instance de l'équipe
        
    Returns:
        Texte formaté de l'équipe
    """
    # Récupération sécurisée des attributs relationnels
    country_name = team.country.name if hasattr(team, 'country') and team.country else 'N/A'
    venue_name = team.venue.name if hasattr(team, 'venue') and team.venue else 'N/A'
    coach_name = None
    
    if hasattr(team, 'current_coach') and team.current_coach:
        coach_name = team.current_coach.name
    
    # Calculs de statistiques
    win_rate = 0
    if hasattr(team, 'total_matches') and team.total_matches and team.total_matches > 0:
        win_rate = (team.total_wins / team.total_matches) * 100
    
    avg_goals_scored = 0
    if hasattr(team, 'total_matches') and team.total_matches and team.total_matches > 0:
        avg_goals_scored = team.total_goals_scored / team.total_matches
    
    avg_goals_conceded = 0
    if hasattr(team, 'total_matches') and team.total_matches and team.total_matches > 0:
        avg_goals_conceded = team.total_goals_conceded / team.total_matches
    
    team_type = "Équipe nationale" if hasattr(team, 'is_national') and team.is_national else "Club"
    
    return f"""
Équipe: {team.name}
Type: {team_type}
Code: {team.code or 'N/A'}
Pays: {country_name}
Stade: {venue_name}
Entraîneur: {coach_name or 'N/A'}
Fondée en: {team.founded or 'N/A'}

Statistiques globales:
- Matchs joués: {team.total_matches or 0}
- Victoires: {team.total_wins or 0} ({win_rate:.1f}%)
- Nuls: {team.total_draws or 0} ({format_percentage(team.total_draws, team.total_matches)})
- Défaites: {team.total_losses or 0} ({format_percentage(team.total_losses, team.total_matches)})
- Buts marqués: {team.total_goals_scored or 0} (moy. {avg_goals_scored:.2f} par match)
- Buts encaissés: {team.total_goals_conceded or 0} (moy. {avg_goals_conceded:.2f} par match)
- Différence de buts: {(team.total_goals_scored or 0) - (team.total_goals_conceded or 0)}
"""

def format_team_display(team: Any, detail_level: str) -> Dict[str, Any]:
    """
    Formate une équipe pour l'affichage.
    
    Args:
        team: L'instance de l'équipe
        detail_level: Niveau de détail ("minimal", "standard", "complet")
        
    Returns:
        Dictionnaire formaté pour l'affichage
    """
    # Attributs de base pour tous les niveaux
    result = {
        "name": team.name,
        "code": team.code
    }
    
    # Niveau standard: ajouter plus d'informations
    if detail_level in ["standard", "complet"]:
        result.update({
            "country": getattr(team.country, "name", None) if hasattr(team, "country") else None,
            "founded": getattr(team, "founded", None),
            "is_national": getattr(team, "is_national", False),
            "logo_url": getattr(team, "logo_url", None),
            "venue": getattr(team.venue, "name", None) if hasattr(team, "venue") else None,
        })
    
    # Niveau complet: ajouter les statistiques et détails
    if detail_level == "complet":
        # Statistiques
        total_matches = getattr(team, "total_matches", 0)
        total_wins = getattr(team, "total_wins", 0)
        
        result.update({
            "total_matches": total_matches,
            "total_wins": total_wins,
            "total_draws": getattr(team, "total_draws", 0),
            "total_losses": getattr(team, "total_losses", 0),
            "total_goals_scored": getattr(team, "total_goals_scored", 0),
            "total_goals_conceded": getattr(team, "total_goals_conceded", 0),
            "win_rate": round((total_wins / total_matches) * 100, 1) if total_matches > 0 else 0,
            "coach": getattr(team.current_coach, "name", None) if hasattr(team, "current_coach") else None
        })
    
    return result

def describe_team_form(form_string: str) -> str:
    """
    Décrit la forme récente d'une équipe à partir de la chaîne de forme.
    
    Args:
        form_string: Chaîne de caractères représentant la forme récente (ex: "WDLWW")
        
    Returns:
        Description textuelle de la forme
    """
    if not form_string:
        return "Forme récente inconnue"
    
    # Traduction des codes
    form_map = {
        'W': 'Victoire',
        'D': 'Nul',
        'L': 'Défaite'
    }
    
    # Compter les résultats
    wins = form_string.count('W')
    draws = form_string.count('D')
    losses = form_string.count('L')
    total = len(form_string)
    
    # Traduire la chaîne
    translated_form = " - ".join([form_map.get(c, '?') for c in form_string])
    
    # Analyser la tendance
    trend_desc = ""
    
    if wins >= total * 0.7:
        trend_desc = "Excellente forme"
    elif wins > losses:
        trend_desc = "Bonne forme"
    elif wins == losses:
        trend_desc = "Forme moyenne"
    elif losses >= total * 0.7:
        trend_desc = "Mauvaise forme"
    else:
        trend_desc = "Forme irrégulière"
    
    # Progression
    progression = ""
    if len(form_string) >= 3:
        recent = form_string[:3]
        older = form_string[3:] if len(form_string) > 3 else ""
        
        recent_wins = recent.count('W')
        older_wins = older.count('W') if older else 0
        
        recent_points = recent_wins * 3 + recent.count('D')
        older_points = older_wins * 3 + older.count('D') if older else 0
        
        if recent_points > older_points:
            progression = "en progression"
        elif recent_points < older_points:
            progression = "en régression"
        else:
            progression = "stable"
    
    return f"{trend_desc}, {progression}. 5 derniers matchs: {translated_form}. {wins} victoires, {draws} nuls, {losses} défaites."

def format_team_statistics(team_stats: Any) -> str:
    """
    Formate les statistiques d'une équipe en texte descriptif.
    
    Args:
        team_stats: Instance de statistiques d'équipe
        
    Returns:
        Texte formaté des statistiques
    """
    team_name = team_stats.team.name if hasattr(team_stats, 'team') and team_stats.team else 'Équipe'
    league_name = team_stats.league.name if hasattr(team_stats, 'league') and team_stats.league else 'Compétition'
    season = f"Saison {team_stats.season.year}" if hasattr(team_stats, 'season') and team_stats.season and hasattr(team_stats.season, 'year') else 'Saison en cours'
    
    form_desc = describe_team_form(team_stats.form) if hasattr(team_stats, 'form') and team_stats.form else "Forme récente non disponible"
    
    # Domicile vs Extérieur
    home_win_rate = 0
    if hasattr(team_stats, 'matches_played_home') and team_stats.matches_played_home > 0:
        home_win_rate = (team_stats.wins_home / team_stats.matches_played_home) * 100
    
    away_win_rate = 0
    if hasattr(team_stats, 'matches_played_away') and team_stats.matches_played_away > 0:
        away_win_rate = (team_stats.wins_away / team_stats.matches_played_away) * 100
    
    return f"""
Statistiques de {team_name} - {league_name} - {season}

Forme récente: {form_desc}

Performances globales:
- Matchs joués: {team_stats.matches_played_total or 0}
- Victoires: {team_stats.wins_total or 0} ({format_percentage(team_stats.wins_total, team_stats.matches_played_total)})
- Nuls: {team_stats.draws_total or 0} ({format_percentage(team_stats.draws_total, team_stats.matches_played_total)})
- Défaites: {team_stats.losses_total or 0} ({format_percentage(team_stats.losses_total, team_stats.matches_played_total)})
- Buts marqués: {team_stats.goals_for_total or 0} (moy. {team_stats.goals_for_average_total or 0} par match)
- Buts encaissés: {team_stats.goals_against_total or 0} (moy. {team_stats.goals_against_average_total or 0} par match)
- Clean sheets: {team_stats.clean_sheets_total or 0}

Performances à domicile:
- Matchs joués: {team_stats.matches_played_home or 0}
- Victoires: {team_stats.wins_home or 0} ({home_win_rate:.1f}%)
- Buts marqués: {team_stats.goals_for_home or 0}
- Buts encaissés: {team_stats.goals_against_home or 0}

Performances à l'extérieur:
- Matchs joués: {team_stats.matches_played_away or 0}
- Victoires: {team_stats.wins_away or 0} ({away_win_rate:.1f}%)
- Buts marqués: {team_stats.goals_for_away or 0}
- Buts encaissés: {team_stats.goals_against_away or 0}

Résultats notables:
- Plus large victoire à domicile: {team_stats.biggest_win_home or 'N/A'}
- Plus large victoire à l'extérieur: {team_stats.biggest_win_away or 'N/A'}
- Plus large défaite à domicile: {team_stats.biggest_loss_home or 'N/A'}
- Plus large défaite à l'extérieur: {team_stats.biggest_loss_away or 'N/A'}
"""