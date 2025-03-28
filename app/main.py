"""
Point d'entrée principal de l'application Flask API avec RAG et CDC.
"""
import logging
import os
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

from app.config import settings
from app.api.routes import api_router
from app.db.qdrant.collections import initialize_collections
from app.cdc import get_cdc_manager
from app.monitoring.metrics import metrics
from app.monitoring.logger import configure_logging, get_logger
from app.monitoring.healthcheck import health_check
from app.services.cache_service import cache_service

# Configuration du logging structuré
configure_logging()
logger = get_logger(__name__)

# Métriques globales
request_latency = metrics.histogram(
    "api_request_latency",
    "Temps de réponse des requêtes API (secondes)",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)

request_count = metrics.counter(
    "api_requests_total",
    "Nombre total de requêtes API",
    ["method", "endpoint", "status_code"]
)

# Contexte de démarrage/arrêt pour FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application FastAPI.
    Ce contexte est exécuté au démarrage et à l'arrêt de l'application.
    """
    # Initialisation des composants au démarrage
    logger.info("🚀 Démarrage de l'application")
    
    # Initialiser les collections Qdrant
    try:
        initialize_collections()
        logger.info("✅ Collections Qdrant initialisées")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation des collections Qdrant: {str(e)}")
    
    # Préchauffer le cache si nécessaire
    if settings.CACHE_WARMUP_ENABLED:
        try:
            await cache_service.warmup()
            logger.info("✅ Cache préchauffé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur lors du préchauffage du cache: {str(e)}")
    
    # Démarrer automatiquement le CDC si configuré ainsi
    if settings.CDC_ENABLED and settings.get("CDC_AUTO_START", False):
        try:
            cdc_manager = get_cdc_manager()
            if not cdc_manager.is_running:
                logger.info("▶️ Démarrage automatique du système CDC")
                # Démarrer en arrière-plan pour ne pas bloquer le démarrage de l'app
                background_task = BackgroundTasks()
                background_task.add_task(cdc_manager.start)
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du CDC: {str(e)}")
    
    # Vérifier la santé des composants
    try:
        health_status = await health_check.check_system_health()
        if health_status["status"] != "healthy":
            logger.warning(f"⚠️ Démarrage avec état de santé non optimal: {health_status['status']}")
            logger.debug(f"Détails de santé: {health_status}")
        else:
            logger.info("✅ Vérification de santé initiale réussie")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification de santé initiale: {str(e)}")
    
    # Ressources prêtes, continuer avec le démarrage de FastAPI
    yield
    
    # Nettoyage des ressources à l'arrêt
    logger.info("🛑 Arrêt de l'application")
    
    # Arrêter proprement le CDC si en cours d'exécution
    try:
        cdc_manager = get_cdc_manager()
        if cdc_manager.is_running:
            logger.info("⏹️ Arrêt du système CDC")
            cdc_manager.stop()
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'arrêt du CDC: {str(e)}")

# Middleware pour mesurer la latence des requêtes et collecter des métriques
async def metrics_middleware(request: Request, call_next):
    """
    Middleware pour mesurer la latence des requêtes et collecter des métriques.
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        # Enregistrer les métriques
        request_latency.observe(processing_time)
        status_code = response.status_code
        
        # Ajouter l'en-tête X-Processing-Time
        response.headers["X-Processing-Time"] = f"{processing_time:.6f}"
        
    except Exception as e:
        processing_time = time.time() - start_time
        request_latency.observe(processing_time)
        status_code = 500
        # Créer une réponse d'erreur
        response = Response(
            content=f"Internal Server Error: {str(e)}",
            status_code=status_code
        )
        logger.error(f"Erreur non interceptée dans le traitement de la requête: {str(e)}")
    
    # Format de l'endpoint pour les métriques (simplifier les chemins variables)
    path = request.url.path
    for param in request.path_params:
        path = path.replace(str(request.path_params[param]), f"{{{param}}}")
    
    # Incrémenter le compteur de requêtes
    request_count.labels(
        method=request.method,
        endpoint=path,
        status_code=status_code
    ).inc()
    
    return response

# Créer l'application FastAPI avec le contexte de cycle de vie
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API RAG pour les données de football avec CDC pour la synchronisation des données",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Désactiver Swagger en production si nécessaire
    redoc_url="/redoc" if settings.DEBUG else None
)

# Ajouter le middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajouter le middleware GZip pour la compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Ajouter le middleware de métriques
app.middleware("http")(metrics_middleware)

# Inclure les routes de l'API
app.include_router(api_router)

# Point d'extrémité pour gérer le CDC
@app.post("/api/admin/cdc/start", tags=["admin"])
async def start_cdc(background_tasks: BackgroundTasks):
    """Démarre le système CDC en tâche d'arrière-plan."""
    if not settings.CDC_ENABLED:
        raise HTTPException(status_code=400, detail="CDC is disabled in configuration")
    
    cdc_manager = get_cdc_manager()
    if cdc_manager.is_running:
        return {"status": "already_running", "message": "CDC system is already running"}
    
    # Démarrer le CDC en arrière-plan
    background_tasks.add_task(cdc_manager.start)
    return {"status": "starting", "message": "CDC system is starting in the background"}

@app.post("/api/admin/cdc/stop", tags=["admin"])
async def stop_cdc():
    """Arrête le système CDC."""
    cdc_manager = get_cdc_manager()
    if not cdc_manager.is_running:
        return {"status": "not_running", "message": "CDC system is not running"}
    
    cdc_manager.stop()
    return {"status": "stopped", "message": "CDC system has been stopped"}

@app.get("/api/admin/cdc/status", tags=["admin"])
async def cdc_status():
    """Obtient le statut actuel du système CDC."""
    cdc_manager = get_cdc_manager()
    return cdc_manager.get_status()

@app.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """Endpoint pour exposer les métriques au format Prometheus."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, Gauge
    
    registry = CollectorRegistry()
    
    # Convertir nos métriques personnalisées au format Prometheus
    # Compteurs
    for name, counter in metrics.counters.items():
        c = Counter(name, counter.description, counter.labels.keys() if hasattr(counter, 'labels') else [], registry=registry)
        c._value.set(counter.value)
    
    # Histogrammes
    for name, histogram in metrics.histograms.items():
        h = Histogram(name, histogram.description, histogram.labels.keys() if hasattr(histogram, 'labels') else [], buckets=histogram.buckets, registry=registry)
        # Pour simplifier, nous ne remplissons pas les buckets ici
        for value in histogram.values:
            h.observe(value)
    
    # Jauges
    for name, gauge in metrics.gauges.items():
        g = Gauge(name, gauge.description, gauge.labels.keys() if hasattr(gauge, 'labels') else [], registry=registry)
        g.set(gauge.value)
    
    # Générer les métriques au format Prometheus
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

# Point d'extrémité pour la vérification de santé
@app.get("/health", tags=["monitoring"])
async def health():
    """
    Endpoint de vérification de santé pour le monitoring.
    Retourne l'état de santé de tous les composants du système.
    """
    health_status = await health_check.check_system_health()
    
    # Déterminer le code de statut HTTP en fonction de l'état de santé
    if health_status["status"] == "healthy":
        status_code = 200
    elif health_status["status"] == "degraded":
        status_code = 200  # Toujours 200 pour degraded pour éviter les faux positifs
    else:
        status_code = 503  # Service Unavailable
    
    return Response(
        content=json.dumps(health_status),
        media_type="application/json",
        status_code=status_code
    )

# Point d'extrémité pour un check de vie simple
@app.get("/ping", tags=["monitoring"])
async def ping():
    """
    Simple check de vie pour vérifier que l'API répond.
    """
    return {"status": "ok", "timestamp": time.time()}

# Point d'extrémité racine
@app.get("/", tags=["Base"])
async def root():
    """
    Route racine pour vérifier que l'API est fonctionnelle.
    """
    return {
        "message": "API football RAG opérationnelle",
        "version": settings.APP_VERSION,
        "documentation": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

# Configuration du serveur ASGI pour haute disponibilité
def start_server():
    """Démarre le serveur avec les paramètres de configuration optimisés."""
    # Configuration uvicorn pour haute disponibilité
    uvicorn_config = {
        "host": settings.HOST,
        "port": settings.PORT,
        "log_level": "info",
        "workers": settings.WORKERS,  # Nombre de processus de travail
        "loop": "uvloop",  # Boucle d'événements plus rapide
        "http": "httptools",  # Parser HTTP plus rapide
        "limit_concurrency": settings.MAX_CONCURRENT_CONNECTIONS,  # Limite de connexions simultanées
        "timeout_keep_alive": 5,  # Durée de maintien des connexions inactives
        "proxy_headers": True,  # Support des en-têtes de proxy
        "forwarded_allow_ips": settings.FORWARDED_ALLOW_IPS,  # IPs autorisées pour les en-têtes X-Forwarded-*
    }
    
    # Démarrer le serveur
    uvicorn.run("app.main:app", **uvicorn_config)

if __name__ == "__main__":
    # Importer ici pour éviter les problèmes d'importation circulaire
    import json
    from fastapi import Response
    start_server()