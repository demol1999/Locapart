"""
Routes API pour la gestion des paiements Stripe
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from database import get_db
from auth import get_current_user
from models import UserAuth, UserSubscription, Payment, PaymentStatus
from schemas import (
    UserSubscriptionOut, CheckoutSessionCreate, PaymentOut, PaymentHistoryFilter,
    SubscriptionUpgradeRequest, ApartmentLimitCheck, SubscriptionStats
)
from stripe_service import StripeService
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

@router.get("/subscription", response_model=UserSubscriptionOut)
async def get_user_subscription(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'abonnement de l'utilisateur connecté"""
    stripe_service = StripeService(db)
    subscription = stripe_service.get_subscription_info(current_user.id, db)
    
    if not subscription:
        # Créer un abonnement gratuit par défaut
        subscription = UserSubscription(user_id=current_user.id)
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return subscription

@router.get("/apartment-limit", response_model=ApartmentLimitCheck)
async def check_apartment_limit(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vérifie les limites d'appartements pour l'utilisateur"""
    stripe_service = StripeService(db)
    limit_info = stripe_service.check_apartment_limit(current_user.id, db)
    return limit_info

@router.post("/create-checkout-session")
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée une session de paiement Stripe Checkout"""
    stripe_service = StripeService(db)
    
    try:
        session = stripe_service.create_checkout_session(
            user=current_user,
            subscription_type=checkout_data.subscription_type,
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url,
            db=db
        )
        
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Annule l'abonnement de l'utilisateur"""
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Aucun abonnement trouvé")
    
    if not subscription.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="Pas d'abonnement Stripe actif")
    
    stripe_service = StripeService(db)
    success = stripe_service.cancel_subscription(subscription, db)
    
    if success:
        return {"message": "Abonnement annulé avec succès"}
    else:
        raise HTTPException(status_code=400, detail="Erreur lors de l'annulation")

@router.get("/payments", response_model=List[PaymentOut])
async def get_payment_history(
    filter_params: PaymentHistoryFilter = Depends(),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'historique des paiements de l'utilisateur"""
    query = db.query(Payment).filter(Payment.user_id == current_user.id)
    
    if filter_params.status:
        query = query.filter(Payment.status == filter_params.status)
    
    if filter_params.start_date:
        query = query.filter(Payment.created_at >= filter_params.start_date)
    
    if filter_params.end_date:
        query = query.filter(Payment.created_at <= filter_params.end_date)
    
    payments = query.order_by(Payment.created_at.desc()).offset(filter_params.offset).limit(filter_params.limit).all()
    return payments

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Endpoint pour les webhooks Stripe"""
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Signature manquante")
    
    stripe_service = StripeService(db)
    
    try:
        result = stripe_service.handle_webhook(payload, signature, db)
        
        # Log de l'événement traité
        audit_logger = AuditLogger(db)
        audit_logger.log_action(
            user_id=None,
            action="UPDATE",
            entity_type="PAYMENT",
            description=f"Webhook Stripe traité: {result['event_type']}",
            details=json.dumps(result)
        )
        
        return result
        
    except Exception as e:
        # Log de l'erreur
        audit_logger = AuditLogger(db)
        audit_logger.log_action(
            user_id=None,
            action="ERROR",
            entity_type="PAYMENT",
            description=f"Erreur webhook Stripe: {str(e)}",
            endpoint="/api/stripe/webhook"
        )
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats", response_model=SubscriptionStats)
async def get_subscription_stats(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Statistiques des abonnements (pour les admins)"""
    # TODO: Ajouter vérification admin
    
    # Compter les utilisateurs par type d'abonnement
    total_users = db.query(UserAuth).count()
    
    subscriptions = db.query(UserSubscription).all()
    free_users = sum(1 for s in subscriptions if s.subscription_type.value == "FREE")
    premium_users = sum(1 for s in subscriptions if s.subscription_type.value == "PREMIUM")
    
    active_subscriptions = sum(1 for s in subscriptions if s.status.value == "ACTIVE")
    cancelled_subscriptions = sum(1 for s in subscriptions if s.status.value == "CANCELLED")
    
    # Calculer le revenu mensuel (paiements réussis du mois dernier)
    from datetime import datetime, timedelta
    last_month = datetime.utcnow() - timedelta(days=30)
    monthly_payments = db.query(Payment).filter(
        Payment.status == PaymentStatus.SUCCEEDED,
        Payment.paid_at >= last_month
    ).all()
    
    monthly_revenue = sum(payment.amount for payment in monthly_payments)
    
    return SubscriptionStats(
        total_users=total_users,
        free_users=free_users,
        premium_users=premium_users,
        active_subscriptions=active_subscriptions,
        cancelled_subscriptions=cancelled_subscriptions,
        monthly_revenue=monthly_revenue
    )

@router.get("/publishable-key")
async def get_publishable_key():
    """Récupère la clé publique Stripe pour le frontend"""
    import os
    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    
    if not publishable_key:
        raise HTTPException(status_code=500, detail="Clé publique Stripe non configurée")
    
    return {"publishable_key": publishable_key}