#!/usr/bin/env python3
"""
Script de migration pour ajouter les colonnes OAuth à la table user_auth
"""

from database import engine
from sqlalchemy import text

def migrate_oauth_columns():
    """Ajoute les colonnes OAuth à la table user_auth si elles n'existent pas"""
    
    print("Migration des colonnes OAuth...")
    
    # Commandes SQL pour ajouter les nouvelles colonnes
    migrations = [
        "ALTER TABLE user_auth ADD COLUMN auth_type ENUM('EMAIL_PASSWORD', 'GOOGLE_OAUTH', 'FACEBOOK_OAUTH', 'MICROSOFT_OAUTH') DEFAULT 'EMAIL_PASSWORD'",
        "ALTER TABLE user_auth ADD COLUMN oauth_provider_id VARCHAR(255) NULL",
        "ALTER TABLE user_auth ADD COLUMN oauth_avatar_url VARCHAR(500) NULL",
        "ALTER TABLE user_auth ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"
    ]
    
    with engine.connect() as connection:
        for i, migration in enumerate(migrations, 1):
            try:
                print(f"  {i}. Ajout de la colonne...")
                connection.execute(text(migration))
                connection.commit()
                print(f"     Reussi")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"     Colonne deja existante (ignore)")
                else:
                    print(f"     Erreur: {str(e)}")
    
    print("Migration terminee!")

def check_columns():
    """Verifie les colonnes de la table user_auth"""
    
    print("\nVerification des colonnes de la table user_auth:")
    
    with engine.connect() as connection:
        result = connection.execute(text("DESCRIBE user_auth"))
        columns = result.fetchall()
        
        for column in columns:
            print(f"  - {column[0]} ({column[1]})")

if __name__ == "__main__":
    migrate_oauth_columns()
    check_columns()