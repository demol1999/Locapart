"""
Migration pour le système de vérification d'email
"""
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url, Base
from email_verification_service import EmailVerification
import models  # Importer tous les modèles pour résoudre les dépendances

class EmailVerificationMigration:
    """Gestionnaire de migration pour la vérification d'email"""
    
    def __init__(self):
        self.engine = create_engine(get_db_url())
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = None
    
    def run_migration(self):
        """Exécute la migration complète"""
        
        print("=== MIGRATION VERIFICATION EMAIL ===")
        print("Debut de la migration...")
        
        try:
            self.session = self.SessionLocal()
            
            # 1. Créer les tables
            print("\n1. Creation des tables...")
            self.create_tables()
            
            # 2. Ajouter les colonnes manquantes au modèle User
            print("\n2. Mise a jour du modele User...")
            self.update_user_model()
            
            # 3. Marquer les utilisateurs OAuth comme vérifiés
            print("\n3. Mise a jour des utilisateurs OAuth...")
            self.update_oauth_users()
            
            # 4. Vérifications finales
            print("\n4. Verifications finales...")
            self.verify_migration()
            
            self.session.commit()
            print("\n[SUCCESS] Migration terminee avec succes!")
            
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"\n[ERROR] Erreur lors de la migration: {e}")
            raise
        finally:
            if self.session:
                self.session.close()
    
    def create_tables(self):
        """Crée les nouvelles tables"""
        
        try:
            # Créer la table de vérification d'email
            Base.metadata.create_all(bind=self.engine, tables=[EmailVerification.__table__])
            print("   [OK] Table email_verifications creee")
            
            # Vérifier que la table existe
            result = self.session.execute(text("SHOW TABLES LIKE 'email_verifications'")).fetchone()
            if not result:
                raise Exception("Table email_verifications n'a pas ete creee")
            
            print("   [OK] Table email_verifications verifiee")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la creation des tables: {e}")
            raise
    
    def update_user_model(self):
        """Met à jour le modèle User avec les nouvelles colonnes"""
        
        try:
            # Vérifier si les colonnes existent déjà
            columns_to_add = [
                ("email_verified_at", "DATETIME NULL COMMENT 'Date de verification email'")
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    # Vérifier si la colonne existe
                    result = self.session.execute(text(f"""
                        SELECT COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = 'user_auth' 
                        AND COLUMN_NAME = '{column_name}'
                        AND TABLE_SCHEMA = DATABASE()
                    """)).fetchone()
                    
                    if not result:
                        # Ajouter la colonne
                        self.session.execute(text(f"""
                            ALTER TABLE user_auth 
                            ADD COLUMN {column_name} {column_def}
                        """))
                        print(f"   [OK] Colonne {column_name} ajoutee")
                    else:
                        print(f"   [INFO] Colonne {column_name} existe deja")
                        
                except Exception as e:
                    print(f"   [WARNING] Erreur avec la colonne {column_name}: {e}")
            
            # S'assurer que email_verified existe et est Boolean
            try:
                # Vérifier le type de la colonne email_verified
                result = self.session.execute(text("""
                    SELECT DATA_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'user_auth' 
                    AND COLUMN_NAME = 'email_verified'
                    AND TABLE_SCHEMA = DATABASE()
                """)).fetchone()
                
                if not result:
                    # Ajouter la colonne email_verified
                    self.session.execute(text("""
                        ALTER TABLE user_auth 
                        ADD COLUMN email_verified BOOLEAN DEFAULT FALSE COMMENT 'Email verifie'
                    """))
                    print("   [OK] Colonne email_verified ajoutee")
                else:
                    print("   [INFO] Colonne email_verified existe deja")
                    
            except Exception as e:
                print(f"   [WARNING] Erreur avec email_verified: {e}")
            
            print("   [OK] Modele User mis a jour")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la mise a jour du modele: {e}")
            raise
    
    def update_oauth_users(self):
        """Marque les utilisateurs OAuth comme ayant un email vérifié"""
        
        try:
            # Mettre à jour les utilisateurs OAuth
            oauth_types = ['GOOGLE_OAUTH', 'FACEBOOK_OAUTH', 'MICROSOFT_OAUTH']
            
            for auth_type in oauth_types:
                result = self.session.execute(text(f"""
                    UPDATE user_auth 
                    SET email_verified = TRUE,
                        email_verified_at = NOW()
                    WHERE auth_type = '{auth_type}' 
                    AND (email_verified IS NULL OR email_verified = FALSE)
                """))
                
                count = result.rowcount
                if count > 0:
                    print(f"   [OK] {count} utilisateurs {auth_type} marques comme verifies")
            
            print("   [OK] Utilisateurs OAuth mis a jour")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la mise a jour OAuth: {e}")
            raise
    
    def verify_migration(self):
        """Vérifie que la migration s'est bien déroulée"""
        
        try:
            # Vérifier que la table existe
            result = self.session.execute(text("SHOW TABLES LIKE 'email_verifications'")).fetchone()
            if not result:
                raise Exception("Table email_verifications manquante")
            
            # Vérifier les colonnes de user_auth
            result = self.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'user_auth' 
                AND COLUMN_NAME IN ('email_verified', 'email_verified_at')
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchall()
            
            found_columns = [row[0] for row in result]
            required_columns = ['email_verified', 'email_verified_at']
            
            for col in required_columns:
                if col in found_columns:
                    print(f"   [OK] Colonne {col} presente")
                else:
                    print(f"   [WARNING] Colonne {col} manquante")
            
            # Compter les utilisateurs OAuth vérifiés
            result = self.session.execute(text("""
                SELECT COUNT(*) 
                FROM user_auth 
                WHERE auth_type IN ('GOOGLE_OAUTH', 'FACEBOOK_OAUTH', 'MICROSOFT_OAUTH')
                AND email_verified = TRUE
            """)).scalar()
            
            print(f"   [INFO] {result} utilisateurs OAuth verifies")
            
            print("   [OK] Verifications terminees")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors des verifications: {e}")
            raise


def main():
    """Point d'entree principal"""
    
    print("Migration - Systeme de verification d'email")
    print("=" * 50)
    
    migration = EmailVerificationMigration()
    migration.run_migration()


if __name__ == "__main__":
    main()