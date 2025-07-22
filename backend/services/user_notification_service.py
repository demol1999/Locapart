"""
Service de notifications utilisateur
Système de cloche et notifications pour informer les utilisateurs
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from models_audit_enhanced import UserNotification, NotificationType
from models import UserAuth
from enums import EntityType


class UserNotificationService:
    """
    Service de gestion des notifications utilisateur
    """
    
    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: str = "normal",
        category: str = None,
        action_url: str = None,
        metadata: Dict[str, Any] = None,
        expires_in_days: int = 30
    ) -> UserNotification:
        """
        Crée une nouvelle notification pour un utilisateur
        """
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        
        notification = UserNotification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            category=category,
            action_url=action_url,
            notification_metadata=metadata,
            expires_at=expires_at
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Récupère les notifications d'un utilisateur
        """
        query = db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_archived == False
        )
        
        # Filtrer les notifications expirées
        query = query.filter(
            or_(
                UserNotification.expires_at.is_(None),
                UserNotification.expires_at > datetime.utcnow()
            )
        )
        
        if unread_only:
            query = query.filter(UserNotification.is_read == False)
        
        # Compter le total
        total_count = query.count()
        
        # Récupérer avec pagination
        notifications = query.order_by(
            desc(UserNotification.created_at)
        ).offset(offset).limit(limit).all()
        
        # Compter les non lues
        unread_count = db.query(func.count(UserNotification.id)).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_read == False,
            UserNotification.is_archived == False,
            or_(
                UserNotification.expires_at.is_(None),
                UserNotification.expires_at > datetime.utcnow()
            )
        ).scalar()
        
        # Formatter les notifications
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                "id": notif.id,
                "type": notif.notification_type,
                "title": notif.title,
                "message": notif.message,
                "priority": notif.priority,
                "category": notif.category,
                "action_url": notif.action_url,
                "is_read": notif.is_read,
                "is_urgent": notif.is_urgent,
                "created_at": notif.created_at,
                "read_at": notif.read_at,
                "metadata": notif.notification_metadata
            })
        
        return {
            "notifications": notifications_data,
            "total_count": total_count,
            "unread_count": unread_count,
            "has_more": (offset + limit) < total_count
        }
    
    @staticmethod
    def mark_as_read(
        db: Session,
        user_id: int,
        notification_ids: List[int] = None,
        mark_all: bool = False
    ) -> int:
        """
        Marque des notifications comme lues
        Retourne le nombre de notifications mises à jour
        """
        query = db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_read == False
        )
        
        if mark_all:
            # Marquer toutes comme lues
            count = query.count()
            query.update({
                UserNotification.is_read: True,
                UserNotification.read_at: datetime.utcnow()
            })
        elif notification_ids:
            # Marquer seulement les IDs spécifiés
            query = query.filter(UserNotification.id.in_(notification_ids))
            count = query.count()
            query.update({
                UserNotification.is_read: True,
                UserNotification.read_at: datetime.utcnow()
            })
        else:
            count = 0
        
        db.commit()
        return count
    
    @staticmethod
    def archive_notifications(
        db: Session,
        user_id: int,
        notification_ids: List[int] = None,
        archive_read: bool = False,
        older_than_days: int = None
    ) -> int:
        """
        Archive des notifications
        """
        query = db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_archived == False
        )
        
        if notification_ids:
            query = query.filter(UserNotification.id.in_(notification_ids))
        
        if archive_read:
            query = query.filter(UserNotification.is_read == True)
        
        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            query = query.filter(UserNotification.created_at < cutoff_date)
        
        count = query.count()
        query.update({
            UserNotification.is_archived: True,
            UserNotification.archived_at: datetime.utcnow()
        })
        
        db.commit()
        return count
    
    @staticmethod
    def get_notification_summary(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère un résumé des notifications pour l'utilisateur (pour la cloche)
        """
        # Compter par type et priorité
        summary_query = db.query(
            UserNotification.notification_type,
            UserNotification.priority,
            func.count(UserNotification.id).label('count')
        ).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_read == False,
            UserNotification.is_archived == False,
            or_(
                UserNotification.expires_at.is_(None),
                UserNotification.expires_at > datetime.utcnow()
            )
        ).group_by(
            UserNotification.notification_type,
            UserNotification.priority
        ).all()
        
        # Total non lues
        total_unread = sum(item.count for item in summary_query)
        
        # Compter les urgentes
        urgent_count = sum(
            item.count for item in summary_query 
            if item.priority in ["high", "urgent"]
        )
        
        # Compter par type
        type_counts = {}
        for item in summary_query:
            type_counts[item.notification_type] = type_counts.get(item.notification_type, 0) + item.count
        
        # Dernières notifications non lues
        recent_notifications = db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_read == False,
            UserNotification.is_archived == False
        ).order_by(
            desc(UserNotification.created_at)
        ).limit(3).all()
        
        recent_data = []
        for notif in recent_notifications:
            recent_data.append({
                "id": notif.id,
                "title": notif.title,
                "type": notif.notification_type,
                "priority": notif.priority,
                "created_at": notif.created_at,
                "is_urgent": notif.is_urgent
            })
        
        return {
            "total_unread": total_unread,
            "urgent_count": urgent_count,
            "type_counts": type_counts,
            "recent_notifications": recent_data,
            "has_notifications": total_unread > 0,
            "bell_color": "red" if urgent_count > 0 else "orange" if total_unread > 0 else "gray"
        }
    
    @staticmethod
    def create_admin_action_notification(
        db: Session,
        user_id: int,
        admin_name: str,
        action_description: str,
        action_type: str = "modification",
        reason: str = None
    ) -> UserNotification:
        """
        Crée une notification pour une action administrative
        """
        title = f"Action administrative: {action_type}"
        
        message = f"Un administrateur ({admin_name}) a effectué une action sur votre compte:\n\n"
        message += action_description
        
        if reason:
            message += f"\n\nRaison: {reason}"
        
        return UserNotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.ADMIN_ACTION,
            title=title,
            message=message,
            priority="high",
            category="admin_action",
            metadata={
                "admin_name": admin_name,
                "action_type": action_type,
                "reason": reason
            }
        )
    
    @staticmethod
    def cleanup_expired_notifications(db: Session) -> int:
        """
        Nettoie les notifications expirées
        """
        expired_count = db.query(UserNotification).filter(
            UserNotification.expires_at < datetime.utcnow()
        ).count()
        
        db.query(UserNotification).filter(
            UserNotification.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        return expired_count
    
    @staticmethod
    def get_user_notification_preferences(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère les préférences de notification d'un utilisateur
        (Pour future implémentation du système de paramétrage)
        """
        # Pour l'instant, retourner des préférences par défaut
        # TODO: Créer une table user_notification_preferences
        
        return {
            "email_notifications": True,
            "admin_actions": True,
            "undo_performed": True,
            "system_alerts": True,
            "account_updates": True,
            "frequency": "immediate",  # immediate, daily, weekly
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00"
            }
        }
    
    @staticmethod
    def create_bulk_notification(
        db: Session,
        user_ids: List[int],
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: str = "normal",
        category: str = None,
        metadata: Dict[str, Any] = None
    ) -> int:
        """
        Crée une notification en masse pour plusieurs utilisateurs
        """
        notifications = []
        
        for user_id in user_ids:
            notification = UserNotification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                category=category,
                notification_metadata=metadata,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            notifications.append(notification)
        
        db.add_all(notifications)
        db.commit()
        
        return len(notifications)
    
    @staticmethod
    def get_notification_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Statistiques des notifications pour un utilisateur
        """
        total_notifications = db.query(func.count(UserNotification.id)).filter(
            UserNotification.user_id == user_id
        ).scalar()
        
        read_notifications = db.query(func.count(UserNotification.id)).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_read == True
        ).scalar()
        
        archived_notifications = db.query(func.count(UserNotification.id)).filter(
            UserNotification.user_id == user_id,
            UserNotification.is_archived == True
        ).scalar()
        
        # Notifications par type
        type_stats = db.query(
            UserNotification.notification_type,
            func.count(UserNotification.id).label('count')
        ).filter(
            UserNotification.user_id == user_id
        ).group_by(UserNotification.notification_type).all()
        
        type_breakdown = {item.notification_type: item.count for item in type_stats}
        
        return {
            "total_notifications": total_notifications,
            "read_notifications": read_notifications,
            "unread_notifications": total_notifications - read_notifications,
            "archived_notifications": archived_notifications,
            "read_rate": (read_notifications / total_notifications * 100) if total_notifications > 0 else 0,
            "type_breakdown": type_breakdown
        }