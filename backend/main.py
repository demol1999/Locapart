from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError
from pydantic import ValidationError
from database import engine, get_db, SessionLocal
import models
from auth import (
    get_password_hash, verify_password, create_access_token, get_current_user,
    create_user_session, verify_refresh_token, invalidate_user_session
)
from models import UserAuth
from audit_logger import AuditLogger, get_model_data
from middleware import AuditMiddleware
from oauth_service import OAuthProviderFactory, OAuthAuthenticationService
from validation_middleware import validation_exception_handler, request_validation_exception_handler, general_exception_handler, ValidationErrorHandler
from rate_limiter import check_rate_limit
from apartment_limit_middleware import check_apartment_limit, get_apartment_limit_info
import stripe_routes
import room_routes
import photo_routes
import floor_plan_routes
import tenant_routes
import lease_routes
import document_routes
import tenant_portal_routes
import tenant_invitation_routes
import detailed_inventory_routes
import lease_generation_routes
import property_management_routes
import email_verification_routes
from routes_admin_simple import admin_router
from routes_audit_undo import audit_undo_router
import schemas
import os
import shutil
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Ajout des gestionnaires d'exceptions de validation
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(IntegrityError, general_exception_handler)
app.add_exception_handler(DataError, general_exception_handler)

from fastapi.middleware.cors import CORSMiddleware

# Ajouter le middleware de logging d'audit
app.add_middleware(AuditMiddleware)

# Middleware de sécurité
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Headers de sécurité
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # CSP pour éviter les injections XSS
    if not request.url.path.startswith("/uploads"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:52388",
        "http://127.0.0.1:52388",
        "file://",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", 
        "Content-Type", 
        "Accept", 
        "Origin", 
        "X-Requested-With"
    ],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Route sécurisée pour les uploads avec vérification d'autorisation
@app.get("/uploads/{file_path:path}")
async def get_upload_file(
    file_path: str, 
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accès sécurisé aux fichiers uploadés avec vérification des permissions"""
    from fastapi.responses import FileResponse
    import os
    
    # Chemin complet du fichier
    full_path = os.path.join(UPLOAD_DIR, file_path)
    
    # Vérifier que le fichier existe
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    # Vérifier les permissions selon le chemin
    if "/buildings/" in file_path:
        # Extraire l'ID du building du chemin
        parts = file_path.split("/")
        if len(parts) >= 2 and parts[0] == "buildings":
            try:
                building_id = int(parts[1])
                
                # Vérifier si l'utilisateur a accès à ce building
                from models import ApartmentUserLink, Apartment
                user_has_access = db.query(ApartmentUserLink).join(Apartment).filter(
                    ApartmentUserLink.user_id == current_user.id,
                    Apartment.building_id == building_id
                ).first()
                
                if not user_has_access:
                    raise HTTPException(status_code=403, detail="Accès non autorisé à ce fichier")
                    
            except ValueError:
                raise HTTPException(status_code=400, detail="ID de building invalide")
    else:
        # Pour les autres fichiers, vérifier que c'est l'utilisateur qui l'a uploadé
        # (basé sur le nom du fichier contenant l'user_id)
        filename = os.path.basename(file_path)
        if f"_{current_user.id}_" not in filename and not filename.startswith(f"user_{current_user.id}_"):
            raise HTTPException(status_code=403, detail="Accès non autorisé à ce fichier")
    
    return FileResponse(full_path)


# ---------------------- AUTH ----------------------
@app.post("/signup/", response_model=schemas.UserOut)
async def signup(
    user: schemas.UserCreate, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("signup"))
):
    try:
        # Vérifier si l'email existe déjà
        existing_user = db.query(models.UserAuth).filter(models.UserAuth.email == user.email).first()
        if existing_user:
            # Log de tentative d'inscription avec email existant
            AuditLogger.log_error(
                db=db,
                description=f"Tentative d'inscription avec email existant: {user.email}",
                error_details="Email déjà utilisé",
                request=request,
                status_code=400
            )
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        
        # Créer l'utilisateur
        hashed_password = get_password_hash(user.password)
        user_obj = models.UserAuth(
            email=user.email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            street_number=user.street_number,
            street_name=user.street_name,
            complement=user.complement,
            postal_code=user.postal_code,
            city=user.city,
            country=user.country
        )
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)
        
    except IntegrityError as e:
        db.rollback()
        error_response = ValidationErrorHandler.format_database_error(e)
        AuditLogger.log_error(
            db=db,
            description=f"Erreur d'intégrité lors de l'inscription: {user.email}",
            error_details=str(e),
            request=request,
            status_code=400
        )
        raise HTTPException(status_code=400, detail=error_response['detail'])
    
    except DataError as e:
        db.rollback()
        error_response = ValidationErrorHandler.format_database_error(e)
        AuditLogger.log_error(
            db=db,
            description=f"Erreur de données lors de l'inscription: {user.email}",
            error_details=str(e),
            request=request,
            status_code=400
        )
        raise HTTPException(status_code=400, detail=error_response['detail'])
    
    # Log de création d'utilisateur
    AuditLogger.log_crud_action(
        db=db,
        action=models.ActionType.CREATE,
        entity_type=models.EntityType.USER,
        entity_id=user_obj.id,
        user_id=user_obj.id,
        description=f"Inscription d'un nouvel utilisateur: {user_obj.email}",
        after_data=get_model_data(user_obj),
        request=request
    )
    
    # Envoyer automatiquement l'email de vérification pour les comptes email/password
    if user_obj.auth_type == models.AuthType.EMAIL_PASSWORD:
        try:
            from email_verification_service import create_verification_service
            verification_service = create_verification_service(db)
            
            # Récupérer les infos de la requête
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
            # Envoyer l'email de vérification en arrière-plan
            async def send_verification_task():
                try:
                    await verification_service.send_verification_email(
                        user_id=user_obj.id,
                        email=user_obj.email,
                        user_name=f"{user_obj.first_name} {user_obj.last_name}",
                        ip_address=client_ip,
                        user_agent=user_agent
                    )
                except Exception as e:
                    # Logger l'erreur mais ne pas faire échouer l'inscription
                    AuditLogger.log_error(
                        db=db,
                        description=f"Erreur envoi email vérification lors inscription: {user_obj.email}",
                        error_details=str(e),
                        request=request,
                        status_code=500
                    )
            
            # Ajouter la tâche aux tâches d'arrière-plan
            background_tasks.add_task(send_verification_task)
            
        except Exception as e:
            # Ne pas faire échouer l'inscription si l'email ne peut pas être envoyé
            AuditLogger.log_error(
                db=db,
                description=f"Erreur configuration email vérification lors inscription: {user_obj.email}",
                error_details=str(e),
                request=request,
                status_code=500
            )
    
    return user_obj


@app.post("/login/")
def login(
    request: Request, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("login"))
):
    user = db.query(models.UserAuth).filter(models.UserAuth.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log de tentative de connexion échouée
        AuditLogger.log_error(
            db=db,
            description=f"Tentative de connexion échouée pour: {form_data.username}",
            error_details="Identifiants invalides",
            request=request,
            status_code=401
        )
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    
    # Récupérer les informations de la requête
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None
    
    # Créer une nouvelle session (invalide automatiquement les autres)
    session = create_user_session(db, user.id, user_agent, client_ip)
    
    # Créer l'access token avec session_id
    access_token = create_access_token(data={
        "sub": user.email, 
        "session_id": session.session_id
    })
    
    # Log de connexion réussie
    AuditLogger.log_auth_action(
        db=db,
        action=models.ActionType.LOGIN,
        user_id=user.id,
        description=f"Connexion réussie pour: {user.email}",
        request=request,
        details={
            "session_id": session.session_id,
            "user_agent": user_agent,
            "ip_address": client_ip
        }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60  # 30 minutes en secondes
    }


@app.post("/refresh/")
def refresh_token(request: Request, refresh_token: str = Form(...), db: Session = Depends(get_db)):
    # Vérifier le refresh token
    payload = verify_refresh_token(refresh_token)
    if not payload:
        AuditLogger.log_error(
            db=db,
            description="Tentative de refresh avec token invalide",
            error_details="Refresh token invalide",
            request=request,
            status_code=401
        )
        raise HTTPException(status_code=401, detail="Refresh token invalide")
    
    session_id = payload.get("session_id")
    user_id = payload.get("sub")
    
    # Vérifier que la session existe et est active
    session = db.query(models.UserSession).filter(
        models.UserSession.session_id == session_id,
        models.UserSession.user_id == int(user_id),
        models.UserSession.is_active == True,
        models.UserSession.refresh_token == refresh_token
    ).first()
    
    if not session:
        AuditLogger.log_error(
            db=db,
            description=f"Tentative de refresh avec session invalide: {session_id}",
            error_details="Session invalide",
            request=request,
            status_code=401
        )
        raise HTTPException(status_code=401, detail="Session invalide")
    
    # Récupérer l'utilisateur
    user = db.query(models.UserAuth).filter(models.UserAuth.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    
    # Créer un nouveau access token
    new_access_token = create_access_token(data={
        "sub": user.email,
        "session_id": session_id
    })
    
    # Mettre à jour la dernière activité
    session.last_activity = datetime.utcnow()
    db.commit()
    
    # Log du refresh token
    AuditLogger.log_auth_action(
        db=db,
        action=models.ActionType.REFRESH_TOKEN,
        user_id=user.id,
        description=f"Refresh token pour: {user.email}",
        request=request,
        details={"session_id": session_id}
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60
    }

@app.post("/logout/")
def logout(request: Request, current_user: models.UserAuth = Depends(get_current_user), db: Session = Depends(get_db)):
    # Invalider toutes les sessions de l'utilisateur
    active_sessions = db.query(models.UserSession).filter(
        models.UserSession.user_id == current_user.id,
        models.UserSession.is_active == True
    ).count()
    
    db.query(models.UserSession).filter(
        models.UserSession.user_id == current_user.id,
        models.UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()
    
    # Log de déconnexion
    AuditLogger.log_auth_action(
        db=db,
        action=models.ActionType.LOGOUT,
        user_id=current_user.id,
        description=f"Déconnexion de: {current_user.email}",
        request=request,
        details={"sessions_invalidated": active_sessions}
    )
    
    return {"message": "Déconnexion réussie"}

# ---------------------- OAUTH AUTHENTICATION ----------------------


@app.get("/auth/{provider}/login")
def oauth_login(provider: str, request: Request):
    """
    Initie le processus OAuth pour un provider donné
    Suit le principe Single Responsibility
    """
    try:
        oauth_provider = OAuthProviderFactory.get_provider(provider)
        
        # URL de redirection après authentification
        redirect_uri = f"{request.base_url}auth/{provider}/callback"
        
        # Générer l'URL d'autorisation
        authorization_url, state = oauth_provider.get_authorization_url(str(redirect_uri))
        
        # Stocker l'état en session (ou en cache Redis en production)
        # Pour simplifier, on retourne juste l'URL
        return {
            "authorization_url": authorization_url,
            "state": state
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        AuditLogger.log_error(
            db=SessionLocal(),
            description=f"Erreur lors de l'initiation OAuth {provider}",
            error_details=str(e),
            request=request
        )
        raise HTTPException(status_code=500, detail="Erreur serveur")

@app.get("/auth/{provider}/callback")
def oauth_callback(provider: str, code: str, request: Request, db: Session = Depends(get_db)):
    """
    Gère le callback OAuth après autorisation
    Suit le principe de responsabilité unique
    """
    try:
        # Créer le provider OAuth
        oauth_provider = OAuthProviderFactory.get_provider(provider)
        
        # Créer le service d'authentification
        auth_service = OAuthAuthenticationService(db, oauth_provider)
        
        # URL de redirection (même que celle utilisée pour l'autorisation)
        redirect_uri = f"{request.base_url}auth/{provider}/callback"
        
        # Authentifier l'utilisateur
        user = auth_service.authenticate_user(code, str(redirect_uri), request)
        
        # Récupérer les informations de la requête
        user_agent = request.headers.get("user-agent")
        client_ip = request.client.host if request.client else None
        
        # Créer une nouvelle session (invalide automatiquement les autres - Session unique)
        session = create_user_session(db, user.id, user_agent, client_ip)
        
        # Créer l'access token avec session_id
        access_token = create_access_token(data={
            "sub": user.email,
            "session_id": session.session_id
        })
        
        return {
            "access_token": access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "expires_in": 30 * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "auth_type": user.auth_type,
                "avatar_url": user.oauth_avatar_url
            }
        }
        
    except ValueError as e:
        # Erreur de validation
        AuditLogger.log_error(
            db=db,
            description=f"Erreur de validation OAuth {provider}",
            error_details=str(e),
            request=request
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Erreur serveur
        AuditLogger.log_error(
            db=db,
            description=f"Erreur serveur OAuth {provider}",
            error_details=str(e),
            request=request
        )
        raise HTTPException(status_code=500, detail="Erreur lors de l'authentification OAuth")

# ---------------------- USER PROFILE ----------------------
@app.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.UserAuth = Depends(get_current_user)):
    return current_user

# ---------------------- DEVELOPMENT ENDPOINTS ----------------------

@app.delete("/dev/reset-users")
def dev_reset_all_users(request: Request, db: Session = Depends(get_db)):
    """
    ENDPOINT DE DÉVELOPPEMENT UNIQUEMENT
    Supprime tous les utilisateurs, sessions et logs d'audit pour les tests
    """
    # Vérifier qu'on est en mode développement
    environment = os.getenv("ENVIRONMENT", "production")
    if environment != "development":
        raise HTTPException(status_code=403, detail="Endpoint disponible uniquement en mode développement")
    
    try:
        # Compter les utilisateurs avant suppression
        user_count = db.query(models.UserAuth).count()
        session_count = db.query(models.UserSession).count()
        audit_count = db.query(models.AuditLog).count()
        
        # Supprimer toutes les sessions utilisateur
        db.query(models.UserSession).delete()
        
        # Supprimer tous les logs d'audit
        db.query(models.AuditLog).delete()
        
        # Supprimer tous les liens appartement-utilisateur
        db.query(models.ApartmentUserLink).delete()
        
        # Supprimer tous les utilisateurs
        db.query(models.UserAuth).delete()
        
        db.commit()
        
        # Log de l'action de reset
        AuditLogger.log_crud_action(
            db=db,
            action=models.ActionType.DELETE,
            entity_type=models.EntityType.USER,
            entity_id=None,
            user_id=None,
            description=f"RESET DÉVELOPPEMENT: {user_count} utilisateurs, {session_count} sessions, {audit_count} logs supprimés",
            request=request
        )
        
        return {
            "message": "Base de données réinitialisée avec succès",
            "deleted": {
                "users": user_count,
                "sessions": session_count,
                "audit_logs": audit_count
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors du reset: {str(e)}")

@app.get("/dev/stats")
def dev_get_stats(db: Session = Depends(get_db)):
    """
    ENDPOINT DE DÉVELOPPEMENT UNIQUEMENT  
    Affiche les statistiques de la base de données
    """
    # Vérifier qu'on est en mode développement
    environment = os.getenv("ENVIRONMENT", "production")
    if environment != "development":
        raise HTTPException(status_code=403, detail="Endpoint disponible uniquement en mode développement")
    
    return {
        "users": db.query(models.UserAuth).count(),
        "sessions": db.query(models.UserSession).count(),
        "audit_logs": db.query(models.AuditLog).count(),
        "buildings": db.query(models.Building).count(),
        "apartments": db.query(models.Apartment).count(),
        "copros": db.query(models.Copro).count(),
        "syndicats": db.query(models.SyndicatCopro).count(),
        "photos": db.query(models.Photo).count()
    }

# ---------------------- COPROPRIÉTÉS ----------------------

@app.post("/copros/", response_model=schemas.CoproOut)
def create_copro(copro: schemas.CoproCreate, request: Request, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro_obj = models.Copro(**copro.dict())
    db.add(copro_obj)
    db.commit()
    db.refresh(copro_obj)
    
    # Log de création de copropriété
    AuditLogger.log_crud_action(
        db=db,
        action=models.ActionType.CREATE,
        entity_type=models.EntityType.COPRO,
        entity_id=copro_obj.id,
        user_id=current_user.id,
        description=f"Création de la copropriété: {copro_obj.nom or f'ID {copro_obj.id}'}",
        after_data=get_model_data(copro_obj),
        request=request
    )
    
    return copro_obj

@app.get("/copros/", response_model=List[schemas.CoproOut])
def list_copros(db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    return db.query(models.Copro).all()

@app.get("/copros/{copro_id}", response_model=schemas.CoproOut)
def get_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro = db.query(models.Copro).filter(models.Copro.id == copro_id).first()
    if not copro:
        raise HTTPException(status_code=404, detail="Copropriété introuvable")
    return copro

@app.put("/copros/{copro_id}", response_model=schemas.CoproOut)
def update_copro(copro_id: int, copro: schemas.CoproUpdate, request: Request, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro_obj = db.query(models.Copro).filter(models.Copro.id == copro_id).first()
    if not copro_obj:
        raise HTTPException(status_code=404, detail="Copropriété introuvable")
    
    # Sauvegarder les données avant modification pour le log
    before_data = get_model_data(copro_obj)
    
    for key, value in copro.dict(exclude_unset=True).items():
        setattr(copro_obj, key, value)
    db.commit()
    db.refresh(copro_obj)
    
    # Log de modification de copropriété
    AuditLogger.log_crud_action(
        db=db,
        action=models.ActionType.UPDATE,
        entity_type=models.EntityType.COPRO,
        entity_id=copro_obj.id,
        user_id=current_user.id,
        description=f"Modification de la copropriété: {copro_obj.nom or f'ID {copro_obj.id}'}",
        before_data=before_data,
        after_data=get_model_data(copro_obj),
        request=request
    )
    
    return copro_obj

@app.delete("/copros/{copro_id}")
def delete_copro(copro_id: int, request: Request, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro_obj = db.query(models.Copro).filter(models.Copro.id == copro_id).first()
    if not copro_obj:
        raise HTTPException(status_code=404, detail="Copropriété introuvable")
    
    # Sauvegarder les données avant suppression pour le log
    before_data = get_model_data(copro_obj)
    copro_name = copro_obj.nom or f'ID {copro_obj.id}'
    
    db.delete(copro_obj)
    db.commit()
    
    # Log de suppression de copropriété
    AuditLogger.log_crud_action(
        db=db,
        action=models.ActionType.DELETE,
        entity_type=models.EntityType.COPRO,
        entity_id=copro_id,
        user_id=current_user.id,
        description=f"Suppression de la copropriété: {copro_name}",
        before_data=before_data,
        request=request
    )
    
    return {"ok": True}

# ---------------------- SYNDICAT COPRO ----------------------

@app.post("/copros/{copro_id}/syndicat", response_model=schemas.SyndicatCoproOut)
def create_syndicat_copro(copro_id: int, syndicat: schemas.SyndicatCoproCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    if db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first():
        raise HTTPException(status_code=400, detail="Syndicat déjà existant pour cette copropriété")
    syndicat_obj = models.SyndicatCopro(**syndicat.dict(), copro_id=copro_id, user_id=current_user.id)
    db.add(syndicat_obj)
    db.commit()
    db.refresh(syndicat_obj)
    return syndicat_obj

@app.get("/copros/{copro_id}/syndicat", response_model=schemas.SyndicatCoproOut)
def get_syndicat_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    syndicat = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first()
    if not syndicat:
        raise HTTPException(status_code=404, detail="Syndicat introuvable")
    return syndicat

@app.put("/copros/{copro_id}/syndicat", response_model=schemas.SyndicatCoproOut)
def update_syndicat_copro(copro_id: int, syndicat: schemas.SyndicatCoproUpdate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    syndicat_obj = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first()
    if not syndicat_obj:
        raise HTTPException(status_code=404, detail="Syndicat introuvable")
    for key, value in syndicat.dict(exclude_unset=True).items():
        setattr(syndicat_obj, key, value)
    db.commit()
    db.refresh(syndicat_obj)
    return syndicat_obj

# Liste de tous les syndicats de copropriété
@app.get("/syndicats_copro/", response_model=List[schemas.SyndicatCoproOut])
def list_syndicats_copro(db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    # Syndicats créés par l'utilisateur
    syndicats_user = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.user_id == current_user.id)
    # Copros visibles par l'utilisateur
    # 1. Immeubles créés par l'utilisateur
    my_buildings = db.query(models.Building).filter(models.Building.user_id == current_user.id).all()
    copro_ids_from_buildings = [b.copro_id for b in my_buildings if b.copro_id]
    # 2. Copros où l'utilisateur est owner/gestionnaire d'au moins un appartement
    links = db.query(models.ApartmentUserLink).filter(models.ApartmentUserLink.user_id == current_user.id, models.ApartmentUserLink.role.in_(["owner","gestionnaire"]))
    apartment_ids = [l.apartment_id for l in links]
    building_ids = db.query(models.Apartment.building_id).filter(models.Apartment.id.in_(apartment_ids)).distinct()
    copros_from_apartments = db.query(models.Building.copro_id).filter(models.Building.id.in_(building_ids)).distinct()
    copro_ids_from_apartments = [c[0] for c in copros_from_apartments if c[0]]
    # Unifie les copro_id
    copro_ids = set(copro_ids_from_buildings) | set(copro_ids_from_apartments)
    syndicats_copros = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id.in_(copro_ids))
    # Union sans doublons
    syndicats = syndicats_user.union(syndicats_copros).all()
    return syndicats

@app.delete("/copros/{copro_id}/syndicat")
def delete_syndicat_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    syndicat_obj = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first()
    if not syndicat_obj:
        raise HTTPException(status_code=404, detail="Syndicat introuvable")
    db.delete(syndicat_obj)
    db.commit()
    return {"ok": True}

# ---------------------- BUILDINGS ----------------------

@app.get("/buildings/{building_id}", response_model=schemas.BuildingOut)
def get_building(building_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    return building

@app.post("/buildings/", response_model=schemas.BuildingOut)
def create_building(building: schemas.BuildingCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    new_building = models.Building(**building.dict(), user_id=current_user.id)
    db.add(new_building)
    db.commit()
    db.refresh(new_building)
    return new_building


@app.get("/buildings/", response_model=List[schemas.BuildingOut])
def get_my_buildings(db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    # Immeubles où l'utilisateur a un appartement
    links = db.query(models.ApartmentUserLink).filter(models.ApartmentUserLink.user_id == current_user.id).all()
    apartment_ids = [link.apartment_id for link in links]
    building_ids = db.query(models.Apartment.building_id).filter(models.Apartment.id.in_(apartment_ids)).distinct()
    # Immeubles créés par l'utilisateur
    my_buildings = db.query(models.Building).filter(models.Building.user_id == current_user.id)
    # Union des deux
    buildings = db.query(models.Building).filter(
        (models.Building.id.in_(building_ids)) | (models.Building.user_id == current_user.id)
    ).all()
    return buildings


@app.put("/buildings/{building_id}", response_model=schemas.BuildingOut)
def update_building(building_id: int, updated: schemas.BuildingCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    apartments = db.query(models.Apartment).filter(models.Apartment.building_id == building_id).all()
    links = db.query(models.ApartmentUserLink).filter(
        models.ApartmentUserLink.user_id == current_user.id,
        models.ApartmentUserLink.apartment_id.in_([a.id for a in apartments])
    ).all()
    if not links or not any(link.role in ["owner", "gestionnaire"] for link in links):
        raise HTTPException(status_code=403, detail="Pas autorisé à modifier ce bâtiment")
    for key, value in updated.dict().items():
        setattr(building, key, value)
    db.commit()
    db.refresh(building)
    return building


@app.delete("/buildings/{building_id}")
def delete_building(building_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    apartments = db.query(models.Apartment).filter(models.Apartment.building_id == building_id).all()
    if apartments:
        raise HTTPException(status_code=400, detail="Immeuble non vide, supprimez d'abord les appartements")
    db.delete(building)
    db.commit()
    return {"msg": "Immeuble supprimé avec succès"}


@app.get("/apartment-limit-info")
def get_apartment_limit_info_endpoint(
    limit_info: dict = Depends(get_apartment_limit_info)
):
    """Retourne les informations sur les limites d'appartements de l'utilisateur"""
    return limit_info

@app.get("/buildings/{building_id}/apartments", response_model=List[schemas.ApartmentOut])
def get_my_apartments_in_building(building_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    if building.user_id == current_user.id:
        # Propriétaire : voit tous les appartements
        apartments = db.query(models.Apartment).filter(models.Apartment.building_id == building_id).all()
    else:
        # Sinon, ne voit que ceux où il est lié
        apartments = db.query(models.Apartment).join(models.ApartmentUserLink).filter(
            models.Apartment.building_id == building_id,
            models.ApartmentUserLink.user_id == current_user.id
        ).all()
    return apartments


# ---------------------- APARTMENTS ----------------------
@app.post("/apartments/", response_model=schemas.ApartmentOut)
def create_apartment(
    apartment: schemas.ApartmentCreate, 
    db: Session = Depends(get_db), 
    current_user: models.UserAuth = Depends(get_current_user),
    _: bool = Depends(check_apartment_limit)
):
    building = db.query(models.Building).filter(models.Building.id == apartment.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    existing_apartments = db.query(models.Apartment).filter(models.Apartment.building_id == apartment.building_id).count()
    if existing_apartments > 0:
        # Autoriser si propriétaire de l'immeuble
        if building.user_id != current_user.id:
            links = db.query(models.ApartmentUserLink).join(models.Apartment).filter(
                models.Apartment.building_id == apartment.building_id,
                models.ApartmentUserLink.user_id == current_user.id,
                models.ApartmentUserLink.role.in_(["owner", "gestionnaire"])
            ).all()
            if not links:
                raise HTTPException(status_code=403, detail="Pas autorisé à ajouter un appartement")
    new_apartment = models.Apartment(**apartment.dict())
    db.add(new_apartment)
    db.commit()
    db.refresh(new_apartment)
    db.add(models.ApartmentUserLink(apartment_id=new_apartment.id, user_id=current_user.id, role="owner"))
    db.commit()
    return new_apartment


@app.get("/apartments/{apartment_id}/users", response_model=List[schemas.ApartmentUserFullOut])
def get_users_for_apartment(apartment_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    apartment = db.query(models.Apartment).filter_by(id=apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    current_link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=current_user.id).first()
    if not current_link:
        raise HTTPException(status_code=403, detail="Accès interdit")
    links = (
        db.query(models.ApartmentUserLink, models.UserAuth)
        .join(models.UserAuth, models.ApartmentUserLink.user_id == models.UserAuth.id)
        .filter(models.ApartmentUserLink.apartment_id == apartment_id)
        .all()
    )
    return [
        schemas.ApartmentUserFullOut(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=link.role
        )
        for link, user in links
    ]


@app.post("/apartments/{apartment_id}/roles")
def add_user_role_to_apartment(apartment_id: int, payload: schemas.RoleAssignment, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    user_id = payload.user_id
    role = payload.role
    apartment = db.query(models.Apartment).filter_by(id=apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    current_link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=current_user.id).first()
    if not current_link or current_link.role != "owner":
        raise HTTPException(status_code=403, detail="Seul un propriétaire peut gérer les accès")
    if db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=user_id).first():
        raise HTTPException(status_code=400, detail="Utilisateur déjà lié")
    db.add(models.ApartmentUserLink(apartment_id=apartment_id, user_id=user_id, role=role))
    db.commit()
    return {"msg": f"Rôle {role} ajouté pour l'utilisateur {user_id}"}


@app.delete("/apartments/{apartment_id}/roles/{user_id}")
def remove_user_role_from_apartment(apartment_id: int, user_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=current_user.id).first()
    if not link or link.role != "owner":
        raise HTTPException(status_code=403, detail="Seul un propriétaire peut supprimer")
    if user_id == current_user.id:
        owner_count = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, role="owner").count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Vous êtes le seul owner")
    target_link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=user_id).first()
    if not target_link:
        raise HTTPException(status_code=404, detail="Aucun lien trouvé")
    db.delete(target_link)
    db.commit()
    return {"msg": "Rôle supprimé avec succès"}


@app.post("/upload-photo/", response_model=schemas.PhotoOut)
def upload_photo(
    file: UploadFile = File(...),
    type: models.PhotoType = Form(...),
    target_id: int = Form(...),
    title: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.UserAuth = Depends(get_current_user)
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"user_{current_user.id}_{timestamp}_{uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    photo = models.Photo(filename=file_path, type=type, title=title, description=description)
    if type == models.PhotoType.building:
        if not db.query(models.Building).filter_by(id=target_id).first():
            raise HTTPException(status_code=404, detail="Immeuble non trouvé")
        photo.building_id = target_id
    elif type == models.PhotoType.apartment:
        if not db.query(models.Apartment).filter_by(id=target_id).first():
            raise HTTPException(status_code=404, detail="Appartement non trouvé")
        photo.apartment_id = target_id
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@app.get("/buildings/{building_id}/photos", response_model=List[schemas.PhotoOut])
def get_building_photos(building_id: int, db: Session = Depends(get_db)):
    return db.query(models.Photo).filter_by(building_id=building_id).all()


@app.get("/apartments/{apartment_id}/photos", response_model=List[schemas.PhotoOut])
def get_apartment_photos(apartment_id: int, db: Session = Depends(get_db)):
    return db.query(models.Photo).filter_by(apartment_id=apartment_id).all()

# ---------------------- AUDIT LOGS ----------------------

@app.get("/logs/", response_model=List[schemas.AuditLogOut])
def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[models.ActionType] = None,
    entity_type: Optional[models.EntityType] = None,
    entity_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.UserAuth = Depends(get_current_user)
):
    """
    Récupérer les logs d'audit avec filtres optionnels
    Seuls les administrateurs peuvent voir tous les logs, 
    les autres utilisateurs ne voient que leurs propres actions
    """
    
    # TODO: Ajouter un système de rôles pour déterminer qui peut voir tous les logs
    # Pour l'instant, chaque utilisateur ne voit que ses propres logs
    query = db.query(
        models.AuditLog,
        models.UserAuth.email.label('user_email'),
        (models.UserAuth.first_name + ' ' + models.UserAuth.last_name).label('user_name')
    ).outerjoin(models.UserAuth, models.AuditLog.user_id == models.UserAuth.id)
    
    # Filtrer par utilisateur (pour l'instant, seulement ses propres logs)
    query = query.filter(models.AuditLog.user_id == current_user.id)
    
    # Appliquer les filtres
    if action:
        query = query.filter(models.AuditLog.action == action)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
    
    # Ordonner par date décroissante
    query = query.order_by(models.AuditLog.created_at.desc())
    
    # Pagination
    query = query.offset(offset).limit(limit)
    
    results = query.all()
    
    # Transformer les résultats
    logs = []
    for audit_log, user_email, user_name in results:
        log_dict = {
            "id": audit_log.id,
            "user_id": audit_log.user_id,
            "action": audit_log.action,
            "entity_type": audit_log.entity_type,
            "entity_id": audit_log.entity_id,
            "description": audit_log.description,
            "details": audit_log.details,
            "ip_address": audit_log.ip_address,
            "user_agent": audit_log.user_agent,
            "endpoint": audit_log.endpoint,
            "method": audit_log.method,
            "status_code": audit_log.status_code,
            "created_at": audit_log.created_at,
            "user_email": user_email,
            "user_name": user_name
        }
        logs.append(schemas.AuditLogOut(**log_dict))
    
    return logs

@app.get("/logs/stats/")
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: models.UserAuth = Depends(get_current_user)
):
    """
    Statistiques des logs pour l'utilisateur connecté
    """
    from sqlalchemy import func
    
    # Statistiques par action
    stats_by_action = db.query(
        models.AuditLog.action,
        func.count(models.AuditLog.id).label('count')
    ).filter(
        models.AuditLog.user_id == current_user.id
    ).group_by(models.AuditLog.action).all()
    
    # Statistiques par entité
    stats_by_entity = db.query(
        models.AuditLog.entity_type,
        func.count(models.AuditLog.id).label('count')
    ).filter(
        models.AuditLog.user_id == current_user.id
    ).group_by(models.AuditLog.entity_type).all()
    
    # Dernière activité
    last_activity = db.query(models.AuditLog).filter(
        models.AuditLog.user_id == current_user.id
    ).order_by(models.AuditLog.created_at.desc()).first()
    
    return {
        "total_actions": sum([stat.count for stat in stats_by_action]),
        "stats_by_action": {stat.action: stat.count for stat in stats_by_action},
        "stats_by_entity": {stat.entity_type: stat.count for stat in stats_by_entity},
        "last_activity": last_activity.created_at if last_activity else None
    }

# Inclure les routes Stripe, Room et Photo
app.include_router(stripe_routes.router)
app.include_router(room_routes.router)
app.include_router(photo_routes.router)
app.include_router(floor_plan_routes.router)
app.include_router(tenant_routes.router)
app.include_router(lease_routes.router)
app.include_router(document_routes.router)
app.include_router(tenant_portal_routes.router)
app.include_router(tenant_invitation_routes.router)
app.include_router(detailed_inventory_routes.router)
app.include_router(lease_generation_routes.router)
app.include_router(property_management_routes.router)
app.include_router(email_verification_routes.router)
app.include_router(admin_router)
app.include_router(audit_undo_router)