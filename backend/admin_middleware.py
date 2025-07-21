"""
Middleware d'authentification pour l'administration
Gestion des sessions et permissions admin
"""
from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional, List, Callable
from datetime import datetime, timedelta
import jwt
from functools import wraps

from database import get_db
from auth import get_current_user, SECRET_KEY, ALGORITHM
from models import UserAuth
from models_admin import AdminUser, AdminAction
from enums import AdminRole, ActionType, EntityType
from audit_logger import AuditLogger


class AdminAuthMiddleware:
    """Middleware d'authentification pour les administrateurs"""
    
    @staticmethod
    def get_admin_user(
        current_user: UserAuth = Depends(get_current_user), 
        db: Session = Depends(get_db)
    ) -> AdminUser:
        """
        Récupère l'utilisateur admin actuel et vérifie qu'il est actif
        """
        admin_user = db.query(AdminUser).filter(
            AdminUser.user_id == current_user.id,
            AdminUser.is_active == True
        ).first()
        
        if not admin_user:
            # Audit de la tentative d'accès non autorisée
            AuditLogger.log_action(
                db=db,
                user_id=current_user.id,
                action=ActionType.ACCESS_DENIED,
                entity_type=EntityType.USER,
                description=f"Tentative d'accès admin refusée pour {current_user.email}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès administrateur requis. Votre compte n'a pas les privilèges nécessaires."
            )
        
        # Mettre à jour la dernière connexion admin
        admin_user.last_login_at = datetime.utcnow()
        db.commit()
        
        # Audit de l'accès admin réussi
        AuditLogger.log_action(
            db=db,
            user_id=current_user.id,
            action=ActionType.LOGIN,
            entity_type=EntityType.USER,
            description=f"Accès admin réussi - Rôle: {admin_user.admin_role}"
        )
        
        return admin_user
    
    @staticmethod
    def require_permission(permission: str) -> Callable:
        """
        Décorateur pour vérifier une permission admin spécifique
        
        Usage:
        @require_permission("manage_users")
        def my_admin_function(admin_user: AdminUser = Depends(AdminAuthMiddleware.get_admin_user)):
            pass
        """
        def permission_decorator(func):
            @wraps(func)
            async def permission_wrapper(
                admin_user: AdminUser = Depends(AdminAuthMiddleware.get_admin_user),
                db: Session = Depends(get_db),
                *args, **kwargs
            ):
                if not admin_user.has_permission(permission):
                    # Audit de la tentative d'accès non autorisée
                    AuditLogger.log_action(
                        db=db,
                        user_id=admin_user.user_id,
                        action=ActionType.ACCESS_DENIED,
                        entity_type=EntityType.USER,
                        description=f"Permission {permission} refusée pour {admin_user.user.email if admin_user.user else admin_user.user_id}"
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission '{permission}' requise. Contactez un super administrateur."
                    )
                
                return await func(admin_user=admin_user, db=db, *args, **kwargs)
            return permission_wrapper
        return permission_decorator
    
    @staticmethod
    def require_role(required_roles: List[AdminRole]) -> Callable:
        """
        Décorateur pour vérifier un rôle admin spécifique
        """
        def role_decorator(func):
            @wraps(func)
            async def role_wrapper(
                admin_user: AdminUser = Depends(AdminAuthMiddleware.get_admin_user),
                db: Session = Depends(get_db),
                *args, **kwargs
            ):
                if admin_user.admin_role not in required_roles:
                    # Audit de la tentative d'accès non autorisée
                    AuditLogger.log_action(
                        db=db,
                        user_id=admin_user.user_id,
                        action=ActionType.ACCESS_DENIED,
                        entity_type=EntityType.USER,
                        description=f"Rôle insuffisant. Requis: {required_roles}, Actuel: {admin_user.admin_role}"
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Rôle administrateur insuffisant. Rôles requis: {', '.join(required_roles)}"
                    )
                
                return await func(admin_user=admin_user, db=db, *args, **kwargs)
            return role_wrapper
        return role_decorator
    
    @staticmethod
    def require_super_admin(func):
        """
        Décorateur pour les fonctions nécessitant un super admin
        """
        @wraps(func)
        async def super_admin_wrapper(
            admin_user: AdminUser = Depends(AdminAuthMiddleware.get_admin_user),
            db: Session = Depends(get_db),
            *args, **kwargs
        ):
            if admin_user.admin_role != AdminRole.SUPER_ADMIN:
                # Audit de la tentative d'accès non autorisée
                AuditLogger.log_action(
                    db=db,
                    user_id=admin_user.user_id,
                    action=ActionType.ACCESS_DENIED,
                    entity_type=EntityType.USER,
                    description=f"Accès super admin refusé. Rôle actuel: {admin_user.admin_role}"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Privilèges de super administrateur requis."
                )
            
            return await func(admin_user=admin_user, db=db, *args, **kwargs)
        return super_admin_wrapper


class AdminPermissionChecker:
    """Vérificateur de permissions pour les administrateurs"""
    
    PERMISSION_HIERARCHY = {
        AdminRole.SUPER_ADMIN: [
            "manage_users", "manage_subscriptions", "view_finances", 
            "manage_properties", "access_audit_logs", "manage_admins",
            "view_dashboard", "manage_system_settings"
        ],
        AdminRole.USER_MANAGER: [
            "manage_users", "view_dashboard", "access_audit_logs"
        ],
        AdminRole.SUPPORT: [
            "manage_users", "view_dashboard", "manage_subscriptions"
        ],
        AdminRole.MODERATOR: [
            "manage_properties", "view_dashboard", "access_audit_logs"
        ],
        AdminRole.VIEWER: [
            "view_dashboard"
        ]
    }
    
    @classmethod
    def get_role_permissions(cls, role: AdminRole) -> List[str]:
        """Retourne les permissions par défaut pour un rôle"""
        return cls.PERMISSION_HIERARCHY.get(role, [])
    
    @classmethod
    def check_permission(cls, admin_user: AdminUser, permission: str) -> bool:
        """Vérifie si un admin a une permission spécifique"""
        return admin_user.has_permission(permission)
    
    @classmethod
    def get_user_permissions(cls, admin_user: AdminUser) -> List[str]:
        """Retourne toutes les permissions d'un utilisateur admin"""
        permissions = []
        
        # Permissions de base selon le rôle
        role_permissions = cls.get_role_permissions(admin_user.admin_role)
        permissions.extend(role_permissions)
        
        # Permissions spécifiques
        if admin_user.can_manage_users:
            permissions.append("manage_users")
        if admin_user.can_manage_subscriptions:
            permissions.append("manage_subscriptions")
        if admin_user.can_view_finances:
            permissions.append("view_finances")
        if admin_user.can_manage_properties:
            permissions.append("manage_properties")
        if admin_user.can_access_audit_logs:
            permissions.append("access_audit_logs")
        if admin_user.can_manage_admins:
            permissions.append("manage_admins")
        
        # Supprimer les doublons et retourner
        return list(set(permissions))


class AdminSessionManager:
    """Gestionnaire de sessions pour les administrateurs"""
    
    @staticmethod
    def log_admin_action(
        db: Session,
        admin_user: AdminUser,
        action_type: str,
        description: str,
        target_user_id: Optional[int] = None,
        additional_data: Optional[dict] = None
    ):
        """
        Log une action administrative
        """
        try:
            admin_action = AdminAction(
                admin_user_id=admin_user.id,
                target_user_id=target_user_id,
                action_type=action_type,
                description=description,
                before_data=additional_data.get("before") if additional_data else None,
                after_data=additional_data.get("after") if additional_data else None
            )
            
            db.add(admin_action)
            db.commit()
            
        except Exception as e:
            print(f"Erreur lors du log d'action admin: {e}")
            db.rollback()
    
    @staticmethod
    def validate_admin_session(admin_user: AdminUser) -> bool:
        """
        Valide une session administrateur
        """
        if not admin_user or not admin_user.is_active:
            return False
        
        # Vérifier la dernière activité (session expirée après 8h d'inactivité)
        if admin_user.last_login_at:
            inactive_duration = datetime.utcnow() - admin_user.last_login_at
            if inactive_duration > timedelta(hours=8):
                return False
        
        return True
    
    @staticmethod
    def get_admin_context(admin_user: AdminUser) -> dict:
        """
        Retourne le contexte administrateur pour les templates et APIs
        """
        return {
            "admin_id": admin_user.id,
            "user_id": admin_user.user_id,
            "admin_role": admin_user.admin_role,
            "admin_email": admin_user.user.email if admin_user.user else None,
            "admin_name": f"{admin_user.user.first_name} {admin_user.user.last_name}" if admin_user.user else None,
            "permissions": AdminPermissionChecker.get_user_permissions(admin_user),
            "is_super_admin": admin_user.admin_role == AdminRole.SUPER_ADMIN,
            "last_login": admin_user.last_login_at,
            "session_valid": AdminSessionManager.validate_admin_session(admin_user)
        }


# Helpers pour les dépendances FastAPI
def get_admin_user_dependency():
    """Dépendance pour récupérer l'utilisateur admin"""
    return Depends(AdminAuthMiddleware.get_admin_user)


def require_admin_permission(permission: str):
    """Helper pour créer une dépendance de permission"""
    def permission_dependency(
        admin_user: AdminUser = Depends(AdminAuthMiddleware.get_admin_user),
        db: Session = Depends(get_db)
    ):
        if not admin_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' requise"
            )
        return admin_user
    
    return Depends(permission_dependency)


def require_admin_role(role: AdminRole):
    """Helper pour créer une dépendance de rôle"""
    def role_dependency(
        admin_user: AdminUser = Depends(AdminAuthMiddleware.get_admin_user)
    ):
        if admin_user.admin_role != role and admin_user.admin_role != AdminRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle '{role}' requis"
            )
        return admin_user
    
    return Depends(role_dependency)