"""
Extension du système de notifications
File d'attente, préférences utilisateur et notifications intelligentes
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum, JSON, Index, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from model_mixins import TimestampMixin
import enum
from datetime import datetime, timedelta


class NotificationChannel(str, enum.Enum):
    """Canaux de notification"""
    IN_APP = "in_app"           # Notification dans l'app (cloche)
    EMAIL = "email"             # Email
    SMS = "sms"                 # SMS (futur)
    PUSH = "push"               # Push notification (futur)


class NotificationCategory(str, enum.Enum):
    """Catégories de notifications"""
    ADMIN_ACTION = "admin_action"           # Actions administratives
    RENT_PAYMENT = "rent_payment"           # Paiements de loyer
    LEASE_EVENTS = "lease_events"           # Événements de bail
    PROPERTY_UPDATES = "property_updates"   # Mises à jour de propriétés
    MAINTENANCE = "maintenance"             # Maintenance et travaux
    FINANCIAL = "financial"                 # Finances et comptabilité
    LEGAL = "legal"                         # Légal et juridique
    SYSTEM = "system"                       # Système et technique
    MARKETING = "marketing"                 # Marketing et promotions


class NotificationTrigger(str, enum.Enum):
    """Déclencheurs de notification"""
    IMMEDIATE = "immediate"                 # Immédiat
    DAILY_DIGEST = "daily_digest"          # Résumé quotidien
    WEEKLY_DIGEST = "weekly_digest"        # Résumé hebdomadaire
    MONTHLY_DIGEST = "monthly_digest"      # Résumé mensuel
    CUSTOM_SCHEDULE = "custom_schedule"    # Programmation personnalisée


class NotificationPriority(str, enum.Enum):
    """Priorités de notification"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class QueueStatus(str, enum.Enum):
    """Statuts de la file d'attente"""
    PENDING = "pending"         # En attente
    PROCESSING = "processing"   # En cours de traitement
    SENT = "sent"              # Envoyée
    FAILED = "failed"          # Échec
    RETRYING = "retrying"      # Nouvelle tentative
    CANCELLED = "cancelled"     # Annulée


class UserNotificationPreferences(Base, TimestampMixin):
    """
    Préférences de notification par utilisateur
    """
    __tablename__ = "user_notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False, unique=True)
    
    # Préférences globales
    notifications_enabled = Column(Boolean, default=True, comment="Notifications activées")
    email_notifications = Column(Boolean, default=True, comment="Notifications par email")
    sms_notifications = Column(Boolean, default=False, comment="Notifications par SMS")
    push_notifications = Column(Boolean, default=True, comment="Push notifications")
    
    # Fréquence et timing
    digest_frequency = Column(Enum(NotificationTrigger), default=NotificationTrigger.IMMEDIATE)
    quiet_hours_enabled = Column(Boolean, default=False, comment="Heures silencieuses")
    quiet_hours_start = Column(String(5), default="22:00", comment="Début heures silencieuses")
    quiet_hours_end = Column(String(5), default="08:00", comment="Fin heures silencieuses")
    timezone = Column(String(50), default="Europe/Paris", comment="Fuseau horaire")
    
    # Préférences par catégorie (JSON)
    category_preferences = Column(JSON, nullable=True, comment="Préférences par catégorie")
    
    # Canaux préférés par type de notification
    admin_action_channels = Column(JSON, default=lambda: ["in_app", "email"])
    rent_payment_channels = Column(JSON, default=lambda: ["in_app", "email"])
    lease_events_channels = Column(JSON, default=lambda: ["in_app", "email"])
    property_updates_channels = Column(JSON, default=lambda: ["in_app"])
    maintenance_channels = Column(JSON, default=lambda: ["in_app"])
    financial_channels = Column(JSON, default=lambda: ["in_app", "email"])
    legal_channels = Column(JSON, default=lambda: ["in_app", "email"])
    system_channels = Column(JSON, default=lambda: ["in_app"])
    marketing_channels = Column(JSON, default=lambda: [])
    
    # Avancé
    email_address = Column(String(255), nullable=True, comment="Email alternatif pour notifications")
    phone_number = Column(String(20), nullable=True, comment="Téléphone pour SMS")
    language = Column(String(5), default="fr", comment="Langue des notifications")
    
    # Relations
    user = relationship("UserAuth", backref="notification_preferences")
    
    def get_channels_for_category(self, category: NotificationCategory) -> list:
        """Retourne les canaux activés pour une catégorie"""
        channel_map = {
            NotificationCategory.ADMIN_ACTION: self.admin_action_channels,
            NotificationCategory.RENT_PAYMENT: self.rent_payment_channels,
            NotificationCategory.LEASE_EVENTS: self.lease_events_channels,
            NotificationCategory.PROPERTY_UPDATES: self.property_updates_channels,
            NotificationCategory.MAINTENANCE: self.maintenance_channels,
            NotificationCategory.FINANCIAL: self.financial_channels,
            NotificationCategory.LEGAL: self.legal_channels,
            NotificationCategory.SYSTEM: self.system_channels,
            NotificationCategory.MARKETING: self.marketing_channels,
        }
        
        return channel_map.get(category, ["in_app"])
    
    def is_category_enabled(self, category: NotificationCategory) -> bool:
        """Vérifie si une catégorie est activée"""
        if not self.notifications_enabled:
            return False
            
        if not self.category_preferences:
            return True  # Activé par défaut
            
        return self.category_preferences.get(category.value, True)
    
    # Index
    __table_args__ = (
        Index('idx_user_notification_prefs', 'user_id'),
    )


class NotificationQueue(Base, TimestampMixin):
    """
    File d'attente des notifications à envoyer
    """
    __tablename__ = "notification_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Destinataire et canal
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    # Contenu de la notification
    category = Column(Enum(NotificationCategory), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    subject = Column(String(255), nullable=False, comment="Sujet/titre")
    message = Column(Text, nullable=False, comment="Message principal")
    html_message = Column(Text, nullable=True, comment="Message HTML pour email")
    
    # Métadonnées
    notification_data = Column(JSON, nullable=True, comment="Données additionnelles")
    template_name = Column(String(100), nullable=True, comment="Template utilisé")
    
    # Programmation
    scheduled_at = Column(DateTime, nullable=True, comment="Programmé pour")
    expires_at = Column(DateTime, nullable=True, comment="Expire le")
    
    # Statut et traitement
    status = Column(Enum(QueueStatus), default=QueueStatus.PENDING)
    attempts = Column(Integer, default=0, comment="Nombre de tentatives")
    max_attempts = Column(Integer, default=3, comment="Max tentatives")
    
    # Résultat
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    external_id = Column(String(255), nullable=True, comment="ID externe (email service, etc.)")
    
    # Groupement (pour digests)
    group_key = Column(String(100), nullable=True, comment="Clé de groupement")
    digest_type = Column(Enum(NotificationTrigger), nullable=True)
    
    # Relations
    user = relationship("UserAuth")
    
    @property
    def can_retry(self) -> bool:
        """Peut être retentée"""
        return self.status == QueueStatus.FAILED and self.attempts < self.max_attempts
    
    @property
    def is_expired(self) -> bool:
        """Est expirée"""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    # Index
    __table_args__ = (
        Index('idx_queue_status_scheduled', 'status', 'scheduled_at'),
        Index('idx_queue_user_category', 'user_id', 'category'),
        Index('idx_queue_priority', 'priority', 'created_at'),
        Index('idx_queue_digest', 'digest_type', 'group_key'),
        Index('idx_queue_expires', 'expires_at'),
    )


class NotificationTemplate(Base, TimestampMixin):
    """
    Templates de notification réutilisables
    """
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identification
    template_key = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Catégorie et canal
    category = Column(Enum(NotificationCategory), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    # Templates
    subject_template = Column(String(500), nullable=False, comment="Template du sujet")
    message_template = Column(Text, nullable=False, comment="Template du message")
    html_template = Column(Text, nullable=True, comment="Template HTML")
    
    # Configuration
    default_priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    variables = Column(JSON, nullable=True, comment="Variables disponibles")
    
    # Métadonnées
    language = Column(String(5), default="fr")
    is_active = Column(Boolean, default=True)
    
    # Index
    __table_args__ = (
        Index('idx_template_key', 'template_key'),
        Index('idx_template_category_channel', 'category', 'channel'),
        Index('idx_template_active', 'is_active'),
    )


class NotificationRule(Base, TimestampMixin):
    """
    Règles automatiques de notification
    """
    __tablename__ = "notification_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identification
    rule_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Déclencheur
    trigger_event = Column(String(100), nullable=False, comment="Événement déclencheur")
    trigger_conditions = Column(JSON, nullable=True, comment="Conditions de déclenchement")
    
    # Cible
    target_user_type = Column(String(50), default="specific", comment="all/owners/tenants/specific")
    target_user_ids = Column(JSON, nullable=True, comment="IDs utilisateurs spécifiques")
    
    # Notification
    category = Column(Enum(NotificationCategory), nullable=False)
    template_key = Column(String(100), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    
    # Timing
    delay_minutes = Column(Integer, default=0, comment="Délai avant envoi")
    schedule_expression = Column(String(100), nullable=True, comment="Expression cron")
    
    # Limitations
    max_frequency_hours = Column(Integer, nullable=True, comment="Fréquence max en heures")
    
    # Statistiques
    total_sent = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    
    # Index
    __table_args__ = (
        Index('idx_rule_active_event', 'is_active', 'trigger_event'),
        Index('idx_rule_next_execution', 'last_executed_at'),
    )


class NotificationDigest(Base, TimestampMixin):
    """
    Digests groupés de notifications
    """
    __tablename__ = "notification_digests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Utilisateur et période
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    digest_type = Column(Enum(NotificationTrigger), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Contenu
    total_notifications = Column(Integer, default=0)
    categories_summary = Column(JSON, nullable=True, comment="Résumé par catégorie")
    digest_content = Column(Text, nullable=False, comment="Contenu du digest")
    html_content = Column(Text, nullable=True, comment="Contenu HTML")
    
    # Statut
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Relations
    user = relationship("UserAuth")
    
    # Index
    __table_args__ = (
        Index('idx_digest_user_period', 'user_id', 'digest_type', 'period_start'),
        Index('idx_digest_unsent', 'is_sent', 'period_end'),
    )


class SmartNotificationTrigger(Base, TimestampMixin):
    """
    Déclencheurs intelligents basés sur les données métier
    """
    __tablename__ = "smart_notification_triggers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identification
    trigger_name = Column(String(255), nullable=False)
    trigger_type = Column(String(50), nullable=False, comment="rent_due/lease_expiry/maintenance_due/etc.")
    
    # Configuration
    days_before = Column(Integer, nullable=True, comment="Jours avant l'échéance")
    recurrence_days = Column(Integer, nullable=True, comment="Récurrence en jours")
    
    # Conditions
    conditions = Column(JSON, nullable=True, comment="Conditions supplémentaires")
    
    # Template et priorité
    template_key = Column(String(100), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    
    # Statut
    is_active = Column(Boolean, default=True)
    next_check_at = Column(DateTime, nullable=True, comment="Prochaine vérification")
    
    # Statistiques
    total_triggered = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    
    # Index
    __table_args__ = (
        Index('idx_trigger_active_type', 'is_active', 'trigger_type'),
        Index('idx_trigger_next_check', 'next_check_at'),
    )


class NotificationAnalytics(Base, TimestampMixin):
    """
    Analytiques des notifications pour optimisation
    """
    __tablename__ = "notification_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Période
    date = Column(DateTime, nullable=False, comment="Date de l'analytique")
    
    # Métriques globales
    total_sent = Column(Integer, default=0)
    total_delivered = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_clicked = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    
    # Par canal
    in_app_sent = Column(Integer, default=0)
    email_sent = Column(Integer, default=0)
    sms_sent = Column(Integer, default=0)
    
    # Par catégorie (JSON)
    category_stats = Column(JSON, nullable=True)
    
    # Taux de performance
    delivery_rate = Column(DECIMAL(5, 4), nullable=True, comment="Taux de livraison")
    open_rate = Column(DECIMAL(5, 4), nullable=True, comment="Taux d'ouverture")
    click_rate = Column(DECIMAL(5, 4), nullable=True, comment="Taux de clic")
    
    # Index
    __table_args__ = (
        Index('idx_analytics_date', 'date'),
    )


# Extension du modèle UserAuth pour les relations
def extend_user_model_for_notifications():
    """Étend UserAuth avec les relations de notification"""
    from models import UserAuth
    
    # Relations avec les nouvelles tables
    UserAuth.notification_queue = relationship(
        "NotificationQueue", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    
    UserAuth.notification_digests = relationship(
        "NotificationDigest",
        back_populates="user",
        cascade="all, delete-orphan"
    )