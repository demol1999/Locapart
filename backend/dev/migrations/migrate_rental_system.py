#!/usr/bin/env python3
"""
Script de migration pour le système de gestion locative
"""

import sys
import os
from sqlalchemy import text

# Ajouter le repertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, Tenant, Lease, TenantDocument, Inventory, InventoryPhoto

def create_rental_tables():
    """Cree les tables du système de gestion locative"""
    
    print("Creation des tables de gestion locative...")
    Base.metadata.create_all(bind=engine)
    print("Tables creees avec succes!")
    
    db = SessionLocal()
    try:
        # Verifier les tables creees
        tables_to_check = ['tenants', 'leases', 'tenant_documents', 'inventories', 'inventory_photos']
        
        print("\nVerification des tables creees:")
        for table_name in tables_to_check:
            result = db.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
            if result.fetchone():
                print(f"   OK: Table '{table_name}' creee")
                
                # Afficher la structure de la table
                columns_result = db.execute(text(f"DESCRIBE {table_name}"))
                columns = columns_result.fetchall()
                print(f"      Colonnes ({len(columns)}): {', '.join([col[0] for col in columns[:5]])}{'...' if len(columns) > 5 else ''}")
            else:
                print(f"   ERREUR: Table '{table_name}' non creee")
                return False
        
        # Verifier les index
        print("\nVerification des index:")
        for table_name in tables_to_check:
            try:
                indexes_result = db.execute(text(f"SHOW INDEXES FROM {table_name}"))
                indexes = indexes_result.fetchall()
                unique_indexes = set([idx[2] for idx in indexes])  # Key_name
                print(f"   {table_name}: {len(unique_indexes)} index")
            except Exception as e:
                print(f"   Erreur verification index {table_name}: {e}")
        
    except Exception as e:
        print(f"Erreur lors de la verification: {e}")
        return False
    finally:
        db.close()
    
    return True

def verify_relationships():
    """Verifie les relations entre les tables"""
    
    db = SessionLocal()
    try:
        print("\nVerification des relations:")
        
        # Relations à vérifier
        relations = [
            ("leases", "tenant_id", "tenants", "id"),
            ("leases", "apartment_id", "apartments", "id"),
            ("leases", "created_by", "user_auth", "id"),
            ("tenant_documents", "tenant_id", "tenants", "id"),
            ("tenant_documents", "lease_id", "leases", "id"),
            ("tenant_documents", "uploaded_by", "user_auth", "id"),
            ("inventories", "lease_id", "leases", "id"),
            ("inventories", "conducted_by", "user_auth", "id"),
            ("inventory_photos", "inventory_id", "inventories", "id"),
            ("inventory_photos", "photo_id", "photos", "id")
        ]
        
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
                else:
                    print(f"   WARNING: Relation {table}.{column} -> {ref_table}.{ref_column} non trouvee")
                    
            except Exception as e:
                print(f"   ERROR: {table}.{column}: {e}")
        
    except Exception as e:
        print(f"Erreur lors de la verification des relations: {e}")
    finally:
        db.close()

def create_sample_data():
    """Cree des donnees d'exemple pour tester le système"""
    
    db = SessionLocal()
    try:
        # Verifier s'il y a deja des donnees
        existing_tenants = db.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
        
        if existing_tenants > 0:
            print(f"\nIl y a deja {existing_tenants} locataire(s) dans la base")
            return
        
        print("\nCreation de donnees d'exemple...")
        
        # Verifier les prerequis
        user_count = db.execute(text("SELECT COUNT(*) FROM user_auth")).scalar()
        apartment_count = db.execute(text("SELECT COUNT(*) FROM apartments")).scalar()
        
        print(f"   - Utilisateurs: {user_count}")
        print(f"   - Appartements: {apartment_count}")
        
        if user_count == 0:
            print("WARNING: Aucun utilisateur trouve - impossible de creer des exemples")
            return
        
        if apartment_count == 0:
            print("WARNING: Aucun appartement trouve - creation d'exemples limitee")
        
        # Recuperer le premier utilisateur
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        
        # Creer un locataire d'exemple
        sample_tenant_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean.dupont@email.com',
            'phone': '0123456789',
            'occupation': 'Ingenieur',
            'monthly_income': 3500.00,
            'notes': 'Locataire d exemple cree par la migration'
        }
        
        db.execute(text("""
            INSERT INTO tenants (first_name, last_name, email, phone, occupation, monthly_income, notes, created_at, updated_at)
            VALUES (:first_name, :last_name, :email, :phone, :occupation, :monthly_income, :notes, NOW(), NOW())
        """), sample_tenant_data)
        
        # Recuperer l'ID du locataire cree
        tenant_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # Creer un bail si il y a des appartements
        if apartment_count > 0:
            first_apartment = db.execute(text("SELECT id FROM apartments LIMIT 1")).scalar()
            
            sample_lease_data = {
                'tenant_id': tenant_id,
                'apartment_id': first_apartment,
                'created_by': first_user,
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'monthly_rent': 800.00,
                'charges': 150.00,
                'deposit': 800.00,
                'status': 'ACTIVE'
            }
            
            db.execute(text("""
                INSERT INTO leases (tenant_id, apartment_id, created_by, start_date, end_date, 
                                   monthly_rent, charges, deposit, status, created_at, updated_at)
                VALUES (:tenant_id, :apartment_id, :created_by, :start_date, :end_date,
                        :monthly_rent, :charges, :deposit, :status, NOW(), NOW())
            """), sample_lease_data)
            
            print("OK: 1 locataire et 1 bail d'exemple crees")
        else:
            print("OK: 1 locataire d'exemple cree (pas de bail sans appartement)")
        
        db.commit()
        
    except Exception as e:
        print(f"Erreur lors de la creation des exemples: {e}")
        db.rollback()
    finally:
        db.close()

def show_statistics():
    """Affiche les statistiques du système"""
    
    db = SessionLocal()
    try:
        print("\nStatistiques du système de gestion locative:")
        
        # Statistiques generales
        stats = {
            'tenants': db.execute(text("SELECT COUNT(*) FROM tenants")).scalar(),
            'leases': db.execute(text("SELECT COUNT(*) FROM leases")).scalar(),
            'documents': db.execute(text("SELECT COUNT(*) FROM tenant_documents")).scalar(),
            'inventories': db.execute(text("SELECT COUNT(*) FROM inventories")).scalar()
        }
        
        for entity, count in stats.items():
            print(f"   - {entity.title()}: {count}")
        
        # Statistiques des baux par statut
        if stats['leases'] > 0:
            lease_stats = db.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM leases 
                GROUP BY status
            """)).fetchall()
            
            print("   - Baux par statut:")
            for status, count in lease_stats:
                print(f"     * {status}: {count}")
        
        # Documents par type
        if stats['documents'] > 0:
            doc_stats = db.execute(text("""
                SELECT document_type, COUNT(*) as count 
                FROM tenant_documents 
                GROUP BY document_type
            """)).fetchall()
            
            print("   - Documents par type:")
            for doc_type, count in doc_stats:
                print(f"     * {doc_type}: {count}")
        
    except Exception as e:
        print(f"Erreur lors du calcul des statistiques: {e}")
    finally:
        db.close()

def main():
    """Fonction principale"""
    
    print("Migration du système de gestion locative - LocAppart")
    print("=" * 60)
    
    try:
        # 1. Creer les tables
        if not create_rental_tables():
            print("ERREUR: Echec de la creation des tables")
            return 1
        
        # 2. Verifier les relations
        verify_relationships()
        
        # 3. Creer des donnees d'exemple
        create_sample_data()
        
        # 4. Afficher les statistiques
        show_statistics()
        
        print("\nSUCCES: Migration du système de gestion locative terminee!")
        print("\nFonctionnalites disponibles:")
        print("1. Gestion des locataires (/api/tenants)")
        print("2. Gestion des baux (/api/leases)")
        print("3. Gestion des documents (/api/documents)")
        print("4. Etats des lieux (/api/documents/inventories)")
        print("5. Espace locataire (/api/tenant-portal)")
        print("\nDemarrage:")
        print("uvicorn main:app --reload")
        print("Documentation: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"ERREUR FATALE: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())