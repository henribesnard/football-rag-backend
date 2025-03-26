#!/bin/bash

# Script pour enregistrer le connecteur Debezium auprès de Kafka Connect

# Attendre que Kafka Connect soit prêt
echo "Attente du démarrage de Kafka Connect..."
while ! curl -s http://localhost:8083/connectors > /dev/null; do
    sleep 1
done

echo "Kafka Connect est prêt. Enregistrement du connecteur..."

# Enregistrer le connecteur PostgreSQL
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" \
  http://localhost:8083/connectors/ -d @debezium-postgres-connector.json

echo "Connecteur enregistré. Vérification du statut..."

# Vérifier le statut du connecteur
sleep 5
curl -s http://localhost:8083/connectors/football-postgres-connector/status | jq

echo "Configuration terminée!"