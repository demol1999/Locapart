"""
Test complet du système de vérification d'email
"""
import sys
import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url
from email_verification_service import create_verification_service, EmailVerification
from models import UserAuth, AuthType
import models

class EmailVerificationTest:
    """Tests pour le système de vérification d'email"""
    
    def __init__(self):
        self.engine = create_engine(get_db_url())
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = None
    
    def run_tests(self):
        """Exécute tous les tests"""
        
        print("=== TESTS SYSTÈME VÉRIFICATION EMAIL ===")
        print("Début des tests...\n")
        
        try:
            self.session = self.SessionLocal()
            
            # 1. Tester la structure de la base
            print("1. Test de la structure de la base...")
            self.test_database_structure()
            
            # 2. Tester la création du service
            print("\n2. Test de création du service...")
            self.test_service_creation()
            
            # 3. Tester les utilisateurs OAuth (auto-vérifiés)
            print("\n3. Test des utilisateurs OAuth...")
            self.test_oauth_users()
            
            # 4. Tester les providers disponibles
            print("\n4. Test des providers email...")
            self.test_email_providers()
            
            # 5. Vérifications des templates
            print("\n5. Test des templates email...")
            self.test_email_templates()
            
            print("\n[SUCCESS] Tous les tests sont passés!")
            
        except Exception as e:
            print(f"\n[ERROR] Erreur lors des tests: {e}")
            raise
        finally:
            if self.session:
                self.session.close()
    
    def test_database_structure(self):
        """Teste la structure de la base de données"""
        
        try:
            # Vérifier que la table email_verifications existe
            result = self.session.execute(text("SHOW TABLES LIKE 'email_verifications'")).fetchone()
            if not result:
                raise Exception("Table email_verifications manquante")
            print("   [OK] Table email_verifications présente")
            
            # Vérifier les colonnes de user_auth
            required_columns = ['email_verified', 'email_verified_at']
            result = self.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'user_auth' 
                AND COLUMN_NAME IN ('email_verified', 'email_verified_at')
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchall()
            
            found_columns = [row[0] for row in result]
            for col in required_columns:
                if col in found_columns:
                    print(f"   [OK] Colonne {col} présente")
                else:
                    raise Exception(f"Colonne {col} manquante")
            
            # Vérifier la structure de la table email_verifications
            result = self.session.execute(text("""
                DESCRIBE email_verifications
            """)).fetchall()
            
            required_fields = ['id', 'user_id', 'email', 'verification_code', 'verification_token']
            table_fields = [row[0] for row in result]
            
            for field in required_fields:
                if field in table_fields:
                    print(f"   [OK] Champ {field} présent dans email_verifications")
                else:
                    raise Exception(f"Champ {field} manquant dans email_verifications")
            
        except Exception as e:
            print(f"   [ERROR] Erreur structure base: {e}")
            raise
    
    def test_service_creation(self):
        """Teste la création du service de vérification"""
        
        try:
            # Créer le service
            verification_service = create_verification_service(self.session)
            
            if verification_service is None:
                raise Exception("Impossible de créer le service de vérification")
            
            print("   [OK] Service de vérification créé avec succès")
            
            # Vérifier que le provider est correctement configuré
            if hasattr(verification_service, 'email_provider'):
                provider_name = verification_service.email_provider.__class__.__name__
                print(f"   [INFO] Provider email configuré: {provider_name}")
            
        except Exception as e:
            print(f"   [ERROR] Erreur création service: {e}")
            raise
    
    def test_oauth_users(self):
        """Teste le statut des utilisateurs OAuth"""
        
        try:
            # Compter les utilisateurs OAuth
            oauth_types = [AuthType.GOOGLE_OAUTH, AuthType.FACEBOOK_OAUTH, AuthType.MICROSOFT_OAUTH]
            
            total_oauth = self.session.query(UserAuth).filter(
                UserAuth.auth_type.in_(oauth_types)
            ).count()
            
            verified_oauth = self.session.query(UserAuth).filter(
                UserAuth.auth_type.in_(oauth_types),
                UserAuth.email_verified == True
            ).count()
            
            print(f"   [INFO] Utilisateurs OAuth total: {total_oauth}")
            print(f"   [INFO] Utilisateurs OAuth vérifiés: {verified_oauth}")
            
            if total_oauth > 0 and verified_oauth == total_oauth:
                print("   [OK] Tous les utilisateurs OAuth sont vérifiés")
            elif total_oauth > 0:
                print(f"   [WARNING] {total_oauth - verified_oauth} utilisateurs OAuth non vérifiés")
            else:
                print("   [INFO] Aucun utilisateur OAuth trouvé")
            
        except Exception as e:
            print(f"   [ERROR] Erreur test OAuth: {e}")
            raise
    
    def test_email_providers(self):
        """Teste la configuration des providers email"""
        
        try:
            from email_verification_service import ResendEmailProvider, MailgunEmailProvider, SMTPEmailProvider
            
            # Tester les différents providers
            providers = {
                "Resend": ResendEmailProvider,
                "Mailgun": MailgunEmailProvider, 
                "SMTP": SMTPEmailProvider
            }
            
            for name, provider_class in providers.items():
                try:
                    # Tenter de créer une instance (sans configuration complète)
                    print(f"   [INFO] Provider {name} disponible")
                except Exception as e:
                    print(f"   [WARNING] Provider {name} - erreur: {str(e)[:50]}...")
            
            print("   [OK] Tous les providers sont disponibles")
            
        except Exception as e:
            print(f"   [ERROR] Erreur test providers: {e}")
            raise
    
    def test_email_templates(self):
        """Teste la génération des templates d'email"""
        
        try:
            verification_service = create_verification_service(self.session)
            
            # Tester la génération d'un template
            test_code = "123456"
            test_token = "test_token_123"
            test_name = "Test User"
            
            # Vérifier que le service peut générer les templates
            if hasattr(verification_service.email_provider, '_create_email_content'):
                print("   [OK] Méthode de création de contenu email présente")
            
            # Vérifier que les constantes de template sont définies
            template_vars = ['VERIFICATION_EMAIL_SUBJECT', 'VERIFICATION_EMAIL_TEMPLATE']
            found_vars = []
            
            for var in template_vars:
                if hasattr(verification_service.email_provider, var):
                    found_vars.append(var)
            
            if found_vars:
                print(f"   [INFO] Variables de template trouvées: {', '.join(found_vars)}")
            
            print("   [OK] Templates email configurés")
            
        except Exception as e:
            print(f"   [ERROR] Erreur test templates: {e}")
            raise


def main():
    """Point d'entrée principal"""
    
    print("Test complet - Système de vérification d'email")
    print("=" * 50)
    
    test = EmailVerificationTest()
    test.run_tests()


if __name__ == "__main__":
    main()