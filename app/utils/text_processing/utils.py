"""
Fonctions utilitaires pour le traitement de texte.
"""
from typing import List, Dict, Any, Optional, Union, Set
from datetime import datetime, date, timedelta
import re

def format_date(date_obj: Optional[Union[datetime, date]], include_time: bool = False) -> Optional[str]:
    """
    Formate une date en chaîne de caractères lisible.
    
    Args:
        date_obj: L'objet date ou datetime à formater
        include_time: Si True, inclut l'heure dans le formatage
        
    Returns:
        La date formatée ou None si date_obj est None
    """
    if date_obj is None:
        return None
    
    if isinstance(date_obj, datetime) and include_time:
        return date_obj.strftime('%d/%m/%Y %H:%M')
    else:
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        return date_obj.strftime('%d/%m/%Y')

def format_percentage(value: Union[int, float], total: Union[int, float]) -> str:
    """
    Calcule et formate un pourcentage.
    
    Args:
        value: La valeur à calculer en pourcentage
        total: La valeur totale
        
    Returns:
        Le pourcentage formaté
    """
    if not total:
        return "0.0%"
    
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"

def format_duration(minutes: Optional[int]) -> str:
    """
    Formate une durée en minutes en format heures/minutes.
    
    Args:
        minutes: Nombre de minutes
        
    Returns:
        La durée formatée
    """
    if minutes is None:
        return "N/A"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours > 0:
        return f"{hours}h {remaining_minutes}min"
    else:
        return f"{remaining_minutes}min"

def get_age_from_birthdate(birth_date: Optional[Union[datetime, date]]) -> Optional[int]:
    """
    Calcule l'âge à partir d'une date de naissance.
    
    Args:
        birth_date: Date de naissance
        
    Returns:
        L'âge en années ou None si birth_date est None
    """
    if birth_date is None:
        return None
    
    today = date.today()
    
    # Convertir datetime en date si nécessaire
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    # Calcul de l'âge
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    return age

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extrait les mots-clés les plus importants d'un texte.
    Méthode simple basée sur la fréquence des mots.
    
    Args:
        text: Le texte à analyser
        max_keywords: Nombre maximum de mots-clés à extraire
        
    Returns:
        Liste des mots-clés extraits
    """
    if not text:
        return []
    
    # Mots vides en français et anglais
    stopwords = {
        # Français
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'à', 'au', 'aux',
        'en', 'par', 'pour', 'sur', 'dans', 'avec', 'ce', 'cette', 'ces', 'que',
        'qui', 'quoi', 'dont', 'où', 'je', 'tu', 'il', 'elle', 'nous', 'vous',
        'ils', 'elles', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
        'notre', 'votre', 'leur', 'nos', 'vos', 'leurs',
        
        # Anglais
        'the', 'a', 'an', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'about',
        'against', 'between', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'over', 'under',
        'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'd', 'll',
        'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn',
        'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn',
        'wasn', 'weren', 'won', 'wouldn'
    }
    
    # Conversion en minuscules et tokenisation simple
    text = text.lower()
    words = re.findall(r'\b\w+\b', text)
    
    # Filtrer les mots vides et les mots courts
    filtered_words = [word for word in words if word not in stopwords and len(word) > 2]
    
    # Compter la fréquence des mots
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Trier les mots par fréquence
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    # Extraire les mots-clés les plus fréquents
    keywords = [word for word, _ in sorted_words[:max_keywords]]
    
    return keywords

def parse_date_range(date_text: str) -> Optional[Dict[str, date]]:
    """
    Parse une plage de dates dans un texte.
    Supporte divers formats courants.
    
    Args:
        date_text: Le texte contenant la plage de dates
        
    Returns:
        Dictionnaire avec les dates de début et de fin, ou None si aucune date trouvée
    """
    # Formats de date reconnus
    date_formats = [
        '%d/%m/%Y',  # 31/12/2023
        '%d-%m-%Y',  # 31-12-2023
        '%d.%m.%Y',  # 31.12.2023
        '%Y-%m-%d',  # 2023-12-31
        '%d/%m/%y',  # 31/12/23
        '%d %B %Y',  # 31 décembre 2023
        '%d %b %Y',  # 31 déc 2023
    ]
    
    # Rechercher différents patterns de plages de dates
    # Format: du/de DD/MM/YYYY au/à DD/MM/YYYY
    pattern1 = r'(?:du|de)\s+(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})(?:\s+au|\s+à)\s+(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})'
    # Format: DD/MM/YYYY - DD/MM/YYYY
    pattern2 = r'(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})\s*[-–—]\s*(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})'
    # Format: entre DD/MM/YYYY et DD/MM/YYYY
    pattern3 = r'entre\s+(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})(?:\s+et|\s+&)\s+(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})'
    
    # Tester les différents patterns
    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, date_text)
        if match:
            start_date_str, end_date_str = match.groups()
            
            # Essayer différents formats de date
            start_date = None
            end_date = None
            
            for date_format in date_formats:
                try:
                    start_date = datetime.strptime(start_date_str, date_format).date()
                    break
                except ValueError:
                    continue
            
            for date_format in date_formats:
                try:
                    end_date = datetime.strptime(end_date_str, date_format).date()
                    break
                except ValueError:
                    continue
            
            if start_date and end_date:
                return {"start": start_date, "end": end_date}
    
    # Si aucun pattern de plage n'est trouvé, chercher une seule date
    date_patterns = [
        r'(\d{1,2}[/-\.]\d{1,2}[/-\.]\d{2,4})',  # Formats numériques
        r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{2,4})'  # Format textuel
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_text)
        if match:
            date_str = match.group(1)
            
            # Essayer différents formats de date
            parsed_date = None
            for date_format in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, date_format).date()
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                # Retourner la même date pour début et fin (une journée)
                return {"start": parsed_date, "end": parsed_date}
    
    # Aucune date trouvée
    return None

def find_entities_in_text(text: str, entity_list: List[str]) -> List[str]:
    """
    Identifie les entités mentionnées dans un texte.
    
    Args:
        text: Le texte à analyser
        entity_list: Liste des entités potentielles
        
    Returns:
        Liste des entités trouvées dans le texte
    """
    text_lower = text.lower()
    found_entities = []
    
    for entity in entity_list:
        entity_lower = entity.lower()
        # Vérifier si l'entité est mentionnée dans le texte (comme mot complet)
        if re.search(r'\b' + re.escape(entity_lower) + r'\b', text_lower):
            found_entities.append(entity)
    
    return found_entities

def truncate_text(text: str, max_length: int = 500, add_ellipsis: bool = True) -> str:
    """
    Tronque un texte à une longueur maximale.
    
    Args:
        text: Le texte à tronquer
        max_length: Longueur maximale du texte
        add_ellipsis: Si True, ajoute des points de suspension
        
    Returns:
        Le texte tronqué
    """
    if not text or len(text) <= max_length:
        return text
    
    # Tronquer au dernier espace avant max_length pour éviter de couper un mot
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    if add_ellipsis:
        truncated += "..."
    
    return truncated

def create_search_variants(term: str) -> List[str]:
    """
    Crée des variantes de recherche pour un terme.
    
    Args:
        term: Le terme de base
        
    Returns:
        Liste des variantes de recherche
    """
    variants = [term]
    term_lower = term.lower()
    
    # Ajouter le terme en minuscules s'il est différent
    if term_lower != term:
        variants.append(term_lower)
    
    # Ajouter le terme avec la première lettre en majuscule
    if term_lower != term and term_lower.capitalize() != term:
        variants.append(term_lower.capitalize())
    
    # Ajouter le terme tout en majuscules pour les acronymes
    if term.upper() != term:
        variants.append(term.upper())
    
    # Variantes avec/sans accents pour les termes français
    from unicodedata import normalize
    normalized = normalize('NFD', term_lower).encode('ascii', 'ignore').decode('utf-8')
    if normalized != term_lower:
        variants.append(normalized)
    
    # Variantes pour les noms de joueurs (prénom-nom, nom seul)
    if ' ' in term:
        parts = term.split(' ', 1)  # Séparer en prénom et nom
        if len(parts) == 2:
            first_name, last_name = parts
            # Ajouter le nom de famille seul
            variants.append(last_name)
            # Ajouter l'initiale du prénom + nom
            if len(first_name) > 0:
                variants.append(f"{first_name[0]}. {last_name}")
    
    return list(set(variants))  # Éliminer les doublons