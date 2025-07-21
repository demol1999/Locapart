"""
Routes API pour la gestion multi-acteurs des propriétés
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import UserAuth, Apartment, Building
from property_management_models import (
    ManagementCompany, PropertyManagement, PropertyOwnership,
    TenantOccupancy, UserPermission, PermissionTemplate, AccessLog,
    UserRole, PermissionType, PropertyScope
)
from property_management_schemas import (
    ManagementCompanyCreate, ManagementCompanyUpdate, ManagementCompanyOut,
    PropertyManagementCreate, PropertyManagementUpdate, PropertyManagementOut,
    PropertyOwnershipCreate, PropertyOwnershipUpdate, PropertyOwnershipOut,
    TenantOccupancyCreate, TenantOccupancyUpdate, TenantOccupancyOut,
    UserPermissionCreate, UserPermissionOut,
    PermissionTemplateCreate, PermissionTemplateOut,
    UserDashboardData, PropertyStakeholders, ApartmentSummary,
    GrantPermissionRequest, RevokePermissionRequest, ApplyRoleRequest,
    TransferOwnershipRequest, AssignManagerRequest,
    AccessLogOut, AccessStatistics, PermissionAuditReport,
    UserRoleEnum, PermissionTypeEnum, PropertyScopeEnum
)
from permission_service import create_permission_service, PermissionService
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/property-management", tags=["Gestion Multi-Acteurs"])


def get_permission_service(db: Session = Depends(get_db)) -> PermissionService:
    """Dependency pour obtenir le service de permissions"""
    return create_permission_service(db)


def require_permission(
    permission: PermissionType,
    resource_type: str = "apartment",
    resource_id: Optional[int] = None
):
    """Décorateur de dépendance pour vérifier les permissions"""
    def permission_checker(
        current_user: UserAuth = Depends(get_current_user),
        perm_service: PermissionService = Depends(get_permission_service)
    ):
        perm_service.require_permission(current_user.id, permission, resource_type, resource_id)
        return current_user
    return permission_checker


# ==================== SOCIÉTÉS DE GESTION ====================

@router.post("/companies", response_model=ManagementCompanyOut)
async def create_management_company(
    company: ManagementCompanyCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(require_permission(PermissionType.CREATE, "company"))
):
    """Créer une nouvelle société de gestion"""
    
    # Vérifier l'unicité du SIRET si fourni
    if company.siret:
        existing = db.query(ManagementCompany).filter(
            ManagementCompany.siret == company.siret
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Une société avec ce SIRET existe déjà"
            )
    
    company_obj = ManagementCompany(**company.dict())
    db.add(company_obj)
    db.commit()
    db.refresh(company_obj)
    
    # Log de création
    AuditLogger.log_crud_action(
        db=db,
        action="CREATE",
        entity_type="MANAGEMENT_COMPANY",
        entity_id=company_obj.id,
        user_id=current_user.id,
        description=f"Création de la société de gestion: {company_obj.name}"
    )
    
    return company_obj


@router.get("/companies", response_model=List[ManagementCompanyOut])
async def list_management_companies(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(require_permission(PermissionType.VIEW, "company"))
):
    """Lister les sociétés de gestion"""
    
    query = db.query(ManagementCompany)
    
    if active_only:
        query = query.filter(ManagementCompany.is_active == True)
    
    companies = query.order_by(ManagementCompany.name).all()
    return companies


@router.get("/companies/{company_id}", response_model=ManagementCompanyOut)
async def get_management_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(require_permission(PermissionType.VIEW, "company"))
):
    """Récupérer une société de gestion"""
    
    company = db.query(ManagementCompany).filter(
        ManagementCompany.id == company_id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Société de gestion introuvable")
    
    return company


@router.put("/companies/{company_id}", response_model=ManagementCompanyOut)
async def update_management_company(
    company_id: int,
    company_update: ManagementCompanyUpdate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(require_permission(PermissionType.EDIT, "company"))
):
    """Mettre à jour une société de gestion"""
    
    company = db.query(ManagementCompany).filter(
        ManagementCompany.id == company_id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Société de gestion introuvable")
    
    # Vérifier l'unicité du SIRET si modifié
    if company_update.siret and company_update.siret != company.siret:
        existing = db.query(ManagementCompany).filter(
            ManagementCompany.siret == company_update.siret,
            ManagementCompany.id != company_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Une société avec ce SIRET existe déjà"
            )
    
    # Mettre à jour les champs
    for key, value in company_update.dict(exclude_unset=True).items():
        setattr(company, key, value)
    
    db.commit()
    db.refresh(company)
    
    return company


# ==================== GESTION DE PROPRIÉTÉS ====================

@router.post("/property-management", response_model=PropertyManagementOut)
async def create_property_management(
    management: PropertyManagementCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Créer un contrat de gestion de propriété"""
    
    # Vérifier les permissions sur l'appartement
    perm_service.require_permission(
        current_user.id, PermissionType.MANAGE_LEASES, "apartment", management.apartment_id
    )
    
    # Vérifier que l'appartement et la société existent
    apartment = db.query(Apartment).filter(Apartment.id == management.apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    company = db.query(ManagementCompany).filter(
        ManagementCompany.id == management.management_company_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Société de gestion introuvable")
    
    # Vérifier qu'il n'y a pas déjà un contrat actif
    existing = db.query(PropertyManagement).filter(
        PropertyManagement.apartment_id == management.apartment_id,
        PropertyManagement.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Un contrat de gestion actif existe déjà pour cet appartement"
        )
    
    # Créer le contrat
    management_data = management.dict()
    delegated_permissions = {
        "permissions": [p.value for p in management_data.pop("delegated_permissions")]
    }
    
    management_obj = PropertyManagement(
        **management_data,
        delegated_permissions=delegated_permissions
    )
    
    db.add(management_obj)
    db.commit()
    db.refresh(management_obj)
    
    # Accorder les permissions au gestionnaire
    for permission in delegated_permissions["permissions"]:
        perm_service.manager.grant_permission(
            user_id=management.managed_by,
            permission=PermissionType(permission),
            resource_type="apartment",
            resource_id=management.apartment_id,
            scope=PropertyScope.APARTMENT,
            granted_by=current_user.id
        )
    
    return management_obj


@router.get("/property-management", response_model=List[PropertyManagementOut])
async def list_property_management(
    apartment_id: Optional[int] = None,
    company_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Lister les contrats de gestion"""
    
    query = db.query(PropertyManagement)
    
    if apartment_id:
        # Vérifier les permissions sur cet appartement
        perm_service.require_permission(
            current_user.id, PermissionType.VIEW, "apartment", apartment_id
        )
        query = query.filter(PropertyManagement.apartment_id == apartment_id)
    else:
        # Filtrer par les appartements accessibles
        accessible_apartments = perm_service.checker.get_accessible_resources(
            current_user.id, "apartment", PermissionType.VIEW
        )
        if accessible_apartments:
            query = query.filter(PropertyManagement.apartment_id.in_(accessible_apartments))
        else:
            return []  # Aucun appartement accessible
    
    if company_id:
        query = query.filter(PropertyManagement.management_company_id == company_id)
    
    if active_only:
        query = query.filter(PropertyManagement.is_active == True)
    
    managements = query.order_by(PropertyManagement.created_at.desc()).all()
    return managements


# ==================== MULTI-PROPRIÉTÉ ====================

@router.post("/ownership", response_model=PropertyOwnershipOut)
async def create_property_ownership(
    ownership: PropertyOwnershipCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Créer un lien de propriété"""
    
    # Vérifier les permissions
    perm_service.require_permission(
        current_user.id, PermissionType.EDIT, "apartment", ownership.apartment_id
    )
    
    # Vérifier que l'appartement existe
    apartment = db.query(Apartment).filter(Apartment.id == ownership.apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # Vérifier que l'utilisateur propriétaire existe
    owner = db.query(UserAuth).filter(UserAuth.id == ownership.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Utilisateur propriétaire introuvable")
    
    # Vérifier la somme des pourcentages
    current_total = db.query(PropertyOwnership).filter(
        PropertyOwnership.apartment_id == ownership.apartment_id,
        PropertyOwnership.is_active == True
    ).all()
    
    total_percentage = sum(o.ownership_percentage for o in current_total) + ownership.ownership_percentage
    
    if total_percentage > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Pourcentage total dépassé: {total_percentage}% > 100%"
        )
    
    # Créer la propriété
    ownership_obj = PropertyOwnership(**ownership.dict())
    db.add(ownership_obj)
    db.commit()
    db.refresh(ownership_obj)
    
    # Accorder les permissions de propriétaire
    owner_permissions = [
        PermissionType.VIEW, PermissionType.EDIT,
        PermissionType.ACCESS_REPORTS, PermissionType.MANAGE_FINANCES
    ]
    
    if ownership.can_sign_leases:
        owner_permissions.append(PermissionType.SIGN_DOCUMENTS)
    
    for permission in owner_permissions:
        perm_service.manager.grant_permission(
            user_id=ownership.owner_id,
            permission=permission,
            resource_type="apartment",
            resource_id=ownership.apartment_id,
            scope=PropertyScope.APARTMENT,
            granted_by=current_user.id
        )
    
    return ownership_obj


@router.get("/ownership", response_model=List[PropertyOwnershipOut])
async def list_property_ownerships(
    apartment_id: Optional[int] = None,
    owner_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Lister les propriétés"""
    
    query = db.query(PropertyOwnership)
    
    if apartment_id:
        # Vérifier les permissions sur cet appartement
        perm_service.require_permission(
            current_user.id, PermissionType.VIEW, "apartment", apartment_id
        )
        query = query.filter(PropertyOwnership.apartment_id == apartment_id)
    else:
        # Filtrer par les appartements accessibles
        accessible_apartments = perm_service.checker.get_accessible_resources(
            current_user.id, "apartment", PermissionType.VIEW
        )
        if accessible_apartments:
            query = query.filter(PropertyOwnership.apartment_id.in_(accessible_apartments))
        else:
            return []
    
    if owner_id:
        query = query.filter(PropertyOwnership.owner_id == owner_id)
    
    if active_only:
        query = query.filter(PropertyOwnership.is_active == True)
    
    ownerships = query.order_by(PropertyOwnership.ownership_percentage.desc()).all()
    return ownerships


# ==================== MULTI-LOCATION ====================

@router.post("/occupancy", response_model=TenantOccupancyOut)
async def create_tenant_occupancy(
    occupancy: TenantOccupancyCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Créer une occupation locative"""
    
    # Vérifier les permissions
    perm_service.require_permission(
        current_user.id, PermissionType.MANAGE_TENANTS, "apartment", occupancy.apartment_id
    )
    
    # Vérifier que l'appartement existe
    apartment = db.query(Apartment).filter(Apartment.id == occupancy.apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # Vérifier que le locataire existe
    tenant = db.query(UserAuth).filter(UserAuth.id == occupancy.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Utilisateur locataire introuvable")
    
    # Vérifier la somme des responsabilités de loyer
    current_occupancies = db.query(TenantOccupancy).filter(
        TenantOccupancy.apartment_id == occupancy.apartment_id,
        TenantOccupancy.is_active == True
    ).all()
    
    total_responsibility = sum(o.rent_responsibility for o in current_occupancies) + occupancy.rent_responsibility
    
    if total_responsibility > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Responsabilité totale dépassée: {total_responsibility}% > 100%"
        )
    
    # Créer l'occupation
    occupancy_obj = TenantOccupancy(**occupancy.dict())
    db.add(occupancy_obj)
    db.commit()
    db.refresh(occupancy_obj)
    
    # Accorder les permissions de locataire
    perm_service.manager.grant_permission(
        user_id=occupancy.tenant_id,
        permission=PermissionType.VIEW,
        resource_type="apartment",
        resource_id=occupancy.apartment_id,
        scope=PropertyScope.TENANT_ONLY,
        granted_by=current_user.id
    )
    
    return occupancy_obj


@router.get("/occupancy", response_model=List[TenantOccupancyOut])
async def list_tenant_occupancies(
    apartment_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Lister les occupations locatives"""
    
    query = db.query(TenantOccupancy)
    
    if apartment_id:
        # Vérifier les permissions sur cet appartement
        perm_service.require_permission(
            current_user.id, PermissionType.VIEW, "apartment", apartment_id
        )
        query = query.filter(TenantOccupancy.apartment_id == apartment_id)
    else:
        # Filtrer par les appartements accessibles
        accessible_apartments = perm_service.checker.get_accessible_resources(
            current_user.id, "apartment", PermissionType.VIEW
        )
        if accessible_apartments:
            query = query.filter(TenantOccupancy.apartment_id.in_(accessible_apartments))
        else:
            return []
    
    if tenant_id:
        query = query.filter(TenantOccupancy.tenant_id == tenant_id)
    
    if active_only:
        query = query.filter(TenantOccupancy.is_active == True)
    
    occupancies = query.order_by(TenantOccupancy.rent_responsibility.desc()).all()
    return occupancies


# ==================== DASHBOARD ET VUE D'ENSEMBLE ====================

@router.get("/dashboard", response_model=UserDashboardData)
async def get_user_dashboard(
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Récupérer le dashboard de l'utilisateur"""
    
    dashboard_data = perm_service.get_user_dashboard_data(current_user.id)
    return UserDashboardData(**dashboard_data)


@router.get("/apartments/{apartment_id}/stakeholders", response_model=PropertyStakeholders)
async def get_apartment_stakeholders(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Récupérer tous les acteurs d'un appartement"""
    
    # Vérifier les permissions
    perm_service.require_permission(
        current_user.id, PermissionType.VIEW, "apartment", apartment_id
    )
    
    # Propriétaires
    ownerships = db.query(PropertyOwnership).options(
        joinedload(PropertyOwnership.owner)
    ).filter(
        PropertyOwnership.apartment_id == apartment_id,
        PropertyOwnership.is_active == True
    ).all()
    
    owners = [
        {
            "user_id": o.owner_id,
            "user_name": f"{o.owner.first_name} {o.owner.last_name}",
            "user_email": o.owner.email,
            "percentage": float(o.ownership_percentage),
            "ownership_type": o.ownership_type,
            "can_sign_leases": o.can_sign_leases,
            "can_authorize_works": o.can_authorize_works
        }
        for o in ownerships
    ]
    
    # Locataires
    occupancies = db.query(TenantOccupancy).options(
        joinedload(TenantOccupancy.tenant)
    ).filter(
        TenantOccupancy.apartment_id == apartment_id,
        TenantOccupancy.is_active == True
    ).all()
    
    tenants = [
        {
            "user_id": o.tenant_id,
            "user_name": f"{o.tenant.first_name} {o.tenant.last_name}",
            "user_email": o.tenant.email,
            "occupancy_type": o.occupancy_type,
            "rent_responsibility": float(o.rent_responsibility),
            "move_in_date": o.move_in_date
        }
        for o in occupancies
    ]
    
    # Gestionnaires
    managements = db.query(PropertyManagement).options(
        joinedload(PropertyManagement.manager),
        joinedload(PropertyManagement.management_company)
    ).filter(
        PropertyManagement.apartment_id == apartment_id,
        PropertyManagement.is_active == True
    ).all()
    
    managers = [
        {
            "user_id": m.managed_by,
            "user_name": f"{m.manager.first_name} {m.manager.last_name}",
            "user_email": m.manager.email,
            "company_name": m.management_company.name,
            "contract_type": m.contract_type,
            "delegated_permissions": m.delegated_permissions
        }
        for m in managements
    ]
    
    # Société de gestion
    management_company = None
    if managements:
        company = managements[0].management_company
        management_company = {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "phone": company.phone,
            "license_number": company.license_number
        }
    
    return PropertyStakeholders(
        apartment_id=apartment_id,
        owners=owners,
        tenants=tenants,
        managers=managers,
        management_company=management_company
    )


# ==================== GESTION DES PERMISSIONS ====================

@router.post("/permissions/grant")
async def grant_permission(
    request: GrantPermissionRequest,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Accorder une permission à un utilisateur"""
    
    # Vérifier que l'utilisateur courant peut accorder cette permission
    perm_service.require_permission(
        current_user.id, request.permission_type, request.resource_type, request.resource_id
    )
    
    # Accorder la permission
    success = perm_service.manager.grant_permission(
        user_id=request.user_id,
        permission=request.permission_type,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        scope=request.scope,
        granted_by=current_user.id,
        expires_at=request.expires_at
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'octroi de la permission"
        )
    
    return {"message": "Permission accordée avec succès"}


@router.post("/permissions/revoke")
async def revoke_permission(
    request: RevokePermissionRequest,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Révoquer une permission d'un utilisateur"""
    
    # Vérifier que l'utilisateur courant peut révoquer cette permission
    perm_service.require_permission(
        current_user.id, request.permission_type, request.resource_type, request.resource_id
    )
    
    # Révoquer la permission
    success = perm_service.manager.revoke_permission(
        user_id=request.user_id,
        permission=request.permission_type,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        revoked_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la révocation de la permission"
        )
    
    return {"message": "Permission révoquée avec succès"}


@router.get("/permissions/user/{user_id}", response_model=List[UserPermissionOut])
async def get_user_permissions(
    user_id: int,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Récupérer les permissions d'un utilisateur"""
    
    # Vérifier que l'utilisateur courant peut voir ces permissions
    if user_id != current_user.id:
        perm_service.require_permission(
            current_user.id, PermissionType.VIEW, "user", user_id
        )
    
    permissions_data = perm_service.checker.get_user_permissions(user_id, resource_type)
    
    # Récupérer les permissions directes de la base
    query = db.query(UserPermission).filter(
        UserPermission.user_id == user_id,
        UserPermission.is_active == True
    )
    
    if resource_type:
        query = query.filter(UserPermission.resource_type == resource_type)
    
    permissions = query.all()
    return permissions


# ==================== LOGS ET STATISTIQUES ====================

@router.get("/access-logs", response_model=List[AccessLogOut])
async def get_access_logs(
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(require_permission(PermissionType.ACCESS_REPORTS))
):
    """Récupérer les logs d'accès"""
    
    query = db.query(AccessLog)
    
    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    
    if resource_type:
        query = query.filter(AccessLog.resource_type == resource_type)
    
    logs = query.order_by(
        AccessLog.timestamp.desc()
    ).offset(offset).limit(limit).all()
    
    return logs


@router.get("/statistics/access/{user_id}", response_model=AccessStatistics)
async def get_user_access_statistics(
    user_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user),
    perm_service: PermissionService = Depends(get_permission_service)
):
    """Récupérer les statistiques d'accès d'un utilisateur"""
    
    # Vérifier les permissions
    if user_id != current_user.id:
        perm_service.require_permission(
            current_user.id, PermissionType.ACCESS_REPORTS, "user", user_id
        )
    
    from datetime import timedelta
    from sqlalchemy import func
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Statistiques générales
    total_accesses = db.query(AccessLog).filter(
        AccessLog.user_id == user_id,
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date
    ).count()
    
    successful_accesses = db.query(AccessLog).filter(
        AccessLog.user_id == user_id,
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.success == True
    ).count()
    
    failed_accesses = total_accesses - successful_accesses
    
    # Permissions les plus utilisées
    most_used_permissions = db.query(
        AccessLog.permission_used,
        func.count(AccessLog.id).label('count')
    ).filter(
        AccessLog.user_id == user_id,
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.permission_used.isnot(None)
    ).group_by(AccessLog.permission_used).order_by(
        func.count(AccessLog.id).desc()
    ).limit(10).all()
    
    # Ressources les plus accédées
    accessed_resources = db.query(
        AccessLog.resource_type,
        AccessLog.resource_id,
        func.count(AccessLog.id).label('count')
    ).filter(
        AccessLog.user_id == user_id,
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date
    ).group_by(
        AccessLog.resource_type, AccessLog.resource_id
    ).order_by(
        func.count(AccessLog.id).desc()
    ).limit(10).all()
    
    # Temps de réponse moyen
    avg_response_time = db.query(
        func.avg(AccessLog.response_time)
    ).filter(
        AccessLog.user_id == user_id,
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.response_time.isnot(None)
    ).scalar()
    
    return AccessStatistics(
        user_id=user_id,
        period_start=start_date,
        period_end=end_date,
        total_accesses=total_accesses,
        successful_accesses=successful_accesses,
        failed_accesses=failed_accesses,
        most_used_permissions=[
            {"permission": perm, "count": count}
            for perm, count in most_used_permissions
        ],
        accessed_resources=[
            {"resource_type": rt, "resource_id": rid, "count": count}
            for rt, rid, count in accessed_resources
        ],
        average_response_time=float(avg_response_time) if avg_response_time else None
    )