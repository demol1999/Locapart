"""
Gestionnaires d'erreurs centralisés pour l'application LocAppart
Standardisation de la gestion et du format des erreurs
"""
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, DataError
from pydantic import ValidationError
from audit_logger import AuditLogger


class ErrorResponse:
    """Structure standardisée pour les réponses d'erreur"""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        status_code: int = 400
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour la réponse JSON"""
        response = {
            "error": True,
            "message": self.message
        }
        
        if self.error_code:
            response["error_code"] = self.error_code
        
        if self.details:
            response["details"] = self.details
        
        return response
    
    def to_json_response(self) -> JSONResponse:
        """Retourne une JSONResponse FastAPI"""
        return JSONResponse(
            status_code=self.status_code,
            content=self.to_dict()
        )


class DatabaseErrorHandler:
    """Gestionnaire pour les erreurs de base de données"""
    
    @staticmethod
    def handle_integrity_error(
        error: IntegrityError,
        db_session = None,
        request: Request = None
    ) -> ErrorResponse:
        """
        Gère les erreurs d'intégrité de la base de données
        """
        error_message = str(error.orig)
        
        # Mapping des erreurs courantes
        if "Duplicate entry" in error_message:
            if "email" in error_message.lower():
                return ErrorResponse(
                    message="Cette adresse email est déjà utilisée",
                    error_code="EMAIL_ALREADY_EXISTS",
                    status_code=status.HTTP_409_CONFLICT
                )
            else:
                return ErrorResponse(
                    message="Cette valeur existe déjà dans la base de données",
                    error_code="DUPLICATE_ENTRY",
                    status_code=status.HTTP_409_CONFLICT
                )
        
        elif "foreign key constraint fails" in error_message.lower():
            return ErrorResponse(
                message="Référence invalide: l'élément lié n'existe pas",
                error_code="FOREIGN_KEY_VIOLATION",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        elif "cannot delete or update a parent row" in error_message.lower():
            return ErrorResponse(
                message="Impossible de supprimer: des éléments dépendants existent",
                error_code="PARENT_ROW_CONSTRAINT",
                status_code=status.HTTP_409_CONFLICT
            )
        
        else:
            # Erreur générique d'intégrité
            return ErrorResponse(
                message="Erreur de contrainte de base de données",
                error_code="INTEGRITY_ERROR",
                details={"technical_message": error_message},
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    @staticmethod
    def handle_data_error(
        error: DataError,
        db_session = None,
        request: Request = None
    ) -> ErrorResponse:
        """
        Gère les erreurs de données de la base de données
        """
        error_message = str(error.orig)
        
        if "Data too long" in error_message:
            return ErrorResponse(
                message="Données trop longues pour le champ spécifié",
                error_code="DATA_TOO_LONG",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        elif "Incorrect" in error_message and "value" in error_message:
            return ErrorResponse(
                message="Format de données incorrect",
                error_code="INVALID_DATA_FORMAT",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        else:
            return ErrorResponse(
                message="Erreur de format de données",
                error_code="DATA_ERROR",
                details={"technical_message": error_message},
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ValidationErrorHandler:
    """Gestionnaire pour les erreurs de validation Pydantic"""
    
    @staticmethod
    def handle_validation_error(error: ValidationError) -> ErrorResponse:
        """
        Formate les erreurs de validation Pydantic
        """
        validation_errors = []
        
        for error_detail in error.errors():
            field_path = " -> ".join(str(loc) for loc in error_detail["loc"])
            
            validation_errors.append({
                "field": field_path,
                "message": error_detail["msg"],
                "type": error_detail["type"],
                "input": error_detail.get("input")
            })
        
        return ErrorResponse(
            message="Erreurs de validation des données",
            error_code="VALIDATION_ERROR",
            details={
                "validation_errors": validation_errors,
                "error_count": len(validation_errors)
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class PermissionErrorHandler:
    """Gestionnaire pour les erreurs de permissions"""
    
    @staticmethod
    def access_denied(
        message: str = "Accès refusé",
        resource: str = None,
        required_permission: str = None
    ) -> ErrorResponse:
        """
        Erreur d'accès refusé standardisée
        """
        details = {}
        if resource:
            details["resource"] = resource
        if required_permission:
            details["required_permission"] = required_permission
        
        return ErrorResponse(
            message=message,
            error_code="ACCESS_DENIED",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(
        resource: str = "Ressource",
        resource_id: Union[int, str] = None
    ) -> ErrorResponse:
        """
        Erreur de ressource non trouvée standardisée
        """
        message = f"{resource} non trouvée"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        return ErrorResponse(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource, "resource_id": resource_id},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentification requise") -> ErrorResponse:
        """
        Erreur d'authentification standardisée
        """
        return ErrorResponse(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class BusinessLogicErrorHandler:
    """Gestionnaire pour les erreurs de logique métier"""
    
    @staticmethod
    def subscription_limit_exceeded(
        current_count: int,
        max_allowed: int,
        resource_type: str = "éléments"
    ) -> ErrorResponse:
        """
        Erreur de limite d'abonnement dépassée
        """
        return ErrorResponse(
            message=f"Limite d'abonnement atteinte: {current_count}/{max_allowed} {resource_type}",
            error_code="SUBSCRIPTION_LIMIT_EXCEEDED",
            details={
                "current_count": current_count,
                "max_allowed": max_allowed,
                "resource_type": resource_type
            },
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )
    
    @staticmethod
    def email_not_verified() -> ErrorResponse:
        """
        Erreur d'email non vérifié
        """
        return ErrorResponse(
            message="Email non vérifié. Veuillez vérifier votre adresse email avant de continuer.",
            error_code="EMAIL_NOT_VERIFIED",
            details={"action_required": "verify_email"},
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def rate_limit_exceeded(
        retry_after: int = None,
        action: str = None
    ) -> ErrorResponse:
        """
        Erreur de limite de taux dépassée
        """
        message = "Trop de tentatives. Veuillez réessayer plus tard."
        if action:
            message = f"Trop de tentatives pour l'action '{action}'. Veuillez réessayer plus tard."
        
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        
        return ErrorResponse(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class ErrorLogger:
    """Utilitaire pour logger les erreurs avec audit"""
    
    @staticmethod
    def log_error(
        error_response: ErrorResponse,
        db_session = None,
        request: Request = None,
        user_id: int = None,
        additional_context: Dict[str, Any] = None
    ):
        """
        Log une erreur avec le système d'audit
        """
        if not db_session or not request:
            return
        
        description = f"Erreur {error_response.error_code or 'UNKNOWN'}: {error_response.message}"
        
        error_details = {
            "error_code": error_response.error_code,
            "message": error_response.message,
            "status_code": error_response.status_code,
            "details": error_response.details
        }
        
        if additional_context:
            error_details.update(additional_context)
        
        try:
            AuditLogger.log_error(
                db=db_session,
                description=description,
                error_details=error_details,
                request=request,
                status_code=error_response.status_code,
                user_id=user_id
            )
        except Exception:
            # Ne pas faire échouer l'application si le logging échoue
            pass


def create_error_response(
    message: str,
    error_code: str = None,
    details: Dict[str, Any] = None,
    status_code: int = 400
) -> HTTPException:
    """
    Utilitaire pour créer facilement une HTTPException avec format standardisé
    """
    error_response = ErrorResponse(message, error_code, details, status_code)
    
    raise HTTPException(
        status_code=status_code,
        detail=error_response.to_dict()
    )