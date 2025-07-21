"""
Main refactorisé de l'application LocAppart
Version simplifiée et organisée avec séparation des responsabilités
"""
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pathlib import Path
import os

# Configuration centralisée
from app_config import AppConfigurator
from database import get_db
from auth import get_current_user
from models import UserAuth, Building, Apartment, ApartmentUserLink, Copro, SyndicatCopro
from enums import ActionType, EntityType
from audit_logger import AuditLogger, get_model_data
from services.query_service import QueryService
from error_handlers import PermissionErrorHandler, ErrorLogger
from oauth_service import OAuthProviderFactory, OAuthAuthenticationService
import schemas

# Créer l'application avec la configuration centralisée
app = AppConfigurator.create_app()


# ==================== ROUTES PRINCIPALES ====================

@app.get("/")
async def root():
    """Point d'entrée de l'API"""
    return {
        "message": "API LocAppart",
        "version": "1.0.0",
        "status": "active"
    }


@app.get("/uploads/{file_path:path}")
async def get_upload_file(
    file_path: str, 
    current_user: UserAuth = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Accès sécurisé aux fichiers uploadés
    Vérifie les permissions avant de servir le fichier
    """
    uploads_dir = Path("uploads")
    full_path = uploads_dir / file_path
    
    # Vérifier que le fichier existe
    if not full_path.exists() or not full_path.is_file():
        error_response = PermissionErrorHandler.not_found("Fichier", file_path)
        return error_response.to_json_response()
    
    # Vérifier les permissions selon le chemin
    if "/buildings/" in file_path:
        # Extraire l'ID du building du chemin
        parts = file_path.split("/")
        if len(parts) >= 2 and parts[0] == "buildings":
            try:
                building_id = int(parts[1])
                
                # Vérifier si l'utilisateur a accès à ce building
                user_has_access = db.query(ApartmentUserLink).join(Apartment).filter(
                    ApartmentUserLink.user_id == current_user.id,
                    Apartment.building_id == building_id
                ).first()
                
                if not user_has_access:
                    error_response = PermissionErrorHandler.access_denied(
                        "Accès non autorisé à ce fichier"
                    )
                    return error_response.to_json_response()
                    
            except ValueError:
                error_response = PermissionErrorHandler.access_denied(
                    "ID de building invalide"
                )
                return error_response.to_json_response()
    else:
        # Pour les autres fichiers, vérifier que c'est l'utilisateur qui l'a uploadé
        filename = os.path.basename(file_path)
        if f"_{current_user.id}_" not in filename and not filename.startswith(f"user_{current_user.id}_"):
            error_response = PermissionErrorHandler.access_denied(
                "Accès non autorisé à ce fichier"
            )
            return error_response.to_json_response()
    
    return FileResponse(full_path)


# ==================== ROUTES MÉTIER PRINCIPALES ====================

@app.get("/me", response_model=schemas.UserOut)
async def get_me(current_user: UserAuth = Depends(get_current_user)):
    """Informations de l'utilisateur connecté"""
    return current_user


@app.get("/my-buildings", response_model=list[schemas.BuildingOut])
async def get_my_buildings(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les buildings de l'utilisateur avec requête optimisée"""
    buildings = QueryService.get_user_buildings_optimized(db, current_user.id)
    return buildings


@app.get("/my-apartments")
async def get_my_apartments(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les appartements de l'utilisateur avec permissions"""
    apartments_data = QueryService.get_user_apartments_with_permissions(
        db, current_user.id
    )
    return apartments_data


@app.get("/apartments/{apartment_id}", response_model=schemas.ApartmentOut)
async def get_apartment_details(
    apartment_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les détails complets d'un appartement"""
    # Vérifier les permissions
    user_role = QueryService.get_apartment_access_check(db, current_user.id, apartment_id)
    if not user_role:
        error_response = PermissionErrorHandler.access_denied(
            "Accès refusé à cet appartement"
        )
        return error_response.to_json_response()
    
    apartment = QueryService.get_apartment_full_details(db, apartment_id)
    if not apartment:
        error_response = PermissionErrorHandler.not_found("Appartement", apartment_id)
        return error_response.to_json_response()
    
    return apartment


@app.get("/buildings/{building_id}/stats")
async def get_building_statistics(
    building_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques d'un building"""
    # Vérifier que l'utilisateur a accès au building
    user_has_access = db.query(ApartmentUserLink).join(Apartment).filter(
        ApartmentUserLink.user_id == current_user.id,
        Apartment.building_id == building_id
    ).first()
    
    if not user_has_access:
        error_response = PermissionErrorHandler.access_denied(
            "Accès refusé à ce building"
        )
        return error_response.to_json_response()
    
    stats = QueryService.get_building_statistics(db, building_id)
    return stats


@app.get("/search/apartments")
async def search_apartments(
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    search_term: str = None,
    min_surface: float = None,
    max_surface: float = None,
    min_rooms: int = None,
    max_rooms: int = None,
    building_id: int = None,
    has_tenants: bool = None
):
    """Recherche d'appartements avec filtres multiples"""
    apartments = QueryService.search_apartments(
        db=db,
        user_id=current_user.id,
        search_term=search_term,
        min_surface=min_surface,
        max_surface=max_surface,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        building_id=building_id,
        has_tenants=has_tenants
    )
    
    return apartments


# ==================== ROUTES OAUTH ====================

@app.get("/auth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Initie le processus OAuth pour un provider donné"""
    try:
        oauth_provider = OAuthProviderFactory.create_provider(provider)
        auth_service = OAuthAuthenticationService(oauth_provider)
        
        authorization_url = auth_service.get_authorization_url()
        
        return {"authorization_url": authorization_url}
        
    except ValueError as e:
        error_response = PermissionErrorHandler.access_denied(str(e))
        return error_response.to_json_response()


@app.get("/auth/{provider}/callback")
async def oauth_callback(
    provider: str, 
    code: str, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """Gère le callback OAuth pour tous les providers"""
    try:
        oauth_provider = OAuthProviderFactory.create_provider(provider)
        auth_service = OAuthAuthenticationService(oauth_provider)
        
        # Échanger le code contre les tokens
        tokens = await auth_service.exchange_code_for_tokens(code)
        user_info = await auth_service.get_user_info(tokens["access_token"])
        
        # Créer ou récupérer l'utilisateur
        user = auth_service.create_or_get_user(db, user_info, request)
        
        # Créer les tokens de session
        from auth import create_access_token, create_user_session
        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_user_session(db, user.id, request)
        
        # Log de la connexion OAuth
        AuditLogger.log_crud_action(
            db=db,
            action=ActionType.LOGIN,
            entity_type=EntityType.USER,
            entity_id=user.id,
            user_id=user.id,
            description=f"Connexion OAuth {provider}: {user.email}",
            request=request
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": schemas.UserOut.model_validate(user)
        }
        
    except Exception as e:
        error_response = PermissionErrorHandler.access_denied(
            f"Erreur lors de l'authentification {provider}: {str(e)}"
        )
        return error_response.to_json_response()


# ==================== CRUD SIMPLIFIÉ ====================

@app.post("/copros/", response_model=schemas.CoproOut)
async def create_copro(
    copro: schemas.CoproCreate,
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée une nouvelle copro"""
    from base_crud import UserOwnedCRUDService
    
    crud_service = UserOwnedCRUDService(
        model=Copro,
        entity_type=EntityType.COPRO,
        entity_name="Copro"
    )
    
    copro_data = copro.model_copy()
    copro_data.user_id = current_user.id
    
    new_copro = crud_service.create(db, copro_data, current_user.id, request)
    return new_copro


@app.get("/copros/", response_model=list[schemas.CoproOut])
async def list_copros(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Liste les copros de l'utilisateur"""
    from base_crud import UserOwnedCRUDService
    
    crud_service = UserOwnedCRUDService(
        model=Copro,
        entity_type=EntityType.COPRO,
        entity_name="Copro"
    )
    
    copros = crud_service.get_user_entities(db, current_user.id, skip, limit)
    return copros


# ==================== POINT D'ENTRÉE ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_refactored:app", host="0.0.0.0", port=8000, reload=True)