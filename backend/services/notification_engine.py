"""
Moteur de notifications intelligent
Gestion complète de la file d'attente et notifications automatiques
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json
import asyncio
import re
from pathlib import Path

from models_notification_extended import (
    NotificationQueue, NotificationTemplate, NotificationRule, NotificationDigest,
    UserNotificationPreferences, SmartNotificationTrigger, NotificationAnalytics,
    NotificationChannel, NotificationCategory, NotificationPriority, 
    QueueStatus, NotificationTrigger
)
from models import UserAuth, Lease, Payment
from services.user_notification_service import UserNotificationService
from error_handlers import BusinessLogicErrorHandler


class NotificationEngine:
    """
    Moteur principal de notifications avec file d'attente intelligente
    """
    
    @staticmethod
    def queue_notification(
        db: Session,
        user_id: int,
        category: NotificationCategory,
        subject: str,
        message: str,
        channels: List[NotificationChannel] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: datetime = None,
        template_name: str = None,
        notification_data: Dict[str, Any] = None,
        expires_in_hours: int = 72
    ) -> List[NotificationQueue]:
        """
        Ajoute une notification à la file d'attente pour tous les canaux spécifiés
        """
        # Récupérer les préférences utilisateur
        prefs = NotificationEngine.get_user_preferences(db, user_id)
        
        # Déterminer les canaux si pas spécifiés
        if not channels:
            channels = [NotificationChannel(ch) for ch in prefs.get_channels_for_category(category)]
        
        # Vérifier si la catégorie est activée
        if not prefs.is_category_enabled(category):
            return []
        
        # Filtrer les canaux selon les préférences
        enabled_channels = []
        for channel in channels:
            if channel == NotificationChannel.IN_APP and prefs.notifications_enabled:
                enabled_channels.append(channel)
            elif channel == NotificationChannel.EMAIL and prefs.email_notifications:
                enabled_channels.append(channel)
            elif channel == NotificationChannel.SMS and prefs.sms_notifications:
                enabled_channels.append(channel)
            elif channel == NotificationChannel.PUSH and prefs.push_notifications:
                enabled_channels.append(channel)
        
        # Créer les entrées dans la queue
        queued_notifications = []
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        for channel in enabled_channels:
            # Adapter le contenu selon le canal
            adapted_subject, adapted_message, html_message = NotificationEngine._adapt_content_for_channel(
                channel, subject, message, template_name, notification_data
            )
            
            queue_item = NotificationQueue(
                user_id=user_id,
                channel=channel,
                category=category,
                priority=priority,
                subject=adapted_subject,
                message=adapted_message,
                html_message=html_message,
                notification_data=notification_data,
                template_name=template_name,
                scheduled_at=scheduled_at or datetime.utcnow(),
                expires_at=expires_at
            )
            
            db.add(queue_item)
            queued_notifications.append(queue_item)
        
        db.commit()
        return queued_notifications
    
    @staticmethod
    def _adapt_content_for_channel(
        channel: NotificationChannel,
        subject: str,
        message: str,
        template_name: str = None,
        data: Dict[str, Any] = None
    ) -> tuple:
        """
        Adapte le contenu selon le canal de notification
        """
        adapted_subject = subject
        adapted_message = message
        html_message = None
        
        if channel == NotificationChannel.EMAIL:
            # Pour email, créer version HTML
            html_message = NotificationEngine._generate_html_email(subject, message, data)
            
        elif channel == NotificationChannel.SMS:
            # Pour SMS, raccourcir le message
            adapted_subject = subject[:50] + "..." if len(subject) > 50 else subject
            adapted_message = message[:140] + "..." if len(message) > 140 else message
            
        elif channel == NotificationChannel.IN_APP:
            # Pour in-app, pas de modification
            pass
        
        return adapted_subject, adapted_message, html_message
    
    @staticmethod
    def _generate_html_email(subject: str, message: str, data: Dict[str, Any] = None) -> str:
        """
        Génère un email HTML à partir du contenu texte
        """
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f8f9fa; }}
                .footer {{ padding: 10px; text-align: center; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏠 LocAppart</h1>
                </div>
                <div class="content">
                    <h2>{subject}</h2>
                    <p>{message.replace(chr(10), '<br>')}</p>
                    {NotificationEngine._generate_email_actions(data)}
                </div>
                <div class="footer">
                    <p>Cette notification a été envoyée automatiquement par LocAppart.<br>
                    Pour modifier vos préférences, <a href="#preferences">cliquez ici</a>.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_template
    
    @staticmethod
    def _generate_email_actions(data: Dict[str, Any] = None) -> str:
        """Génère des boutons d'action pour l'email"""
        if not data:
            return ""
        
        actions_html = ""
        if data.get("action_url"):
            actions_html += f'<p><a href="{data["action_url"]}" class="btn">Voir les détails</a></p>'
        
        if data.get("payment_url"):
            actions_html += f'<p><a href="{data["payment_url"]}" class="btn">Effectuer le paiement</a></p>'
        
        return actions_html
    
    @staticmethod
    def process_queue(db: Session, batch_size: int = 50) -> Dict[str, int]:
        """
        Traite la file d'attente de notifications
        """
        stats = {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Récupérer les notifications en attente
        pending_notifications = db.query(NotificationQueue).filter(
            NotificationQueue.status == QueueStatus.PENDING,
            NotificationQueue.scheduled_at <= datetime.utcnow(),
            or_(
                NotificationQueue.expires_at.is_(None),
                NotificationQueue.expires_at > datetime.utcnow()
            )
        ).order_by(
            NotificationQueue.priority.desc(),
            NotificationQueue.scheduled_at
        ).limit(batch_size).all()
        
        for notification in pending_notifications:
            stats["processed"] += 1
            
            try:
                # Marquer comme en cours de traitement
                notification.status = QueueStatus.PROCESSING
                notification.attempts += 1
                db.commit()
                
                # Envoyer selon le canal
                success = False
                if notification.channel == NotificationChannel.IN_APP:
                    success = NotificationEngine._send_in_app_notification(db, notification)
                elif notification.channel == NotificationChannel.EMAIL:
                    success = NotificationEngine._send_email_notification(db, notification)
                elif notification.channel == NotificationChannel.SMS:
                    success = NotificationEngine._send_sms_notification(db, notification)
                
                if success:
                    notification.status = QueueStatus.SENT
                    notification.processed_at = datetime.utcnow()
                    stats["sent"] += 1
                else:
                    if notification.can_retry:
                        notification.status = QueueStatus.RETRYING
                        notification.scheduled_at = datetime.utcnow() + timedelta(minutes=5 * notification.attempts)
                    else:
                        notification.status = QueueStatus.FAILED
                    stats["failed"] += 1
                
            except Exception as e:
                notification.status = QueueStatus.FAILED
                notification.error_message = str(e)
                stats["failed"] += 1
            
            db.commit()
        
        return stats
    
    @staticmethod
    def _send_in_app_notification(db: Session, queue_item: NotificationQueue) -> bool:
        """Envoie une notification in-app"""
        try:
            # Convertir category en NotificationType de l'ancien système
            from models_audit_enhanced import NotificationType
            
            type_mapping = {
                NotificationCategory.ADMIN_ACTION: NotificationType.ADMIN_ACTION,
                NotificationCategory.SYSTEM: NotificationType.SYSTEM_ALERT,
                NotificationCategory.FINANCIAL: NotificationType.ACCOUNT_UPDATE,
            }
            
            notification_type = type_mapping.get(
                queue_item.category, 
                NotificationType.SYSTEM_ALERT
            )
            
            # Créer la notification in-app
            UserNotificationService.create_notification(
                db=db,
                user_id=queue_item.user_id,
                notification_type=notification_type,
                title=queue_item.subject,
                message=queue_item.message,
                priority=queue_item.priority.value,
                category=queue_item.category.value,
                metadata=queue_item.notification_data
            )
            
            return True
            
        except Exception as e:
            queue_item.error_message = f"Erreur in-app: {str(e)}"
            return False
    
    @staticmethod
    def _send_email_notification(db: Session, queue_item: NotificationQueue) -> bool:
        """Envoie une notification par email"""
        try:
            # Récupérer l'utilisateur et ses préférences
            user = db.query(UserAuth).filter(UserAuth.id == queue_item.user_id).first()
            if not user:
                return False
            
            prefs = NotificationEngine.get_user_preferences(db, queue_item.user_id)
            email_to = prefs.email_address or user.email
            
            # TODO: Intégrer avec un service d'email (SendGrid, AWS SES, etc.)
            # Pour l'instant, simuler l'envoi
            print(f"📧 EMAIL ENVOYÉ À {email_to}")
            print(f"Sujet: {queue_item.subject}")
            print(f"Message: {queue_item.message[:100]}...")
            
            # Simuler un ID externe
            queue_item.external_id = f"email_{datetime.utcnow().timestamp()}"
            
            return True
            
        except Exception as e:
            queue_item.error_message = f"Erreur email: {str(e)}"
            return False
    
    @staticmethod
    def _send_sms_notification(db: Session, queue_item: NotificationQueue) -> bool:
        """Envoie une notification par SMS"""
        try:
            prefs = NotificationEngine.get_user_preferences(db, queue_item.user_id)
            if not prefs.phone_number:
                queue_item.error_message = "Numéro de téléphone manquant"
                return False
            
            # TODO: Intégrer avec un service SMS (Twilio, AWS SNS, etc.)
            print(f"📱 SMS ENVOYÉ AU {prefs.phone_number}")
            print(f"Message: {queue_item.message}")
            
            queue_item.external_id = f"sms_{datetime.utcnow().timestamp()}"
            return True
            
        except Exception as e:
            queue_item.error_message = f"Erreur SMS: {str(e)}"
            return False
    
    @staticmethod
    def get_user_preferences(db: Session, user_id: int) -> UserNotificationPreferences:
        """
        Récupère ou crée les préférences de notification d'un utilisateur
        """
        prefs = db.query(UserNotificationPreferences).filter(
            UserNotificationPreferences.user_id == user_id
        ).first()
        
        if not prefs:
            # Créer des préférences par défaut
            prefs = UserNotificationPreferences(user_id=user_id)
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        
        return prefs
    
    @staticmethod
    def create_digest(
        db: Session,
        user_id: int,
        digest_type: NotificationTrigger,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[NotificationDigest]:
        """
        Crée un digest de notifications pour une période
        """
        # Récupérer les notifications de la période
        notifications = db.query(NotificationQueue).filter(
            NotificationQueue.user_id == user_id,
            NotificationQueue.created_at >= period_start,
            NotificationQueue.created_at < period_end,
            NotificationQueue.status == QueueStatus.SENT
        ).all()
        
        if not notifications:
            return None
        
        # Grouper par catégorie
        categories_summary = {}
        for notif in notifications:
            category = notif.category.value
            if category not in categories_summary:
                categories_summary[category] = {
                    "count": 0,
                    "subjects": []
                }
            categories_summary[category]["count"] += 1
            categories_summary[category]["subjects"].append(notif.subject)
        
        # Générer le contenu du digest
        digest_content = NotificationEngine._generate_digest_content(
            digest_type, categories_summary, period_start, period_end
        )
        
        # Créer le digest
        digest = NotificationDigest(
            user_id=user_id,
            digest_type=digest_type,
            period_start=period_start,
            period_end=period_end,
            total_notifications=len(notifications),
            categories_summary=categories_summary,
            digest_content=digest_content
        )
        
        db.add(digest)
        db.commit()
        
        return digest
    
    @staticmethod
    def _generate_digest_content(
        digest_type: NotificationTrigger,
        categories_summary: Dict[str, Any],
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """Génère le contenu textuel du digest"""
        
        period_str = {
            NotificationTrigger.DAILY_DIGEST: "aujourd'hui",
            NotificationTrigger.WEEKLY_DIGEST: "cette semaine",
            NotificationTrigger.MONTHLY_DIGEST: "ce mois"
        }.get(digest_type, "récemment")
        
        content = f"📋 Résumé de vos notifications {period_str}\n\n"
        
        total = sum(cat["count"] for cat in categories_summary.values())
        content += f"Total: {total} notification(s)\n\n"
        
        for category, data in categories_summary.items():
            category_name = {
                "admin_action": "🔧 Actions administratives",
                "rent_payment": "💰 Paiements de loyer",
                "lease_events": "📄 Événements de bail",
                "property_updates": "🏠 Mises à jour propriétés",
                "maintenance": "🔨 Maintenance",
                "financial": "💳 Finances",
                "legal": "⚖️ Légal",
                "system": "⚙️ Système"
            }.get(category, category)
            
            content += f"{category_name}: {data['count']} notification(s)\n"
            for subject in data["subjects"][:3]:  # Max 3 sujets
                content += f"  • {subject}\n"
            if len(data["subjects"]) > 3:
                content += f"  • ... et {len(data['subjects']) - 3} autre(s)\n"
            content += "\n"
        
        return content


class SmartNotificationService:
    """
    Service de notifications intelligentes basées sur les données métier
    """
    
    @staticmethod
    def check_rent_due_notifications(db: Session) -> int:
        """
        Vérifie les loyers à échéance et envoie des notifications
        """
        notifications_sent = 0
        
        # Récupérer les baux actifs avec loyers bientôt dus
        from sqlalchemy import extract
        
        # Loyers dus dans 7 jours
        seven_days = datetime.utcnow() + timedelta(days=7)
        
        # Ici on simule, il faudrait une vraie logique de calcul des échéances
        # basée sur les dates de paiement dans les baux
        
        active_leases = db.query(Lease).filter(
            Lease.status == "active",
            Lease.end_date > datetime.utcnow()
        ).all()
        
        for lease in active_leases:
            # Calculer la prochaine échéance (simulation)
            # En réalité, il faudrait une table des échéances de paiement
            next_due_date = datetime.utcnow() + timedelta(days=7)  # Simulation
            
            if next_due_date.date() == seven_days.date():
                # Notifier le locataire et le propriétaire
                tenant_user = lease.tenant.user if hasattr(lease.tenant, 'user') else None
                owner_user = lease.creator  # Le créateur du bail est généralement le propriétaire
                
                for user in [tenant_user, owner_user]:
                    if user:
                        NotificationEngine.queue_notification(
                            db=db,
                            user_id=user.id,
                            category=NotificationCategory.RENT_PAYMENT,
                            subject=f"💰 Loyer à payer - {lease.apartment.building.name if lease.apartment and lease.apartment.building else 'Appartement'}",
                            message=f"Le loyer de {lease.monthly_rent}€ est dû le {next_due_date.strftime('%d/%m/%Y')}.",
                            notification_data={
                                "lease_id": lease.id,
                                "amount": float(lease.monthly_rent),
                                "due_date": next_due_date.isoformat(),
                                "apartment_name": f"{lease.apartment.building.name} - {lease.apartment.type_logement}" if lease.apartment else "Appartement",
                                "payment_url": f"/payments/lease/{lease.id}"
                            },
                            priority=NotificationPriority.HIGH
                        )
                        notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def check_lease_expiry_notifications(db: Session) -> int:
        """
        Vérifie les baux qui arrivent à expiration
        """
        notifications_sent = 0
        
        # Baux expirant dans 30 jours
        thirty_days = datetime.utcnow() + timedelta(days=30)
        
        expiring_leases = db.query(Lease).filter(
            Lease.status == "active",
            Lease.end_date >= datetime.utcnow(),
            Lease.end_date <= thirty_days
        ).all()
        
        for lease in expiring_leases:
            days_until_expiry = (lease.end_date - datetime.utcnow()).days
            
            # Notifier à 30, 15 et 7 jours
            if days_until_expiry in [30, 15, 7]:
                message = f"📄 Le bail de {lease.tenant.first_name} {lease.tenant.last_name} expire dans {days_until_expiry} jours."
                
                if days_until_expiry <= 7:
                    message += " Action urgente requise pour le renouvellement."
                
                NotificationEngine.queue_notification(
                    db=db,
                    user_id=lease.creator.id,
                    category=NotificationCategory.LEASE_EVENTS,
                    subject=f"📄 Expiration de bail - {days_until_expiry} jours",
                    message=message,
                    notification_data={
                        "lease_id": lease.id,
                        "tenant_name": f"{lease.tenant.first_name} {lease.tenant.last_name}",
                        "expiry_date": lease.end_date.isoformat(),
                        "days_until_expiry": days_until_expiry,
                        "action_url": f"/leases/{lease.id}"
                    },
                    priority=NotificationPriority.HIGH if days_until_expiry <= 7 else NotificationPriority.NORMAL
                )
                notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def check_maintenance_reminders(db: Session) -> int:
        """
        Rappels de maintenance périodique
        """
        notifications_sent = 0
        
        # Récupérer les propriétés qui nécessitent une maintenance
        # (simulation - il faudrait une vraie table de maintenance)
        from models import Building, Apartment
        
        # Bâtiments anciens nécessitant une inspection annuelle
        old_buildings = db.query(Building).filter(
            Building.floors > 3  # Simulation: bâtiments de plus de 3 étages
        ).all()
        
        for building in old_buildings:
            # Simulation: notification annuelle de maintenance
            # En réalité, il faudrait tracker les dernières maintenances
            
            NotificationEngine.queue_notification(
                db=db,
                user_id=building.user_id,
                category=NotificationCategory.MAINTENANCE,
                subject=f"🔨 Maintenance périodique - {building.name}",
                message=f"Il est temps de programmer la maintenance annuelle pour {building.name}. Vérifiez l'ascenseur, la plomberie et l'électricité.",
                notification_data={
                    "building_id": building.id,
                    "building_name": building.name,
                    "maintenance_type": "annual_inspection",
                    "action_url": f"/buildings/{building.id}/maintenance"
                },
                priority=NotificationPriority.NORMAL,
                scheduled_at=datetime.utcnow() + timedelta(days=1)  # Programmer pour demain
            )
            notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def check_lease_anniversaries(db: Session) -> int:
        """
        Notifications d'anniversaire de bail pour révision de loyer
        """
        notifications_sent = 0
        
        # Récupérer les baux qui ont un an aujourd'hui (ou dans les prochains jours)
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        anniversary_window = datetime.utcnow() - timedelta(days=358)  # 7 jours de marge
        
        anniversary_leases = db.query(Lease).filter(
            Lease.status == "active",
            Lease.start_date >= anniversary_window,
            Lease.start_date <= one_year_ago
        ).all()
        
        for lease in anniversary_leases:
            anniversary_date = lease.start_date + timedelta(days=365)
            days_to_anniversary = (anniversary_date - datetime.utcnow()).days
            
            if -3 <= days_to_anniversary <= 7:  # Fenêtre de -3 à +7 jours
                NotificationEngine.queue_notification(
                    db=db,
                    user_id=lease.creator.id,
                    category=NotificationCategory.LEASE_EVENTS,
                    subject=f"📅 Anniversaire de bail - Révision possible",
                    message=f"Le bail de {lease.tenant.first_name} {lease.tenant.last_name} a un an le {anniversary_date.strftime('%d/%m/%Y')}. C'est le moment idéal pour réviser le loyer selon l'IRL.",
                    notification_data={
                        "lease_id": lease.id,
                        "tenant_name": f"{lease.tenant.first_name} {lease.tenant.last_name}",
                        "current_rent": float(lease.monthly_rent),
                        "anniversary_date": anniversary_date.isoformat(),
                        "action_url": f"/leases/{lease.id}/revision"
                    },
                    priority=NotificationPriority.NORMAL
                )
                notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def check_document_expiry(db: Session) -> int:
        """
        Vérification des documents qui expirent (assurances, diagnostics, etc.)
        """
        notifications_sent = 0
        
        # Documents expirant dans 30 jours
        thirty_days = datetime.utcnow() + timedelta(days=30)
        
        from models import TenantDocument
        
        expiring_docs = db.query(TenantDocument).filter(
            TenantDocument.expiry_date.isnot(None),
            TenantDocument.expiry_date >= datetime.utcnow(),
            TenantDocument.expiry_date <= thirty_days
        ).all()
        
        for doc in expiring_docs:
            days_until_expiry = (doc.expiry_date - datetime.utcnow()).days
            
            NotificationEngine.queue_notification(
                db=db,
                user_id=doc.uploaded_by,
                category=NotificationCategory.LEGAL,
                subject=f"⚖️ Document expirant - {doc.title}",
                message=f"Le document '{doc.title}' expire dans {days_until_expiry} jours. Pensez à le renouveler.",
                notification_data={
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "document_type": doc.document_type,
                    "expiry_date": doc.expiry_date.isoformat(),
                    "days_until_expiry": days_until_expiry,
                    "action_url": f"/documents/{doc.id}"
                },
                priority=NotificationPriority.HIGH if days_until_expiry <= 7 else NotificationPriority.NORMAL
            )
            notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def send_welcome_notification(db: Session, user_id: int):
        """
        Notification de bienvenue pour les nouveaux utilisateurs
        """
        user = db.query(UserAuth).filter(UserAuth.id == user_id).first()
        if not user:
            return
        
        welcome_message = f"""
        🎉 Bienvenue sur LocAppart, {user.first_name} !
        
        Votre compte a été créé avec succès. Vous pouvez maintenant :
        • Ajouter vos propriétés
        • Gérer vos locataires
        • Suivre vos paiements
        • Créer des baux
        
        N'hésitez pas à explorer toutes les fonctionnalités disponibles.
        """
        
        NotificationEngine.queue_notification(
            db=db,
            user_id=user_id,
            category=NotificationCategory.SYSTEM,
            subject="🎉 Bienvenue sur LocAppart !",
            message=welcome_message.strip(),
            notification_data={
                "user_name": f"{user.first_name} {user.last_name}",
                "registration_date": user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                "action_url": "/dashboard"
            },
            priority=NotificationPriority.NORMAL
        )
    
    @staticmethod
    def send_quota_warning(db: Session, user_id: int, current_count: int, limit: int):
        """
        Notification d'avertissement de quota
        """
        percentage = (current_count / limit) * 100
        
        if percentage >= 80:  # Avertir à 80% du quota
            message = f"⚠️ Vous approchez de votre limite d'appartements.\n\nVous avez {current_count} appartement(s) sur {limit} autorisés ({percentage:.0f}%)."
            
            if percentage >= 95:
                message += "\n\n🔔 Pensez à passer en Premium pour un nombre illimité d'appartements !"
            
            NotificationEngine.queue_notification(
                db=db,
                user_id=user_id,
                category=NotificationCategory.SYSTEM,
                subject=f"⚠️ Quota d'appartements - {percentage:.0f}%",
                message=message,
                notification_data={
                    "current_count": current_count,
                    "limit": limit,
                    "percentage": percentage,
                    "action_url": "/subscription" if percentage >= 95 else "/apartments"
                },
                priority=NotificationPriority.HIGH if percentage >= 95 else NotificationPriority.NORMAL
            )


class NotificationScheduler:
    """
    Planificateur de tâches pour les notifications automatiques
    """
    
    @staticmethod
    def run_daily_tasks(db: Session) -> Dict[str, int]:
        """
        Tâches quotidiennes de notification
        """
        results = {
            "rent_due": 0,
            "lease_expiry": 0,
            "maintenance": 0,
            "anniversaries": 0,
            "document_expiry": 0,
            "queue_processed": 0
        }
        
        try:
            # Vérifications métier
            results["rent_due"] = SmartNotificationService.check_rent_due_notifications(db)
            results["lease_expiry"] = SmartNotificationService.check_lease_expiry_notifications(db)
            results["maintenance"] = SmartNotificationService.check_maintenance_reminders(db)
            results["anniversaries"] = SmartNotificationService.check_lease_anniversaries(db)
            results["document_expiry"] = SmartNotificationService.check_document_expiry(db)
            
            # Traitement de la queue
            queue_stats = NotificationEngine.process_queue(db, batch_size=100)
            results["queue_processed"] = queue_stats["sent"]
            
            print(f"📊 Tâches quotidiennes terminées: {results}")
            
        except Exception as e:
            print(f"❌ Erreur lors des tâches quotidiennes: {e}")
        
        return results
    
    @staticmethod
    def generate_daily_digests(db: Session) -> int:
        """
        Génère les digests quotidiens pour les utilisateurs qui l'ont configuré
        """
        digests_created = 0
        
        # Récupérer les utilisateurs avec digest quotidien
        users_with_daily_digest = db.query(UserNotificationPreferences).filter(
            UserNotificationPreferences.digest_frequency == NotificationTrigger.DAILY_DIGEST
        ).all()
        
        yesterday = datetime.utcnow() - timedelta(days=1)
        today = datetime.utcnow()
        
        for user_prefs in users_with_daily_digest:
            digest = NotificationEngine.create_digest(
                db=db,
                user_id=user_prefs.user_id,
                digest_type=NotificationTrigger.DAILY_DIGEST,
                period_start=yesterday.replace(hour=0, minute=0, second=0, microsecond=0),
                period_end=today.replace(hour=0, minute=0, second=0, microsecond=0)
            )
            
            if digest:
                # Envoyer le digest par email
                NotificationEngine.queue_notification(
                    db=db,
                    user_id=user_prefs.user_id,
                    category=NotificationCategory.SYSTEM,
                    subject="📋 Votre résumé quotidien - LocAppart",
                    message=digest.digest_content,
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.LOW
                )
                digests_created += 1
        
        return digests_created