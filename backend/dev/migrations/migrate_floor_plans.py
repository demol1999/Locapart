#!/usr/bin/env python3
"""
Script de migration pour creer la table des plans 2D
"""

import sys
import os
from sqlalchemy import text

# Ajouter le repertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, FloorPlan

def create_floor_plans_table():
    """Cree la table floor_plans et ses index"""
    
    # Creer toutes les tables qui n'existent pas encore
    print("Creation des tables manquantes...")
    Base.metadata.create_all(bind=engine)
    print("Tables creees avec succes!")
    
    db = SessionLocal()
    try:
        # Verifier que la table a ete creee
        result = db.execute(text("SHOW TABLES LIKE 'floor_plans'"))
        if result.fetchone():
            print("Table 'floor_plans' creee avec succes!")
            
            # Verifier les colonnes
            columns_result = db.execute(text("DESCRIBE floor_plans"))
            columns = columns_result.fetchall()
            
            print("\nStructure de la table 'floor_plans':")
            for column in columns:
                print(f"   - {column[0]} ({column[1]}) {'NOT NULL' if column[2] == 'NO' else 'NULL'}")
            
            # Verifier les index
            indexes_result = db.execute(text("SHOW INDEXES FROM floor_plans"))
            indexes = indexes_result.fetchall()
            
            print("\nIndex crees:")
            unique_indexes = set()
            for index in indexes:
                index_name = index[2]  # Key_name
                if index_name not in unique_indexes:
                    unique_indexes.add(index_name)
                    print(f"   - {index_name}")
            
        else:
            print("Erreur: Table 'floor_plans' non creee")
            return False
            
    except Exception as e:
        print(f"Erreur lors de la verification: {e}")
        return False
    finally:
        db.close()
    
    return True

def verify_relationships():
    """Verifie que les relations avec les autres tables fonctionnent"""
    
    db = SessionLocal()
    try:
        print("\nVerification des relations:")
        
        # Verifier foreign keys
        fk_checks = [
            ("room_id", "rooms", "id"),
            ("apartment_id", "apartments", "id"), 
            ("created_by", "user_auth", "id")
        ]
        
        for fk_column, ref_table, ref_column in fk_checks:
            try:
                query = text(f"""
                    SELECT CONSTRAINT_NAME 
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = 'floor_plans' 
                    AND COLUMN_NAME = '{fk_column}'
                    AND REFERENCED_TABLE_NAME = '{ref_table}'
                    AND REFERENCED_COLUMN_NAME = '{ref_column}'
                """)
                result = db.execute(query)
                constraint = result.fetchone()
                
                if constraint:
                    print(f"   OK: Foreign key {fk_column} -> {ref_table}.{ref_column}")
                else:
                    print(f"   WARNING: Foreign key {fk_column} -> {ref_table}.{ref_column} non trouvee")
                    
            except Exception as e:
                print(f"   ERROR: Erreur verification {fk_column}: {e}")
        
    except Exception as e:
        print(f"Erreur lors de la verification des relations: {e}")
    finally:
        db.close()

def create_sample_data():
    """Cree quelques exemples de plans pour tester"""
    
    db = SessionLocal()
    try:
        # Verifier s'il y a deja des donnees
        existing_count = db.execute(text("SELECT COUNT(*) FROM floor_plans")).scalar()
        
        if existing_count > 0:
            print(f"\nIl y a deja {existing_count} plan(s) dans la base")
            return
        
        print("\nCreation de donnees d'exemple...")
        
        # Verifier qu'il y a des utilisateurs et des appartements/pieces
        user_count = db.execute(text("SELECT COUNT(*) FROM user_auth")).scalar()
        apartment_count = db.execute(text("SELECT COUNT(*) FROM apartments")).scalar()
        room_count = db.execute(text("SELECT COUNT(*) FROM rooms")).scalar()
        
        print(f"   - Utilisateurs: {user_count}")
        print(f"   - Appartements: {apartment_count}")
        print(f"   - Pieces: {room_count}")
        
        if user_count == 0:
            print("WARNING: Aucun utilisateur trouve - impossible de creer des exemples")
            return
        
        # Recuperer le premier utilisateur
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        
        sample_plans = []
        
        # Plan d'exemple simple
        simple_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<floorplan version="1.0" created="2024-01-01T00:00:00">
  <metadata>
    <generator>LocAppart Floor Plan Editor</generator>
    <timestamp>2024-01-01T00:00:00</timestamp>
  </metadata>
  <elements>
    <element id="wall_1" type="wall">
      <wall>
        <start_point x="0" y="0"/>
        <end_point x="400" y="0"/>
        <thickness>15</thickness>
      </wall>
    </element>
    <element id="wall_2" type="wall">
      <wall>
        <start_point x="400" y="0"/>
        <end_point x="400" y="300"/>
        <thickness>15</thickness>
      </wall>
    </element>
    <element id="wall_3" type="wall">
      <wall>
        <start_point x="400" y="300"/>
        <end_point x="0" y="300"/>
        <thickness>15</thickness>
      </wall>
    </element>
    <element id="wall_4" type="wall">
      <wall>
        <start_point x="0" y="300"/>
        <end_point x="0" y="0"/>
        <thickness>15</thickness>
      </wall>
    </element>
  </elements>
</floorplan>'''
        
        sample_plans.append({
            'name': 'Plan d\'exemple - Studio',
            'type': 'room',
            'xml_data': simple_xml,
            'scale': 1.0,
            'grid_size': 20,
            'created_by': first_user
        })
        
        # Inserer les exemples
        for plan_data in sample_plans:
            db.execute(text("""
                INSERT INTO floor_plans (name, type, xml_data, scale, grid_size, created_by, created_at, updated_at)
                VALUES (:name, :type, :xml_data, :scale, :grid_size, :created_by, NOW(), NOW())
            """), plan_data)
        
        db.commit()
        print(f"OK: {len(sample_plans)} plan(s) d'exemple cree(s)")
        
    except Exception as e:
        print(f"Erreur lors de la creation des exemples: {e}")
        db.rollback()
    finally:
        db.close()

def show_statistics():
    """Affiche les statistiques de la table"""
    
    db = SessionLocal()
    try:
        print("\nStatistiques des plans 2D:")
        
        # Statistiques generales
        total_plans = db.execute(text("SELECT COUNT(*) FROM floor_plans")).scalar()
        print(f"   - Total plans: {total_plans}")
        
        if total_plans > 0:
            # Par type
            type_stats = db.execute(text("""
                SELECT type, COUNT(*) as count 
                FROM floor_plans 
                GROUP BY type
            """)).fetchall()
            
            print("   - Par type:")
            for type_name, count in type_stats:
                print(f"     * {type_name}: {count}")
            
            # Plans recents
            recent_plans = db.execute(text("""
                SELECT name, type, created_at 
                FROM floor_plans 
                ORDER BY created_at DESC 
                LIMIT 5
            """)).fetchall()
            
            print("   - Plans recents:")
            for name, plan_type, created_at in recent_plans:
                print(f"     * {name} ({plan_type}) - {created_at}")
        
    except Exception as e:
        print(f"Erreur lors du calcul des statistiques: {e}")
    finally:
        db.close()

def main():
    """Fonction principale"""
    
    print("Migration des plans 2D - LocAppart")
    print("=" * 50)
    
    try:
        # 1. Creer la table
        if not create_floor_plans_table():
            print("ERREUR: Echec de la creation de la table")
            return 1
        
        # 2. Verifier les relations
        verify_relationships()
        
        # 3. Creer des donnees d'exemple
        create_sample_data()
        
        # 4. Afficher les statistiques
        show_statistics()
        
        print("\nSUCCES: Migration terminee avec succes!")
        print("\nPour tester le systeme:")
        print("1. Demarrez le backend: uvicorn main:app --reload")
        print("2. Accedez a l'editeur de plans via l'interface")
        print("3. Creez votre premier plan 2D!")
        
    except Exception as e:
        print(f"ERREUR FATALE: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())