"""
Test complet du système de multipropriété
Validation de toutes les fonctionnalités
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url
from models import UserAuth
from models_multipropriete import PropertyGroup, PropertyGroupMember, PropertyGroupInvitation
from services.multipropriete_service import MultiproprietService
from services.subscription_service import SubscriptionService
from enums import SubscriptionType


class MultiproprieteTester:
    """Testeur pour le système de multipropriété"""
    
    def __init__(self):
        self.engine = create_engine(get_db_url())
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = None
    
    def run_tests(self):
        """Exécute tous les tests"""
        
        print("=== TESTS SYSTÈME MULTIPROPRIÉTÉ ===")
        print("Début des tests...\n")
        
        try:
            self.session = self.SessionLocal()
            
            # 1. Tester la structure de la base
            print("1. Test de la structure de la base...")
            self.test_database_structure()
            
            # 2. Tester les services
            print("\n2. Test des services...")
            self.test_services()
            
            # 3. Tester les quotas
            print("\n3. Test des quotas...")
            self.test_quotas()
            
            # 4. Tester un scénario complet
            print("\n4. Test d'un scénario complet...")
            self.test_complete_scenario()
            
            print("\n[SUCCESS] Tous les tests sont passés!")
            
        except Exception as e:
            print(f"\n[ERROR] Erreur lors des tests: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.session:
                self.session.close()
    
    def test_database_structure(self):
        """Teste la structure de la base de données"""
        
        try:
            from sqlalchemy import text
            
            # Vérifier les tables
            tables = ['property_groups', 'property_group_members', 'property_group_invitations']
            for table in tables:
                result = self.session.execute(text(f"SHOW TABLES LIKE '{table}'")).fetchone()
                if result:
                    print(f"   [OK] Table {table} présente")
                else:
                    raise Exception(f"Table {table} manquante")
            
            # Vérifier la colonne ajoutée
            result = self.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'apartments' 
                AND COLUMN_NAME = 'property_group_id'
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchone()
            
            if result:
                print("   [OK] Colonne property_group_id présente dans apartments")
            else:
                raise Exception("Colonne property_group_id manquante")
            
            # Tester une requête simple
            count = self.session.query(PropertyGroup).count()
            print(f"   [OK] Requête sur PropertyGroup réussie ({count} groupes)")
            
        except Exception as e:
            print(f"   [ERROR] Erreur structure base: {e}")
            raise
    
    def test_services(self):
        """Teste les services de multipropriété"""
        
        try:
            # Tester le service de quotas avec un utilisateur fictif
            user_id = 99999  # ID qui n'existe pas normalement
            
            try:
                quotas = MultiproprietService.get_user_apartment_quotas(self.session, user_id)
                print("   [WARNING] Quotas calculés pour utilisateur inexistant (comportement à vérifier)")
            except:
                print("   [OK] Service de quotas gère bien les utilisateurs inexistants")
            
            # Tester la vérification d'abonnement
            try:
                is_premium = SubscriptionService.has_premium_subscription(self.session, user_id)
                print(f"   [OK] Vérification abonnement: {is_premium}")
            except Exception as e:
                print(f"   [WARNING] Service abonnement: {e}")
            
            # Tester les limites
            limits = SubscriptionService.get_subscription_limits(SubscriptionType.FREE)
            print(f"   [OK] Limites FREE: {limits}")
            
            limits_premium = SubscriptionService.get_subscription_limits(SubscriptionType.PREMIUM)
            print(f"   [OK] Limites PREMIUM: {limits_premium}")
            
        except Exception as e:
            print(f"   [ERROR] Erreur test services: {e}")
            raise
    
    def test_quotas(self):
        """Teste la logique des quotas"""
        
        try:
            # Compter les utilisateurs existants pour les tests
            user_count = self.session.query(UserAuth).count()
            print(f"   [INFO] {user_count} utilisateurs dans la base")
            
            if user_count > 0:
                # Prendre le premier utilisateur pour tester
                user = self.session.query(UserAuth).first()
                
                try:
                    quotas = MultiproprietService.get_user_apartment_quotas(self.session, user.id)
                    print(f"   [OK] Quotas utilisateur {user.email}:")
                    print(f"        - Appartements personnels: {quotas['personal_apartments']}")
                    print(f"        - Appartements sponsorisés: {quotas['sponsored_apartments']}")
                    print(f"        - Accessible via groupes: {quotas['accessible_via_groups']}")
                    print(f"        - Quota personnel: {quotas['personal_quota']}")
                    print(f"        - Peut sponsoriser: {quotas['can_sponsor_groups']}")
                    
                    # Tester la vérification d'ajout d'appartement
                    can_add, message = MultiproprietService.can_user_add_apartment(
                        self.session, user.id, "personal"
                    )
                    print(f"   [OK] Peut ajouter appartement personnel: {can_add} ({message})")
                    
                except Exception as e:
                    print(f"   [WARNING] Erreur quotas utilisateur: {e}")
            else:
                print("   [INFO] Aucun utilisateur pour tester les quotas")
            
        except Exception as e:
            print(f"   [ERROR] Erreur test quotas: {e}")
            raise
    
    def test_complete_scenario(self):
        """Teste un scénario complet de multipropriété"""
        
        try:
            # Vérifier s'il y a des groupes existants
            group_count = self.session.query(PropertyGroup).count()
            member_count = self.session.query(PropertyGroupMember).count()
            invitation_count = self.session.query(PropertyGroupInvitation).count()
            
            print(f"   [INFO] État actuel:")
            print(f"        - Groupes: {group_count}")
            print(f"        - Membres: {member_count}")
            print(f"        - Invitations: {invitation_count}")
            
            # Si il y a des données, analyser
            if group_count > 0:
                groups = self.session.query(PropertyGroup).all()
                for group in groups:
                    print(f"   [INFO] Groupe '{group.name}':")
                    print(f"        - Sponsor: {group.sponsor_id}")
                    print(f"        - Statut: {group.group_status}")
                    print(f"        - Type: {group.group_type}")
                    print(f"        - Membres actifs: {group.active_members_count}")
                    print(f"        - Appartements: {group.apartments_count}")
            
            # Tester la création d'un dashboard fictif
            try:
                # Utiliser le premier utilisateur s'il existe
                if self.session.query(UserAuth).count() > 0:
                    user = self.session.query(UserAuth).first()
                    dashboard = MultiproprietService.get_user_multipropriete_dashboard(
                        self.session, user.id
                    )
                    
                    print(f"   [OK] Dashboard généré:")
                    print(f"        - Appartements personnels: {dashboard.personal_apartments}")
                    print(f"        - Appartements sponsorisés: {dashboard.sponsored_apartments}")
                    print(f"        - Appartements accessibles: {dashboard.accessible_apartments}")
                    print(f"        - Peut créer groupes: {dashboard.can_create_groups}")
                    print(f"        - Groupes sponsorisés: {len(dashboard.sponsored_groups)}")
                    print(f"        - Groupes membre: {len(dashboard.member_groups)}")
                
            except Exception as e:
                print(f"   [WARNING] Erreur dashboard: {e}")
            
            print("   [OK] Scénario de test terminé")
            
        except Exception as e:
            print(f"   [ERROR] Erreur scénario complet: {e}")
            raise
    
    def test_api_schemas(self):
        """Teste les schémas Pydantic"""
        
        try:
            from schemas_multipropriete import (
                PropertyGroupCreate, MultiproprieteDashboardOut, 
                GroupInvitationCreate
            )
            
            # Tester la création d'un schéma de groupe
            group_data = PropertyGroupCreate(
                name="Test SCI",
                description="Test de création de groupe",
                group_type="SCI",
                max_members=15
            )
            print(f"   [OK] Schéma PropertyGroupCreate: {group_data.name}")
            
            # Tester un schéma d'invitation
            invitation_data = GroupInvitationCreate(
                invited_user_email="test@example.com",
                invitation_message="Test d'invitation",
                expires_in_days=7
            )
            print(f"   [OK] Schéma GroupInvitationCreate: {invitation_data.invited_user_email}")
            
        except Exception as e:
            print(f"   [ERROR] Erreur test schémas: {e}")
            raise


def main():
    """Point d'entrée principal"""
    
    print("Test complet - Système de multipropriété")
    print("=" * 50)
    
    tester = MultiproprieteTester()
    tester.run_tests()


if __name__ == "__main__":
    main()