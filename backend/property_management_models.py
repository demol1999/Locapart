"""
Modèles pour la gestion multi-acteurs des propriétés
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Numeric, JSON, Table
from sqlalchemy.orm import relationship
from database import Base
import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class UserRole(str, Enum):
    """Rôles des utilisateurs dans le système"""
    SUPER_ADMIN = "SUPER_ADMIN"           # Contrôle total système
    PROPERTY_MANAGER = "PROPERTY_MANAGER"  # Gestionnaire immobilier
    OWNER = "OWNER"                       # Propriétaire
    TENANT = "TENANT"                     # Locataire
    AGENT = "AGENT"                       # Agent immobilier
    MAINTENANCE = "MAINTENANCE"           # Équipe maintenance
    ACCOUNTANT = "ACCOUNTANT"             # Comptable
    VIEWER = "VIEWER"                     # Visualisation seulement


class PermissionType(str, Enum):
    """Types de permissions"""
    # Permissions générales
    VIEW = "VIEW"                         # Consultation
    EDIT = "EDIT"                         # Modification
    DELETE = "DELETE"                     # Suppression
    CREATE = "CREATE"                     # Création
    
    # Permissions spécialisées
    SIGN_DOCUMENTS = "SIGN_DOCUMENTS"     # Signature documents
    MANAGE_FINANCES = "MANAGE_FINANCES"   # Gestion financière
    MANAGE_LEASES = "MANAGE_LEASES"       # Gestion des baux
    MANAGE_TENANTS = "MANAGE_TENANTS"     # Gestion locataires
    MANAGE_MAINTENANCE = "MANAGE_MAINTENANCE"  # Gestion maintenance
    ACCESS_REPORTS = "ACCESS_REPORTS"     # Accès rapports
    MANAGE_KEYS = "MANAGE_KEYS"           # Gestion des clés
    SCHEDULE_VISITS = "SCHEDULE_VISITS"   # Planifier visites


class PropertyScope(str, Enum):
    """Portée des permissions"""
    GLOBAL = "GLOBAL"                     # Toutes les propriétés
    BUILDING = "BUILDING"                 # Un immeuble spécifique
    APARTMENT = "APARTMENT"               # Un appartement spécifique
    TENANT_ONLY = "TENANT_ONLY"           # Seulement ses propres données


class ManagementCompany(Base):
    """Société de gestion immobilière"""
    __tablename__ = "management_companies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Informations de la société
    name = Column(String(200), nullable=False)
    business_name = Column(String(200), nullable=True)  # Raison sociale si différente
    siret = Column(String(14), nullable=True, unique=True)
    registration_number = Column(String(50), nullable=True)  # Numéro d'immatriculation
    
    # Coordonnées
    address = Column(String(500), nullable=True)
    postal_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), default="France")
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Informations légales
    license_number = Column(String(100), nullable=True)  # Carte professionnelle
    insurance_number = Column(String(100), nullable=True)  # Assurance RC
    guarantee_fund = Column(String(100), nullable=True)   # Fonds de garantie
    
    # Configuration
    default_commission_rate = Column(Numeric(5, 2), nullable=True)  # Taux de commission par défaut
    billing_settings = Column(JSON, nullable=True)        # Configuration facturation
    
    # Statut
    is_active = Column(Boolean, default=True)
    contract_start_date = Column(DateTime, nullable=True)
    contract_end_date = Column(DateTime, nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations  
    managed_properties = relationship("PropertyManagement", back_populates="management_company")


# Table d'association pour les gestionnaires d'une société
company_managers = Table(
    'company_managers',
    Base.metadata,
    Column('company_id', Integer, ForeignKey('management_companies.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user_auth.id'), primary_key=True),
    Column('role', String(50), default="MANAGER"),  # ADMIN, MANAGER, EMPLOYEE
    Column('permissions', JSON, nullable=True),      # Permissions spécifiques
    Column('created_at', DateTime, default=datetime.datetime.utcnow),
    Column('is_active', Boolean, default=True)
)


class PropertyManagement(Base):
    """Gestion d'une propriété par une société"""
    __tablename__ = "property_management"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    management_company_id = Column(Integer, ForeignKey("management_companies.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    managed_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)  # Gestionnaire principal
    
    # Contrat de gestion
    contract_type = Column(String(50), nullable=False)  # FULL, RENTAL_ONLY, MAINTENANCE_ONLY
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    commission_rate = Column(Numeric(5, 2), nullable=True)  # Taux de commission
    
    # Services inclus
    services_included = Column(JSON, nullable=True)     # Liste des services
    billing_frequency = Column(String(20), default="MONTHLY")  # MONTHLY, QUARTERLY, ANNUALLY
    
    # Permissions déléguées
    delegated_permissions = Column(JSON, nullable=False)  # Permissions accordées
    
    # Statut
    is_active = Column(Boolean, default=True)
    termination_reason = Column(String(500), nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    management_company = relationship("ManagementCompany", back_populates="managed_properties")
    apartment = relationship("Apartment", backref="property_management")
    manager = relationship("UserAuth", foreign_keys=[managed_by])


class PropertyOwnership(Base):
    """Multi-propriété d'un appartement"""
    __tablename__ = "property_ownership"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Détails de propriété
    ownership_percentage = Column(Numeric(5, 2), nullable=False, default=100.00)  # Pourcentage de propriété
    ownership_type = Column(String(50), nullable=False)  # FULL, USUFRUCT, BARE_OWNERSHIP
    
    # Droits spécifiques
    can_sign_leases = Column(Boolean, default=True)
    can_authorize_works = Column(Boolean, default=True)
    can_receive_rent = Column(Boolean, default=True)
    can_access_reports = Column(Boolean, default=True)
    
    # Informations légales
    acquisition_date = Column(DateTime, nullable=True)
    acquisition_price = Column(Numeric(12, 2), nullable=True)
    notary_deed_reference = Column(String(100), nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    apartment = relationship("Apartment", backref="ownerships")
    owner = relationship("UserAuth", back_populates="owned_properties")


class TenantOccupancy(Base):
    """Multi-locataires d'un appartement"""
    __tablename__ = "tenant_occupancy"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=True)
    
    # Détails d'occupation
    occupancy_type = Column(String(50), nullable=False)  # MAIN_TENANT, CO_TENANT, OCCUPANT
    rent_responsibility = Column(Numeric(5, 2), default=100.00)  # Pourcentage de loyer
    
    # Droits d'accès
    can_invite_guests = Column(Boolean, default=True)
    can_sublease = Column(Boolean, default=False)
    can_access_common_areas = Column(Boolean, default=True)
    can_receive_mail = Column(Boolean, default=True)
    
    # Période d'occupation
    move_in_date = Column(DateTime, nullable=True)
    move_out_date = Column(DateTime, nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True)
    occupancy_status = Column(String(20), default="ACTIVE")  # ACTIVE, TERMINATED, SUSPENDED
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    apartment = relationship("Apartment", backref="occupancies")
    tenant = relationship("UserAuth", back_populates="occupied_properties")
    lease = relationship("Lease", backref="occupancies")


class UserPermission(Base):
    """Permissions granulaires des utilisateurs"""
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    granted_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Permission
    permission_type = Column(String(50), nullable=False)  # Type de permission
    resource_type = Column(String(50), nullable=False)    # Type de ressource (apartment, building, etc.)
    resource_id = Column(Integer, nullable=True)          # ID de la ressource (null = global)
    scope = Column(String(50), nullable=False)            # Portée de la permission
    
    # Conditions
    conditions = Column(JSON, nullable=True)              # Conditions d'application
    expires_at = Column(DateTime, nullable=True)          # Date d'expiration
    
    # Statut
    is_active = Column(Boolean, default=True)
    
    # Métadonnées
    granted_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Relations
    user = relationship("UserAuth", foreign_keys=[user_id], back_populates="permissions")
    granted_by_user = relationship("UserAuth", foreign_keys=[granted_by])


class PermissionTemplate(Base):
    """Templates de permissions pour les rôles"""
    __tablename__ = "permission_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Template
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String(50), nullable=False)             # Rôle associé
    
    # Permissions
    permissions = Column(JSON, nullable=False)            # Liste des permissions
    default_scope = Column(String(50), nullable=False)    # Portée par défaut
    
    # Configuration
    is_system_template = Column(Boolean, default=False)   # Template système
    is_active = Column(Boolean, default=True)
    
    # Métadonnées
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    creator = relationship("UserAuth")


class AccessLog(Base):
    """Log des accès et actions des utilisateurs"""
    __tablename__ = "access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Utilisateur et action
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    action = Column(String(50), nullable=False)           # Type d'action
    resource_type = Column(String(50), nullable=False)    # Type de ressource
    resource_id = Column(Integer, nullable=True)          # ID de la ressource
    
    # Détails de l'accès
    permission_used = Column(String(50), nullable=True)   # Permission utilisée
    access_method = Column(String(20), nullable=False)    # WEB, API, MOBILE
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Résultat
    success = Column(Boolean, nullable=False)
    error_message = Column(String(500), nullable=True)
    response_time = Column(Integer, nullable=True)        # Temps de réponse en ms
    
    # Données
    request_data = Column(JSON, nullable=True)            # Données de la requête
    response_data = Column(JSON, nullable=True)           # Données de la réponse
    
    # Métadonnées
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session_id = Column(String(255), nullable=True)
    
    # Relations
    user = relationship("UserAuth", back_populates="access_logs")


# Fonctions utilitaires pour les permissions

def get_default_permissions_by_role(role: UserRole) -> Dict[str, Any]:
    """Retourne les permissions par défaut pour un rôle"""
    
    permissions_map = {
        UserRole.SUPER_ADMIN: {
            "permissions": [p.value for p in PermissionType],
            "scope": PropertyScope.GLOBAL,
            "description": "Accès total au système"
        },
        
        UserRole.PROPERTY_MANAGER: {
            "permissions": [
                PermissionType.VIEW, PermissionType.EDIT, PermissionType.CREATE,
                PermissionType.MANAGE_LEASES, PermissionType.MANAGE_TENANTS,
                PermissionType.MANAGE_FINANCES, PermissionType.ACCESS_REPORTS,
                PermissionType.SCHEDULE_VISITS, PermissionType.MANAGE_MAINTENANCE
            ],
            "scope": PropertyScope.BUILDING,
            "description": "Gestion complète des propriétés assignées"
        },
        
        UserRole.OWNER: {
            "permissions": [
                PermissionType.VIEW, PermissionType.EDIT,
                PermissionType.SIGN_DOCUMENTS, PermissionType.MANAGE_LEASES,
                PermissionType.ACCESS_REPORTS, PermissionType.MANAGE_FINANCES
            ],
            "scope": PropertyScope.APARTMENT,
            "description": "Gestion de ses propriétés"
        },
        
        UserRole.TENANT: {
            "permissions": [
                PermissionType.VIEW
            ],
            "scope": PropertyScope.TENANT_ONLY,
            "description": "Consultation de ses informations locatives"
        },
        
        UserRole.AGENT: {
            "permissions": [
                PermissionType.VIEW, PermissionType.SCHEDULE_VISITS,
                PermissionType.MANAGE_TENANTS
            ],
            "scope": PropertyScope.BUILDING,
            "description": "Actions commerciales et visites"
        },
        
        UserRole.MAINTENANCE: {
            "permissions": [
                PermissionType.VIEW, PermissionType.MANAGE_MAINTENANCE,
                PermissionType.MANAGE_KEYS
            ],
            "scope": PropertyScope.BUILDING,
            "description": "Gestion technique et maintenance"
        },
        
        UserRole.ACCOUNTANT: {
            "permissions": [
                PermissionType.VIEW, PermissionType.MANAGE_FINANCES,
                PermissionType.ACCESS_REPORTS
            ],
            "scope": PropertyScope.GLOBAL,
            "description": "Gestion comptable et financière"
        },
        
        UserRole.VIEWER: {
            "permissions": [
                PermissionType.VIEW
            ],
            "scope": PropertyScope.APARTMENT,
            "description": "Consultation seulement"
        }
    }
    
    return permissions_map.get(role, {
        "permissions": [PermissionType.VIEW],
        "scope": PropertyScope.TENANT_ONLY,
        "description": "Permissions minimales"
    })


def create_management_company_templates() -> List[Dict[str, Any]]:
    """Crée les templates par défaut pour les sociétés de gestion"""
    
    return [
        {
            "name": "Gestion locative complète",
            "role": UserRole.PROPERTY_MANAGER,
            "permissions": [
                PermissionType.VIEW, PermissionType.EDIT, PermissionType.CREATE,
                PermissionType.MANAGE_LEASES, PermissionType.MANAGE_TENANTS,
                PermissionType.MANAGE_FINANCES, PermissionType.SCHEDULE_VISITS,
                PermissionType.MANAGE_MAINTENANCE, PermissionType.ACCESS_REPORTS
            ],
            "default_scope": PropertyScope.BUILDING,
            "is_system_template": True,
            "description": "Gestion complète d'un portefeuille immobilier"
        },
        {
            "name": "Gestion locative simple",
            "role": UserRole.PROPERTY_MANAGER,
            "permissions": [
                PermissionType.VIEW, PermissionType.EDIT,
                PermissionType.MANAGE_LEASES, PermissionType.MANAGE_TENANTS,
                PermissionType.ACCESS_REPORTS
            ],
            "default_scope": PropertyScope.BUILDING,
            "is_system_template": True,
            "description": "Gestion locative sans gestion financière"
        },
        {
            "name": "Agent commercial",
            "role": UserRole.AGENT,
            "permissions": [
                PermissionType.VIEW, PermissionType.SCHEDULE_VISITS,
                PermissionType.MANAGE_TENANTS
            ],
            "default_scope": PropertyScope.BUILDING,
            "is_system_template": True,
            "description": "Commercialisation et prospection"
        },
        {
            "name": "Maintenance technique",
            "role": UserRole.MAINTENANCE,
            "permissions": [
                PermissionType.VIEW, PermissionType.MANAGE_MAINTENANCE,
                PermissionType.MANAGE_KEYS
            ],
            "default_scope": PropertyScope.BUILDING,
            "is_system_template": True,
            "description": "Gestion technique et maintenance"
        }
    ]


def create_ownership_scenarios() -> List[Dict[str, Any]]:
    """Scénarios d'exemples pour multi-propriété"""
    
    return [
        {
            "scenario": "Propriété unique",
            "description": "Un seul propriétaire à 100%",
            "ownerships": [
                {"percentage": 100.0, "type": "FULL", "can_sign_leases": True}
            ]
        },
        {
            "scenario": "Copropriété 50/50",
            "description": "Deux propriétaires à parts égales",
            "ownerships": [
                {"percentage": 50.0, "type": "FULL", "can_sign_leases": True},
                {"percentage": 50.0, "type": "FULL", "can_sign_leases": True}
            ]
        },
        {
            "scenario": "Usufruit/Nue-propriété",
            "description": "Séparation usufruit et nue-propriété",
            "ownerships": [
                {"percentage": 100.0, "type": "USUFRUCT", "can_sign_leases": True},
                {"percentage": 100.0, "type": "BARE_OWNERSHIP", "can_sign_leases": False}
            ]
        },
        {
            "scenario": "Propriété familiale",
            "description": "Plusieurs héritiers avec parts inégales",
            "ownerships": [
                {"percentage": 40.0, "type": "FULL", "can_sign_leases": True},
                {"percentage": 30.0, "type": "FULL", "can_sign_leases": False},
                {"percentage": 20.0, "type": "FULL", "can_sign_leases": False},
                {"percentage": 10.0, "type": "FULL", "can_sign_leases": False}
            ]
        }
    ]