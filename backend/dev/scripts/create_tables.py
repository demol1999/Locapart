#!/usr/bin/env python3
"""
Script pour créer/mettre à jour toutes les tables de la base de données
"""

from database import engine
import models

def create_all_tables():
    """Crée toutes les tables définies dans models.py"""
    print("Creation des tables...")
    
    try:
        # Créer toutes les tables
        models.Base.metadata.create_all(bind=engine)
        print("Tables creees avec succes!")
        
        # Lister les tables créées
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\nTables disponibles ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")
            
    except Exception as e:
        print(f"Erreur lors de la creation des tables: {str(e)}")

if __name__ == "__main__":
    create_all_tables()