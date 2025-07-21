"""
Configuration centralisée de l'application LocAppart
Organisation des routes, middleware et configuration
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, DataError
from pydantic import ValidationError

# Import des modules de configuration
from database import engine
import models

# Import des middlewares
from middleware import AuditMiddleware
from validation_middleware import (
    validation_exception_handler, request_validation_exception_handler, 
    general_exception_handler
)

# Import des contrôleurs et routes
from controllers.auth_controller import router as auth_router
import stripe_routes
import room_routes
import photo_routes
import floor_plan_routes
import tenant_routes
import lease_routes
import document_routes
import tenant_portal_routes
import tenant_invitation_routes
import detailed_inventory_routes
import lease_generation_routes
import property_management_routes
import email_verification_routes

# Import des constantes
from constants import APP_NAME, APP_VERSION, APP_DESCRIPTION


class AppConfigurator:
    """
    Configurateur centralisé pour l'application FastAPI
    """
    
    @staticmethod
    def create_app() -> FastAPI:
        """
        Crée et configure l'application FastAPI
        """
        # Créer les tables
        models.Base.metadata.create_all(bind=engine)
        
        # Créer l'application
        app = FastAPI(
            title=APP_NAME,
            version=APP_VERSION,
            description=APP_DESCRIPTION
        )
        
        # Configurer les middlewares
        AppConfigurator._configure_middlewares(app)
        
        # Configurer les gestionnaires d'exceptions
        AppConfigurator._configure_exception_handlers(app)
        
        # Configurer les routes
        AppConfigurator._configure_routes(app)
        
        # Configurer les fichiers statiques
        AppConfigurator._configure_static_files(app)
        
        return app
    
    @staticmethod
    def _configure_middlewares(app: FastAPI):
        """
        Configure tous les middlewares
        """
        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:5173",
                "http://localhost:52388",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:52388"
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        
        # Middleware d'audit
        app.add_middleware(AuditMiddleware)
        
        # Middleware de sécurité (si nécessaire)
        # app.add_middleware(SecurityMiddleware)
    
    @staticmethod
    def _configure_exception_handlers(app: FastAPI):
        """
        Configure tous les gestionnaires d'exceptions
        """
        app.add_exception_handler(ValidationError, validation_exception_handler)
        app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
        app.add_exception_handler(IntegrityError, general_exception_handler)
        app.add_exception_handler(DataError, general_exception_handler)
    
    @staticmethod
    def _configure_routes(app: FastAPI):
        """
        Configure toutes les routes de l'application
        """
        # Routes d'authentification
        app.include_router(auth_router)
        
        # Routes métier
        app.include_router(stripe_routes.router)
        app.include_router(room_routes.router)
        app.include_router(photo_routes.router)
        app.include_router(floor_plan_routes.router)
        app.include_router(tenant_routes.router)
        app.include_router(lease_routes.router)
        app.include_router(document_routes.router)
        app.include_router(tenant_portal_routes.router)
        app.include_router(tenant_invitation_routes.router)
        app.include_router(detailed_inventory_routes.router)
        app.include_router(lease_generation_routes.router)
        app.include_router(property_management_routes.router)
        app.include_router(email_verification_routes.router)
        
        # Routes de développement (conditionnelles)
        AppConfigurator._configure_dev_routes(app)
    
    @staticmethod
    def _configure_dev_routes(app: FastAPI):
        """
        Configure les routes de développement (uniquement en mode dev)
        """
        import os
        
        if os.getenv("ENVIRONMENT") == "development":
            from controllers.dev_controller import router as dev_router
            app.include_router(dev_router)
    
    @staticmethod
    def _configure_static_files(app: FastAPI):
        """
        Configure le service de fichiers statiques
        """
        import os
        
        uploads_dir = "uploads"
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        # Servir les fichiers uploads (avec authentification dans les routes)
        app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# Configuration CORS détaillée
CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:5173",
        "http://localhost:52388", 
        "http://127.0.0.1:5173",
        "http://127.0.0.1:52388"
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
}

# Configuration des en-têtes de sécurité
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "object-src 'none';"
    )
}