"""
Routes API pour l'audit avancé et le système d'undo
Timeline des actions utilisateur avec capacités d'annulation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import UserAuth
from models_admin import AdminUser
from services.enhanced_audit_service import EnhancedAuditService
from services.undo_service import UndoService
from services.user_notification_service import UserNotificationService
from error_handlers import PermissionErrorHandler
from audit_logger import AuditLogger
from enums import ActionType, EntityType, AdminRole


# Router pour l'audit et undo
audit_undo_router = APIRouter(prefix="/audit", tags=["Audit & Undo"])


def get_admin_user(current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)) -> AdminUser:
    """Récupère l'utilisateur admin actuel"""
    admin_user = db.query(AdminUser).filter(
        AdminUser.user_id == current_user.id,
        AdminUser.is_active == True
    ).first()
    
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis"
        )
    
    return admin_user


# === ROUTES TIMELINE AUDIT ===

@audit_undo_router.get("/users/{user_id}/timeline")
def get_user_audit_timeline(
    user_id: int,
    days: int = Query(7, ge=1, le=30),
    include_non_undoable: bool = Query(True),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère la timeline d'audit d'un utilisateur avec actions groupées
    """
    # Vérifier permissions
    if not admin_user.has_permission("manage_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission manage_users requise"
        )
    
    try:
        # Vérifier que l'utilisateur existe
        target_user = db.query(UserAuth).filter(UserAuth.id == user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Récupérer la timeline
        timeline = EnhancedAuditService.get_user_audit_timeline(
            db=db,
            user_id=user_id,
            days=days,
            include_non_undoable=include_non_undoable,
            admin_role=admin_user.admin_role
        )
        
        return {
            "user_id": user_id,
            "user_info": {
                "email": target_user.email,
                "name": f"{target_user.first_name} {target_user.last_name}",
            },
            "timeline_period_days": days,
            "total_action_groups": len(timeline),
            "timeline": timeline,
            "admin_permissions": {
                "can_undo_simple": admin_user.admin_role in [AdminRole.SUPER_ADMIN, AdminRole.USER_MANAGER, AdminRole.SUPPORT],
                "can_undo_moderate": admin_user.admin_role in [AdminRole.SUPER_ADMIN, AdminRole.SUPPORT],
                "can_undo_complex": admin_user.admin_role == AdminRole.SUPER_ADMIN
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement de la timeline: {str(e)}"
        )


@audit_undo_router.get("/actions/{audit_log_id}/requirements")
def get_undo_requirements(
    audit_log_id: int,
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Analyse les pré-requis pour effectuer un undo
    """
    try:
        requirements = EnhancedAuditService.get_undo_requirements(db, audit_log_id)
        return requirements
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'analyse des pré-requis: {str(e)}"
        )


@audit_undo_router.get("/actions/{audit_log_id}/preview")
def get_undo_preview(
    audit_log_id: int,
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Génère un aperçu de ce qui sera fait lors de l'undo
    """
    try:
        preview = UndoService.get_undo_preview(db, audit_log_id)
        
        if "error" in preview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=preview["error"]
            )
        
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération de l'aperçu: {str(e)}"
        )


# === ROUTES UNDO ===

@audit_undo_router.post("/actions/{audit_log_id}/undo")
def perform_undo_action(
    audit_log_id: int,
    undo_data: Dict[str, Any] = Body(...),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Effectue un undo sur une action d'audit
    """
    try:
        reason = undo_data.get("reason", "")
        confirm_complex = undo_data.get("confirm_complex", False)
        
        # Vérification supplémentaire pour actions complexes
        from models_audit_enhanced import AuditLogEnhanced, UndoComplexity
        audit_log = db.query(AuditLogEnhanced).filter(
            AuditLogEnhanced.id == audit_log_id
        ).first()
        
        if not audit_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action d'audit non trouvée"
            )
        
        if audit_log.undo_complexity == UndoComplexity.COMPLEX and not confirm_complex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation requise pour les actions complexes (confirm_complex=true)"
            )
        
        # Effectuer l'undo
        success, message, undo_action = UndoService.perform_undo(
            db=db,
            audit_log_id=audit_log_id,
            admin_user_id=admin_user.id,
            reason=reason
        )
        
        response = {
            "success": success,
            "message": message,
            "audit_log_id": audit_log_id,
            "undo_action_id": undo_action.id if undo_action else None,
            "performed_at": datetime.utcnow(),
            "performed_by": {
                "admin_id": admin_user.id,
                "admin_name": f"{admin_user.user.first_name} {admin_user.user.last_name}" if admin_user.user else "Unknown",
                "admin_role": admin_user.admin_role
            }
        }
        
        if success:
            # Logger cette action admin
            AuditLogger.log_action(
                db=db,
                user_id=admin_user.user_id,
                action=ActionType.UPDATE,
                entity_type=EntityType.USER,
                description=f"Undo effectué sur action {audit_log_id}: {audit_log.description}",
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'undo: {str(e)}"
        )


@audit_undo_router.get("/undo-history/{user_id}")
def get_user_undo_history(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique des undo effectués sur un utilisateur
    """
    try:
        from models_audit_enhanced import UndoAction, AuditLogEnhanced
        
        # Vérifier que l'utilisateur existe
        target_user = db.query(UserAuth).filter(UserAuth.id == user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Récupérer l'historique des undo
        undo_query = db.query(UndoAction).join(AuditLogEnhanced).filter(
            AuditLogEnhanced.user_id == user_id
        ).order_by(UndoAction.created_at.desc())
        
        total_count = undo_query.count()
        undo_actions = undo_query.offset(offset).limit(limit).all()
        
        undo_history = []
        for undo in undo_actions:
            undo_history.append({
                "id": undo.id,
                "audit_log_id": undo.audit_log_id,
                "status": undo.status,
                "reason": undo.undo_reason,
                "performed_at": undo.created_at,
                "completed_at": undo.completed_at,
                "performed_by": {
                    "admin_name": f"{undo.performed_by_admin.user.first_name} {undo.performed_by_admin.user.last_name}" if undo.performed_by_admin and undo.performed_by_admin.user else "Unknown",
                    "admin_role": undo.performed_by_admin.admin_role if undo.performed_by_admin else None
                },
                "original_action": {
                    "action": undo.audit_log.action,
                    "entity_type": undo.audit_log.entity_type,
                    "description": undo.audit_log.description,
                    "created_at": undo.audit_log.created_at
                },
                "execution_log": undo.execution_log,
                "error_message": undo.error_message
            })
        
        return {
            "user_id": user_id,
            "user_info": {
                "email": target_user.email,
                "name": f"{target_user.first_name} {target_user.last_name}"
            },
            "undo_history": undo_history,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement de l'historique: {str(e)}"
        )


# === ROUTES NOTIFICATIONS UTILISATEUR ===

@audit_undo_router.get("/notifications")
def get_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les notifications de l'utilisateur connecté
    """
    try:
        notifications_data = UserNotificationService.get_user_notifications(
            db=db,
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )
        
        return notifications_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des notifications: {str(e)}"
        )


@audit_undo_router.get("/notifications/summary")
def get_notifications_summary(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère le résumé des notifications pour la cloche
    """
    try:
        summary = UserNotificationService.get_notification_summary(db, current_user.id)
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement du résumé: {str(e)}"
        )


@audit_undo_router.post("/notifications/mark-read")
def mark_notifications_read(
    notification_data: Dict[str, Any] = Body(...),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marque des notifications comme lues
    """
    try:
        notification_ids = notification_data.get("notification_ids", [])
        mark_all = notification_data.get("mark_all", False)
        
        count = UserNotificationService.mark_as_read(
            db=db,
            user_id=current_user.id,
            notification_ids=notification_ids if notification_ids else None,
            mark_all=mark_all
        )
        
        return {
            "success": True,
            "marked_count": count,
            "message": f"{count} notification(s) marquée(s) comme lue(s)"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )


@audit_undo_router.post("/notifications/archive")
def archive_notifications(
    archive_data: Dict[str, Any] = Body(...),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Archive des notifications
    """
    try:
        notification_ids = archive_data.get("notification_ids", [])
        archive_read = archive_data.get("archive_read", False)
        older_than_days = archive_data.get("older_than_days")
        
        count = UserNotificationService.archive_notifications(
            db=db,
            user_id=current_user.id,
            notification_ids=notification_ids if notification_ids else None,
            archive_read=archive_read,
            older_than_days=older_than_days
        )
        
        return {
            "success": True,
            "archived_count": count,
            "message": f"{count} notification(s) archivée(s)"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'archivage: {str(e)}"
        )


# === ROUTES STATISTIQUES AUDIT ===

@audit_undo_router.get("/stats/global")
def get_audit_global_stats(
    days: int = Query(30, ge=1, le=365),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Statistiques globales d'audit pour les admins
    """
    if not admin_user.has_permission("access_audit_logs"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission access_audit_logs requise"
        )
    
    try:
        from models_audit_enhanced import AuditLogEnhanced, UndoAction
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Statistiques des actions
        total_actions = db.query(func.count(AuditLogEnhanced.id)).filter(
            AuditLogEnhanced.created_at >= since_date
        ).scalar()
        
        undoable_actions = db.query(func.count(AuditLogEnhanced.id)).filter(
            AuditLogEnhanced.created_at >= since_date,
            AuditLogEnhanced.is_undoable == True
        ).scalar()
        
        # Statistiques des undo
        total_undos = db.query(func.count(UndoAction.id)).filter(
            UndoAction.created_at >= since_date
        ).scalar()
        
        successful_undos = db.query(func.count(UndoAction.id)).filter(
            UndoAction.created_at >= since_date,
            UndoAction.status == "completed"
        ).scalar()
        
        # Actions par type
        action_types = db.query(
            AuditLogEnhanced.action,
            func.count(AuditLogEnhanced.id).label('count')
        ).filter(
            AuditLogEnhanced.created_at >= since_date
        ).group_by(AuditLogEnhanced.action).all()
        
        action_breakdown = {action.action: action.count for action in action_types}
        
        return {
            "period_days": days,
            "total_actions": total_actions,
            "undoable_actions": undoable_actions,
            "non_undoable_actions": total_actions - undoable_actions,
            "total_undos": total_undos,
            "successful_undos": successful_undos,
            "failed_undos": total_undos - successful_undos,
            "undo_success_rate": (successful_undos / total_undos * 100) if total_undos > 0 else 0,
            "action_breakdown": action_breakdown,
            "undoable_percentage": (undoable_actions / total_actions * 100) if total_actions > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des statistiques: {str(e)}"
        )


@audit_undo_router.get("/search")
def search_audit_logs(
    query: str = Query(..., min_length=2),
    days: int = Query(7, ge=1, le=90),
    entity_type: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Recherche dans les logs d'audit
    """
    if not admin_user.has_permission("access_audit_logs"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission access_audit_logs requise"
        )
    
    try:
        from models_audit_enhanced import AuditLogEnhanced
        from datetime import datetime, timedelta
        from sqlalchemy import or_, and_
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Construction de la requête
        search_query = db.query(AuditLogEnhanced).filter(
            AuditLogEnhanced.created_at >= since_date
        )
        
        # Recherche textuelle
        search_query = search_query.filter(
            or_(
                AuditLogEnhanced.description.ilike(f"%{query}%"),
                AuditLogEnhanced.user_action_context.ilike(f"%{query}%")
            )
        )
        
        # Filtres optionnels
        if entity_type:
            search_query = search_query.filter(AuditLogEnhanced.entity_type == entity_type)
        
        if action_type:
            search_query = search_query.filter(AuditLogEnhanced.action == action_type)
        
        if user_id:
            search_query = search_query.filter(AuditLogEnhanced.user_id == user_id)
        
        # Exécuter et formater
        results = search_query.order_by(
            AuditLogEnhanced.created_at.desc()
        ).limit(limit).all()
        
        search_results = []
        for log in results:
            search_results.append({
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "description": log.description,
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else None,
                "created_at": log.created_at,
                "is_undoable": log.is_undoable,
                "undo_complexity": log.undo_complexity,
                "transaction_group_id": log.transaction_group_id
            })
        
        return {
            "query": query,
            "results": search_results,
            "total_found": len(search_results),
            "filters": {
                "days": days,
                "entity_type": entity_type,
                "action_type": action_type,
                "user_id": user_id
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )