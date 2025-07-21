"""
Script de migration pour le systeme de gestion multi-acteurs des proprietes
"""
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json
from datetime import datetime
from typing import Dict, Any, List

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url, Base
from models import UserAuth, Apartment, Building
from property_management_models import (
    ManagementCompany, PropertyManagement, PropertyOwnership,
    TenantOccupancy, UserPermission, PermissionTemplate, AccessLog,
    UserRole, PermissionType, PropertyScope,
    get_default_permissions_by_role, create_management_company_templates,
    company_managers
)

class PropertyManagementMigration:
    """Gestionnaire de migration pour le systeme multi-acteurs"""
    
    def __init__(self):
        self.engine = create_engine(get_db_url())
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = None
    
    def run_migration(self):
        """Execute la migration complete"""
        
        print("=== MIGRATION SYSTEME GESTION MULTI-ACTEURS ===")
        print("Debut de la migration...")
        
        try:
            self.session = self.SessionLocal()
            
            # 1. Creer les tables
            print("\n1. Creation des tables...")
            self.create_tables()
            
            # 2. Creer les templates par defaut
            print("\n2. Creation des templates de permissions...")
            self.create_default_templates()
            
            # 3. Creer une societe de gestion par defaut
            print("\n3. Creation d'une societe de gestion par defaut...")
            self.create_default_management_company()
            
            # 4. Migrer les donnees existantes
            print("\n4. Migration des donnees existantes...")
            self.migrate_existing_data()
            
            # 5. Verifications finales
            print("\n5. Verifications finales...")
            self.verify_migration()
            
            self.session.commit()
            print("\n[SUCCESS] Migration terminee avec succes!")
            
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"\n[ERROR] Erreur lors de la migration: {e}")
            raise
        finally:
            if self.session:
                self.session.close()
    
    def create_tables(self):
        """Cree toutes les nouvelles tables"""
        
        try:
            # Creer toutes les tables definies dans les modeles
            Base.metadata.create_all(bind=self.engine)
            print("   [OK] Tables creees avec succes")
            
            # Verifier que toutes les tables existent
            required_tables = [
                'management_companies',
                'company_managers', 
                'property_management',
                'property_ownership',
                'tenant_occupancy',
                'user_permissions',
                'permission_templates',
                'access_logs'
            ]
            
            for table in required_tables:
                result = self.session.execute(text(f"SHOW TABLES LIKE '{table}'")).fetchone()
                if not result:
                    raise Exception(f"Table {table} n'a pas ete creee")
            
            print("   [OK] Toutes les tables requises sont presentes")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la creation des tables: {e}")
            raise
    
    def create_default_templates(self):
        """Cree les templates de permissions par defaut"""
        
        try:
            # Templates pour societes de gestion
            templates_data = create_management_company_templates()
            
            for template_data in templates_data:
                # Verifier si le template existe deja
                existing = self.session.query(PermissionTemplate).filter(
                    PermissionTemplate.name == template_data["name"]
                ).first()
                
                if not existing:
                    template = PermissionTemplate(
                        name=template_data["name"],
                        description=template_data["description"],
                        role=template_data["role"].value,
                        permissions={
                            "permissions": [p.value for p in template_data["permissions"]]
                        },
                        default_scope=template_data["default_scope"].value,
                        is_system_template=template_data["is_system_template"]
                    )
                    
                    self.session.add(template)
                    print(f"   [OK] Template cree: {template_data['name']}")
                else:
                    print(f"   [INFO] Template existe deja: {template_data['name']}")
            
            # Templates pour tous les roles utilisateur
            for role in UserRole:
                role_data = get_default_permissions_by_role(role)
                template_name = f"Role par defaut: {role.value}"
                
                existing = self.session.query(PermissionTemplate).filter(
                    PermissionTemplate.name == template_name
                ).first()
                
                if not existing:
                    template = PermissionTemplate(
                        name=template_name,
                        description=role_data["description"],
                        role=role.value,
                        permissions={
                            "permissions": [p.value if hasattr(p, 'value') else p for p in role_data["permissions"]]
                        },
                        default_scope=role_data["scope"].value,
                        is_system_template=True
                    )
                    
                    self.session.add(template)
                    print(f"   [OK] Template de role cree: {role.value}")
            
            print("   [OK] Templates de permissions crees")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la creation des templates: {e}")
            raise
    
    def create_default_management_company(self):
        """Cree une societe de gestion par defaut"""
        
        try:
            # Verifier si une societe existe deja
            existing = self.session.query(ManagementCompany).first()
            
            if not existing:
                company = ManagementCompany(
                    name="LocAppart Gestion",
                    business_name="LocAppart Societe de Gestion Immobiliere",
                    address="123 Rue de la Gestion",
                    postal_code="75001",
                    city="Paris",
                    country="France",
                    phone="01.23.45.67.89",
                    email="gestion@locappart.fr",
                    license_number="CPI-75-2024-001",
                    default_commission_rate=8.5,
                    billing_settings={
                        "currency": "EUR",
                        "tax_rate": 20.0,
                        "payment_terms": "30 jours"
                    }
                )
                
                self.session.add(company)
                self.session.flush()  # Pour obtenir l'ID
                
                print(f"   [OK] Societe de gestion par defaut creee (ID: {company.id})")
                return company.id
            else:
                print(f"   [INFO] Societe de gestion existe deja (ID: {existing.id})")
                return existing.id
                
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la creation de la societe: {e}")
            raise
    
    def migrate_existing_data(self):
        """Migre les donnees existantes vers le nouveau systeme"""
        
        try:
            # 1. Migrer les proprietaires existants
            self.migrate_existing_owners()
            
            # 2. Creer des permissions par defaut pour les utilisateurs existants
            self.create_default_permissions()
            
            print("   [OK] Migration des donnees existantes terminee")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la migration des donnees: {e}")
            raise
    
    def migrate_existing_owners(self):
        """Cree des enregistrements de propriete pour les appartements existants"""
        
        try:
            # Recuperer tous les appartements
            apartments = self.session.query(Apartment).all()
            
            migrated_count = 0
            for apartment in apartments:
                # Verifier si cet appartement a deja des proprietaires
                existing_ownership = self.session.query(PropertyOwnership).filter(
                    PropertyOwnership.apartment_id == apartment.id
                ).first()
                
                if not existing_ownership:
                    # Essayer de trouver le proprietaire via ApartmentUserLink
                    try:
                        from models import ApartmentUserLink
                        owner_links = self.session.query(ApartmentUserLink).filter(
                            ApartmentUserLink.apartment_id == apartment.id,
                            ApartmentUserLink.role.in_(['owner', 'gestionnaire'])
                        ).all()
                        
                        if owner_links:
                            for link in owner_links:
                                ownership = PropertyOwnership(
                                    apartment_id=apartment.id,
                                    owner_id=link.user_id,
                                    ownership_percentage=100.0 if len(owner_links) == 1 else 100.0 / len(owner_links),
                                    ownership_type="FULL",
                                    can_sign_leases=True,
                                    can_authorize_works=True,
                                    can_receive_rent=True,
                                    can_access_reports=True,
                                    start_date=datetime.utcnow()
                                )
                                self.session.add(ownership)
                                migrated_count += 1
                        else:
                            # Pas de proprietaire defini, creer un enregistrement par defaut
                            # avec le premier utilisateur admin si disponible
                            admin_user = self.session.query(UserAuth).filter(
                                UserAuth.role == 'admin'
                            ).first()
                            
                            if admin_user:
                                ownership = PropertyOwnership(
                                    apartment_id=apartment.id,
                                    owner_id=admin_user.id,
                                    ownership_percentage=100.0,
                                    ownership_type="FULL",
                                    can_sign_leases=True,
                                    can_authorize_works=True,
                                    can_receive_rent=True,
                                    can_access_reports=True,
                                    start_date=datetime.utcnow()
                                )
                                self.session.add(ownership)
                                migrated_count += 1
                    
                    except ImportError:
                        # ApartmentUserLink n'existe pas, ignorer
                        pass
            
            print(f"   [OK] {migrated_count} proprietes migrees")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la migration des proprietaires: {e}")
            raise
    
    def create_default_permissions(self):
        """Cree des permissions par defaut pour les utilisateurs existants"""
        
        try:
            users = self.session.query(UserAuth).all()
            
            permissions_created = 0
            for user in users:
                # Determiner le role base sur l'ancien systeme
                user_role = UserRole.VIEWER  # Par defaut
                
                if hasattr(user, 'role'):
                    if user.role == 'admin':
                        user_role = UserRole.SUPER_ADMIN
                    elif user.role == 'gestionnaire':
                        user_role = UserRole.PROPERTY_MANAGER
                    elif user.role == 'owner':
                        user_role = UserRole.OWNER
                    elif user.role == 'tenant':
                        user_role = UserRole.TENANT
                
                # Obtenir les permissions par defaut pour ce role
                default_perms = get_default_permissions_by_role(user_role)
                
                # Creer les permissions
                for perm_name in default_perms["permissions"]:
                    if hasattr(perm_name, 'value'):
                        permission_type = perm_name
                    else:
                        permission_type = PermissionType(perm_name)
                    
                    # Verifier si la permission existe deja
                    existing = self.session.query(UserPermission).filter(
                        UserPermission.user_id == user.id,
                        UserPermission.permission_type == permission_type,
                        UserPermission.resource_type == "apartment"
                    ).first()
                    
                    if not existing:
                        permission = UserPermission(
                            user_id=user.id,
                            granted_by=user.id,  # Auto-accorde lors de la migration
                            permission_type=permission_type,
                            resource_type="apartment",
                            resource_id=None,  # Permission globale lors de la migration
                            scope=default_perms["scope"]
                        )
                        
                        self.session.add(permission)
                        permissions_created += 1
            
            print(f"   [OK] {permissions_created} permissions par défaut créées")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la création des permissions: {e}")
            raise
    
    def verify_migration(self):
        """Vérifie que la migration s'est bien déroulée"""
        
        try:
            # Compter les enregistrements créés
            counts = {
                'management_companies': self.session.query(ManagementCompany).count(),
                'permission_templates': self.session.query(PermissionTemplate).count(),
                'property_ownership': self.session.query(PropertyOwnership).count(),
                'user_permissions': self.session.query(UserPermission).count()
            }
            
            print("\n   [STATS] Statistiques de migration:")
            for table, count in counts.items():
                print(f"   - {table}: {count} enregistrements")
            
            # Verifications de coherence
            apartments_count = self.session.query(Apartment).count()
            ownership_count = counts['property_ownership']
            
            if apartments_count > 0 and ownership_count == 0:
                print("   [WARNING] Attention: Aucune propriete migree pour des appartements existants")
            
            # Verifier les templates systeme
            system_templates = self.session.query(PermissionTemplate).filter(
                PermissionTemplate.is_system_template == True
            ).count()
            
            if system_templates < len(UserRole):
                print(f"   [WARNING] Attention: Templates systeme incomplets ({system_templates}/{len(UserRole)})")
            
            print("   [OK] Verifications terminees")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors des verifications: {e}")
            raise
    
    def rollback_migration(self):
        """Annule la migration (a utiliser avec precaution)"""
        
        print("=== ROLLBACK MIGRATION ===")
        print("[WARNING] ATTENTION: Cette operation va supprimer toutes les donnees du systeme multi-acteurs!")
        
        confirm = input("Tapez 'CONFIRM' pour continuer: ")
        if confirm != 'CONFIRM':
            print("Rollback annule.")
            return
        
        try:
            self.session = self.SessionLocal()
            
            # Supprimer les donnees dans l'ordre inverse des dependances
            tables_to_clean = [
                'access_logs',
                'user_permissions', 
                'tenant_occupancy',
                'property_ownership',
                'property_management',
                'permission_templates',
                'company_managers',
                'management_companies'
            ]
            
            for table in tables_to_clean:
                self.session.execute(text(f"DELETE FROM {table}"))
                print(f"   [OK] Table {table} videe")
            
            self.session.commit()
            print("[SUCCESS] Rollback termine avec succes!")
            
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"[ERROR] Erreur lors du rollback: {e}")
            raise
        finally:
            if self.session:
                self.session.close()


def main():
    """Point d'entree principal"""
    
    print("Script de migration - Systeme de gestion multi-acteurs")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        migration = PropertyManagementMigration()
        migration.rollback_migration()
    else:
        migration = PropertyManagementMigration()
        migration.run_migration()


if __name__ == "__main__":
    main()