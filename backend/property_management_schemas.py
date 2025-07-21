"""
Schémas Pydantic pour la gestion multi-acteurs des propriétés
"""
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, date
from enum import Enum
from property_management_models import UserRole, PermissionType, PropertyScope


# ==================== ÉNUMÉRATIONS ====================

class UserRoleEnum(str, Enum):
    """Rôles des utilisateurs"""
    SUPER_ADMIN = "SUPER_ADMIN"
    PROPERTY_MANAGER = "PROPERTY_MANAGER"
    OWNER = "OWNER"
    TENANT = "TENANT"
    AGENT = "AGENT"
    MAINTENANCE = "MAINTENANCE"
    ACCOUNTANT = "ACCOUNTANT"
    VIEWER = "VIEWER"


class PermissionTypeEnum(str, Enum):
    """Types de permissions"""
    VIEW = "VIEW"
    EDIT = "EDIT"
    DELETE = "DELETE"
    CREATE = "CREATE"
    SIGN_DOCUMENTS = "SIGN_DOCUMENTS"
    MANAGE_FINANCES = "MANAGE_FINANCES"
    MANAGE_LEASES = "MANAGE_LEASES"
    MANAGE_TENANTS = "MANAGE_TENANTS"
    MANAGE_MAINTENANCE = "MANAGE_MAINTENANCE"
    ACCESS_REPORTS = "ACCESS_REPORTS"
    MANAGE_KEYS = "MANAGE_KEYS"
    SCHEDULE_VISITS = "SCHEDULE_VISITS"


class PropertyScopeEnum(str, Enum):
    """Portée des permissions"""
    GLOBAL = "GLOBAL"
    BUILDING = "BUILDING"
    APARTMENT = "APARTMENT"
    TENANT_ONLY = "TENANT_ONLY"


class OwnershipTypeEnum(str, Enum):
    """Types de propriété"""
    FULL = "FULL"
    USUFRUCT = "USUFRUCT"
    BARE_OWNERSHIP = "BARE_OWNERSHIP"


class OccupancyTypeEnum(str, Enum):
    """Types d'occupation"""
    MAIN_TENANT = "MAIN_TENANT"
    CO_TENANT = "CO_TENANT"
    OCCUPANT = "OCCUPANT"


class ContractTypeEnum(str, Enum):
    """Types de contrats de gestion"""
    FULL = "FULL"
    RENTAL_ONLY = "RENTAL_ONLY"
    MAINTENANCE_ONLY = "MAINTENANCE_ONLY"


# ==================== SCHÉMAS POUR LES SOCIÉTÉS DE GESTION ====================

class ManagementCompanyCreate(BaseModel):
    """Schéma pour créer une société de gestion"""
    name: str = Field(..., min_length=1, max_length=200)
    business_name: Optional[str] = Field(None, max_length=200)
    siret: Optional[str] = Field(None, pattern=r'^\d{14}$')
    registration_number: Optional[str] = Field(None, max_length=50)
    
    # Coordonnées
    address: Optional[str] = Field(None, max_length=500)
    postal_code: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    country: str = "France"
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    website: Optional[str] = None
    
    # Informations légales
    license_number: Optional[str] = Field(None, max_length=100)
    insurance_number: Optional[str] = Field(None, max_length=100)
    guarantee_fund: Optional[str] = Field(None, max_length=100)
    
    # Configuration
    default_commission_rate: Optional[float] = Field(None, ge=0, le=100)
    billing_settings: Optional[Dict[str, Any]] = {}


class ManagementCompanyUpdate(BaseModel):
    """Schéma pour mettre à jour une société de gestion"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    business_name: Optional[str] = Field(None, max_length=200)
    siret: Optional[str] = Field(None, pattern=r'^\d{14}$')
    registration_number: Optional[str] = Field(None, max_length=50)
    
    address: Optional[str] = Field(None, max_length=500)
    postal_code: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    website: Optional[str] = None
    
    license_number: Optional[str] = Field(None, max_length=100)
    insurance_number: Optional[str] = Field(None, max_length=100)
    guarantee_fund: Optional[str] = Field(None, max_length=100)
    
    default_commission_rate: Optional[float] = Field(None, ge=0, le=100)
    billing_settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ManagementCompanyOut(BaseModel):
    """Schéma de sortie pour une société de gestion"""
    id: int
    name: str
    business_name: Optional[str]
    siret: Optional[str]
    registration_number: Optional[str]
    
    address: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]
    country: str
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    
    license_number: Optional[str]
    insurance_number: Optional[str]
    guarantee_fund: Optional[str]
    
    default_commission_rate: Optional[float]
    billing_settings: Optional[Dict[str, Any]]
    
    is_active: bool
    contract_start_date: Optional[datetime]
    contract_end_date: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LA GESTION DE PROPRIÉTÉS ====================

class PropertyManagementCreate(BaseModel):
    """Schéma pour créer un contrat de gestion"""
    management_company_id: int
    apartment_id: int
    managed_by: int
    
    contract_type: ContractTypeEnum
    start_date: datetime
    end_date: Optional[datetime] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    
    services_included: Optional[List[str]] = []
    billing_frequency: str = Field("MONTHLY", pattern="^(MONTHLY|QUARTERLY|ANNUALLY)$")
    
    delegated_permissions: List[PermissionTypeEnum]
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v <= values['start_date']:
            raise ValueError('La date de fin doit être postérieure à la date de début')
        return v
    
    @validator('delegated_permissions')
    def validate_permissions(cls, v):
        if not v:
            raise ValueError('Au moins une permission doit être déléguée')
        return v


class PropertyManagementUpdate(BaseModel):
    """Schéma pour mettre à jour un contrat de gestion"""
    managed_by: Optional[int] = None
    contract_type: Optional[ContractTypeEnum] = None
    end_date: Optional[datetime] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    
    services_included: Optional[List[str]] = None
    billing_frequency: Optional[str] = Field(None, pattern="^(MONTHLY|QUARTERLY|ANNUALLY)$")
    
    delegated_permissions: Optional[List[PermissionTypeEnum]] = None
    is_active: Optional[bool] = None
    termination_reason: Optional[str] = None


class PropertyManagementOut(BaseModel):
    """Schéma de sortie pour un contrat de gestion"""
    id: int
    management_company_id: int
    apartment_id: int
    managed_by: int
    
    contract_type: str
    start_date: datetime
    end_date: Optional[datetime]
    commission_rate: Optional[float]
    
    services_included: Optional[List[str]]
    billing_frequency: str
    
    delegated_permissions: Dict[str, Any]
    
    is_active: bool
    termination_reason: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LA MULTI-PROPRIÉTÉ ====================

class PropertyOwnershipCreate(BaseModel):
    """Schéma pour créer une propriété"""
    apartment_id: int
    owner_id: int
    
    ownership_percentage: float = Field(..., gt=0, le=100)
    ownership_type: OwnershipTypeEnum = OwnershipTypeEnum.FULL
    
    can_sign_leases: bool = True
    can_authorize_works: bool = True
    can_receive_rent: bool = True
    can_access_reports: bool = True
    
    acquisition_date: Optional[date] = None
    acquisition_price: Optional[float] = Field(None, gt=0)
    notary_deed_reference: Optional[str] = Field(None, max_length=100)
    
    start_date: Optional[datetime] = None


class PropertyOwnershipUpdate(BaseModel):
    """Schéma pour mettre à jour une propriété"""
    ownership_percentage: Optional[float] = Field(None, gt=0, le=100)
    ownership_type: Optional[OwnershipTypeEnum] = None
    
    can_sign_leases: Optional[bool] = None
    can_authorize_works: Optional[bool] = None
    can_receive_rent: Optional[bool] = None
    can_access_reports: Optional[bool] = None
    
    acquisition_date: Optional[date] = None
    acquisition_price: Optional[float] = Field(None, gt=0)
    notary_deed_reference: Optional[str] = Field(None, max_length=100)
    
    is_active: Optional[bool] = None
    end_date: Optional[datetime] = None


class PropertyOwnershipOut(BaseModel):
    """Schéma de sortie pour une propriété"""
    id: int
    apartment_id: int
    owner_id: int
    
    ownership_percentage: float
    ownership_type: str
    
    can_sign_leases: bool
    can_authorize_works: bool
    can_receive_rent: bool
    can_access_reports: bool
    
    acquisition_date: Optional[date]
    acquisition_price: Optional[float]
    notary_deed_reference: Optional[str]
    
    is_active: bool
    start_date: datetime
    end_date: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LA MULTI-LOCATION ====================

class TenantOccupancyCreate(BaseModel):
    """Schéma pour créer une occupation"""
    apartment_id: int
    tenant_id: int
    lease_id: Optional[int] = None
    
    occupancy_type: OccupancyTypeEnum = OccupancyTypeEnum.MAIN_TENANT
    rent_responsibility: float = Field(100.0, gt=0, le=100)
    
    can_invite_guests: bool = True
    can_sublease: bool = False
    can_access_common_areas: bool = True
    can_receive_mail: bool = True
    
    move_in_date: Optional[datetime] = None
    move_out_date: Optional[datetime] = None
    
    @validator('move_out_date')
    def validate_move_out_date(cls, v, values):
        if v and 'move_in_date' in values and values['move_in_date'] and v <= values['move_in_date']:
            raise ValueError("La date de sortie doit être postérieure à la date d'entrée")
        return v


class TenantOccupancyUpdate(BaseModel):
    """Schéma pour mettre à jour une occupation"""
    lease_id: Optional[int] = None
    occupancy_type: Optional[OccupancyTypeEnum] = None
    rent_responsibility: Optional[float] = Field(None, gt=0, le=100)
    
    can_invite_guests: Optional[bool] = None
    can_sublease: Optional[bool] = None
    can_access_common_areas: Optional[bool] = None
    can_receive_mail: Optional[bool] = None
    
    move_in_date: Optional[datetime] = None
    move_out_date: Optional[datetime] = None
    
    is_active: Optional[bool] = None
    occupancy_status: Optional[str] = Field(None, pattern="^(ACTIVE|TERMINATED|SUSPENDED)$")


class TenantOccupancyOut(BaseModel):
    """Schéma de sortie pour une occupation"""
    id: int
    apartment_id: int
    tenant_id: int
    lease_id: Optional[int]
    
    occupancy_type: str
    rent_responsibility: float
    
    can_invite_guests: bool
    can_sublease: bool
    can_access_common_areas: bool
    can_receive_mail: bool
    
    move_in_date: Optional[datetime]
    move_out_date: Optional[datetime]
    
    is_active: bool
    occupancy_status: str
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LES PERMISSIONS ====================

class UserPermissionCreate(BaseModel):
    """Schéma pour créer une permission"""
    user_id: int
    permission_type: PermissionTypeEnum
    resource_type: str = Field(..., min_length=1, max_length=50)
    resource_id: Optional[int] = None
    scope: PropertyScopeEnum
    
    conditions: Optional[Dict[str, Any]] = {}
    expires_at: Optional[datetime] = None
    
    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.now():
            raise ValueError("La date d'expiration doit être dans le futur")
        return v


class UserPermissionOut(BaseModel):
    """Schéma de sortie pour une permission"""
    id: int
    user_id: int
    granted_by: int
    permission_type: str
    resource_type: str
    resource_id: Optional[int]
    scope: str
    
    conditions: Optional[Dict[str, Any]]
    expires_at: Optional[datetime]
    
    is_active: bool
    granted_at: datetime
    last_used_at: Optional[datetime]
    usage_count: int
    
    class Config:
        from_attributes = True


class PermissionTemplateCreate(BaseModel):
    """Schéma pour créer un template de permissions"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    role: UserRoleEnum
    
    permissions: List[PermissionTypeEnum]
    default_scope: PropertyScopeEnum
    
    is_active: bool = True
    
    @validator('permissions')
    def validate_permissions(cls, v):
        if not v:
            raise ValueError('Au moins une permission doit être définie')
        return v


class PermissionTemplateOut(BaseModel):
    """Schéma de sortie pour un template de permissions"""
    id: int
    name: str
    description: Optional[str]
    role: str
    
    permissions: Dict[str, Any]
    default_scope: str
    
    is_system_template: bool
    is_active: bool
    
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LE DASHBOARD ====================

class UserDashboardData(BaseModel):
    """Données du dashboard utilisateur"""
    accessible_apartments: List[Dict[str, Any]]
    managed_properties: List[Dict[str, Any]]
    owned_properties: List[Dict[str, Any]]
    rented_properties: List[Dict[str, Any]]
    permissions_summary: Dict[str, int]
    recent_actions: List[Dict[str, Any]]


class ApartmentSummary(BaseModel):
    """Résumé d'un appartement pour le dashboard"""
    id: int
    address: str
    type: Optional[str]
    surface: Optional[float]
    user_role: str  # owner, tenant, manager
    permissions: List[str]
    
    # Informations contextuelles selon le rôle
    ownership_percentage: Optional[float] = None
    rent_responsibility: Optional[float] = None
    management_company: Optional[str] = None


class PropertyStakeholders(BaseModel):
    """Acteurs d'une propriété"""
    apartment_id: int
    
    owners: List[Dict[str, Any]]
    tenants: List[Dict[str, Any]]
    managers: List[Dict[str, Any]]
    
    management_company: Optional[Dict[str, Any]]


# ==================== SCHÉMAS POUR LES ACTIONS ====================

class GrantPermissionRequest(BaseModel):
    """Demande d'octroi de permission"""
    user_id: int
    permission_type: PermissionTypeEnum
    resource_type: str
    resource_id: Optional[int] = None
    scope: PropertyScopeEnum
    expires_at: Optional[datetime] = None
    
    reason: Optional[str] = None


class RevokePermissionRequest(BaseModel):
    """Demande de révocation de permission"""
    user_id: int
    permission_type: PermissionTypeEnum
    resource_type: str
    resource_id: Optional[int] = None
    
    reason: str = Field(..., min_length=1)


class ApplyRoleRequest(BaseModel):
    """Demande d'application de rôle"""
    user_id: int
    role: UserRoleEnum
    resource_id: Optional[int] = None
    
    override_existing: bool = False


class TransferOwnershipRequest(BaseModel):
    """Demande de transfert de propriété"""
    apartment_id: int
    from_owner_id: int
    to_owner_id: int
    
    percentage_to_transfer: float = Field(..., gt=0, le=100)
    transfer_all_rights: bool = True
    
    notary_deed_reference: Optional[str] = None
    transfer_date: date = Field(default_factory=date.today)


class AssignManagerRequest(BaseModel):
    """Demande d'assignation de gestionnaire"""
    apartment_id: int
    management_company_id: int
    manager_id: int
    
    contract_type: ContractTypeEnum
    start_date: datetime
    end_date: Optional[datetime] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    
    delegated_permissions: List[PermissionTypeEnum]
    services_included: List[str] = []


# ==================== SCHÉMAS POUR LES RAPPORTS ====================

class PermissionAuditReport(BaseModel):
    """Rapport d'audit des permissions"""
    apartment_id: int
    
    current_stakeholders: PropertyStakeholders
    permission_changes: List[Dict[str, Any]]
    access_logs: List[Dict[str, Any]]
    
    generated_at: datetime
    generated_by: int


class AccessStatistics(BaseModel):
    """Statistiques d'accès"""
    user_id: int
    period_start: datetime
    period_end: datetime
    
    total_accesses: int
    successful_accesses: int
    failed_accesses: int
    
    most_used_permissions: List[Dict[str, Any]]
    accessed_resources: List[Dict[str, Any]]
    
    average_response_time: Optional[float]


# ==================== VALIDATIONS PERSONNALISÉES ====================

class PropertyOwnershipCreate(PropertyOwnershipCreate):
    """Version étendue avec validations"""
    
    @validator('ownership_percentage')
    def validate_percentage_sum(cls, v, values):
        # Note: Cette validation devrait être faite au niveau service
        # pour vérifier la somme totale des pourcentages par appartement
        return v


class TenantOccupancyCreate(TenantOccupancyCreate):
    """Version étendue avec validations"""
    
    @validator('rent_responsibility')
    def validate_rent_responsibility_sum(cls, v, values):
        # Note: Cette validation devrait être faite au niveau service
        # pour vérifier la somme totale des responsabilités par appartement
        return v


# ==================== SCHÉMAS POUR LES LOGS ====================

class AccessLogOut(BaseModel):
    """Schéma de sortie pour un log d'accès"""
    id: int
    user_id: int
    action: str
    resource_type: str
    resource_id: Optional[int]
    
    permission_used: Optional[str]
    access_method: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    
    success: bool
    error_message: Optional[str]
    response_time: Optional[int]
    
    request_data: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    
    timestamp: datetime
    session_id: Optional[str]
    
    class Config:
        from_attributes = True