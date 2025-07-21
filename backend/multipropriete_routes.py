"""
Routes pour le système de multipropriété
APIs pour gérer les groupes de propriété partagée
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database import get_db
from auth import get_current_user
from models import UserAuth
from models_multipropriete import PropertyGroup, PropertyGroupMember, PropertyGroupInvitation
from services.multipropriete_service import MultiproprietService
from services.subscription_service import SubscriptionService
from schemas_multipropriete import (
    PropertyGroupCreate, PropertyGroupUpdate, PropertyGroupOut,
    PropertyGroupMemberOut, PropertyGroupMemberUpdate,
    GroupInvitationCreate, GroupInvitationResponse, PropertyGroupInvitationOut,
    MultiproprieteDashboardOut, UserApartmentsAccessOut,
    AddApartmentToGroupRequest, RemoveApartmentFromGroupRequest,
    LeaveGroupRequest, GroupSearchFilters, GroupStatistics
)
from error_handlers import PermissionErrorHandler, BusinessLogicErrorHandler, ErrorLogger
from audit_logger import AuditLogger
from enums import ActionType, EntityType
from rate_limiter import check_rate_limit

router = APIRouter(prefix="/api/multipropriete", tags=["Multipropriété"])


# ==================== TABLEAU DE BORD ====================

@router.get("/dashboard", response_model=MultiproprieteDashboardOut)
async def get_multipropriete_dashboard(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère le tableau de bord complet de multipropriété
    """
    try:
        dashboard = MultiproprietService.get_user_multipropriete_dashboard(db, current_user.id)
        
        # Compter les invitations en attente
        pending_received = db.query(PropertyGroupInvitation).filter(
            PropertyGroupInvitation.invited_user_id == current_user.id,
            PropertyGroupInvitation.status == "pending"
        ).count()
        
        pending_sent = db.query(PropertyGroupInvitation).join(PropertyGroup).filter(
            PropertyGroup.sponsor_id == current_user.id,
            PropertyGroupInvitation.status == "pending"
        ).count()
        
        # Convertir en schéma de réponse
        return MultiproprieteDashboardOut(
            personal_apartments=dashboard.personal_apartments,
            sponsored_apartments=dashboard.sponsored_apartments,
            accessible_apartments=dashboard.accessible_apartments,
            total_accessible_apartments=dashboard.total_accessible_apartments,
            personal_quota={
                "current_count": dashboard.personal_quota_used,
                "limit": dashboard.personal_quota_max,
                "remaining": dashboard.personal_quota_max - dashboard.personal_quota_used if dashboard.personal_quota_max > 0 else -1,
                "is_unlimited": dashboard.personal_quota_max == -1,
                "can_add_more": dashboard.can_add_personal_apartment
            },
            can_create_groups=dashboard.can_create_groups,
            is_premium=SubscriptionService.has_premium_subscription(db, current_user.id),
            sponsored_groups=dashboard.sponsored_groups,
            member_groups=dashboard.member_groups,
            pending_invitations_received=pending_received,
            pending_invitations_sent=pending_sent
        )
        
    except Exception as e:
        ErrorLogger.log_error(
            BusinessLogicErrorHandler.rate_limit_exceeded(),
            db, None, current_user.id, {"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du tableau de bord")


@router.get("/my-apartments", response_model=UserApartmentsAccessOut)
async def get_my_accessible_apartments(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les appartements accessibles (personnels + groupes)
    """
    try:
        apartments_data = MultiproprietService.get_user_accessible_apartments(db, current_user.id)
        
        # Transformer en format de réponse
        apartments_info = []
        for apt_data in apartments_data:
            apartment = apt_data["apartment"]
            
            # Déterminer les permissions
            can_edit = apt_data["access_type"] in ["personal", "sponsored"]
            can_delete = apt_data["access_type"] == "personal"
            can_invite_tenants = apt_data["access_type"] in ["personal", "sponsored"]
            can_manage_finances = apt_data["access_type"] in ["personal", "sponsored"]
            
            apartments_info.append({
                "apartment_id": apartment.id,
                "apartment_name": apartment.name,
                "building_name": apartment.building.name if apartment.building else None,
                "access_type": apt_data["access_type"],
                "role": apt_data["role"],
                "group_name": apt_data["group_name"],
                "sponsor_email": apt_data["sponsor_email"],
                "can_edit": can_edit,
                "can_delete": can_delete,
                "can_invite_tenants": can_invite_tenants,
                "can_manage_finances": can_manage_finances
            })
        
        # Compter par type
        personal_count = len([a for a in apartments_data if a["access_type"] == "personal"])
        sponsored_count = len([a for a in apartments_data if a["access_type"] == "sponsored"])
        member_count = len([a for a in apartments_data if a["access_type"] == "member"])
        
        return UserApartmentsAccessOut(
            apartments=apartments_info,
            total_count=len(apartments_info),
            personal_count=personal_count,
            sponsored_count=sponsored_count,
            member_count=member_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des appartements")


# ==================== GESTION DES GROUPES ====================

@router.post("/groups", response_model=PropertyGroupOut)
async def create_property_group(
    group_data: PropertyGroupCreate,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("signup"))  # Réutiliser le rate limit
):
    """
    Crée un nouveau groupe de multipropriété
    """
    try:
        group = MultiproprietService.create_property_group(
            db=db,
            sponsor_id=current_user.id,
            name=group_data.name,
            description=group_data.description,
            group_type=group_data.group_type,
            max_members=group_data.max_members
        )
        
        # Log de création
        AuditLogger.log_crud_action(
            db=db,
            action=ActionType.CREATE,
            entity_type=EntityType.COPRO,  # Réutiliser ce type pour les groupes
            entity_id=group.id,
            user_id=current_user.id,
            description=f"Création groupe multipropriété: {group.name}",
            request=request
        )
        
        return PropertyGroupOut.model_validate(group)
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups", response_model=List[PropertyGroupOut])
async def list_my_groups(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_member_groups: bool = Query(True, description="Inclure les groupes où l'utilisateur est membre")
):
    """
    Liste les groupes de l'utilisateur (sponsorisés + memberships)
    """
    groups = []
    
    # Groupes sponsorisés
    sponsored_groups = db.query(PropertyGroup).filter(
        PropertyGroup.sponsor_id == current_user.id
    ).all()
    
    groups.extend(sponsored_groups)
    
    # Groupes où l'utilisateur est membre (si demandé)
    if include_member_groups:
        member_groups = db.query(PropertyGroup).join(PropertyGroupMember).filter(
            PropertyGroupMember.user_id == current_user.id,
            PropertyGroupMember.membership_status == "ACTIVE",
            PropertyGroup.sponsor_id != current_user.id
        ).all()
        
        groups.extend(member_groups)
    
    return [PropertyGroupOut.model_validate(group) for group in groups]


@router.get("/groups/{group_id}", response_model=PropertyGroupOut)
async def get_group_details(
    group_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les détails d'un groupe
    """
    # Vérifier l'accès au groupe
    group = db.query(PropertyGroup).filter(PropertyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")
    
    # Vérifier que l'utilisateur a accès au groupe
    has_access = (
        group.sponsor_id == current_user.id or
        db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.user_id == current_user.id,
            PropertyGroupMember.membership_status == "ACTIVE"
        ).first() is not None
    )
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Accès refusé à ce groupe")
    
    return PropertyGroupOut.model_validate(group)


@router.put("/groups/{group_id}", response_model=PropertyGroupOut)
async def update_group(
    group_id: int,
    group_data: PropertyGroupUpdate,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour un groupe de multipropriété
    """
    group = db.query(PropertyGroup).filter(PropertyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")
    
    # Seul le sponsor peut modifier le groupe
    if group.sponsor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Seul le sponsor peut modifier le groupe")
    
    # Mettre à jour les champs
    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    
    # Log de modification
    AuditLogger.log_crud_action(
        db=db,
        action=ActionType.UPDATE,
        entity_type=EntityType.COPRO,
        entity_id=group.id,
        user_id=current_user.id,
        description=f"Modification groupe multipropriété: {group.name}",
        request=request
    )
    
    return PropertyGroupOut.model_validate(group)


# ==================== GESTION DES MEMBRES ====================

@router.get("/groups/{group_id}/members", response_model=List[PropertyGroupMemberOut])
async def list_group_members(
    group_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Liste les membres d'un groupe
    """
    # Vérifier l'accès au groupe
    group = db.query(PropertyGroup).filter(PropertyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")
    
    # Vérifier que l'utilisateur a accès au groupe
    has_access = (
        group.sponsor_id == current_user.id or
        db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.user_id == current_user.id,
            PropertyGroupMember.membership_status == "ACTIVE"
        ).first() is not None
    )
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Accès refusé à ce groupe")
    
    members = db.query(PropertyGroupMember).filter(
        PropertyGroupMember.group_id == group_id
    ).all()
    
    return [PropertyGroupMemberOut.model_validate(member) for member in members]


@router.post("/groups/{group_id}/invite")
async def invite_user_to_group(
    group_id: int,
    invitation_data: GroupInvitationCreate,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit("verification"))
):
    """
    Invite un utilisateur à rejoindre un groupe
    """
    try:
        invitation = MultiproprietService.invite_user_to_group(
            db=db,
            group_id=group_id,
            invited_user_email=invitation_data.invited_user_email,
            invited_by_id=current_user.id,
            message=invitation_data.invitation_message,
            expires_in_days=invitation_data.expires_in_days
        )
        
        # Log de l'invitation
        AuditLogger.log_crud_action(
            db=db,
            action=ActionType.CREATE,
            entity_type=EntityType.USER,
            entity_id=invitation.invited_user_id,
            user_id=current_user.id,
            description=f"Invitation multipropriété envoyée à: {invitation_data.invited_user_email}",
            request=request
        )
        
        return {
            "success": True,
            "message": "Invitation envoyée avec succès",
            "invitation_code": invitation.invitation_code,
            "expires_at": invitation.expires_at
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/invitations/respond")
async def respond_to_invitation(
    response_data: GroupInvitationResponse,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Répond à une invitation de groupe (accepter/refuser)
    """
    if response_data.accept:
        try:
            member = MultiproprietService.accept_group_invitation(
                db=db,
                invitation_code=response_data.invitation_code,
                user_id=current_user.id
            )
            
            # Log de l'acceptation
            AuditLogger.log_crud_action(
                db=db,
                action=ActionType.CREATE,
                entity_type=EntityType.USER,
                entity_id=current_user.id,
                user_id=current_user.id,
                description=f"Invitation multipropriété acceptée: groupe {member.group.name}",
                request=request
            )
            
            return {
                "success": True,
                "message": "Invitation acceptée avec succès",
                "group_name": member.group.name,
                "role": member.role_in_group
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Refuser l'invitation
        invitation = db.query(PropertyGroupInvitation).filter(
            PropertyGroupInvitation.invitation_code == response_data.invitation_code,
            PropertyGroupInvitation.invited_user_id == current_user.id
        ).first()
        
        if invitation:
            invitation.status = "declined"
            invitation.responded_at = datetime.utcnow()
            db.commit()
        
        return {
            "success": True,
            "message": "Invitation refusée"
        }


@router.get("/invitations/received", response_model=List[PropertyGroupInvitationOut])
async def list_received_invitations(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filtrer par statut")
):
    """
    Liste les invitations reçues par l'utilisateur
    """
    query = db.query(PropertyGroupInvitation).filter(
        PropertyGroupInvitation.invited_user_id == current_user.id
    )
    
    if status:
        query = query.filter(PropertyGroupInvitation.status == status)
    
    invitations = query.order_by(PropertyGroupInvitation.created_at.desc()).all()
    
    return [PropertyGroupInvitationOut.model_validate(inv) for inv in invitations]


# ==================== GESTION DES APPARTEMENTS ====================

@router.post("/groups/{group_id}/apartments")
async def add_apartment_to_group(
    group_id: int,
    apartment_data: AddApartmentToGroupRequest,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ajoute un appartement à un groupe de multipropriété
    """
    try:
        success = MultiproprietService.add_apartment_to_group(
            db=db,
            apartment_id=apartment_data.apartment_id,
            group_id=group_id,
            user_id=current_user.id
        )
        
        if success:
            # Log de l'ajout
            AuditLogger.log_crud_action(
                db=db,
                action=ActionType.UPDATE,
                entity_type=EntityType.APARTMENT,
                entity_id=apartment_data.apartment_id,
                user_id=current_user.id,
                description=f"Appartement ajouté au groupe multipropriété {group_id}",
                request=request
            )
            
            return {
                "success": True,
                "message": "Appartement ajouté au groupe avec succès"
            }
        else:
            raise HTTPException(status_code=400, detail="Erreur lors de l'ajout de l'appartement")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/apartments/{apartment_id}/group")
async def remove_apartment_from_group(
    apartment_id: int,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retire un appartement d'un groupe de multipropriété
    """
    from models import Apartment
    
    # Trouver l'appartement
    apartment = db.query(Apartment).filter(Apartment.id == apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement non trouvé")
    
    if not apartment.property_group_id:
        raise HTTPException(status_code=400, detail="L'appartement n'est pas dans un groupe")
    
    # Vérifier les permissions (propriétaire ou sponsor du groupe)
    group = apartment.property_group
    is_owner = db.query(ApartmentUserLink).filter(
        ApartmentUserLink.apartment_id == apartment_id,
        ApartmentUserLink.user_id == current_user.id,
        ApartmentUserLink.role == UserRole.owner
    ).first() is not None
    
    is_sponsor = group.sponsor_id == current_user.id
    
    if not (is_owner or is_sponsor):
        raise HTTPException(status_code=403, detail="Permissions insuffisantes")
    
    # Retirer du groupe
    group_id = apartment.property_group_id
    apartment.property_group_id = None
    db.commit()
    
    # Log du retrait
    AuditLogger.log_crud_action(
        db=db,
        action=ActionType.UPDATE,
        entity_type=EntityType.APARTMENT,
        entity_id=apartment_id,
        user_id=current_user.id,
        description=f"Appartement retiré du groupe multipropriété {group_id}",
        request=request
    )
    
    return {
        "success": True,
        "message": "Appartement retiré du groupe avec succès"
    }


# ==================== STATISTIQUES ====================

@router.get("/groups/{group_id}/statistics", response_model=GroupStatistics)
async def get_group_statistics(
    group_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques détaillées d'un groupe
    """
    # Vérifier l'accès au groupe
    group = db.query(PropertyGroup).filter(PropertyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")
    
    # Vérifier que l'utilisateur a accès au groupe
    has_access = (
        group.sponsor_id == current_user.id or
        db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.user_id == current_user.id,
            PropertyGroupMember.membership_status == "ACTIVE"
        ).first() is not None
    )
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Accès refusé à ce groupe")
    
    # Calculer les statistiques
    from sqlalchemy import func
    from models import Apartment
    
    # Statistiques des membres
    total_members = db.query(func.count(PropertyGroupMember.id)).filter(
        PropertyGroupMember.group_id == group_id
    ).scalar() or 0
    
    active_members = db.query(func.count(PropertyGroupMember.id)).filter(
        PropertyGroupMember.group_id == group_id,
        PropertyGroupMember.membership_status == "ACTIVE"
    ).scalar() or 0
    
    pending_invitations = db.query(func.count(PropertyGroupInvitation.id)).filter(
        PropertyGroupInvitation.group_id == group_id,
        PropertyGroupInvitation.status == "pending"
    ).scalar() or 0
    
    # Statistiques des appartements
    apartments_stats = db.query(
        func.count(Apartment.id).label('total'),
        func.sum(Apartment.surface).label('total_surface'),
        func.avg(Apartment.surface).label('avg_surface')
    ).filter(
        Apartment.property_group_id == group_id
    ).first()
    
    total_apartments = apartments_stats.total or 0
    total_surface = float(apartments_stats.total_surface or 0)
    average_surface = float(apartments_stats.avg_surface or 0)
    
    return GroupStatistics(
        group_id=group.id,
        group_name=group.name,
        total_members=total_members,
        active_members=active_members,
        pending_invitations=pending_invitations,
        total_apartments=total_apartments,
        total_surface=total_surface,
        average_surface=average_surface,
        created_at=group.created_at,
        last_activity=None,  # À implémenter si nécessaire
        total_value=None,    # À implémenter selon les permissions
        monthly_revenue=None # À implémenter selon les permissions
    )


from datetime import datetime
from models import ApartmentUserLink
from enums import UserRole