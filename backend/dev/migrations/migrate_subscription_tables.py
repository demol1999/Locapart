#!/usr/bin/env python3
"""
Script de migration pour créer les tables d'abonnement et de paiement Stripe
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine, SessionLocal
from models import Base, UserSubscription, Payment, SubscriptionType, SubscriptionStatus
import models

def create_subscription_tables():
    """Crée les tables d'abonnement et de paiement"""
    print("🚀 Création des tables d'abonnement et de paiement...")
    
    try:
        # Créer toutes les tables définies dans les modèles
        Base.metadata.create_all(bind=engine)
        print("✅ Tables créées avec succès")
        
        # Créer des abonnements gratuits par défaut pour tous les utilisateurs existants
        create_default_subscriptions()
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return False
    
    return True

def create_default_subscriptions():
    """Crée des abonnements gratuits par défaut pour tous les utilisateurs existants"""
    print("📝 Création des abonnements par défaut...")
    
    db = SessionLocal()
    try:
        # Récupérer tous les utilisateurs qui n'ont pas d'abonnement
        users_without_subscription = db.execute(text("""
            SELECT ua.id, ua.email 
            FROM user_auth ua 
            LEFT JOIN user_subscriptions us ON ua.id = us.user_id 
            WHERE us.id IS NULL
        """)).fetchall()
        
        print(f"📊 {len(users_without_subscription)} utilisateurs sans abonnement trouvés")
        
        for user_id, email in users_without_subscription:
            # Créer un abonnement gratuit par défaut
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type=SubscriptionType.FREE,
                status=SubscriptionStatus.ACTIVE,
                apartment_limit=3
            )
            db.add(subscription)
            print(f"✅ Abonnement gratuit créé pour l'utilisateur {email} (ID: {user_id})")
        
        db.commit()
        print(f"✅ {len(users_without_subscription)} abonnements par défaut créés")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des abonnements par défaut: {e}")
        db.rollback()
    finally:
        db.close()

def verify_tables():
    """Vérifie que les tables ont été créées correctement"""
    print("🔍 Vérification des tables...")
    
    db = SessionLocal()
    try:
        # Vérifier la table user_subscriptions
        subscription_count = db.query(UserSubscription).count()
        print(f"📊 Nombre d'abonnements: {subscription_count}")
        
        # Vérifier la table payments
        payment_count = db.query(Payment).count()
        print(f"💳 Nombre de paiements: {payment_count}")
        
        # Afficher quelques statistiques
        free_subscriptions = db.query(UserSubscription).filter(
            UserSubscription.subscription_type == SubscriptionType.FREE
        ).count()
        
        premium_subscriptions = db.query(UserSubscription).filter(
            UserSubscription.subscription_type == SubscriptionType.PREMIUM
        ).count()
        
        print(f"📈 Abonnements gratuits: {free_subscriptions}")
        print(f"🌟 Abonnements premium: {premium_subscriptions}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False
    finally:
        db.close()

def main():
    """Fonction principale de migration"""
    print("=" * 50)
    print("🔄 MIGRATION DES TABLES D'ABONNEMENT")
    print("=" * 50)
    
    # Étape 1: Créer les tables
    if not create_subscription_tables():
        print("❌ Échec de la migration")
        return
    
    # Étape 2: Vérifier les tables
    if not verify_tables():
        print("⚠️  Tables créées mais vérification échouée")
        return
    
    print("=" * 50)
    print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
    print("=" * 50)
    print()
    print("📋 Prochaines étapes:")
    print("1. Configurer les variables d'environnement Stripe:")
    print("   - STRIPE_SECRET_KEY")
    print("   - STRIPE_PUBLISHABLE_KEY") 
    print("   - STRIPE_WEBHOOK_SECRET")
    print("   - STRIPE_PREMIUM_PRICE_ID")
    print()
    print("2. Créer un produit et prix dans le dashboard Stripe")
    print("3. Configurer les webhooks Stripe vers /api/stripe/webhook")
    print("4. Tester le flux de paiement")

if __name__ == "__main__":
    main()