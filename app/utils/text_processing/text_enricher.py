"""
Fonctions pour enrichir les textes avec du contexte footballistique.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

def enrich_football_text(text: str, metadata: Dict[str, Any]) -> str:
    """
    Enrichit le texte avec des métadonnées pour améliorer la recherche sémantique.
    
    Args:
        text: Le texte original
        metadata: Un dictionnaire de métadonnées
        
    Returns:
        Le texte enrichi
    """
    enriched_text = text
    
    # Ajouter un préambule avec les informations clés
    preface = []
    
    if 'entity_type' in metadata:
        preface.append(f"Type: {metadata['entity_type']}")
    
    if 'name' in metadata:
        preface.append(f"Nom: {metadata['name']}")
        
    if 'date' in metadata and metadata['date']:
        date_str = metadata['date'].strftime('%d/%m/%Y') if isinstance(metadata['date'], datetime) else metadata['date']
        preface.append(f"Date: {date_str}")
        
    if 'category' in metadata:
        preface.append(f"Catégorie: {metadata['category']}")
        
    if 'competition' in metadata:
        preface.append(f"Compétition: {metadata['competition']}")
        
    if 'season' in metadata:
        preface.append(f"Saison: {metadata['season']}")
        
    if 'teams' in metadata:
        teams = metadata['teams'] if isinstance(metadata['teams'], list) else [metadata['teams']]
        preface.append(f"Équipes: {', '.join(teams)}")
        
    if 'players' in metadata:
        players = metadata['players'] if isinstance(metadata['players'], list) else [metadata['players']]
        preface.append(f"Joueurs: {', '.join(players)}")
        
    if 'tags' in metadata and metadata['tags']:
        tags = metadata['tags'] if isinstance(metadata['tags'], list) else [metadata['tags']]
        preface.append(f"Tags: {', '.join(tags)}")
    
    # Combiner le préambule et le texte original
    if preface:
        enriched_text = "\n".join(preface) + "\n\n" + enriched_text
    
    return enriched_text

def add_football_context(text: str, context_type: str, context_data: Dict[str, Any]) -> str:
    """
    Ajoute du contexte footballistique spécifique à un texte.
    
    Args:
        text: Le texte original
        context_type: Type de contexte à ajouter ('match', 'player', 'team', 'competition')
        context_data: Données de contexte à intégrer
        
    Returns:
        Le texte enrichi avec le contexte
    """
    enriched_text = text
    
    # Ajouter une section contextuelle selon le type
    if context_type == 'match':
        context_section = _generate_match_context(context_data)
    elif context_type == 'player':
        context_section = _generate_player_context(context_data)
    elif context_type == 'team':
        context_section = _generate_team_context(context_data)
    elif context_type == 'competition':
        context_section = _generate_competition_context(context_data)
    else:
        return text  # Type de contexte non reconnu
    
    # Ajouter le contexte au texte
    if context_section:
        enriched_text += f"\n\nContexte additionnel:\n{context_section}"
    
    return enriched_text

def _generate_match_context(data: Dict[str, Any]) -> str:
    """Génère un contexte pour un match."""
    context = []
    
    if 'home_team' in data and 'away_team' in data:
        context.append(f"Match: {data['home_team']} vs {data['away_team']}")
    
    if 'date' in data:
        date_str = data['date'].strftime('%d/%m/%Y') if isinstance(data['date'], datetime) else data['date']
        context.append(f"Date: {date_str}")
    
    if 'competition' in data:
        context.append(f"Compétition: {data['competition']}")
    
    if 'venue' in data:
        context.append(f"Stade: {data['venue']}")
    
    if 'referee' in data:
        context.append(f"Arbitre: {data['referee']}")
    
    if 'score' in data:
        context.append(f"Score: {data['score']}")
    
    if 'status' in data:
        context.append(f"Statut: {data['status']}")
    
    # Historique des confrontations
    if 'h2h_summary' in data:
        context.append(f"Historique: {data['h2h_summary']}")
    
    return "\n".join(context)

def _generate_player_context(data: Dict[str, Any]) -> str:
    """Génère un contexte pour un joueur."""
    context = []
    
    if 'name' in data:
        context.append(f"Joueur: {data['name']}")
    
    if 'team' in data:
        context.append(f"Équipe actuelle: {data['team']}")
    
    if 'position' in data:
        context.append(f"Poste: {data['position']}")
    
    if 'nationality' in data:
        context.append(f"Nationalité: {data['nationality']}")
    
    if 'age' in data:
        context.append(f"Âge: {data['age']} ans")
    
    # Statistiques
    stats = []
    for stat_name in ['goals', 'assists', 'appearances', 'yellow_cards', 'red_cards']:
        if stat_name in data:
            stat_label = {
                'goals': 'Buts',
                'assists': 'Passes décisives',
                'appearances': 'Matchs joués',
                'yellow_cards': 'Cartons jaunes',
                'red_cards': 'Cartons rouges'
            }.get(stat_name, stat_name)
            stats.append(f"{stat_label}: {data[stat_name]}")
    
    if stats:
        context.append("Statistiques saison en cours: " + ", ".join(stats))
    
    # Forme récente
    if 'form' in data:
        context.append(f"Forme récente: {data['form']}")
    
    # Valeur marchande
    if 'market_value' in data:
        context.append(f"Valeur marchande: {data['market_value']}")
    
    # Statut de blessure
    if 'injury_status' in data:
        context.append(f"Statut: {data['injury_status']}")
    
    return "\n".join(context)

def _generate_team_context(data: Dict[str, Any]) -> str:
    """Génère un contexte pour une équipe."""
    context = []
    
    if 'name' in data:
        context.append(f"Équipe: {data['name']}")
    
    if 'country' in data:
        context.append(f"Pays: {data['country']}")
    
    if 'league' in data:
        context.append(f"Championnat: {data['league']}")
    
    if 'stadium' in data:
        context.append(f"Stade: {data['stadium']}")
    
    if 'coach' in data:
        context.append(f"Entraîneur: {data['coach']}")
    
    # Classement actuel
    if 'standing' in data:
        context.append(f"Classement actuel: {data['standing']}")
    
    # Statistiques
    stats = []
    for stat_name in ['wins', 'draws', 'losses', 'goals_scored', 'goals_conceded']:
        if stat_name in data:
            stat_label = {
                'wins': 'Victoires',
                'draws': 'Nuls',
                'losses': 'Défaites',
                'goals_scored': 'Buts marqués',
                'goals_conceded': 'Buts encaissés'
            }.get(stat_name, stat_name)
            stats.append(f"{stat_label}: {data[stat_name]}")
    
    if stats:
        context.append("Statistiques saison en cours: " + ", ".join(stats))
    
    # Forme récente
    if 'form' in data:
        context.append(f"Forme récente: {data['form']}")
    
    # Joueurs clés
    if 'key_players' in data and isinstance(data['key_players'], list):
        context.append(f"Joueurs clés: {', '.join(data['key_players'])}")
    
    return "\n".join(context)

def _generate_competition_context(data: Dict[str, Any]) -> str:
    """Génère un contexte pour une compétition."""
    context = []
    
    if 'name' in data:
        context.append(f"Compétition: {data['name']}")
    
    if 'country' in data:
        context.append(f"Pays/Zone: {data['country']}")
    
    if 'type' in data:
        context.append(f"Type: {data['type']}")
    
    if 'season' in data:
        context.append(f"Saison: {data['season']}")
    
    # Équipes participantes
    if 'teams_count' in data:
        context.append(f"Nombre d'équipes: {data['teams_count']}")
    
    if 'current_champion' in data:
        context.append(f"Tenant du titre: {data['current_champion']}")
    
    if 'most_titles' in data:
        context.append(f"Équipe la plus titrée: {data['most_titles']}")
    
    # Format de la compétition
    if 'format' in data:
        context.append(f"Format: {data['format']}")
    
    return "\n".join(context)

def add_multilingual_terms(text: str, language: str = 'fr') -> str:
    """
    Ajoute des termes équivalents dans d'autres langues pour améliorer la recherche multilingue.
    
    Args:
        text: Le texte original
        language: La langue principale du texte
        
    Returns:
        Le texte enrichi avec des termes multilingues
    """
    # Dictionnaire des termes footballistiques dans différentes langues
    football_terms = {
        'fr': {
            'but': ['goal', 'gol'],
            'gardien': ['goalkeeper', 'portero', 'portiere'],
            'défenseur': ['defender', 'defensa', 'difensore'],
            'milieu': ['midfielder', 'centrocampista', 'centrocampista'],
            'attaquant': ['forward', 'striker', 'delantero', 'attaccante'],
            'carton rouge': ['red card', 'tarjeta roja', 'cartellino rosso'],
            'carton jaune': ['yellow card', 'tarjeta amarilla', 'cartellino giallo'],
            'championnat': ['league', 'liga', 'campionato'],
            'coupe': ['cup', 'copa', 'coppa'],
            'classement': ['standings', 'clasificación', 'classifica']
        },
        'en': {
            'goal': ['but', 'gol'],
            'goalkeeper': ['gardien', 'portero', 'portiere'],
            'defender': ['défenseur', 'defensa', 'difensore'],
            'midfielder': ['milieu', 'centrocampista', 'centrocampista'],
            'forward': ['attaquant', 'delantero', 'attaccante'],
            'striker': ['attaquant', 'delantero', 'attaccante'],
            'red card': ['carton rouge', 'tarjeta roja', 'cartellino rosso'],
            'yellow card': ['carton jaune', 'tarjeta amarilla', 'cartellino giallo'],
            'league': ['championnat', 'liga', 'campionato'],
            'cup': ['coupe', 'copa', 'coppa'],
            'standings': ['classement', 'clasificación', 'classifica']
        }
    }
    
    # Si la langue n'est pas supportée, retourner le texte original
    if language not in football_terms:
        return text
    
    # Pour chaque terme dans la langue source, ajouter les équivalents
    terms_dict = football_terms[language]
    enriched_text = text
    
    for term, equivalents in terms_dict.items():
        # Vérifier si le terme est présent dans le texte
        import re
        if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
            # Ajouter les termes équivalents comme métadonnées
            equiv_text = ', '.join(equivalents)
            term_annotation = f"[{term}: {equiv_text}]"
            
            # Ajouter une seule fois l'annotation à la fin
            if term_annotation not in enriched_text:
                enriched_text += f"\n{term_annotation}"
    
    return enriched_text