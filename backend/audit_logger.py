from sqlalchemy.orm import Session
from fastapi import Request
import models
import json
from typing import Optional, Dict, Any
from datetime import datetime

class AuditLogger:
    """Service de logging pour auditer toutes les actions dans l'application"""
    
    @staticmethod
    def log_action(
        db: Session,
        action: models.ActionType,
        entity_type: models.EntityType,
        description: str,
        user_id: Optional[int] = None,
        entity_id: Optional[int] = None,
        details: Optional[Dict[Any, Any]] = None,
        request: Optional[Request] = None,
        status_code: Optional[int] = None
    ):
        """
        Log une action dans la base de données
        
        Args:
            db: Session de base de données
            action: Type d'action (CREATE, UPDATE, etc.)
            entity_type: Type d'entité concernée (USER, BUILDING, etc.)
            description: Description de l'action
            user_id: ID de l'utilisateur qui effectue l'action
            entity_id: ID de l'entité concernée
            details: Détails supplémentaires (avant/après, erreurs, etc.)
            request: Objet Request FastAPI pour récupérer IP, user-agent, etc.
            status_code: Code de statut HTTP
        """
        
        # Récupérer les informations de la requête
        ip_address = None
        user_agent = None
        endpoint = None
        method = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            endpoint = str(request.url.path)
            method = request.method
        
        # Convertir les détails en JSON
        details_json = None
        if details:
            try:
                details_json = json.dumps(details, default=str, ensure_ascii=False)
            except Exception as e:
                details_json = f"Erreur de sérialisation: {str(e)}"
        
        # Créer l'entrée de log
        audit_log = models.AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code
        )
        
        db.add(audit_log)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Erreur lors de l'enregistrement du log: {e}")
    
    @staticmethod
    def log_auth_action(db: Session, action: models.ActionType, user_id: int, description: str, request: Request = None, details: Dict = None):
        """Log spécialisé pour les actions d'authentification"""
        AuditLogger.log_action(
            db=db,
            action=action,
            entity_type=models.EntityType.USER,
            description=description,
            user_id=user_id,
            entity_id=user_id,
            details=details,
            request=request,
            status_code=200
        )
    
    @staticmethod
    def log_crud_action(db: Session, action: models.ActionType, entity_type: models.EntityType, 
                       entity_id: int, user_id: int, description: str, 
                       before_data: Dict = None, after_data: Dict = None, request: Request = None):
        """Log spécialisé pour les actions CRUD"""
        details = {}
        if before_data:
            details["before"] = before_data
        if after_data:
            details["after"] = after_data
            
        AuditLogger.log_action(
            db=db,
            action=action,
            entity_type=entity_type,
            description=description,
            user_id=user_id,
            entity_id=entity_id,
            details=details,
            request=request,
            status_code=200
        )
    
    @staticmethod
    def log_error(db: Session, description: str, user_id: int = None, 
                 error_details: str = None, request: Request = None, status_code: int = 500):
        """Log spécialisé pour les erreurs"""
        details = {"error": error_details} if error_details else None
        
        AuditLogger.log_action(
            db=db,
            action=models.ActionType.ERROR,
            entity_type=models.EntityType.USER,  # Par défaut
            description=description,
            user_id=user_id,
            details=details,
            request=request,
            status_code=status_code
        )
    
    @staticmethod
    def log_access_denied(db: Session, description: str, user_id: int = None, request: Request = None):
        """Log spécialisé pour les tentatives d'accès refusées"""
        AuditLogger.log_action(
            db=db,
            action=models.ActionType.ACCESS_DENIED,
            entity_type=models.EntityType.USER,
            description=description,
            user_id=user_id,
            request=request,
            status_code=403
        )

def get_model_data(obj) -> Dict:
    """
    Convertit un objet SQLAlchemy en dictionnaire pour le logging
    """
    if obj is None:
        return {}
    
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        # Convertir les datetime en string
        if isinstance(value, datetime):
            value = value.isoformat()
        data[column.name] = value
    return data