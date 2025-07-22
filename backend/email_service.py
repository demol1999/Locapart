"""
Service d'envoi d'emails basique pour les invitations
"""
from typing import List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmailRecipient:
    """Destinataire d'un email"""
    email: str
    name: Optional[str] = None


@dataclass
class EmailMessage:
    """Message email"""
    subject: str
    html_content: str
    text_content: Optional[str] = None


class EmailService:
    """Service d'envoi d'emails (implémentation basique pour dev)"""
    
    def __init__(self):
        self.enabled = False  # Désactivé par défaut pour le dev
        logger.info("EmailService initialisé en mode développement (envois désactivés)")
    
    async def send_email(
        self, 
        recipients: List[EmailRecipient], 
        message: EmailMessage,
        sender_email: Optional[str] = None
    ) -> bool:
        """
        Envoie un email aux destinataires
        En mode dev, log seulement le message
        """
        try:
            if not self.enabled:
                logger.info(f"[DEV MODE] Email non envoyé:")
                logger.info(f"  Destinataires: {[r.email for r in recipients]}")
                logger.info(f"  Sujet: {message.subject}")
                logger.info(f"  Contenu: {message.text_content or 'HTML uniquement'}")
                return True
            
            # En production, implémenter l'envoi réel (SMTP, SendGrid, etc.)
            logger.warning("EmailService: Envoi d'email en production non implémenté")
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi d'email: {e}")
            return False
    
    def set_enabled(self, enabled: bool):
        """Active ou désactive l'envoi d'emails"""
        self.enabled = enabled
        logger.info(f"EmailService: envois {'activés' if enabled else 'désactivés'}")


# Instance globale
email_service = EmailService()