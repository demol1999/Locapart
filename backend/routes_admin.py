"""
Routes API pour l'administration
Panel administrateur avec toutes les fonctionnalités
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from auth import get_current_user
from models import UserAuth
from models_admin import AdminUser
from services.admin_service import AdminService
from schemas_admin import (
    AdminDashboardOut, UsersListOut, UsersListQuery, UserDetailedOut,
    UserActionRequest, UserActionResponse, AdminUserCreate, AdminUserOut,
    AdminUserUpdate, AdminNotificationOut, SystemSettingOut, 
    SystemSettingCreate, SystemSettingUpdate, SearchResults, SearchQuery,
    AdminStatsOut, AdminStatsQuery
)
from error_handlers import PermissionErrorHandler, BusinessLogicErrorHandler
from audit_logger import AuditLogger
from enums import AdminRole, EntityType, ActionType


# Router principal pour l'administration
admin_router = APIRouter(prefix="/admin", tags=["Administration"])


# === MIDDLEWARE DE SÉCURITÉ ADMIN ===

def get_admin_user(current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)) -> AdminUser:
    """
    Récupère l'utilisateur admin actuel et vérifie ses permissions
    """
    admin_user = db.query(AdminUser).filter(
        AdminUser.user_id == current_user.id,
        AdminUser.is_active == True
    ).first()
    
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis"
        )
    
    # Audit de l'accès admin
    AuditLogger.log_action(
        db=db,
        user_id=current_user.id,
        action=ActionType.read,
        entity_type=EntityType.USER,
        description=f"Accès panel admin - Rôle: {admin_user.admin_role}"
    )
    
    return admin_user


def require_admin_permission(permission: str):
    """
    Décorateur pour vérifier une permission admin spécifique
    """
    def permission_checker(admin_user: AdminUser = Depends(get_admin_user), db: Session = Depends(get_db)):
        if not admin_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission {permission} requise"
            )
        return admin_user
    return Depends(permission_checker)


# === ROUTES DASHBOARD ===

@admin_router.get("/dashboard", response_model=AdminDashboardOut)
def get_admin_dashboard(
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les données du tableau de bord administrateur
    """
    # Vérifier permission
    if not admin_user.has_permission("view_dashboard"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission view_dashboard requise"
        )
    
    try:
        dashboard_data = AdminService.get_admin_dashboard(db, admin_user.user_id)
        
        # Convertir en schéma Pydantic
        return AdminDashboardOut(
            stats={
                "total_users": dashboard_data.total_users,
                "active_users": dashboard_data.active_users,
                "premium_users": dashboard_data.premium_users,
                "total_apartments": dashboard_data.total_apartments,
                "total_buildings": dashboard_data.total_buildings,
                "total_groups": dashboard_data.total_groups,
                "new_users_today": dashboard_data.new_users_today,
                "new_users_week": dashboard_data.new_users_week
            },
            recent_signups=[
                {
                    "id": signup["id"],
                    "email": signup["email"],
                    "name": signup["name"],
                    "created_at": signup["created_at"],
                    "auth_type": signup["auth_type"],
                    "status": signup["status"]
                }
                for signup in dashboard_data.recent_signups
            ],
            user_growth=[
                {
                    "date": growth["date"],
                    "count": growth["count"]
                }
                for growth in dashboard_data.user_growth
            ],
            subscription_breakdown={
                "free": dashboard_data.subscription_breakdown["free"],
                "premium": dashboard_data.subscription_breakdown["premium"]
            },
            system_alerts=[
                {
                    "type": alert["type"],
                    "title": alert["title"],
                    "message": alert["message"],
                    "action_url": alert.get("action_url")
                }
                for alert in dashboard_data.system_alerts
            ]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement du dashboard: {str(e)}"
        )


# === ROUTES GESTION UTILISATEURS ===

@admin_router.get("/users", response_model=UsersListOut)
async def get_users_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    subscription_filter: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    admin_user: AdminUser = Depends(require_admin_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Récupère la liste paginée des utilisateurs avec filtres
    """
    try:
        users_data = AdminService.get_users_list(
            db=db,
            admin_user_id=admin_user.user_id,
            page=page,
            per_page=per_page,
            search=search,
            status_filter=status_filter,
            subscription_filter=subscription_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return UsersListOut(**users_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des utilisateurs: {str(e)}"
        )


@admin_router.get("/users/{user_id}", response_model=UserDetailedOut)
async def get_user_details(
    user_id: int,
    admin_user: AdminUser = Depends(require_admin_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Récupère les informations détaillées d'un utilisateur
    """
    try:
        user_info = AdminService.get_user_detailed_info(db, admin_user.user_id, user_id)
        
        return UserDetailedOut(
            user_data=user_info.user_data,
            properties_data=user_info.properties_data,
            activity_data=user_info.activity_data
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des détails utilisateur: {str(e)}"
        )


@admin_router.post("/users/{user_id}/actions", response_model=UserActionResponse)
async def perform_user_action(
    user_id: int,
    action_request: UserActionRequest,
    admin_user: AdminUser = Depends(require_admin_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """
    Effectue une action administrative sur un utilisateur
    """
    try:
        success = AdminService.perform_user_action(
            db=db,
            admin_user_id=admin_user.user_id,
            target_user_id=user_id,
            action=action_request.action,
            reason=action_request.reason,
            duration_days=action_request.duration_days
        )
        
        if success:
            return UserActionResponse(
                success=True,
                message=f"Action {action_request.action} effectuée avec succès",
                user_id=user_id,
                action=action_request.action,
                executed_at=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Échec de l'action"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'action sur l'utilisateur: {str(e)}"
        )


# === ROUTES GESTION ADMINISTRATEURS ===

@admin_router.get("/admins", response_model=List[AdminUserOut])
async def get_admin_users(
    admin_user: AdminUser = Depends(require_admin_permission("manage_admins")),
    db: Session = Depends(get_db)
):
    """
    Liste tous les administrateurs
    """
    try:
        admins = db.query(AdminUser).all()
        
        admin_list = []
        for admin in admins:
            admin_data = AdminUserOut(
                id=admin.id,
                user_id=admin.user_id,
                admin_role=admin.admin_role,
                can_manage_users=admin.can_manage_users,
                can_manage_subscriptions=admin.can_manage_subscriptions,
                can_view_finances=admin.can_view_finances,
                can_manage_properties=admin.can_manage_properties,
                can_access_audit_logs=admin.can_access_audit_logs,
                can_manage_admins=admin.can_manage_admins,
                is_active=admin.is_active,
                notes=admin.notes,
                last_login_at=admin.last_login_at,
                created_at=admin.created_at,
                updated_at=admin.updated_at,
                user_email=admin.user.email if admin.user else None,
                user_name=f"{admin.user.first_name} {admin.user.last_name}" if admin.user else None
            )
            admin_list.append(admin_data)
        
        return admin_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des administrateurs: {str(e)}"
        )


@admin_router.post("/admins", response_model=AdminUserOut)
async def create_admin_user(
    admin_create: AdminUserCreate,
    admin_user: AdminUser = Depends(require_admin_permission("manage_admins")),
    db: Session = Depends(get_db)
):
    """
    Crée un nouvel utilisateur administrateur
    """
    try:
        # Vérifier que l'utilisateur existe
        target_user = db.query(UserAuth).filter(UserAuth.id == admin_create.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Vérifier qu'il n'est pas déjà admin
        existing_admin = db.query(AdminUser).filter(AdminUser.user_id == admin_create.user_id).first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet utilisateur est déjà administrateur"
            )
        
        # Créer l'admin
        new_admin = AdminUser(
            user_id=admin_create.user_id,
            admin_role=admin_create.admin_role,
            can_manage_users=admin_create.can_manage_users,
            can_manage_subscriptions=admin_create.can_manage_subscriptions,
            can_view_finances=admin_create.can_view_finances,
            can_manage_properties=admin_create.can_manage_properties,
            can_access_audit_logs=admin_create.can_access_audit_logs,
            can_manage_admins=admin_create.can_manage_admins,
            is_active=admin_create.is_active,
            notes=admin_create.notes,
            created_by_id=admin_user.id
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        # Audit
        AuditLogger.log_action(
            db=db,
            user_id=admin_user.user_id,
            action=ActionType.CREATE,
            entity_type=EntityType.USER,
            entity_id=new_admin.id,
            description=f"Création admin pour {target_user.email}"
        )
        
        return AdminUserOut(
            id=new_admin.id,
            user_id=new_admin.user_id,
            admin_role=new_admin.admin_role,
            can_manage_users=new_admin.can_manage_users,
            can_manage_subscriptions=new_admin.can_manage_subscriptions,
            can_view_finances=new_admin.can_view_finances,
            can_manage_properties=new_admin.can_manage_properties,
            can_access_audit_logs=new_admin.can_access_audit_logs,
            can_manage_admins=new_admin.can_manage_admins,
            is_active=new_admin.is_active,
            notes=new_admin.notes,
            last_login_at=new_admin.last_login_at,
            created_at=new_admin.created_at,
            updated_at=new_admin.updated_at,
            user_email=target_user.email,
            user_name=f"{target_user.first_name} {target_user.last_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de l'administrateur: {str(e)}"
        )


@admin_router.put("/admins/{admin_id}", response_model=AdminUserOut)
async def update_admin_user(
    admin_id: int,
    admin_update: AdminUserUpdate,
    admin_user: AdminUser = Depends(require_admin_permission("manage_admins")),
    db: Session = Depends(get_db)
):
    """
    Met à jour un utilisateur administrateur
    """
    try:
        target_admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
        if not target_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Administrateur non trouvé"
            )
        
        # Mise à jour des champs
        update_data = admin_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(target_admin, field, value)
        
        db.commit()
        db.refresh(target_admin)
        
        # Audit
        AuditLogger.log_action(
            db=db,
            user_id=admin_user.user_id,
            action=ActionType.UPDATE,
            entity_type=EntityType.USER,
            entity_id=target_admin.id,
            description=f"Modification admin {target_admin.user.email if target_admin.user else target_admin.id}"
        )
        
        return AdminUserOut(
            id=target_admin.id,
            user_id=target_admin.user_id,
            admin_role=target_admin.admin_role,
            can_manage_users=target_admin.can_manage_users,
            can_manage_subscriptions=target_admin.can_manage_subscriptions,
            can_view_finances=target_admin.can_view_finances,
            can_manage_properties=target_admin.can_manage_properties,
            can_access_audit_logs=target_admin.can_access_audit_logs,
            can_manage_admins=target_admin.can_manage_admins,
            is_active=target_admin.is_active,
            notes=target_admin.notes,
            last_login_at=target_admin.last_login_at,
            created_at=target_admin.created_at,
            updated_at=target_admin.updated_at,
            user_email=target_admin.user.email if target_admin.user else None,
            user_name=f"{target_admin.user.first_name} {target_admin.user.last_name}" if target_admin.user else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour de l'administrateur: {str(e)}"
        )


# === ROUTES RECHERCHE ET STATISTIQUES ===

@admin_router.post("/search", response_model=SearchResults)
async def admin_search(
    search_query: SearchQuery,
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Recherche globale dans le système administrateur
    """
    try:
        from datetime import datetime
        import time
        
        start_time = time.time()
        
        # Recherche basique - à étendre selon les besoins
        results = []
        
        # Recherche dans les utilisateurs
        if not search_query.entity_types or "users" in search_query.entity_types:
            users = db.query(UserAuth).filter(
                UserAuth.email.ilike(f"%{search_query.query}%") |
                UserAuth.first_name.ilike(f"%{search_query.query}%") |
                UserAuth.last_name.ilike(f"%{search_query.query}%")
            ).limit(search_query.limit // 2).all()
            
            for user in users:
                results.append({
                    "entity_type": "user",
                    "entity_id": user.id,
                    "title": f"{user.first_name} {user.last_name}",
                    "description": user.email,
                    "url": f"/admin/users/{user.id}",
                    "relevance_score": 0.8
                })
        
        search_time = (time.time() - start_time) * 1000
        
        return SearchResults(
            query=search_query.query,
            results=results[:search_query.limit],
            total_found=len(results),
            search_time_ms=search_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )


# === ROUTES D'INFORMATIONS SYSTÈME ===

@admin_router.get("/system/info")
async def get_system_info(
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Informations système pour les administrateurs
    """
    try:
        from datetime import datetime
        import sys
        import os
        
        return {
            "system": {
                "python_version": sys.version,
                "platform": sys.platform,
                "server_time": datetime.utcnow(),
                "database_connection": "active"
            },
            "application": {
                "name": "LocAppart Admin Panel",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development")
            },
            "admin_info": {
                "admin_id": admin_user.id,
                "admin_role": admin_user.admin_role,
                "permissions": admin_user.permissions_summary
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des informations système: {str(e)}"
        )


# === IMPORTS ADDITIONNELS ===
from datetime import datetime