"""
Fonctions pour extraire des mots-clés et concepts de textes footballistiques.
"""
from typing import List, Dict, Any, Set, Tuple
import re

# Dictionnaire des termes footballistiques par catégorie
FOOTBALL_TERMS = {
    "positions": {
        "gardien", "gardien de but", "goalkeeper", "keeper", 
        "défenseur", "défenseur central", "latéral", "arrière", "defender", "centre-back", "full-back",
        "milieu", "milieu de terrain", "milieu défensif", "milieu offensif", "midfielder", "defensive midfielder",
        "attaquant", "avant-centre", "ailier", "buteur", "forward", "striker", "winger"
    },
    
    "événements": {
        "but", "goal", "penalty", "coup franc", "free kick", "corner", "hors-jeu", "offside",
        "carton", "carton jaune", "carton rouge", "yellow card", "red card", 
        "faute", "foul", "tacle", "tackle", "passe", "pass", "tir", "shot", "arrêt", "save",
        "remplacement", "substitution", "blessure", "injury", "mi-temps", "half-time"
    },
    
    "compétitions": {
        "championnat", "league", "ligue", "coupe", "cup", 
        "ligue des champions", "champions league", "europa league", "ligue europa",
        "coupe du monde", "world cup", "mondial", "euro", "championnat d'europe",
        "qualification", "éliminatoires", "groupe", "phase finale", "knockout stage"
    },
    
    "statistiques": {
        "victoire", "win", "défaite", "loss", "nul", "draw", "match nul",
        "classement", "standing", "points", "goals", "buts", "assists", "passes décisives",
        "clean sheet", "possession", "tirs", "shots", "précision", "accuracy",
        "série", "streak", "invaincu", "unbeaten"
    },
    
    "tactiques": {
        "formation", "système", "system", "tactique", "tactics",
        "pressing", "contre-attaque", "counter-attack", "jeu de possession", "possession game",
        "défense", "defense", "attaque", "attack", "aile", "wing", "centre", "center",
        "marquage", "marking", "zone", "bloc", "block", "hors-jeu", "offside trap"
    },
    
    "transferts": {
        "transfert", "transfer", "mercato", "recrutement", "recruitment",
        "prêt", "loan", "option d'achat", "buy option", "clause libératoire", "release clause",
        "contrat", "contract", "prolongation", "extension", "agent", "libre", "free agent"
    }
}

def extract_football_keywords(text: str) -> Dict[str, List[str]]:
    """
    Extrait les mots-clés footballistiques d'un texte et les catégorise.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        Dictionnaire des mots-clés par catégorie
    """
    text_lower = text.lower()
    found_keywords = {category: [] for category in FOOTBALL_TERMS}
    
    # Rechercher les termes par catégorie
    for category, terms in FOOTBALL_TERMS.items():
        for term in terms:
            # Chercher le terme comme mot complet
            if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
                found_keywords[category].append(term)
    
    # Filtrer les catégories vides
    return {cat: terms for cat, terms in found_keywords.items() if terms}

def identify_entities(text: str, entity_lists: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Identifie les entités footballistiques mentionnées dans un texte.
    
    Args:
        text: Le texte à analyser
        entity_lists: Dictionnaire avec les listes d'entités par type
        
    Returns:
        Dictionnaire des entités identifiées par type
    """
    text_lower = text.lower()
    found_entities = {entity_type: [] for entity_type in entity_lists}
    
    # Rechercher chaque type d'entité
    for entity_type, entities in entity_lists.items():
        for entity in entities:
            entity_lower = entity.lower()
            
            # Vérifier les variantes possibles (avec/sans accents, etc.)
            variants = [
                entity_lower,
                entity_lower.replace(" ", ""),  # Sans espaces
                # Ajouter d'autres variantes si nécessaire
            ]
            
            for variant in variants:
                if re.search(r'\b' + re.escape(variant) + r'\b', text_lower):
                    found_entities[entity_type].append(entity)
                    break  # Sortir après avoir trouvé une correspondance
    
    # Filtrer les types sans entités
    return {ent_type: ents for ent_type, ents in found_entities.items() if ents}

def extract_question_type(question: str) -> Tuple[str, float]:
    """
    Identifie le type de question footballistique.
    
    Args:
        question: La question à analyser
        
    Returns:
        Tuple (type de question, niveau de confiance)
    """
    # Catégories de questions avec mots-clés associés
    question_types = {
        "statistics": {
            "keywords": ["statistiques", "stats", "combien", "nombre", "meilleur", "buteur", 
                        "passes", "buts", "cartons", "clean sheets", "victoires", "défaites"],
            "pattern": r"\b(combien|quel est le nombre|statistiques|meilleur buteur|classement)\b"
        },
        "result": {
            "keywords": ["score", "résultat", "match", "gagné", "perdu", "nul", "vainqueur"],
            "pattern": r"\b(score|résultat|a gagné|qui a gagné|quel a été le)\b"
        },
        "player_info": {
            "keywords": ["joueur", "joue", "quel club", "nationalité", "âge", "position", "contrat"],
            "pattern": r"\b(quel joueur|où joue|quelle équipe|quel âge|nationalité|position)\b"
        },
        "team_info": {
            "keywords": ["équipe", "club", "entraîneur", "stade", "fondé", "palmarès", "effectif"],
            "pattern": r"\b(équipe|club|entraîneur|joueurs|stade|fondé(e)?|palmarès)\b"
        },
        "transfer": {
            "keywords": ["transfert", "recruté", "acheté", "vendu", "prêté", "montant", "clause"],
            "pattern": r"\b(transfert|recrut(é|er|ement)|achet(é|er)|vend(u|re)|prêt(é)?|combien coûte)\b"
        },
        "fixture": {
            "keywords": ["quand", "joue", "prochain match", "calendrier", "programmé", "rencontre"],
            "pattern": r"\b(quand|quel jour|à quelle date|prochain match|rencontre|programmé|joue contre)\b"
        },
        "comparison": {
            "keywords": ["compare", "comparaison", "meilleur", "pire", "versus", "contre", "ou"],
            "pattern": r"\b(compar(er|aison)|meilleur|mieux que|pire que|plus que|versus|vs)\b"
        }
    }
    
    # Calculer le score pour chaque type de question
    scores = {}
    question_lower = question.lower()
    
    for q_type, q_info in question_types.items():
        # Score basé sur les mots-clés
        keyword_matches = sum(1 for kw in q_info["keywords"] if re.search(r'\b' + re.escape(kw) + r'\b', question_lower))
        keyword_score = keyword_matches / len(q_info["keywords"])
        
        # Score basé sur les patterns
        pattern_match = 1.0 if re.search(q_info["pattern"], question_lower) else 0.0
        
        # Score combiné (privilégier les patterns)
        final_score = 0.3 * keyword_score + 0.7 * pattern_match
        scores[q_type] = final_score
    
    # Déterminer le type le plus probable
    best_type = max(scores.items(), key=lambda x: x[1])
    
    return best_type

def extract_named_entities(text: str) -> Dict[str, List[str]]:
    """
    Extrait les entités nommées d'un texte footballistique de manière simplifiée.
    Pour une implémentation complète, il faudrait utiliser une bibliothèque NER.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        Dictionnaire des entités nommées par type
    """
    found_entities = {
        "players": [],
        "teams": [],
        "competitions": [],
        "venues": []
    }
    
    # Patrons de recherche simplifiés
    patterns = {
        "players": [
            r'(?:[A-Z][a-zéèêëàâäôöùûüç]+ ){1,2}[A-Z][a-zéèêëàâäôöùûüç]+',  # Nom complet avec majuscules
            r'(?:joueur|footballer|player|gardien|attaquant|défenseur|milieu)\s+([A-Z][a-zéèêëàâäôöùûüç]+)'  # Titre + nom
        ],
        "teams": [
            r'(?:équipe|club|team|sélection)\s+(?:de|du|d\'|des)?\s+([A-Z][a-zéèêëàâäôöùûüç]+(?:\s+[A-Z][a-zéèêëàâäôöùûüç]+)*)',
            r'(?:le|la|l\'|les)\s+([A-Z][a-zéèêëàâäôöùûüç]+(?:\s+[A-Z][a-zéèêëàâäôöùûüç]+)*)'
        ],
        "competitions": [
            r'(?:championnat|coupe|trophy|cup|ligue|league|compétition)\s+(?:de|du|d\'|des)?\s+([A-Z][a-zéèêëàâäôöùûüç]+(?:\s+[A-Z][a-zéèêëàâäôöùûüç]+)*)',
            r'(?:la|le|l\'|les)\s+([A-Z][a-zéèêëàâäôöùûüç]+(?:\s+[A-Z][a-zéèêëàâäôöùûüç]+)*)'
        ],
        "venues": [
            r'(?:stade|stadium|arena|parc)\s+([A-Z][a-zéèêëàâäôöùûüç]+(?:\s+[A-Z][a-zéèêëàâäôöùûüç]+)*)'
        ]
    }
    
    # Rechercher chaque type d'entité
    for entity_type, entity_patterns in patterns.items():
        for pattern in entity_patterns:
            matches = re.findall(pattern, text)
            if matches:
                found_entities[entity_type].extend(matches)
    
    # Éliminer les doublons
    for entity_type in found_entities:
        found_entities[entity_type] = list(set(found_entities[entity_type]))
    
    return found_entities

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyse simplifiée du sentiment d'un texte footballistique.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        Dictionnaire avec le sentiment et sa force
    """
    text_lower = text.lower()
    
    # Dictionnaires de termes positifs et négatifs dans le contexte du football
    positive_terms = {
        "victoire", "gagné", "champion", "succès", "triomphe", "réussite", "excellent", "superbe",
        "brillant", "fantastique", "impressionnant", "incroyable", "talent", "qualité", "force",
        "efficace", "performant", "historique", "remarquable", "meilleur", "dominant"
    }
    
    negative_terms = {
        "défaite", "perdu", "échec", "désastre", "catastrophe", "décevant", "misérable", "médiocre",
        "faible", "insuffisant", "mauvais", "pire", "inquiétant", "préoccupant", "problème",
        "difficulté", "crise", "relégation", "élimination", "blessure", "sanction"
    }
    
    # Compter les occurrences
    positive_count = sum(1 for term in positive_terms if term in text_lower)
    negative_count = sum(1 for term in negative_terms if term in text_lower)
    
    total_terms = positive_count + negative_count
    
    if total_terms == 0:
        return {"sentiment": "neutre", "score": 0.0, "confidence": 0.0}
    
    # Calculer le score de sentiment et la confiance
    sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
    confidence = min(1.0, (positive_count + negative_count) / 10)  # Plus de termes = plus de confiance
    
    # Déterminer le sentiment
    if sentiment_score > 0.2:
        sentiment = "positif"
    elif sentiment_score < -0.2:
        sentiment = "négatif"
    else:
        sentiment = "neutre"
    
    return {
        "sentiment": sentiment,
        "score": sentiment_score,
        "confidence": confidence,
        "positive_terms": positive_count,
        "negative_terms": negative_count
    }