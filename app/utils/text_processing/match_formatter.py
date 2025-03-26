"""
Fonctions pour formater les données relatives aux matchs de football.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from .utils import format_date, format_percentage, format_duration

def format_match_data(fixture: Any) -> str:
    """
    Crée une représentation textuelle riche d'un match pour l'embedding.
    
    Args:
        fixture: L'instance du match (fixture)
        
    Returns:
        Texte formaté du match
    """
    # Récupération sécurisée des attributs relationnels
    home_team_name = fixture.home_team.name if hasattr(fixture, 'home_team') and fixture.home_team else 'N/A'
    away_team_name = fixture.away_team.name if hasattr(fixture, 'away_team') and fixture.away_team else 'N/A'
    league_name = fixture.league.name if hasattr(fixture, 'league') and fixture.league else 'N/A'
    season_info = f"Saison {fixture.season.year}" if hasattr(fixture, 'season') and fixture.season and hasattr(fixture.season, 'year') else 'N/A'
    venue_name = fixture.venue.name if hasattr(fixture, 'venue') and fixture.venue else 'N/A'
    
    # Statut du match
    status_desc = fixture.status.long_description if hasattr(fixture, 'status') and fixture.status and hasattr(fixture.status, 'long_description') else 'N/A'
    
    # Formatage de la date
    match_date = "N/A"
    if hasattr(fixture, 'date') and fixture.date:
        match_date = fixture.date.strftime('%d/%m/%Y %H:%M')
    
    # Score
    score_text = "N/A"
    if hasattr(fixture, 'home_score') and hasattr(fixture, 'away_score') and fixture.home_score is not None and fixture.away_score is not None:
        score_text = f"{fixture.home_score} - {fixture.away_score}"
    
    # Temps écoulé pour les matchs en cours
    elapsed_text = ""
    if hasattr(fixture, 'elapsed_time') and fixture.elapsed_time is not None and fixture.status and hasattr(fixture.status, 'short_code'):
        if fixture.status.short_code in ['1H', '2H', 'ET', 'P']:
            elapsed_text = f" ({fixture.elapsed_time}')"
    
    # Déterminer le vainqueur
    winner_text = ""
    if hasattr(fixture, 'is_finished') and fixture.is_finished and hasattr(fixture, 'home_score') and hasattr(fixture, 'away_score') and fixture.home_score is not None and fixture.away_score is not None:
        if fixture.home_score > fixture.away_score:
            winner_text = f"\nVainqueur: {home_team_name}"
        elif fixture.away_score > fixture.home_score:
            winner_text = f"\nVainqueur: {away_team_name}"
        else:
            winner_text = "\nRésultat: Match nul"
    
    return f"""
Match: {home_team_name} vs {away_team_name}
Score: {score_text}{elapsed_text}
Compétition: {league_name} ({season_info})
Date: {match_date}
Stade: {venue_name}
Arbitre: {fixture.referee or 'N/A'}
Statut: {status_desc}{winner_text}
Round: {fixture.round or 'N/A'}
"""

def format_match_display(fixture: Any, detail_level: str) -> Dict[str, Any]:
    """
    Formate un match pour l'affichage.
    
    Args:
        fixture: L'instance du match
        detail_level: Niveau de détail ("minimal", "standard", "complet")
        
    Returns:
        Dictionnaire formaté pour l'affichage
    """
    # Récupération des noms d'équipes sécurisée
    home_team = getattr(fixture.home_team, "name", None) if hasattr(fixture, "home_team") else None
    away_team = getattr(fixture.away_team, "name", None) if hasattr(fixture, "away_team") else None
    
    # Attributs de base pour tous les niveaux
    result = {
        "home_team": home_team,
        "away_team": away_team,
        "date": format_date(fixture.date, include_time=True) if hasattr(fixture, "date") else None
    }
    
    # Ajouter le score si disponible
    if hasattr(fixture, "home_score") and hasattr(fixture, "away_score") and fixture.home_score is not None and fixture.away_score is not None:
        result["score"] = f"{fixture.home_score} - {fixture.away_score}"
        result["home_score"] = fixture.home_score
        result["away_score"] = fixture.away_score
    
    # Niveau standard: ajouter plus d'informations
    if detail_level in ["standard", "complet"]:
        result.update({
            "league": getattr(fixture.league, "name", None) if hasattr(fixture, "league") else None,
            "venue": getattr(fixture.venue, "name", None) if hasattr(fixture, "venue") else None,
            "status": getattr(fixture.status, "long_description", None) if hasattr(fixture, "status") else None,
            "round": getattr(fixture, "round", None),
            "is_finished": getattr(fixture, "is_finished", None)
        })
        
        # Temps écoulé pour les matchs en cours
        if hasattr(fixture, "elapsed_time") and fixture.elapsed_time:
            result["elapsed_time"] = fixture.elapsed_time
    
    # Niveau complet: ajouter les détails avancés
    if detail_level == "complet":
        result.update({
            "referee": getattr(fixture, "referee", None),
            "season": getattr(fixture.season, "year", None) if hasattr(fixture, "season") else None,
            "timezone": getattr(fixture, "timezone", "UTC")
        })
    
    return result

def format_match_events(events: List[Any]) -> str:
    """
    Formate les événements d'un match en texte descriptif chronologique.
    
    Args:
        events: Liste des événements du match
        
    Returns:
        Texte formaté des événements
    """
    if not events or len(events) == 0:
        return "Aucun événement enregistré pour ce match."
    
    # Trier les événements par temps
    sorted_events = sorted(events, key=lambda e: e.time_elapsed if hasattr(e, 'time_elapsed') else 0)
    
    # Mapper les types d'événements à des descriptions plus lisibles
    event_type_map = {
        'Goal': 'But',
        'Card': 'Carton',
        'Substitution': 'Remplacement',
        'VAR': 'Décision VAR',
        'Injury': 'Blessure',
        'Penalty': 'Penalty',
        'Missed Penalty': 'Penalty Manqué'
    }
    
    events_text = "Chronologie des événements du match:\n\n"
    
    for event in sorted_events:
        time = event.time_elapsed if hasattr(event, 'time_elapsed') else 0
        event_type = event_type_map.get(event.event_type, event.event_type) if hasattr(event, 'event_type') else 'Événement'
        
        # Récupérer les informations sur les joueurs
        player_name = event.player.name if hasattr(event, 'player') and event.player else 'Joueur inconnu'
        team_name = event.team.name if hasattr(event, 'team') and event.team else 'Équipe inconnue'
        
        # Informations supplémentaires selon le type d'événement
        event_detail = ""
        
        if hasattr(event, 'event_type'):
            if event.event_type == 'Goal':
                assist_name = event.assist.name if hasattr(event, 'assist') and event.assist else None
                assist_text = f" (Passe décisive: {assist_name})" if assist_name else ""
                event_detail = f"{player_name} ({team_name}){assist_text}"
                
                # Ajouter le type de but si disponible
                if hasattr(event, 'detail') and event.detail:
                    detail_map = {
                        'Normal Goal': '',
                        'Own Goal': 'Contre son camp',
                        'Penalty': 'Sur penalty',
                        'Header': 'De la tête',
                        'Free Kick': 'Sur coup franc'
                    }
                    detail_desc = detail_map.get(event.detail, event.detail)
                    if detail_desc:
                        event_detail += f" - {detail_desc}"
            
            elif event.event_type == 'Card':
                card_type = event.detail if hasattr(event, 'detail') else "Carton"
                event_detail = f"{card_type} - {player_name} ({team_name})"
            
            elif event.event_type == 'Substitution':
                # Pour les remplacements, on a besoin de plus d'informations
                # Normalement le joueur entrant est dans player et sortant dans assist
                player_in = player_name
                player_out = event.assist.name if hasattr(event, 'assist') and event.assist else 'Joueur inconnu'
                event_detail = f"{player_in} remplace {player_out} ({team_name})"
            
            else:
                # Cas générique pour les autres types d'événements
                event_detail = f"{player_name} ({team_name})"
                if hasattr(event, 'detail') and event.detail:
                    event_detail += f" - {event.detail}"
        
        # Ajouter les commentaires si disponibles
        comments = f" - {event.comments}" if hasattr(event, 'comments') and event.comments else ""
        
        events_text += f"{time}' - {event_type}: {event_detail}{comments}\n"
    
    return events_text

def describe_match_context(fixture: Any, h2h_matches: List[Any] = None) -> str:
    """
    Fournit un contexte riche autour d'un match, incluant l'historique des confrontations.
    
    Args:
        fixture: Instance du match
        h2h_matches: Liste des confrontations directes précédentes
        
    Returns:
        Description contextuelle du match
    """
    context_text = ""
    
    # Récupération des noms d'équipes
    home_team_name = fixture.home_team.name if hasattr(fixture, 'home_team') and fixture.home_team else 'Équipe domicile'
    away_team_name = fixture.away_team.name if hasattr(fixture, 'away_team') and fixture.away_team else 'Équipe extérieur'
    
    # Importance du match
    league_name = fixture.league.name if hasattr(fixture, 'league') and fixture.league else 'Compétition'
    
    # Déterminer si le match est à venir, en cours ou terminé
    match_date = fixture.date if hasattr(fixture, 'date') and fixture.date else None
    is_finished = hasattr(fixture, 'is_finished') and fixture.is_finished
    
    if match_date and match_date > datetime.now():
        time_until = match_date - datetime.now()
        days_until = time_until.days
        
        if days_until > 7:
            timing_desc = f"Ce match aura lieu dans {days_until} jours"
        elif days_until > 0:
            timing_desc = f"Ce match aura lieu dans {days_until} jour(s)"
        elif time_until.seconds > 3600:
            hours_until = time_until.seconds // 3600
            timing_desc = f"Ce match aura lieu dans {hours_until} heure(s)"
        else:
            minutes_until = time_until.seconds // 60
            timing_desc = f"Ce match aura lieu dans {minutes_until} minute(s)"
    elif is_finished:
        timing_desc = "Ce match est terminé"
    else:
        timing_desc = "Ce match est en cours ou sa date n'est pas spécifiée"
    
    context_text += f"Match: {home_team_name} vs {away_team_name}\n"
    context_text += f"Compétition: {league_name}\n"
    context_text += f"{timing_desc}\n\n"
    
    # Historique des confrontations directes
    if h2h_matches and len(h2h_matches) > 0:
        home_wins = 0
        away_wins = 0
        draws = 0
        
        context_text += f"Historique des confrontations directes ({len(h2h_matches)} matchs):\n"
        
        for h2h in sorted(h2h_matches, key=lambda m: m.date if hasattr(m, 'date') else datetime.min, reverse=True):
            h2h_date = h2h.date.strftime('%d/%m/%Y') if hasattr(h2h, 'date') and h2h.date else 'Date inconnue'
            h2h_home = h2h.home_team.name if hasattr(h2h, 'home_team') and h2h.home_team else 'Équipe domicile'
            h2h_away = h2h.away_team.name if hasattr(h2h, 'away_team') and h2h.away_team else 'Équipe extérieur'
            
            # Score
            h2h_score = "Score inconnu"
            if hasattr(h2h, 'home_score') and hasattr(h2h, 'away_score') and h2h.home_score is not None and h2h.away_score is not None:
                h2h_score = f"{h2h.home_score} - {h2h.away_score}"
                
                # Comptabiliser pour les statistiques
                if h2h_home == home_team_name:
                    if h2h.home_score > h2h.away_score:
                        home_wins += 1
                    elif h2h.home_score < h2h.away_score:
                        away_wins += 1
                    else:
                        draws += 1
                else:  # Si l'équipe à domicile du match h2h est l'équipe à l'extérieur du match actuel
                    if h2h.home_score > h2h.away_score:
                        away_wins += 1
                    elif h2h.home_score < h2h.away_score:
                        home_wins += 1
                    else:
                        draws += 1
            
            context_text += f"- {h2h_date}: {h2h_home} {h2h_score} {h2h_away}\n"
        
        # Résumé des statistiques
        # Résumé des statistiques
        total_matches = home_wins + away_wins + draws
        if total_matches > 0:
            context_text += f"\nRésumé des confrontations: {home_team_name} a remporté {home_wins} match(s) ({format_percentage(home_wins, total_matches)}), "
            context_text += f"{away_team_name} a remporté {away_wins} match(s) ({format_percentage(away_wins, total_matches)}), "
            context_text += f"et {draws} match(s) se sont soldés par un nul ({format_percentage(draws, total_matches)}).\n"
    else:
        context_text += "Aucun historique de confrontation directe n'est disponible.\n"
    
    # Forme récente des équipes (à implémenter si les données sont disponibles)
    # Cela nécessiterait d'avoir accès aux statistiques des équipes
    
    return context_text