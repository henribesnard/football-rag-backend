"""
Dépendances pour la limitation de débit des requêtes API.
"""
import time
import redis
from fastapi import Depends, HTTPException, Request, status
from typing import Optional, Dict, Any, List

from app.config import settings
from app.api.dependencies.auth import get_current_user
from app.models.user.user import User

# Connexion Redis (utilisée pour stocker les compteurs de limitation de débit)
redis_client = redis.Redis.from_url(
    settings.REDIS_URL, 
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

class RateLimiter:
    """
    Dépendance pour limiter le nombre de requêtes par utilisateur ou par IP.
    """
    
    def __init__(
        self, 
        requests_per_minute: int = 60,
        burst: int = 5,
        exempted_roles: Optional[List[str]] = None
    ):
        """
        Initialise le limiteur de débit.
        
        Args:
            requests_per_minute: Nombre de requêtes autorisées par minute
            burst: Nombre de requêtes supplémentaires autorisées en rafale
            exempted_roles: Liste des noms de rôles exemptés de limitation
        """
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.exempted_roles = exempted_roles or ["admin", "premium"]
        self.window_seconds = 60  # Fenêtre d'une minute
        
    async def __call__(
        self, 
        request: Request, 
        user: Optional[User] = Depends(get_current_user, use_cache=False)
    ) -> None:
        """
        Applique la limitation de débit.
        
        Args:
            request: L'objet requête FastAPI
            user: L'utilisateur authentifié (optionnel)
            
        Raises:
            HTTPException: Si la limite de débit est dépassée
        """
        # Si l'utilisateur est authentifié et a un rôle exempté, ne pas appliquer la limitation
        if user:
            user_roles = [role.name for role in user.roles]
            if any(role in self.exempted_roles for role in user_roles):
                return
            
            # Clé Redis basée sur l'ID utilisateur pour les utilisateurs authentifiés
            key = f"rate_limit:{user.id}"
        else:
            # Clé Redis basée sur l'adresse IP pour les utilisateurs non authentifiés
            client_ip = request.client.host
            key = f"rate_limit:{client_ip}"
        
        # Timestamping actuel en secondes
        current_time = int(time.time())
        
        # Implémentation du Token Bucket Algorithm
        # 1. Vérifier si une entrée existe pour cet utilisateur/IP
        if not redis_client.exists(key):
            # Initialiser avec le maximum de tokens
            pipe = redis_client.pipeline()
            pipe.hset(key, "tokens", self.requests_per_minute)
            pipe.hset(key, "last_request", current_time)
            pipe.expire(key, self.window_seconds * 2)  # Durée de vie de la clé: 2 minutes
            pipe.execute()
            return
        
        # 2. Récupérer les informations actuelles
        tokens = float(redis_client.hget(key, "tokens") or 0)
        last_request = int(redis_client.hget(key, "last_request") or 0)
        
        # 3. Calculer le nombre de tokens à ajouter (basé sur le temps écoulé)
        elapsed = current_time - last_request
        tokens_to_add = elapsed * (self.requests_per_minute / self.window_seconds)
        
        # 4. Mettre à jour le nombre de tokens (maximum: requests_per_minute + burst)
        new_tokens = min(tokens + tokens_to_add, self.requests_per_minute + self.burst)
        
        # 5. Si nous avons au moins un token, consommer un token et autoriser la requête
        if new_tokens >= 1:
            # Mettre à jour les valeurs dans Redis
            pipe = redis_client.pipeline()
            pipe.hset(key, "tokens", new_tokens - 1)  # Consommer un token
            pipe.hset(key, "last_request", current_time)
            pipe.expire(key, self.window_seconds * 2)  # Réinitialiser le TTL à 2 minutes
            pipe.execute()
            return
        
        # 6. Si nous n'avons pas assez de tokens, refuser la requête
        retry_after = int((1 - new_tokens) * self.window_seconds / self.requests_per_minute)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de requêtes. Veuillez réessayer dans {retry_after} secondes.",
            headers={"Retry-After": str(retry_after)}
        )