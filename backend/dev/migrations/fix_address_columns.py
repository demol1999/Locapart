#!/usr/bin/env python3
"""
Migration pour augmenter la taille des colonnes d'adresse
"""

from database import engine
from sqlalchemy import text

def fix_address_column_sizes():
    """Augmente la taille des colonnes d'adresse pour permettre des adresses plus longues"""
    
    print("Migration des tailles de colonnes d'adresse...")
    
    # Commandes SQL pour augmenter la taille des colonnes
    migrations = [
        "ALTER TABLE user_auth MODIFY COLUMN street_number VARCHAR(100) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN street_name VARCHAR(500) NULL", 
        "ALTER TABLE user_auth MODIFY COLUMN complement VARCHAR(500) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN postal_code VARCHAR(50) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN city VARCHAR(200) NULL",
        "ALTER TABLE user_auth MODIFY COLUMN country VARCHAR(200) NULL"
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

def check_new_sizes():
    """Vérifie les nouvelles tailles des colonnes"""
    
    print("\nVerification des nouvelles tailles:")
    
    with engine.connect() as connection:
        result = connection.execute(text("DESCRIBE user_auth"))
        columns = result.fetchall()
        
        print("Colonnes d'adresse:")
        address_fields = ['street_number', 'street_name', 'complement', 'postal_code', 'city', 'country']
        
        for column in columns:
            if column[0] in address_fields:
                print(f"  - {column[0]}: {column[1]}")

if __name__ == "__main__":
    fix_address_column_sizes()
    check_new_sizes()