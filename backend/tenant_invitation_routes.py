"""
Routes API pour les invitations de locataires
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import UserAuth, Tenant, TenantInvitation
from schemas import TenantOut
from tenant_invitation_service import get_tenant_invitation_service, TenantInvitationService
from pydantic import BaseModel
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/invitations", tags=["tenant-invitations"])


class TenantInvitationCreate(BaseModel):
    """Schéma pour créer une invitation de locataire"""
    tenant_id: int
    send_email: bool = True
    expires_in_hours: int = 168  # 7 jours par défaut


class TenantInvitationOut(BaseModel):
    """Schéma de sortie pour une invitation"""
    id: int
    tenant_id: int
    invited_by: int
    invitation_token: str
    token_expires_at: datetime
    is_sent: bool
    is_used: bool
    sent_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    email_sent_to: Optional[str] = None
    email_message_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantInvitationWithDetails(TenantInvitationOut):
    """Invitation avec détails du locataire"""
    tenant: TenantOut
    
    class Config:
        from_attributes = True


class TokenValidationResponse(BaseModel):
    """Réponse de validation de token"""
    is_valid: bool
    tenant_id: Optional[int] = None
    tenant_email: Optional[str] = None
    tenant_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


@router.post("/", response_model=TenantInvitationOut)
async def create_tenant_invitation(
    invitation_data: TenantInvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crée une invitation pour un locataire
    Si send_email=True, envoie automatiquement l'email d'invitation
    """
    
    # Vérifier que le locataire existe et appartient à l'utilisateur
    tenant = db.query(Tenant).filter(Tenant.id == invitation_data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Vérifier l'accès au locataire via un bail
    from models import Lease
    lease = db.query(Lease).filter(
        Lease.tenant_id == invitation_data.tenant_id,
        Lease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce locataire"
        )
    
    # Créer le service d'invitation
    invitation_service = get_tenant_invitation_service(db)
    
    try:
        # Créer l'invitation
        invitation = invitation_service.create_invitation(
            tenant_id=invitation_data.tenant_id,
            invited_by_user_id=current_user.id,
            expires_in_hours=invitation_data.expires_in_hours
        )
        
        # Programmer l'envoi d'email si demandé
        if invitation_data.send_email:
            background_tasks.add_task(
                send_invitation_email_task,
                invitation.id,
                db
            )
        
        return invitation
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de l'invitation: {str(e)}")


async def send_invitation_email_task(invitation_id: int, db: Session):
    """Tâche en arrière-plan pour envoyer l'email d'invitation"""
    try:
        invitation_service = get_tenant_invitation_service(db)
        await invitation_service.send_invitation_email(invitation_id)
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email d'invitation {invitation_id}: {e}")


@router.post("/{invitation_id}/send-email")
async def send_invitation_email(
    invitation_id: int,
    background_tasks: BackgroundTasks,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Envoie l'email d'invitation (si pas encore envoyé)"""
    
    # Vérifier que l'invitation existe et appartient à l'utilisateur
    invitation = db.query(TenantInvitation).filter(
        TenantInvitation.id == invitation_id,
        TenantInvitation.invited_by == current_user.id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation introuvable")
    
    if invitation.is_sent:
        raise HTTPException(status_code=400, detail="Cette invitation a déjà été envoyée")
    
    if invitation.token_expires_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cette invitation a expiré")
    
    # Programmer l'envoi en arrière-plan
    background_tasks.add_task(send_invitation_email_task, invitation_id, db)
    
    return {"message": "Email d'invitation en cours d'envoi"}


@router.get("/", response_model=List[TenantInvitationWithDetails])
async def get_user_invitations(
    include_expired: bool = False,
    include_used: bool = True,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les invitations créées par l'utilisateur"""
    
    query = db.query(TenantInvitation).filter(
        TenantInvitation.invited_by == current_user.id
    )
    
    if not include_expired:
        query = query.filter(TenantInvitation.token_expires_at > datetime.utcnow())
    
    if not include_used:
        query = query.filter(TenantInvitation.is_used == False)
    
    invitations = query.order_by(TenantInvitation.created_at.desc()).all()
    
    # Enrichir avec les données des locataires
    result = []
    for invitation in invitations:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            invitation_dict = {
                **invitation.__dict__,
                "tenant": tenant
            }
            result.append(invitation_dict)
    
    return result


@router.get("/{invitation_id}", response_model=TenantInvitationWithDetails)
async def get_invitation(
    invitation_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère une invitation spécifique"""
    
    invitation = db.query(TenantInvitation).filter(
        TenantInvitation.id == invitation_id,
        TenantInvitation.invited_by == current_user.id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation introuvable")
    
    # Récupérer les données du locataire
    tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
    
    return {
        **invitation.__dict__,
        "tenant": tenant
    }


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Annule une invitation (la supprime si pas encore utilisée)"""
    
    invitation = db.query(TenantInvitation).filter(
        TenantInvitation.id == invitation_id,
        TenantInvitation.invited_by == current_user.id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation introuvable")
    
    if invitation.is_used:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'annuler une invitation déjà utilisée"
        )
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="TENANT_INVITATION",
        entity_id=invitation_id,
        description=f"Annulation de l'invitation #{invitation_id}",
        details=json.dumps({
            "invitation_id": invitation_id,
            "tenant_id": invitation.tenant_id,
            "was_sent": invitation.is_sent
        })
    )
    
    # Supprimer l'invitation
    db.delete(invitation)
    db.commit()
    
    return {"message": f"Invitation #{invitation_id} annulée avec succès"}


# ==================== ROUTES PUBLIQUES (sans authentification) ====================

@router.post("/validate-token", response_model=TokenValidationResponse)
async def validate_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Valide un token d'invitation (route publique pour le portail locataire)
    """
    
    invitation_service = get_tenant_invitation_service(db)
    
    try:
        validation_result = invitation_service.validate_invitation_token(token)
        
        if validation_result:
            return TokenValidationResponse(
                is_valid=True,
                tenant_id=validation_result["tenant_id"],
                tenant_email=validation_result["tenant_email"],
                tenant_name=validation_result["tenant_name"],
                expires_at=validation_result["expires_at"]
            )
        else:
            return TokenValidationResponse(
                is_valid=False,
                error_message="Token d'invitation invalide ou expiré"
            )
            
    except Exception as e:
        return TokenValidationResponse(
            is_valid=False,
            error_message=f"Erreur lors de la validation: {str(e)}"
        )


@router.post("/use-token")
async def use_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Utilise un token d'invitation (marque comme utilisé)
    Route publique pour le portail locataire
    """
    
    invitation_service = get_tenant_invitation_service(db)
    
    try:
        # D'abord valider le token
        validation_result = invitation_service.validate_invitation_token(token)
        
        if not validation_result:
            raise HTTPException(
                status_code=400,
                detail="Token d'invitation invalide ou expiré"
            )
        
        # Marquer comme utilisé
        success = invitation_service.use_invitation_token(token)
        
        if success:
            return {
                "message": "Token d'invitation utilisé avec succès",
                "tenant_id": validation_result["tenant_id"],
                "tenant_email": validation_result["tenant_email"]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Impossible d'utiliser ce token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'utilisation du token: {str(e)}"
        )


@router.get("/tenant/{tenant_id}/stats")
async def get_tenant_invitation_stats(
    tenant_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques d'invitation pour un locataire"""
    
    # Vérifier l'accès au locataire
    from models import Lease
    lease = db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce locataire"
        )
    
    # Compter les invitations
    total_invitations = db.query(TenantInvitation).filter(
        TenantInvitation.tenant_id == tenant_id
    ).count()
    
    sent_invitations = db.query(TenantInvitation).filter(
        TenantInvitation.tenant_id == tenant_id,
        TenantInvitation.is_sent == True
    ).count()
    
    used_invitations = db.query(TenantInvitation).filter(
        TenantInvitation.tenant_id == tenant_id,
        TenantInvitation.is_used == True
    ).count()
    
    active_invitations = db.query(TenantInvitation).filter(
        TenantInvitation.tenant_id == tenant_id,
        TenantInvitation.is_used == False,
        TenantInvitation.token_expires_at > datetime.utcnow()
    ).count()
    
    return {
        "tenant_id": tenant_id,
        "total_invitations": total_invitations,
        "sent_invitations": sent_invitations,
        "used_invitations": used_invitations,
        "active_invitations": active_invitations,
        "has_active_access": used_invitations > 0
    }