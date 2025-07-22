"""
Migration pour le système d'audit avancé et d'undo
Création de toutes les tables nécessaires
"""
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_url, Base


def run_migration():
    """Exécute la migration du système d'audit avancé"""
    
    print("=== MIGRATION SYSTÈME AUDIT AVANCÉ & UNDO ===")
    print("Création des tables d'audit, backup et notifications...\n")
    
    try:
        # Connexion à la base de données
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        print("1. Vérification de la connexion à la base...")
        session.execute(text("SELECT 1"))
        print("   [OK] Connexion établie")
        
        # Importer tous les modèles pour que SQLAlchemy les connaisse
        print("\n2. Import de tous les modèles...")
        # Importer les modèles existants d'abord
        from models import UserAuth, Building, Apartment, ApartmentUserLink, Copro, SyndicatCopro, Photo, UserSession, AuditLog, UserSubscription, Payment, FloorPlan, Tenant, Lease, TenantDocument, Inventory, InventoryPhoto, TenantInvitation, Room
        from models_admin import AdminUser, AdminAction, UserStatusHistory, SystemSettings, AdminNotification
        
        # Puis les nouveaux modèles audit
        from models_audit_enhanced import (
            AuditLogEnhanced, DataBackup, UndoAction, UserNotification, 
            AuditTransactionGroup, UndoComplexity, UndoStatus, NotificationType
        )
        print("   [OK] Tous les modèles importés")
        
        # Récupérer l'inspector pour vérifier les tables existantes
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print("\n3. Création des nouvelles tables d'audit...")
        
        # Tables à créer dans l'ordre des dépendances
        audit_tables = [
            'audit_logs_enhanced',
            'data_backups',
            'audit_transaction_groups',
            'undo_actions',
            'user_notifications'
        ]
        
        # Créer toutes les tables (SQLAlchemy ne créera que celles qui n'existent pas)
        Base.metadata.create_all(bind=engine)
        print("   [OK] Tables d'audit avancé créées")
        
        # Vérifier quelles tables ont été créées
        print("\n4. Vérification des tables créées...")
        new_inspector = inspect(engine)
        current_tables = new_inspector.get_table_names()
        
        for table in audit_tables:
            if table in current_tables:
                print(f"   [OK] Table {table} présente")
            else:
                print(f"   [WARNING] Table {table} manquante")
        
        # Créer les index supplémentaires si nécessaire
        print("\n5. Création des index d'optimisation...")
        
        index_queries = [
            """
            CREATE INDEX IF NOT EXISTS idx_audit_enhanced_user_recent 
            ON audit_logs_enhanced (user_id, created_at DESC, is_undoable)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_enhanced_entity_recent 
            ON audit_logs_enhanced (entity_type, entity_id, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_notifications_unread 
            ON user_notifications (user_id, is_read, priority, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_undo_actions_recent 
            ON undo_actions (created_at DESC, status)
            """
        ]
        
        for query in index_queries:
            try:
                session.execute(text(query))
                print(f"   [OK] Index créé")
            except SQLAlchemyError as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"   [INFO] Index déjà existant")
                else:
                    print(f"   [WARNING] Erreur création index: {e}")
        
        # Créer le dossier de backup
        print("\n6. Création du dossier de backup...")
        backup_dir = "backups/entities"
        os.makedirs(backup_dir, exist_ok=True)
        print(f"   [OK] Dossier {backup_dir} créé")
        
        # Commit des changements
        session.commit()
        print("\n7. Migration terminée avec succès!")
        
        # Statistiques
        print("\n8. Statistiques de migration...")
        try:
            audit_count = session.execute(text("SELECT COUNT(*) FROM audit_logs_enhanced")).scalar()
            backup_count = session.execute(text("SELECT COUNT(*) FROM data_backups")).scalar()
            notification_count = session.execute(text("SELECT COUNT(*) FROM user_notifications")).scalar()
            
            print(f"   - Logs d'audit: {audit_count}")
            print(f"   - Backups: {backup_count}")
            print(f"   - Notifications: {notification_count}")
            
        except:
            print("   [INFO] Impossible de récupérer les statistiques")
        
        print("\n[SUCCESS] Migration du système d'audit avancé terminée!")
        print("\nFonctionnalités disponibles:")
        print("- Timeline d'audit utilisateur avec groupement")
        print("- Système d'undo complet avec backup")
        print("- Notifications utilisateur (cloche)")
        print("- Audit avancé avec métadonnées complètes")
        print("- Gestion des transactions groupées")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()


def rollback_migration():
    """Rollback de la migration audit avancé"""
    
    print("=== ROLLBACK MIGRATION AUDIT AVANCÉ ===")
    print("Suppression des tables d'audit avancé...\n")
    
    try:
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Tables à supprimer dans l'ordre inverse des dépendances
        tables_to_drop = [
            'user_notifications',
            'undo_actions',
            'data_backups',
            'audit_transaction_groups',
            'audit_logs_enhanced'
        ]
        
        print("1. Suppression des tables d'audit avancé...")
        for table in tables_to_drop:
            try:
                session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"   [OK] Table {table} supprimée")
            except SQLAlchemyError as e:
                print(f"   [WARNING] Erreur suppression {table}: {e}")
        
        # Supprimer le dossier de backup (optionnel)
        print("\n2. Nettoyage des dossiers de backup...")
        try:
            import shutil
            if os.path.exists("backups"):
                shutil.rmtree("backups")
                print("   [OK] Dossier backups supprimé")
        except Exception as e:
            print(f"   [WARNING] Erreur suppression dossier backup: {e}")
        
        session.commit()
        print("\n[SUCCESS] Rollback terminé!")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors du rollback: {e}")
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()


def test_migration():
    """Teste les fonctionnalités de base après migration"""
    
    print("=== TEST MIGRATION AUDIT AVANCÉ ===")
    
    try:
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Import des services
        from services.enhanced_audit_service import EnhancedAuditService
        from services.user_notification_service import UserNotificationService
        from models_audit_enhanced import NotificationType
        from enums import ActionType, EntityType
        
        print("1. Test création d'un audit log enhanced...")
        
        # Créer un audit log test
        audit_log = EnhancedAuditService.log_enhanced_action(
            db=session,
            user_id=1,  # Utiliser un utilisateur existant
            action=ActionType.UPDATE,
            entity_type=EntityType.USER,
            entity_id=1,
            description="Test audit enhanced",
            before_data={"test": "before"},
            after_data={"test": "after"},
            is_undoable=True,
            create_backup=True
        )
        
        if audit_log:
            print(f"   [OK] Audit log créé: ID {audit_log.id}")
        
        print("\n2. Test création notification...")
        
        # Créer une notification test
        notification = UserNotificationService.create_notification(
            db=session,
            user_id=1,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Test notification",
            message="Ceci est un test du système de notifications"
        )
        
        if notification:
            print(f"   [OK] Notification créée: ID {notification.id}")
        
        print("\n3. Test récupération timeline...")
        
        # Tester la timeline
        timeline = EnhancedAuditService.get_user_audit_timeline(
            db=session,
            user_id=1,
            days=7
        )
        
        print(f"   [OK] Timeline récupérée: {len(timeline)} groupe(s) d'actions")
        
        print("\n4. Test résumé notifications...")
        
        # Tester le résumé de notifications
        summary = UserNotificationService.get_notification_summary(session, 1)
        
        print(f"   [OK] Résumé notifications: {summary['total_unread']} non lues")
        
        session.commit()
        print("\n[SUCCESS] Tous les tests sont passés!")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()


def create_sample_data():
    """Crée des données d'exemple pour tester le système"""
    
    print("=== CRÉATION DONNÉES D'EXEMPLE ===")
    
    try:
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        from services.enhanced_audit_service import EnhancedAuditService
        from services.user_notification_service import UserNotificationService
        from models_audit_enhanced import NotificationType
        from enums import ActionType, EntityType
        from datetime import datetime, timedelta
        import uuid
        
        print("1. Création d'actions d'audit variées...")
        
        # Simuler différentes actions pour créer une timeline intéressante
        group_id = str(uuid.uuid4())
        
        actions = [
            {
                "action": ActionType.CREATE,
                "entity_type": EntityType.USER,
                "description": "Création de compte utilisateur",
                "before_data": None,
                "after_data": {"email": "test@example.com", "name": "Test User"},
                "complexity": "simple"
            },
            {
                "action": ActionType.UPDATE,
                "entity_type": EntityType.USER,
                "description": "Modification du profil utilisateur",
                "before_data": {"name": "Test User"},
                "after_data": {"name": "Test User Updated"},
                "complexity": "simple"
            },
            {
                "action": ActionType.CREATE,
                "entity_type": EntityType.APARTMENT,
                "description": "Ajout d'un appartement",
                "before_data": None,
                "after_data": {"type": "T3", "surface": "75m²"},
                "complexity": "moderate"
            }
        ]
        
        for i, action_data in enumerate(actions):
            audit_log = EnhancedAuditService.log_enhanced_action(
                db=session,
                user_id=2,  # Utiliser utilisateur debug
                action=action_data["action"],
                entity_type=action_data["entity_type"],
                entity_id=i + 100,  # ID fictif
                description=action_data["description"],
                before_data=action_data["before_data"],
                after_data=action_data["after_data"],
                transaction_group_id=group_id,
                is_undoable=True,
                create_backup=action_data["before_data"] is not None
            )
            
            print(f"   [OK] Action créée: {action_data['description']}")
        
        print("\n2. Création de notifications d'exemple...")
        
        notifications = [
            {
                "type": NotificationType.ADMIN_ACTION,
                "title": "Action administrative",
                "message": "Un administrateur a modifié votre profil",
                "priority": "high"
            },
            {
                "type": NotificationType.SYSTEM_ALERT,
                "title": "Alerte système",
                "message": "Votre quota d'appartements est presque atteint",
                "priority": "normal"
            },
            {
                "type": NotificationType.ACCOUNT_UPDATE,
                "title": "Mise à jour de compte",
                "message": "Votre email a été vérifié avec succès",
                "priority": "low"
            }
        ]
        
        for notif_data in notifications:
            notification = UserNotificationService.create_notification(
                db=session,
                user_id=2,
                notification_type=notif_data["type"],
                title=notif_data["title"],
                message=notif_data["message"],
                priority=notif_data["priority"]
            )
            
            print(f"   [OK] Notification créée: {notif_data['title']}")
        
        session.commit()
        print("\n[SUCCESS] Données d'exemple créées!")
        
        print("\nPour tester:")
        print("- Timeline: GET /audit/users/2/timeline")
        print("- Notifications: GET /audit/notifications")
        print("- Résumé cloche: GET /audit/notifications/summary")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Erreur création données: {e}")
        if 'session' in locals():
            session.rollback()
        return False
    
    finally:
        if 'session' in locals():
            session.close()


def main():
    """Point d'entrée principal"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration du système d\'audit avancé')
    parser.add_argument('--rollback', action='store_true', help='Effectuer un rollback')
    parser.add_argument('--test', action='store_true', help='Tester la migration')
    parser.add_argument('--sample-data', action='store_true', help='Créer des données d\'exemple')
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    elif args.test:
        success = test_migration()
    elif args.sample_data:
        success = create_sample_data()
    else:
        success = run_migration()
    
    if success:
        print("\n[OK] Opération terminée avec succès")
    else:
        print("\n[ERROR] Échec de l'opération")
        sys.exit(1)


if __name__ == "__main__":
    main()