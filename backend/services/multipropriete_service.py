"""
Service de gestion de la multipropriété
Gestion des groupes, quotas et permissions avec sponsor Premium
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid

from models import UserAuth, Apartment, ApartmentUserLink
from models_multipropriete import (
    PropertyGroup, PropertyGroupMember, PropertyGroupInvitation,
    PropertyGroupStatus, MembershipStatus, PropertyGroupType
)
from enums import UserRole, SubscriptionType
from services.subscription_service import SubscriptionService
from error_handlers import BusinessLogicErrorHandler, PermissionErrorHandler
from constants import FREE_SUBSCRIPTION_LIMITS


class MultiproprieteDashboard:
    """Données du tableau de bord multipropriété"""
    
    def __init__(
        self,
        personal_apartments: int,
        sponsored_apartments: int,
        accessible_apartments: int,
        personal_quota_used: int,
        personal_quota_max: int,
        sponsored_groups: List[Dict],
        member_groups: List[Dict],
        can_create_groups: bool
    ):
        self.personal_apartments = personal_apartments
        self.sponsored_apartments = sponsored_apartments
        self.accessible_apartments = accessible_apartments
        self.personal_quota_used = personal_quota_used
        self.personal_quota_max = personal_quota_max
        self.sponsored_groups = sponsored_groups
        self.member_groups = member_groups
        self.can_create_groups = can_create_groups
    
    @property
    def total_accessible_apartments(self) -> int:
        return self.personal_apartments + self.accessible_apartments
    
    @property
    def is_personal_quota_exceeded(self) -> bool:
        return self.personal_quota_used > self.personal_quota_max
    
    @property
    def can_add_personal_apartment(self) -> bool:
        return self.personal_quota_used < self.personal_quota_max


class MultiproprietService:
    """
    Service principal pour gérer la multipropriété
    """
    
    @staticmethod
    def get_user_apartment_quotas(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Calcule les quotas d'appartements pour un utilisateur avec multipropriété
        """
        user = db.query(UserAuth).filter(UserAuth.id == user_id).first()
        if not user:
            raise ValueError("Utilisateur non trouvé")
        
        # Vérifier le type d'abonnement
        subscription = SubscriptionService.get_user_subscription(db, user_id)
        is_premium = subscription.get("type") == SubscriptionType.PREMIUM
        
        # Compter les appartements personnels (hors groupes)
        personal_apartments = db.query(func.count(ApartmentUserLink.apartment_id)).join(
            Apartment, ApartmentUserLink.apartment_id == Apartment.id
        ).filter(
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.role == UserRole.owner,
            Apartment.property_group_id.is_(None)  # Pas dans un groupe
        ).scalar() or 0
        
        # Compter les appartements sponsorisés (dans ses groupes)
        sponsored_apartments = 0
        if is_premium:
            sponsored_apartments = db.query(func.count(Apartment.id)).join(
                PropertyGroup, Apartment.property_group_id == PropertyGroup.id
            ).filter(
                PropertyGroup.sponsor_id == user_id,
                PropertyGroup.group_status == PropertyGroupStatus.ACTIVE
            ).scalar() or 0
        
        # Compter les appartements accessibles via memberships
        accessible_via_groups = db.query(func.count(Apartment.id)).join(
            PropertyGroup, Apartment.property_group_id == PropertyGroup.id
        ).join(
            PropertyGroupMember, PropertyGroup.id == PropertyGroupMember.group_id
        ).filter(
            PropertyGroupMember.user_id == user_id,
            PropertyGroupMember.membership_status == MembershipStatus.ACTIVE,
            PropertyGroup.group_status == PropertyGroupStatus.ACTIVE,
            PropertyGroup.sponsor_id != user_id  # Pas ses propres groupes
        ).scalar() or 0
        
        # Calculer les limites
        if is_premium:
            personal_quota = -1  # Illimité
            sponsored_quota = -1  # Illimité
        else:
            personal_quota = FREE_SUBSCRIPTION_LIMITS["max_apartments"]  # 3
            sponsored_quota = 0  # Ne peut pas sponsoriser
        
        return {
            "personal_apartments": personal_apartments,
            "sponsored_apartments": sponsored_apartments,
            "accessible_via_groups": accessible_via_groups,
            "total_accessible": personal_apartments + sponsored_apartments + accessible_via_groups,
            "personal_quota": personal_quota,
            "sponsored_quota": sponsored_quota,
            "can_add_personal": personal_quota == -1 or personal_apartments < personal_quota,
            "can_sponsor_groups": is_premium,
            "is_premium": is_premium
        }
    
    @staticmethod
    def can_user_add_apartment(db: Session, user_id: int, apartment_type: str = "personal") -> Tuple[bool, str]:
        """
        Vérifie si un utilisateur peut ajouter un appartement
        apartment_type: "personal" ou "sponsored"
        """
        quotas = MultiproprietService.get_user_apartment_quotas(db, user_id)
        
        if apartment_type == "personal":
            if quotas["can_add_personal"]:
                return True, "OK"
            else:
                remaining = quotas["personal_quota"] - quotas["personal_apartments"]
                return False, f"Limite d'appartements personnels atteinte ({quotas['personal_apartments']}/{quotas['personal_quota']})"
        
        elif apartment_type == "sponsored":
            if quotas["can_sponsor_groups"]:
                return True, "OK"
            else:
                return False, "Abonnement Premium requis pour sponsoriser des groupes"
        
        return False, "Type d'appartement invalide"
    
    @staticmethod
    def create_property_group(
        db: Session,
        sponsor_id: int,
        name: str,
        description: str = None,
        group_type: PropertyGroupType = PropertyGroupType.OTHER,
        max_members: int = 10
    ) -> PropertyGroup:
        """
        Crée un nouveau groupe de multipropriété
        """
        # Vérifier que le sponsor peut créer des groupes
        can_sponsor, message = MultiproprietService.can_user_add_apartment(db, sponsor_id, "sponsored")
        if not can_sponsor:
            raise PermissionErrorHandler.access_denied(message)
        
        # Créer le groupe
        group = PropertyGroup(
            name=name,
            description=description,
            group_type=group_type,
            sponsor_id=sponsor_id,
            max_members=max_members,
            group_status=PropertyGroupStatus.ACTIVE
        )
        
        db.add(group)
        db.commit()
        db.refresh(group)
        
        # Ajouter le sponsor comme membre administrateur
        sponsor_member = PropertyGroupMember(
            group_id=group.id,
            user_id=sponsor_id,
            membership_status=MembershipStatus.ACTIVE,
            role_in_group="admin",
            can_invite_members=True,
            can_manage_apartments=True,
            can_view_finances=True,
            joined_at=datetime.utcnow()
        )
        
        db.add(sponsor_member)
        db.commit()
        
        return group
    
    @staticmethod
    def invite_user_to_group(
        db: Session,
        group_id: int,
        invited_user_email: str,
        invited_by_id: int,
        message: str = None,
        expires_in_days: int = 7
    ) -> PropertyGroupInvitation:
        """
        Invite un utilisateur à rejoindre un groupe de multipropriété
        """
        # Vérifier que le groupe existe et est actif
        group = db.query(PropertyGroup).filter(
            PropertyGroup.id == group_id,
            PropertyGroup.group_status == PropertyGroupStatus.ACTIVE
        ).first()
        
        if not group:
            raise ValueError("Groupe non trouvé ou inactif")
        
        # Vérifier que l'inviteur a les permissions
        inviter_member = db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.user_id == invited_by_id,
            PropertyGroupMember.membership_status == MembershipStatus.ACTIVE
        ).first()
        
        if not inviter_member or not inviter_member.can_invite_members:
            raise PermissionErrorHandler.access_denied("Vous n'avez pas les permissions pour inviter des membres")
        
        # Trouver l'utilisateur à inviter
        invited_user = db.query(UserAuth).filter(UserAuth.email == invited_user_email).first()
        if not invited_user:
            raise ValueError(f"Utilisateur {invited_user_email} non trouvé")
        
        # Vérifier qu'il n'est pas déjà membre
        existing_member = db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.user_id == invited_user.id
        ).first()
        
        if existing_member:
            if existing_member.membership_status == MembershipStatus.ACTIVE:
                raise ValueError("L'utilisateur est déjà membre du groupe")
            elif existing_member.membership_status == MembershipStatus.PENDING:
                raise ValueError("Une invitation est déjà en attente pour cet utilisateur")
        
        # Vérifier la limite de membres
        active_members_count = db.query(func.count(PropertyGroupMember.id)).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.membership_status == MembershipStatus.ACTIVE
        ).scalar()
        
        if active_members_count >= group.max_members:
            raise BusinessLogicErrorHandler.subscription_limit_exceeded(
                active_members_count, group.max_members, "membres dans le groupe"
            )
        
        # Créer l'invitation
        invitation_code = str(uuid.uuid4())[:8].upper()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        invitation = PropertyGroupInvitation(
            group_id=group_id,
            invited_user_id=invited_user.id,
            invited_by_id=invited_by_id,
            invitation_code=invitation_code,
            invitation_message=message,
            expires_at=expires_at
        )
        
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        
        return invitation
    
    @staticmethod
    def accept_group_invitation(
        db: Session,
        invitation_code: str,
        user_id: int
    ) -> PropertyGroupMember:
        """
        Accepte une invitation à un groupe de multipropriété
        """
        # Trouver l'invitation
        invitation = db.query(PropertyGroupInvitation).filter(
            PropertyGroupInvitation.invitation_code == invitation_code,
            PropertyGroupInvitation.invited_user_id == user_id,
            PropertyGroupInvitation.status == "pending"
        ).first()
        
        if not invitation:
            raise ValueError("Invitation non trouvée ou déjà traitée")
        
        if invitation.is_expired:
            invitation.status = "expired"
            db.commit()
            raise ValueError("Invitation expirée")
        
        # Vérifier que le groupe est toujours actif
        if invitation.group.group_status != PropertyGroupStatus.ACTIVE:
            raise ValueError("Le groupe n'est plus actif")
        
        # Créer ou mettre à jour le membership
        existing_member = db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == invitation.group_id,
            PropertyGroupMember.user_id == user_id
        ).first()
        
        if existing_member:
            # Réactiver un ancien membre
            existing_member.membership_status = MembershipStatus.ACTIVE
            existing_member.joined_at = datetime.utcnow()
            member = existing_member
        else:
            # Créer un nouveau membre
            member = PropertyGroupMember(
                group_id=invitation.group_id,
                user_id=user_id,
                membership_status=MembershipStatus.ACTIVE,
                role_in_group="member",
                invited_by_id=invitation.invited_by_id,
                invitation_message=invitation.invitation_message,
                joined_at=datetime.utcnow()
            )
            db.add(member)
        
        # Marquer l'invitation comme acceptée
        invitation.status = "accepted"
        invitation.responded_at = datetime.utcnow()
        
        db.commit()
        db.refresh(member)
        
        return member
    
    @staticmethod
    def add_apartment_to_group(
        db: Session,
        apartment_id: int,
        group_id: int,
        user_id: int
    ) -> bool:
        """
        Ajoute un appartement à un groupe de multipropriété
        """
        # Vérifier que l'utilisateur est le propriétaire de l'appartement
        apartment_link = db.query(ApartmentUserLink).filter(
            ApartmentUserLink.apartment_id == apartment_id,
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.role == UserRole.owner
        ).first()
        
        if not apartment_link:
            raise PermissionErrorHandler.access_denied("Vous n'êtes pas propriétaire de cet appartement")
        
        apartment = apartment_link.apartment
        
        # Vérifier que l'appartement n'est pas déjà dans un groupe
        if apartment.property_group_id:
            raise ValueError("L'appartement est déjà dans un groupe de multipropriété")
        
        # Vérifier que l'utilisateur peut gérer ce groupe
        group_member = db.query(PropertyGroupMember).filter(
            PropertyGroupMember.group_id == group_id,
            PropertyGroupMember.user_id == user_id,
            PropertyGroupMember.membership_status == MembershipStatus.ACTIVE
        ).first()
        
        if not group_member or not group_member.can_manage_apartments:
            raise PermissionErrorHandler.access_denied("Vous n'avez pas les permissions pour gérer les appartements de ce groupe")
        
        # Ajouter l'appartement au groupe
        apartment.property_group_id = group_id
        db.commit()
        
        return True
    
    @staticmethod
    def get_user_multipropriete_dashboard(db: Session, user_id: int) -> MultiproprieteDashboard:
        """
        Récupère le tableau de bord complet de multipropriété pour un utilisateur
        """
        quotas = MultiproprietService.get_user_apartment_quotas(db, user_id)
        
        # Groupes sponsorisés
        sponsored_groups = []
        user_sponsored_groups = db.query(PropertyGroup).filter(
            PropertyGroup.sponsor_id == user_id,
            PropertyGroup.group_status == PropertyGroupStatus.ACTIVE
        ).all()
        
        for group in user_sponsored_groups:
            sponsored_groups.append({
                "id": group.id,
                "name": group.name,
                "type": group.group_type,
                "members_count": group.active_members_count,
                "apartments_count": group.apartments_count,
                "created_at": group.created_at
            })
        
        # Groupes où l'utilisateur est membre
        member_groups = []
        user_memberships = db.query(PropertyGroupMember).filter(
            PropertyGroupMember.user_id == user_id,
            PropertyGroupMember.membership_status == MembershipStatus.ACTIVE
        ).join(PropertyGroup).filter(
            PropertyGroup.sponsor_id != user_id,  # Pas ses propres groupes
            PropertyGroup.group_status == PropertyGroupStatus.ACTIVE
        ).all()
        
        for membership in user_memberships:
            group = membership.group
            member_groups.append({
                "id": group.id,
                "name": group.name,
                "type": group.group_type,
                "sponsor_email": group.sponsor.email,
                "role": membership.role_in_group,
                "apartments_count": group.apartments_count,
                "joined_at": membership.joined_at
            })
        
        return MultiproprieteDashboard(
            personal_apartments=quotas["personal_apartments"],
            sponsored_apartments=quotas["sponsored_apartments"],
            accessible_apartments=quotas["accessible_via_groups"],
            personal_quota_used=quotas["personal_apartments"],
            personal_quota_max=quotas["personal_quota"],
            sponsored_groups=sponsored_groups,
            member_groups=member_groups,
            can_create_groups=quotas["can_sponsor_groups"]
        )
    
    @staticmethod
    def suspend_group_if_sponsor_not_premium(db: Session, group_id: int) -> bool:
        """
        Suspend un groupe si le sponsor n'a plus d'abonnement Premium
        """
        group = db.query(PropertyGroup).filter(PropertyGroup.id == group_id).first()
        if not group:
            return False
        
        # Vérifier le statut d'abonnement du sponsor
        subscription = SubscriptionService.get_user_subscription(db, group.sponsor_id)
        is_premium = subscription.get("type") == SubscriptionType.PREMIUM
        
        if not is_premium and group.group_status == PropertyGroupStatus.ACTIVE:
            # Suspendre le groupe
            group.group_status = PropertyGroupStatus.SUSPENDED
            db.commit()
            return True
        
        elif is_premium and group.group_status == PropertyGroupStatus.SUSPENDED:
            # Réactiver le groupe
            group.group_status = PropertyGroupStatus.ACTIVE
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def get_user_accessible_apartments(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Récupère tous les appartements accessibles par un utilisateur (personnels + groupes)
        """
        apartments_data = []
        
        # Appartements personnels
        personal_apartments = db.query(Apartment).join(ApartmentUserLink).filter(
            ApartmentUserLink.user_id == user_id,
            Apartment.property_group_id.is_(None)
        ).all()
        
        for apt in personal_apartments:
            apartments_data.append({
                "apartment": apt,
                "access_type": "personal",
                "role": "owner",
                "group_name": None,
                "sponsor_email": None
            })
        
        # Appartements via groupes sponsorisés
        sponsored_apartments = db.query(Apartment).join(PropertyGroup).filter(
            PropertyGroup.sponsor_id == user_id,
            PropertyGroup.group_status == PropertyGroupStatus.ACTIVE,
            Apartment.property_group_id == PropertyGroup.id
        ).all()
        
        for apt in sponsored_apartments:
            apartments_data.append({
                "apartment": apt,
                "access_type": "sponsored",
                "role": "sponsor",
                "group_name": apt.property_group.name,
                "sponsor_email": apt.property_group.sponsor.email
            })
        
        # Appartements via memberships
        member_apartments = db.query(Apartment).join(PropertyGroup).join(
            PropertyGroupMember, PropertyGroup.id == PropertyGroupMember.group_id
        ).filter(
            PropertyGroupMember.user_id == user_id,
            PropertyGroupMember.membership_status == MembershipStatus.ACTIVE,
            PropertyGroup.group_status == PropertyGroupStatus.ACTIVE,
            PropertyGroup.sponsor_id != user_id
        ).all()
        
        for apt in member_apartments:
            # Trouver le rôle dans le groupe
            membership = next(
                (m for m in apt.property_group.members 
                 if m.user_id == user_id and m.membership_status == MembershipStatus.ACTIVE),
                None
            )
            
            apartments_data.append({
                "apartment": apt,
                "access_type": "member",
                "role": membership.role_in_group if membership else "member",
                "group_name": apt.property_group.name,
                "sponsor_email": apt.property_group.sponsor.email
            })
        
        return apartments_data