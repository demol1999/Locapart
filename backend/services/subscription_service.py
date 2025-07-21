"""
Service de gestion des abonnements
Centralise la logique métier des abonnements Premium/Gratuit
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import UserAuth
from enums import SubscriptionType, SubscriptionStatus
from constants import FREE_SUBSCRIPTION_LIMITS, PREMIUM_SUBSCRIPTION_LIMITS


class SubscriptionService:
    """
    Service central pour la gestion des abonnements
    """
    
    @staticmethod
    def get_user_subscription(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère les informations d'abonnement d'un utilisateur
        """
        try:
            # Tenter d'importer UserSubscription si le modèle existe
            from models import UserSubscription
            
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if subscription and subscription.status == SubscriptionStatus.ACTIVE:
                return {
                    "type": subscription.subscription_type,
                    "status": subscription.status,
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                    "stripe_subscription_id": subscription.stripe_subscription_id
                }
        except ImportError:
            # Le modèle UserSubscription n'existe pas encore
            pass
        
        # Par défaut, abonnement gratuit
        return {
            "type": SubscriptionType.FREE,
            "status": SubscriptionStatus.ACTIVE,
            "start_date": None,
            "end_date": None,
            "stripe_subscription_id": None
        }
    
    @staticmethod
    def has_premium_subscription(db: Session, user_id: int) -> bool:
        """
        Vérifie si un utilisateur a un abonnement Premium actif
        """
        subscription = SubscriptionService.get_user_subscription(db, user_id)
        return (
            subscription.get("type") == SubscriptionType.PREMIUM and 
            subscription.get("status") == SubscriptionStatus.ACTIVE
        )
    
    @staticmethod
    def get_subscription_limits(subscription_type: str) -> Dict[str, int]:
        """
        Retourne les limites selon le type d'abonnement
        """
        if subscription_type == SubscriptionType.PREMIUM:
            return PREMIUM_SUBSCRIPTION_LIMITS.copy()
        else:
            return FREE_SUBSCRIPTION_LIMITS.copy()
    
    @staticmethod
    def get_user_usage_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Calcule les statistiques d'utilisation d'un utilisateur
        """
        from models import ApartmentUserLink, Photo, Document, Tenant
        from enums import UserRole, PhotoType
        
        # Compter les appartements personnels (hors groupes de multipropriété)
        personal_apartments_count = db.query(func.count(ApartmentUserLink.apartment_id)).join(
            "apartment"  # Relation vers Apartment
        ).filter(
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.role == UserRole.owner
        ).scalar() or 0
        
        # Compter les photos par appartement (pour vérifier les limites)
        # Cette requête est plus complexe car il faut vérifier par appartement
        
        # Compter les documents
        documents_count = db.query(func.count(Document.id)).join(
            "apartment"
        ).join(
            ApartmentUserLink, 
        ).filter(
            ApartmentUserLink.user_id == user_id
        ).scalar() or 0
        
        # Compter les locataires
        tenants_count = db.query(func.count(Tenant.id)).join(
            "apartment"
        ).join(
            ApartmentUserLink
        ).filter(
            ApartmentUserLink.user_id == user_id,
            Tenant.status == "active"
        ).scalar() or 0
        
        return {
            "personal_apartments": personal_apartments_count,
            "documents": documents_count,
            "active_tenants": tenants_count
        }
    
    @staticmethod
    def check_feature_limit(
        db: Session, 
        user_id: int, 
        feature: str, 
        current_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Vérifie si un utilisateur peut utiliser une fonctionnalité selon ses limites
        """
        subscription = SubscriptionService.get_user_subscription(db, user_id)
        limits = SubscriptionService.get_subscription_limits(subscription["type"])
        
        # Si pas de limite spécifiée, calculer la valeur actuelle
        if current_count is None:
            usage_stats = SubscriptionService.get_user_usage_stats(db, user_id)
            current_count = usage_stats.get(feature, 0)
        
        limit = limits.get(f"max_{feature}", 0)
        
        # -1 signifie illimité
        if limit == -1:
            return {
                "allowed": True,
                "current_count": current_count,
                "limit": -1,
                "remaining": -1,
                "is_unlimited": True
            }
        
        remaining = max(0, limit - current_count)
        allowed = current_count < limit
        
        return {
            "allowed": allowed,
            "current_count": current_count,
            "limit": limit,
            "remaining": remaining,
            "is_unlimited": False,
            "upgrade_required": not allowed and subscription["type"] == SubscriptionType.FREE
        }
    
    @staticmethod
    def can_user_add_apartment(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Vérifie si un utilisateur peut ajouter un appartement
        Prend en compte la multipropriété
        """
        # Importer ici pour éviter les dépendances circulaires
        from services.multipropriete_service import MultiproprietService
        
        try:
            # Utiliser le service de multipropriété si disponible
            can_add, message = MultiproprietService.can_user_add_apartment(db, user_id, "personal")
            quotas = MultiproprietService.get_user_apartment_quotas(db, user_id)
            
            return {
                "allowed": can_add,
                "message": message,
                "current_count": quotas["personal_apartments"],
                "limit": quotas["personal_quota"],
                "with_multipropriete": True
            }
        except:
            # Fallback sur la logique simple si multipropriété non disponible
            return SubscriptionService.check_feature_limit(db, user_id, "apartments")
    
    @staticmethod
    def get_upgrade_benefits() -> Dict[str, Any]:
        """
        Retourne les avantages de l'upgrade vers Premium
        """
        free_limits = FREE_SUBSCRIPTION_LIMITS
        premium_limits = PREMIUM_SUBSCRIPTION_LIMITS
        
        benefits = []
        
        for feature, free_limit in free_limits.items():
            premium_limit = premium_limits.get(feature, free_limit)
            
            if premium_limit == -1:
                benefit_text = f"{feature.replace('max_', '').replace('_', ' ').title()}: Illimité"
            else:
                benefit_text = f"{feature.replace('max_', '').replace('_', ' ').title()}: {premium_limit} (au lieu de {free_limit})"
            
            benefits.append(benefit_text)
        
        # Ajouter les fonctionnalités spéciales Premium
        benefits.extend([
            "Groupes de multipropriété illimités",
            "Sponsoring d'autres utilisateurs",
            "Support prioritaire",
            "Fonctionnalités avancées"
        ])
        
        return {
            "benefits": benefits,
            "free_limits": free_limits,
            "premium_limits": premium_limits
        }
    
    @staticmethod
    def simulate_upgrade_impact(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Simule l'impact d'un upgrade vers Premium pour un utilisateur
        """
        current_subscription = SubscriptionService.get_user_subscription(db, user_id)
        current_usage = SubscriptionService.get_user_usage_stats(db, user_id)
        
        if current_subscription["type"] == SubscriptionType.PREMIUM:
            return {"message": "Utilisateur déjà Premium"}
        
        # Calculer les nouvelles possibilités
        current_limits = SubscriptionService.get_subscription_limits(SubscriptionType.FREE)
        premium_limits = SubscriptionService.get_subscription_limits(SubscriptionType.PREMIUM)
        
        improvements = {}
        for feature, current_limit in current_limits.items():
            premium_limit = premium_limits.get(feature, current_limit)
            current_usage_value = current_usage.get(feature.replace("max_", ""), 0)
            
            if premium_limit == -1:
                improvements[feature] = {
                    "current_limit": current_limit,
                    "new_limit": "Illimité",
                    "current_usage": current_usage_value,
                    "additional_capacity": "Illimité"
                }
            else:
                additional = premium_limit - current_limit
                improvements[feature] = {
                    "current_limit": current_limit,
                    "new_limit": premium_limit,
                    "current_usage": current_usage_value,
                    "additional_capacity": additional
                }
        
        return {
            "current_subscription": current_subscription["type"],
            "target_subscription": SubscriptionType.PREMIUM,
            "current_usage": current_usage,
            "improvements": improvements,
            "new_features": [
                "Création de groupes de multipropriété",
                "Sponsoring d'utilisateurs gratuits",
                "Accès aux fonctionnalités avancées"
            ]
        }