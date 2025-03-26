"""
Fonctions pour formater les données relatives aux joueurs de football.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from .utils import format_date, format_percentage, format_duration, get_age_from_birthdate

def format_player_data(player: Any) -> str:
    """
    Crée une représentation textuelle riche d'un joueur pour l'embedding.
    
    Args:
        player: L'instance du joueur
        
    Returns:
        Texte formaté du joueur
    """
    # Récupération sécurisée des attributs relationnels
    nationality_name = player.nationality.name if hasattr(player, 'nationality') and player.nationality else 'N/A'
    team_name = player.team.name if hasattr(player, 'team') and player.team else 'N/A'
    
    # Formatage de la date de naissance et calcul de l'âge
    birth_date_str = player.birth_date.strftime('%d/%m/%Y') if hasattr(player, 'birth_date') and player.birth_date else 'N/A'
    age = get_age_from_birthdate(player.birth_date) if hasattr(player, 'birth_date') and player.birth_date else 'N/A'
    
    # Conversion de la position en format plus lisible
    position_map = {
        'GK': 'Gardien de but',
        'DF': 'Défenseur',
        'MF': 'Milieu de terrain',
        'FW': 'Attaquant'
    }
    position = position_map.get(player.position, player.position) if hasattr(player, 'position') else 'N/A'
    
    # Caractéristiques physiques
    height_str = f"{player.height} cm" if hasattr(player, 'height') and player.height else 'N/A'
    weight_str = f"{player.weight} kg" if hasattr(player, 'weight') and player.weight else 'N/A'
    
    # Statut d'injury
    injury_status = "Blessé" if hasattr(player, 'injured') and player.injured else "En forme"
    
    return f"""
Joueur: {player.name}
Prénom: {player.firstname or 'N/A'}
Nom: {player.lastname or 'N/A'}
Date de naissance: {birth_date_str}
Âge: {age}
Nationalité: {nationality_name}
Équipe actuelle: {team_name}
Position: {position}
Numéro: {player.number or 'N/A'}
Taille: {height_str}
Poids: {weight_str}
Statut: {injury_status}

Statistiques saison en cours:
- Buts: {player.season_goals or 0}
- Passes décisives: {player.season_assists or 0}
- Cartons jaunes: {player.season_yellow_cards or 0}
- Cartons rouges: {player.season_red_cards or 0}
- Apparitions: {player.total_appearances or 0}
"""

def format_player_display(player: Any, detail_level: str) -> Dict[str, Any]:
    """
    Formate un joueur pour l'affichage.
    
    Args:
        player: L'instance du joueur
        detail_level: Niveau de détail ("minimal", "standard", "complet")
        
    Returns:
        Dictionnaire formaté pour l'affichage
    """
    # Attributs de base pour tous les niveaux
    result = {
        "name": player.name,
        "position": player.position
    }
    
    # Niveau standard: ajouter plus d'informations
    if detail_level in ["standard", "complet"]:
        result.update({
            "firstname": getattr(player, "firstname", None),
            "lastname": getattr(player, "lastname", None),
            "nationality": getattr(player.nationality, "name", None) if hasattr(player, "nationality") else None,
            "team": getattr(player.team, "name", None) if hasattr(player, "team") else None,
            "number": getattr(player, "number", None),
            "age": get_age_from_birthdate(player.birth_date) if hasattr(player, "birth_date") and player.birth_date else None,
            "photo_url": getattr(player, "photo_url", None),
            "injured": getattr(player, "injured", False)
        })
    
    # Niveau complet: ajouter les statistiques et détails
    if detail_level == "complet":
        result.update({
            "birth_date": format_date(player.birth_date) if hasattr(player, "birth_date") else None,
            "height": getattr(player, "height", None),
            "weight": getattr(player, "weight", None),
            "season_goals": getattr(player, "season_goals", 0),
            "season_assists": getattr(player, "season_assists", 0),
            "season_yellow_cards": getattr(player, "season_yellow_cards", 0),
            "season_red_cards": getattr(player, "season_red_cards", 0),
            "total_appearances": getattr(player, "total_appearances", 0)
        })
    
    return result

def format_player_statistics(player_stats: Any) -> str:
    """
    Formate les statistiques d'un joueur en texte descriptif.
    
    Args:
        player_stats: Instance de statistiques d'un joueur
        
    Returns:
        Texte formaté des statistiques
    """
    # Récupération des références
    player_name = player_stats.player.name if hasattr(player_stats, 'player') and player_stats.player else 'Joueur'
    team_name = player_stats.team.name if hasattr(player_stats, 'team') and player_stats.team else 'Équipe'
    match_info = ""
    
    if hasattr(player_stats, 'fixture') and player_stats.fixture:
        fixture = player_stats.fixture
        match_date = fixture.date.strftime('%d/%m/%Y') if hasattr(fixture, 'date') and fixture.date else 'Date inconnue'
        
        home_team_name = fixture.home_team.name if hasattr(fixture, 'home_team') and fixture.home_team else 'Équipe domicile'
        away_team_name = fixture.away_team.name if hasattr(fixture, 'away_team') and fixture.away_team else 'Équipe extérieur'
        
        score = f"{fixture.home_score} - {fixture.away_score}" if hasattr(fixture, 'home_score') and hasattr(fixture, 'away_score') else 'Score inconnu'
        
        match_info = f"{home_team_name} vs {away_team_name} ({score}), {match_date}"
    
    # Statut dans le match
    status = "Titulaire"
    if hasattr(player_stats, 'is_substitute') and player_stats.is_substitute:
        status = "Remplaçant"
    
    captain_info = ", Capitaine" if hasattr(player_stats, 'is_captain') and player_stats.is_captain else ""
    
    # Temps de jeu
    minutes_played = player_stats.minutes_played if hasattr(player_stats, 'minutes_played') else 0
    minutes_info = format_duration(minutes_played) if minutes_played else "N/A"
    
    # Statistiques offensives
    shots_accuracy = "N/A"
    if hasattr(player_stats, 'shots_total') and player_stats.shots_total > 0 and hasattr(player_stats, 'shots_on_target'):
        shots_accuracy = f"{(player_stats.shots_on_target / player_stats.shots_total) * 100:.1f}%"
    
    pass_accuracy = "N/A"
    if hasattr(player_stats, 'pass_accuracy'):
        pass_accuracy = f"{player_stats.pass_accuracy:.1f}%" if player_stats.pass_accuracy else "N/A"
    
    # Note de performance
    rating_info = ""
    if hasattr(player_stats, 'rating') and player_stats.rating:
        rating = player_stats.rating
        rating_desc = "Excellente" if rating >= 8.0 else "Bonne" if rating >= 7.0 else "Moyenne" if rating >= 6.0 else "Médiocre"
        rating_info = f"\nNote de performance: {rating}/10 ({rating_desc})"
    
    return f"""
Statistiques de {player_name} ({team_name})
Match: {match_info}
Statut: {status}{captain_info}
Temps de jeu: {minutes_info}

Performance offensive:
- Buts: {getattr(player_stats, 'goals', 0)}
- Passes décisives: {getattr(player_stats, 'assists', 0)}
- Tirs: {getattr(player_stats, 'shots_total', 0)} (Cadrés: {getattr(player_stats, 'shots_on_target', 0)}, Précision: {shots_accuracy})

Passes:
- Passes totales: {getattr(player_stats, 'passes', 0)}
- Passes clés: {getattr(player_stats, 'key_passes', 0)}
- Précision des passes: {pass_accuracy}

Défense:
- Tacles: {getattr(player_stats, 'tackles', 0)}
- Interceptions: {getattr(player_stats, 'interceptions', 0)}

Discipline:
- Fautes commises: {getattr(player_stats, 'fouls_committed', 0)}
- Fautes subies: {getattr(player_stats, 'fouls_drawn', 0)}
- Cartons jaunes: {getattr(player_stats, 'yellow_cards', 0)}
- Cartons rouges: {getattr(player_stats, 'red_cards', 0)}
{rating_info}
"""

def describe_player_career(player: Any, transfers: List[Any] = None, team_history: List[Any] = None) -> str:
    """
    Décrit la carrière d'un joueur en se basant sur son historique de transferts et d'équipes.
    
    Args:
        player: Instance du joueur
        transfers: Liste de transferts
        team_history: Historique des équipes
        
    Returns:
        Description textuelle de la carrière
    """
    player_name = player.name if hasattr(player, 'name') else "Joueur"
    
    career_text = f"Carrière de {player_name}\n\n"
    
    # Situation actuelle
    current_team_name = player.team.name if hasattr(player, 'team') and player.team else "Équipe inconnue"
    career_text += f"Équipe actuelle: {current_team_name}\n"
    
    # Historique des transferts
    if transfers and len(transfers) > 0:
        career_text += "\nHistorique des transferts:\n"
        
        # Trier les transferts par date (du plus récent au plus ancien)
        sorted_transfers = sorted(transfers, key=lambda t: t.date if hasattr(t, 'date') else datetime.min, reverse=True)
        
        for transfer in sorted_transfers:
            transfer_date = transfer.date.strftime('%d/%m/%Y') if hasattr(transfer, 'date') and transfer.date else "Date inconnue"
            from_team = transfer.team_out.name if hasattr(transfer, 'team_out') and transfer.team_out else "?"
            to_team = transfer.team_in.name if hasattr(transfer, 'team_in') and transfer.team_in else "?"
            transfer_type = transfer.type if hasattr(transfer, 'type') else "Transfert"
            
            career_text += f"- {transfer_date}: {from_team} → {to_team} ({transfer_type})\n"
    
    # Historique des équipes
    if team_history and len(team_history) > 0:
        career_text += "\nHistorique des clubs:\n"
        
        # Trier par saison (de la plus récente à la plus ancienne)
        sorted_history = sorted(team_history, 
                               key=lambda th: th.season.year if hasattr(th, 'season') and hasattr(th.season, 'year') else 0, 
                               reverse=True)
        
        for history_entry in sorted_history:
            season_year = f"{history_entry.season.year}-{history_entry.season.year + 1}" if hasattr(history_entry, 'season') and hasattr(history_entry.season, 'year') else "Saison inconnue"
            team_name = history_entry.team.name if hasattr(history_entry, 'team') and history_entry.team else "Équipe inconnue"
            
            career_text += f"- Saison {season_year}: {team_name}\n"
    
    # Si aucune information disponible
    if (not transfers or len(transfers) == 0) and (not team_history or len(team_history) == 0):
        career_text += "\nAucune information détaillée sur la carrière n'est disponible."
    
    return career_text