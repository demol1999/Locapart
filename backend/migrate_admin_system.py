"""
Migration pour le système d'administration
Création des tables admin et extension du modèle UserAuth
"""
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url
from models import Base


def run_migration():
    """Exécute la migration du système d'administration"""
    
    print("=== MIGRATION SYSTÈME D'ADMINISTRATION ===")
    print("Création des tables et colonnes admin...\n")
    
    try:
        # Connexion à la base de données
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        print("1. Vérification de la connexion à la base...")
        session.execute(text("SELECT 1"))
        print("   [OK] Connexion établie")
        
        # Importer tous les modèles pour que SQLAlchemy les connaisse
        print("\n2. Import des modèles...")
        from models import UserAuth, Building, Apartment, ApartmentUserLink, Copro, SyndicatCopro, Photo, UserSession, AuditLog, UserSubscription, Payment, FloorPlan, Tenant, Lease, TenantDocument, Inventory, InventoryPhoto, TenantInvitation, Room
        from models_admin import AdminUser, AdminAction, UserStatusHistory, SystemSettings, AdminNotification, extend_user_model_for_admin
        from models_multipropriete import PropertyGroup, PropertyGroupMember, PropertyGroupInvitation
        print("   [OK] Modèles importés")
        
        # Étendre le modèle UserAuth pour l'administration
        print("\n3. Extension du modèle UserAuth...")
        extend_user_model_for_admin()
        print("   [OK] Modèle UserAuth étendu")
        
        # Récupérer l'inspector pour vérifier les tables existantes
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Créer les nouvelles tables
        print("\n4. Création des tables admin...")
        
        # Tables à créer dans l'ordre des dépendances
        admin_tables = [
            'admin_users',
            'admin_actions', 
            'user_status_history',
            'system_settings',
            'admin_notifications'
        ]
        
        # Créer toutes les tables (SQLAlchemy ne créera que celles qui n'existent pas)
        Base.metadata.create_all(bind=engine)
        print("   [OK] Tables admin créées")
        
        # Vérifier quelles tables ont été créées
        print("\n5. Vérification des tables créées...")
        new_inspector = inspect(engine)
        current_tables = new_inspector.get_table_names()
        
        for table in admin_tables:
            if table in current_tables:
                print(f"   [OK] Table {table} présente")
            else:
                print(f"   [WARNING] Table {table} manquante")
        
        # Ajouter les colonnes admin au modèle UserAuth si elles n'existent pas
        print("\n6. Extension de la table user_auth...")
        
        user_columns = inspector.get_columns('user_auth')
        existing_columns = [col['name'] for col in user_columns]
        
        admin_columns_to_add = [
            ('user_status', "ENUM('active', 'inactive', 'suspended', 'banned', 'pending_verification') NOT NULL DEFAULT 'active' COMMENT 'Statut administratif de l\\'utilisateur'"),
            ('admin_notes', 'TEXT NULL COMMENT \'Notes administratives\''),
            ('suspension_reason', 'TEXT NULL COMMENT \'Raison de suspension\''),
            ('suspension_expires_at', 'DATETIME NULL COMMENT \'Fin de suspension\''),
            ('last_admin_action', 'DATETIME NULL COMMENT \'Dernière action admin\'')
        ]
        
        for col_name, col_definition in admin_columns_to_add:
            if col_name not in existing_columns:
                try:
                    session.execute(text(f"ALTER TABLE user_auth ADD COLUMN {col_name} {col_definition}"))
                    print(f"   [OK] Colonne {col_name} ajoutée")
                except SQLAlchemyError as e:
                    if "Duplicate column name" in str(e):
                        print(f"   [INFO] Colonne {col_name} déjà présente")
                    else:
                        print(f"   [WARNING] Erreur ajout colonne {col_name}: {e}")
            else:
                print(f"   [INFO] Colonne {col_name} déjà présente")
        
        # Commit des changements
        session.commit()
        print("\n7. Migration terminée avec succès!")
        
        # Créer un super admin par défaut si aucun admin n'existe
        print("\n8. Vérification des administrateurs...")
        try:
            admin_count = session.execute(text("SELECT COUNT(*) FROM admin_users")).scalar()
            if admin_count == 0:
                print("   [INFO] Aucun administrateur trouvé")
                print("   [INFO] Pour créer un super admin, utilisez le script create_super_admin.py")
            else:
                print(f"   [OK] {admin_count} administrateur(s) trouvé(s)")
        except:
            print("   [INFO] Impossible de vérifier les administrateurs (normal si première installation)")
        
        print("\n[SUCCESS] Migration du système d'administration terminée!")
        print("\nÉtapes suivantes:")
        print("1. Créer un super administrateur avec create_super_admin.py")
        print("2. Ajouter les routes admin à main.py")
        print("3. Tester l'accès au panel admin")
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()
    
    return True


def rollback_migration():
    """Rollback de la migration admin (pour les tests)"""
    
    print("=== ROLLBACK MIGRATION ADMIN ===")
    print("Suppression des tables et colonnes admin...\n")
    
    try:
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Tables à supprimer dans l'ordre inverse des dépendances
        admin_tables = [
            'admin_notifications',
            'system_settings', 
            'user_status_history',
            'admin_actions',
            'admin_users'
        ]
        
        print("1. Suppression des tables admin...")
        for table in admin_tables:
            try:
                session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"   [OK] Table {table} supprimée")
            except SQLAlchemyError as e:
                print(f"   [WARNING] Erreur suppression {table}: {e}")
        
        # Supprimer les colonnes ajoutées à user_auth
        print("\n2. Suppression des colonnes admin de user_auth...")
        admin_columns = [
            'user_status',
            'admin_notes', 
            'suspension_reason',
            'suspension_expires_at',
            'last_admin_action'
        ]
        
        for col_name in admin_columns:
            try:
                session.execute(text(f"ALTER TABLE user_auth DROP COLUMN {col_name}"))
                print(f"   [OK] Colonne {col_name} supprimée")
            except SQLAlchemyError as e:
                if "doesn't exist" in str(e).lower():
                    print(f"   [INFO] Colonne {col_name} n'existe pas")
                else:
                    print(f"   [WARNING] Erreur suppression colonne {col_name}: {e}")
        
        session.commit()
        print("\n[SUCCESS] Rollback terminé!")
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors du rollback: {e}")
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()
    
    return True


def create_super_admin(email: str, user_id: int = None):
    """Crée un super administrateur"""
    
    print(f"=== CRÉATION SUPER ADMIN ===")
    print(f"Email: {email}")
    
    try:
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Si user_id n'est pas fourni, chercher par email
        if not user_id:
            result = session.execute(
                text("SELECT id FROM user_auth WHERE email = :email"), 
                {"email": email}
            ).fetchone()
            
            if not result:
                print(f"[ERROR] Utilisateur avec email {email} non trouvé")
                return False
            
            user_id = result[0]
        
        # Vérifier si cet utilisateur est déjà admin
        existing = session.execute(
            text("SELECT id FROM admin_users WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if existing:
            print("[WARNING] Cet utilisateur est déjà administrateur")
            return False
        
        # Créer le super admin
        session.execute(text("""
            INSERT INTO admin_users (
                user_id, admin_role, can_manage_users, can_manage_subscriptions,
                can_view_finances, can_manage_properties, can_access_audit_logs,
                can_manage_admins, is_active, notes, created_at, updated_at
            ) VALUES (
                :user_id, 'super_admin', 1, 1, 1, 1, 1, 1, 1, 
                'Super administrateur créé automatiquement',
                NOW(), NOW()
            )
        """), {"user_id": user_id})
        
        session.commit()
        print("[SUCCESS] Super administrateur créé!")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de la création du super admin: {e}")
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()


def main():
    """Point d'entrée principal"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration du système d\'administration')
    parser.add_argument('--rollback', action='store_true', help='Effectuer un rollback')
    parser.add_argument('--create-super-admin', type=str, help='Créer un super admin avec cet email')
    parser.add_argument('--user-id', type=int, help='ID utilisateur pour le super admin')
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    elif args.create_super_admin:
        # D'abord exécuter la migration si nécessaire
        run_migration()
        success = create_super_admin(args.create_super_admin, args.user_id)
    else:
        success = run_migration()
    
    if success:
        print("\n✓ Opération terminée avec succès")
    else:
        print("\n✗ Échec de l'opération")
        sys.exit(1)


if __name__ == "__main__":
    main()