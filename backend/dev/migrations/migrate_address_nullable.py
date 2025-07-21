#!/usr/bin/env python3
"""
Migration pour rendre les champs d'adresse nullable dans user_auth
"""

from database import engine
from sqlalchemy import text

def migrate_address_nullable():
    """Rend les champs d'adresse nullable dans la table user_auth"""
    
    print("Migration des champs d'adresse vers nullable...")
    
    # Commandes SQL pour modifier les colonnes
    migrations = [
        "ALTER TABLE user_auth MODIFY COLUMN street_number VARCHAR(20) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN street_name VARCHAR(255) NULL", 
        "ALTER TABLE user_auth MODIFY COLUMN complement VARCHAR(255) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN postal_code VARCHAR(20) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN city VARCHAR(100) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN country VARCHAR(100) NULL"
    ]
    
    with engine.connect() as connection:
        for i, migration in enumerate(migrations, 1):
            try:
                print(f"  {i}. Modification de la colonne...")
                connection.execute(text(migration))
                connection.commit()
                print(f"     Reussi")
            except Exception as e:
                print(f"     Erreur: {str(e)}")
    
    print("Migration terminee!")

def check_table_structure():
    """Vérifie la structure de la table user_auth"""
    
    print("\nVerification de la structure de la table user_auth:")
    
    with engine.connect() as connection:
        result = connection.execute(text("DESCRIBE user_auth"))
        columns = result.fetchall()
        
        print("Colonnes d'adresse:")
        address_fields = ['street_number', 'street_name', 'complement', 'postal_code', 'city', 'country']
        
        for column in columns:
            if column[0] in address_fields:
                nullable = "NULL" if column[2] == "YES" else "NOT NULL"
                print(f"  - {column[0]}: {column[1]} ({nullable})")

if __name__ == "__main__":
    migrate_address_nullable()
    check_table_structure()