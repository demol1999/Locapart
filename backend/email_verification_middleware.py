"""
Middleware pour vérifier l'email sur certaines actions critiques
"""
from fastapi import HTTPException, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from models import UserAuth, AuthType

def require_verified_email(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Middleware qui exige que l'email soit vérifié pour certaines actions.
    À utiliser sur les endpoints critiques.
    """
    
    # Les utilisateurs OAuth ont leurs emails automatiquement vérifiés
    oauth_types = [AuthType.GOOGLE_OAUTH, AuthType.FACEBOOK_OAUTH, AuthType.MICROSOFT_OAUTH]
    
    if current_user.auth_type in oauth_types:
        # OAuth users are automatically verified
        if not current_user.email_verified:
            # Update user to be verified if using OAuth
            current_user.email_verified = True
            db.commit()
        return current_user
    
    # Pour les utilisateurs email/password, vérifier explicitement
    if not current_user.email_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Email non vérifié. Veuillez vérifier votre email avant de continuer.",
                "error_code": "EMAIL_NOT_VERIFIED",
                "action_required": "verify_email"
            }
        )
    
    return current_user


def require_verified_email_for_critical_actions():
    """
    Version plus stricte pour les actions très critiques
    (ex: paiements, signatures, etc.)
    """
    def dependency(current_user: UserAuth = Depends(require_verified_email)):
        # Vérification supplémentaire pour les actions critiques
        # Peut inclure d'autres vérifications comme 2FA, etc.
        return current_user
    
    return dependency


class EmailVerificationStatus:
    """Helper pour vérifier le statut sans lever d'exception"""
    
    @staticmethod
    def is_verified(user: UserAuth) -> bool:
        """Vérifie si l'email est vérifié"""
        # OAuth users are considered verified
        oauth_types = [AuthType.GOOGLE_OAUTH, AuthType.FACEBOOK_OAUTH, AuthType.MICROSOFT_OAUTH]
        
        if user.auth_type in oauth_types:
            return True
        
        return user.email_verified
    
    @staticmethod
    def needs_verification(user: UserAuth) -> bool:
        """Vérifie si l'utilisateur a besoin de vérifier son email"""
        return not EmailVerificationStatus.is_verified(user)
    
    @staticmethod
    def get_verification_message(user: UserAuth) -> str:
        """Retourne un message approprié selon le statut"""
        if EmailVerificationStatus.is_verified(user):
            return "Email vérifié"
        else:
            return "Email non vérifié. Veuillez vérifier votre adresse email."