"""
Service d'administration pour le panel admin
Gestion des utilisateurs, propriétés et statistiques
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from datetime import datetime, timedelta
import json

from models import UserAuth, Building, Apartment, ApartmentUserLink
from models_admin import AdminUser, AdminAction, UserStatusHistory, SystemSettings
from models_multipropriete import PropertyGroup, PropertyGroupMember
from enums import (
    AdminRole, UserStatus, AccountAction, UserRole, 
    SubscriptionType, AuthType
)
from services.subscription_service import SubscriptionService
from services.multipropriete_service import MultiproprietService
from error_handlers import PermissionErrorHandler, BusinessLogicErrorHandler
from audit_logger import AuditLogger


class AdminDashboardData:
    """Données du tableau de bord administrateur"""
    
    def __init__(
        self,
        total_users: int,
        active_users: int,
        premium_users: int,
        total_apartments: int,
        total_buildings: int,
        total_groups: int,
        new_users_today: int,
        new_users_week: int,
        recent_signups: List[Dict],
        user_growth: List[Dict],
        subscription_breakdown: Dict,
        system_alerts: List[Dict]
    ):
        self.total_users = total_users
        self.active_users = active_users
        self.premium_users = premium_users
        self.total_apartments = total_apartments
        self.total_buildings = total_buildings
        self.total_groups = total_groups
        self.new_users_today = new_users_today
        self.new_users_week = new_users_week
        self.recent_signups = recent_signups
        self.user_growth = user_growth
        self.subscription_breakdown = subscription_breakdown
        self.system_alerts = system_alerts


class UserDetailedInfo:
    """Informations détaillées d'un utilisateur pour l'admin"""
    
    def __init__(self, user_data: Dict, properties_data: Dict, activity_data: Dict):
        self.user_data = user_data
        self.properties_data = properties_data
        self.activity_data = activity_data


class AdminService:
    """
    Service principal pour les opérations d'administration
    """
    
    @staticmethod
    def check_admin_permission(db: Session, user_id: int, required_permission: str) -> bool:
        """
        Vérifie les permissions administrateur d'un utilisateur
        """
        admin_user = db.query(AdminUser).filter(
            AdminUser.user_id == user_id,
            AdminUser.is_active == True
        ).first()
        
        if not admin_user:
            return False
        
        return admin_user.has_permission(required_permission)
    
    @staticmethod
    def get_admin_dashboard(db: Session, admin_user_id: int) -> AdminDashboardData:
        """
        Récupère les données du tableau de bord administrateur
        """
        # Vérifier les permissions
        if not AdminService.check_admin_permission(db, admin_user_id, "view_dashboard"):
            raise PermissionErrorHandler.access_denied("Accès au tableau de bord refusé")
        
        # Statistiques générales
        total_users = db.query(func.count(UserAuth.id)).scalar()
        active_users = db.query(func.count(UserAuth.id)).filter(
            UserAuth.user_status == UserStatus.ACTIVE
        ).scalar()
        
        # Compter les utilisateurs Premium
        try:
            premium_users = 0  # À implémenter avec le service d'abonnement
        except:
            premium_users = 0
        
        total_apartments = db.query(func.count(Apartment.id)).scalar()
        total_buildings = db.query(func.count(Building.id)).scalar()
        
        try:
            total_groups = db.query(func.count(PropertyGroup.id)).scalar()
        except:
            total_groups = 0
        
        # Nouveaux utilisateurs
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        
        new_users_today = db.query(func.count(UserAuth.id)).filter(
            func.date(UserAuth.created_at) == today
        ).scalar()
        
        new_users_week = db.query(func.count(UserAuth.id)).filter(
            func.date(UserAuth.created_at) >= week_ago
        ).scalar()
        
        # Inscriptions récentes
        recent_signups = []
        recent_users = db.query(UserAuth).order_by(
            desc(UserAuth.created_at)
        ).limit(10).all()
        
        for user in recent_users:
            recent_signups.append({
                "id": user.id,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}",
                "created_at": user.created_at,
                "auth_type": user.auth_type,
                "status": user.user_status if hasattr(user, 'user_status') else "active"
            })
        
        # Croissance utilisateurs (7 derniers jours)
        user_growth = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = db.query(func.count(UserAuth.id)).filter(
                func.date(UserAuth.created_at) == date
            ).scalar()
            user_growth.append({
                "date": date.isoformat(),
                "count": count
            })
        
        # Répartition des abonnements
        subscription_breakdown = {
            "free": total_users - premium_users,
            "premium": premium_users
        }
        
        # Alertes système
        system_alerts = AdminService._get_system_alerts(db)
        
        return AdminDashboardData(
            total_users=total_users,
            active_users=active_users,
            premium_users=premium_users,
            total_apartments=total_apartments,
            total_buildings=total_buildings,
            total_groups=total_groups,
            new_users_today=new_users_today,
            new_users_week=new_users_week,
            recent_signups=recent_signups,
            user_growth=user_growth,
            subscription_breakdown=subscription_breakdown,
            system_alerts=system_alerts
        )
    
    @staticmethod
    def get_users_list(
        db: Session,
        admin_user_id: int,
        page: int = 1,
        per_page: int = 50,
        search: str = None,
        status_filter: str = None,
        subscription_filter: str = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Récupère la liste des utilisateurs avec filtres et pagination
        """
        # Vérifier les permissions
        if not AdminService.check_admin_permission(db, admin_user_id, "manage_users"):
            raise PermissionErrorHandler.access_denied("Accès à la gestion des utilisateurs refusé")
        
        # Construction de la requête de base
        query = db.query(UserAuth)
        
        # Filtres
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    UserAuth.email.ilike(search_term),
                    UserAuth.first_name.ilike(search_term),
                    UserAuth.last_name.ilike(search_term)
                )
            )
        
        if status_filter and hasattr(UserAuth, 'user_status'):
            query = query.filter(UserAuth.user_status == status_filter)
        
        # Compter le total avant pagination
        total_count = query.count()
        
        # Tri
        sort_column = getattr(UserAuth, sort_by, UserAuth.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Pagination
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        # Enrichir les données utilisateurs
        users_data = []
        for user in users:
            # Compter les appartements
            apartment_count = db.query(func.count(ApartmentUserLink.apartment_id)).filter(
                ApartmentUserLink.user_id == user.id,
                ApartmentUserLink.role == UserRole.owner
            ).scalar()
            
            # Récupérer le statut d'abonnement
            subscription = SubscriptionService.get_user_subscription(db, user.id)
            
            # Quotas multipropriété
            try:
                quotas = MultiproprietService.get_user_apartment_quotas(db, user.id)
                multipropriete_data = {
                    "personal_apartments": quotas["personal_apartments"],
                    "sponsored_apartments": quotas["sponsored_apartments"],
                    "accessible_apartments": quotas["accessible_via_groups"],
                    "can_sponsor": quotas["can_sponsor_groups"]
                }
            except:
                multipropriete_data = {
                    "personal_apartments": apartment_count,
                    "sponsored_apartments": 0,
                    "accessible_apartments": 0,
                    "can_sponsor": False
                }
            
            users_data.append({
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "created_at": user.created_at,
                "auth_type": user.auth_type,
                "email_verified": user.email_verified,
                "user_status": getattr(user, 'user_status', 'active'),
                "subscription_type": subscription["type"],
                "subscription_status": subscription["status"],
                "apartment_count": apartment_count,
                "multipropriete": multipropriete_data,
                "last_login": getattr(user, 'last_login_at', None),
                "full_address": getattr(user, 'full_address', '')
            })
        
        return {
            "users": users_data,
            "pagination": {
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "pages": (total_count + per_page - 1) // per_page
            },
            "filters": {
                "search": search,
                "status_filter": status_filter,
                "subscription_filter": subscription_filter,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
    
    @staticmethod
    def get_user_detailed_info(db: Session, admin_user_id: int, target_user_id: int) -> UserDetailedInfo:
        """
        Récupère les informations détaillées d'un utilisateur
        """
        # Vérifier les permissions
        if not AdminService.check_admin_permission(db, admin_user_id, "manage_users"):
            raise PermissionErrorHandler.access_denied("Accès aux détails utilisateur refusé")
        
        # Récupérer l'utilisateur
        user = db.query(UserAuth).filter(UserAuth.id == target_user_id).first()
        if not user:
            raise ValueError("Utilisateur non trouvé")
        
        # Données utilisateur de base
        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "created_at": user.created_at,
            "auth_type": user.auth_type,
            "email_verified": user.email_verified,
            "email_verified_at": user.email_verified_at,
            "user_status": getattr(user, 'user_status', 'active'),
            "admin_notes": getattr(user, 'admin_notes', ''),
            "suspension_reason": getattr(user, 'suspension_reason', ''),
            "suspension_expires_at": getattr(user, 'suspension_expires_at', None),
            "address": {
                "street_number": user.street_number,
                "street_name": user.street_name,
                "complement": user.complement,
                "postal_code": user.postal_code,
                "city": user.city,
                "country": user.country
            }
        }
        
        # Données des propriétés
        properties_data = AdminService._get_user_properties_info(db, target_user_id)
        
        # Données d'activité
        activity_data = AdminService._get_user_activity_info(db, target_user_id)
        
        return UserDetailedInfo(user_data, properties_data, activity_data)
    
    @staticmethod
    def perform_user_action(
        db: Session,
        admin_user_id: int,
        target_user_id: int,
        action: AccountAction,
        reason: str = None,
        duration_days: int = None
    ) -> bool:
        """
        Effectue une action administrative sur un utilisateur
        """
        # Vérifier les permissions
        if not AdminService.check_admin_permission(db, admin_user_id, "manage_users"):
            raise PermissionErrorHandler.access_denied("Permission refusée pour cette action")
        
        # Récupérer l'utilisateur cible
        target_user = db.query(UserAuth).filter(UserAuth.id == target_user_id).first()
        if not target_user:
            raise ValueError("Utilisateur non trouvé")
        
        # Récupérer l'admin
        admin_user = db.query(AdminUser).filter(AdminUser.user_id == admin_user_id).first()
        if not admin_user:
            raise ValueError("Administrateur non trouvé")
        
        # Sauvegarder l'état avant
        before_data = {
            "user_status": getattr(target_user, 'user_status', 'active'),
            "email_verified": target_user.email_verified,
            "suspension_reason": getattr(target_user, 'suspension_reason', None),
            "suspension_expires_at": getattr(target_user, 'suspension_expires_at', None)
        }
        
        # Effectuer l'action
        success = AdminService._execute_user_action(db, target_user, action, reason, duration_days)
        
        if success:
            # Sauvegarder l'état après
            after_data = {
                "user_status": getattr(target_user, 'user_status', 'active'),
                "email_verified": target_user.email_verified,
                "suspension_reason": getattr(target_user, 'suspension_reason', None),
                "suspension_expires_at": getattr(target_user, 'suspension_expires_at', None)
            }
            
            # Logger l'action admin
            admin_action = AdminAction(
                admin_user_id=admin_user.id,
                target_user_id=target_user_id,
                action_type=action,
                description=f"Action {action} effectuée sur {target_user.email}",
                reason=reason,
                before_data=before_data,
                after_data=after_data
            )
            
            db.add(admin_action)
            
            # Ajouter à l'historique des statuts si changement de statut
            if before_data["user_status"] != after_data["user_status"]:
                status_history = UserStatusHistory(
                    user_id=target_user_id,
                    previous_status=before_data["user_status"],
                    new_status=after_data["user_status"],
                    reason=reason,
                    changed_by_admin_id=admin_user.id,
                    duration_days=duration_days,
                    expires_at=after_data["suspension_expires_at"]
                )
                db.add(status_history)
            
            db.commit()
        
        return success
    
    @staticmethod
    def _execute_user_action(
        db: Session,
        user: UserAuth,
        action: AccountAction,
        reason: str = None,
        duration_days: int = None
    ) -> bool:
        """
        Exécute l'action spécifique sur l'utilisateur
        """
        try:
            if action == AccountAction.ACTIVATE:
                if hasattr(user, 'user_status'):
                    user.user_status = UserStatus.ACTIVE
                user.suspension_reason = None
                user.suspension_expires_at = None
                
            elif action == AccountAction.DEACTIVATE:
                if hasattr(user, 'user_status'):
                    user.user_status = UserStatus.INACTIVE
                
            elif action == AccountAction.SUSPEND:
                if hasattr(user, 'user_status'):
                    user.user_status = UserStatus.SUSPENDED
                user.suspension_reason = reason
                if duration_days:
                    user.suspension_expires_at = datetime.utcnow() + timedelta(days=duration_days)
                
            elif action == AccountAction.UNSUSPEND:
                if hasattr(user, 'user_status'):
                    user.user_status = UserStatus.ACTIVE
                user.suspension_reason = None
                user.suspension_expires_at = None
                
            elif action == AccountAction.BAN:
                if hasattr(user, 'user_status'):
                    user.user_status = UserStatus.BANNED
                user.suspension_reason = reason
                
            elif action == AccountAction.UNBAN:
                if hasattr(user, 'user_status'):
                    user.user_status = UserStatus.ACTIVE
                user.suspension_reason = None
                
            elif action == AccountAction.FORCE_EMAIL_VERIFICATION:
                user.email_verified = True
                user.email_verified_at = datetime.utcnow()
                
            elif action == AccountAction.RESET_PASSWORD:
                # Marquer que le mot de passe doit être réinitialisé
                # L'utilisateur recevra un email de réinitialisation
                pass
                
            # Mettre à jour la date de dernière action admin
            user.last_admin_action = datetime.utcnow()
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'exécution de l'action {action}: {e}")
            return False
    
    @staticmethod
    def _get_user_properties_info(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère les informations sur les propriétés d'un utilisateur
        """
        # Appartements en propriété directe
        apartments = db.query(Apartment).join(ApartmentUserLink).filter(
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.role == UserRole.owner
        ).all()
        
        apartments_data = []
        for apt in apartments:
            apartments_data.append({
                "id": apt.id,
                "name": getattr(apt, 'name', f"Appartement {apt.id}"),
                "building_name": apt.building.name if apt.building else None,
                "type_logement": apt.type_logement,
                "floor": apt.floor,
                "is_in_group": apt.property_group_id is not None,
                "group_name": apt.property_group.name if apt.property_group else None
            })
        
        # Groupes de multipropriété
        try:
            quotas = MultiproprietService.get_user_apartment_quotas(db, user_id)
            dashboard = MultiproprietService.get_user_multipropriete_dashboard(db, user_id)
            
            multipropriete_data = {
                "personal_apartments": quotas["personal_apartments"],
                "sponsored_apartments": quotas["sponsored_apartments"],
                "accessible_apartments": quotas["accessible_via_groups"],
                "sponsored_groups": dashboard.sponsored_groups,
                "member_groups": dashboard.member_groups,
                "can_create_groups": dashboard.can_create_groups
            }
        except:
            multipropriete_data = {
                "personal_apartments": len(apartments_data),
                "sponsored_apartments": 0,
                "accessible_apartments": 0,
                "sponsored_groups": [],
                "member_groups": [],
                "can_create_groups": False
            }
        
        return {
            "apartments": apartments_data,
            "multipropriete": multipropriete_data,
            "subscription": SubscriptionService.get_user_subscription(db, user_id)
        }
    
    @staticmethod
    def _get_user_activity_info(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère les informations d'activité d'un utilisateur
        """
        # Actions administratives reçues
        admin_actions = db.query(AdminAction).filter(
            AdminAction.target_user_id == user_id
        ).order_by(desc(AdminAction.created_at)).limit(10).all()
        
        admin_actions_data = []
        for action in admin_actions:
            admin_actions_data.append({
                "id": action.id,
                "action_type": action.action_type,
                "description": action.description,
                "reason": action.reason,
                "created_at": action.created_at,
                "admin_email": action.admin_user.user.email if action.admin_user else "Système"
            })
        
        # Historique des statuts
        status_history = []
        if hasattr(UserAuth, 'status_history'):
            history = db.query(UserStatusHistory).filter(
                UserStatusHistory.user_id == user_id
            ).order_by(desc(UserStatusHistory.created_at)).limit(10).all()
            
            for h in history:
                status_history.append({
                    "id": h.id,
                    "previous_status": h.previous_status,
                    "new_status": h.new_status,
                    "reason": h.reason,
                    "created_at": h.created_at,
                    "changed_by": h.changed_by_admin.user.email if h.changed_by_admin else "Système",
                    "expires_at": h.expires_at,
                    "is_temporary": h.is_temporary
                })
        
        return {
            "admin_actions": admin_actions_data,
            "status_history": status_history,
            "login_history": [],  # À implémenter si nécessaire
            "recent_activity": []  # À implémenter si nécessaire
        }
    
    @staticmethod
    def _get_system_alerts(db: Session) -> List[Dict[str, Any]]:
        """
        Récupère les alertes système
        """
        alerts = []
        
        # Utilisateurs suspendus avec expiration proche
        try:
            expiring_suspensions = db.query(UserAuth).filter(
                UserAuth.user_status == UserStatus.SUSPENDED,
                UserAuth.suspension_expires_at <= datetime.utcnow() + timedelta(days=1),
                UserAuth.suspension_expires_at > datetime.utcnow()
            ).count()
            
            if expiring_suspensions > 0:
                alerts.append({
                    "type": "warning",
                    "title": "Suspensions expirant bientôt",
                    "message": f"{expiring_suspensions} suspension(s) expirent dans les 24h",
                    "action_url": "/admin/users?filter=suspended"
                })
        except:
            pass
        
        # Nouveaux utilisateurs non vérifiés
        try:
            unverified_count = db.query(UserAuth).filter(
                UserAuth.email_verified == False,
                UserAuth.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            if unverified_count > 10:
                alerts.append({
                    "type": "info",
                    "title": "Utilisateurs non vérifiés",
                    "message": f"{unverified_count} nouveaux utilisateurs n'ont pas vérifié leur email",
                    "action_url": "/admin/users?filter=unverified"
                })
        except:
            pass
        
        return alerts