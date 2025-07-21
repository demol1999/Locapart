"""
Modèles pour le système de multipropriété (SCI)
Gestion des groupes de propriété partagée avec sponsor Premium
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from enums import UserRole
from model_mixins import TimestampMixin, StatusMixin
import enum


class PropertyGroupType(str, enum.Enum):
    """Types de groupes de propriété"""
    SCI = "SCI"                    # Société Civile Immobilière
    FAMILY = "FAMILY"              # Famille
    INVESTMENT = "INVESTMENT"       # Investissement groupé
    OTHER = "OTHER"                # Autre


class PropertyGroupStatus(str, enum.Enum):
    """Statuts des groupes de propriété"""
    ACTIVE = "ACTIVE"              # Actif
    SUSPENDED = "SUSPENDED"        # Suspendu (sponsor non Premium)
    DISSOLVED = "DISSOLVED"        # Dissous


class MembershipStatus(str, enum.Enum):
    """Statuts des membres dans un groupe"""
    PENDING = "PENDING"            # Invitation en attente
    ACTIVE = "ACTIVE"              # Membre actif
    SUSPENDED = "SUSPENDED"        # Membre suspendu
    LEFT = "LEFT"                  # A quitté le groupe


class PropertyGroup(Base, TimestampMixin, StatusMixin):
    """
    Groupe de multipropriété géré par un sponsor Premium
    """
    __tablename__ = "property_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="Nom du groupe (ex: SCI Familiale)")
    description = Column(Text, nullable=True, comment="Description du groupe")
    group_type = Column(Enum(PropertyGroupType), nullable=False, default=PropertyGroupType.OTHER)
    
    # Sponsor (celui qui paie l'abonnement Premium)
    sponsor_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False, comment="Utilisateur Premium sponsor")
    
    # Configuration du groupe
    max_members = Column(Integer, default=10, comment="Nombre maximum de membres")
    auto_accept_invitations = Column(Boolean, default=False, comment="Acceptation automatique des invitations")
    
    # Statut du groupe
    group_status = Column(Enum(PropertyGroupStatus), nullable=False, default=PropertyGroupStatus.ACTIVE)
    
    # Relations
    sponsor = relationship("UserAuth", foreign_keys=[sponsor_id], back_populates="sponsored_groups")
    members = relationship("PropertyGroupMember", back_populates="group", cascade="all, delete-orphan")
    apartments = relationship("Apartment", back_populates="property_group")
    
    def __str__(self):
        return f"{self.name} (Sponsor: {self.sponsor.email if self.sponsor else 'N/A'})"
    
    @property
    def is_active(self) -> bool:
        return self.group_status == PropertyGroupStatus.ACTIVE
    
    @property
    def active_members_count(self) -> int:
        return len([m for m in self.members if m.membership_status == MembershipStatus.ACTIVE])
    
    @property
    def apartments_count(self) -> int:
        return len(self.apartments)


class PropertyGroupMember(Base, TimestampMixin):
    """
    Membres d'un groupe de multipropriété
    """
    __tablename__ = "property_group_members"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    group_id = Column(Integer, ForeignKey("property_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Statut et rôle
    membership_status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.PENDING)
    role_in_group = Column(String(50), nullable=False, default="member", comment="Rôle dans le groupe")
    
    # Permissions spécifiques
    can_invite_members = Column(Boolean, default=False, comment="Peut inviter d'autres membres")
    can_manage_apartments = Column(Boolean, default=False, comment="Peut gérer les appartements du groupe")
    can_view_finances = Column(Boolean, default=False, comment="Peut voir les données financières")
    
    # Métadonnées
    invited_by_id = Column(Integer, ForeignKey("user_auth.id"), nullable=True, comment="Qui a invité ce membre")
    invitation_message = Column(Text, nullable=True, comment="Message d'invitation")
    joined_at = Column(DateTime, nullable=True, comment="Date d'acceptation")
    left_at = Column(DateTime, nullable=True, comment="Date de départ")
    
    # Relations
    group = relationship("PropertyGroup", back_populates="members")
    user = relationship("UserAuth", foreign_keys=[user_id], back_populates="group_memberships")
    invited_by = relationship("UserAuth", foreign_keys=[invited_by_id])
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Unknown'} in {self.group.name if self.group else 'Unknown'}"
    
    @property
    def is_active(self) -> bool:
        return self.membership_status == MembershipStatus.ACTIVE
    
    def accept_invitation(self):
        """Accepte l'invitation au groupe"""
        self.membership_status = MembershipStatus.ACTIVE
        self.joined_at = func.now()
    
    def leave_group(self):
        """Quitte le groupe"""
        self.membership_status = MembershipStatus.LEFT
        self.left_at = func.now()


class PropertyGroupInvitation(Base, TimestampMixin):
    """
    Invitations pour rejoindre un groupe de multipropriété
    """
    __tablename__ = "property_group_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    group_id = Column(Integer, ForeignKey("property_groups.id"), nullable=False)
    invited_user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    invited_by_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Détails de l'invitation
    invitation_code = Column(String(50), unique=True, nullable=False, comment="Code unique d'invitation")
    invitation_message = Column(Text, nullable=True, comment="Message personnalisé")
    
    # Statut et timing
    status = Column(String(20), nullable=False, default="pending", comment="pending, accepted, declined, expired")
    expires_at = Column(DateTime, nullable=False, comment="Date d'expiration")
    responded_at = Column(DateTime, nullable=True, comment="Date de réponse")
    
    # Relations
    group = relationship("PropertyGroup")
    invited_user = relationship("UserAuth", foreign_keys=[invited_user_id])
    invited_by = relationship("UserAuth", foreign_keys=[invited_by_id])
    
    @property
    def is_expired(self) -> bool:
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_pending(self) -> bool:
        return self.status == "pending" and not self.is_expired


# Extension du modèle Apartment pour supporter les groupes
def extend_apartment_model():
    """
    Extension du modèle Apartment pour supporter la multipropriété
    """
    # Ajouter la relation au groupe de propriété
    from models import Apartment
    
    # Nouvelle colonne pour lier à un groupe de propriété
    Apartment.property_group_id = Column(
        Integer, 
        ForeignKey("property_groups.id"), 
        nullable=True, 
        comment="Groupe de multipropriété (si applicable)"
    )
    
    # Nouvelle relation
    Apartment.property_group = relationship("PropertyGroup", back_populates="apartments")
    
    # Propriétés calculées
    @property
    def is_shared_property(self) -> bool:
        """Vérifie si c'est un appartement en multipropriété"""
        return self.property_group_id is not None
    
    @property
    def sponsor_user(self):
        """Retourne l'utilisateur sponsor (celui qui paie)"""
        if self.property_group:
            return self.property_group.sponsor
        # Sinon, trouver le propriétaire principal
        owner_link = next((link for link in self.apartment_user_links if link.role == UserRole.owner), None)
        return owner_link.user if owner_link else None
    
    Apartment.is_shared_property = is_shared_property
    Apartment.sponsor_user = sponsor_user


# Extension du modèle UserAuth pour supporter les groupes
def extend_user_model():
    """
    Extension du modèle UserAuth pour supporter la multipropriété
    """
    from models import UserAuth
    
    # Nouvelles relations
    UserAuth.sponsored_groups = relationship(
        "PropertyGroup", 
        foreign_keys="PropertyGroup.sponsor_id",
        back_populates="sponsor",
        cascade="all, delete-orphan"
    )
    
    UserAuth.group_memberships = relationship(
        "PropertyGroupMember", 
        foreign_keys="PropertyGroupMember.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Méthodes utilitaires
    def get_active_memberships(self):
        """Retourne les memberships actifs"""
        return [m for m in self.group_memberships if m.is_active]
    
    def get_sponsored_apartments_count(self):
        """Compte les appartements sponsorisés (dans ses groupes)"""
        total = 0
        for group in self.sponsored_groups:
            if group.is_active:
                total += group.apartments_count
        return total
    
    def get_accessible_apartments_via_groups(self):
        """Retourne les appartements accessibles via les groupes"""
        apartments = []
        for membership in self.get_active_memberships():
            if membership.group.is_active:
                apartments.extend(membership.group.apartments)
        return apartments
    
    def can_sponsor_groups(self):
        """Vérifie si l'utilisateur peut sponsoriser des groupes (Premium requis)"""
        from services.subscription_service import SubscriptionService
        return SubscriptionService.has_premium_subscription(self.id)
    
    UserAuth.get_active_memberships = get_active_memberships
    UserAuth.get_sponsored_apartments_count = get_sponsored_apartments_count
    UserAuth.get_accessible_apartments_via_groups = get_accessible_apartments_via_groups
    UserAuth.can_sponsor_groups = can_sponsor_groups