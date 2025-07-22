"""
Routes avancées pour la gestion des notifications
Configuration utilisateur, file d'attente et notifications intelligentes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from database import get_db
from auth import get_current_user
from models import UserAuth
from models_admin import AdminUser
from models_notification_extended import (
    UserNotificationPreferences, NotificationQueue, NotificationTemplate,
    NotificationRule, NotificationDigest, NotificationAnalytics,
    NotificationChannel, NotificationCategory, NotificationPriority,
    QueueStatus, NotificationTrigger
)
from services.notification_engine import NotificationEngine, SmartNotificationService, NotificationScheduler
from error_handlers import BusinessLogicErrorHandler


# Router pour les notifications avancées
notifications_router = APIRouter(prefix="/notifications", tags=["Notifications Avancées"])


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


# === ROUTES CONFIGURATION UTILISATEUR ===

@notifications_router.get("/preferences")
def get_user_notification_preferences(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les préférences de notification de l'utilisateur
    """
    try:
        prefs = NotificationEngine.get_user_preferences(db, current_user.id)
        
        return {
            "user_id": current_user.id,
            "global_settings": {
                "notifications_enabled": prefs.notifications_enabled,
                "email_notifications": prefs.email_notifications,
                "sms_notifications": prefs.sms_notifications,
                "push_notifications": prefs.push_notifications,
                "digest_frequency": prefs.digest_frequency,
                "timezone": prefs.timezone,
                "language": prefs.language
            },
            "quiet_hours": {
                "enabled": prefs.quiet_hours_enabled,
                "start": prefs.quiet_hours_start,
                "end": prefs.quiet_hours_end
            },
            "contact_info": {
                "email_address": prefs.email_address,
                "phone_number": prefs.phone_number
            },
            "category_channels": {
                "admin_action": prefs.admin_action_channels,
                "rent_payment": prefs.rent_payment_channels,
                "lease_events": prefs.lease_events_channels,
                "property_updates": prefs.property_updates_channels,
                "maintenance": prefs.maintenance_channels,
                "financial": prefs.financial_channels,
                "legal": prefs.legal_channels,
                "system": prefs.system_channels,
                "marketing": prefs.marketing_channels
            },
            "category_preferences": prefs.category_preferences or {}
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des préférences: {str(e)}"
        )


@notifications_router.put("/preferences")
def update_user_notification_preferences(
    preferences_data: Dict[str, Any] = Body(...),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour les préférences de notification de l'utilisateur
    """
    try:
        prefs = NotificationEngine.get_user_preferences(db, current_user.id)
        
        # Mise à jour des paramètres globaux
        global_settings = preferences_data.get("global_settings", {})
        for key, value in global_settings.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        
        # Mise à jour des heures silencieuses
        quiet_hours = preferences_data.get("quiet_hours", {})
        if quiet_hours:
            prefs.quiet_hours_enabled = quiet_hours.get("enabled", prefs.quiet_hours_enabled)
            prefs.quiet_hours_start = quiet_hours.get("start", prefs.quiet_hours_start)
            prefs.quiet_hours_end = quiet_hours.get("end", prefs.quiet_hours_end)
        
        # Mise à jour des infos de contact
        contact_info = preferences_data.get("contact_info", {})
        if contact_info:
            prefs.email_address = contact_info.get("email_address", prefs.email_address)
            prefs.phone_number = contact_info.get("phone_number", prefs.phone_number)
        
        # Mise à jour des canaux par catégorie
        category_channels = preferences_data.get("category_channels", {})
        for category, channels in category_channels.items():
            channel_attr = f"{category}_channels"
            if hasattr(prefs, channel_attr):
                setattr(prefs, channel_attr, channels)
        
        # Mise à jour des préférences par catégorie
        category_preferences = preferences_data.get("category_preferences", {})
        if category_preferences:
            prefs.category_preferences = category_preferences
        
        db.commit()
        
        return {
            "success": True,
            "message": "Préférences mises à jour avec succès",
            "updated_at": datetime.utcnow()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )


@notifications_router.post("/test")
def send_test_notification(
    test_data: Dict[str, Any] = Body(...),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Envoie une notification de test à l'utilisateur
    """
    try:
        category = NotificationCategory(test_data.get("category", "system"))
        channels = [NotificationChannel(ch) for ch in test_data.get("channels", ["in_app"])]
        
        NotificationEngine.queue_notification(
            db=db,
            user_id=current_user.id,
            category=category,
            subject="🧪 Notification de test",
            message=f"Ceci est une notification de test envoyée le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')}.",
            channels=channels,
            priority=NotificationPriority.LOW,
            notification_data={
                "test": True,
                "sent_at": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "success": True,
            "message": "Notification de test envoyée",
            "category": category.value,
            "channels": [ch.value for ch in channels]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi du test: {str(e)}"
        )


# === ROUTES FILE D'ATTENTE ===

@notifications_router.get("/queue/status")
def get_queue_status(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Statut de la file d'attente de notifications pour l'utilisateur
    """
    try:
        # Statistiques de la queue pour cet utilisateur
        queue_stats = db.query(NotificationQueue).filter(
            NotificationQueue.user_id == current_user.id
        ).all()
        
        stats = {
            "total": len(queue_stats),
            "pending": 0,
            "processing": 0,
            "sent": 0,
            "failed": 0,
            "by_channel": {},
            "by_category": {}
        }
        
        for notif in queue_stats:
            # Par statut
            stats[notif.status.value] = stats.get(notif.status.value, 0) + 1
            
            # Par canal
            channel = notif.channel.value
            stats["by_channel"][channel] = stats["by_channel"].get(channel, 0) + 1
            
            # Par catégorie
            category = notif.category.value
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        # Prochaines notifications programmées
        upcoming = db.query(NotificationQueue).filter(
            NotificationQueue.user_id == current_user.id,
            NotificationQueue.status == QueueStatus.PENDING,
            NotificationQueue.scheduled_at > datetime.utcnow()
        ).order_by(NotificationQueue.scheduled_at).limit(5).all()
        
        upcoming_list = []
        for notif in upcoming:
            upcoming_list.append({
                "id": notif.id,
                "subject": notif.subject,
                "category": notif.category.value,
                "channel": notif.channel.value,
                "scheduled_at": notif.scheduled_at
            })
        
        return {
            "user_id": current_user.id,
            "queue_stats": stats,
            "upcoming_notifications": upcoming_list
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement du statut: {str(e)}"
        )


@notifications_router.get("/history")
def get_notification_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Historique des notifications envoyées à l'utilisateur
    """
    try:
        query = db.query(NotificationQueue).filter(
            NotificationQueue.user_id == current_user.id
        )
        
        # Filtres
        if category:
            query = query.filter(NotificationQueue.category == category)
        if channel:
            query = query.filter(NotificationQueue.channel == channel)
        if status:
            query = query.filter(NotificationQueue.status == status)
        
        # Compter le total
        total_count = query.count()
        
        # Récupérer avec pagination
        notifications = query.order_by(
            NotificationQueue.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        history = []
        for notif in notifications:
            history.append({
                "id": notif.id,
                "subject": notif.subject,
                "message": notif.message[:200] + "..." if len(notif.message) > 200 else notif.message,
                "category": notif.category.value,
                "channel": notif.channel.value,
                "priority": notif.priority.value,
                "status": notif.status.value,
                "created_at": notif.created_at,
                "scheduled_at": notif.scheduled_at,
                "processed_at": notif.processed_at,
                "attempts": notif.attempts,
                "error_message": notif.error_message
            })
        
        return {
            "history": history,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            },
            "filters": {
                "category": category,
                "channel": channel,
                "status": status
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement de l'historique: {str(e)}"
        )


# === ROUTES DIGESTS ===

@notifications_router.get("/digests")
def get_user_digests(
    limit: int = Query(10, ge=1, le=50),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les digests de l'utilisateur
    """
    try:
        digests = db.query(NotificationDigest).filter(
            NotificationDigest.user_id == current_user.id
        ).order_by(
            NotificationDigest.period_end.desc()
        ).limit(limit).all()
        
        digest_list = []
        for digest in digests:
            digest_list.append({
                "id": digest.id,
                "digest_type": digest.digest_type.value,
                "period_start": digest.period_start,
                "period_end": digest.period_end,
                "total_notifications": digest.total_notifications,
                "categories_summary": digest.categories_summary,
                "digest_content": digest.digest_content,
                "is_sent": digest.is_sent,
                "sent_at": digest.sent_at,
                "created_at": digest.created_at
            })
        
        return {
            "digests": digest_list,
            "total_count": len(digest_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des digests: {str(e)}"
        )


@notifications_router.post("/digests/generate")
def generate_custom_digest(
    digest_data: Dict[str, Any] = Body(...),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Génère un digest personnalisé pour une période donnée
    """
    try:
        period_start = datetime.fromisoformat(digest_data["period_start"])
        period_end = datetime.fromisoformat(digest_data["period_end"])
        digest_type = NotificationTrigger(digest_data.get("digest_type", "custom_schedule"))
        
        digest = NotificationEngine.create_digest(
            db=db,
            user_id=current_user.id,
            digest_type=digest_type,
            period_start=period_start,
            period_end=period_end
        )
        
        if not digest:
            return {
                "success": False,
                "message": "Aucune notification trouvée pour cette période"
            }
        
        return {
            "success": True,
            "digest": {
                "id": digest.id,
                "digest_type": digest.digest_type.value,
                "period_start": digest.period_start,
                "period_end": digest.period_end,
                "total_notifications": digest.total_notifications,
                "categories_summary": digest.categories_summary,
                "digest_content": digest.digest_content
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération du digest: {str(e)}"
        )


# === ROUTES ADMINISTRATEUR ===

@notifications_router.get("/admin/queue/global")
def get_global_queue_status(
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Statut global de la file d'attente (admin seulement)
    """
    try:
        # Statistiques globales
        total_queue = db.query(NotificationQueue).count()
        
        stats_by_status = db.query(
            NotificationQueue.status,
            db.func.count(NotificationQueue.id).label('count')
        ).group_by(NotificationQueue.status).all()
        
        stats_by_channel = db.query(
            NotificationQueue.channel,
            db.func.count(NotificationQueue.id).label('count')
        ).group_by(NotificationQueue.channel).all()
        
        stats_by_priority = db.query(
            NotificationQueue.priority,
            db.func.count(NotificationQueue.id).label('count')
        ).group_by(NotificationQueue.priority).all()
        
        # Notifications en échec
        failed_notifications = db.query(NotificationQueue).filter(
            NotificationQueue.status == QueueStatus.FAILED
        ).order_by(NotificationQueue.created_at.desc()).limit(10).all()
        
        failed_list = []
        for notif in failed_notifications:
            failed_list.append({
                "id": notif.id,
                "user_id": notif.user_id,
                "subject": notif.subject,
                "channel": notif.channel.value,
                "attempts": notif.attempts,
                "error_message": notif.error_message,
                "created_at": notif.created_at
            })
        
        return {
            "global_stats": {
                "total_queue": total_queue,
                "by_status": {item.status.value: item.count for item in stats_by_status},
                "by_channel": {item.channel.value: item.count for item in stats_by_channel},
                "by_priority": {item.priority.value: item.count for item in stats_by_priority}
            },
            "failed_notifications": failed_list,
            "queue_health": {
                "pending_count": sum(1 for item in stats_by_status if item.status == QueueStatus.PENDING),
                "failed_count": sum(1 for item in stats_by_status if item.status == QueueStatus.FAILED),
                "success_rate": 0  # À calculer
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des statistiques: {str(e)}"
        )


@notifications_router.post("/admin/queue/process")
def process_notification_queue(
    batch_size: int = Body(50, embed=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Traite manuellement la file d'attente (admin seulement)
    """
    try:
        # Traitement en arrière-plan
        def process_queue_task():
            stats = NotificationEngine.process_queue(db, batch_size)
            print(f"📊 Queue traitée par admin {admin_user.user.email}: {stats}")
        
        background_tasks.add_task(process_queue_task)
        
        return {
            "success": True,
            "message": f"Traitement de la queue lancé (batch: {batch_size})",
            "processed_by": admin_user.user.email if admin_user.user else "Admin"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement: {str(e)}"
        )


@notifications_router.post("/admin/tasks/daily")
def run_daily_tasks(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Lance manuellement les tâches quotidiennes (admin seulement)
    """
    try:
        def run_tasks():
            results = NotificationScheduler.run_daily_tasks(db)
            print(f"📅 Tâches quotidiennes lancées par {admin_user.user.email}: {results}")
        
        background_tasks.add_task(run_tasks)
        
        return {
            "success": True,
            "message": "Tâches quotidiennes lancées en arrière-plan",
            "launched_by": admin_user.user.email if admin_user.user else "Admin",
            "launched_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du lancement des tâches: {str(e)}"
        )


# === ROUTES NOTIFICATIONS INTELLIGENTES ===

@notifications_router.post("/smart/welcome")
def send_welcome_notification(
    user_id: int = Body(..., embed=True),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Envoie une notification de bienvenue à un utilisateur
    """
    try:
        SmartNotificationService.send_welcome_notification(db, user_id)
        
        return {
            "success": True,
            "message": f"Notification de bienvenue envoyée à l'utilisateur {user_id}",
            "sent_by": admin_user.user.email if admin_user.user else "Admin"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi: {str(e)}"
        )


@notifications_router.post("/smart/quota-warning")
def send_quota_warning(
    quota_data: Dict[str, Any] = Body(...),
    admin_user: AdminUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Envoie un avertissement de quota à un utilisateur
    """
    try:
        user_id = quota_data["user_id"]
        current_count = quota_data["current_count"]
        limit = quota_data["limit"]
        
        SmartNotificationService.send_quota_warning(db, user_id, current_count, limit)
        
        return {
            "success": True,
            "message": f"Avertissement de quota envoyé à l'utilisateur {user_id}",
            "quota_info": {
                "current": current_count,
                "limit": limit,
                "percentage": (current_count / limit) * 100
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi: {str(e)}"
        )


@notifications_router.get("/analytics")
def get_notification_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analytiques des notifications pour l'utilisateur
    """
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Notifications envoyées par jour
        daily_stats = db.query(
            db.func.date(NotificationQueue.created_at).label('date'),
            db.func.count(NotificationQueue.id).label('count')
        ).filter(
            NotificationQueue.user_id == current_user.id,
            NotificationQueue.created_at >= since_date
        ).group_by(
            db.func.date(NotificationQueue.created_at)
        ).order_by('date').all()
        
        # Par catégorie
        category_stats = db.query(
            NotificationQueue.category,
            db.func.count(NotificationQueue.id).label('count')
        ).filter(
            NotificationQueue.user_id == current_user.id,
            NotificationQueue.created_at >= since_date
        ).group_by(NotificationQueue.category).all()
        
        # Par canal
        channel_stats = db.query(
            NotificationQueue.channel,
            db.func.count(NotificationQueue.id).label('count')
        ).filter(
            NotificationQueue.user_id == current_user.id,
            NotificationQueue.created_at >= since_date
        ).group_by(NotificationQueue.channel).all()
        
        # Taux de succès
        total_sent = db.query(NotificationQueue).filter(
            NotificationQueue.user_id == current_user.id,
            NotificationQueue.created_at >= since_date
        ).count()
        
        successful_sent = db.query(NotificationQueue).filter(
            NotificationQueue.user_id == current_user.id,
            NotificationQueue.created_at >= since_date,
            NotificationQueue.status == QueueStatus.SENT
        ).count()
        
        success_rate = (successful_sent / total_sent * 100) if total_sent > 0 else 0
        
        return {
            "period_days": days,
            "total_notifications": total_sent,
            "successful_notifications": successful_sent,
            "success_rate": round(success_rate, 2),
            "daily_stats": [
                {"date": item.date.isoformat(), "count": item.count}
                for item in daily_stats
            ],
            "category_breakdown": {
                item.category.value: item.count for item in category_stats
            },
            "channel_breakdown": {
                item.channel.value: item.count for item in channel_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du chargement des analytiques: {str(e)}"
        )