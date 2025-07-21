"""
Schémas Pydantic pour l'administration
Validation des données pour le panel administrateur
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enums import AdminRole, UserStatus, AccountAction, SubscriptionType, AuthType


# === SCHÉMAS DE BASE ADMIN ===

class AdminUserBase(BaseModel):
    """Schéma de base pour un utilisateur admin"""
    admin_role: AdminRole = Field(default=AdminRole.VIEWER)
    can_manage_users: bool = Field(default=False)
    can_manage_subscriptions: bool = Field(default=False)
    can_view_finances: bool = Field(default=False)
    can_manage_properties: bool = Field(default=False)
    can_access_audit_logs: bool = Field(default=False)
    can_manage_admins: bool = Field(default=False)
    is_active: bool = Field(default=True)
    notes: Optional[str] = Field(default=None, max_length=1000)


class AdminUserCreate(AdminUserBase):
    """Schéma pour créer un utilisateur admin"""
    user_id: int = Field(gt=0)


class AdminUserUpdate(BaseModel):
    """Schéma pour mettre à jour un utilisateur admin"""
    admin_role: Optional[AdminRole] = None
    can_manage_users: Optional[bool] = None
    can_manage_subscriptions: Optional[bool] = None
    can_view_finances: Optional[bool] = None
    can_manage_properties: Optional[bool] = None
    can_access_audit_logs: Optional[bool] = None
    can_manage_admins: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class AdminUserOut(AdminUserBase):
    """Schéma de sortie pour un utilisateur admin"""
    id: int
    user_id: int
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Données utilisateur
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# === SCHÉMAS DASHBOARD ===

class DashboardStats(BaseModel):
    """Statistiques principales du dashboard"""
    total_users: int = Field(ge=0)
    active_users: int = Field(ge=0)
    premium_users: int = Field(ge=0)
    total_apartments: int = Field(ge=0)
    total_buildings: int = Field(ge=0)
    total_groups: int = Field(ge=0)
    new_users_today: int = Field(ge=0)
    new_users_week: int = Field(ge=0)


class RecentSignup(BaseModel):
    """Inscription récente"""
    id: int
    email: str
    name: str
    created_at: datetime
    auth_type: AuthType
    status: str


class UserGrowthData(BaseModel):
    """Données de croissance utilisateur"""
    date: str
    count: int = Field(ge=0)


class SubscriptionBreakdown(BaseModel):
    """Répartition des abonnements"""
    free: int = Field(ge=0)
    premium: int = Field(ge=0)


class SystemAlert(BaseModel):
    """Alerte système"""
    type: str = Field(pattern="^(info|warning|error|success)$")
    title: str = Field(max_length=200)
    message: str = Field(max_length=500)
    action_url: Optional[str] = Field(default=None, max_length=500)


class AdminDashboardOut(BaseModel):
    """Données complètes du dashboard admin"""
    stats: DashboardStats
    recent_signups: List[RecentSignup]
    user_growth: List[UserGrowthData]
    subscription_breakdown: SubscriptionBreakdown
    system_alerts: List[SystemAlert]


# === SCHÉMAS GESTION UTILISATEURS ===

class UserMultiproprietData(BaseModel):
    """Données multipropriété d'un utilisateur"""
    personal_apartments: int = Field(ge=0)
    sponsored_apartments: int = Field(ge=0)
    accessible_apartments: int = Field(ge=0)
    can_sponsor: bool


class UserListItem(BaseModel):
    """Item d'utilisateur dans la liste"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    auth_type: AuthType
    email_verified: bool
    user_status: str
    subscription_type: SubscriptionType
    subscription_status: str
    apartment_count: int = Field(ge=0)
    multipropriete: UserMultiproprietData
    last_login: Optional[datetime] = None
    full_address: Optional[str] = None


class UsersListPagination(BaseModel):
    """Pagination de la liste utilisateurs"""
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    pages: int = Field(ge=0)


class UsersListFilters(BaseModel):
    """Filtres de la liste utilisateurs"""
    search: Optional[str] = None
    status_filter: Optional[str] = None
    subscription_filter: Optional[str] = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class UsersListOut(BaseModel):
    """Liste paginée d'utilisateurs"""
    users: List[UserListItem]
    pagination: UsersListPagination
    filters: UsersListFilters


class UsersListQuery(BaseModel):
    """Paramètres de requête pour la liste utilisateurs"""
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)
    search: Optional[str] = Field(default=None, max_length=255)
    status_filter: Optional[UserStatus] = None
    subscription_filter: Optional[SubscriptionType] = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# === SCHÉMAS DÉTAILS UTILISATEUR ===

class UserAddress(BaseModel):
    """Adresse d'un utilisateur"""
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    complement: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class UserDetailedData(BaseModel):
    """Données détaillées d'un utilisateur"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    auth_type: AuthType
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    user_status: str
    admin_notes: Optional[str] = None
    suspension_reason: Optional[str] = None
    suspension_expires_at: Optional[datetime] = None
    address: UserAddress


class UserApartmentInfo(BaseModel):
    """Informations d'appartement utilisateur"""
    id: int
    name: Optional[str] = None
    building_name: Optional[str] = None
    type_logement: Optional[str] = None
    floor: Optional[int] = None
    is_in_group: bool
    group_name: Optional[str] = None


class UserPropertiesData(BaseModel):
    """Données des propriétés d'un utilisateur"""
    apartments: List[UserApartmentInfo]
    multipropriete: UserMultiproprietData
    subscription: Dict[str, Any]


class AdminActionInfo(BaseModel):
    """Informations d'action admin"""
    id: int
    action_type: AccountAction
    description: str
    reason: Optional[str] = None
    created_at: datetime
    admin_email: Optional[str] = None


class StatusHistoryInfo(BaseModel):
    """Historique des statuts"""
    id: int
    previous_status: Optional[UserStatus] = None
    new_status: UserStatus
    reason: Optional[str] = None
    created_at: datetime
    changed_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_temporary: bool


class UserActivityData(BaseModel):
    """Données d'activité d'un utilisateur"""
    admin_actions: List[AdminActionInfo]
    status_history: List[StatusHistoryInfo]
    login_history: List[Dict[str, Any]] = []  # À implémenter
    recent_activity: List[Dict[str, Any]] = []  # À implémenter


class UserDetailedOut(BaseModel):
    """Informations complètes d'un utilisateur"""
    user_data: UserDetailedData
    properties_data: UserPropertiesData
    activity_data: UserActivityData


# === SCHÉMAS ACTIONS ADMINISTRATIVES ===

class UserActionRequest(BaseModel):
    """Requête d'action sur utilisateur"""
    action: AccountAction
    reason: Optional[str] = Field(default=None, max_length=500)
    duration_days: Optional[int] = Field(default=None, ge=1, le=365)
    
    @validator('reason')
    def reason_required_for_some_actions(cls, v, values):
        """Certaines actions nécessitent une raison"""
        if 'action' in values:
            action = values['action']
            if action in [AccountAction.SUSPEND, AccountAction.BAN, AccountAction.DEACTIVATE]:
                if not v or not v.strip():
                    raise ValueError(f'Une raison est requise pour l\'action {action}')
        return v
    
    @validator('duration_days')
    def duration_for_suspend_only(cls, v, values):
        """Durée uniquement pour les suspensions"""
        if 'action' in values and v is not None:
            if values['action'] != AccountAction.SUSPEND:
                raise ValueError('La durée n\'est applicable que pour les suspensions')
        return v


class UserActionResponse(BaseModel):
    """Réponse d'action sur utilisateur"""
    success: bool
    message: str
    user_id: int
    action: AccountAction
    executed_at: datetime


# === SCHÉMAS NOTIFICATIONS ADMIN ===

class AdminNotificationBase(BaseModel):
    """Notification admin de base"""
    title: str = Field(max_length=200)
    message: str = Field(max_length=1000)
    notification_type: str = Field(default="info")
    priority: str = Field(default="normal")
    action_url: Optional[str] = Field(default=None, max_length=500)
    expires_at: Optional[datetime] = None


class AdminNotificationCreate(AdminNotificationBase):
    """Créer une notification admin"""
    admin_user_id: Optional[int] = None  # None = tous les admins


class AdminNotificationOut(AdminNotificationBase):
    """Notification admin sortie"""
    id: int
    admin_user_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    is_expired: bool
    is_urgent: bool
    
    class Config:
        from_attributes = True


# === SCHÉMAS PARAMÈTRES SYSTÈME ===

class SystemSettingBase(BaseModel):
    """Paramètre système de base"""
    setting_key: str = Field(max_length=100)
    setting_value: Optional[str] = None
    setting_type: str = Field(default="string", pattern="^(string|bool|int|float|json)$")
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=50)
    is_sensitive: bool = Field(default=False)


class SystemSettingCreate(SystemSettingBase):
    """Créer un paramètre système"""
    pass


class SystemSettingUpdate(BaseModel):
    """Mettre à jour un paramètre système"""
    setting_value: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=50)
    is_sensitive: Optional[bool] = None


class SystemSettingOut(SystemSettingBase):
    """Paramètre système sortie"""
    id: int
    modified_by_admin_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# === SCHÉMAS D'AUTHENTIFICATION ADMIN ===

class AdminLoginRequest(BaseModel):
    """Requête de connexion admin"""
    email: EmailStr
    password: str = Field(min_length=8)
    remember_me: bool = Field(default=False)


class AdminLoginResponse(BaseModel):
    """Réponse de connexion admin"""
    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int
    admin_user: AdminUserOut
    permissions: Dict[str, bool]


# === SCHÉMAS DE RECHERCHE ET STATISTIQUES ===

class SearchQuery(BaseModel):
    """Requête de recherche générale"""
    query: str = Field(min_length=2, max_length=255)
    entity_types: Optional[List[str]] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=100)


class SearchResult(BaseModel):
    """Résultat de recherche"""
    entity_type: str
    entity_id: int
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    relevance_score: float = Field(ge=0, le=1)


class SearchResults(BaseModel):
    """Résultats de recherche"""
    query: str
    results: List[SearchResult]
    total_found: int
    search_time_ms: float


class AdminStatsQuery(BaseModel):
    """Requête de statistiques admin"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    group_by: str = Field(default="day", pattern="^(hour|day|week|month)$")
    metrics: Optional[List[str]] = Field(default=None)


class MetricDataPoint(BaseModel):
    """Point de données métrique"""
    timestamp: datetime
    value: Union[int, float]
    label: Optional[str] = None


class AdminStatsOut(BaseModel):
    """Statistiques admin sortie"""
    query: AdminStatsQuery
    metrics: Dict[str, List[MetricDataPoint]]
    generated_at: datetime