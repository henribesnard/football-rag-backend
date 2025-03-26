"""
Point d'entrée principal de l'application Flask API avec RAG et CDC.
"""
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import api_router
from app.db.qdrant.collections import initialize_collections
from app.cdc import get_cdc_manager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API RAG pour les données de football avec CDC pour la synchronisation des données"
)

# Ajouter le middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À modifier pour la production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.on_event("startup")
async def startup_event():
    """Exécuté au démarrage de l'application."""
    # Initialiser les collections Qdrant
    initialize_collections()
    logger.info("Collections Qdrant initialisées")
    
    # Démarrer automatiquement le CDC si configuré ainsi
    if settings.CDC_ENABLED and settings.get("CDC_AUTO_START", False):
        cdc_manager = get_cdc_manager()
        if not cdc_manager.is_running:
            logger.info("Démarrage automatique du système CDC")
            # Démarrer en arrière-plan pour ne pas bloquer le démarrage de l'app
            background_task = BackgroundTasks()
            background_task.add_task(cdc_manager.start)

@app.on_event("shutdown")
async def shutdown_event():
    """Exécuté à l'arrêt de l'application."""
    # Arrêter proprement le CDC si en cours d'exécution
    cdc_manager = get_cdc_manager()
    if cdc_manager.is_running:
        logger.info("Arrêt du système CDC")
        cdc_manager.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)