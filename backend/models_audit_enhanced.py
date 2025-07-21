"""
Modèles d'audit enrichis pour le système d'undo
Backup complet et traçabilité avancée
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from enums import ActionType, EntityType, AdminRole
from model_mixins import TimestampMixin
import json
import uuid
from datetime import datetime, timedelta
import enum


class UndoComplexity(str, enum.Enum):
    """Niveaux de complexité pour l'undo"""
    SIMPLE = "simple"           # UPDATE simple, pas de dépendances
    MODERATE = "moderate"       # CREATE/DELETE avec peu de dépendances
    COMPLEX = "complex"         # DELETE avec beaucoup de dépendances
    IMPOSSIBLE = "impossible"   # Actions non-undoables (LOGIN, EMAIL, etc.)


class UndoStatus(str, enum.Enum):
    """Statut d'une action undo"""
    PENDING = "pending"         # En attente d'exécution
    EXECUTING = "executing"     # En cours d'exécution
    COMPLETED = "completed"     # Terminé avec succès
    FAILED = "failed"          # Échec de l'undo
    CANCELLED = "cancelled"     # Annulé par admin


class NotificationType(str, enum.Enum):
    """Types de notifications utilisateur"""
    ADMIN_ACTION = "admin_action"       # Action admin sur le compte
    UNDO_PERFORMED = "undo_performed"   # Un undo a été fait sur vos données
    SYSTEM_ALERT = "system_alert"       # Alerte système
    ACCOUNT_UPDATE = "account_update"   # Mise à jour de compte


class AuditLogEnhanced(Base, TimestampMixin):
    """
    Version enrichie du log d'audit avec capacités d'undo
    """
    __tablename__ = "audit_logs_enhanced"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Groupe de transaction pour actions liées
    transaction_group_id = Column(String(36), nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    
    # Informations de base
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=True)
    admin_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)  # Si action admin
    
    # Action effectuée
    action = Column(Enum(ActionType), nullable=False)
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_id = Column(Integer, nullable=True)
    
    # Description et contexte
    description = Column(String(500), nullable=False)
    user_action_context = Column(Text, nullable=True)  # Contexte de l'action utilisateur
    
    # Données complètes pour l'undo
    before_data = Column(JSON, nullable=True)  # État complet AVANT l'action
    after_data = Column(JSON, nullable=True)   # État complet APRÈS l'action
    related_entities = Column(JSON, nullable=True)  # Entités liées affectées
    
    # Métadonnées undo
    is_undoable = Column(Boolean, default=True)
    undo_complexity = Column(Enum(UndoComplexity), default=UndoComplexity.SIMPLE)
    undo_requirements = Column(JSON, nullable=True)  # Pré-requis pour l'undo
    
    # Informations techniques
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    endpoint = Column(String(200), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Expiration et rétention
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(days=7))
    
    # Relations
    user = relationship("UserAuth")
    admin_user = relationship("AdminUser")
    undo_actions = relationship("UndoAction", back_populates="audit_log", cascade="all, delete-orphan")
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        Index('idx_audit_enhanced_user_date', 'user_id', 'created_at'),
        Index('idx_audit_enhanced_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_enhanced_transaction', 'transaction_group_id'),
        Index('idx_audit_enhanced_undoable', 'is_undoable', 'undo_complexity'),
        Index('idx_audit_enhanced_expires', 'expires_at'),
    )
    
    def can_be_undone_by_role(self, admin_role: AdminRole) -> bool:
        """Vérifie si cette action peut être undone par un rôle admin"""
        if not self.is_undoable:
            return False
            
        # Super admin peut tout undo
        if admin_role == AdminRole.SUPER_ADMIN:
            return True
            
        # Autres rôles selon complexité
        role_permissions = {
            AdminRole.USER_MANAGER: [UndoComplexity.SIMPLE],
            AdminRole.SUPPORT: [UndoComplexity.SIMPLE, UndoComplexity.MODERATE],
            AdminRole.MODERATOR: [UndoComplexity.SIMPLE],
        }
        
        allowed_complexities = role_permissions.get(admin_role, [])
        return self.undo_complexity in allowed_complexities
    
    def is_still_undoable(self) -> bool:
        """Vérifie si l'action est encore undoable (pas expirée, pas déjà undone)"""
        if not self.is_undoable:
            return False
            
        # Vérifier expiration
        if datetime.utcnow() > self.expires_at:
            return False
            
        # Vérifier si déjà undone
        completed_undo = any(
            undo.status == UndoStatus.COMPLETED 
            for undo in self.undo_actions
        )
        
        return not completed_undo
    
    def get_impact_preview(self) -> dict:
        """Retourne un aperçu de l'impact de l'undo"""
        impact = {
            "primary_entity": {
                "type": self.entity_type,
                "id": self.entity_id,
                "description": self.description
            },
            "related_entities": self.related_entities or [],
            "complexity": self.undo_complexity,
            "risk_level": "low"
        }
        
        # Calculer niveau de risque
        if self.undo_complexity == UndoComplexity.COMPLEX:
            impact["risk_level"] = "high"
        elif self.undo_complexity == UndoComplexity.MODERATE:
            impact["risk_level"] = "medium"
            
        return impact


class DataBackup(Base, TimestampMixin):
    """
    Sauvegarde complète des données pour restore complexe
    """
    __tablename__ = "data_backups"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Référence à l'audit log
    audit_log_id = Column(Integer, ForeignKey("audit_logs_enhanced.id"), nullable=False)
    
    # Entité sauvegardée
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_id = Column(Integer, nullable=False)
    
    # Données complètes
    full_backup_data = Column(JSON, nullable=False)  # Backup JSON complet
    relationships_data = Column(JSON, nullable=True)  # Relations liées
    files_backup_path = Column(String(500), nullable=True)  # Chemin backup fichiers
    
    # Métadonnées
    backup_size_bytes = Column(Integer, nullable=True)
    compression_used = Column(Boolean, default=False)
    
    # Expiration (même que l'audit log)
    expires_at = Column(DateTime, nullable=False)
    
    # Relations
    audit_log = relationship("AuditLogEnhanced")
    
    # Index
    __table_args__ = (
        Index('idx_backup_entity', 'entity_type', 'entity_id'),
        Index('idx_backup_audit', 'audit_log_id'),
        Index('idx_backup_expires', 'expires_at'),
    )


class UndoAction(Base, TimestampMixin):
    """
    Suivi des actions d'undo effectuées par les admins
    """
    __tablename__ = "undo_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Référence à l'action originale
    audit_log_id = Column(Integer, ForeignKey("audit_logs_enhanced.id"), nullable=False)
    
    # Admin qui fait l'undo
    performed_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    
    # Statut et exécution
    status = Column(Enum(UndoStatus), default=UndoStatus.PENDING)
    
    # Détails de l'undo
    undo_reason = Column(Text, nullable=True)
    preview_data = Column(JSON, nullable=True)  # Aperçu des changements
    execution_steps = Column(JSON, nullable=True)  # Étapes d'exécution
    
    # Résultat
    execution_log = Column(Text, nullable=True)  # Log d'exécution détaillé
    error_message = Column(Text, nullable=True)  # Message d'erreur si échec
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relations
    audit_log = relationship("AuditLogEnhanced", back_populates="undo_actions")
    performed_by_admin = relationship("AdminUser")
    notification = relationship("UserNotification", back_populates="undo_action", uselist=False)
    
    # Index
    __table_args__ = (
        Index('idx_undo_audit', 'audit_log_id'),
        Index('idx_undo_admin', 'performed_by_admin_id'),
        Index('idx_undo_status', 'status'),
    )


class UserNotification(Base, TimestampMixin):
    """
    Notifications pour les utilisateurs (système de cloche)
    """
    __tablename__ = "user_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Destinataire
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Type et contenu
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Référence optionnelle à une action undo
    undo_action_id = Column(Integer, ForeignKey("undo_actions.id"), nullable=True)
    
    # Métadonnées
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    category = Column(String(50), nullable=True)
    action_url = Column(String(500), nullable=True)  # URL d'action si applicable
    
    # Statut
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Données additionnelles
    metadata = Column(JSON, nullable=True)
    
    # Relations
    user = relationship("UserAuth")
    undo_action = relationship("UndoAction", back_populates="notification")
    
    @property
    def is_expired(self) -> bool:
        """Vérifie si la notification a expiré"""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    @property
    def is_urgent(self) -> bool:
        """Vérifie si la notification est urgente"""
        return self.priority in ["high", "urgent"]
    
    # Index
    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_unread', 'user_id', 'is_read'),
        Index('idx_notification_type', 'notification_type'),
        Index('idx_notification_expires', 'expires_at'),
    )


class AuditTransactionGroup(Base, TimestampMixin):
    """
    Groupement des actions liées pour undo en bloc
    """
    __tablename__ = "audit_transaction_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identifiant unique du groupe
    group_id = Column(String(36), unique=True, nullable=False, index=True)
    
    # Métadonnées du groupe
    group_name = Column(String(200), nullable=False)  # Ex: "Création immeuble avec 5 appartements"
    group_description = Column(Text, nullable=True)
    
    # Statistiques
    total_actions = Column(Integer, default=0)
    undoable_actions = Column(Integer, default=0)
    complexity_level = Column(Enum(UndoComplexity), default=UndoComplexity.SIMPLE)
    
    # Utilisateur principal affecté
    primary_user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=True)
    
    # Statut global
    all_undoable = Column(Boolean, default=True)
    has_been_undone = Column(Boolean, default=False)
    
    # Relations
    primary_user = relationship("UserAuth")
    
    def get_audit_logs(self, db_session):
        """Récupère tous les logs d'audit de ce groupe"""
        return db_session.query(AuditLogEnhanced).filter(
            AuditLogEnhanced.transaction_group_id == self.group_id
        ).order_by(AuditLogEnhanced.created_at).all()
    
    def can_be_fully_undone(self) -> bool:
        """Vérifie si tout le groupe peut être undone"""
        return self.all_undoable and not self.has_been_undone
    
    # Index
    __table_args__ = (
        Index('idx_transaction_group_id', 'group_id'),
        Index('idx_transaction_user', 'primary_user_id'),
        Index('idx_transaction_undoable', 'all_undoable', 'has_been_undone'),
    )