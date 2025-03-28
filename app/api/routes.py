"""
Configuration des routes de l'API pour le système RAG football.
Définit tous les endpoints disponibles regroupés par catégorie.
"""
from fastapi import APIRouter, Depends, Query, Path, HTTPException, BackgroundTasks, Request, status
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from app.api.dependencies.auth import get_current_user, get_admin_user
from app.api.dependencies.rate_limit import RateLimiter
from app.services.search_service import SearchService
from app.services.rag_service import RagService
from app.services.betting_service import BettingService
from app.services.indexation_service import IndexationService
from app.services.feedback_service import feedback_service
from app.db.qdrant.monitoring import get_collection_stats, check_qdrant_health
from app.monitoring.metrics import metrics
from app.models.user.user import User

# Router principal qui regroupera tous les autres routers
api_router = APIRouter()

# Router pour l'authentification
auth_router = APIRouter(prefix="/auth", tags=["Authentification"])

@auth_router.post("/login")
async def login(username: str, password: str):
    """
    Authentifie un utilisateur et retourne un token JWT.
    """
    # Logique d'authentification à implémenter
    return {"access_token": "dummy_token", "token_type": "bearer"}

@auth_router.post("/register")
async def register(username: str, email: str, password: str):
    """
    Inscrit un nouvel utilisateur.
    """
    # Logique d'inscription à implémenter
    return {"message": "Utilisateur inscrit avec succès"}

# Router pour les opérations RAG
rag_router = APIRouter(prefix="/rag", tags=["RAG"])

@rag_router.post("/ask", dependencies=[Depends(RateLimiter(requests_per_minute=10))])
async def ask_question(
    question: str, 
    max_context_items: int = Query(5, ge=1, le=20),
    use_reranking: bool = Query(True),
    use_cache: bool = Query(True),
    user: Optional[User] = Depends(get_current_user)
):
    """
    Répond à une question en utilisant le RAG sur la base de connaissances football.
    """
    # Générer un ID unique pour la question
    question_id = str(uuid.uuid4())
    
    result = await RagService.answer_question(
        question=question,
        max_context_items=max_context_items,
        use_reranking=use_reranking,
        use_cache=use_cache,
        user_id=user.id if user else None
    )
    
    # Ajouter les identifiants pour le feedback
    result["question_id"] = question_id
    result["response_id"] = str(uuid.uuid4())
    
    return result

@rag_router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_details(
    entity_type: str = Path(..., description="Type d'entité (team, player, league, etc.)"),
    entity_id: int = Path(..., description="ID de l'entité"),
    include_related: bool = Query(True, description="Inclure les entités liées")
):
    """
    Récupère les détails d'une entité spécifique et les entités associées.
    """
    result = await RagService.get_entity_details(
        entity_type=entity_type,
        entity_id=entity_id,
        include_related=include_related
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@rag_router.post("/analyze")
async def analyze_content(
    content: str,
    identify_entities: bool = Query(True),
    extract_facts: bool = Query(True)
):
    """
    Analyse un contenu textuel pour identifier les entités et extraire des faits.
    """
    result = await RagService.analyze_football_content(
        content=content,
        identify_entities=identify_entities,
        extract_facts=extract_facts
    )
    return result

@rag_router.get("/stats/{entity_type}/{entity_id}")
async def get_stats(
    entity_type: str = Path(..., description="Type d'entité (team, player, league)"),
    entity_id: int = Path(..., description="ID de l'entité"),
    stat_type: Optional[str] = Query(None, description="Type de statistique spécifique")
):
    """
    Récupère les statistiques liées au football pour une entité donnée.
    """
    if entity_type not in ['team', 'player', 'league']:
        raise HTTPException(status_code=400, detail="Type d'entité non supporté. Utilisez 'team', 'player', ou 'league'.")
    
    result = await RagService.get_football_stats(
        entity_type=entity_type,
        entity_id=entity_id,
        stat_type=stat_type
    )
    return result

# Router pour la recherche
search_router = APIRouter(prefix="/search", tags=["Recherche"])

@search_router.get("/")
async def search(
    query: str = Query(..., description="Texte de recherche"),
    entity_types: Optional[List[str]] = Query(None, description="Types d'entités à rechercher"),
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.7, ge=0, le=1.0)
):
    """
    Recherche des entités par texte en utilisant la recherche sémantique.
    """
    results = await SearchService.search_by_text(
        text=query,
        entity_types=entity_types,
        limit=limit,
        score_threshold=threshold
    )
    return results

@search_router.get("/advanced")
async def advanced_search(
    query: Optional[str] = Query(None, description="Texte de recherche (optionnel)"),
    entity_types: Optional[List[str]] = Query(None, description="Types d'entités à rechercher"),
    filters: Optional[Dict[str, Any]] = None,
    sort_by: Optional[str] = Query(None, description="Champ pour le tri"),
    sort_order: str = Query("desc", description="Ordre de tri ('asc' ou 'desc')"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    combine_results: bool = Query(True, description="Combiner les résultats de tous les types")
):
    """
    Recherche avancée avec filtres, tri et pagination.
    """
    results = await SearchService.advanced_search(
        text=query,
        entity_types=entity_types,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
        combine_results=combine_results
    )
    return results

@search_router.get("/similar/{entity_type}/{entity_id}")
async def get_similar_entities(
    entity_type: str = Path(..., description="Type de l'entité de référence"),
    entity_id: int = Path(..., description="ID de l'entité de référence"),
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.7, ge=0, le=1.0)
):
    """
    Trouve des entités similaires à une entité donnée.
    """
    results = await SearchService.get_similar_entities(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        score_threshold=threshold
    )
    return results

# Router pour les paris
betting_router = APIRouter(prefix="/betting", tags=["Paris"])

@betting_router.get("/matches-of-day")
async def get_matches_of_day(date: Optional[str] = None):
    """
    Récupère tous les matchs prévus pour une date spécifique.
    """
    from datetime import datetime, date as date_type
    
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD.")
    else:
        target_date = date_type.today()
    
    result = await BettingService.get_matches_of_day(target_date)
    return result

@betting_router.get("/next-match")
async def get_team_next_match(team_name: str):
    """
    Récupère le prochain match d'une équipe.
    """
    if not team_name:
        raise HTTPException(status_code=400, detail="Le nom de l'équipe est requis.")
    
    result = await BettingService.get_team_next_match(team_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Aucune équipe ou match trouvé pour '{team_name}'.")
    
    return result

@betting_router.get("/odds")
async def get_match_odds(home_team: str, away_team: str):
    """
    Récupère les cotes pour un match entre deux équipes.
    """
    if not home_team or not away_team:
        raise HTTPException(status_code=400, detail="Les noms des équipes à domicile et à l'extérieur sont requis.")
    
    result = await BettingService.get_match_odds(home_team, away_team)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@betting_router.get("/high-confidence-bets")
async def get_high_confidence_bets(
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Récupère une liste de paris à haute confiance.
    """
    result = await BettingService.get_high_confidence_bets(
        min_confidence=min_confidence,
        limit=limit
    )
    return result

@betting_router.get("/betting-combination")
async def generate_betting_combination(
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    max_bets: int = Query(20, ge=1, le=50)
):
    """
    Génère une combinaison de paris à haute confiance.
    """
    result = await BettingService.generate_betting_combination(
        min_confidence=min_confidence,
        max_bets=max_bets
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

# Router pour l'administration
admin_router = APIRouter(prefix="/admin", tags=["Administration"])

@admin_router.post("/indexation/{entity_type}", dependencies=[Depends(get_admin_user)])
async def index_entities(
    entity_type: str = Path(..., description="Type d'entité à indexer"),
    limit: int = Query(1000, ge=1),
    batch_size: int = Query(100, ge=1, le=500),
    background_tasks: BackgroundTasks = None
):
    """
    Indexe les entités d'un type spécifique dans Qdrant.
    """
    if background_tasks:
        # Exécution en arrière-plan pour les opérations longues
        background_tasks.add_task(
            IndexationService.index_entities_by_type,
            entity_type=entity_type,
            limit=limit,
            batch_size=batch_size
        )
        return {"status": "indexation_started", "message": f"Indexation de {entity_type} lancée en arrière-plan"}
    else:
        # Exécution synchrone pour les petites opérations
        result = await IndexationService.index_entities_by_type(
            entity_type=entity_type,
            limit=limit,
            batch_size=batch_size
        )
        return result

@admin_router.post("/indexation/all", dependencies=[Depends(get_admin_user)])
async def index_all_entities(
    batch_size: int = Query(100, ge=1, le=500),
    background_tasks: BackgroundTasks = None
):
    """
    Indexe toutes les entités de tous les types dans Qdrant.
    """
    # Cette opération est potentiellement longue, donc toujours en arrière-plan
    background_tasks.add_task(
        IndexationService.index_all_entities,
        batch_size=batch_size
    )
    return {"status": "indexation_started", "message": "Indexation complète lancée en arrière-plan"}

@admin_router.post("/incremental_update", dependencies=[Depends(get_admin_user)])
async def run_incremental_update(
    since_hours: int = Query(24, ge=1, le=168),
    batch_size: int = Query(100, ge=1, le=500),
    background_tasks: BackgroundTasks = None
):
    """
    Met à jour l'index de manière incrémentielle pour les entités modifiées récemment.
    """
    if background_tasks:
        background_tasks.add_task(
            IndexationService.incremental_update,
            since_hours=since_hours,
            batch_size=batch_size
        )
        return {"status": "update_started", "message": "Mise à jour incrémentielle lancée en arrière-plan"}
    else:
        result = await IndexationService.incremental_update(
            since_hours=since_hours,
            batch_size=batch_size
        )
        return result

@admin_router.get("/system/qdrant/status", dependencies=[Depends(get_admin_user)])
async def get_qdrant_status():
    """
    Vérifie l'état de santé de Qdrant.
    """
    health_status = check_qdrant_health()
    return health_status

@admin_router.get("/system/qdrant/collections", dependencies=[Depends(get_admin_user)])
async def get_qdrant_collections_stats():
    """
    Récupère les statistiques de toutes les collections Qdrant.
    """
    stats = get_collection_stats("all")
    return stats

@admin_router.get("/system/qdrant/collection/{collection_name}", dependencies=[Depends(get_admin_user)])
async def get_qdrant_collection_stats(collection_name: str):
    """
    Récupère les statistiques d'une collection Qdrant spécifique.
    """
    stats = get_collection_stats(collection_name)
    return stats

@admin_router.get("/system/metrics", dependencies=[Depends(get_admin_user)])
async def get_custom_metrics():
    """
    Récupère les métriques internes du système.
    """
    return metrics.get_metrics()

# Router pour le feedback utilisateur
feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])

@feedback_router.post("/")
async def submit_feedback(
    question_id: str,
    response_id: str,
    rating: int = Query(..., ge=1, le=5, description="Note de 1 à 5"),
    comment: Optional[str] = None,
    feedback_type: str = "general",
    user: Optional[User] = Depends(get_current_user)
):
    """
    Enregistre le feedback d'un utilisateur sur une réponse.
    """
    user_id = user.id if user else None
    
    result = await feedback_service.record_feedback(
        question_id=question_id,
        response_id=response_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
        feedback_type=feedback_type
    )
    
    return result

@feedback_router.get("/stats", dependencies=[Depends(get_admin_user)])
async def get_feedback_stats(
    period: str = Query("week", description="Période d'analyse (day, week, month, all)")
):
    """
    Récupère les statistiques sur les feedbacks.
    """
    if period not in ["day", "week", "month", "all"]:
        raise HTTPException(status_code=400, detail="Période invalide. Utilisez 'day', 'week', 'month' ou 'all'.")
    
    result = await feedback_service.get_feedback_stats(period)
    return result

# Router pour le monitoring
monitoring_router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@monitoring_router.get("/performance", dependencies=[Depends(get_admin_user)])
async def get_performance_metrics(
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    group_by: str = Query("endpoint", description="Groupement des métriques (endpoint, method, status_code)")
):
    """
    Récupère les métriques de performance du système.
    """
    # Récupérer les compteurs et histogrammes de métriques
    all_metrics = metrics.get_metrics()
    
    # Filtrer et formater les métriques de performance API
    api_metrics = {}
    
    for name, metric in all_metrics.items():
        if name.startswith("api_") or name.startswith("rag_") or name.startswith("search_"):
            api_metrics[name] = metric
    
    return {
        "period": {
            "from": from_time,
            "to": to_time
        },
        "group_by": group_by,
        "metrics": api_metrics
    }

@monitoring_router.get("/errors", dependencies=[Depends(get_admin_user)])
async def get_error_logs(
    severity: str = Query("error", description="Niveau de sévérité (warning, error, critical)"),
    limit: int = Query(50, ge=1, le=1000)
):
    """
    Récupère les logs d'erreurs récents.
    """
    # Dans une implémentation réelle, ceci récupérerait les logs depuis un stockage
    # Pour cette démo, nous retournons une structure factice
    return {
        "severity": severity,
        "count": 0,
        "errors": []
    }

@monitoring_router.get("/system-health", dependencies=[Depends(get_admin_user)])
async def get_system_health():
    """
    Vérifie l'état de santé de tous les composants du système.
    """
    from app.monitoring.healthcheck import health_check
    
    health_status = await health_check.check_system_health()
    return health_status

# Intégrer tous les routers dans le router principal
api_router.include_router(auth_router)
api_router.include_router(rag_router)
api_router.include_router(search_router)
api_router.include_router(betting_router)
api_router.include_router(admin_router)
api_router.include_router(feedback_router)
api_router.include_router(monitoring_router)

# Route de base pour tester que l'API fonctionne
@api_router.get("/", tags=["Base"])
async def root():
    """
    Route racine pour vérifier que l'API est fonctionnelle.
    """
    return {
        "message": "API football RAG opérationnelle",
        "version": "1.0.0",
        "documentation": "/docs"
    }