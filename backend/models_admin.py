"""
Modèles pour le système d'administration
Gestion des rôles admin et actions administratives
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from enums import AdminRole, UserStatus, AccountAction
from model_mixins import TimestampMixin, AuditMixin
import json


class AdminUser(Base, TimestampMixin):
    """
    Utilisateur administrateur avec rôles et permissions
    """
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Lien vers l'utilisateur principal
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False, unique=True)
    
    # Rôle administrateur
    admin_role = Column(Enum(AdminRole), nullable=False, default=AdminRole.VIEWER)
    
    # Permissions spécifiques
    can_manage_users = Column(Boolean, default=False, comment="Peut gérer les utilisateurs")
    can_manage_subscriptions = Column(Boolean, default=False, comment="Peut gérer les abonnements")
    can_view_finances = Column(Boolean, default=False, comment="Peut voir les données financières")
    can_manage_properties = Column(Boolean, default=False, comment="Peut gérer les propriétés")
    can_access_audit_logs = Column(Boolean, default=False, comment="Peut accéder aux logs d'audit")
    can_manage_admins = Column(Boolean, default=False, comment="Peut gérer d'autres admins")
    
    # Statut
    is_active = Column(Boolean, default=True, comment="Admin actif")
    last_login_at = Column(DateTime, nullable=True, comment="Dernière connexion admin")
    
    # Métadonnées
    notes = Column(Text, nullable=True, comment="Notes internes")
    created_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    
    # Relations
    user = relationship("UserAuth", backref="admin_profile")
    created_by = relationship("AdminUser", remote_side=[id])
    admin_actions = relationship("AdminAction", back_populates="admin_user", cascade="all, delete-orphan")
    
    def __str__(self):
        return f"Admin {self.user.email if self.user else 'Unknown'} ({self.admin_role})"
    
    @property
    def permissions_summary(self) -> dict:
        """Résumé des permissions"""
        return {
            "role": self.admin_role,
            "can_manage_users": self.can_manage_users,
            "can_manage_subscriptions": self.can_manage_subscriptions,
            "can_view_finances": self.can_view_finances,
            "can_manage_properties": self.can_manage_properties,
            "can_access_audit_logs": self.can_access_audit_logs,
            "can_manage_admins": self.can_manage_admins
        }
    
    def has_permission(self, permission: str) -> bool:
        """Vérifie si l'admin a une permission spécifique"""
        if not self.is_active:
            return False
        
        # Super admin a tous les droits
        if self.admin_role == AdminRole.SUPER_ADMIN:
            return True
        
        permission_map = {
            "manage_users": self.can_manage_users,
            "manage_subscriptions": self.can_manage_subscriptions,
            "view_finances": self.can_view_finances,
            "manage_properties": self.can_manage_properties,
            "access_audit_logs": self.can_access_audit_logs,
            "manage_admins": self.can_manage_admins
        }
        
        return permission_map.get(permission, False)


class AdminAction(Base, TimestampMixin):
    """
    Log des actions administratives
    """
    __tablename__ = "admin_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Qui a fait l'action
    admin_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    
    # Sur quel utilisateur
    target_user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Type d'action
    action_type = Column(Enum(AccountAction), nullable=False)
    
    # Détails
    description = Column(Text, nullable=False, comment="Description de l'action")
    reason = Column(Text, nullable=True, comment="Raison de l'action")
    
    # Données avant/après (pour rollback)
    before_data = Column(JSON, nullable=True, comment="État avant l'action")
    after_data = Column(JSON, nullable=True, comment="État après l'action")
    
    # Contexte
    ip_address = Column(String(45), nullable=True, comment="Adresse IP de l'admin")
    user_agent = Column(Text, nullable=True, comment="User agent de l'admin")
    
    # Relations
    admin_user = relationship("AdminUser", back_populates="admin_actions")
    target_user = relationship("UserAuth")
    
    def __str__(self):
        return f"{self.action_type} on {self.target_user.email if self.target_user else 'Unknown'} by {self.admin_user.user.email if self.admin_user else 'Unknown'}"


class UserStatusHistory(Base, TimestampMixin):
    """
    Historique des changements de statut utilisateur
    """
    __tablename__ = "user_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Utilisateur concerné
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Changement de statut
    previous_status = Column(Enum(UserStatus), nullable=True)
    new_status = Column(Enum(UserStatus), nullable=False)
    
    # Détails
    reason = Column(Text, nullable=True, comment="Raison du changement")
    changed_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    
    # Durée (pour suspensions temporaires)
    duration_days = Column(Integer, nullable=True, comment="Durée en jours (si applicable)")
    expires_at = Column(DateTime, nullable=True, comment="Expiration (si applicable)")
    
    # Relations
    user = relationship("UserAuth")
    changed_by_admin = relationship("AdminUser")
    
    @property
    def is_temporary(self) -> bool:
        """Vérifie si c'est un changement temporaire"""
        return self.expires_at is not None and self.expires_at > func.now()


# Extension du modèle UserAuth pour l'administration
def extend_user_model_for_admin():
    """
    Étend le modèle UserAuth avec les champs d'administration
    """
    from models import UserAuth
    
    # Nouveau statut utilisateur
    UserAuth.user_status = Column(
        Enum(UserStatus), 
        nullable=False, 
        default=UserStatus.ACTIVE,
        comment="Statut administratif de l'utilisateur"
    )
    
    # Métadonnées admin
    UserAuth.admin_notes = Column(Text, nullable=True, comment="Notes administratives")
    UserAuth.suspension_reason = Column(Text, nullable=True, comment="Raison de suspension")
    UserAuth.suspension_expires_at = Column(DateTime, nullable=True, comment="Fin de suspension")
    UserAuth.last_admin_action = Column(DateTime, nullable=True, comment="Dernière action admin")
    
    # Relations
    UserAuth.status_history = relationship(
        "UserStatusHistory", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    
    UserAuth.admin_actions_received = relationship(
        "AdminAction",
        foreign_keys="AdminAction.target_user_id",
        back_populates="target_user",
        cascade="all, delete-orphan"
    )
    
    # Méthodes utilitaires
    def is_suspended(self) -> bool:
        """Vérifie si l'utilisateur est suspendu"""
        if self.user_status != UserStatus.SUSPENDED:
            return False
        
        # Vérifier si la suspension a expiré
        if self.suspension_expires_at and self.suspension_expires_at <= func.now():
            return False
        
        return True
    
    def is_banned(self) -> bool:
        """Vérifie si l'utilisateur est banni"""
        return self.user_status == UserStatus.BANNED
    
    def can_login(self) -> bool:
        """Vérifie si l'utilisateur peut se connecter"""
        return self.user_status in [UserStatus.ACTIVE, UserStatus.PENDING_VERIFICATION]
    
    def get_status_display(self) -> str:
        """Retourne le statut formaté pour l'affichage"""
        status_map = {
            UserStatus.ACTIVE: "Actif",
            UserStatus.INACTIVE: "Inactif", 
            UserStatus.SUSPENDED: "Suspendu",
            UserStatus.BANNED: "Banni",
            UserStatus.PENDING_VERIFICATION: "En attente de vérification"
        }
        return status_map.get(self.user_status, str(self.user_status))
    
    UserAuth.is_suspended = is_suspended
    UserAuth.is_banned = is_banned
    UserAuth.can_login = can_login
    UserAuth.get_status_display = get_status_display


class SystemSettings(Base, TimestampMixin):
    """
    Paramètres système configurables par les admins
    """
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Clé de paramètre
    setting_key = Column(String(100), nullable=False, unique=True, comment="Clé du paramètre")
    setting_value = Column(Text, nullable=True, comment="Valeur du paramètre")
    setting_type = Column(String(20), nullable=False, default="string", comment="Type de donnée")
    
    # Métadonnées
    description = Column(Text, nullable=True, comment="Description du paramètre")
    category = Column(String(50), nullable=True, comment="Catégorie")
    is_sensitive = Column(Boolean, default=False, comment="Paramètre sensible")
    
    # Audit
    modified_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    
    # Relations
    modified_by_admin = relationship("AdminUser")
    
    def get_value(self):
        """Retourne la valeur typée"""
        if self.setting_type == "bool":
            return self.setting_value.lower() in ["true", "1", "yes", "on"]
        elif self.setting_type == "int":
            return int(self.setting_value) if self.setting_value else 0
        elif self.setting_type == "float":
            return float(self.setting_value) if self.setting_value else 0.0
        elif self.setting_type == "json":
            return json.loads(self.setting_value) if self.setting_value else {}
        else:
            return self.setting_value
    
    def set_value(self, value):
        """Définit la valeur avec conversion de type"""
        if self.setting_type == "json":
            self.setting_value = json.dumps(value)
        else:
            self.setting_value = str(value)


class AdminNotification(Base, TimestampMixin):
    """
    Notifications pour les administrateurs
    """
    __tablename__ = "admin_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Destinataire
    admin_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)  # Null = tous les admins
    
    # Contenu
    title = Column(String(200), nullable=False, comment="Titre de la notification")
    message = Column(Text, nullable=False, comment="Message")
    notification_type = Column(String(50), nullable=False, default="info", comment="Type de notification")
    
    # Statut
    is_read = Column(Boolean, default=False, comment="Lu")
    read_at = Column(DateTime, nullable=True, comment="Date de lecture")
    
    # Métadonnées
    priority = Column(String(20), default="normal", comment="Priorité")
    action_url = Column(String(500), nullable=True, comment="URL d'action")
    expires_at = Column(DateTime, nullable=True, comment="Date d'expiration")
    
    # Relations
    admin_user = relationship("AdminUser")
    
    @property
    def is_expired(self) -> bool:
        """Vérifie si la notification a expiré"""
        return self.expires_at and self.expires_at <= func.now()
    
    @property
    def is_urgent(self) -> bool:
        """Vérifie si la notification est urgente"""
        return self.priority in ["high", "urgent"]