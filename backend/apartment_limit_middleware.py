"""
Middleware pour vérifier les limites d'appartements selon l'abonnement
"""
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import UserAuth, UserSubscription, ApartmentUserLink, SubscriptionType, SubscriptionStatus
from auth import get_current_user


class ApartmentLimitChecker:
    """Service de vérification des limites d'appartements (Single Responsibility)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_subscription(self, user_id: int) -> UserSubscription:
        """Récupère l'abonnement de l'utilisateur"""
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id
        ).first()
        
        if not subscription:
            # Créer un abonnement gratuit par défaut
            subscription = UserSubscription(user_id=user_id)
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
        
        return subscription
    
    def count_user_apartments(self, user_id: int) -> int:
        """Compte le nombre d'appartements de l'utilisateur"""
        return self.db.query(ApartmentUserLink).filter(
            ApartmentUserLink.user_id == user_id
        ).count()
    
    def can_add_apartment(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur peut ajouter un appartement"""
        subscription = self.get_user_subscription(user_id)
        
        # Si l'abonnement n'est pas actif, interdire
        if subscription.status != SubscriptionStatus.ACTIVE:
            return False
        
        # Si abonnement premium, autoriser (limite illimitée)
        if subscription.subscription_type == SubscriptionType.PREMIUM:
            return True
        
        # Pour l'abonnement gratuit, vérifier la limite
        current_count = self.count_user_apartments(user_id)
        return current_count < subscription.apartment_limit
    
    def get_limit_info(self, user_id: int) -> dict:
        """Retourne les informations sur les limites"""
        subscription = self.get_user_subscription(user_id)
        current_count = self.count_user_apartments(user_id)
        
        can_add = self.can_add_apartment(user_id)
        needs_upgrade = (
            not can_add and 
            subscription.subscription_type == SubscriptionType.FREE and
            subscription.status == SubscriptionStatus.ACTIVE
        )
        
        return {
            "current_count": current_count,
            "limit": subscription.apartment_limit,
            "can_add": can_add,
            "subscription_type": subscription.subscription_type.value,
            "subscription_status": subscription.status.value,
            "needs_upgrade": needs_upgrade
        }


def check_apartment_limit(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Middleware dependency pour vérifier les limites d'appartements.
    À utiliser dans les endpoints de création d'appartements.
    """
    checker = ApartmentLimitChecker(db)
    
    if not checker.can_add_apartment(current_user.id):
        limit_info = checker.get_limit_info(current_user.id)
        
        if limit_info["subscription_status"] != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "subscription_inactive",
                    "message": "Votre abonnement n'est pas actif",
                    "limit_info": limit_info
                }
            )
        
        if limit_info["needs_upgrade"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "apartment_limit_exceeded",
                    "message": f"Limite d'appartements atteinte ({limit_info['current_count']}/{limit_info['limit']}). Passez à l'abonnement Premium pour ajouter plus d'appartements.",
                    "limit_info": limit_info
                }
            )
        
        # Autre cas d'erreur
        raise HTTPException(
            status_code=403,
            detail={
                "error": "cannot_add_apartment",
                "message": "Impossible d'ajouter un appartement",
                "limit_info": limit_info
            }
        )
    
    return True


def get_apartment_limit_info(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Dependency pour récupérer les informations sur les limites sans bloquer.
    Utile pour afficher les limites dans l'interface.
    """
    checker = ApartmentLimitChecker(db)
    return checker.get_limit_info(current_user.id)


class SubscriptionGuard:
    """Classe pour protéger différentes fonctionnalités selon l'abonnement"""
    
    def __init__(self, db: Session):
        self.db = db
        self.checker = ApartmentLimitChecker(db)
    
    def require_premium(self, user_id: int) -> bool:
        """Vérifie que l'utilisateur a un abonnement premium actif"""
        subscription = self.checker.get_user_subscription(user_id)
        return (
            subscription.subscription_type == SubscriptionType.PREMIUM and
            subscription.status == SubscriptionStatus.ACTIVE
        )
    
    def require_active_subscription(self, user_id: int) -> bool:
        """Vérifie que l'utilisateur a un abonnement actif"""
        subscription = self.checker.get_user_subscription(user_id)
        return subscription.status == SubscriptionStatus.ACTIVE


def require_premium_subscription(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Middleware pour les fonctionnalités premium uniquement"""
    guard = SubscriptionGuard(db)
    
    if not guard.require_premium(current_user.id):
        subscription = guard.checker.get_user_subscription(current_user.id)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "premium_required",
                "message": "Cette fonctionnalité nécessite un abonnement Premium",
                "current_subscription": subscription.subscription_type.value,
                "subscription_status": subscription.status.value
            }
        )
    
    return True


def require_active_subscription(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Middleware pour s'assurer que l'abonnement est actif"""
    guard = SubscriptionGuard(db)
    
    if not guard.require_active_subscription(current_user.id):
        subscription = guard.checker.get_user_subscription(current_user.id)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "subscription_inactive",
                "message": "Votre abonnement n'est pas actif",
                "subscription_status": subscription.status.value
            }
        )
    
    return True