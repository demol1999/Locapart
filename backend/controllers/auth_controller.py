"""
Contrôleur pour l'authentification
Gestion centralisée de toutes les opérations d'auth
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError
from typing import Dict, Any

from database import get_db
from auth import (
    get_password_hash, verify_password, create_access_token, get_current_user,
    create_user_session, verify_refresh_token, invalidate_user_session
)
from models import UserAuth
from enums import ActionType, EntityType, AuthType
from audit_logger import AuditLogger, get_model_data
from validation_middleware import ValidationErrorHandler
from rate_limiter import check_rate_limit
from error_handlers import (
    DatabaseErrorHandler, PermissionErrorHandler, ErrorLogger, ErrorResponse
)
import schemas

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/signup", response_model=schemas.UserOut)
async def signup(
    user: schemas.UserCreate, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("signup"))
):
    """
    Inscription d'un nouvel utilisateur
    """
    try:
        # Vérifier si l'email existe déjà
        existing_user = db.query(UserAuth).filter(UserAuth.email == user.email).first()
        if existing_user:
            error_response = PermissionErrorHandler.access_denied(
                "Cette adresse email est déjà utilisée"
            )
            ErrorLogger.log_error(error_response, db, request)
            return error_response.to_json_response()
        
        # Créer l'utilisateur
        hashed_password = get_password_hash(user.password)
        user_obj = UserAuth(
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
        error_response = DatabaseErrorHandler.handle_integrity_error(e, db, request)
        ErrorLogger.log_error(error_response, db, request)
        return error_response.to_json_response()
    
    except DataError as e:
        db.rollback()
        error_response = DatabaseErrorHandler.handle_data_error(e, db, request)
        ErrorLogger.log_error(error_response, db, request)
        return error_response.to_json_response()
    
    # Log de création d'utilisateur
    AuditLogger.log_crud_action(
        db=db,
        action=ActionType.CREATE,
        entity_type=EntityType.USER,
        entity_id=user_obj.id,
        user_id=user_obj.id,
        description=f"Inscription d'un nouvel utilisateur: {user_obj.email}",
        after_data=get_model_data(user_obj),
        request=request
    )
    
    # Envoyer automatiquement l'email de vérification pour les comptes email/password
    if user_obj.auth_type == AuthType.EMAIL_PASSWORD:
        await _send_verification_email_background(
            user_obj, request, background_tasks, db
        )
    
    return user_obj


@router.post("/login")
async def login(
    request: Request, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("login"))
) -> Dict[str, Any]:
    """
    Connexion utilisateur
    """
    user = db.query(UserAuth).filter(UserAuth.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        error_response = PermissionErrorHandler.unauthorized(
            "Email ou mot de passe incorrect"
        )
        
        AuditLogger.log_error(
            db=db,
            description=f"Tentative de connexion échouée pour: {form_data.username}",
            error_details="Identifiants incorrects",
            request=request,
            status_code=401
        )
        
        return error_response.to_json_response()
    
    # Créer les tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_user_session(db, user.id, request)
    
    # Log de connexion réussie
    AuditLogger.log_crud_action(
        db=db,
        action=ActionType.LOGIN,
        entity_type=EntityType.USER,
        entity_id=user.id,
        user_id=user.id,
        description=f"Connexion réussie: {user.email}",
        request=request
    )
    
    response_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": schemas.UserOut.model_validate(user)
    }
    
    return response_data


@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_request: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Renouvellement des tokens
    """
    user_session = verify_refresh_token(db, refresh_request.refresh_token)
    
    if not user_session:
        error_response = PermissionErrorHandler.unauthorized("Token invalide ou expiré")
        return error_response.to_json_response()
    
    user = db.query(UserAuth).filter(UserAuth.id == user_session.user_id).first()
    if not user:
        error_response = PermissionErrorHandler.unauthorized("Utilisateur non trouvé")
        return error_response.to_json_response()
    
    # Créer un nouveau token d'accès
    access_token = create_access_token(data={"sub": user.email})
    
    # Log du renouvellement
    AuditLogger.log_crud_action(
        db=db,
        action=ActionType.REFRESH_TOKEN,
        entity_type=EntityType.USER,
        entity_id=user.id,
        user_id=user.id,
        description=f"Renouvellement de token: {user.email}",
        request=request
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    request: Request,
    logout_request: schemas.LogoutRequest,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Déconnexion utilisateur
    """
    # Invalider la session
    invalidate_user_session(db, logout_request.refresh_token)
    
    # Log de déconnexion
    AuditLogger.log_crud_action(
        db=db,
        action=ActionType.LOGOUT,
        entity_type=EntityType.USER,
        entity_id=current_user.id,
        user_id=current_user.id,
        description=f"Déconnexion: {current_user.email}",
        request=request
    )
    
    return {"message": "Déconnexion réussie"}


@router.get("/me", response_model=schemas.UserOut)
async def get_current_user_info(
    current_user: UserAuth = Depends(get_current_user)
):
    """
    Récupère les informations de l'utilisateur connecté
    """
    return current_user


async def _send_verification_email_background(
    user_obj: UserAuth,
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session
):
    """
    Envoie l'email de vérification en arrière-plan
    """
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