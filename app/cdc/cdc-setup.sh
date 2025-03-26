#!/bin/bash

# Script de configuration du système CDC

# Couleurs pour améliorer la lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Configuration du système CDC pour l'application Football RAG${NC}"
echo "--------------------------------------------------------"

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker n'est pas installé. Veuillez l'installer avant de continuer.${NC}"
    exit 1
fi

# Vérifier que Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose n'est pas installé. Veuillez l'installer avant de continuer.${NC}"
    exit 1
fi

echo -e "${YELLOW}Création des répertoires nécessaires...${NC}"
mkdir -p data/zookeeper
mkdir -p data/kafka
mkdir -p data/postgres-wal

echo -e "${YELLOW}Démarrage des conteneurs Docker...${NC}"
docker-compose -f docker-compose-cdc.yml up -d

# Attendre que Kafka Connect soit prêt
echo -e "${YELLOW}Attente du démarrage de Kafka Connect...${NC}"
while ! curl -s http://localhost:8083/connectors > /dev/null; do
    echo -n "."
    sleep 2
done
echo -e "\n${GREEN}Kafka Connect est prêt !${NC}"

# Attendre un peu plus pour s'assurer que tout est bien démarré
sleep 5

echo -e "${YELLOW}Configuration de PostgreSQL pour la réplication logique...${NC}"
# Exécuter le script SQL dans PostgreSQL
docker exec -i postgres psql -U postgres -d ${DB_NAME:-football_db} < postgresql-replication-setup.sql
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Configuration PostgreSQL terminée avec succès !${NC}"
else
    echo -e "${RED}Erreur lors de la configuration PostgreSQL.${NC}"
    exit 1
fi

echo -e "${YELLOW}Enregistrement du connecteur Debezium...${NC}"
# Enregistrer le connecteur Debezium
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" \
    http://localhost:8083/connectors/ -d @debezium-postgres-connector.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Connecteur Debezium enregistré avec succès !${NC}"
else
    echo -e "${RED}Erreur lors de l'enregistrement du connecteur Debezium.${NC}"
    exit 1
fi

echo -e "${YELLOW}Vérification du statut du connecteur...${NC}"
sleep 5
curl -s http://localhost:8083/connectors/football-postgres-connector/status

echo -e "\n${GREEN}Configuration du système CDC terminée !${NC}"
echo -e "${BLUE}Vous pouvez maintenant démarrer le système CDC avec :${NC}"
echo -e "${YELLOW}python -m app.cdc.cli start${NC}"

echo -e "${BLUE}Interface Kafdrop disponible à l'adresse :${NC} http://localhost:9000"
echo "--------------------------------------------------------"