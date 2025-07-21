"""
Service de gestion des permissions avec architecture SOLID
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from models import UserAuth
from property_management_models import (
    UserPermission, PermissionTemplate, AccessLog, PropertyOwnership,
    TenantOccupancy, PropertyManagement, ManagementCompany,
    UserRole, PermissionType, PropertyScope,
    get_default_permissions_by_role
)


class IPermissionChecker(ABC):
    """Interface pour la vérification des permissions"""
    
    @abstractmethod
    def has_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int] = None
    ) -> bool:
        """Vérifie si un utilisateur a une permission spécifique"""
        pass
    
    @abstractmethod
    def get_user_permissions(
        self,
        user_id: int,
        resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retourne toutes les permissions d'un utilisateur"""
        pass
    
    @abstractmethod
    def get_accessible_resources(
        self,
        user_id: int,
        resource_type: str,
        permission: PermissionType
    ) -> List[int]:
        """Retourne les IDs des ressources accessibles pour une permission"""
        pass


class IPermissionManager(ABC):
    """Interface pour la gestion des permissions"""
    
    @abstractmethod
    def grant_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int],
        scope: PropertyScope,
        granted_by: int,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Accorde une permission à un utilisateur"""
        pass
    
    @abstractmethod
    def revoke_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int],
        revoked_by: int
    ) -> bool:
        """Révoque une permission d'un utilisateur"""
        pass
    
    @abstractmethod
    def apply_role_template(
        self,
        user_id: int,
        role: UserRole,
        resource_id: Optional[int],
        applied_by: int
    ) -> bool:
        """Applique un template de rôle à un utilisateur"""
        pass


class DatabasePermissionChecker(IPermissionChecker):
    """Vérificateur de permissions basé sur la base de données"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def has_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int] = None
    ) -> bool:
        """Vérifie si un utilisateur a une permission spécifique"""
        
        # Vérifier les permissions directes
        query = self.db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_type == permission,
            UserPermission.resource_type == resource_type,
            UserPermission.is_active == True
        )
        
        # Filtrer par resource_id si spécifié
        if resource_id is not None:
            query = query.filter(
                (UserPermission.resource_id == resource_id) |
                (UserPermission.resource_id.is_(None))  # Permissions globales
            )
        
        # Vérifier l'expiration
        query = query.filter(
            (UserPermission.expires_at.is_(None)) |
            (UserPermission.expires_at > datetime.utcnow())
        )
        
        direct_permission = query.first()
        if direct_permission:
            return True
        
        # Vérifier les permissions héritées
        return self._check_inherited_permissions(user_id, permission, resource_type, resource_id)
    
    def _check_inherited_permissions(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int]
    ) -> bool:
        """Vérifie les permissions héritées (propriété, gestion, etc.)"""
        
        if resource_type == "apartment" and resource_id:
            # Vérifier si l'utilisateur est propriétaire
            ownership = self.db.query(PropertyOwnership).filter(
                PropertyOwnership.apartment_id == resource_id,
                PropertyOwnership.owner_id == user_id,
                PropertyOwnership.is_active == True
            ).first()
            
            if ownership:
                # Propriétaires ont des permissions étendues
                owner_permissions = [
                    PermissionType.VIEW, PermissionType.EDIT,
                    PermissionType.SIGN_DOCUMENTS, PermissionType.MANAGE_LEASES,
                    PermissionType.ACCESS_REPORTS
                ]
                if permission in owner_permissions:
                    if permission == PermissionType.SIGN_DOCUMENTS and not ownership.can_sign_leases:
                        return False
                    return True
            
            # Vérifier si l'utilisateur est locataire
            occupancy = self.db.query(TenantOccupancy).filter(
                TenantOccupancy.apartment_id == resource_id,
                TenantOccupancy.tenant_id == user_id,
                TenantOccupancy.is_active == True
            ).first()
            
            if occupancy:
                # Locataires ont des permissions limitées
                tenant_permissions = [PermissionType.VIEW]
                return permission in tenant_permissions
            
            # Vérifier si l'utilisateur est gestionnaire
            management = self.db.query(PropertyManagement).filter(
                PropertyManagement.apartment_id == resource_id,
                PropertyManagement.managed_by == user_id,
                PropertyManagement.is_active == True
            ).first()
            
            if management:
                # Vérifier les permissions déléguées
                delegated = management.delegated_permissions or {}
                return permission.value in delegated.get('permissions', [])
        
        return False
    
    def get_user_permissions(
        self,
        user_id: int,
        resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retourne toutes les permissions d'un utilisateur"""
        
        query = self.db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.is_active == True
        )
        
        if resource_type:
            query = query.filter(UserPermission.resource_type == resource_type)
        
        # Filtrer les permissions expirées
        query = query.filter(
            (UserPermission.expires_at.is_(None)) |
            (UserPermission.expires_at > datetime.utcnow())
        )
        
        permissions = query.all()
        
        result = []
        for perm in permissions:
            result.append({
                'permission_type': perm.permission_type,
                'resource_type': perm.resource_type,
                'resource_id': perm.resource_id,
                'scope': perm.scope,
                'expires_at': perm.expires_at,
                'granted_at': perm.granted_at
            })
        
        # Ajouter les permissions héritées
        inherited = self._get_inherited_permissions(user_id, resource_type)
        result.extend(inherited)
        
        return result
    
    def _get_inherited_permissions(
        self,
        user_id: int,
        resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retourne les permissions héritées"""
        
        inherited = []
        
        # Permissions de propriétaire
        ownerships = self.db.query(PropertyOwnership).filter(
            PropertyOwnership.owner_id == user_id,
            PropertyOwnership.is_active == True
        ).all()
        
        for ownership in ownerships:
            if not resource_type or resource_type == "apartment":
                owner_perms = [
                    PermissionType.VIEW, PermissionType.EDIT,
                    PermissionType.ACCESS_REPORTS, PermissionType.MANAGE_FINANCES
                ]
                
                if ownership.can_sign_leases:
                    owner_perms.append(PermissionType.SIGN_DOCUMENTS)
                
                for perm in owner_perms:
                    inherited.append({
                        'permission_type': perm,
                        'resource_type': 'apartment',
                        'resource_id': ownership.apartment_id,
                        'scope': PropertyScope.APARTMENT,
                        'source': 'ownership',
                        'ownership_percentage': float(ownership.ownership_percentage)
                    })
        
        # Permissions de locataire
        occupancies = self.db.query(TenantOccupancy).filter(
            TenantOccupancy.tenant_id == user_id,
            TenantOccupancy.is_active == True
        ).all()
        
        for occupancy in occupancies:
            if not resource_type or resource_type == "apartment":
                inherited.append({
                    'permission_type': PermissionType.VIEW,
                    'resource_type': 'apartment',
                    'resource_id': occupancy.apartment_id,
                    'scope': PropertyScope.TENANT_ONLY,
                    'source': 'tenancy',
                    'occupancy_type': occupancy.occupancy_type
                })
        
        # Permissions de gestionnaire
        managements = self.db.query(PropertyManagement).filter(
            PropertyManagement.managed_by == user_id,
            PropertyManagement.is_active == True
        ).all()
        
        for management in managements:
            if not resource_type or resource_type == "apartment":
                delegated = management.delegated_permissions or {}
                for perm_name in delegated.get('permissions', []):
                    try:
                        perm = PermissionType(perm_name)
                        inherited.append({
                            'permission_type': perm,
                            'resource_type': 'apartment',
                            'resource_id': management.apartment_id,
                            'scope': PropertyScope.APARTMENT,
                            'source': 'management',
                            'company': management.management_company.name
                        })
                    except ValueError:
                        continue
        
        return inherited
    
    def get_accessible_resources(
        self,
        user_id: int,
        resource_type: str,
        permission: PermissionType
    ) -> List[int]:
        """Retourne les IDs des ressources accessibles pour une permission"""
        
        accessible_ids = set()
        
        # Permissions directes
        direct_permissions = self.db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_type == permission,
            UserPermission.resource_type == resource_type,
            UserPermission.is_active == True,
            (UserPermission.expires_at.is_(None)) |
            (UserPermission.expires_at > datetime.utcnow())
        ).all()
        
        for perm in direct_permissions:
            if perm.resource_id:
                accessible_ids.add(perm.resource_id)
            elif perm.scope == PropertyScope.GLOBAL:
                # Permission globale - retourner tous les IDs de ce type
                if resource_type == "apartment":
                    from models import Apartment
                    all_apartments = self.db.query(Apartment.id).all()
                    accessible_ids.update([apt.id for apt in all_apartments])
        
        # Permissions héritées
        if resource_type == "apartment":
            # Propriétés
            ownerships = self.db.query(PropertyOwnership.apartment_id).filter(
                PropertyOwnership.owner_id == user_id,
                PropertyOwnership.is_active == True
            ).all()
            
            owner_permissions = [
                PermissionType.VIEW, PermissionType.EDIT,
                PermissionType.ACCESS_REPORTS, PermissionType.MANAGE_FINANCES
            ]
            
            if permission in owner_permissions:
                accessible_ids.update([ownership.apartment_id for ownership in ownerships])
            
            # Locations
            if permission == PermissionType.VIEW:
                occupancies = self.db.query(TenantOccupancy.apartment_id).filter(
                    TenantOccupancy.tenant_id == user_id,
                    TenantOccupancy.is_active == True
                ).all()
                accessible_ids.update([occ.apartment_id for occ in occupancies])
            
            # Gestion
            managements = self.db.query(PropertyManagement).filter(
                PropertyManagement.managed_by == user_id,
                PropertyManagement.is_active == True
            ).all()
            
            for management in managements:
                delegated = management.delegated_permissions or {}
                if permission.value in delegated.get('permissions', []):
                    accessible_ids.add(management.apartment_id)
        
        return list(accessible_ids)


class DatabasePermissionManager(IPermissionManager):
    """Gestionnaire de permissions basé sur la base de données"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def grant_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int],
        scope: PropertyScope,
        granted_by: int,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Accorde une permission à un utilisateur"""
        
        try:
            # Vérifier si la permission existe déjà
            existing = self.db.query(UserPermission).filter(
                UserPermission.user_id == user_id,
                UserPermission.permission_type == permission,
                UserPermission.resource_type == resource_type,
                UserPermission.resource_id == resource_id,
                UserPermission.is_active == True
            ).first()
            
            if existing:
                # Mettre à jour l'expiration si nécessaire
                if expires_at and (not existing.expires_at or expires_at > existing.expires_at):
                    existing.expires_at = expires_at
                    self.db.commit()
                return True
            
            # Créer la nouvelle permission
            new_permission = UserPermission(
                user_id=user_id,
                granted_by=granted_by,
                permission_type=permission,
                resource_type=resource_type,
                resource_id=resource_id,
                scope=scope,
                expires_at=expires_at
            )
            
            self.db.add(new_permission)
            self.db.commit()
            
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def revoke_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int],
        revoked_by: int
    ) -> bool:
        """Révoque une permission d'un utilisateur"""
        
        try:
            permissions = self.db.query(UserPermission).filter(
                UserPermission.user_id == user_id,
                UserPermission.permission_type == permission,
                UserPermission.resource_type == resource_type,
                UserPermission.resource_id == resource_id,
                UserPermission.is_active == True
            ).all()
            
            for perm in permissions:
                perm.is_active = False
            
            self.db.commit()
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def apply_role_template(
        self,
        user_id: int,
        role: UserRole,
        resource_id: Optional[int],
        applied_by: int
    ) -> bool:
        """Applique un template de rôle à un utilisateur"""
        
        try:
            # Récupérer les permissions par défaut pour ce rôle
            default_perms = get_default_permissions_by_role(role)
            
            # Accorder chaque permission
            for perm_name in default_perms["permissions"]:
                if isinstance(perm_name, str):
                    permission = PermissionType(perm_name)
                else:
                    permission = perm_name
                
                self.grant_permission(
                    user_id=user_id,
                    permission=permission,
                    resource_type="apartment",  # Par défaut
                    resource_id=resource_id,
                    scope=PropertyScope(default_perms["scope"]),
                    granted_by=applied_by
                )
            
            return True
            
        except Exception:
            self.db.rollback()
            return False


class AccessLogger:
    """Service de logging des accès"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_access(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        success: bool,
        permission_used: Optional[str] = None,
        access_method: str = "WEB",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        request_data: Optional[Dict] = None,
        response_data: Optional[Dict] = None,
        response_time: Optional[int] = None,
        session_id: Optional[str] = None
    ):
        """Enregistre un accès dans les logs"""
        
        try:
            log_entry = AccessLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                permission_used=permission_used,
                access_method=access_method,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message,
                request_data=request_data,
                response_data=response_data,
                response_time=response_time,
                session_id=session_id
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            # Mettre à jour les statistiques d'utilisation
            if success and permission_used:
                self._update_permission_usage(user_id, permission_used)
            
        except Exception:
            self.db.rollback()
    
    def _update_permission_usage(self, user_id: int, permission_used: str):
        """Met à jour les statistiques d'utilisation des permissions"""
        
        try:
            permission = self.db.query(UserPermission).filter(
                UserPermission.user_id == user_id,
                UserPermission.permission_type == permission_used,
                UserPermission.is_active == True
            ).first()
            
            if permission:
                permission.last_used_at = datetime.utcnow()
                permission.usage_count += 1
                self.db.commit()
        except Exception:
            pass


class PermissionService:
    """Service principal de gestion des permissions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.checker = DatabasePermissionChecker(db)
        self.manager = DatabasePermissionManager(db)
        self.logger = AccessLogger(db)
    
    def check_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int] = None
    ) -> bool:
        """Vérifie une permission et log l'accès"""
        
        has_perm = self.checker.has_permission(user_id, permission, resource_type, resource_id)
        
        self.logger.log_access(
            user_id=user_id,
            action="CHECK_PERMISSION",
            resource_type=resource_type,
            resource_id=resource_id,
            success=has_perm,
            permission_used=permission.value
        )
        
        return has_perm
    
    def require_permission(
        self,
        user_id: int,
        permission: PermissionType,
        resource_type: str,
        resource_id: Optional[int] = None
    ):
        """Vérifie une permission et lève une exception si refusée"""
        
        if not self.check_permission(user_id, permission, resource_type, resource_id):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission {permission.value} requise pour {resource_type}"
            )
    
    def get_user_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Retourne les données du dashboard en fonction des permissions"""
        
        dashboard_data = {
            "accessible_apartments": [],
            "managed_properties": [],
            "owned_properties": [],
            "rented_properties": [],
            "permissions_summary": {},
            "recent_actions": []
        }
        
        # Appartements accessibles
        accessible_apt_ids = self.checker.get_accessible_resources(
            user_id, "apartment", PermissionType.VIEW
        )
        
        if accessible_apt_ids:
            from models import Apartment
            apartments = self.db.query(Apartment).filter(
                Apartment.id.in_(accessible_apt_ids)
            ).all()
            
            dashboard_data["accessible_apartments"] = [
                {
                    "id": apt.id,
                    "address": apt.address,
                    "type": apt.apartment_type,
                    "surface": apt.surface_area
                }
                for apt in apartments
            ]
        
        # Propriétés gérées
        managements = self.db.query(PropertyManagement).filter(
            PropertyManagement.managed_by == user_id,
            PropertyManagement.is_active == True
        ).all()
        
        dashboard_data["managed_properties"] = [
            {
                "apartment_id": mgmt.apartment_id,
                "company": mgmt.management_company.name,
                "contract_type": mgmt.contract_type,
                "permissions": mgmt.delegated_permissions
            }
            for mgmt in managements
        ]
        
        # Propriétés possédées
        ownerships = self.db.query(PropertyOwnership).filter(
            PropertyOwnership.owner_id == user_id,
            PropertyOwnership.is_active == True
        ).all()
        
        dashboard_data["owned_properties"] = [
            {
                "apartment_id": ownership.apartment_id,
                "percentage": float(ownership.ownership_percentage),
                "type": ownership.ownership_type,
                "can_sign": ownership.can_sign_leases
            }
            for ownership in ownerships
        ]
        
        # Propriétés louées
        occupancies = self.db.query(TenantOccupancy).filter(
            TenantOccupancy.tenant_id == user_id,
            TenantOccupancy.is_active == True
        ).all()
        
        dashboard_data["rented_properties"] = [
            {
                "apartment_id": occ.apartment_id,
                "occupancy_type": occ.occupancy_type,
                "rent_responsibility": float(occ.rent_responsibility),
                "move_in_date": occ.move_in_date
            }
            for occ in occupancies
        ]
        
        # Résumé des permissions
        all_permissions = self.checker.get_user_permissions(user_id)
        permissions_by_type = {}
        
        for perm in all_permissions:
            perm_type = perm['permission_type']
            if perm_type not in permissions_by_type:
                permissions_by_type[perm_type] = 0
            permissions_by_type[perm_type] += 1
        
        dashboard_data["permissions_summary"] = permissions_by_type
        
        # Actions récentes
        recent_logs = self.db.query(AccessLog).filter(
            AccessLog.user_id == user_id
        ).order_by(AccessLog.timestamp.desc()).limit(10).all()
        
        dashboard_data["recent_actions"] = [
            {
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "success": log.success,
                "timestamp": log.timestamp
            }
            for log in recent_logs
        ]
        
        return dashboard_data


# Factory pour créer le service
def create_permission_service(db: Session) -> PermissionService:
    """Factory pour créer le service de permissions"""
    return PermissionService(db)