# app/utils/text_processing.py
from typing import Any, Optional
from datetime import datetime

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
    if entity_type == 'country':
        return f"""
        Pays: {entity.name}
        Code: {entity.code or 'N/A'}
        """
        
    elif entity_type == 'team':
        return f"""
        Équipe: {entity.name}
        Code: {entity.code or 'N/A'}
        Pays: {entity.country.name if entity.country else 'N/A'}
        {'Équipe nationale' if entity.is_national else 'Club'}
        Fondée en: {entity.founded or 'N/A'}
        Statistiques globales:
        - Matchs joués: {entity.total_matches}
        - Victoires: {entity.total_wins}
        - Nuls: {entity.total_draws}
        - Défaites: {entity.total_losses}
        - Buts marqués: {entity.total_goals_scored}
        - Buts encaissés: {entity.total_goals_conceded}
        """
        
    elif entity_type == 'player':
        return f"""
        Joueur: {entity.name}
        Prénom: {entity.firstname or 'N/A'}
        Nom: {entity.lastname or 'N/A'}
        Date de naissance: {entity.birth_date.strftime('%Y-%m-%d') if entity.birth_date else 'N/A'}
        Nationalité: {entity.nationality.name if entity.nationality else 'N/A'}
        Équipe actuelle: {entity.team.name if entity.team else 'N/A'}
        Position: {entity.get_position_display() if hasattr(entity, 'get_position_display') else entity.position}
        Numéro: {entity.number or 'N/A'}
        Statistiques saison en cours:
        - Buts: {entity.season_goals}
        - Passes décisives: {entity.season_assists}
        - Cartons jaunes: {entity.season_yellow_cards}
        - Cartons rouges: {entity.season_red_cards}
        - Apparitions: {entity.total_appearances}
        Statut: {"Blessé" if entity.injured else "En forme"}
        """
        
    elif entity_type == 'fixture':
        return f"""
        Match: {entity.home_team.name if entity.home_team else 'N/A'} vs {entity.away_team.name if entity.away_team else 'N/A'}
        Compétition: {entity.league.name if entity.league else 'N/A'}
        Saison: {entity.season.year if entity.season else 'N/A'}
        Date: {entity.date.strftime('%Y-%m-%d %H:%M') if entity.date else 'N/A'}
        Stade: {entity.venue.name if entity.venue else 'N/A'}
        Arbitre: {entity.referee or 'N/A'}
        Statut: {entity.status.long_description if entity.status else 'N/A'}
        Score: {f"{entity.home_score} - {entity.away_score}" if entity.home_score is not None and entity.away_score is not None else "N/A"}
        """
        
    elif entity_type == 'coach':
        return f"""
        Entraîneur: {entity.name}
        Prénom: {entity.firstname or 'N/A'}
        Nom: {entity.lastname or 'N/A'}
        Date de naissance: {entity.birth_date.strftime('%Y-%m-%d') if entity.birth_date else 'N/A'}
        Nationalité: {entity.nationality.name if entity.nationality else 'N/A'}
        Équipe actuelle: {entity.team.name if entity.team else 'N/A'}
        Carrière:
        - Matchs: {entity.career_matches}
        - Victoires: {entity.career_wins}
        - Nuls: {entity.career_draws}
        - Défaites: {entity.career_losses}
        """
        
    elif entity_type == 'standing':
        return f"""
        Classement: {entity.team.name if entity.team else 'N/A'} ({entity.season.league.name if entity.season and entity.season.league else 'N/A'} - {entity.season.year if entity.season else 'N/A'})
        Position: {entity.rank}
        Points: {entity.points}
        Différence de buts: {entity.goals_diff}
        Forme récente: {entity.form or 'N/A'}
        Matchs joués: {entity.played}
        Victoires: {entity.won}
        Nuls: {entity.drawn}
        Défaites: {entity.lost}
        Buts marqués: {entity.goals_for}
        Buts encaissés: {entity.goals_against}
        """
    
    elif entity_type == 'league':
        return f"""
        Compétition: {entity.name}
        Type: {entity.get_type_display() if hasattr(entity, 'get_type_display') else entity.type}
        Pays: {entity.country.name if entity.country else 'N/A'}
        """
    
    # Ajouter d'autres types d'entités selon les besoins
    
    # Si le type d'entité n'est pas pris en charge, retourner None
    return None

def clean_text_for_embedding(text: str) -> str:
    """
    Nettoie et normalise le texte avant de générer un embedding.
    
    Args:
        text: Le texte à nettoyer
        
    Returns:
        Le texte nettoyé
    """
    # Supprimer les espaces multiples
    text = ' '.join(text.split())
    
    # Supprimer les caractères spéciaux inutiles
    text = text.replace('\t', ' ').replace('\r', ' ')
    
    # Normaliser les sauts de ligne
    text = text.replace('\n\n\n', '\n').replace('\n\n', '\n')
    
    return text.strip()

def enrich_football_text(text: str, metadata: dict) -> str:
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
        date_str = metadata['date'].strftime('%Y-%m-%d') if isinstance(metadata['date'], datetime) else metadata['date']
        preface.append(f"Date: {date_str}")
        
    if 'category' in metadata:
        preface.append(f"Catégorie: {metadata['category']}")
        
    if 'tags' in metadata and metadata['tags']:
        tags = metadata['tags'] if isinstance(metadata['tags'], list) else [metadata['tags']]
        preface.append(f"Tags: {', '.join(tags)}")
    
    # Combiner le préambule et le texte original
    if preface:
        enriched_text = "\n".join(preface) + "\n\n" + enriched_text
    
    return enriched_text