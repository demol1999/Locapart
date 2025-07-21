"""
Routes API pour la gestion des baux
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
from datetime import datetime, date

from database import get_db
from auth import get_current_user
from models import UserAuth, Lease, Tenant, Apartment, LeaseStatus
from schemas import (
    LeaseCreate, LeaseUpdate, LeaseOut, LeaseWithDetails
)
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/leases", tags=["leases"])

def check_lease_access(lease_id: int, user: UserAuth, db: Session) -> Lease:
    """Vérifie que l'utilisateur a accès au bail"""
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    if lease.created_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce bail"
        )
    
    return lease

@router.get("/", response_model=List[LeaseOut])
async def get_user_leases(
    status: Optional[str] = None,
    apartment_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les baux de l'utilisateur avec filtres optionnels"""
    
    query = db.query(Lease).filter(Lease.created_by == current_user.id)
    
    # Filtres
    if status:
        query = query.filter(Lease.status == status)
    if apartment_id:
        query = query.filter(Lease.apartment_id == apartment_id)
    if tenant_id:
        query = query.filter(Lease.tenant_id == tenant_id)
    
    leases = query.order_by(Lease.start_date.desc()).all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="LEASE",
        description=f"Consultation des baux ({len(leases)} baux)",
        details=json.dumps({
            "filters": {
                "status": status,
                "apartment_id": apartment_id,
                "tenant_id": tenant_id
            },
            "results_count": len(leases)
        })
    )
    
    return leases

@router.get("/{lease_id}", response_model=LeaseWithDetails)
async def get_lease(
    lease_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un bail spécifique avec détails"""
    
    lease = check_lease_access(lease_id, current_user, db)
    
    # Charger avec les relations
    lease_with_details = db.query(Lease).options(
        joinedload(Lease.tenant),
        joinedload(Lease.apartment)
    ).filter(Lease.id == lease_id).first()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="LEASE",
        entity_id=lease_id,
        description=f"Consultation du bail #{lease_id}",
        details=json.dumps({
            "lease_id": lease_id,
            "tenant_id": lease.tenant_id,
            "apartment_id": lease.apartment_id
        })
    )
    
    return lease_with_details

@router.post("/", response_model=LeaseOut)
async def create_lease(
    lease_data: LeaseCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau bail"""
    
    # Vérifier que le locataire existe
    tenant = db.query(Tenant).filter(Tenant.id == lease_data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Vérifier que l'appartement existe et appartient à l'utilisateur
    apartment = db.query(Apartment).filter(Apartment.id == lease_data.apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # TODO: Vérifier les permissions sur l'appartement
    
    # Vérifier qu'il n'y a pas de bail actif sur cet appartement
    existing_lease = db.query(Lease).filter(
        Lease.apartment_id == lease_data.apartment_id,
        Lease.status.in_(["ACTIVE", "PENDING"]),
        Lease.start_date <= lease_data.end_date,
        Lease.end_date >= lease_data.start_date
    ).first()
    
    if existing_lease:
        raise HTTPException(
            status_code=400,
            detail="Il existe déjà un bail actif sur cet appartement pour cette période"
        )
    
    # Créer le bail
    lease = Lease(
        **lease_data.dict(),
        created_by=current_user.id
    )
    
    db.add(lease)
    db.commit()
    db.refresh(lease)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="LEASE",
        entity_id=lease.id,
        description=f"Création du bail #{lease.id} pour {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "lease_id": lease.id,
            "tenant_id": lease.tenant_id,
            "apartment_id": lease.apartment_id,
            "monthly_rent": str(lease.monthly_rent),
            "start_date": lease.start_date.isoformat(),
            "end_date": lease.end_date.isoformat()
        })
    )
    
    return lease

@router.put("/{lease_id}", response_model=LeaseOut)
async def update_lease(
    lease_id: int,
    lease_update: LeaseUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour un bail"""
    
    lease = check_lease_access(lease_id, current_user, db)
    
    # Sauvegarder les anciennes valeurs
    old_values = {
        "monthly_rent": str(lease.monthly_rent),
        "charges": str(lease.charges),
        "status": lease.status.value,
        "start_date": lease.start_date.isoformat(),
        "end_date": lease.end_date.isoformat()
    }
    
    # Mettre à jour les champs
    update_data = lease_update.dict(exclude_unset=True)
    
    # Vérifications spéciales pour les dates
    if 'start_date' in update_data or 'end_date' in update_data:
        new_start = update_data.get('start_date', lease.start_date)
        new_end = update_data.get('end_date', lease.end_date)
        
        if new_end <= new_start:
            raise HTTPException(
                status_code=400,
                detail="La date de fin doit être postérieure à la date de début"
            )
        
        # Vérifier les conflits avec d'autres baux
        conflicting_lease = db.query(Lease).filter(
            Lease.apartment_id == lease.apartment_id,
            Lease.id != lease_id,
            Lease.status.in_(["ACTIVE", "PENDING"]),
            Lease.start_date <= new_end,
            Lease.end_date >= new_start
        ).first()
        
        if conflicting_lease:
            raise HTTPException(
                status_code=400,
                detail="Conflit avec un autre bail existant"
            )
    
    for field, value in update_data.items():
        if hasattr(lease, field):
            setattr(lease, field, value)
    
    lease.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lease)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    new_values = {
        "monthly_rent": str(lease.monthly_rent),
        "charges": str(lease.charges),
        "status": lease.status.value,
        "start_date": lease.start_date.isoformat(),
        "end_date": lease.end_date.isoformat()
    }
    
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="LEASE",
        entity_id=lease_id,
        description=f"Modification du bail #{lease_id}",
        details=json.dumps({
            "lease_id": lease_id,
            "old_values": old_values,
            "new_values": new_values
        })
    )
    
    return lease

@router.delete("/{lease_id}")
async def delete_lease(
    lease_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un bail"""
    
    lease = check_lease_access(lease_id, current_user, db)
    
    # Vérifier que le bail peut être supprimé
    if lease.status == "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un bail actif. Veuillez d'abord le résilier."
        )
    
    lease_info = {
        "lease_id": lease_id,
        "tenant_id": lease.tenant_id,
        "apartment_id": lease.apartment_id,
        "status": lease.status.value
    }
    
    db.delete(lease)
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="LEASE",
        entity_id=lease_id,
        description=f"Suppression du bail #{lease_id}",
        details=json.dumps(lease_info)
    )
    
    return {"message": f"Bail #{lease_id} supprimé avec succès"}

@router.post("/{lease_id}/terminate")
async def terminate_lease(
    lease_id: int,
    termination_date: Optional[date] = None,
    reason: Optional[str] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Résilie un bail"""
    
    lease = check_lease_access(lease_id, current_user, db)
    
    if lease.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Seuls les baux actifs peuvent être résiliés"
        )
    
    # Date de résiliation par défaut = aujourd'hui
    if not termination_date:
        termination_date = date.today()
    
    # Mettre à jour le bail
    lease.status = LeaseStatus.TERMINATED
    lease.end_date = datetime.combine(termination_date, datetime.min.time())
    if reason:
        lease.notes = f"{lease.notes or ''}\nRésiliation le {termination_date}: {reason}".strip()
    
    db.commit()
    db.refresh(lease)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="LEASE",
        entity_id=lease_id,
        description=f"Résiliation du bail #{lease_id}",
        details=json.dumps({
            "lease_id": lease_id,
            "termination_date": termination_date.isoformat(),
            "reason": reason
        })
    )
    
    return {"message": f"Bail #{lease_id} résilié avec succès", "lease": lease}

@router.post("/{lease_id}/renew")
async def renew_lease(
    lease_id: int,
    new_end_date: date,
    new_rent: Optional[float] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Renouvelle un bail"""
    
    lease = check_lease_access(lease_id, current_user, db)
    
    if lease.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Seuls les baux actifs peuvent être renouvelés"
        )
    
    if not lease.renewable:
        raise HTTPException(
            status_code=400,
            detail="Ce bail n'est pas renouvelable"
        )
    
    # Vérifier que la nouvelle date est postérieure
    if new_end_date <= lease.end_date.date():
        raise HTTPException(
            status_code=400,
            detail="La nouvelle date de fin doit être postérieure à l'actuelle"
        )
    
    old_end_date = lease.end_date
    old_rent = lease.monthly_rent
    
    # Mettre à jour le bail
    lease.end_date = datetime.combine(new_end_date, datetime.min.time())
    if new_rent:
        lease.monthly_rent = new_rent
    
    db.commit()
    db.refresh(lease)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="LEASE",
        entity_id=lease_id,
        description=f"Renouvellement du bail #{lease_id}",
        details=json.dumps({
            "lease_id": lease_id,
            "old_end_date": old_end_date.isoformat(),
            "new_end_date": new_end_date.isoformat(),
            "old_rent": str(old_rent),
            "new_rent": str(lease.monthly_rent)
        })
    )
    
    return {"message": f"Bail #{lease_id} renouvelé avec succès", "lease": lease}

@router.get("/expiring/", response_model=List[LeaseWithDetails])
async def get_expiring_leases(
    days: int = 30,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les baux qui expirent dans les X jours"""
    
    from datetime import timedelta
    
    cutoff_date = datetime.now() + timedelta(days=days)
    
    leases = db.query(Lease).options(
        joinedload(Lease.tenant),
        joinedload(Lease.apartment)
    ).filter(
        Lease.created_by == current_user.id,
        Lease.status == "ACTIVE",
        Lease.end_date <= cutoff_date
    ).order_by(Lease.end_date.asc()).all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="LEASE",
        description=f"Consultation des baux expirant dans {days} jours ({len(leases)} baux)",
        details=json.dumps({
            "days": days,
            "expiring_leases_count": len(leases)
        })
    )
    
    return leases