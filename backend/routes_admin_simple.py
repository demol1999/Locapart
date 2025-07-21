"""
Routes API simplifiées pour l'administration
Panel administrateur avec authentification basique
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import UserAuth
from models_admin import AdminUser
from services.admin_service import AdminService
from error_handlers import PermissionErrorHandler
from audit_logger import AuditLogger
from enums import ActionType, EntityType


# Router principal pour l'administration
admin_router = APIRouter(prefix="/admin", tags=["Administration"])


def get_admin_user(current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)) -> AdminUser:
    """
    Récupère l'utilisateur admin actuel et vérifie ses permissions
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
            detail="Accès administrateur requis"
        )
    
    # Mettre à jour la dernière connexion admin
    admin_user.last_login_at = datetime.utcnow()
    db.commit()
    
    return admin_user


# === ROUTES DASHBOARD ===

@admin_router.get("/dashboard")
def get_admin_dashboard(
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les données du tableau de bord administrateur
    """
    if not admin_user.has_permission("view_dashboard"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission view_dashboard requise"
        )
    
    try:
        dashboard_data = AdminService.get_admin_dashboard(db, admin_user.user_id)
        
        return {
            "stats": {
                "total_users": dashboard_data.total_users,
                "active_users": dashboard_data.active_users,
                "premium_users": dashboard_data.premium_users,
                "total_apartments": dashboard_data.total_apartments,
                "total_buildings": dashboard_data.total_buildings,
                "total_groups": dashboard_data.total_groups,
                "new_users_today": dashboard_data.new_users_today,
                "new_users_week": dashboard_data.new_users_week
            },
            "recent_signups": dashboard_data.recent_signups,
            "user_growth": dashboard_data.user_growth,
            "subscription_breakdown": dashboard_data.subscription_breakdown,
            "system_alerts": dashboard_data.system_alerts
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement du dashboard: {str(e)}"
        )


# === ROUTES GESTION UTILISATEURS ===

@admin_router.get("/users")
def get_users_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    subscription_filter: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère la liste paginée des utilisateurs avec filtres
    """
    if not admin_user.has_permission("manage_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission manage_users requise"
        )
    
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
        
        return users_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des utilisateurs: {str(e)}"
        )


@admin_router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les informations détaillées d'un utilisateur
    """
    if not admin_user.has_permission("manage_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission manage_users requise"
        )
    
    try:
        user_info = AdminService.get_user_detailed_info(db, admin_user.user_id, user_id)
        
        return {
            "user_data": user_info.user_data,
            "properties_data": user_info.properties_data,
            "activity_data": user_info.activity_data
        }
        
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


# === ROUTES ACTIONS ADMIN ===

@admin_router.post("/users/{user_id}/actions")
def perform_user_action(
    user_id: int,
    action_data: dict,
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Effectue une action administrative sur un utilisateur
    """
    if not admin_user.has_permission("manage_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission manage_users requise"
        )
    
    try:
        from enums import AccountAction
        
        action = AccountAction(action_data.get("action"))
        reason = action_data.get("reason")
        duration_days = action_data.get("duration_days")
        
        success = AdminService.perform_user_action(
            db=db,
            admin_user_id=admin_user.user_id,
            target_user_id=user_id,
            action=action,
            reason=reason,
            duration_days=duration_days
        )
        
        if success:
            return {
                "success": True,
                "message": f"Action {action} effectuée avec succès",
                "user_id": user_id,
                "action": action,
                "executed_at": datetime.utcnow()
            }
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


# === ROUTES D'INFORMATION ===

@admin_router.get("/system/info")
def get_system_info(
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Informations système pour les administrateurs
    """
    try:
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
                "permissions": admin_user.permissions_summary,
                "is_super_admin": admin_user.admin_role == "super_admin",
                "last_login": admin_user.last_login_at
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des informations système: {str(e)}"
        )


# === ROUTES DE RECHERCHE ===

@admin_router.get("/search")
def admin_search(
    query: str = Query(min_length=2, max_length=255),
    entity_types: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Recherche globale dans le système administrateur
    """
    try:
        import time
        
        start_time = time.time()
        results = []
        
        # Recherche dans les utilisateurs
        if not entity_types or "users" in entity_types:
            users = db.query(UserAuth).filter(
                UserAuth.email.ilike(f"%{query}%") |
                UserAuth.first_name.ilike(f"%{query}%") |
                UserAuth.last_name.ilike(f"%{query}%")
            ).limit(limit // 2).all()
            
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
        
        return {
            "query": query,
            "results": results[:limit],
            "total_found": len(results),
            "search_time_ms": search_time
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )