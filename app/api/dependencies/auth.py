"""
Dépendances pour la gestion de l'authentification et l'autorisation dans l'API.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional

from app.config import settings
from app.models.user.user import User
from app.db.postgres.connection import get_db
from sqlalchemy.orm import Session

# Configuration du schéma OAuth2 pour la récupération du token depuis les requêtes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def decode_token(token: str) -> dict:
    """
    Décode et vérifie un token JWT.
    
    Args:
        token: Le token JWT à décoder
        
    Returns:
        Données contenues dans le token
        
    Raises:
        HTTPException: Si le token est invalide ou expiré
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Récupère l'utilisateur actuel à partir du token JWT.
    
    Args:
        token: Le token JWT d'authentification
        db: Session de base de données
        
    Returns:
        L'instance de l'utilisateur authentifié
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas trouvé ou si le token est invalide
    """
    payload = decode_token(token)
    user_id: Optional[int] = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Récupérer l'utilisateur depuis la base de données
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif",
        )
    
    return user

def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """
    Vérifie que l'utilisateur actuel est un administrateur.
    
    Args:
        user: L'instance de l'utilisateur authentifié
        
    Returns:
        L'instance de l'utilisateur administrateur
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas un administrateur
    """
    # Vérifier si l'utilisateur a un rôle d'administrateur
    is_admin = any(role.name == "admin" for role in user.roles)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis",
        )
    
    return user