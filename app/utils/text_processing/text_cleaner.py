"""
Fonctions pour nettoyer et normaliser les textes avant traitement.
"""
import re
from typing import Dict, List, Set, Optional

# Dictionnaire de normalisation des termes footballistiques
FOOTBALL_TERMS_NORMALIZATION = {
    # Positions
    "gardien de but": "gardien",
    "goal": "gardien",
    "goalkeeper": "gardien",
    "keeper": "gardien",
    "goalie": "gardien",
    "défenseur central": "défenseur",
    "central defender": "défenseur",
    "centre-back": "défenseur",
    "arrière central": "défenseur",
    "libero": "défenseur",
    "stopper": "défenseur",
    "latéral": "défenseur",
    "full-back": "défenseur",
    "arrière latéral": "défenseur",
    "piston": "défenseur",
    "wing-back": "défenseur",
    "milieu défensif": "milieu",
    "defensive midfielder": "milieu",
    "milieu récupérateur": "milieu",
    "milieu relayeur": "milieu",
    "box-to-box": "milieu",
    "milieu offensif": "milieu",
    "meneur de jeu": "milieu",
    "playmaker": "milieu",
    "number 10": "milieu",
    "numéro 10": "milieu",
    "ailier": "attaquant",
    "winger": "attaquant",
    "avant-centre": "attaquant",
    "centre-forward": "attaquant",
    "striker": "attaquant",
    "buteur": "attaquant",
    "numéro 9": "attaquant",
    "number 9": "attaquant",
    
    # Événements de match
    "carton jaune": "carton",
    "yellow card": "carton",
    "carton rouge": "carton",
    "red card": "carton",
    "but": "goal",
    "goal": "goal",
    "assist": "passe décisive",
    "passe décisive": "passe décisive",
    "penalty": "penalty",
    "coup franc": "coup franc",
    "free kick": "coup franc",
    "corner": "corner",
    "coup de coin": "corner",
    
    # Types de compétitions
    "championnat": "league",
    "championship": "league",
    "liga": "league",
    "ligue": "league",
    "coupe": "cup",
    "cup": "cup",
    "champions league": "champions league",
    "ligue des champions": "champions league",
    "europa league": "europa league",
    "ligue europa": "europa league",
    "coupe du monde": "world cup",
    "world cup": "world cup",
    "euro": "euro",
    "european championship": "euro",
    "championnat d'europe": "euro",
    
    # Statistiques
    "clean sheet": "clean sheet",
    "match nul": "draw",
    "nul": "draw",
    "draw": "draw",
    "victoire": "win",
    "win": "win",
    "défaite": "loss",
    "loss": "loss",
    "lose": "loss",
    "classement": "standing",
    "standing": "standing",
    "stats": "statistics",
    "statistiques": "statistics",
    "statistics": "statistics"
}

def clean_text_for_embedding(text: str) -> str:
    """
    Nettoie et normalise le texte avant de générer un embedding.
    
    Args:
        text: Le texte à nettoyer
        
    Returns:
        Le texte nettoyé
    """
    if not text:
        return ""
    
    # Supprimer les espaces multiples
    text = ' '.join(text.split())
    
    # Supprimer les caractères spéciaux inutiles
    text = text.replace('\t', ' ').replace('\r', ' ')
    
    # Normaliser les sauts de ligne
    text = text.replace('\n\n\n', '\n').replace('\n\n', '\n')
    
    # Convertir en minuscules pour les recherches sémantiques
    text = text.lower()
    
    return text.strip()

def sanitize_user_query(query: str) -> str:
    """
    Nettoie et normalise une requête utilisateur.
    
    Args:
        query: La requête à nettoyer
        
    Returns:
        La requête nettoyée
    """
    if not query:
        return ""
    
    # Supprimer les espaces excessifs
    query = ' '.join(query.split())
    
    # Supprimer les caractères spéciaux inutiles
    query = re.sub(r'[^\w\s\.,;:!?&\(\)\[\]\'"-]', '', query)
    
    # Normaliser certains caractères
    query = query.replace("’", "'").replace('“', '"').replace('”', '"')
    
    return query.strip()

def normalize_football_terms(text: str) -> str:
    """
    Normalise les termes footballistiques pour améliorer la cohérence de la recherche.
    
    Args:
        text: Le texte à normaliser
        
    Returns:
        Le texte avec termes footballistiques normalisés
    """
    text_lower = text.lower()
    
    # Rechercher et remplacer les termes footballistiques
    for term, normalized in FOOTBALL_TERMS_NORMALIZATION.items():
        # Remplacer uniquement des mots entiers (avec des limites de mots)
        text_lower = re.sub(r'\b' + re.escape(term) + r'\b', normalized, text_lower)
    
    # Si le texte original contenait des majuscules, conserver la casse d'origine
    if not text.islower():
        return text
    
    return text_lower

def remove_stopwords(text: str, stopwords: Optional[Set[str]] = None) -> str:
    """
    Supprime les mots vides du texte.
    
    Args:
        text: Le texte à nettoyer
        stopwords: Ensemble optionnel de mots vides à utiliser
        
    Returns:
        Le texte sans mots vides
    """
    if not text:
        return ""
    
    # Utiliser l'ensemble de mots vides fourni ou un ensemble par défaut
    if stopwords is None:
        # Mots vides français courants
        stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'à', 'au', 'aux',
            'en', 'par', 'pour', 'sur', 'dans', 'avec', 'ce', 'cette', 'ces', 'que',
            'qui', 'quoi', 'dont', 'où', 'je', 'tu', 'il', 'elle', 'nous', 'vous',
            'ils', 'elles', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
            'notre', 'votre', 'leur', 'nos', 'vos', 'leurs'
        }
    
    # Tokenisation simple en utilisant l'espace comme séparateur
    words = text.split()
    
    # Filtrer les mots vides
    filtered_words = [word for word in words if word.lower() not in stopwords]
    
    # Reconstituer le texte
    return ' '.join(filtered_words)

def normalize_accents(text: str) -> str:
    """
    Normalise les caractères accentués.
    
    Args:
        text: Le texte à normaliser
        
    Returns:
        Le texte avec accents normalisés
    """
    import unicodedata
    
    # Normaliser les caractères Unicode (NFD décompose les caractères accentués)
    nfkd_form = unicodedata.normalize('NFKD', text)
    
    # Recombiner sans les accents (supprimer les caractères non-ASCII)
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))