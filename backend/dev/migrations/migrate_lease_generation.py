#!/usr/bin/env python3
"""
Script de migration pour le système de génération de baux
"""

import sys
import os
from sqlalchemy import text
import json

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models  # Import des modèles principaux
from lease_template_models import (
    LeaseTemplate, GeneratedLease, LeaseSignature, LeaseClause,
    create_standard_unfurnished_lease_template,
    create_furnished_lease_template,
    create_student_lease_template
)


def create_lease_generation_tables():
    """Crée les tables pour la génération de baux"""
    
    print("Migration : Ajout des tables de génération de baux...")
    
    # Vérifier d'abord que les tables principales existent
    try:
        # Créer toutes les tables depuis models.py
        models.Base.metadata.create_all(bind=engine)
        print("   OK: Tables principales vérifiées/créées")
    except Exception as e:
        print(f"   ERREUR: Création des tables principales: {e}")
        return False
    
    # Créer toutes les nouvelles tables
    tables_to_create = [
        LeaseTemplate,
        GeneratedLease,
        LeaseSignature,
        LeaseClause
    ]
    
    for table_class in tables_to_create:
        try:
            table_class.__table__.create(bind=engine, checkfirst=True)
            print(f"   OK: Table '{table_class.__tablename__}' créée")
        except Exception as e:
            print(f"   ERREUR: {table_class.__tablename__}: {e}")
            return False
    
    return True


def verify_tables_structure():
    """Vérifie la structure des tables créées"""
    
    print("\nVérification de la structure des tables...")
    
    db = SessionLocal()
    try:
        tables_to_check = [
            'lease_templates',
            'generated_leases',
            'lease_signatures',
            'lease_clauses'
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
                    print(f"   ERREUR: Table {table_name} non trouvée")
                    return False
            except Exception as e:
                print(f"   ERREUR: {table_name}: {e}")
                return False
        
        return True
        
    finally:
        db.close()


def verify_foreign_keys():
    """Vérifie les clés étrangères"""
    
    print("\nVérification des clés étrangères...")
    
    db = SessionLocal()
    try:
        # Relations principales à vérifier
        relations = [
            ("lease_templates", "created_by", "user_auth", "id"),
            ("lease_templates", "apartment_id", "apartments", "id"),
            ("generated_leases", "template_id", "lease_templates", "id"),
            ("generated_leases", "created_by", "user_auth", "id"),
            ("generated_leases", "apartment_id", "apartments", "id"),
            ("lease_signatures", "lease_id", "generated_leases", "id"),
            ("lease_clauses", "created_by", "user_auth", "id")
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
                    print(f"   WARNING: {table}.{column} -> {ref_table}.{ref_column} non trouvée")
                    
            except Exception as e:
                print(f"   ERREUR: {table}.{column}: {e}")
        
        print(f"\nRelations trouvées: {relations_ok}/{len(relations)}")
        return relations_ok > 0
        
    finally:
        db.close()


def create_default_templates():
    """Crée les templates par défaut"""
    
    print("\nCréation des templates par défaut...")
    
    db = SessionLocal()
    try:
        # Vérifier s'il y a déjà des templates
        existing_templates = db.execute(text("SELECT COUNT(*) FROM lease_templates")).scalar()
        
        if existing_templates > 0:
            print(f"   {existing_templates} template(s) déjà existant(s)")
            return True
        
        # Récupérer le premier utilisateur pour créer les templates
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        
        if not first_user:
            print("   WARNING: Aucun utilisateur trouvé - pas de templates par défaut")
            return True
        
        # Créer les templates par défaut
        templates_data = [
            create_standard_unfurnished_lease_template(),
            create_furnished_lease_template(),
            create_student_lease_template()
        ]
        
        templates_created = 0
        
        for template_data in templates_data:
            try:
                template = {
                    'created_by': first_user,
                    'name': template_data['name'],
                    'description': template_data['description'],
                    'lease_type': template_data['lease_type'],
                    'is_public': True,
                    'is_default': True,
                    'template_data': json.dumps(template_data)
                }
                
                db.execute(text("""
                    INSERT INTO lease_templates 
                    (created_by, name, description, lease_type, is_public, is_default, template_data, created_at, updated_at)
                    VALUES (:created_by, :name, :description, :lease_type, :is_public, :is_default, :template_data, NOW(), NOW())
                """), template)
                
                templates_created += 1
                print(f"   OK: Template '{template_data['name']}' créé")
                
            except Exception as e:
                print(f"   ERREUR: Template '{template_data['name']}': {e}")
        
        db.commit()
        
        print(f"   Total: {templates_created} templates par défaut créés")
        return templates_created > 0
        
    except Exception as e:
        print(f"   ERREUR: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_default_clauses():
    """Crée les clauses par défaut"""
    
    print("\nCréation des clauses par défaut...")
    
    db = SessionLocal()
    try:
        # Vérifier s'il y a déjà des clauses
        existing_clauses = db.execute(text("SELECT COUNT(*) FROM lease_clauses")).scalar()
        
        if existing_clauses > 0:
            print(f"   {existing_clauses} clause(s) déjà existante(s)")
            return True
        
        # Récupérer le premier utilisateur
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        
        if not first_user:
            print("   WARNING: Aucun utilisateur trouvé - pas de clauses par défaut")
            return True
        
        # Clauses standard
        default_clauses = [
            {
                'title': 'Destination des lieux',
                'category': 'usage',
                'content': 'Le logement est loué à usage d\'habitation principale exclusivement. Toute autre affectation est interdite.',
                'is_mandatory': True,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'État des lieux',
                'category': 'inventory',
                'content': 'Un état des lieux contradictoire sera établi lors de la remise des clés et devra être joint au présent contrat. L\'état des lieux de sortie sera effectué lors de la restitution des clés.',
                'is_mandatory': True,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Obligations du locataire',
                'category': 'obligations',
                'content': 'Le locataire s\'engage à occuper paisiblement les lieux, à les entretenir en bon père de famille, à ne pas transformer les lieux sans accord écrit du bailleur, et à s\'acquitter du loyer et des charges aux échéances convenues.',
                'is_mandatory': True,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Obligations du bailleur',
                'category': 'obligations',
                'content': 'Le bailleur s\'engage à délivrer un logement décent et en bon état d\'usage et de réparation, à assurer la jouissance paisible du logement et à effectuer les réparations autres que locatives.',
                'is_mandatory': True,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Résiliation - Bail nu',
                'category': 'termination',
                'content': 'Le locataire peut résilier le bail à tout moment en respectant un préavis de 3 mois (1 mois pour les logements situés en zone tendue ou en cas de mutation professionnelle).',
                'is_mandatory': False,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED'])
            },
            {
                'title': 'Résiliation - Bail meublé',
                'category': 'termination',
                'content': 'Le locataire peut résilier le bail à tout moment en respectant un préavis d\'1 mois.',
                'is_mandatory': False,
                'is_public': True,
                'applies_to_types': json.dumps(['FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Animaux domestiques',
                'category': 'rules',
                'content': 'Les animaux domestiques sont autorisés sous réserve qu\'ils ne causent aucun dégât ni trouble de voisinage. Une assurance responsabilité civile spécifique est exigée.',
                'is_mandatory': False,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Interdiction de fumer',
                'category': 'rules',
                'content': 'Il est formellement interdit de fumer dans le logement et les parties communes de l\'immeuble.',
                'is_mandatory': False,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Assurance habitation',
                'category': 'insurance',
                'content': 'Le locataire doit souscrire une assurance multirisques habitation couvrant les risques locatifs et fournir l\'attestation au bailleur avant l\'entrée dans les lieux et à chaque renouvellement.',
                'is_mandatory': True,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED', 'FURNISHED', 'STUDENT'])
            },
            {
                'title': 'Dépôt de garantie - Bail nu',
                'category': 'deposit',
                'content': 'Le dépôt de garantie ne peut excéder un mois de loyer hors charges. Il sera restitué dans un délai de 1 mois après remise des clés si l\'état des lieux de sortie est conforme à celui d\'entrée, ou de 2 mois si des réparations sont nécessaires.',
                'is_mandatory': False,
                'is_public': True,
                'applies_to_types': json.dumps(['UNFURNISHED'])
            },
            {
                'title': 'Dépôt de garantie - Bail meublé',
                'category': 'deposit',
                'content': 'Le dépôt de garantie ne peut excéder deux mois de loyer hors charges. Il sera restitué dans un délai de 1 mois après remise des clés si l\'état des lieux de sortie est conforme à celui d\'entrée, ou de 2 mois si des réparations sont nécessaires.',
                'is_mandatory': False,
                'is_public': True,
                'applies_to_types': json.dumps(['FURNISHED', 'STUDENT'])
            }
        ]
        
        clauses_created = 0
        
        for clause_data in default_clauses:
            try:
                clause = {
                    'created_by': first_user,
                    **clause_data
                }
                
                db.execute(text("""
                    INSERT INTO lease_clauses 
                    (created_by, title, category, content, is_mandatory, is_public, applies_to_types, created_at, updated_at)
                    VALUES (:created_by, :title, :category, :content, :is_mandatory, :is_public, :applies_to_types, NOW(), NOW())
                """), clause)
                
                clauses_created += 1
                
            except Exception as e:
                print(f"   ERREUR: Clause '{clause_data['title']}': {e}")
        
        db.commit()
        
        print(f"   OK: {clauses_created} clauses par défaut créées")
        return clauses_created > 0
        
    except Exception as e:
        print(f"   ERREUR: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_sample_lease():
    """Crée un bail d'exemple si possible"""
    
    print("\nCréation d'un exemple de bail...")
    
    db = SessionLocal()
    try:
        # Vérifier les prérequis
        user_count = db.execute(text("SELECT COUNT(*) FROM user_auth")).scalar()
        apartment_count = db.execute(text("SELECT COUNT(*) FROM apartments")).scalar()
        template_count = db.execute(text("SELECT COUNT(*) FROM lease_templates")).scalar()
        
        if user_count == 0 or apartment_count == 0 or template_count == 0:
            print(f"   Prérequis insuffisants:")
            print(f"      - Utilisateurs: {user_count}")
            print(f"      - Appartements: {apartment_count}")
            print(f"      - Templates: {template_count}")
            print("   Exemple non créé")
            return True
        
        # Vérifier s'il y a déjà des baux générés
        existing_leases = db.execute(text("SELECT COUNT(*) FROM generated_leases")).scalar()
        
        if existing_leases > 0:
            print(f"   {existing_leases} bail(aux) déjà existant(s)")
            return True
        
        # Récupérer les données nécessaires
        first_user = db.execute(text("SELECT id FROM user_auth LIMIT 1")).scalar()
        first_apartment = db.execute(text("SELECT id FROM apartments LIMIT 1")).scalar()
        first_template = db.execute(text("SELECT id FROM lease_templates LIMIT 1")).scalar()
        
        # Créer un bail d'exemple
        sample_lease_data = {
            'title': 'Bail d\'exemple créé par la migration',
            'lease_type': 'UNFURNISHED',
            'landlord_info': {
                'first_name': 'Jean',
                'last_name': 'Dupont',
                'email': 'jean.dupont@example.com',
                'phone': '01.23.45.67.89'
            },
            'financial_terms': {
                'monthly_rent': 800.0,
                'charges': 50.0,
                'deposit': 800.0,
                'rent_payment_day': 1
            },
            'apartment_data': {
                'address': 'Adresse d\'exemple',
                'apartment_type': 'T2',
                'surface_area': 45
            }
        }
        
        sample_lease = {
            'template_id': first_template,
            'created_by': first_user,
            'apartment_id': first_apartment,
            'lease_type': 'UNFURNISHED',
            'status': 'DRAFT',
            'title': 'Bail d\'exemple créé par la migration',
            'lease_data': json.dumps(sample_lease_data),
            'monthly_rent': 800.0,
            'charges': 50.0,
            'deposit': 800.0,
            'duration_months': 36
        }
        
        db.execute(text("""
            INSERT INTO generated_leases 
            (template_id, created_by, apartment_id, lease_type, status, title, lease_data,
             monthly_rent, charges, deposit, duration_months, created_at, updated_at)
            VALUES (:template_id, :created_by, :apartment_id, :lease_type, :status, :title, :lease_data,
                    :monthly_rent, :charges, :deposit, :duration_months, NOW(), NOW())
        """), sample_lease)
        
        lease_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        db.commit()
        
        print("   OK: Bail d'exemple créé")
        print(f"      - ID: {lease_id}")
        print(f"      - Type: Bail nu (36 mois)")
        print(f"      - Loyer: 800€ + 50€ de charges")
        
        return True
        
    except Exception as e:
        print(f"   ERREUR: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def show_statistics():
    """Affiche les statistiques du système"""
    
    print("\nStatistiques du système de génération de baux:")
    
    db = SessionLocal()
    try:
        # Compter les enregistrements dans chaque table
        tables_stats = {
            'lease_templates': 'Templates de baux',
            'generated_leases': 'Baux générés',
            'lease_signatures': 'Signatures',
            'lease_clauses': 'Clauses'
        }
        
        for table, description in tables_stats.items():
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"   - {description}: {count}")
            except:
                print(f"   - {description}: N/A")
        
        # Statistiques par type de bail
        try:
            type_stats = db.execute(text("""
                SELECT lease_type, COUNT(*) as count 
                FROM generated_leases 
                GROUP BY lease_type
            """)).fetchall()
            
            if type_stats:
                print("\n   Baux par type:")
                for lease_type, count in type_stats:
                    print(f"      - {lease_type}: {count}")
        except:
            pass
        
        # Statistiques par statut
        try:
            status_stats = db.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM generated_leases 
                GROUP BY status
            """)).fetchall()
            
            if status_stats:
                print("\n   Baux par statut:")
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
    print("RÉSUMÉ DE LA MIGRATION - GÉNÉRATION DE BAUX")
    print("="*60)
    
    print("\nNouvelles fonctionnalités:")
    print("1. Templates de baux personnalisables")
    print("2. Génération automatique de baux (PDF, Word)")
    print("3. Upload de baux existants (PDF, images)")
    print("4. Workflow de signature électronique intégré")
    print("5. Clauses réutilisables et personnalisables")
    print("6. Gestion des types de locataires souhaités")
    print("7. Inventaire de mobilier pour baux meublés")
    print("8. Suivi complet du processus de signature")
    
    print("\nEndpoints API principaux:")
    print("   - POST /api/lease-generation/templates - Créer un template")
    print("   - POST /api/lease-generation/generate - Générer un bail")
    print("   - POST /api/lease-generation/upload - Upload bail existant")
    print("   - POST /api/lease-generation/leases/{id}/generate-pdf - Générer PDF")
    print("   - POST /api/lease-generation/leases/{id}/request-signature - Signature")
    print("   - GET /api/lease-generation/leases/{id}/download - Télécharger")
    print("   - GET /api/lease-generation/stats - Statistiques")
    
    print("\nFormats de documents supportés:")
    print("   - Génération: PDF (ReportLab), Word (python-docx)")
    print("   - Upload: PDF, JPEG, PNG, TIFF")
    print("   - Signature: DocuSign, HelloSign, Adobe Sign")
    
    print("\nTypes de baux supportés:")
    print("   - Bail nu (loi 1989) - 36 mois minimum")
    print("   - Bail meublé - 12 mois minimum")
    print("   - Bail étudiant - 9 mois typique")
    print("   - Bail saisonnier - durée libre")
    print("   - Bail commercial - conditions spécifiques")
    
    print("\nWorkflow complet:")
    print("   1. Création template ou utilisation template existant")
    print("   2. Génération bail avec données personnalisées")
    print("   3. Génération PDF professionnel")
    print("   4. Ajout signataires (propriétaire, locataire, garant)")
    print("   5. Envoi demande signature électronique")
    print("   6. Suivi statut signatures en temps réel")
    print("   7. Récupération document signé final")
    
    print("\nAlternative upload:")
    print("   1. Upload document existant (PDF/image)")
    print("   2. Ajout métadonnées (loyer, durée, etc.)")
    print("   3. Envoi direct en signature électronique")
    print("   4. Même workflow de signature que pour les générés")


def main():
    """Fonction principale"""
    
    print("Migration du système de génération de baux - LocAppart")
    print("=" * 60)
    
    try:
        # 1. Créer les tables
        if not create_lease_generation_tables():
            print("ÉCHEC: Création des tables")
            return 1
        
        # 2. Vérifier la structure
        if not verify_tables_structure():
            print("ÉCHEC: Vérification de la structure")
            return 1
        
        # 3. Vérifier les relations
        if not verify_foreign_keys():
            print("WARNING: Certaines relations manquantes")
        
        # 4. Créer les templates par défaut
        if not create_default_templates():
            print("WARNING: Templates par défaut non créés")
        
        # 5. Créer les clauses par défaut
        if not create_default_clauses():
            print("WARNING: Clauses par défaut non créées")
        
        # 6. Créer un exemple si possible
        if not create_sample_lease():
            print("WARNING: Exemple non créé")
        
        # 7. Afficher les statistiques
        show_statistics()
        
        # 8. Afficher le résumé
        show_migration_summary()
        
        print("\nSUCCÈS: Migration du système de génération de baux terminée!")
        print("\nPour utiliser le système:")
        print("1. Configurer un provider de signature électronique (.env)")
        print("2. Installer les dépendances optionnelles:")
        print("   pip install reportlab python-docx  # Pour génération PDF/Word")
        print("   pip install pillow  # Pour traitement images")
        print("3. Démarrer le serveur: uvicorn main:app --reload")
        print("4. Documentation: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"ERREUR FATALE: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())