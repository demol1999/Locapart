"""
Script pour créer un super administrateur
Utilise un utilisateur existant ou en crée un nouveau
"""
import sys
import os
from getpass import getpass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url
from models import UserAuth
from models_admin import AdminUser
from enums import AdminRole, AuthType
from auth import get_password_hash


def create_super_admin():
    """Crée un super administrateur"""
    
    print("=== CRÉATION SUPER ADMINISTRATEUR ===")
    print("Ce script va créer un super administrateur pour le panel admin.\n")
    
    try:
        # Connexion à la base de données
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("1. Vérification de la base de données...")
        
        # Vérifier si des admins existent déjà
        admin_count = db.query(AdminUser).count()
        if admin_count > 0:
            print(f"   [INFO] {admin_count} administrateur(s) déjà présent(s)")
            response = input("   Voulez-vous créer un autre administrateur ? (o/N): ")
            if response.lower() not in ['o', 'oui', 'y', 'yes']:
                print("   [INFO] Opération annulée")
                return False
        
        print("\n2. Sélection de l'utilisateur...")
        
        # Demander l'email de l'utilisateur
        email = input("   Email de l'utilisateur à promouvoir admin (ou nouveau): ").strip()
        if not email:
            print("   [ERROR] Email requis")
            return False
        
        # Chercher l'utilisateur existant
        user = db.query(UserAuth).filter(UserAuth.email == email).first()
        
        if user:
            print(f"   [OK] Utilisateur trouvé: {user.first_name} {user.last_name}")
            
            # Vérifier s'il n'est pas déjà admin
            existing_admin = db.query(AdminUser).filter(AdminUser.user_id == user.id).first()
            if existing_admin:
                print(f"   [WARNING] Cet utilisateur est déjà administrateur (rôle: {existing_admin.admin_role})")
                response = input("   Voulez-vous mettre à jour ses permissions ? (o/N): ")
                if response.lower() in ['o', 'oui', 'y', 'yes']:
                    return update_admin_permissions(db, existing_admin)
                else:
                    return False
        else:
            print("   [INFO] Utilisateur non trouvé, création d'un nouveau compte...")
            user = create_new_user(db, email)
            if not user:
                return False
        
        print("\n3. Création de l'administrateur...")
        
        # Créer l'admin
        new_admin = AdminUser(
            user_id=user.id,
            admin_role=AdminRole.SUPER_ADMIN,
            can_manage_users=True,
            can_manage_subscriptions=True,
            can_view_finances=True,
            can_manage_properties=True,
            can_access_audit_logs=True,
            can_manage_admins=True,
            is_active=True,
            notes="Super administrateur créé via script"
        )
        
        db.add(new_admin)
        db.commit()
        
        print(f"   [SUCCESS] Super administrateur créé!")
        print(f"   - Utilisateur: {user.email}")
        print(f"   - Nom: {user.first_name} {user.last_name}")
        print(f"   - Rôle: {new_admin.admin_role}")
        print(f"   - ID Admin: {new_admin.id}")
        
        print("\n4. Récapitulatif des permissions:")
        permissions = [
            ("Gestion des utilisateurs", "✓"),
            ("Gestion des abonnements", "✓"),
            ("Consultation financière", "✓"),
            ("Gestion des propriétés", "✓"),
            ("Accès aux logs d'audit", "✓"),
            ("Gestion des administrateurs", "✓")
        ]
        
        for perm, status in permissions:
            print(f"   - {perm}: {status}")
        
        print(f"\n[SUCCESS] Super administrateur créé avec succès!")
        print(f"L'utilisateur {user.email} peut maintenant accéder au panel admin.")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.rollback()
        return False
    
    finally:
        if 'db' in locals():
            db.close()


def create_new_user(db, email: str) -> UserAuth:
    """Crée un nouvel utilisateur"""
    
    try:
        print(f"   Création d'un compte pour {email}...")
        
        # Demander les informations
        first_name = input("   Prénom: ").strip()
        last_name = input("   Nom: ").strip()
        
        if not first_name or not last_name:
            print("   [ERROR] Prénom et nom requis")
            return None
        
        # Demander le mot de passe
        while True:
            password = getpass("   Mot de passe (8 caractères min): ")
            if len(password) >= 8:
                break
            print("   [ERROR] Le mot de passe doit contenir au moins 8 caractères")
        
        confirm_password = getpass("   Confirmer le mot de passe: ")
        if password != confirm_password:
            print("   [ERROR] Les mots de passe ne correspondent pas")
            return None
        
        # Créer l'utilisateur
        hashed_password = get_password_hash(password)
        
        new_user = UserAuth(
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            auth_type=AuthType.EMAIL_PASSWORD,
            email_verified=True,  # Auto-vérifier pour les admins
            email_verified_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"   [OK] Utilisateur créé: {new_user.email}")
        return new_user
        
    except Exception as e:
        print(f"   [ERROR] Erreur création utilisateur: {e}")
        db.rollback()
        return None


def update_admin_permissions(db, admin: AdminUser) -> bool:
    """Met à jour les permissions d'un admin existant"""
    
    try:
        print(f"   Mise à jour des permissions pour {admin.user.email}...")
        
        # Forcer super admin
        admin.admin_role = AdminRole.SUPER_ADMIN
        admin.can_manage_users = True
        admin.can_manage_subscriptions = True
        admin.can_view_finances = True
        admin.can_manage_properties = True
        admin.can_access_audit_logs = True
        admin.can_manage_admins = True
        admin.is_active = True
        admin.notes = "Permissions mises à jour via script"
        
        db.commit()
        
        print("   [OK] Permissions mises à jour")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Erreur mise à jour: {e}")
        db.rollback()
        return False


def list_existing_admins():
    """Liste les administrateurs existants"""
    
    print("=== LISTE DES ADMINISTRATEURS ===")
    
    try:
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        admins = db.query(AdminUser).all()
        
        if not admins:
            print("Aucun administrateur trouvé.")
            return
        
        print(f"Nombre d'administrateurs: {len(admins)}\n")
        
        for admin in admins:
            print(f"ID: {admin.id}")
            print(f"Email: {admin.user.email if admin.user else 'N/A'}")
            print(f"Nom: {admin.user.first_name} {admin.user.last_name}" if admin.user else "N/A")
            print(f"Rôle: {admin.admin_role}")
            print(f"Actif: {'Oui' if admin.is_active else 'Non'}")
            print(f"Dernière connexion: {admin.last_login_at or 'Jamais'}")
            print(f"Créé le: {admin.created_at}")
            print("-" * 40)
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de la liste: {e}")
    
    finally:
        if 'db' in locals():
            db.close()


def main():
    """Point d'entrée principal"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Gestion des super administrateurs')
    parser.add_argument('--list', action='store_true', help='Liste les admins existants')
    parser.add_argument('--create', action='store_true', help='Crée un super admin')
    
    args = parser.parse_args()
    
    if args.list:
        list_existing_admins()
    elif args.create or len(sys.argv) == 1:  # Par défaut si pas d'arguments
        success = create_super_admin()
        if not success:
            sys.exit(1)
    else:
        parser.print_help()


# Import nécessaire
from datetime import datetime


if __name__ == "__main__":
    main()