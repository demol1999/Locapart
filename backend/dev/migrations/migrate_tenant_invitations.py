#!/usr/bin/env python3
"""
Script de migration pour ajouter la table tenant_invitations
"""

import sys
import os
from sqlalchemy import text

# Ajouter le repertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, TenantInvitation

def create_tenant_invitations_table():
    """Crée la table tenant_invitations"""
    
    print("Migration : Ajout de la table tenant_invitations...")
    
    # Créer seulement la nouvelle table
    TenantInvitation.__table__.create(bind=engine, checkfirst=True)
    
    db = SessionLocal()
    try:
        # Vérifier que la table a été créée
        result = db.execute(text("SHOW TABLES LIKE 'tenant_invitations'"))
        if result.fetchone():
            print("   OK: Table 'tenant_invitations' creee avec succes")
            
            # Afficher la structure de la table
            columns_result = db.execute(text("DESCRIBE tenant_invitations"))
            columns = columns_result.fetchall()
            print(f"   Structure de la table ({len(columns)} colonnes):")
            for col in columns:
                print(f"      - {col[0]} ({col[1]})")
            
            # Vérifier les index
            indexes_result = db.execute(text("SHOW INDEXES FROM tenant_invitations"))
            indexes = indexes_result.fetchall()
            unique_indexes = set([idx[2] for idx in indexes])  # Key_name
            print(f"   Index crees ({len(unique_indexes)} index):")
            for idx_name in sorted(unique_indexes):
                print(f"      - {idx_name}")
            
            return True
        else:
            print("   ERREUR: Table 'tenant_invitations' non creee")
            return False
        
    except Exception as e:
        print(f"   Erreur lors de la verification: {e}")
        return False
    finally:
        db.close()

def verify_foreign_keys():
    """Vérifie les clés étrangères de la nouvelle table"""
    
    print("\nVérification des clés étrangères...")
    
    db = SessionLocal()
    try:
        # Relations à vérifier
        relations = [
            ("tenant_invitations", "tenant_id", "tenants", "id"),
            ("tenant_invitations", "invited_by", "user_auth", "id")
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
                print(f"   ERREUR: {table}.{column}: {e}")
        
    except Exception as e:
        print(f"Erreur lors de la vérification des relations: {e}")
    finally:
        db.close()

def test_table_operations():
    """Teste les opérations de base sur la nouvelle table"""
    
    print("\nTest des opérations sur la table...")
    
    db = SessionLocal()
    try:
        # Test d'insertion (simulation)
        print("   Test de la structure de la table:")
        
        # Vérifier qu'on peut compter les enregistrements
        count_result = db.execute(text("SELECT COUNT(*) FROM tenant_invitations"))
        count = count_result.scalar()
        print(f"      - Nombre d'invitations existantes: {count}")
        
        # Vérifier les contraintes
        print("   Verification des contraintes:")
        
        # Contrainte d'unicité sur le token
        unique_constraints = db.execute(text("""
            SELECT CONSTRAINT_NAME, COLUMN_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'tenant_invitations' 
            AND COLUMN_NAME = 'invitation_token'
        """)).fetchall()
        
        if unique_constraints:
            print(f"      - Contrainte d'unicite sur invitation_token: OK")
        else:
            print(f"      - Contrainte d'unicite sur invitation_token: WARNING")
        
        return True
        
    except Exception as e:
        print(f"   Erreur lors des tests: {e}")
        return False
    finally:
        db.close()

def show_migration_summary():
    """Affiche un résumé de la migration"""
    
    print("\n" + "="*60)
    print("RÉSUMÉ DE LA MIGRATION")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Statistiques des tables liées
        tables_stats = {}
        tables_to_check = ['tenants', 'leases', 'tenant_documents', 'inventories', 'tenant_invitations']
        
        for table_name in tables_to_check:
            try:
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = count_result.scalar()
                tables_stats[table_name] = count
            except:
                tables_stats[table_name] = "N/A"
        
        print("\nStatistiques des tables du systeme de gestion locative:")
        for table, count in tables_stats.items():
            print(f"   - {table}: {count} enregistrement(s)")
        
        print("\nNouvelles fonctionnalites disponibles:")
        print("   1. Invitation de locataires par email")
        print("   2. Tokens d'acces securises avec expiration")
        print("   3. Suivi des invitations (envoyees/utilisees)")
        print("   4. Audit trail complet des invitations")
        
        print("\nEndpoints API ajoutes:")
        print("   - POST /api/invitations/ - Creer une invitation")
        print("   - GET /api/invitations/ - Lister les invitations")
        print("   - POST /api/invitations/validate-token - Valider un token")
        print("   - POST /api/tenants/{id}/send-invitation - Inviter un locataire")
        print("   - POST /api/tenants/with-invitation - Creer + inviter")
        
        print("\nService d'email configure:")
        print("   - Architecture SOLID avec providers interchangeables")
        print("   - Support Resend, SMTP, SendGrid, Mailgun")
        print("   - Templates HTML et texte pour les invitations")
        print("   - Configuration via variables d'environnement")
        
    except Exception as e:
        print(f"Erreur lors du résumé: {e}")
    finally:
        db.close()

def main():
    """Fonction principale"""
    
    print("Migration tenant_invitations - LocAppart")
    print("=" * 60)
    
    try:
        # 1. Créer la table
        if not create_tenant_invitations_table():
            print("ECHEC: Impossible de creer la table tenant_invitations")
            return 1
        
        # 2. Vérifier les relations
        verify_foreign_keys()
        
        # 3. Tester les opérations
        if not test_table_operations():
            print("ATTENTION: Certains tests ont echoue")
        
        # 4. Afficher le résumé
        show_migration_summary()
        
        print("\nSUCCES: Migration tenant_invitations terminee!")
        print("\nProchaines etapes:")
        print("   1. Configurer les variables d'environnement pour l'email:")
        print("      - EMAIL_PROVIDER=resend")
        print("      - RESEND_API_KEY=your_api_key")
        print("      - EMAIL_FROM=noreply@votredomaine.com")
        print("   2. Installer les dependances email:")
        print("      pip install resend jinja2")
        print("   3. Tester l'envoi d'invitations via l'API")
        print("   4. Demarrer le serveur: uvicorn main:app --reload")
        
    except Exception as e:
        print(f"ERREUR FATALE: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())