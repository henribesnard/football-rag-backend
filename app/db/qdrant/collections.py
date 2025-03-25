import logging
from typing import Dict, List, Optional, Union

from qdrant_client.http import models as rest
from .client import get_qdrant_client
from app.config import settings

logger = logging.getLogger(__name__)

# Définition des collections pour correspondre aux modèles Django
COLLECTIONS = {
    # Collection des pays
    "countries": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les pays",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "code": rest.PayloadSchemaType.KEYWORD,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des stades
    "venues": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les stades et enceintes sportives",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "city": rest.PayloadSchemaType.KEYWORD,
            "country_id": rest.PayloadSchemaType.INTEGER,
            "capacity": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des ligues
    "leagues": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les ligues et compétitions",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "type": rest.PayloadSchemaType.KEYWORD,
            "country_id": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des équipes
    "teams": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les équipes de football",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "code": rest.PayloadSchemaType.KEYWORD,
            "country_id": rest.PayloadSchemaType.INTEGER,
            "founded": rest.PayloadSchemaType.INTEGER,
            "is_national": rest.PayloadSchemaType.BOOLEAN,
            "venue_id": rest.PayloadSchemaType.INTEGER,
            "total_matches": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des saisons
    "seasons": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les saisons des compétitions",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "league_id": rest.PayloadSchemaType.INTEGER,
            "year": rest.PayloadSchemaType.INTEGER,
            "start_date": rest.PayloadSchemaType.DATETIME,
            "end_date": rest.PayloadSchemaType.DATETIME,
            "is_current": rest.PayloadSchemaType.BOOLEAN,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des matchs
    "fixtures": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les matchs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "league_id": rest.PayloadSchemaType.INTEGER,
            "season_id": rest.PayloadSchemaType.INTEGER,
            "round": rest.PayloadSchemaType.KEYWORD,
            "home_team_id": rest.PayloadSchemaType.INTEGER,
            "away_team_id": rest.PayloadSchemaType.INTEGER,
            "date": rest.PayloadSchemaType.DATETIME,
            "venue_id": rest.PayloadSchemaType.INTEGER,
            "status_code": rest.PayloadSchemaType.KEYWORD,
            "home_score": rest.PayloadSchemaType.INTEGER,
            "away_score": rest.PayloadSchemaType.INTEGER,
            "is_finished": rest.PayloadSchemaType.BOOLEAN,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des événements de match
    "fixture_events": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Événements survenus pendant les matchs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "fixture_id": rest.PayloadSchemaType.INTEGER,
            "time_elapsed": rest.PayloadSchemaType.INTEGER,
            "event_type": rest.PayloadSchemaType.KEYWORD,
            "player_id": rest.PayloadSchemaType.INTEGER,
            "assist_id": rest.PayloadSchemaType.INTEGER,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des joueurs
    "players": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les joueurs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "firstname": rest.PayloadSchemaType.KEYWORD,
            "lastname": rest.PayloadSchemaType.KEYWORD,
            "birth_date": rest.PayloadSchemaType.DATETIME,
            "nationality_id": rest.PayloadSchemaType.INTEGER,
            "height": rest.PayloadSchemaType.INTEGER,
            "weight": rest.PayloadSchemaType.INTEGER,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "position": rest.PayloadSchemaType.KEYWORD,
            "injured": rest.PayloadSchemaType.BOOLEAN,
            "season_goals": rest.PayloadSchemaType.INTEGER,
            "season_assists": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des statistiques des joueurs
    "player_statistics": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Statistiques des joueurs par match",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "player_id": rest.PayloadSchemaType.INTEGER,
            "fixture_id": rest.PayloadSchemaType.INTEGER,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "minutes_played": rest.PayloadSchemaType.INTEGER,
            "goals": rest.PayloadSchemaType.INTEGER,
            "assists": rest.PayloadSchemaType.INTEGER,
            "rating": rest.PayloadSchemaType.FLOAT,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des entraîneurs
    "coaches": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Informations sur les entraîneurs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "external_id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "nationality_id": rest.PayloadSchemaType.INTEGER,
            "birth_date": rest.PayloadSchemaType.DATETIME,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "career_matches": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des carrières d'entraîneurs
    "coach_careers": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Historique de carrière des entraîneurs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "coach_id": rest.PayloadSchemaType.INTEGER,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "role": rest.PayloadSchemaType.KEYWORD,
            "start_date": rest.PayloadSchemaType.DATETIME,
            "end_date": rest.PayloadSchemaType.DATETIME,
            "matches": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des cotes de paris
    "odds": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Cotes de paris par match et bookmaker",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "fixture_id": rest.PayloadSchemaType.INTEGER,
            "bookmaker_id": rest.PayloadSchemaType.INTEGER,
            "odds_type_id": rest.PayloadSchemaType.INTEGER,
            "odds_value_id": rest.PayloadSchemaType.INTEGER,
            "value": rest.PayloadSchemaType.FLOAT,
            "probability": rest.PayloadSchemaType.FLOAT,
            "status": rest.PayloadSchemaType.KEYWORD,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des classements
    "standings": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Classements des équipes par saison",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "season_id": rest.PayloadSchemaType.INTEGER,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "rank": rest.PayloadSchemaType.INTEGER,
            "points": rest.PayloadSchemaType.INTEGER,
            "goals_diff": rest.PayloadSchemaType.INTEGER,
            "played": rest.PayloadSchemaType.INTEGER,
            "won": rest.PayloadSchemaType.INTEGER,
            "drawn": rest.PayloadSchemaType.INTEGER,
            "lost": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des transferts de joueurs
    "player_transfers": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Historique des transferts de joueurs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "player_id": rest.PayloadSchemaType.INTEGER,
            "date": rest.PayloadSchemaType.DATETIME,
            "type": rest.PayloadSchemaType.KEYWORD,
            "team_in_id": rest.PayloadSchemaType.INTEGER,
            "team_out_id": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des blessures de joueurs
    "player_injuries": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Historique des blessures de joueurs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "player_id": rest.PayloadSchemaType.INTEGER,
            "fixture_id": rest.PayloadSchemaType.INTEGER,
            "type": rest.PayloadSchemaType.KEYWORD,
            "severity": rest.PayloadSchemaType.KEYWORD,
            "status": rest.PayloadSchemaType.KEYWORD,
            "start_date": rest.PayloadSchemaType.DATETIME,
            "end_date": rest.PayloadSchemaType.DATETIME,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des statistiques d'équipe
    "team_statistics": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Statistiques des équipes par saison",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "team_id": rest.PayloadSchemaType.INTEGER,
            "league_id": rest.PayloadSchemaType.INTEGER,
            "season_id": rest.PayloadSchemaType.INTEGER,
            "matches_played_total": rest.PayloadSchemaType.INTEGER,
            "wins_total": rest.PayloadSchemaType.INTEGER,
            "draws_total": rest.PayloadSchemaType.INTEGER,
            "losses_total": rest.PayloadSchemaType.INTEGER,
            "goals_for_total": rest.PayloadSchemaType.INTEGER,
            "goals_against_total": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection des confrontations directes
    "h2h_fixtures": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Confrontations directes entre équipes",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "reference_fixture_id": rest.PayloadSchemaType.INTEGER,
            "related_fixture_id": rest.PayloadSchemaType.INTEGER,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    # Collection de connaissances enrichies
    "football_knowledge": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Articles, analyses et connaissances générales sur le football",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "title": rest.PayloadSchemaType.KEYWORD,
            "content_type": rest.PayloadSchemaType.KEYWORD,
            "entities": rest.PayloadSchemaType.KEYWORD,  
            "relevance": rest.PayloadSchemaType.FLOAT,
            "created_at": rest.PayloadSchemaType.DATETIME,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    }
}

def get_collection_name(entity_type: str) -> str:
    """
    Retourne le nom de la collection Qdrant pour un type d'entité donné.
    Permet de standardiser les noms de collections.
    """
    mapping = {
        'country': 'countries',
        'venue': 'venues',
        'league': 'leagues',
        'team': 'teams',
        'season': 'seasons',
        'fixture': 'fixtures',
        'fixture_event': 'fixture_events',
        'player': 'players',
        'player_statistic': 'player_statistics',
        'coach': 'coaches',
        'coach_career': 'coach_careers',
        'odd': 'odds',
        'standing': 'standings',
        'player_transfer': 'player_transfers',
        'player_injury': 'player_injuries',
        'team_statistic': 'team_statistics',
        'h2h_fixture': 'h2h_fixtures',
        'knowledge': 'football_knowledge'
    }
    
    return mapping.get(entity_type, entity_type)

def initialize_collections() -> None:
    """
    Initialise toutes les collections Qdrant définies dans COLLECTIONS.
    Crée les collections si elles n'existent pas ou vérifie leur configuration.
    """
    client = get_qdrant_client()
    
    # Récupérer les collections existantes
    existing_collections = {
        collection.name for collection in client.get_collections().collections
    }
    
    # Créer ou mettre à jour chaque collection
    for collection_name, config in COLLECTIONS.items():
        try:
            if collection_name not in existing_collections:
                logger.info(f"Création de la collection {collection_name}...")
                
                # Configuration HNSW optimisée pour les performances de recherche
                hnsw_config = rest.HnswConfigDiff(
                    m=16,                   # Nombre de connexions par nœud (par défaut: 16)
                    ef_construct=128,       # Priorité à la précision pendant la construction (par défaut: 100)
                    full_scan_threshold=10000  # Seuil pour basculer en scan complet (par défaut: 10000)
                )
                
                # Configuration d'optimisation
                optimizers_config = rest.OptimizersConfigDiff(
                    deleted_threshold=0.2   # Seuil pour déclencher l'optimisation (par défaut: 0.2)
                )
                
                # Création de la collection avec les configurations
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=config["vectors_config"],
                    hnsw_config=hnsw_config,
                    optimizers_config=optimizers_config
                )
                
                # Création des index de payload pour améliorer les performances de filtrage
                for field_name, field_type in config["payload_schema"].items():
                    client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field_name,
                        field_schema=field_type
                    )
                    
                logger.info(f"Collection {collection_name} créée avec succès")
            else:
                logger.info(f"La collection {collection_name} existe déjà")
                
                # Mise à jour des index de payload (si nécessaire)
                for field_name, field_type in config["payload_schema"].items():
                    try:
                        client.create_payload_index(
                            collection_name=collection_name,
                            field_name=field_name,
                            field_schema=field_type
                        )
                    except Exception as e:
                        # Ignorer les erreurs si l'index existe déjà
                        logger.debug(f"Index pour {field_name} déjà existant ou erreur: {str(e)}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la collection {collection_name}: {str(e)}")
            raise