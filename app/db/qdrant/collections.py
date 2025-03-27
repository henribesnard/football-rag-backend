import logging
from typing import Dict, List, Optional, Union

from qdrant_client.http import models as rest
from .client import get_qdrant_client
from app.config import settings

logger = logging.getLogger(__name__)

# Définition des collections pour correspondre aux modèles Django

COLLECTIONS = {
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
    "odds_types": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Types de paris disponibles",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "name": rest.PayloadSchemaType.KEYWORD,
            "key": rest.PayloadSchemaType.KEYWORD,
            "description": rest.PayloadSchemaType.TEXT,
            "category": rest.PayloadSchemaType.KEYWORD,
            "update_at": rest.PayloadSchemaType.DATETIME
        }
    },
    "predictions": {
        "vectors_config": rest.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=rest.Distance.COSINE
        ),
        "description": "Prédictions de matchs",
        "payload_schema": {
            "id": rest.PayloadSchemaType.INTEGER,
            "fixture_id": rest.PayloadSchemaType.INTEGER,
            "winner_id": rest.PayloadSchemaType.INTEGER,
            "winner_name": rest.PayloadSchemaType.KEYWORD,
            "percent_home": rest.PayloadSchemaType.KEYWORD,
            "percent_draw": rest.PayloadSchemaType.KEYWORD,
            "percent_away": rest.PayloadSchemaType.KEYWORD,
            "advice": rest.PayloadSchemaType.TEXT,
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
        'prediction': 'predictions',
        'odd': 'odds',
        'odd_type': 'odds_types'
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