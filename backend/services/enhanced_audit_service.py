"""
Service d'audit avancé avec capacités de backup et undo
Remplace et enrichit l'audit_logger existant
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid
import os
import shutil
from pathlib import Path

from models_audit_enhanced import (
    AuditLogEnhanced, DataBackup, UndoAction, UserNotification, 
    AuditTransactionGroup, UndoComplexity, UndoStatus, NotificationType
)
from models import UserAuth
from models_admin import AdminUser
from enums import ActionType, EntityType, AdminRole
from error_handlers import BusinessLogicErrorHandler


class EnhancedAuditService:
    """
    Service principal pour l'audit avancé avec undo
    """
    
    BACKUP_BASE_PATH = "backups/entities"
    
    @staticmethod
    def start_transaction_group(
        db: Session,
        group_name: str,
        description: str = None,
        primary_user_id: int = None
    ) -> str:
        """
        Démarre un groupe de transactions pour actions liées
        Retourne l'ID du groupe
        """
        group_id = str(uuid.uuid4())
        
        transaction_group = AuditTransactionGroup(
            group_id=group_id,
            group_name=group_name,
            group_description=description,
            primary_user_id=primary_user_id
        )
        
        db.add(transaction_group)
        db.commit()
        
        return group_id
    
    @staticmethod
    def log_enhanced_action(
        db: Session,
        user_id: Optional[int],
        action: ActionType,
        entity_type: EntityType,
        entity_id: Optional[int],
        description: str,
        before_data: Optional[Dict[str, Any]] = None,
        after_data: Optional[Dict[str, Any]] = None,
        transaction_group_id: Optional[str] = None,
        admin_user_id: Optional[int] = None,
        is_undoable: bool = True,
        undo_complexity: UndoComplexity = UndoComplexity.SIMPLE,
        related_entities: Optional[List[Dict]] = None,
        ip_address: str = None,
        user_agent: str = None,
        endpoint: str = None,
        method: str = None,
        status_code: int = None,
        create_backup: bool = True
    ) -> AuditLogEnhanced:
        """
        Log une action avec toutes les métadonnées pour l'undo
        """
        # Générer transaction_group_id si pas fourni
        if not transaction_group_id:
            transaction_group_id = str(uuid.uuid4())
        
        # Déterminer la complexité automatiquement si pas spécifiée
        if undo_complexity == UndoComplexity.SIMPLE:
            undo_complexity = EnhancedAuditService._calculate_complexity(
                action, entity_type, before_data, after_data, related_entities
            )
        
        # Créer le log d'audit
        audit_log = AuditLogEnhanced(
            transaction_group_id=transaction_group_id,
            user_id=user_id,
            admin_user_id=admin_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            before_data=before_data,
            after_data=after_data,
            related_entities=related_entities,
            is_undoable=is_undoable and action in [ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE],
            undo_complexity=undo_complexity,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code
        )
        
        db.add(audit_log)
        db.flush()  # Pour obtenir l'ID
        
        # Créer backup si nécessaire
        if create_backup and audit_log.is_undoable and before_data:
            EnhancedAuditService._create_data_backup(
                db, audit_log, entity_type, entity_id, before_data, related_entities
            )
        
        # Mettre à jour le groupe de transaction
        EnhancedAuditService._update_transaction_group(db, transaction_group_id, audit_log)
        
        db.commit()
        return audit_log
    
    @staticmethod
    def _calculate_complexity(
        action: ActionType,
        entity_type: EntityType,
        before_data: Optional[Dict],
        after_data: Optional[Dict],
        related_entities: Optional[List[Dict]]
    ) -> UndoComplexity:
        """
        Calcule automatiquement la complexité de l'undo
        """
        # Actions non-undoables
        if action in [ActionType.read, ActionType.LOGIN, ActionType.LOGOUT, ActionType.ACCESS_DENIED]:
            return UndoComplexity.IMPOSSIBLE
        
        # UPDATE simple sur utilisateur
        if action == ActionType.UPDATE and entity_type == EntityType.USER:
            return UndoComplexity.SIMPLE
        
        # DELETE avec beaucoup de relations
        if action == ActionType.DELETE and related_entities and len(related_entities) > 5:
            return UndoComplexity.COMPLEX
        
        # DELETE d'entités critiques
        if action == ActionType.DELETE and entity_type in [EntityType.BUILDING, EntityType.COPRO]:
            return UndoComplexity.COMPLEX
        
        # CREATE avec relations
        if action == ActionType.CREATE and related_entities:
            return UndoComplexity.MODERATE
        
        return UndoComplexity.SIMPLE
    
    @staticmethod
    def _create_data_backup(
        db: Session,
        audit_log: AuditLogEnhanced,
        entity_type: EntityType,
        entity_id: Optional[int],
        before_data: Dict[str, Any],
        related_entities: Optional[List[Dict]]
    ):
        """
        Crée un backup complet des données pour restore
        """
        backup = DataBackup(
            audit_log_id=audit_log.id,
            entity_type=entity_type,
            entity_id=entity_id,
            full_backup_data=before_data,
            relationships_data=related_entities,
            backup_size_bytes=len(json.dumps(before_data).encode('utf-8')),
            expires_at=audit_log.expires_at
        )
        
        # Backup des fichiers si nécessaire
        if entity_type in [EntityType.PHOTO, EntityType.DOCUMENT]:
            backup.files_backup_path = EnhancedAuditService._backup_files(
                entity_type, entity_id, before_data
            )
        
        db.add(backup)
    
    @staticmethod
    def _backup_files(entity_type: EntityType, entity_id: int, data: Dict) -> Optional[str]:
        """
        Sauvegarde les fichiers liés à l'entité
        """
        try:
            # Créer le dossier de backup
            backup_dir = Path(EnhancedAuditService.BACKUP_BASE_PATH) / entity_type.value / str(entity_id)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder selon le type
            if entity_type == EntityType.PHOTO and 'filename' in data:
                source_path = Path("uploads") / data['filename']
                if source_path.exists():
                    shutil.copy2(source_path, backup_dir / data['filename'])
            
            return str(backup_dir)
            
        except Exception as e:
            print(f"Erreur backup fichiers: {e}")
            return None
    
    @staticmethod
    def _update_transaction_group(db: Session, group_id: str, audit_log: AuditLogEnhanced):
        """
        Met à jour les statistiques du groupe de transaction
        """
        group = db.query(AuditTransactionGroup).filter(
            AuditTransactionGroup.group_id == group_id
        ).first()
        
        if not group:
            # Créer le groupe s'il n'existe pas
            group = AuditTransactionGroup(
                group_id=group_id,
                group_name=f"Transaction {group_id[:8]}",
                primary_user_id=audit_log.user_id
            )
            db.add(group)
        
        # Mettre à jour les statistiques
        group.total_actions += 1
        if audit_log.is_undoable:
            group.undoable_actions += 1
        else:
            group.all_undoable = False
        
        # Mettre à jour la complexité globale
        if audit_log.undo_complexity == UndoComplexity.COMPLEX:
            group.complexity_level = UndoComplexity.COMPLEX
        elif audit_log.undo_complexity == UndoComplexity.MODERATE and group.complexity_level == UndoComplexity.SIMPLE:
            group.complexity_level = UndoComplexity.MODERATE
    
    @staticmethod
    def get_user_audit_timeline(
        db: Session,
        user_id: int,
        days: int = 7,
        include_non_undoable: bool = True,
        admin_role: Optional[AdminRole] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère la timeline d'audit d'un utilisateur avec groupement
        """
        # Date limite
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Requête de base
        query = db.query(AuditLogEnhanced).filter(
            AuditLogEnhanced.user_id == user_id,
            AuditLogEnhanced.created_at >= since_date
        )
        
        if not include_non_undoable:
            query = query.filter(AuditLogEnhanced.is_undoable == True)
        
        audit_logs = query.order_by(desc(AuditLogEnhanced.created_at)).all()
        
        # Grouper par transaction_group_id
        grouped_actions = {}
        for log in audit_logs:
            group_id = log.transaction_group_id
            if group_id not in grouped_actions:
                grouped_actions[group_id] = {
                    "group_id": group_id,
                    "group_name": None,
                    "actions": [],
                    "complexity": UndoComplexity.SIMPLE,
                    "can_undo": True,
                    "undo_count": 0,
                    "created_at": log.created_at
                }
            
            action_data = {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "description": log.description,
                "created_at": log.created_at,
                "is_undoable": log.is_undoable,
                "undo_complexity": log.undo_complexity,
                "can_undo_by_role": log.can_be_undone_by_role(admin_role) if admin_role else False,
                "is_still_undoable": log.is_still_undoable(),
                "impact_preview": log.get_impact_preview(),
                "undo_actions": [
                    {
                        "id": undo.id,
                        "status": undo.status,
                        "performed_at": undo.created_at,
                        "performed_by": undo.performed_by_admin.user.email if undo.performed_by_admin and undo.performed_by_admin.user else "Unknown"
                    }
                    for undo in log.undo_actions
                ]
            }
            
            grouped_actions[group_id]["actions"].append(action_data)
            
            # Mettre à jour la complexité du groupe
            if log.undo_complexity == UndoComplexity.COMPLEX:
                grouped_actions[group_id]["complexity"] = UndoComplexity.COMPLEX
            elif log.undo_complexity == UndoComplexity.MODERATE and grouped_actions[group_id]["complexity"] == UndoComplexity.SIMPLE:
                grouped_actions[group_id]["complexity"] = UndoComplexity.MODERATE
            
            # Vérifier si peut être undo
            if not log.is_still_undoable() or (admin_role and not log.can_be_undone_by_role(admin_role)):
                grouped_actions[group_id]["can_undo"] = False
            
            # Compter les undo déjà effectués
            grouped_actions[group_id]["undo_count"] += len(log.undo_actions)
        
        # Récupérer les noms des groupes
        group_ids = list(grouped_actions.keys())
        transaction_groups = db.query(AuditTransactionGroup).filter(
            AuditTransactionGroup.group_id.in_(group_ids)
        ).all()
        
        for tg in transaction_groups:
            if tg.group_id in grouped_actions:
                grouped_actions[tg.group_id]["group_name"] = tg.group_name
        
        # Convertir en liste et trier par date
        timeline = list(grouped_actions.values())
        timeline.sort(key=lambda x: x["created_at"], reverse=True)
        
        return timeline
    
    @staticmethod
    def get_undo_requirements(db: Session, audit_log_id: int) -> Dict[str, Any]:
        """
        Analyse les pré-requis pour un undo
        """
        audit_log = db.query(AuditLogEnhanced).filter(
            AuditLogEnhanced.id == audit_log_id
        ).first()
        
        if not audit_log:
            raise ValueError("Audit log non trouvé")
        
        requirements = {
            "audit_log_id": audit_log_id,
            "can_undo": audit_log.is_still_undoable(),
            "complexity": audit_log.undo_complexity,
            "requirements": [],
            "warnings": [],
            "blockers": []
        }
        
        # Vérifications selon le type d'action
        if audit_log.action == ActionType.DELETE:
            requirements = EnhancedAuditService._check_delete_undo_requirements(
                db, audit_log, requirements
            )
        elif audit_log.action == ActionType.CREATE:
            requirements = EnhancedAuditService._check_create_undo_requirements(
                db, audit_log, requirements
            )
        elif audit_log.action == ActionType.UPDATE:
            requirements = EnhancedAuditService._check_update_undo_requirements(
                db, audit_log, requirements
            )
        
        return requirements
    
    @staticmethod
    def _check_delete_undo_requirements(
        db: Session, 
        audit_log: AuditLogEnhanced, 
        requirements: Dict
    ) -> Dict:
        """
        Vérifie les pré-requis pour undo d'une suppression
        """
        # Vérifier que l'entité n'a pas été recréée
        if audit_log.entity_id:
            # TODO: Vérifier selon entity_type
            if audit_log.entity_type == EntityType.USER:
                existing = db.query(UserAuth).filter(UserAuth.id == audit_log.entity_id).first()
                if existing:
                    requirements["blockers"].append(
                        f"Un utilisateur avec l'ID {audit_log.entity_id} existe déjà"
                    )
        
        # Vérifier les backups
        backup = db.query(DataBackup).filter(
            DataBackup.audit_log_id == audit_log.id
        ).first()
        
        if backup:
            requirements["requirements"].append("Backup de données disponible")
            if backup.files_backup_path:
                requirements["requirements"].append("Backup de fichiers disponible")
        else:
            requirements["blockers"].append("Aucun backup disponible pour la restauration")
        
        return requirements
    
    @staticmethod
    def _check_create_undo_requirements(
        db: Session, 
        audit_log: AuditLogEnhanced, 
        requirements: Dict
    ) -> Dict:
        """
        Vérifie les pré-requis pour undo d'une création
        """
        # Vérifier que l'entité existe encore
        if audit_log.entity_id:
            # TODO: Vérifier selon entity_type
            if audit_log.entity_type == EntityType.USER:
                existing = db.query(UserAuth).filter(UserAuth.id == audit_log.entity_id).first()
                if not existing:
                    requirements["blockers"].append(
                        f"L'utilisateur {audit_log.entity_id} n'existe plus"
                    )
        
        # Vérifier les dépendances créées après
        related_audits = db.query(AuditLogEnhanced).filter(
            and_(
                AuditLogEnhanced.entity_type == audit_log.entity_type,
                AuditLogEnhanced.entity_id == audit_log.entity_id,
                AuditLogEnhanced.created_at > audit_log.created_at,
                AuditLogEnhanced.action.in_([ActionType.CREATE, ActionType.UPDATE])
            )
        ).count()
        
        if related_audits > 0:
            requirements["warnings"].append(
                f"{related_audits} modification(s) effectuée(s) depuis la création"
            )
        
        return requirements
    
    @staticmethod
    def _check_update_undo_requirements(
        db: Session, 
        audit_log: AuditLogEnhanced, 
        requirements: Dict
    ) -> Dict:
        """
        Vérifie les pré-requis pour undo d'une mise à jour
        """
        # Vérifier que l'entité existe encore et n'a pas été modifiée depuis
        if audit_log.entity_id:
            # Chercher des modifications ultérieures
            later_updates = db.query(AuditLogEnhanced).filter(
                and_(
                    AuditLogEnhanced.entity_type == audit_log.entity_type,
                    AuditLogEnhanced.entity_id == audit_log.entity_id,
                    AuditLogEnhanced.created_at > audit_log.created_at,
                    AuditLogEnhanced.action == ActionType.UPDATE
                )
            ).count()
            
            if later_updates > 0:
                requirements["warnings"].append(
                    f"L'entité a été modifiée {later_updates} fois depuis cette action"
                )
        
        return requirements