"""
Service OAuth suivant les principes SOLID
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from authlib.integrations.requests_client import OAuth2Session
from sqlalchemy.orm import Session
import models
from auth import create_user_session
from audit_logger import AuditLogger
import os


# Interface Segregation Principle - Interface pour les providers OAuth
class OAuthProvider(ABC):
    """Interface abstraite pour les providers OAuth"""
    
    @abstractmethod
    def get_authorization_url(self, redirect_uri: str) -> Tuple[str, str]:
        """Retourne l'URL d'autorisation et l'état"""
        pass
    
    @abstractmethod
    def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        """Récupère les infos utilisateur avec le code d'autorisation"""
        pass
    
    @abstractmethod
    def get_provider_type(self) -> models.AuthType:
        """Retourne le type de provider"""
        pass


# Single Responsibility Principle - Chaque provider a sa responsabilité
class GoogleOAuthProvider(OAuthProvider):
    """Provider OAuth pour Google"""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.scope = "openid email profile"
    
    def get_authorization_url(self, redirect_uri: str) -> Tuple[str, str]:
        client = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=redirect_uri,
            scope=self.scope
        )
        authorization_url, state = client.create_authorization_url(
            self.authorization_endpoint
        )
        return authorization_url, state
    
    def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        client = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=redirect_uri
        )
        
        # Échanger le code contre un token
        token = client.fetch_token(
            self.token_endpoint,
            code=code,
            client_secret=self.client_secret
        )
        
        # Récupérer les infos utilisateur
        response = client.get(self.userinfo_endpoint)
        user_data = response.json()
        
        return {
            "email": user_data.get("email"),
            "first_name": user_data.get("given_name", ""),
            "last_name": user_data.get("family_name", ""),
            "oauth_provider_id": user_data.get("id"),
            "oauth_avatar_url": user_data.get("picture"),
            "email_verified": user_data.get("verified_email", False)
        }
    
    def get_provider_type(self) -> models.AuthType:
        return models.AuthType.GOOGLE_OAUTH


class FacebookOAuthProvider(OAuthProvider):
    """Provider OAuth pour Facebook"""
    
    def __init__(self):
        self.client_id = os.getenv("FACEBOOK_CLIENT_ID")
        self.client_secret = os.getenv("FACEBOOK_CLIENT_SECRET")
        self.authorization_endpoint = "https://www.facebook.com/v18.0/dialog/oauth"
        self.token_endpoint = "https://graph.facebook.com/v18.0/oauth/access_token"
        self.userinfo_endpoint = "https://graph.facebook.com/v18.0/me"
        self.scope = "email public_profile"
    
    def get_authorization_url(self, redirect_uri: str) -> Tuple[str, str]:
        client = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=redirect_uri,
            scope=self.scope
        )
        authorization_url, state = client.create_authorization_url(
            self.authorization_endpoint
        )
        return authorization_url, state
    
    def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        client = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=redirect_uri
        )
        
        # Échanger le code contre un token
        token = client.fetch_token(
            self.token_endpoint,
            code=code,
            client_secret=self.client_secret
        )
        
        # Récupérer les infos utilisateur
        response = client.get(
            self.userinfo_endpoint,
            params={"fields": "id,email,first_name,last_name,picture"}
        )
        user_data = response.json()
        
        return {
            "email": user_data.get("email"),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "oauth_provider_id": user_data.get("id"),
            "oauth_avatar_url": user_data.get("picture", {}).get("data", {}).get("url"),
            "email_verified": True  # Facebook vérifie toujours l'email
        }
    
    def get_provider_type(self) -> models.AuthType:
        return models.AuthType.FACEBOOK_OAUTH


class MicrosoftOAuthProvider(OAuthProvider):
    """Provider OAuth pour Microsoft"""
    
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")  # "common" pour les comptes personnels et professionnels
        self.authorization_endpoint = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        self.token_endpoint = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.userinfo_endpoint = "https://graph.microsoft.com/v1.0/me"
        self.scope = "openid profile email User.Read"
    
    def get_authorization_url(self, redirect_uri: str) -> Tuple[str, str]:
        client = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=redirect_uri,
            scope=self.scope
        )
        authorization_url, state = client.create_authorization_url(
            self.authorization_endpoint
        )
        return authorization_url, state
    
    def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        client = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=redirect_uri
        )
        
        # Échanger le code contre un token
        token = client.fetch_token(
            self.token_endpoint,
            code=code,
            client_secret=self.client_secret
        )
        
        # Récupérer les infos utilisateur
        response = client.get(self.userinfo_endpoint)
        user_data = response.json()
        
        return {
            "email": user_data.get("mail") or user_data.get("userPrincipalName"),
            "first_name": user_data.get("givenName", ""),
            "last_name": user_data.get("surname", ""),
            "oauth_provider_id": user_data.get("id"),
            "oauth_avatar_url": None,  # Microsoft Graph nécessite un appel séparé pour la photo
            "email_verified": True  # Microsoft vérifie toujours l'email
        }
    
    def get_provider_type(self) -> models.AuthType:
        return models.AuthType.MICROSOFT_OAUTH


# Open/Closed Principle - Facilement extensible pour d'autres providers
class OAuthProviderFactory:
    """Factory pour créer les providers OAuth"""
    
    @staticmethod
    def get_provider(provider_type: str) -> OAuthProvider:
        providers = {
            "google": GoogleOAuthProvider,
            "facebook": FacebookOAuthProvider,
            "microsoft": MicrosoftOAuthProvider
        }
        
        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Provider OAuth non supporté: {provider_type}")
        
        return provider_class()


# Single Responsibility Principle - Service pour gérer l'authentification OAuth
class OAuthAuthenticationService:
    """Service pour gérer l'authentification OAuth"""
    
    def __init__(self, db: Session, provider: OAuthProvider):
        self.db = db
        self.provider = provider
    
    def create_or_get_user(self, user_data: Dict, request=None) -> models.UserAuth:
        """
        Crée ou récupère un utilisateur basé sur les données OAuth
        Dependency Inversion Principle - dépend de l'abstraction, pas du concret
        """
        email = user_data.get("email")
        oauth_provider_id = user_data.get("oauth_provider_id")
        
        if not email:
            raise ValueError("Email requis pour l'authentification OAuth")
        
        # Chercher l'utilisateur existant
        user = self.db.query(models.UserAuth).filter(
            models.UserAuth.email == email
        ).first()
        
        if user:
            # Utilisateur existant - mettre à jour les infos OAuth si nécessaire
            if user.auth_type == models.AuthType.EMAIL_PASSWORD:
                # Migrer vers OAuth
                user.auth_type = self.provider.get_provider_type()
                user.oauth_provider_id = oauth_provider_id
                user.oauth_avatar_url = user_data.get("oauth_avatar_url")
                user.email_verified = user_data.get("email_verified", False)
                
                # Log de migration
                AuditLogger.log_auth_action(
                    db=self.db,
                    action=models.ActionType.UPDATE,
                    user_id=user.id,
                    description=f"Migration vers OAuth {self.provider.get_provider_type().value}",
                    request=request
                )
            
            # Mettre à jour les infos de profil
            user.first_name = user_data.get("first_name", user.first_name)
            user.last_name = user_data.get("last_name", user.last_name)
            user.oauth_avatar_url = user_data.get("oauth_avatar_url", user.oauth_avatar_url)
            
        else:
            # Nouvel utilisateur OAuth
            user = models.UserAuth(
                email=email,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
                auth_type=self.provider.get_provider_type(),
                oauth_provider_id=oauth_provider_id,
                oauth_avatar_url=user_data.get("oauth_avatar_url"),
                email_verified=user_data.get("email_verified", False),
                # Pas de mot de passe pour OAuth
                hashed_password=None
            )
            self.db.add(user)
            
            # Log de création
            AuditLogger.log_crud_action(
                db=self.db,
                action=models.ActionType.CREATE,
                entity_type=models.EntityType.USER,
                entity_id=None,  # Sera mis à jour après commit
                user_id=None,    # Sera mis à jour après commit
                description=f"Inscription OAuth {self.provider.get_provider_type().value}: {email}",
                request=request
            )
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def authenticate_user(self, code: str, redirect_uri: str, request=None) -> models.UserAuth:
        """Authentifie un utilisateur via OAuth"""
        try:
            # Récupérer les infos utilisateur du provider
            user_data = self.provider.get_user_info(code, redirect_uri)
            
            # Créer ou récupérer l'utilisateur
            user = self.create_or_get_user(user_data, request)
            
            # Log de connexion OAuth
            AuditLogger.log_auth_action(
                db=self.db,
                action=models.ActionType.LOGIN,
                user_id=user.id,
                description=f"Connexion OAuth {self.provider.get_provider_type().value}: {user.email}",
                request=request,
                details={
                    "provider": self.provider.get_provider_type().value,
                    "email_verified": user.email_verified
                }
            )
            
            return user
            
        except Exception as e:
            # Log d'erreur OAuth
            AuditLogger.log_error(
                db=self.db,
                description=f"Erreur authentification OAuth {self.provider.get_provider_type().value}",
                error_details=str(e),
                request=request
            )
            raise