# app/utils/text_processing/__init__.py
"""
Module d'utilitaires pour le traitement et la génération de texte à partir des modèles de données.
Ce module est crucial pour transformer les données structurées en représentations textuelles riches
pour l'embedding vectoriel et la génération de réponses.
"""

from .entity_formatter import create_entity_text, format_entity_for_display
from .text_cleaner import clean_text_for_embedding, sanitize_user_query, normalize_football_terms
from .text_enricher import enrich_football_text, add_football_context
from .team_formatter import format_team_data, describe_team_form, format_team_statistics
from .player_formatter import format_player_data, format_player_statistics, describe_player_career
from .match_formatter import format_match_data, format_match_events, describe_match_context
from .competition_formatter import format_league_data, format_standing_data, describe_competition_format
from .utils import extract_keywords, format_date, format_percentage, format_duration

__all__ = [
    'create_entity_text',
    'format_entity_for_display',
    'clean_text_for_embedding',
    'sanitize_user_query',
    'normalize_football_terms',
    'enrich_football_text',
    'add_football_context',
    'format_team_data',
    'describe_team_form',
    'format_team_statistics',
    'format_player_data',
    'format_player_statistics',
    'describe_player_career',
    'format_match_data',
    'format_match_events',
    'describe_match_context',
    'format_league_data',
    'format_standing_data',
    'describe_competition_format',
    'extract_keywords',
    'format_date',
    'format_percentage',
    'format_duration'
]