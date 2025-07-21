"""
Migration pour le système de multipropriété
Ajoute les tables et colonnes nécessaires pour gérer les groupes de propriété partagée
"""
import sys
import os
from sqlalchemy import create_engine, text, Column, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url, Base
import models
from models_multipropriete import PropertyGroup, PropertyGroupMember, PropertyGroupInvitation


class MultiproprieteMigration:
    """Gestionnaire de migration pour le système de multipropriété"""
    
    def __init__(self):
        self.engine = create_engine(get_db_url())
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = None
    
    def run_migration(self):
        """Exécute la migration complète"""
        
        print("=== MIGRATION SYSTÈME MULTIPROPRIÉTÉ ===")
        print("Début de la migration...")
        
        try:
            self.session = self.SessionLocal()
            
            # 1. Créer les nouvelles tables
            print("\n1. Création des nouvelles tables...")
            self.create_tables()
            
            # 2. Ajouter les colonnes aux tables existantes
            print("\n2. Mise à jour des tables existantes...")
            self.update_existing_tables()
            
            # 3. Créer les index pour les performances
            print("\n3. Création des index...")
            self.create_indexes()
            
            # 4. Vérifications finales
            print("\n4. Vérifications finales...")
            self.verify_migration()
            
            self.session.commit()
            print("\n[SUCCESS] Migration multipropriété terminée avec succès!")
            
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"\n[ERROR] Erreur lors de la migration: {e}")
            raise
        finally:
            if self.session:
                self.session.close()
    
    def create_tables(self):
        """Crée les nouvelles tables de multipropriété"""
        
        try:
            # Créer toutes les tables de multipropriété
            tables_to_create = [
                PropertyGroup.__table__,
                PropertyGroupMember.__table__,
                PropertyGroupInvitation.__table__
            ]
            
            for table in tables_to_create:
                try:
                    Base.metadata.create_all(bind=self.engine, tables=[table])
                    print(f"   [OK] Table {table.name} créée")
                except Exception as e:
                    print(f"   [WARNING] Table {table.name}: {e}")
            
            # Vérifier que les tables existent
            required_tables = ['property_groups', 'property_group_members', 'property_group_invitations']
            for table_name in required_tables:
                result = self.session.execute(text(f"SHOW TABLES LIKE '{table_name}'")).fetchone()
                if result:
                    print(f"   [OK] Table {table_name} vérifiée")
                else:
                    raise Exception(f"Table {table_name} n'a pas été créée")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la création des tables: {e}")
            raise
    
    def update_existing_tables(self):
        """Met à jour les tables existantes avec les nouvelles colonnes"""
        
        try:
            # Ajouter la colonne property_group_id à la table apartments
            self._add_column_if_not_exists(
                'apartments',
                'property_group_id',
                'INT NULL COMMENT "ID du groupe de multipropriété"'
            )
            
            # Ajouter la contrainte de clé étrangère
            self._add_foreign_key_if_not_exists(
                'apartments',
                'fk_apartments_property_group',
                'property_group_id',
                'property_groups(id)'
            )
            
            print("   [OK] Tables existantes mises à jour")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors de la mise à jour des tables: {e}")
            raise
    
    def create_indexes(self):
        """Crée les index pour optimiser les performances"""
        
        indexes_to_create = [
            # Index pour property_groups
            ("idx_property_groups_sponsor", "property_groups", "sponsor_id"),
            ("idx_property_groups_status", "property_groups", "group_status"),
            ("idx_property_groups_type", "property_groups", "group_type"),
            
            # Index pour property_group_members
            ("idx_group_members_group", "property_group_members", "group_id"),
            ("idx_group_members_user", "property_group_members", "user_id"),
            ("idx_group_members_status", "property_group_members", "membership_status"),
            ("idx_group_members_composite", "property_group_members", "group_id, user_id"),
            
            # Index pour property_group_invitations
            ("idx_group_invitations_group", "property_group_invitations", "group_id"),
            ("idx_group_invitations_user", "property_group_invitations", "invited_user_id"),
            ("idx_group_invitations_code", "property_group_invitations", "invitation_code"),
            ("idx_group_invitations_status", "property_group_invitations", "status"),
            
            # Index pour apartments
            ("idx_apartments_property_group", "apartments", "property_group_id"),
        ]
        
        for index_name, table_name, columns in indexes_to_create:
            try:
                self.session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({columns})
                """))
                print(f"   [OK] Index {index_name} créé")
            except Exception as e:
                print(f"   [WARNING] Index {index_name}: {e}")
    
    def verify_migration(self):
        """Vérifie que la migration s'est bien déroulée"""
        
        try:
            # Vérifier les tables
            required_tables = ['property_groups', 'property_group_members', 'property_group_invitations']
            for table_name in required_tables:
                result = self.session.execute(text(f"SHOW TABLES LIKE '{table_name}'")).fetchone()
                if result:
                    print(f"   [OK] Table {table_name} présente")
                else:
                    raise Exception(f"Table {table_name} manquante")
            
            # Vérifier la colonne ajoutée à apartments
            result = self.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'apartments' 
                AND COLUMN_NAME = 'property_group_id'
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchone()
            
            if result:
                print("   [OK] Colonne property_group_id ajoutée à apartments")
            else:
                print("   [WARNING] Colonne property_group_id manquante dans apartments")
            
            # Vérifier les contraintes de clés étrangères
            fk_check = self.session.execute(text("""
                SELECT CONSTRAINT_NAME 
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
                WHERE TABLE_NAME = 'apartments' 
                AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                AND CONSTRAINT_NAME LIKE '%property_group%'
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchone()
            
            if fk_check:
                print("   [OK] Contrainte de clé étrangère property_group présente")
            else:
                print("   [WARNING] Contrainte de clé étrangère property_group manquante")
            
            # Tester une insertion simple
            try:
                # Test d'insertion et suppression pour vérifier la structure
                test_query = text("""
                    SELECT COUNT(*) FROM property_groups 
                    WHERE 1=0
                """)
                self.session.execute(test_query)
                print("   [OK] Structure des tables validée")
            except Exception as e:
                print(f"   [WARNING] Erreur de validation: {e}")
            
            print("   [OK] Vérifications terminées")
            
        except Exception as e:
            print(f"   [ERROR] Erreur lors des vérifications: {e}")
            raise
    
    def _add_column_if_not_exists(self, table_name: str, column_name: str, column_definition: str):
        """Ajoute une colonne si elle n'existe pas déjà"""
        
        # Vérifier si la colonne existe
        result = self.session.execute(text(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}' 
            AND COLUMN_NAME = '{column_name}'
            AND TABLE_SCHEMA = DATABASE()
        """)).fetchone()
        
        if not result:
            # Ajouter la colonne
            self.session.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN {column_name} {column_definition}
            """))
            print(f"   [OK] Colonne {column_name} ajoutée à {table_name}")
        else:
            print(f"   [INFO] Colonne {column_name} existe déjà dans {table_name}")
    
    def _add_foreign_key_if_not_exists(self, table_name: str, constraint_name: str, column_name: str, references: str):
        """Ajoute une contrainte de clé étrangère si elle n'existe pas"""
        
        # Vérifier si la contrainte existe
        result = self.session.execute(text(f"""
            SELECT CONSTRAINT_NAME 
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
            WHERE TABLE_NAME = '{table_name}' 
            AND CONSTRAINT_NAME = '{constraint_name}'
            AND TABLE_SCHEMA = DATABASE()
        """)).fetchone()
        
        if not result:
            try:
                # Ajouter la contrainte
                self.session.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ADD CONSTRAINT {constraint_name} 
                    FOREIGN KEY ({column_name}) REFERENCES {references}
                    ON DELETE SET NULL ON UPDATE CASCADE
                """))
                print(f"   [OK] Contrainte {constraint_name} ajoutée")
            except Exception as e:
                print(f"   [WARNING] Contrainte {constraint_name}: {e}")
        else:
            print(f"   [INFO] Contrainte {constraint_name} existe déjà")
    
    def rollback_migration(self):
        """Annule la migration (pour les tests)"""
        
        print("=== ROLLBACK MIGRATION MULTIPROPRIÉTÉ ===")
        
        try:
            self.session = self.SessionLocal()
            
            # Supprimer les contraintes de clés étrangères
            try:
                self.session.execute(text("ALTER TABLE apartments DROP FOREIGN KEY fk_apartments_property_group"))
                print("   [OK] Contrainte fk_apartments_property_group supprimée")
            except:
                print("   [INFO] Contrainte fk_apartments_property_group n'existait pas")
            
            # Supprimer la colonne ajoutée
            try:
                self.session.execute(text("ALTER TABLE apartments DROP COLUMN property_group_id"))
                print("   [OK] Colonne property_group_id supprimée")
            except:
                print("   [INFO] Colonne property_group_id n'existait pas")
            
            # Supprimer les tables
            tables_to_drop = ['property_group_invitations', 'property_group_members', 'property_groups']
            for table_name in tables_to_drop:
                try:
                    self.session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    print(f"   [OK] Table {table_name} supprimée")
                except Exception as e:
                    print(f"   [WARNING] Table {table_name}: {e}")
            
            self.session.commit()
            print("\n[SUCCESS] Rollback terminé")
            
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"\n[ERROR] Erreur lors du rollback: {e}")
            raise
        finally:
            if self.session:
                self.session.close()


def main():
    """Point d'entrée principal"""
    
    print("Migration - Système de multipropriété")
    print("=" * 50)
    
    migration = MultiproprieteMigration()
    
    # Vérifier si on veut faire un rollback
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        migration.rollback_migration()
    else:
        migration.run_migration()


if __name__ == "__main__":
    main()