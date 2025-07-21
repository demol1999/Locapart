"""
Routes API pour la gestion des locataires
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import UserAuth, Tenant, Lease, TenantDocument, Apartment, Building
from schemas import (
    TenantCreate, TenantUpdate, TenantOut,
    LeaseCreate, LeaseUpdate, LeaseOut, LeaseWithDetails,
    TenantDocumentCreate, TenantDocumentUpdate, TenantDocumentOut,
    RentalStats
)
from pydantic import BaseModel
from fastapi import BackgroundTasks
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


class TenantCreateWithInvitation(BaseModel):
    """Schéma pour créer un locataire avec option d'invitation"""
    tenant_data: TenantCreate
    send_invitation: bool = False
    invitation_expires_hours: int = 168  # 7 jours par défaut

def check_tenant_access(tenant_id: int, user: UserAuth, db: Session) -> Tenant:
    """Vérifie que l'utilisateur a accès au locataire"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Vérifier si l'utilisateur a un bail avec ce locataire
    lease = db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.created_by == user.id
    ).first()
    
    if not lease:
        raise HTTPException(
            status_code=403, 
            detail="Accès non autorisé à ce locataire"
        )
    
    return tenant

@router.get("/", response_model=List[TenantOut])
async def get_user_tenants(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les locataires de l'utilisateur"""
    
    # Récupérer les locataires via les baux créés par l'utilisateur
    tenants = db.query(Tenant).join(Lease).filter(
        Lease.created_by == current_user.id
    ).distinct().all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="TENANT",
        description=f"Consultation des locataires ({len(tenants)} locataires)",
        details=json.dumps({
            "tenants_count": len(tenants)
        })
    )
    
    return tenants

@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un locataire spécifique"""
    
    tenant = check_tenant_access(tenant_id, current_user, db)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="TENANT",
        entity_id=tenant_id,
        description=f"Consultation du locataire {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant_id,
            "tenant_email": tenant.email
        })
    )
    
    return tenant

@router.post("/", response_model=TenantOut)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau locataire"""
    
    # Vérifier que l'email n'existe pas déjà
    existing_tenant = db.query(Tenant).filter(Tenant.email == tenant_data.email).first()
    if existing_tenant:
        raise HTTPException(
            status_code=400,
            detail="Un locataire avec cet email existe déjà"
        )
    
    # Créer le locataire
    tenant = Tenant(**tenant_data.dict())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="TENANT",
        entity_id=tenant.id,
        description=f"Création du locataire {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant.id,
            "tenant_email": tenant.email,
            "tenant_name": f"{tenant.first_name} {tenant.last_name}"
        })
    )
    
    return tenant


@router.post("/with-invitation", response_model=TenantOut)
async def create_tenant_with_invitation(
    tenant_data: TenantCreate,
    send_invitation: bool = False,
    invitation_expires_hours: int = 168,
    background_tasks: BackgroundTasks,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crée un nouveau locataire avec option d'envoi d'invitation par email
    """
    
    # Vérifier que l'email n'existe pas déjà
    existing_tenant = db.query(Tenant).filter(Tenant.email == tenant_data.email).first()
    if existing_tenant:
        raise HTTPException(
            status_code=400,
            detail="Un locataire avec cet email existe déjà"
        )
    
    # Créer le locataire
    tenant = Tenant(**tenant_data.dict())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="TENANT",
        entity_id=tenant.id,
        description=f"Création du locataire {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant.id,
            "tenant_email": tenant.email,
            "tenant_name": f"{tenant.first_name} {tenant.last_name}",
            "invitation_requested": send_invitation
        })
    )
    
    # Si une invitation est demandée, il faut d'abord créer un bail
    if send_invitation:
        # Vérifier qu'il y a un bail pour ce locataire créé par cet utilisateur
        lease = db.query(Lease).filter(
            Lease.tenant_id == tenant.id,
            Lease.created_by == current_user.id
        ).first()
        
        if lease:
            # Créer et envoyer l'invitation en arrière-plan
            background_tasks.add_task(
                create_and_send_invitation_task,
                tenant.id,
                current_user.id,
                invitation_expires_hours,
                db
            )
            
            audit_logger.log_action(
                user_id=current_user.id,
                action="CREATE",
                entity_type="TENANT_INVITATION",
                description=f"Programmation d'invitation pour {tenant.first_name} {tenant.last_name}",
                details=json.dumps({
                    "tenant_id": tenant.id,
                    "expires_in_hours": invitation_expires_hours
                })
            )
        else:
            # Log que l'invitation ne peut pas être envoyée
            audit_logger.log_action(
                user_id=current_user.id,
                action="ERROR",
                entity_type="TENANT_INVITATION",
                description=f"Impossible d'envoyer l'invitation pour {tenant.first_name} {tenant.last_name} - aucun bail trouvé",
                details=json.dumps({
                    "tenant_id": tenant.id,
                    "error": "No lease found for this tenant"
                })
            )
    
    return tenant


async def create_and_send_invitation_task(
    tenant_id: int, 
    user_id: int, 
    expires_hours: int, 
    db: Session
):
    """Tâche en arrière-plan pour créer et envoyer une invitation"""
    try:
        from tenant_invitation_service import get_tenant_invitation_service
        
        invitation_service = get_tenant_invitation_service(db)
        
        # Créer l'invitation
        invitation = invitation_service.create_invitation(
            tenant_id=tenant_id,
            invited_by_user_id=user_id,
            expires_in_hours=expires_hours
        )
        
        # Envoyer l'email
        await invitation_service.send_invitation_email(invitation.id)
        
    except Exception as e:
        print(f"Erreur lors de la création/envoi d'invitation pour le locataire {tenant_id}: {e}")


@router.post("/{tenant_id}/send-invitation")
async def send_tenant_invitation(
    tenant_id: int,
    invitation_expires_hours: int = 168,
    background_tasks: BackgroundTasks,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Envoie une invitation à un locataire existant"""
    
    # Vérifier l'accès au locataire
    tenant = check_tenant_access(tenant_id, current_user, db)
    
    # Vérifier qu'il n'y a pas déjà une invitation active
    from models import TenantInvitation
    existing_invitation = db.query(TenantInvitation).filter(
        TenantInvitation.tenant_id == tenant_id,
        TenantInvitation.is_used == False,
        TenantInvitation.token_expires_at > datetime.utcnow()
    ).first()
    
    if existing_invitation:
        raise HTTPException(
            status_code=400,
            detail="Une invitation active existe déjà pour ce locataire"
        )
    
    # Créer et envoyer l'invitation en arrière-plan
    background_tasks.add_task(
        create_and_send_invitation_task,
        tenant_id,
        current_user.id,
        invitation_expires_hours,
        db
    )
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="TENANT_INVITATION",
        description=f"Envoi d'invitation programmé pour {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant_id,
            "expires_in_hours": invitation_expires_hours
        })
    )
    
    return {
        "message": f"Invitation en cours d'envoi à {tenant.email}",
        "tenant_id": tenant_id,
        "tenant_name": f"{tenant.first_name} {tenant.last_name}"
    }


@router.put("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour un locataire"""
    
    tenant = check_tenant_access(tenant_id, current_user, db)
    
    # Sauvegarder les anciennes valeurs pour l'audit
    old_values = {
        "first_name": tenant.first_name,
        "last_name": tenant.last_name,
        "email": tenant.email,
        "phone": tenant.phone
    }
    
    # Vérifier l'unicité de l'email si modifié
    update_data = tenant_update.dict(exclude_unset=True)
    if 'email' in update_data and update_data['email'] != tenant.email:
        existing_tenant = db.query(Tenant).filter(
            Tenant.email == update_data['email'],
            Tenant.id != tenant_id
        ).first()
        if existing_tenant:
            raise HTTPException(
                status_code=400,
                detail="Un locataire avec cet email existe déjà"
            )
    
    # Mettre à jour les champs
    for field, value in update_data.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)
    
    tenant.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tenant)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    new_values = {
        "first_name": tenant.first_name,
        "last_name": tenant.last_name,
        "email": tenant.email,
        "phone": tenant.phone
    }
    
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="TENANT",
        entity_id=tenant_id,
        description=f"Modification du locataire {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant_id,
            "old_values": old_values,
            "new_values": new_values
        })
    )
    
    return tenant

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un locataire"""
    
    tenant = check_tenant_access(tenant_id, current_user, db)
    
    # Vérifier s'il y a des baux actifs
    active_leases = db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.status.in_(["ACTIVE", "PENDING"])
    ).count()
    
    if active_leases > 0:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un locataire avec des baux actifs"
        )
    
    tenant_name = f"{tenant.first_name} {tenant.last_name}"
    tenant_email = tenant.email
    
    db.delete(tenant)
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="TENANT",
        entity_id=tenant_id,
        description=f"Suppression du locataire {tenant_name}",
        details=json.dumps({
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "tenant_email": tenant_email
        })
    )
    
    return {"message": f"Locataire {tenant_name} supprimé avec succès"}

@router.get("/{tenant_id}/leases", response_model=List[LeaseOut])
async def get_tenant_leases(
    tenant_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les baux d'un locataire"""
    
    check_tenant_access(tenant_id, current_user, db)
    
    leases = db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.created_by == current_user.id
    ).order_by(Lease.start_date.desc()).all()
    
    return leases

@router.get("/{tenant_id}/documents", response_model=List[TenantDocumentOut])
async def get_tenant_documents(
    tenant_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les documents d'un locataire"""
    
    check_tenant_access(tenant_id, current_user, db)
    
    documents = db.query(TenantDocument).filter(
        TenantDocument.tenant_id == tenant_id
    ).order_by(TenantDocument.created_at.desc()).all()
    
    return documents

@router.get("/search/", response_model=List[TenantOut])
async def search_tenants(
    q: str,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recherche de locataires par nom ou email"""
    
    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="La recherche doit contenir au moins 2 caractères"
        )
    
    search_term = f"%{q.strip()}%"
    
    tenants = db.query(Tenant).join(Lease).filter(
        Lease.created_by == current_user.id
    ).filter(
        (Tenant.first_name.ilike(search_term)) |
        (Tenant.last_name.ilike(search_term)) |
        (Tenant.email.ilike(search_term))
    ).distinct().limit(20).all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="TENANT",
        description=f"Recherche de locataires: '{q}' ({len(tenants)} résultats)",
        details=json.dumps({
            "search_query": q,
            "results_count": len(tenants)
        })
    )
    
    return tenants

@router.get("/stats/summary", response_model=RentalStats)
async def get_rental_stats(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques de gestion locative"""
    
    # Statistiques des locataires
    total_tenants = db.query(Tenant).join(Lease).filter(
        Lease.created_by == current_user.id
    ).distinct().count()
    
    # Statistiques des baux
    active_leases = db.query(Lease).filter(
        Lease.created_by == current_user.id,
        Lease.status == "ACTIVE"
    ).count()
    
    pending_leases = db.query(Lease).filter(
        Lease.created_by == current_user.id,
        Lease.status == "PENDING"
    ).count()
    
    expired_leases = db.query(Lease).filter(
        Lease.created_by == current_user.id,
        Lease.status == "EXPIRED"
    ).count()
    
    # Revenus mensuels
    total_monthly_revenue = db.query(
        db.func.sum(Lease.monthly_rent + Lease.charges)
    ).filter(
        Lease.created_by == current_user.id,
        Lease.status == "ACTIVE"
    ).scalar() or 0
    
    # Taux d'occupation (approximatif)
    total_apartments = db.query(Apartment).join(
        db.query(Apartment.building_id).join(
            db.query(Apartment.id).join(Lease).filter(
                Lease.created_by == current_user.id
            ).subquery(), Apartment.id == db.text("anon_1.id")
        ).subquery(), Apartment.building_id == db.text("anon_1.building_id")
    ).count()
    
    occupancy_rate = (active_leases / total_apartments * 100) if total_apartments > 0 else 0
    
    stats = RentalStats(
        total_tenants=total_tenants,
        active_leases=active_leases,
        pending_leases=pending_leases,
        expired_leases=expired_leases,
        total_monthly_revenue=total_monthly_revenue,
        occupancy_rate=round(occupancy_rate, 2)
    )
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="TENANT",
        description="Consultation des statistiques locatives",
        details=json.dumps({
            "total_tenants": total_tenants,
            "active_leases": active_leases
        })
    )
    
    return stats