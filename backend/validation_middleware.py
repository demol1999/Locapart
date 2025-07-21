#!/usr/bin/env python3
"""
Middleware de gestion des erreurs de validation avec messages détaillés
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import traceback
import logging

logger = logging.getLogger(__name__)

class ValidationErrorHandler:
    """Gestionnaire d'erreurs de validation personnalisé"""
    
    @staticmethod
    def format_validation_error(validation_error: ValidationError) -> dict:
        """
        Formate les erreurs de validation Pydantic en messages utilisateur lisibles
        """
        errors = {}
        
        for error in validation_error.errors():
            field_path = '.'.join(str(x) for x in error['loc'])
            error_type = error['type']
            error_msg = error['msg']
            
            # Messages d'erreur personnalisés en français
            if error_type == 'value_error.missing':
                message = 'Ce champ est requis'
            elif error_type == 'value_error.email':
                message = 'Format d\'email invalide'
            elif error_type == 'value_error.any_str.max_length':
                max_length = error.get('ctx', {}).get('limit_value', 'N/A')
                message = f'Ne peut pas dépasser {max_length} caractères'
            elif error_type == 'value_error.any_str.min_length':
                min_length = error.get('ctx', {}).get('limit_value', 'N/A')
                message = f'Doit contenir au moins {min_length} caractères'
            elif error_type == 'value_error.number.not_ge':
                min_value = error.get('ctx', {}).get('limit_value', 'N/A')
                message = f'Doit être supérieur ou égal à {min_value}'
            elif error_type == 'value_error.number.not_le':
                max_value = error.get('ctx', {}).get('limit_value', 'N/A')
                message = f'Doit être inférieur ou égal à {max_value}'
            elif error_type == 'type_error.integer':
                message = 'Doit être un nombre entier'
            elif error_type == 'type_error.bool':
                message = 'Doit être vrai ou faux'
            elif 'invalid' in error_msg.lower():
                message = 'Format invalide'
            else:
                # Utiliser le message personnalisé de notre validator si disponible
                message = error_msg
            
            # Traduire les noms de champs en français
            field_translations = {
                'email': 'Email',
                'password': 'Mot de passe',
                'first_name': 'Prénom',
                'last_name': 'Nom',
                'phone': 'Téléphone',
                'street_number': 'Numéro de rue',
                'street_name': 'Nom de rue',
                'complement': 'Complément d\'adresse',
                'postal_code': 'Code postal',
                'city': 'Ville',
                'country': 'Pays',
                'name': 'Nom',
                'floors': 'Nombre d\'étages',
                'type_logement': 'Type de logement',
                'layout': 'Agencement',
                'floor': 'Étage',
                'building_id': 'ID de l\'immeuble'
            }
            
            field_name = field_translations.get(field_path, field_path)
            
            if field_path not in errors:
                errors[field_path] = []
            
            errors[field_path].append({
                'field': field_name,
                'message': message,
                'type': error_type
            })
        
        return {
            'detail': 'Erreurs de validation',
            'errors': errors,
            'type': 'validation_error'
        }
    
    @staticmethod
    def format_database_error(error: Exception) -> dict:
        """
        Formate les erreurs de base de données en messages utilisateur lisibles
        """
        error_str = str(error).lower()
        
        if 'duplicate entry' in error_str or 'unique constraint' in error_str:
            if 'email' in error_str:
                return {
                    'detail': 'Email déjà utilisé',
                    'type': 'duplicate_error',
                    'field': 'email'
                }
            else:
                return {
                    'detail': 'Cette valeur existe déjà',
                    'type': 'duplicate_error'
                }
        
        elif 'data too long' in error_str:
            if 'street_number' in error_str:
                return {
                    'detail': 'Le numéro de rue est trop long (maximum 100 caractères)',
                    'type': 'length_error',
                    'field': 'street_number'
                }
            elif 'street_name' in error_str:
                return {
                    'detail': 'Le nom de rue est trop long (maximum 500 caractères)',
                    'type': 'length_error',
                    'field': 'street_name'
                }
            elif 'email' in error_str:
                return {
                    'detail': 'L\'email est trop long (maximum 255 caractères)',
                    'type': 'length_error',
                    'field': 'email'
                }
            else:
                return {
                    'detail': 'Une des valeurs saisies est trop longue',
                    'type': 'length_error'
                }
        
        elif 'foreign key constraint' in error_str:
            return {
                'detail': 'Référence invalide vers un autre élément',
                'type': 'reference_error'
            }
        
        elif 'not null constraint' in error_str:
            return {
                'detail': 'Un champ requis est manquant',
                'type': 'required_error'
            }
        
        else:
            # Erreur générique de base de données
            logger.error(f"Database error: {error}")
            return {
                'detail': 'Erreur lors de l\'enregistrement des données',
                'type': 'database_error'
            }

async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Gestionnaire d'exceptions pour les erreurs de validation Pydantic
    """
    logger.warning(f"Validation error on {request.url}: {exc}")
    error_response = ValidationErrorHandler.format_validation_error(exc)
    return JSONResponse(
        status_code=422,
        content=error_response
    )

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Gestionnaire d'exceptions pour les erreurs de validation de requête FastAPI
    """
    logger.warning(f"Request validation error on {request.url}: {exc}")
    error_response = ValidationErrorHandler.format_validation_error(exc)
    return JSONResponse(
        status_code=422,
        content=error_response
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Gestionnaire d'exceptions général pour toutes les autres erreurs
    """
    if hasattr(exc, 'orig') and exc.orig:  # SQLAlchemy error
        error_response = ValidationErrorHandler.format_database_error(exc.orig)
        return JSONResponse(
            status_code=400,
            content=error_response
        )
    
    logger.error(f"Unhandled error on {request.url}: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            'detail': 'Erreur interne du serveur',
            'type': 'server_error'
        }
    )