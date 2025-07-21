"""
Service Stripe suivant les principes SOLID
"""
import os
import stripe
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import UserSubscription, Payment, UserAuth, SubscriptionType, SubscriptionStatus, PaymentStatus
from audit_logger import AuditLogger
from database import get_db

class StripeConfig:
    """Configuration Stripe (Single Responsibility)"""
    
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.premium_price_id = os.getenv("STRIPE_PREMIUM_PRICE_ID")  # ID du prix mensuel premium
        
        if not self.api_key:
            raise ValueError("STRIPE_SECRET_KEY manquant dans les variables d'environnement")
        
        stripe.api_key = self.api_key
    
    @property
    def prices(self) -> Dict[str, str]:
        """Prix Stripe par type d'abonnement"""
        return {
            SubscriptionType.PREMIUM.value: self.premium_price_id
        }

class StripeCustomerService:
    """Service de gestion des clients Stripe (Single Responsibility)"""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
    
    def create_customer(self, user: UserAuth) -> stripe.Customer:
        """Crée un client Stripe"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={
                    "user_id": str(user.id),
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            self.audit_logger.log_action(
                user_id=user.id,
                action="CREATE",
                entity_type="SUBSCRIPTION",
                description=f"Client Stripe créé: {customer.id}",
                details=json.dumps({"stripe_customer_id": customer.id})
            )
            
            return customer
            
        except stripe.error.StripeError as e:
            self.audit_logger.log_action(
                user_id=user.id,
                action="ERROR",
                entity_type="SUBSCRIPTION",
                description=f"Erreur création client Stripe: {str(e)}"
            )
            raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")
    
    def get_or_create_customer(self, user: UserAuth, subscription: UserSubscription) -> stripe.Customer:
        """Récupère ou crée un client Stripe"""
        if subscription.stripe_customer_id:
            try:
                return stripe.Customer.retrieve(subscription.stripe_customer_id)
            except stripe.error.StripeError:
                # Client introuvable, on en crée un nouveau
                pass
        
        return self.create_customer(user)

class StripeSubscriptionService:
    """Service de gestion des abonnements Stripe (Single Responsibility)"""
    
    def __init__(self, config: StripeConfig, customer_service: StripeCustomerService, audit_logger: AuditLogger):
        self.config = config
        self.customer_service = customer_service
        self.audit_logger = audit_logger
    
    def create_checkout_session(self, user: UserAuth, subscription_type: SubscriptionType, 
                              success_url: str, cancel_url: str, db: Session) -> stripe.checkout.Session:
        """Crée une session de paiement Stripe Checkout"""
        try:
            # Récupérer ou créer l'abonnement utilisateur
            subscription = db.query(UserSubscription).filter(UserSubscription.user_id == user.id).first()
            if not subscription:
                subscription = UserSubscription(user_id=user.id)
                db.add(subscription)
                db.commit()
            
            # Récupérer ou créer le client Stripe
            customer = self.customer_service.get_or_create_customer(user, subscription)
            
            # Mettre à jour l'ID client si nécessaire
            if subscription.stripe_customer_id != customer.id:
                subscription.stripe_customer_id = customer.id
                db.commit()
            
            # Créer la session checkout
            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': self.config.prices[subscription_type.value],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user.id),
                    'subscription_type': subscription_type.value
                },
                subscription_data={
                    'metadata': {
                        'user_id': str(user.id),
                        'subscription_type': subscription_type.value
                    }
                }
            )
            
            self.audit_logger.log_action(
                user_id=user.id,
                action="CREATE",
                entity_type="PAYMENT",
                description=f"Session checkout créée pour {subscription_type.value}",
                details=json.dumps({
                    "session_id": session.id,
                    "subscription_type": subscription_type.value,
                    "customer_id": customer.id
                })
            )
            
            return session
            
        except stripe.error.StripeError as e:
            self.audit_logger.log_action(
                user_id=user.id,
                action="ERROR",
                entity_type="PAYMENT",
                description=f"Erreur création session checkout: {str(e)}"
            )
            raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")
    
    def cancel_subscription(self, subscription: UserSubscription, db: Session) -> bool:
        """Annule un abonnement Stripe"""
        if not subscription.stripe_subscription_id:
            return False
        
        try:
            stripe_subscription = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            subscription.cancel_at = datetime.fromtimestamp(stripe_subscription.cancel_at)
            subscription.status = SubscriptionStatus.CANCELLED
            db.commit()
            
            self.audit_logger.log_action(
                user_id=subscription.user_id,
                action="UPDATE",
                entity_type="SUBSCRIPTION",
                description="Abonnement annulé",
                details=json.dumps({
                    "stripe_subscription_id": subscription.stripe_subscription_id,
                    "cancel_at": stripe_subscription.cancel_at
                })
            )
            
            return True
            
        except stripe.error.StripeError as e:
            self.audit_logger.log_action(
                user_id=subscription.user_id,
                action="ERROR",
                entity_type="SUBSCRIPTION",
                description=f"Erreur annulation abonnement: {str(e)}"
            )
            raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")

class StripeWebhookService:
    """Service de traitement des webhooks Stripe (Single Responsibility)"""
    
    def __init__(self, config: StripeConfig, audit_logger: AuditLogger):
        self.config = config
        self.audit_logger = audit_logger
    
    def verify_webhook(self, payload: bytes, signature: str) -> stripe.Event:
        """Vérifie la signature du webhook"""
        try:
            return stripe.Webhook.construct_event(
                payload, signature, self.config.webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Payload invalide")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Signature invalide")
    
    def handle_subscription_created(self, event_data: Dict[str, Any], db: Session):
        """Traite l'événement customer.subscription.created"""
        subscription_data = event_data['object']
        user_id = int(subscription_data['metadata'].get('user_id'))
        subscription_type = subscription_data['metadata'].get('subscription_type', 'PREMIUM')
        
        # Mettre à jour l'abonnement en base
        subscription = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
        if subscription:
            subscription.stripe_subscription_id = subscription_data['id']
            subscription.subscription_type = SubscriptionType(subscription_type)
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
            subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
            subscription.apartment_limit = -1 if subscription_type == 'PREMIUM' else 3
            db.commit()
            
            self.audit_logger.log_action(
                user_id=user_id,
                action="UPDATE",
                entity_type="SUBSCRIPTION",
                description="Abonnement Stripe activé",
                details=json.dumps(subscription_data)
            )
    
    def handle_invoice_payment_succeeded(self, event_data: Dict[str, Any], db: Session):
        """Traite l'événement invoice.payment_succeeded"""
        invoice_data = event_data['object']
        customer_id = invoice_data['customer']
        
        # Trouver l'utilisateur via le customer_id
        subscription = db.query(UserSubscription).filter(
            UserSubscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            # Créer un enregistrement de paiement
            payment = Payment(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                stripe_payment_intent_id=invoice_data['payment_intent'],
                stripe_invoice_id=invoice_data['id'],
                amount=Decimal(invoice_data['amount_paid']) / 100,  # Convertir centimes en euros
                currency=invoice_data['currency'].upper(),
                status=PaymentStatus.SUCCEEDED,
                description=f"Paiement abonnement {subscription.subscription_type.value}",
                paid_at=datetime.fromtimestamp(invoice_data['status_transitions']['paid_at']),
                stripe_event_data=json.dumps(event_data)
            )
            db.add(payment)
            
            # Mettre à jour l'abonnement
            subscription.status = SubscriptionStatus.ACTIVE
            db.commit()
            
            self.audit_logger.log_action(
                user_id=subscription.user_id,
                action="CREATE",
                entity_type="PAYMENT",
                description=f"Paiement réussi: {payment.amount}€",
                details=json.dumps({"payment_id": payment.id, "amount": str(payment.amount)})
            )

class StripeService:
    """Service principal Stripe (Facade Pattern)"""
    
    def __init__(self, db: Session):
        self.config = StripeConfig()
        self.audit_logger = AuditLogger(db)
        self.customer_service = StripeCustomerService(self.audit_logger)
        self.subscription_service = StripeSubscriptionService(self.config, self.customer_service, self.audit_logger)
        self.webhook_service = StripeWebhookService(self.config, self.audit_logger)
    
    def create_checkout_session(self, user: UserAuth, subscription_type: SubscriptionType,
                              success_url: str, cancel_url: str, db: Session) -> stripe.checkout.Session:
        """Crée une session de paiement"""
        return self.subscription_service.create_checkout_session(user, subscription_type, success_url, cancel_url, db)
    
    def cancel_subscription(self, subscription: UserSubscription, db: Session) -> bool:
        """Annule un abonnement"""
        return self.subscription_service.cancel_subscription(subscription, db)
    
    def handle_webhook(self, payload: bytes, signature: str, db: Session) -> Dict[str, Any]:
        """Traite un webhook Stripe"""
        event = self.webhook_service.verify_webhook(payload, signature)
        
        if event['type'] == 'customer.subscription.created':
            self.webhook_service.handle_subscription_created(event['data'], db)
        elif event['type'] == 'invoice.payment_succeeded':
            self.webhook_service.handle_invoice_payment_succeeded(event['data'], db)
        
        return {"status": "success", "event_type": event['type']}
    
    def get_subscription_info(self, user_id: int, db: Session) -> Optional[UserSubscription]:
        """Récupère les informations d'abonnement d'un utilisateur"""
        return db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    
    def check_apartment_limit(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Vérifie les limites d'appartements pour un utilisateur"""
        subscription = self.get_subscription_info(user_id, db)
        if not subscription:
            # Créer un abonnement gratuit par défaut
            subscription = UserSubscription(user_id=user_id)
            db.add(subscription)
            db.commit()
        
        # Compter les appartements actuels
        from models import ApartmentUserLink
        current_count = db.query(ApartmentUserLink).filter(ApartmentUserLink.user_id == user_id).count()
        
        limit = subscription.apartment_limit if subscription.apartment_limit > 0 else float('inf')
        can_add = current_count < limit
        needs_upgrade = not can_add and subscription.subscription_type == SubscriptionType.FREE
        
        return {
            "current_count": current_count,
            "limit": subscription.apartment_limit,
            "can_add": can_add,
            "subscription_type": subscription.subscription_type,
            "needs_upgrade": needs_upgrade
        }