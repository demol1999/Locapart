#!/usr/bin/env python3
"""
Script de migration pour les états des lieux détaillés
"""

import sys
import os
from sqlalchemy import text

# Ajouter le repertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models  # Import des modèles principaux
from inventory_models import (
    DetailedInventory, InventoryRoom, InventoryItem, 
    DetailedInventoryPhoto, InventoryItemPhoto, InventoryTemplate,
    InventorySignature, create_standard_apartment_template,
    create_house_template
)

def create_detailed_inventory_tables():
    """Crée les tables pour les états des lieux détaillés"""
    
    print("Migration : Ajout des tables d'états des lieux détaillés...")
    
    # Vérifier d'abord que les tables principales existent
    try:
        # Créer toutes les tables depuis models.py (inclut leases, tenants, etc.)
        models.Base.metadata.create_all(bind=engine)
        print("   OK: Tables principales verifiees/creees")
    except Exception as e:
        print(f"   ERREUR: Creation des tables principales: {e}")
        return False
    
    # Créer toutes les nouvelles tables
    tables_to_create = [
        DetailedInventory,
        InventoryRoom,
        InventoryItem,
        DetailedInventoryPhoto,
        InventoryItemPhoto,
        InventoryTemplate,
        InventorySignature
    ]
    
    for table_class in tables_to_create:
        try:
            table_class.__table__.create(bind=engine, checkfirst=True)
            print(f"   OK: Table '{table_class.__tablename__}' creee")
        except Exception as e:
            print(f"   ERREUR: {table_class.__tablename__}: {e}")
            return False
    
    return True

def verify_tables_structure():
    """Vérifie la structure des tables créées"""
    
    print("\nVerification de la structure des tables...")
    
    db = SessionLocal()
    try:
        tables_to_check = [
            'detailed_inventories',
            'inventory_rooms',
            'inventory_items', 
            'detailed_inventory_photos',
            'inventory_item_photos',
            'inventory_templates',
            'inventory_signatures'
        ]
        
        for table_name in tables_to_check:
            try:
                result = db.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                if result.fetchone():
                    # Afficher la structure
                    columns_result = db.execute(text(f"DESCRIBE {table_name}"))
                    columns = columns_result.fetchall()
                    print(f"   OK: {table_name} ({len(columns)} colonnes)")
                    
                    # Afficher les 5 premières colonnes
                    first_columns = [col[0] for col in columns[:5]]
                    if len(columns) > 5:
                        first_columns.append("...")
                    print(f"      Colonnes: {', '.join(first_columns)}")
                else:
                    print(f"   ERREUR: Table {table_name} non trouvee")
                    return False
            except Exception as e:
                print(f"   ERREUR: {table_name}: {e}")
                return False
        
        return True
        
    finally:
        db.close()

def verify_foreign_keys():
    """Vérifie les clés étrangères"""
    
    print("\nVerification des cles etrangeres...")
    
    db = SessionLocal()
    try:
        # Relations principales à vérifier
        relations = [
            ("detailed_inventories", "lease_id", "leases", "id"),
            ("detailed_inventories", "conducted_by", "user_auth", "id"),
            ("detailed_inventories", "apartment_id", "apartments", "id"),
            ("inventory_rooms", "inventory_id", "detailed_inventories", "id"),
            ("inventory_items", "room_id", "inventory_rooms", "id"),
            ("detailed_inventory_photos", "inventory_id", "detailed_inventories", "id"),
            ("detailed_inventory_photos", "room_id", "inventory_rooms", "id"),
            ("inventory_item_photos", "item_id", "inventory_items", "id"),
            ("inventory_templates", "created_by", "user_auth", "id"),
            ("inventory_templates", "apartment_id", "apartments", "id"),
            ("inventory_signatures", "inventory_id", "detailed_inventories", "id")
        ]
        
        relations_ok = 0
        for table, column, ref_table, ref_column in relations:
            try:
                query = text(f"""
                    SELECT CONSTRAINT_NAME 
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = '{table}' 
                    AND COLUMN_NAME = '{column}'
                    AND REFERENCED_TABLE_NAME = '{ref_table}'
                    AND REFERENCED_COLUMN_NAME = '{ref_column}'
                """)
                result = db.execute(query)
                constraint = result.fetchone()
                
                if constraint:
                    print(f"   OK: {table}.{column} -> {ref_table}.{ref_column}")
                    relations_ok += 1
                else:
                    print(f"   WARNING: {table}.{column} -> {ref_table}.{ref_column} non trouvee")
                    
            except Exception as e:
                print(f"   ERREUR: {table}.{column}: {e}")
        
        print(f"\nRelations trouvees: {relations_ok}/{len(relations)}")
        return relations_ok > 0
        
    finally:
        db.close()

def create_default_templates():
    """Crée les templates par défaut"""
    
    print("\nCreation des templates par defaut...")
    
    import json  # Import JSON ici
    
    db = SessionLocal()
    try:
        # Vérifier s'il y a déjà des templates
        existing_templates = db.execute(text("SELECT COUNT(*) FROM inventory_templates")).scalar()
        
        if existing_templates > 0:
            print(f"   {existing_templates} template(s) deja existant(s)")
            return True
        
        # Récupérer le premier utilisateur pour créer les templates
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        
        if not first_user:
            print("   WARNING: Aucun utilisateur trouve - pas de templates par defaut")
            return True
        
        # Créer le template appartement standard
        apartment_template_data = create_standard_apartment_template()
        
        apartment_template = {
            'created_by': first_user,
            'name': apartment_template_data['name'],
            'description': apartment_template_data['description'],
            'is_public': True,
            'template_data': json.dumps(apartment_template_data)
        }
        
        db.execute(text("""
            INSERT INTO inventory_templates (created_by, name, description, is_public, template_data, created_at, updated_at)
            VALUES (:created_by, :name, :description, :is_public, :template_data, NOW(), NOW())
        """), apartment_template)
        
        # Créer le template maison
        house_template_data = create_house_template()
        
        house_template = {
            'created_by': first_user,
            'name': house_template_data['name'],
            'description': house_template_data['description'],
            'is_public': True,
            'template_data': json.dumps(house_template_data)
        }
        
        db.execute(text("""
            INSERT INTO inventory_templates (created_by, name, description, is_public, template_data, created_at, updated_at)
            VALUES (:created_by, :name, :description, :is_public, :template_data, NOW(), NOW())
        """), house_template)
        
        db.commit()
        
        print("   OK: 2 templates par defaut crees")
        print("      - Appartement standard")
        print("      - Maison standard")
        
        return True
        
    except Exception as e:
        print(f"   ERREUR: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_sample_detailed_inventory():
    """Crée un état des lieux d'exemple si possible"""
    
    print("\nCreation d'un exemple d'etat des lieux...")
    
    db = SessionLocal()
    try:
        # Vérifier les prérequis
        user_count = db.execute(text("SELECT COUNT(*) FROM user_auth")).scalar()
        lease_count = db.execute(text("SELECT COUNT(*) FROM leases")).scalar()
        apartment_count = db.execute(text("SELECT COUNT(*) FROM apartments")).scalar()
        
        if user_count == 0 or lease_count == 0 or apartment_count == 0:
            print(f"   Prerequis insuffisants:")
            print(f"      - Utilisateurs: {user_count}")
            print(f"      - Baux: {lease_count}")
            print(f"      - Appartements: {apartment_count}")
            print("   Exemple non cree")
            return True
        
        # Vérifier s'il y a déjà des états des lieux détaillés
        existing_inventories = db.execute(text("SELECT COUNT(*) FROM detailed_inventories")).scalar()
        
        if existing_inventories > 0:
            print(f"   {existing_inventories} etat(s) des lieux deja existant(s)")
            return True
        
        # Récupérer les données nécessaires
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        first_lease = db.execute(text("SELECT id, apartment_id FROM leases LIMIT 1")).fetchone()
        
        if not first_lease:
            print("   Aucun bail trouve")
            return True
        
        lease_id, apartment_id = first_lease
        
        # Créer un état des lieux d'exemple
        sample_inventory = {
            'lease_id': lease_id,
            'conducted_by': first_user,
            'apartment_id': apartment_id,
            'inventory_type': 'ENTRY',
            'status': 'DRAFT',
            'tenant_present': True,
            'landlord_present': True,
            'overall_condition': 'GOOD',
            'general_notes': 'Etat des lieux d exemple cree par la migration'
        }
        
        db.execute(text("""
            INSERT INTO detailed_inventories 
            (lease_id, conducted_by, apartment_id, inventory_type, status, 
             tenant_present, landlord_present, overall_condition, general_notes, created_at, updated_at)
            VALUES (:lease_id, :conducted_by, :apartment_id, :inventory_type, :status,
                    :tenant_present, :landlord_present, :overall_condition, :general_notes, NOW(), NOW())
        """), sample_inventory)
        
        # Récupérer l'ID de l'inventaire créé
        inventory_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # Créer une pièce d'exemple
        sample_room = {
            'inventory_id': inventory_id,
            'name': 'Salon',
            'room_type': 'LIVING_ROOM',
            'order': 1,
            'overall_condition': 'GOOD',
            'notes': 'Piece d exemple'
        }
        
        db.execute(text("""
            INSERT INTO inventory_rooms 
            (inventory_id, name, room_type, order, overall_condition, notes, created_at, updated_at)
            VALUES (:inventory_id, :name, :room_type, :order, :overall_condition, :notes, NOW(), NOW())
        """), sample_room)
        
        # Récupérer l'ID de la pièce créée
        room_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # Créer quelques éléments d'exemple
        sample_items = [
            {
                'room_id': room_id,
                'name': 'Sol parquet',
                'category': 'FLOOR',
                'condition': 'GOOD',
                'order': 1,
                'is_mandatory': True
            },
            {
                'room_id': room_id,
                'name': 'Murs peinture',
                'category': 'WALL',
                'condition': 'GOOD',
                'order': 2,
                'is_mandatory': True
            },
            {
                'room_id': room_id,
                'name': 'Fenetre double vitrage',
                'category': 'WINDOW',
                'condition': 'EXCELLENT',
                'order': 3,
                'is_mandatory': True
            }
        ]
        
        for item in sample_items:
            db.execute(text("""
                INSERT INTO inventory_items 
                (room_id, name, category, condition, order, is_mandatory, created_at, updated_at)
                VALUES (:room_id, :name, :category, :condition, :order, :is_mandatory, NOW(), NOW())
            """), item)
        
        db.commit()
        
        print("   OK: Etat des lieux d'exemple cree")
        print(f"      - ID: {inventory_id}")
        print(f"      - Pieces: 1 (Salon)")
        print(f"      - Elements: {len(sample_items)}")
        
        return True
        
    except Exception as e:
        print(f"   ERREUR: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def show_statistics():
    """Affiche les statistiques du système"""
    
    print("\nStatistiques du systeme d'etats des lieux detailles:")
    
    db = SessionLocal()
    try:
        # Compter les enregistrements dans chaque table
        tables_stats = {
            'detailed_inventories': 'Etats des lieux detailles',
            'inventory_rooms': 'Pieces',
            'inventory_items': 'Elements',
            'detailed_inventory_photos': 'Photos d\'inventaire',
            'inventory_item_photos': 'Photos d\'elements',
            'inventory_templates': 'Templates',
            'inventory_signatures': 'Signatures'
        }
        
        for table, description in tables_stats.items():
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"   - {description}: {count}")
            except:
                print(f"   - {description}: N/A")
        
        # Statistiques par statut (si il y a des données)
        try:
            status_stats = db.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM detailed_inventories 
                GROUP BY status
            """)).fetchall()
            
            if status_stats:
                print("\n   Etats des lieux par statut:")
                for status, count in status_stats:
                    print(f"      - {status}: {count}")
        except:
            pass
        
    except Exception as e:
        print(f"   ERREUR: {e}")
    finally:
        db.close()

def show_migration_summary():
    """Affiche un résumé de la migration"""
    
    print("\n" + "="*60)
    print("RESUME DE LA MIGRATION - ETATS DES LIEUX DETAILLES")
    print("="*60)
    
    print("\nNouvelles fonctionnalites:")
    print("1. Etats des lieux detailles piece par piece")
    print("2. Gestion d'elements avec photos et conditions")
    print("3. Templates reutilisables pour differents types de logements")
    print("4. Workflow de signature electronique integre")
    print("5. Suivi photographique complet")
    print("6. Audit trail et historique des modifications")
    
    print("\nEndpoints API principaux:")
    print("   - POST /api/detailed-inventories/ - Creer un etat des lieux")
    print("   - GET /api/detailed-inventories/ - Lister les etats des lieux")
    print("   - POST /api/detailed-inventories/{id}/rooms - Ajouter une piece")
    print("   - POST /api/detailed-inventories/rooms/{id}/items - Ajouter un element")
    print("   - POST /api/detailed-inventories/{id}/photos - Ajouter des photos")
    print("   - POST /api/detailed-inventories/{id}/request-signature - Demander signature")
    print("   - GET /api/detailed-inventories/templates - Templates disponibles")
    
    print("\nProviders de signature supportes:")
    print("   - DocuSign (configuration: DOCUSIGN_API_KEY, DOCUSIGN_ACCOUNT_ID)")
    print("   - HelloSign/Dropbox Sign (configuration: HELLOSIGN_API_KEY)")
    print("   - Adobe Sign (configuration: ADOBE_SIGN_API_KEY)")
    print("   - Mock (pour les tests)")
    
    print("\nStructure des donnees:")
    print("   - Inventaire -> Pieces -> Elements -> Photos")
    print("   - Chaque element peut avoir plusieurs photos")
    print("   - Conditions trackees avec historique")
    print("   - Templates pour standardiser les processus")
    
    print("\nWorkflow complet:")
    print("   1. Creation de l'etat des lieux (DRAFT)")
    print("   2. Ajout des pieces et elements (IN_PROGRESS)")
    print("   3. Upload des photos et finalisation")
    print("   4. Demande de signature electronique (PENDING_SIGNATURE)")
    print("   5. Signature par toutes les parties (SIGNED)")
    print("   6. Finalisation et archivage (COMPLETED)")

def main():
    """Fonction principale"""
    
    print("Migration des etats des lieux detailles - LocAppart")
    print("=" * 60)
    
    # Import JSON pour les templates
    import json
    
    try:
        # 1. Créer les tables
        if not create_detailed_inventory_tables():
            print("ECHEC: Creation des tables")
            return 1
        
        # 2. Vérifier la structure
        if not verify_tables_structure():
            print("ECHEC: Verification de la structure")
            return 1
        
        # 3. Vérifier les relations
        if not verify_foreign_keys():
            print("WARNING: Certaines relations manquantes")
        
        # 4. Créer les templates par défaut
        if not create_default_templates():
            print("WARNING: Templates par defaut non crees")
        
        # 5. Créer un exemple si possible
        if not create_sample_detailed_inventory():
            print("WARNING: Exemple non cree")
        
        # 6. Afficher les statistiques
        show_statistics()
        
        # 7. Afficher le résumé
        show_migration_summary()
        
        print("\nSUCCES: Migration des etats des lieux detailles terminee!")
        print("\nPour utiliser le systeme:")
        print("1. Configurer un provider de signature electronique (.env)")
        print("2. Installer les dependances optionnelles:")
        print("   pip install reportlab  # Pour generation PDF")
        print("   pip install docusign-esign  # Pour DocuSign")
        print("   pip install dropbox-sign  # Pour HelloSign")
        print("3. Demarrer le serveur: uvicorn main:app --reload")
        print("4. Documentation: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"ERREUR FATALE: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())