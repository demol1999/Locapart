"""
Schémas Pydantic pour le système de multipropriété
Validation et sérialisation des données d'API
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from models_multipropriete import PropertyGroupType, PropertyGroupStatus, MembershipStatus
from validators import CommonValidators


# ==================== ENUMS POUR API ====================

class PropertyGroupTypeAPI(str, Enum):
    SCI = "SCI"
    FAMILY = "FAMILY"
    INVESTMENT = "INVESTMENT"
    OTHER = "OTHER"


class MembershipStatusAPI(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    LEFT = "LEFT"


# ==================== SCHÉMAS DE BASE ====================

class PropertyGroupBase(BaseModel):
    """Schéma de base pour les groupes de propriété"""
    name: str = Field(..., min_length=2, max_length=200, description="Nom du groupe")
    description: Optional[str] = Field(None, max_length=1000, description="Description du groupe")
    group_type: PropertyGroupTypeAPI = Field(default=PropertyGroupTypeAPI.OTHER, description="Type de groupe")
    max_members: int = Field(default=10, ge=2, le=50, description="Nombre maximum de membres")
    auto_accept_invitations: bool = Field(default=False, description="Acceptation automatique des invitations")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return CommonValidators.validate_name(v, "nom du groupe")


class PropertyGroupCreate(PropertyGroupBase):
    """Schéma pour créer un groupe de propriété"""
    pass


class PropertyGroupUpdate(BaseModel):
    """Schéma pour mettre à jour un groupe de propriété"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    max_members: Optional[int] = Field(None, ge=2, le=50)
    auto_accept_invitations: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            return CommonValidators.validate_name(v, "nom du groupe")
        return v


class PropertyGroupMemberBase(BaseModel):
    """Schéma de base pour les membres de groupe"""
    role_in_group: str = Field(default="member", max_length=50, description="Rôle dans le groupe")
    can_invite_members: bool = Field(default=False, description="Peut inviter des membres")
    can_manage_apartments: bool = Field(default=False, description="Peut gérer les appartements")
    can_view_finances: bool = Field(default=False, description="Peut voir les finances")


class PropertyGroupMemberUpdate(PropertyGroupMemberBase):
    """Schéma pour mettre à jour un membre de groupe"""
    role_in_group: Optional[str] = Field(None, max_length=50)
    can_invite_members: Optional[bool] = None
    can_manage_apartments: Optional[bool] = None
    can_view_finances: Optional[bool] = None


# ==================== SCHÉMAS D'INVITATION ====================

class GroupInvitationCreate(BaseModel):
    """Schéma pour créer une invitation"""
    invited_user_email: EmailStr = Field(..., description="Email de l'utilisateur à inviter")
    invitation_message: Optional[str] = Field(None, max_length=500, description="Message personnalisé")
    expires_in_days: int = Field(default=7, ge=1, le=30, description="Expiration en jours")
    
    # Permissions par défaut pour le nouveau membre
    role_in_group: str = Field(default="member", max_length=50)
    can_invite_members: bool = Field(default=False)
    can_manage_apartments: bool = Field(default=False)
    can_view_finances: bool = Field(default=False)


class GroupInvitationResponse(BaseModel):
    """Schéma pour répondre à une invitation"""
    invitation_code: str = Field(..., min_length=8, max_length=8, description="Code d'invitation")
    accept: bool = Field(..., description="Accepter (True) ou refuser (False)")


# ==================== SCHÉMAS DE RÉPONSE ====================

class UserSummary(BaseModel):
    """Résumé d'un utilisateur pour les réponses"""
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    
    class Config:
        from_attributes = True


class PropertyGroupOut(BaseModel):
    """Schéma de sortie pour un groupe de propriété"""
    id: int
    name: str
    description: Optional[str]
    group_type: PropertyGroupTypeAPI
    group_status: str
    max_members: int
    auto_accept_invitations: bool
    created_at: datetime
    updated_at: datetime
    
    # Sponsor info
    sponsor: UserSummary
    
    # Statistiques
    active_members_count: int
    apartments_count: int
    
    class Config:
        from_attributes = True


class PropertyGroupMemberOut(BaseModel):
    """Schéma de sortie pour un membre de groupe"""
    id: int
    membership_status: MembershipStatusAPI
    role_in_group: str
    can_invite_members: bool
    can_manage_apartments: bool
    can_view_finances: bool
    joined_at: Optional[datetime]
    
    # Info utilisateur
    user: UserSummary
    
    # Info invitation
    invited_by: Optional[UserSummary]
    invitation_message: Optional[str]
    
    class Config:
        from_attributes = True


class PropertyGroupInvitationOut(BaseModel):
    """Schéma de sortie pour une invitation"""
    id: int
    invitation_code: str
    invitation_message: Optional[str]
    status: str
    expires_at: datetime
    responded_at: Optional[datetime]
    created_at: datetime
    
    # Relations
    group: PropertyGroupOut
    invited_user: UserSummary
    invited_by: UserSummary
    
    # Propriétés calculées
    is_expired: bool
    is_pending: bool
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS DE TABLEAU DE BORD ====================

class QuotaInfo(BaseModel):
    """Information sur les quotas"""
    current_count: int
    limit: int  # -1 pour illimité
    remaining: int  # -1 pour illimité
    is_unlimited: bool
    can_add_more: bool


class MultiproprieteDashboardOut(BaseModel):
    """Tableau de bord complet de multipropriété"""
    # Statistiques des appartements
    personal_apartments: int
    sponsored_apartments: int
    accessible_apartments: int
    total_accessible_apartments: int
    
    # Quotas
    personal_quota: QuotaInfo
    can_create_groups: bool
    is_premium: bool
    
    # Groupes
    sponsored_groups: List[Dict[str, Any]]
    member_groups: List[Dict[str, Any]]
    
    # Invitations en attente
    pending_invitations_received: int
    pending_invitations_sent: int


class ApartmentAccessInfo(BaseModel):
    """Information sur l'accès à un appartement"""
    apartment_id: int
    apartment_name: str
    building_name: Optional[str]
    access_type: str  # "personal", "sponsored", "member"
    role: str
    group_name: Optional[str]
    sponsor_email: Optional[str]
    
    # Permissions
    can_edit: bool
    can_delete: bool
    can_invite_tenants: bool
    can_manage_finances: bool


class UserApartmentsAccessOut(BaseModel):
    """Liste complète des appartements accessibles par un utilisateur"""
    apartments: List[ApartmentAccessInfo]
    total_count: int
    personal_count: int
    sponsored_count: int
    member_count: int


# ==================== SCHÉMAS D'ACTIONS ====================

class AddApartmentToGroupRequest(BaseModel):
    """Demande d'ajout d'appartement à un groupe"""
    apartment_id: int = Field(..., description="ID de l'appartement à ajouter")
    group_id: int = Field(..., description="ID du groupe de destination")


class RemoveApartmentFromGroupRequest(BaseModel):
    """Demande de retrait d'appartement d'un groupe"""
    apartment_id: int = Field(..., description="ID de l'appartement à retirer")


class TransferGroupOwnershipRequest(BaseModel):
    """Demande de transfert de propriété de groupe"""
    new_sponsor_id: int = Field(..., description="ID du nouveau sponsor")
    confirmation_message: str = Field(..., min_length=10, description="Message de confirmation")


class LeaveGroupRequest(BaseModel):
    """Demande pour quitter un groupe"""
    group_id: int = Field(..., description="ID du groupe à quitter")
    leave_message: Optional[str] = Field(None, max_length=500, description="Message de départ")


# ==================== SCHÉMAS DE RECHERCHE ====================

class GroupSearchFilters(BaseModel):
    """Filtres de recherche pour les groupes"""
    group_type: Optional[PropertyGroupTypeAPI] = None
    sponsor_email: Optional[str] = None
    min_members: Optional[int] = Field(None, ge=1)
    max_members: Optional[int] = Field(None, ge=1)
    has_apartments: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class MemberSearchFilters(BaseModel):
    """Filtres de recherche pour les membres"""
    membership_status: Optional[MembershipStatusAPI] = None
    role_in_group: Optional[str] = None
    joined_after: Optional[datetime] = None
    joined_before: Optional[datetime] = None
    can_invite_members: Optional[bool] = None
    can_manage_apartments: Optional[bool] = None


# ==================== SCHÉMAS DE STATISTIQUES ====================

class GroupStatistics(BaseModel):
    """Statistiques détaillées d'un groupe"""
    group_id: int
    group_name: str
    
    # Membres
    total_members: int
    active_members: int
    pending_invitations: int
    
    # Appartements
    total_apartments: int
    total_surface: float
    average_surface: float
    
    # Activité
    created_at: datetime
    last_activity: Optional[datetime]
    
    # Finances (si autorisé)
    total_value: Optional[float]
    monthly_revenue: Optional[float]


class UserMultiproprietStatistics(BaseModel):
    """Statistiques de multipropriété pour un utilisateur"""
    user_id: int
    
    # Groupes sponsorisés
    sponsored_groups_count: int
    sponsored_apartments_count: int
    sponsored_members_count: int
    
    # Memberships
    member_groups_count: int
    accessible_apartments_count: int
    
    # Totaux
    total_accessible_apartments: int
    total_surface_accessible: float
    
    # Statut
    subscription_type: str
    can_create_more_groups: bool


# ==================== SCHÉMAS DE NOTIFICATIONS ====================

class GroupNotification(BaseModel):
    """Notification liée à un groupe"""
    id: int
    notification_type: str  # "invitation", "member_joined", "apartment_added", etc.
    title: str
    message: str
    is_read: bool
    created_at: datetime
    
    # Contexte
    group_id: Optional[int]
    group_name: Optional[str]
    user_id: Optional[int]
    user_email: Optional[str]
    
    # Actions possibles
    action_url: Optional[str]
    action_label: Optional[str]