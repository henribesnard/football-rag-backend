"""
Interface en ligne de commande pour le système CDC.
"""
import argparse
import logging
import sys
import time
import json
from typing import Dict, Any

from app.cdc.manager import CDCManager
from app.config import settings

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.CDC_LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_cdc() -> None:
    """Démarre le système CDC."""
    manager = CDCManager()
    logger.info("Démarrage du système CDC...")
    try:
        manager.start()
    except KeyboardInterrupt:
        logger.info("Arrêt du système CDC par l'utilisateur")
    finally:
        manager.stop()

def status_cdc() -> None:
    """Affiche le statut du système CDC."""
    manager = CDCManager()
    status = manager.get_status()
    
    print(json.dumps(status, indent=2))

def test_cdc() -> None:
    """Effectue un test du système CDC."""
    from app.db.postgres.connection import get_db_session
    from app.models import Country
    
    logger.info("Test du système CDC en cours...")
    
    # Créer un manager CDC mais ne pas le démarrer complètement
    manager = CDCManager()
    
    # Créer un nouvel enregistrement dans la base de données
    session = get_db_session()
    try:
        # Créer un pays de test
        test_country = Country(
            name=f"Test Country {int(time.time())}",
            code=f"TC{int(time.time()) % 1000}",
            flag_url="https://example.com/flag.png"
        )
        session.add(test_country)
        session.commit()
        
        country_id = test_country.id
        logger.info(f"Pays de test créé avec ID {country_id}")
        
        # Attendre un peu pour que Debezium détecte le changement
        time.sleep(5)
        
        # Modifier le pays
        test_country.name += " (Modified)"
        session.commit()
        logger.info(f"Pays de test modifié (ID {country_id})")
        
        # Attendre encore un peu
        time.sleep(5)
        
        # Supprimer le pays
        session.delete(test_country)
        session.commit()
        logger.info(f"Pays de test supprimé (ID {country_id})")
        
        logger.info("Test terminé. Vérifiez les logs pour voir si les événements CDC ont été traités correctement.")
    
    except Exception as e:
        logger.error(f"Erreur lors du test: {str(e)}")
    finally:
        session.close()

def main():
    """Point d'entrée principal pour la CLI."""
    parser = argparse.ArgumentParser(description='Gestion du système CDC')
    
    subparsers = parser.add_subparsers(dest='command', help='Commande à exécuter')
    
    # Commande start
    start_parser = subparsers.add_parser('start', help='Démarrer le système CDC')
    
    # Commande status
    status_parser = subparsers.add_parser('status', help='Afficher le statut du système CDC')
    
    # Commande test
    test_parser = subparsers.add_parser('test', help='Tester le système CDC')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        start_cdc()
    elif args.command == 'status':
        status_cdc()
    elif args.command == 'test':
        test_cdc()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()