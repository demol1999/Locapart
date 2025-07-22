"""
Service d'undo pour restaurer les actions utilisateur
Gestion complète des restaurations avec backup
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import traceback
from pathlib import Path
import shutil

from models_audit_enhanced import (
    AuditLogEnhanced, DataBackup, UndoAction, UserNotification,
    UndoStatus, UndoComplexity, NotificationType
)
from models import UserAuth, Building, Apartment, Photo
from models_admin import AdminUser
from enums import ActionType, EntityType, AdminRole
from services.enhanced_audit_service import EnhancedAuditService
from error_handlers import BusinessLogicErrorHandler


class UndoService:
    """
    Service principal pour les opérations d'undo
    """
    
    @staticmethod
    def perform_undo(
        db: Session,
        audit_log_id: int,
        admin_user_id: int,
        reason: str = None
    ) -> Tuple[bool, str, Optional[UndoAction]]:
        """
        Effectue un undo sur une action d'audit
        Retourne (success, message, undo_action)
        """
        try:
            # Récupérer l'audit log
            audit_log = db.query(AuditLogEnhanced).filter(
                AuditLogEnhanced.id == audit_log_id
            ).first()
            
            if not audit_log:
                return False, "Action d'audit non trouvée", None
            
            # Récupérer l'admin
            admin_user = db.query(AdminUser).filter(
                AdminUser.id == admin_user_id
            ).first()
            
            if not admin_user:
                return False, "Administrateur non trouvé", None
            
            # Vérifications préliminaires
            can_undo, error_msg = UndoService._validate_undo_permissions(
                audit_log, admin_user
            )
            
            if not can_undo:
                return False, error_msg, None
            
            # Vérifier les pré-requis
            requirements = EnhancedAuditService.get_undo_requirements(db, audit_log_id)
            if requirements["blockers"]:
                return False, f"Undo bloqué: {'; '.join(requirements['blockers'])}", None
            
            # Créer l'action undo
            undo_action = UndoAction(
                audit_log_id=audit_log_id,
                performed_by_admin_id=admin_user_id,
                status=UndoStatus.PENDING,
                undo_reason=reason,
                preview_data=requirements
            )
            
            db.add(undo_action)
            db.flush()
            
            # Exécuter l'undo
            success, message = UndoService._execute_undo(
                db, audit_log, undo_action, admin_user
            )
            
            if success:
                undo_action.status = UndoStatus.COMPLETED
                undo_action.completed_at = datetime.utcnow()
                
                # Créer notification pour l'utilisateur
                UndoService._create_user_notification(
                    db, audit_log, undo_action, admin_user
                )
                
                # Logger cette action d'undo
                EnhancedAuditService.log_enhanced_action(
                    db=db,
                    user_id=None,
                    action=ActionType.UPDATE,
                    entity_type=EntityType.USER,
                    entity_id=audit_log.user_id,
                    description=f"Undo effectué par admin: {audit_log.description}",
                    admin_user_id=admin_user_id,
                    is_undoable=False,  # On ne peut pas undo un undo
                    create_backup=False
                )
                
            else:
                undo_action.status = UndoStatus.FAILED
                undo_action.error_message = message
            
            db.commit()
            return success, message, undo_action
            
        except Exception as e:
            db.rollback()
            error_msg = f"Erreur lors de l'undo: {str(e)}"
            
            if 'undo_action' in locals():
                undo_action.status = UndoStatus.FAILED
                undo_action.error_message = error_msg
                undo_action.execution_log = traceback.format_exc()
                db.commit()
            
            return False, error_msg, locals().get('undo_action')
    
    @staticmethod
    def _validate_undo_permissions(
        audit_log: AuditLogEnhanced, 
        admin_user: AdminUser
    ) -> Tuple[bool, str]:
        """
        Valide les permissions pour effectuer l'undo
        """
        # Vérifier que l'action est undoable
        if not audit_log.is_undoable:
            return False, "Cette action n'est pas annulable"
        
        # Vérifier que l'action n'est pas expirée
        if not audit_log.is_still_undoable():
            return False, "Cette action ne peut plus être annulée (expirée ou déjà annulée)"
        
        # Vérifier les permissions par rôle
        if not audit_log.can_be_undone_by_role(admin_user.admin_role):
            return False, f"Votre rôle {admin_user.admin_role} n'autorise pas l'annulation de cette action de complexité {audit_log.undo_complexity}"
        
        # Vérifications spéciales pour actions complexes
        if audit_log.undo_complexity == UndoComplexity.COMPLEX:
            if admin_user.admin_role != AdminRole.SUPER_ADMIN:
                return False, "Seul un super administrateur peut annuler des actions complexes"
        
        return True, "OK"
    
    @staticmethod
    def _execute_undo(
        db: Session,
        audit_log: AuditLogEnhanced,
        undo_action: UndoAction,
        admin_user: AdminUser
    ) -> Tuple[bool, str]:
        """
        Exécute l'undo selon le type d'action
        """
        undo_action.status = UndoStatus.EXECUTING
        undo_action.started_at = datetime.utcnow()
        db.flush()
        
        execution_log = []
        
        try:
            execution_log.append(f"Début undo action {audit_log.action} sur {audit_log.entity_type}")
            
            if audit_log.action == ActionType.CREATE:
                success, message = UndoService._undo_create(db, audit_log, execution_log)
            elif audit_log.action == ActionType.UPDATE:
                success, message = UndoService._undo_update(db, audit_log, execution_log)
            elif audit_log.action == ActionType.DELETE:
                success, message = UndoService._undo_delete(db, audit_log, execution_log)
            else:
                success, message = False, f"Type d'action {audit_log.action} non supporté pour l'undo"
            
            execution_log.append(f"Résultat: {'SUCCESS' if success else 'FAILED'} - {message}")
            undo_action.execution_log = "\n".join(execution_log)
            
            return success, message
            
        except Exception as e:
            execution_log.append(f"ERREUR: {str(e)}")
            undo_action.execution_log = "\n".join(execution_log)
            return False, f"Erreur d'exécution: {str(e)}"
    
    @staticmethod
    def _undo_create(
        db: Session,
        audit_log: AuditLogEnhanced,
        execution_log: List[str]
    ) -> Tuple[bool, str]:
        """
        Undo d'une création = suppression de l'entité créée
        """
        try:
            execution_log.append(f"Suppression de {audit_log.entity_type} ID {audit_log.entity_id}")
            
            if audit_log.entity_type == EntityType.USER:
                user = db.query(UserAuth).filter(UserAuth.id == audit_log.entity_id).first()
                if user:
                    # Vérifier les dépendances
                    apartment_count = len(user.apartment_links) if user.apartment_links else 0
                    if apartment_count > 0:
                        execution_log.append(f"ATTENTION: L'utilisateur a {apartment_count} appartement(s) liés")
                    
                    db.delete(user)
                    execution_log.append("Utilisateur supprimé")
                    return True, "Création d'utilisateur annulée (utilisateur supprimé)"
                else:
                    return False, "Utilisateur non trouvé (déjà supprimé?)"
            
            elif audit_log.entity_type == EntityType.APARTMENT:
                apartment = db.query(Apartment).filter(Apartment.id == audit_log.entity_id).first()
                if apartment:
                    # Supprimer les photos liées
                    photos = db.query(Photo).filter(Photo.apartment_id == audit_log.entity_id).all()
                    for photo in photos:
                        UndoService._delete_photo_file(photo.filename)
                        db.delete(photo)
                    
                    db.delete(apartment)
                    execution_log.append(f"Appartement et {len(photos)} photo(s) supprimés")
                    return True, "Création d'appartement annulée"
                else:
                    return False, "Appartement non trouvé"
            
            elif audit_log.entity_type == EntityType.BUILDING:
                building = db.query(Building).filter(Building.id == audit_log.entity_id).first()
                if building:
                    # Vérifier les appartements liés
                    apartment_count = len(building.apartments) if building.apartments else 0
                    if apartment_count > 0:
                        return False, f"Impossible de supprimer l'immeuble: {apartment_count} appartement(s) liés"
                    
                    db.delete(building)
                    execution_log.append("Immeuble supprimé")
                    return True, "Création d'immeuble annulée"
                else:
                    return False, "Immeuble non trouvé"
            
            else:
                return False, f"Undo CREATE non implémenté pour {audit_log.entity_type}"
                
        except SQLAlchemyError as e:
            execution_log.append(f"Erreur base de données: {str(e)}")
            return False, f"Erreur base de données: {str(e)}"
    
    @staticmethod
    def _undo_update(
        db: Session,
        audit_log: AuditLogEnhanced,
        execution_log: List[str]
    ) -> Tuple[bool, str]:
        """
        Undo d'une mise à jour = restauration des valeurs précédentes
        """
        try:
            if not audit_log.before_data:
                return False, "Aucune donnée de sauvegarde disponible pour la restauration"
            
            execution_log.append(f"Restauration de {audit_log.entity_type} ID {audit_log.entity_id}")
            
            if audit_log.entity_type == EntityType.USER:
                user = db.query(UserAuth).filter(UserAuth.id == audit_log.entity_id).first()
                if not user:
                    return False, "Utilisateur non trouvé"
                
                # Restaurer les champs modifiés
                restored_fields = []
                for field, old_value in audit_log.before_data.items():
                    if hasattr(user, field):
                        current_value = getattr(user, field)
                        if current_value != old_value:
                            setattr(user, field, old_value)
                            restored_fields.append(f"{field}: {current_value} → {old_value}")
                
                if restored_fields:
                    execution_log.append(f"Champs restaurés: {', '.join(restored_fields)}")
                    return True, f"Utilisateur restauré ({len(restored_fields)} champs modifiés)"
                else:
                    return False, "Aucun changement détecté (valeurs déjà identiques)"
            
            elif audit_log.entity_type == EntityType.APARTMENT:
                apartment = db.query(Apartment).filter(Apartment.id == audit_log.entity_id).first()
                if not apartment:
                    return False, "Appartement non trouvé"
                
                # Restaurer les champs
                restored_fields = []
                for field, old_value in audit_log.before_data.items():
                    if hasattr(apartment, field):
                        setattr(apartment, field, old_value)
                        restored_fields.append(field)
                
                execution_log.append(f"Appartement restauré: {', '.join(restored_fields)}")
                return True, "Appartement restauré à son état précédent"
            
            else:
                return False, f"Undo UPDATE non implémenté pour {audit_log.entity_type}"
                
        except SQLAlchemyError as e:
            execution_log.append(f"Erreur base de données: {str(e)}")
            return False, f"Erreur base de données: {str(e)}"
    
    @staticmethod
    def _undo_delete(
        db: Session,
        audit_log: AuditLogEnhanced,
        execution_log: List[str]
    ) -> Tuple[bool, str]:
        """
        Undo d'une suppression = recréation à partir du backup
        """
        try:
            # Récupérer le backup
            backup = db.query(DataBackup).filter(
                DataBackup.audit_log_id == audit_log.id
            ).first()
            
            if not backup:
                return False, "Aucun backup disponible pour la restauration"
            
            execution_log.append(f"Restauration de {audit_log.entity_type} ID {audit_log.entity_id} depuis backup")
            
            if audit_log.entity_type == EntityType.USER:
                # Vérifier qu'aucun utilisateur n'existe avec cet ID
                existing = db.query(UserAuth).filter(UserAuth.id == audit_log.entity_id).first()
                if existing:
                    return False, f"Un utilisateur avec l'ID {audit_log.entity_id} existe déjà"
                
                # Recréer l'utilisateur
                user_data = backup.full_backup_data
                user = UserAuth(**user_data)
                db.add(user)
                
                execution_log.append("Utilisateur recréé depuis backup")
                return True, "Utilisateur restauré depuis la sauvegarde"
            
            elif audit_log.entity_type == EntityType.PHOTO:
                # Recréer la photo
                photo_data = backup.full_backup_data
                photo = Photo(**photo_data)
                db.add(photo)
                
                # Restaurer le fichier si disponible
                if backup.files_backup_path:
                    UndoService._restore_photo_file(backup.files_backup_path, photo_data.get('filename'))
                
                execution_log.append("Photo et fichier restaurés")
                return True, "Photo restaurée"
            
            else:
                return False, f"Undo DELETE non implémenté pour {audit_log.entity_type}"
                
        except SQLAlchemyError as e:
            execution_log.append(f"Erreur base de données: {str(e)}")
            return False, f"Erreur base de données: {str(e)}"
    
    @staticmethod
    def _delete_photo_file(filename: str):
        """Supprime un fichier photo du disque"""
        try:
            file_path = Path("uploads") / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Erreur suppression fichier {filename}: {e}")
    
    @staticmethod
    def _restore_photo_file(backup_path: str, filename: str):
        """Restaure un fichier photo depuis le backup"""
        try:
            source_path = Path(backup_path) / filename
            dest_path = Path("uploads") / filename
            
            if source_path.exists():
                shutil.copy2(source_path, dest_path)
        except Exception as e:
            print(f"Erreur restauration fichier {filename}: {e}")
    
    @staticmethod
    def _create_user_notification(
        db: Session,
        audit_log: AuditLogEnhanced,
        undo_action: UndoAction,
        admin_user: AdminUser
    ):
        """
        Crée une notification pour informer l'utilisateur de l'undo
        """
        try:
            if not audit_log.user_id:
                return
            
            # Déterminer le titre et message selon l'action
            if audit_log.action == ActionType.CREATE:
                title = "Création annulée par l'administration"
                message = f"La création que vous aviez effectuée ({audit_log.description}) a été annulée par un administrateur."
            elif audit_log.action == ActionType.UPDATE:
                title = "Modification annulée par l'administration"
                message = f"Vos modifications ({audit_log.description}) ont été annulées et restaurées à l'état précédent."
            elif audit_log.action == ActionType.DELETE:
                title = "Suppression annulée par l'administration"
                message = f"L'élément que vous aviez supprimé ({audit_log.description}) a été restauré par un administrateur."
            else:
                title = "Action annulée par l'administration"
                message = f"Une de vos actions ({audit_log.description}) a été annulée par l'administration."
            
            # Ajouter le nom de l'admin si disponible
            admin_name = "un administrateur"
            if admin_user.user:
                admin_name = f"{admin_user.user.first_name} {admin_user.user.last_name}"
            
            message += f"\n\nAction effectuée par: {admin_name}"
            if undo_action.undo_reason:
                message += f"\nRaison: {undo_action.undo_reason}"
            
            notification = UserNotification(
                user_id=audit_log.user_id,
                notification_type=NotificationType.UNDO_PERFORMED,
                title=title,
                message=message,
                undo_action_id=undo_action.id,
                priority="high",
                category="admin_action",
                notification_metadata={
                    "original_action": audit_log.action,
                    "entity_type": audit_log.entity_type,
                    "entity_id": audit_log.entity_id,
                    "admin_user_id": admin_user.id,
                    "complexity": audit_log.undo_complexity
                }
            )
            
            db.add(notification)
            
        except Exception as e:
            print(f"Erreur création notification: {e}")
    
    @staticmethod
    def get_undo_preview(db: Session, audit_log_id: int) -> Dict[str, Any]:
        """
        Génère un aperçu de ce qui sera fait lors de l'undo
        """
        audit_log = db.query(AuditLogEnhanced).filter(
            AuditLogEnhanced.id == audit_log_id
        ).first()
        
        if not audit_log:
            return {"error": "Audit log non trouvé"}
        
        preview = {
            "audit_log_id": audit_log_id,
            "original_action": audit_log.action,
            "entity_type": audit_log.entity_type,
            "entity_id": audit_log.entity_id,
            "description": audit_log.description,
            "complexity": audit_log.undo_complexity,
            "undo_operation": "",
            "affected_data": {},
            "warnings": [],
            "estimated_duration": "< 1 minute"
        }
        
        # Description de l'opération d'undo
        if audit_log.action == ActionType.CREATE:
            preview["undo_operation"] = f"Suppression définitive de {audit_log.entity_type}"
            if audit_log.related_entities:
                preview["warnings"].append(f"Supprimera également {len(audit_log.related_entities)} entité(s) liée(s)")
        
        elif audit_log.action == ActionType.UPDATE:
            preview["undo_operation"] = f"Restauration des valeurs précédentes de {audit_log.entity_type}"
            if audit_log.before_data:
                preview["affected_data"] = audit_log.before_data
        
        elif audit_log.action == ActionType.DELETE:
            preview["undo_operation"] = f"Recréation de {audit_log.entity_type} depuis la sauvegarde"
            
            backup = db.query(DataBackup).filter(
                DataBackup.audit_log_id == audit_log_id
            ).first()
            
            if backup:
                preview["affected_data"] = backup.full_backup_data
                if backup.files_backup_path:
                    preview["warnings"].append("Restaurera également les fichiers associés")
            else:
                preview["warnings"].append("ATTENTION: Aucune sauvegarde disponible!")
        
        # Estimation de durée
        if audit_log.undo_complexity == UndoComplexity.COMPLEX:
            preview["estimated_duration"] = "2-5 minutes"
        elif audit_log.undo_complexity == UndoComplexity.MODERATE:
            preview["estimated_duration"] = "30 secondes - 2 minutes"
        
        return preview