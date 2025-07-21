"""
Script de nettoyage des fichiers de développement et de test
Déplace les fichiers non-production dans un dossier séparé
"""
import os
import shutil
from pathlib import Path

# Fichiers à déplacer vers le dossier dev/
DEV_FILES = [
    # Scripts de test
    "test_email_verification_complete.py",
    "test_invitation_system.py", 
    "test_oauth_flow.py",
    "test_registration.py",
    "test_signup_direct.py", 
    "test_swagger.py",
    "test_validation_complete.py",
    
    # Scripts de debug
    "debug_signup.py",
    "capture_signup_error.py",
    "diagnose_oauth.py",
    
    # Scripts de développement
    "dev_reset_users.py",
    "create_tables.py",
    
    # Scripts d'installation (à garder mais dans dev/)
    "install_photo_dependencies.py",
    "install_stripe.py",
    
    # Scripts de migration (garder mais organiser)
    "fix_address_columns.py",
    "migrate_address_nullable.py",
    "migrate_detailed_inventories.py", 
    "migrate_email_verification.py",
    "migrate_floor_plans.py",
    "migrate_lease_generation.py",
    "migrate_oauth_columns.py",
    "migrate_property_management.py",
    "migrate_rental_system.py",
    "migrate_rooms_photos.py",
    "migrate_subscription_tables.py",
    "migrate_tenant_invitations.py",
]

# Fichiers obsolètes à supprimer complètement
OBSOLETE_FILES = [
    # Services remplacés par des versions améliorées
    "email_service.py",  # Remplacé par email_verification_service.py
]

def cleanup_dev_files():
    """
    Nettoie les fichiers de développement
    """
    backend_dir = Path(__file__).parent
    dev_dir = backend_dir / "dev"
    migrations_dir = dev_dir / "migrations"
    tests_dir = dev_dir / "tests"
    scripts_dir = dev_dir / "scripts"
    
    # Créer les dossiers de développement
    dev_dir.mkdir(exist_ok=True)
    migrations_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)
    scripts_dir.mkdir(exist_ok=True)
    
    print("=== NETTOYAGE DES FICHIERS DE DÉVELOPPEMENT ===")
    
    moved_count = 0
    deleted_count = 0
    
    # Déplacer les fichiers de développement
    for filename in DEV_FILES:
        file_path = backend_dir / filename
        
        if file_path.exists():
            # Déterminer la destination
            if filename.startswith("test_"):
                destination = tests_dir / filename
            elif filename.startswith("migrate_") or filename.startswith("fix_"):
                destination = migrations_dir / filename
            else:
                destination = scripts_dir / filename
            
            try:
                shutil.move(str(file_path), str(destination))
                print(f"[OK] Déplacé: {filename} -> {destination.relative_to(backend_dir)}")
                moved_count += 1
            except Exception as e:
                print(f"[ERROR] Erreur lors du déplacement de {filename}: {e}")
    
    # Supprimer les fichiers obsolètes
    for filename in OBSOLETE_FILES:
        file_path = backend_dir / filename
        
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"[DELETED] Supprimé: {filename}")
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] Erreur lors de la suppression de {filename}: {e}")
    
    # Créer un fichier README dans le dossier dev
    readme_content = """# Dossier de Développement

Ce dossier contient les fichiers et scripts utilisés uniquement en développement.

## Structure

- `tests/` : Scripts de test et validation
- `migrations/` : Scripts de migration de base de données
- `scripts/` : Scripts utilitaires et d'installation

## Utilisation

Ces fichiers ne doivent PAS être déployés en production.
Ils sont conservés pour le développement et la maintenance.

## Scripts de Migration

Les scripts de migration doivent être exécutés dans l'ordre chronologique.
Vérifiez toujours l'état de la base avant d'exécuter une migration.

## Scripts de Test

Utilisez les scripts de test pour valider les fonctionnalités avant déploiement.
"""
    
    readme_path = dev_dir / "README.md"
    try:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"[CREATED] Créé: {readme_path.relative_to(backend_dir)}")
    except Exception as e:
        print(f"[ERROR] Erreur lors de la création du README: {e}")
    
    print(f"\n[SUCCESS] Nettoyage terminé:")
    print(f"   - {moved_count} fichiers déplacés")
    print(f"   - {deleted_count} fichiers supprimés")
    print(f"   - Structure dev/ créée")

if __name__ == "__main__":
    cleanup_dev_files()