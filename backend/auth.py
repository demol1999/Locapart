from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import os
import secrets
import uuid

# Utilise une variable d'environnement pour la clé secrète
# Si pas définie, génère une clé aléatoire (pour dev seulement)
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    print("⚠️  ATTENTION: JWT_SECRET_KEY non définie, utilisation d'une clé temporaire")
    print(f"   Pour la production, définir: JWT_SECRET_KEY={SECRET_KEY}")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Réduit à 15 minutes pour plus de sécurité
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Réduit à 7 jours pour plus de sécurité

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_password_hash(password):
    """Hash un mot de passe avec bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password):
    """Vérifie un mot de passe contre son hash bcrypt"""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    # Utilise la valeur configurée ACCESS_TOKEN_EXPIRE_MINUTES par défaut
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        return None

def get_user_by_email(db: Session, email: str):
    return db.query(models.UserAuth).filter(models.UserAuth.email == email).first()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        session_id: str = payload.get("session_id")
        if email is None or session_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    
    # Vérifier que la session est toujours active
    session = db.query(models.UserSession).filter(
        models.UserSession.session_id == session_id,
        models.UserSession.user_id == user.id,
        models.UserSession.is_active == True,
        models.UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if session is None:
        raise credentials_exception
    
    # Mettre à jour la dernière activité
    session.last_activity = datetime.utcnow()
    db.commit()
    
    return user

def create_user_session(db: Session, user_id: int, user_agent: str = None, ip_address: str = None):
    # Invalider toutes les sessions existantes pour cet utilisateur (session unique)
    db.query(models.UserSession).filter(
        models.UserSession.user_id == user_id,
        models.UserSession.is_active == True
    ).update({"is_active": False})
    
    # Créer une nouvelle session
    session_id = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(user_id), "session_id": session_id})
    
    new_session = models.UserSession(
        user_id=user_id,
        session_id=session_id,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session

def invalidate_user_session(db: Session, session_id: str):
    session = db.query(models.UserSession).filter(
        models.UserSession.session_id == session_id
    ).first()
    if session:
        session.is_active = False
        db.commit()
    return session
