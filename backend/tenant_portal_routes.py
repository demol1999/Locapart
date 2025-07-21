"""
Routes API pour l'espace locataire (portail)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
from datetime import datetime

from database import get_db
from models import (
    Tenant, Lease, TenantDocument, Inventory, Apartment, Building, LeaseStatus
)
from schemas import (
    TenantPortalInfo, TenantLoginRequest, TenantOut, LeaseOut, 
    TenantDocumentOut, InventoryOut, ApartmentOut, BuildingOut
)
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/tenant-portal", tags=["tenant-portal"])

def get_tenant_by_email(email: str, db: Session) -> Optional[Tenant]:
    """Récupère un locataire par email"""
    return db.query(Tenant).filter(Tenant.email == email).first()

def get_active_lease_for_tenant(tenant_id: int, db: Session) -> Optional[Lease]:
    """Récupère le bail actif d'un locataire"""
    return db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.status == LeaseStatus.ACTIVE
    ).first()

@router.post("/login", response_model=TenantPortalInfo)
async def tenant_login(
    login_request: TenantLoginRequest,
    db: Session = Depends(get_db)
):
    """Connexion d'un locataire à son espace"""
    
    # Rechercher le locataire par email
    tenant = get_tenant_by_email(login_request.email, db)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Aucun locataire trouvé avec cet email"
        )
    
    # Récupérer le bail actif
    current_lease = get_active_lease_for_tenant(tenant.id, db)
    if not current_lease:
        raise HTTPException(
            status_code=404,
            detail="Aucun bail actif trouvé pour ce locataire"
        )
    
    # Charger les informations complètes
    apartment_info = None
    building_info = None
    if current_lease.apartment_id:
        apartment = db.query(Apartment).options(
            joinedload(Apartment.building)
        ).filter(Apartment.id == current_lease.apartment_id).first()
        
        if apartment:
            apartment_info = apartment
            building_info = apartment.building
    
    # Récupérer les documents
    documents = db.query(TenantDocument).filter(
        TenantDocument.tenant_id == tenant.id
    ).order_by(TenantDocument.created_at.desc()).all()
    
    # Récupérer les états des lieux
    inventories = db.query(Inventory).filter(
        Inventory.lease_id == current_lease.id
    ).order_by(Inventory.conducted_date.desc()).all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=None,  # Pas d'utilisateur authentifié classique
        action="LOGIN",
        entity_type="TENANT",
        entity_id=tenant.id,
        description=f"Connexion locataire: {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant.id,
            "tenant_email": tenant.email,
            "lease_id": current_lease.id if current_lease else None
        })
    )
    
    return TenantPortalInfo(
        tenant=tenant,
        current_lease=current_lease,
        apartment_info=apartment_info,
        building_info=building_info,
        documents=documents,
        inventories=inventories
    )

@router.get("/tenant/{tenant_id}/info", response_model=TenantPortalInfo)
async def get_tenant_portal_info(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère toutes les informations de l'espace locataire"""
    
    # Vérifier que le locataire existe
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Récupérer le bail actif
    current_lease = get_active_lease_for_tenant(tenant_id, db)
    
    # Informations de l'appartement et immeuble
    apartment_info = None
    building_info = None
    if current_lease and current_lease.apartment_id:
        apartment = db.query(Apartment).options(
            joinedload(Apartment.building)
        ).filter(Apartment.id == current_lease.apartment_id).first()
        
        if apartment:
            apartment_info = apartment
            building_info = apartment.building
    
    # Documents du locataire
    documents = db.query(TenantDocument).filter(
        TenantDocument.tenant_id == tenant_id
    ).order_by(TenantDocument.created_at.desc()).all()
    
    # États des lieux
    inventories = []
    if current_lease:
        inventories = db.query(Inventory).filter(
            Inventory.lease_id == current_lease.id
        ).order_by(Inventory.conducted_date.desc()).all()
    
    return TenantPortalInfo(
        tenant=tenant,
        current_lease=current_lease,
        apartment_info=apartment_info,
        building_info=building_info,
        documents=documents,
        inventories=inventories
    )

@router.get("/tenant/{tenant_id}/documents", response_model=List[TenantDocumentOut])
async def get_tenant_portal_documents(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère les documents accessibles au locataire"""
    
    # Vérifier que le locataire existe
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Récupérer les documents (seulement ceux visibles au locataire)
    documents = db.query(TenantDocument).filter(
        TenantDocument.tenant_id == tenant_id,
        TenantDocument.document_type.in_([
            "LEASE", "INVENTORY", "RENT_RECEIPT", "DEPOSIT_RECEIPT"
        ])  # Types de documents que le locataire peut voir
    ).order_by(TenantDocument.created_at.desc()).all()
    
    return documents

@router.get("/tenant/{tenant_id}/lease", response_model=LeaseOut)
async def get_tenant_current_lease(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère le bail actuel du locataire"""
    
    # Vérifier que le locataire existe
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Récupérer le bail actif
    current_lease = get_active_lease_for_tenant(tenant_id, db)
    if not current_lease:
        raise HTTPException(
            status_code=404,
            detail="Aucun bail actif trouvé"
        )
    
    return current_lease

@router.get("/tenant/{tenant_id}/apartment", response_model=ApartmentOut)
async def get_tenant_apartment_info(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère les informations de l'appartement du locataire"""
    
    # Récupérer le bail actif
    current_lease = get_active_lease_for_tenant(tenant_id, db)
    if not current_lease:
        raise HTTPException(
            status_code=404,
            detail="Aucun bail actif trouvé"
        )
    
    # Récupérer l'appartement
    apartment = db.query(Apartment).filter(
        Apartment.id == current_lease.apartment_id
    ).first()
    
    if not apartment:
        raise HTTPException(
            status_code=404,
            detail="Informations de l'appartement indisponibles"
        )
    
    return apartment

@router.get("/tenant/{tenant_id}/building", response_model=BuildingOut)
async def get_tenant_building_info(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère les informations de l'immeuble du locataire"""
    
    # Récupérer le bail actif
    current_lease = get_active_lease_for_tenant(tenant_id, db)
    if not current_lease:
        raise HTTPException(
            status_code=404,
            detail="Aucun bail actif trouvé"
        )
    
    # Récupérer l'appartement et l'immeuble
    apartment = db.query(Apartment).options(
        joinedload(Apartment.building)
    ).filter(Apartment.id == current_lease.apartment_id).first()
    
    if not apartment or not apartment.building:
        raise HTTPException(
            status_code=404,
            detail="Informations de l'immeuble indisponibles"
        )
    
    return apartment.building

@router.get("/tenant/{tenant_id}/inventories", response_model=List[InventoryOut])
async def get_tenant_inventories(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère les états des lieux du locataire"""
    
    # Récupérer le bail actif
    current_lease = get_active_lease_for_tenant(tenant_id, db)
    if not current_lease:
        raise HTTPException(
            status_code=404,
            detail="Aucun bail actif trouvé"
        )
    
    # Récupérer les états des lieux
    inventories = db.query(Inventory).filter(
        Inventory.lease_id == current_lease.id
    ).order_by(Inventory.conducted_date.desc()).all()
    
    return inventories

@router.get("/tenant/{tenant_id}/lease-history", response_model=List[LeaseOut])
async def get_tenant_lease_history(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Récupère l'historique des baux du locataire"""
    
    # Vérifier que le locataire existe
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Récupérer tous les baux du locataire
    leases = db.query(Lease).filter(
        Lease.tenant_id == tenant_id
    ).order_by(Lease.start_date.desc()).all()
    
    return leases

@router.get("/tenant/search/{email}")
async def find_tenant_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """Recherche un locataire par email (pour la page de connexion)"""
    
    tenant = get_tenant_by_email(email, db)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Aucun locataire trouvé avec cet email"
        )
    
    # Vérifier s'il a un bail actif
    active_lease = get_active_lease_for_tenant(tenant.id, db)
    
    return {
        "tenant_found": True,
        "tenant_name": f"{tenant.first_name} {tenant.last_name}",
        "has_active_lease": active_lease is not None,
        "tenant_id": tenant.id
    }

@router.post("/tenant/{tenant_id}/contact-landlord")
async def contact_landlord(
    tenant_id: int,
    message: str,
    subject: str = "Message du locataire",
    db: Session = Depends(get_db)
):
    """Permet au locataire de contacter son propriétaire"""
    
    # Récupérer le locataire et son bail
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    current_lease = get_active_lease_for_tenant(tenant_id, db)
    if not current_lease:
        raise HTTPException(
            status_code=404,
            detail="Aucun bail actif trouvé"
        )
    
    # Log du message (dans un vrai système, on enverrait un email)
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=None,
        action="CREATE",
        entity_type="TENANT",
        entity_id=tenant_id,
        description=f"Message du locataire {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "tenant_id": tenant_id,
            "landlord_id": current_lease.created_by,
            "subject": subject,
            "message": message[:500]  # Tronquer pour les logs
        })
    )
    
    # Ici, dans un vrai système, on enverrait un email au propriétaire
    # Pour l'instant, on retourne juste une confirmation
    
    return {
        "message": "Votre message a été envoyé au propriétaire",
        "sent_to": f"Propriétaire (ID: {current_lease.created_by})",
        "subject": subject
    }