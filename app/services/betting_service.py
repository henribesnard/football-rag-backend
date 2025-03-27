# app/services/betting_service.py
"""
Service pour les paris et prédictions sportives.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

from app.db.qdrant.operations import (
    search_fixtures_by_date, 
    get_fixture_odds, 
    get_fixture_prediction,
    search_team_fixtures
)
from app.db.postgres.connection import get_db_session
from app.db.postgres.models import get_model_by_entity_type

logger = logging.getLogger(__name__)

class BettingService:
    """
    Service pour les paris et prédictions sportives.
    """
    
    @staticmethod
    async def get_matches_of_day(target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Récupère tous les matchs prévus pour une date spécifique.
        
        Args:
            target_date: Date cible (aujourd'hui par défaut)
            
        Returns:
            Dictionnaire contenant les informations sur les matchs du jour
        """
        if target_date is None:
            target_date = date.today()
        
        # Récupérer les matchs pour cette date
        fixtures = search_fixtures_by_date(target_date, limit=50)
        
        if not fixtures:
            return {
                "date": target_date.strftime("%d/%m/%Y"),
                "matches_count": 0,
                "matches": []
            }
        
        # Enrichir les informations des matchs avec les noms d'équipes, etc.
        enriched_fixtures = []
        for fixture in fixtures:
            payload = fixture.get("payload", {})
            
            # Récupérer les informations sur les équipes
            session = get_db_session()
            try:
                Team = get_model_by_entity_type('team')
                League = get_model_by_entity_type('league')
                
                home_team = session.query(Team).filter(Team.id == payload.get("home_team_id")).first()
                away_team = session.query(Team).filter(Team.id == payload.get("away_team_id")).first()
                league = session.query(League).filter(League.id == payload.get("league_id")).first()
                
                match_time = datetime.fromisoformat(payload.get("date")) if payload.get("date") else None
                
                enriched_fixture = {
                    "id": payload.get("id"),
                    "home_team": home_team.name if home_team else "Équipe inconnue",
                    "away_team": away_team.name if away_team else "Équipe inconnue",
                    "league": league.name if league else "Compétition inconnue",
                    "time": match_time.strftime("%H:%M") if match_time else "Heure inconnue",
                    "status": payload.get("status_code", "Programmé")
                }
                
                enriched_fixtures.append(enriched_fixture)
            except Exception as e:
                logger.error(f"Erreur lors de l'enrichissement des informations du match: {str(e)}")
            finally:
                session.close()
        
        # Trier les matchs par heure
        enriched_fixtures.sort(key=lambda x: x.get("time", "00:00"))
        
        return {
            "date": target_date.strftime("%d/%m/%Y"),
            "matches_count": len(enriched_fixtures),
            "matches": enriched_fixtures
        }
    
    @staticmethod
    async def get_team_next_match(team_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le prochain match d'une équipe.
        
        Args:
            team_name: Nom de l'équipe
            
        Returns:
            Informations sur le prochain match ou None si non trouvé
        """
        # Rechercher l'équipe par son nom
        session = get_db_session()
        try:
            Team = get_model_by_entity_type('team')
            team = session.query(Team).filter(Team.name.ilike(f"%{team_name}%")).first()
            
            if not team:
                return None
            
            # Récupérer le prochain match
            fixtures = search_team_fixtures(team.id, upcoming=True, limit=1)
            
            if not fixtures or len(fixtures) == 0:
                return {
                    "team": team.name,
                    "message": "Aucun match à venir trouvé pour cette équipe"
                }
            
            fixture = fixtures[0]
            payload = fixture.get("payload", {})
            
            # Récupérer les informations sur l'adversaire et la compétition
            home_team_id = payload.get("home_team_id")
            away_team_id = payload.get("away_team_id")
            league_id = payload.get("league_id")
            
            opponent_id = away_team_id if home_team_id == team.id else home_team_id
            is_home = home_team_id == team.id
            
            League = get_model_by_entity_type('league')
            opponent = session.query(Team).filter(Team.id == opponent_id).first()
            league = session.query(League).filter(League.id == league_id).first()
            
            match_time = datetime.fromisoformat(payload.get("date")) if payload.get("date") else None
            
            # Format de la réponse
            return {
                "team": team.name,
                "match_id": payload.get("id"),
                "opponent": opponent.name if opponent else "Adversaire inconnu",
                "is_home": is_home,
                "date": match_time.strftime("%d/%m/%Y") if match_time else "Date inconnue",
                "time": match_time.strftime("%H:%M") if match_time else "Heure inconnue",
                "league": league.name if league else "Compétition inconnue"
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du prochain match pour {team_name}: {str(e)}")
            return None
        finally:
            session.close()
    
    @staticmethod
    async def get_match_odds(home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Récupère les cotes pour un match entre deux équipes.
        
        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
            
        Returns:
            Informations sur les cotes du match
        """
        # Rechercher les équipes et le match
        session = get_db_session()
        try:
            Team = get_model_by_entity_type('team')
            home = session.query(Team).filter(Team.name.ilike(f"%{home_team}%")).first()
            away = session.query(Team).filter(Team.name.ilike(f"%{away_team}%")).first()
            
            if not home or not away:
                return {
                    "error": f"Équipe(s) non trouvée(s): {'Domicile' if not home else ''} {'Extérieur' if not away else ''}"
                }
            
            # Rechercher le match à venir entre ces équipes
            Fixture = get_model_by_entity_type('fixture')
            fixture = session.query(Fixture).filter(
                Fixture.home_team_id == home.id,
                Fixture.away_team_id == away.id,
                Fixture.date > datetime.now()
            ).order_by(Fixture.date).first()
            
            if not fixture:
                return {
                    "error": f"Aucun match à venir trouvé entre {home.name} et {away.name}"
                }
            
            # Récupérer les cotes
            odds_data = get_fixture_odds(fixture.id)
            if not odds_data:
                return {
                    "match": f"{home.name} vs {away.name}",
                    "date": fixture.date.strftime("%d/%m/%Y %H:%M") if fixture.date else "Date inconnue",
                    "message": "Aucune cote disponible pour ce match"
                }
            
            # Traiter les cotes par type de pari
            OddsType = get_model_by_entity_type('odds_type')
            OddsValue = get_model_by_entity_type('odds_value')
            Bookmaker = get_model_by_entity_type('bookmaker')
            
            processed_odds = {}
            for odd in odds_data:
                payload = odd.get("payload", {})
                odds_type_id = payload.get("odds_type_id")
                odds_value_id = payload.get("odds_value_id")
                bookmaker_id = payload.get("bookmaker_id")
                
                odds_type = session.query(OddsType).filter(OddsType.id == odds_type_id).first()
                odds_value = session.query(OddsValue).filter(OddsValue.id == odds_value_id).first()
                bookmaker = session.query(Bookmaker).filter(Bookmaker.id == bookmaker_id).first()
                
                if not odds_type or not odds_value:
                    continue
                
                type_name = odds_type.name if odds_type else f"Type {odds_type_id}"
                value_name = odds_value.name if odds_value else f"Valeur {odds_value_id}"
                bookmaker_name = bookmaker.name if bookmaker else f"Bookmaker {bookmaker_id}"
                
                if type_name not in processed_odds:
                    processed_odds[type_name] = {}
                
                if value_name not in processed_odds[type_name]:
                    processed_odds[type_name][value_name] = []
                
                processed_odds[type_name][value_name].append({
                    "bookmaker": bookmaker_name,
                    "value": payload.get("value"),
                    "probability": payload.get("probability")
                })
            
            # Récupérer la prédiction
            prediction_data = get_fixture_prediction(fixture.id)
            prediction = None
            
            if prediction_data:
                prediction_payload = prediction_data.get("payload", {})
                prediction = {
                    "winner": prediction_payload.get("winner_name"),
                    "percent_home": prediction_payload.get("percent_home"),
                    "percent_draw": prediction_payload.get("percent_draw"),
                    "percent_away": prediction_payload.get("percent_away"),
                    "advice": prediction_payload.get("advice")
                }
            
            return {
                "match": f"{home.name} vs {away.name}",
                "date": fixture.date.strftime("%d/%m/%Y %H:%M") if fixture.date else "Date inconnue",
                "odds": processed_odds,
                "prediction": prediction
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des cotes pour {home_team} vs {away_team}: {str(e)}")
            return {"error": f"Erreur lors de la récupération des cotes: {str(e)}"}
        finally:
            session.close()
    
    @staticmethod
    async def get_high_confidence_bets(min_confidence: float = 0.6, limit: int = 20) -> Dict[str, Any]:
        """
        Récupère une liste de paris à haute confiance.
        
        Args:
            min_confidence: Seuil minimum de confiance (0.0 à 1.0)
            limit: Nombre maximum de paris à retourner
            
        Returns:
            Liste des paris à haute confiance
        """
        # Récupérer les matchs des 7 prochains jours
        high_confidence_bets = []
        
        for day_offset in range(7):
            target_date = date.today() + timedelta(days=day_offset)
            fixtures = search_fixtures_by_date(target_date)
            
            if not fixtures:
                continue
            
            session = get_db_session()
            try:
                for fixture in fixtures:
                    payload = fixture.get("payload", {})
                    fixture_id = payload.get("id")
                    
                    # Récupérer la prédiction
                    prediction_data = get_fixture_prediction(fixture_id)
                    if not prediction_data:
                        continue
                    
                    prediction_payload = prediction_data.get("payload", {})
                    
                    # Analyser la confiance
                    home_percent = float(prediction_payload.get("percent_home", "0").replace("%", "")) / 100
                    draw_percent = float(prediction_payload.get("percent_draw", "0").replace("%", "")) / 100
                    away_percent = float(prediction_payload.get("percent_away", "0").replace("%", "")) / 100
                    
                    max_confidence = max(home_percent, draw_percent, away_percent)
                    if max_confidence < min_confidence:
                        continue
                    
                    # Enrichir avec des informations sur le match
                    Team = get_model_by_entity_type('team')
                    League = get_model_by_entity_type('league')
                    
                    home_team = session.query(Team).filter(Team.id == payload.get("home_team_id")).first()
                    away_team = session.query(Team).filter(Team.id == payload.get("away_team_id")).first()
                    league = session.query(League).filter(League.id == payload.get("league_id")).first()
                    
                    match_time = datetime.fromisoformat(payload.get("date")) if payload.get("date") else None
                    
                    # Déterminer le résultat prédit
                    predicted_outcome = "draw"
                    if home_percent >= draw_percent and home_percent >= away_percent:
                        predicted_outcome = "home"
                    elif away_percent >= home_percent and away_percent >= draw_percent:
                        predicted_outcome = "away"
                    
                    # Récupérer la cote pour ce résultat
                    odds_data = get_fixture_odds(fixture_id)
                    best_odds = None
                    
                    if odds_data:
                        match_winner_odds = [odd for odd in odds_data if 
                                            odd.get("payload", {}).get("odds_type_id") == 1]  # 1 = Match Winner typiquement
                        
                        if match_winner_odds:
                            for odd in match_winner_odds:
                                odd_payload = odd.get("payload", {})
                                odds_value_id = odd_payload.get("odds_value_id")
                                
                                # Vérifier si cette cote correspond au résultat prédit
                                if ((predicted_outcome == "home" and odds_value_id == 1) or
                                    (predicted_outcome == "draw" and odds_value_id == 2) or
                                    (predicted_outcome == "away" and odds_value_id == 3)):
                                    
                                    if not best_odds or odd_payload.get("value", 0) > best_odds.get("value", 0):
                                        best_odds = {
                                            "value": odd_payload.get("value"),
                                            "bookmaker_id": odd_payload.get("bookmaker_id")
                                        }
                    
                    # Ajouter à la liste de paris
                    high_confidence_bet = {
                        "match_id": fixture_id,
                        "match": f"{home_team.name if home_team else 'Équipe 1'} vs {away_team.name if away_team else 'Équipe 2'}",
                        "league": league.name if league else "Ligue inconnue",
                        "date": match_time.strftime("%d/%m/%Y %H:%M") if match_time else "Date inconnue",
                        "prediction": {
                            "outcome": predicted_outcome,
                            "confidence": max_confidence,
                            "home_percent": f"{home_percent:.2%}",
                            "draw_percent": f"{draw_percent:.2%}",
                            "away_percent": f"{away_percent:.2%}"
                        },
                        "odds": best_odds.get("value") if best_odds else None
                    }
                    
                    high_confidence_bets.append(high_confidence_bet)
                    
                    # Arrêter si on a atteint la limite
                    if len(high_confidence_bets) >= limit:
                        break
            
            except Exception as e:
                logger.error(f"Erreur lors de la recherche de paris à haute confiance: {str(e)}")
            finally:
                session.close()
            
            # Arrêter si on a atteint la limite
            if len(high_confidence_bets) >= limit:
                break
        
        # Trier par confiance décroissante
        high_confidence_bets.sort(key=lambda x: x["prediction"]["confidence"], reverse=True)
        
        return {
            "count": len(high_confidence_bets),
            "min_confidence": f"{min_confidence:.0%}",
            "bets": high_confidence_bets[:limit]
        }
    
    @staticmethod
    async def generate_betting_combination(
        min_confidence: float = 0.6, 
        max_bets: int = 20
    ) -> Dict[str, Any]:
        """
        Génère une combinaison de paris à haute confiance.
        
        Args:
            min_confidence: Seuil minimum de confiance (0.0 à 1.0)
            max_bets: Nombre maximum de paris à inclure
            
        Returns:
            Combinaison de paris avec détails
        """
        # Récupérer les paris à haute confiance
        high_confidence_data = await BettingService.get_high_confidence_bets(
            min_confidence=min_confidence, 
            limit=max_bets
        )
        
        bets = high_confidence_data.get("bets", [])
        
        if not bets:
            return {
                "error": f"Aucun pari avec une confiance d'au moins {min_confidence:.0%} n'a été trouvé"
            }
        
        # Calculer les statistiques de la combinaison
        total_odds = 1.0
        for bet in bets:
            if bet.get("odds"):
                total_odds *= bet.get("odds")
        
        # Calculer le potentiel de gain pour une mise de 10€
        potential_winnings = 10.0 * total_odds
        
        return {
            "bets_count": len(bets),
            "total_odds": total_odds,
            "min_confidence": f"{min_confidence:.0%}",
            "potential_winnings": f"{potential_winnings:.2f}€ (pour une mise de 10€)",
            "bets": bets
        }