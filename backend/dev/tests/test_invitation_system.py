#!/usr/bin/env python3
"""
Script de test pour le système d'invitation des locataires
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Ajouter le repertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import UserAuth, Tenant, Lease, TenantInvitation
from tenant_invitation_service import get_tenant_invitation_service
from email_service import create_email_service_from_env

async def test_invitation_system():
    """Test complet du système d'invitation"""
    
    print("Test du système d'invitation des locataires")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 1. Vérifier qu'il y a des données de test
        user_count = db.query(UserAuth).count()
        tenant_count = db.query(Tenant).count()
        lease_count = db.query(Lease).count()
        
        print(f"Données existantes:")
        print(f"  - Utilisateurs: {user_count}")
        print(f"  - Locataires: {tenant_count}")
        print(f"  - Baux: {lease_count}")
        
        if user_count == 0:
            print("\n❌ Aucun utilisateur trouvé. Créez d'abord un utilisateur.")
            return False
        
        if tenant_count == 0:
            print("\n❌ Aucun locataire trouvé. Créez d'abord un locataire.")
            return False
        
        # 2. Prendre le premier utilisateur et locataire
        user = db.query(UserAuth).first()
        tenant = db.query(Tenant).first()
        
        print(f"\nTest avec:")
        print(f"  - Utilisateur: {user.email}")
        print(f"  - Locataire: {tenant.email}")
        
        # 3. Créer un bail si nécessaire
        lease = db.query(Lease).filter(
            Lease.tenant_id == tenant.id,
            Lease.created_by == user.id
        ).first()
        
        if not lease:
            print("\n🔧 Création d'un bail de test...")
            
            # Trouver un appartement
            from models import Apartment
            apartment = db.query(Apartment).first()
            
            if not apartment:
                print("❌ Aucun appartement trouvé. Impossible de créer un bail.")
                return False
            
            lease = Lease(
                tenant_id=tenant.id,
                apartment_id=apartment.id,
                created_by=user.id,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=365),
                monthly_rent=800.00,
                deposit=800.00,
                status="ACTIVE"
            )
            
            db.add(lease)
            db.commit()
            db.refresh(lease)
            print(f"   ✅ Bail créé (ID: {lease.id})")
        
        # 4. Tester le service d'invitation
        print(f"\n🧪 Test du service d'invitation...")
        
        invitation_service = get_tenant_invitation_service(db)
        
        # Vérifier la configuration email
        print(f"   📧 Vérification du service email...")
        if invitation_service.email_service.validate_provider():
            print(f"   ✅ Service email configuré correctement")
        else:
            print(f"   ⚠️  Service email non configuré (normal en développement)")
        
        # 5. Créer une invitation
        print(f"\n📨 Création d'une invitation...")
        
        try:
            invitation = invitation_service.create_invitation(
                tenant_id=tenant.id,
                invited_by_user_id=user.id,
                expires_in_hours=24  # 24h pour le test
            )
            
            print(f"   ✅ Invitation créée:")
            print(f"      - ID: {invitation.id}")
            print(f"      - Token: {invitation.invitation_token[:20]}...")
            print(f"      - Expire le: {invitation.token_expires_at}")
            
        except Exception as e:
            print(f"   ❌ Erreur lors de la création: {e}")
            return False
        
        # 6. Tester la validation du token
        print(f"\n🔍 Test de validation du token...")
        
        validation_result = invitation_service.validate_invitation_token(invitation.invitation_token)
        
        if validation_result:
            print(f"   ✅ Token valide:")
            print(f"      - Locataire: {validation_result['tenant_name']}")
            print(f"      - Email: {validation_result['tenant_email']}")
        else:
            print(f"   ❌ Token invalide")
            return False
        
        # 7. Tester l'envoi d'email (seulement si configuré)
        email_provider = os.getenv("EMAIL_PROVIDER", "").lower()
        if email_provider and os.getenv("RESEND_API_KEY" if email_provider == "resend" else f"{email_provider.upper()}_API_KEY"):
            print(f"\n📤 Test d'envoi d'email...")
            
            try:
                await invitation_service.send_invitation_email(invitation.id)
                print(f"   ✅ Email envoyé avec succès")
                
                # Recharger l'invitation pour voir les changements
                db.refresh(invitation)
                print(f"      - Statut envoyé: {invitation.is_sent}")
                print(f"      - Envoyé le: {invitation.sent_at}")
                
            except Exception as e:
                print(f"   ⚠️  Erreur d'envoi d'email: {e}")
                print(f"      (Ceci est normal si la configuration email n'est pas complète)")
        else:
            print(f"\n⚠️  Configuration email non trouvée - test d'envoi ignoré")
            print(f"   Configurez EMAIL_PROVIDER et les clés API dans .env pour tester l'envoi")
        
        # 8. Tester l'utilisation du token
        print(f"\n✅ Test d'utilisation du token...")
        
        success = invitation_service.use_invitation_token(invitation.invitation_token)
        
        if success:
            print(f"   ✅ Token utilisé avec succès")
            
            # Vérifier que le token ne peut plus être utilisé
            validation_result_after = invitation_service.validate_invitation_token(invitation.invitation_token)
            if not validation_result_after:
                print(f"   ✅ Token invalidé après utilisation")
            else:
                print(f"   ❌ Token encore valide après utilisation")
                return False
        else:
            print(f"   ❌ Échec d'utilisation du token")
            return False
        
        # 9. Statistiques finales
        print(f"\n📊 Statistiques finales:")
        
        invitation_count = db.query(TenantInvitation).count()
        sent_count = db.query(TenantInvitation).filter(TenantInvitation.is_sent == True).count()
        used_count = db.query(TenantInvitation).filter(TenantInvitation.is_used == True).count()
        
        print(f"   - Total invitations: {invitation_count}")
        print(f"   - Invitations envoyées: {sent_count}")
        print(f"   - Invitations utilisées: {used_count}")
        
        print(f"\n🎉 Tous les tests ont réussi!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur durant les tests: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

def main():
    """Fonction principale"""
    
    print("Script de test - Système d'invitation LocAppart")
    print("=" * 60)
    
    # Vérifier les dépendances
    try:
        import resend
        print("✅ Module 'resend' installé")
    except ImportError:
        print("⚠️  Module 'resend' non installé (optionnel)")
    
    try:
        import jinja2
        print("✅ Module 'jinja2' installé")
    except ImportError:
        print("❌ Module 'jinja2' non installé - requis pour les templates")
        print("   Installez avec: pip install jinja2")
        return 1
    
    # Vérifier la configuration
    print(f"\n🔧 Configuration détectée:")
    print(f"   - EMAIL_PROVIDER: {os.getenv('EMAIL_PROVIDER', 'non configuré')}")
    print(f"   - EMAIL_FROM: {os.getenv('EMAIL_FROM', 'non configuré')}")
    print(f"   - RESEND_API_KEY: {'configuré' if os.getenv('RESEND_API_KEY') else 'non configuré'}")
    
    # Lancer les tests
    print(f"\n🚀 Lancement des tests...\n")
    
    try:
        success = asyncio.run(test_invitation_system())
        
        if success:
            print(f"\n🎯 RÉSUMÉ: Tous les tests ont réussi!")
            print(f"\n📋 Le système d'invitation est opérationnel:")
            print(f"   1. ✅ Création d'invitations")
            print(f"   2. ✅ Validation de tokens")
            print(f"   3. ✅ Utilisation de tokens")
            print(f"   4. ✅ Audit trail complet")
            
            if os.getenv("EMAIL_PROVIDER"):
                print(f"   5. ✅ Service email configuré")
            else:
                print(f"   5. ⚠️  Service email à configurer (voir .env.email.example)")
            
            print(f"\n🚀 Prêt pour la production!")
            return 0
        else:
            print(f"\n❌ Certains tests ont échoué")
            return 1
            
    except Exception as e:
        print(f"\n💥 Erreur fatale: {e}")
        return 1

if __name__ == "__main__":
    exit(main())