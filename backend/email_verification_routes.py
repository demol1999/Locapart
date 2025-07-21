"""
Routes pour la vérification d'email
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel, EmailStr, Field

from database import get_db
from auth import get_current_user
from models import UserAuth
from email_verification_service import create_verification_service, EmailVerificationService
from audit_logger import AuditLogger
from rate_limiter import check_rate_limit

router = APIRouter(prefix="/api/email-verification", tags=["Vérification Email"])


# ==================== SCHÉMAS ====================

class SendVerificationRequest(BaseModel):
    """Demande d'envoi de code de vérification"""
    email: EmailStr = Field(..., description="Email à vérifier")


class VerifyCodeRequest(BaseModel):
    """Demande de vérification de code"""
    code: str = Field(..., min_length=6, max_length=6, description="Code à 6 chiffres")


class VerifyTokenRequest(BaseModel):
    """Demande de vérification par token"""
    token: str = Field(..., min_length=10, description="Token de vérification")


class VerificationStatusResponse(BaseModel):
    """Statut de vérification"""
    is_verified: bool
    email: str
    verified_at: str = None


# ==================== ROUTES ====================

@router.post("/send")
async def send_verification_email(
    request: SendVerificationRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("verification"))
):
    """Envoie un email de vérification"""
    
    try:
        # Vérifier que l'email correspond à celui de l'utilisateur
        if current_user.email != request.email:
            raise HTTPException(
                status_code=400, 
                detail="Vous ne pouvez vérifier que votre propre email"
            )
        
        # Vérifier si déjà vérifié
        if current_user.email_verified:
            return {
                "success": True,
                "message": "Email déjà vérifié",
                "already_verified": True
            }
        
        # Créer le service de vérification
        verification_service = create_verification_service(db)
        
        # Récupérer les infos de la requête
        client_ip = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")
        
        # Envoyer l'email en arrière-plan
        result = await verification_service.send_verification_email(
            user_id=current_user.id,
            email=current_user.email,
            user_name=f"{current_user.first_name} {current_user.last_name}",
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Logger l'action
        AuditLogger.log_crud_action(
            db=db,
            action="CREATE",
            entity_type="EMAIL_VERIFICATION",
            entity_id=result.get("verification_id"),
            user_id=current_user.id,
            description=f"Demande de vérification email pour: {current_user.email}",
            request=req
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Email de vérification envoyé",
                "expires_in_minutes": 15,
                "provider": result.get("provider")
            }
        else:
            # Logger l'erreur
            AuditLogger.log_error(
                db=db,
                description=f"Erreur envoi email vérification: {current_user.email}",
                error_details=result.get("error", "Erreur inconnue"),
                request=req,
                status_code=500
            )
            
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de l'envoi de l'email de vérification"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        AuditLogger.log_error(
            db=db,
            description=f"Erreur système envoi vérification: {current_user.email}",
            error_details=str(e),
            request=req,
            status_code=500
        )
        raise HTTPException(
            status_code=500,
            detail="Erreur système lors de l'envoi"
        )


@router.post("/verify-code")
async def verify_email_code(
    request: VerifyCodeRequest,
    req: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("verification"))
):
    """Vérifie un code de vérification"""
    
    try:
        # Créer le service de vérification
        verification_service = create_verification_service(db)
        
        # Vérifier le code
        result = verification_service.verify_code(current_user.id, request.code)
        
        # Logger l'action
        action_description = f"Vérification code email: {current_user.email}"
        if result["success"]:
            AuditLogger.log_crud_action(
                db=db,
                action="UPDATE",
                entity_type="USER",
                entity_id=current_user.id,
                user_id=current_user.id,
                description=f"{action_description} - SUCCÈS",
                request=req
            )
        else:
            AuditLogger.log_error(
                db=db,
                description=f"{action_description} - ÉCHEC",
                error_details=result.get("message", "Code incorrect"),
                request=req,
                status_code=400
            )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "email_verified": True
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        AuditLogger.log_error(
            db=db,
            description=f"Erreur système vérification code: {current_user.email}",
            error_details=str(e),
            request=req,
            status_code=500
        )
        raise HTTPException(
            status_code=500,
            detail="Erreur système lors de la vérification"
        )


@router.post("/verify-token")
async def verify_email_token(
    request: VerifyTokenRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """Vérifie un token de vérification (via URL)"""
    
    try:
        # Créer le service de vérification
        verification_service = create_verification_service(db)
        
        # Vérifier le token
        result = verification_service.verify_token(request.token)
        
        if result["success"]:
            # Logger l'action
            AuditLogger.log_crud_action(
                db=db,
                action="UPDATE",
                entity_type="USER",
                entity_id=result.get("user_id"),
                user_id=result.get("user_id"),
                description="Vérification email par token - SUCCÈS",
                request=req
            )
            
            return {
                "success": True,
                "message": result["message"],
                "email_verified": True
            }
        else:
            AuditLogger.log_error(
                db=db,
                description="Vérification email par token - ÉCHEC",
                error_details=result.get("message", "Token invalide"),
                request=req,
                status_code=400
            )
            
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        AuditLogger.log_error(
            db=db,
            description="Erreur système vérification token",
            error_details=str(e),
            request=req,
            status_code=500
        )
        raise HTTPException(
            status_code=500,
            detail="Erreur système lors de la vérification"
        )


@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère le statut de vérification de l'email"""
    
    return VerificationStatusResponse(
        is_verified=current_user.email_verified,
        email=current_user.email,
        verified_at=current_user.email_verified_at.isoformat() if current_user.email_verified_at else None
    )


@router.post("/resend")
async def resend_verification_email(
    background_tasks: BackgroundTasks,
    req: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("verification"))
):
    """Renvoie un email de vérification"""
    
    # Réutiliser la route d'envoi
    request_data = SendVerificationRequest(email=current_user.email)
    return await send_verification_email(
        request=request_data,
        background_tasks=background_tasks,
        req=req,
        current_user=current_user,
        db=db,
        _=True  # Rate limit déjà vérifié
    )