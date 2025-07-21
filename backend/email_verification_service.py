"""
Service de vérification d'email avec architecture SOLID
"""
import secrets
import string
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from database import Base
import os
import json

# ==================== MODÈLES ====================

class EmailVerification(Base):
    """Modèle pour les codes de vérification d'email"""
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    email = Column(String(255), nullable=False)
    verification_code = Column(String(10), nullable=False)  # Code à 6 chiffres
    verification_token = Column(String(255), nullable=True)  # Token pour URL
    
    # Expiration et statut
    expires_at = Column(DateTime, nullable=False)
    is_verified = Column(Boolean, default=False)
    is_used = Column(Boolean, default=False)
    
    # Tentatives
    attempts_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )


# ==================== INTERFACES ====================

class IEmailProvider(ABC):
    """Interface pour les providers d'email"""
    
    @abstractmethod
    async def send_verification_email(
        self, 
        to_email: str, 
        verification_code: str,
        verification_url: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Envoie un email de vérification"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Retourne le nom du provider"""
        pass


class IVerificationCodeGenerator(ABC):
    """Interface pour la génération de codes"""
    
    @abstractmethod
    def generate_code(self) -> str:
        """Génère un code de vérification"""
        pass
    
    @abstractmethod
    def generate_token(self) -> str:
        """Génère un token sécurisé"""
        pass


# ==================== IMPLEMENTATIONS ====================

class NumericCodeGenerator(IVerificationCodeGenerator):
    """Générateur de codes numériques à 6 chiffres"""
    
    def generate_code(self) -> str:
        """Génère un code à 6 chiffres"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def generate_token(self) -> str:
        """Génère un token URL-safe"""
        return secrets.token_urlsafe(32)


class ResendEmailProvider(IEmailProvider):
    """Provider Resend (recommandé - gratuit jusqu'à 3000 emails/mois)"""
    
    def __init__(self, api_key: str, from_email: str = "noreply@locappart.fr"):
        self.api_key = api_key
        self.from_email = from_email
    
    async def send_verification_email(
        self, 
        to_email: str, 
        verification_code: str,
        verification_url: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Envoie via Resend API"""
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Template HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Vérification de votre email - LocAppart</title>
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #2563eb;">LocAppart</h1>
                    <h2 style="color: #374151;">Vérifiez votre adresse email</h2>
                </div>
                
                <p>Bonjour {user_name},</p>
                
                <p>Merci de vous être inscrit sur LocAppart ! Pour finaliser votre inscription, veuillez vérifier votre adresse email.</p>
                
                <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                    <p style="margin: 0; font-size: 14px; color: #6b7280;">Votre code de vérification :</p>
                    <h1 style="font-size: 36px; color: #2563eb; margin: 10px 0; letter-spacing: 8px; font-family: monospace;">{verification_code}</h1>
                    <p style="margin: 0; font-size: 12px; color: #9ca3af;">Ce code expire dans 15 minutes</p>
                </div>
                
                <p>Vous pouvez aussi cliquer sur ce lien pour vérifier automatiquement :</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        Vérifier mon email
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #6b7280;">
                    Si vous n'avez pas créé de compte sur LocAppart, vous pouvez ignorer cet email.
                    <br>
                    Ce lien de vérification expirera dans 15 minutes pour votre sécurité.
                </p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <p style="font-size: 12px; color: #9ca3af;">
                        © 2024 LocAppart - Plateforme de gestion immobilière
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Version texte
            text_content = f"""
            Vérification de votre email - LocAppart
            
            Bonjour {user_name},
            
            Merci de vous être inscrit sur LocAppart ! Pour finaliser votre inscription, 
            veuillez vérifier votre adresse email.
            
            Votre code de vérification : {verification_code}
            
            Ou cliquez sur ce lien : {verification_url}
            
            Ce code expire dans 15 minutes.
            
            Si vous n'avez pas créé de compte, ignorez cet email.
            
            © 2024 LocAppart
            """
            
            payload = {
                "from": self.from_email,
                "to": to_email,
                "subject": "Vérifiez votre email - LocAppart",
                "html": html_content,
                "text": text_content
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider": "resend",
                        "message_id": response.json().get("id"),
                        "data": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "provider": "resend",
                        "error": response.text,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "provider": "resend",
                "error": str(e)
            }
    
    def get_provider_name(self) -> str:
        return "Resend"


class MailgunEmailProvider(IEmailProvider):
    """Provider Mailgun (gratuit jusqu'à 5000 emails/mois)"""
    
    def __init__(self, api_key: str, domain: str, from_email: str):
        self.api_key = api_key
        self.domain = domain
        self.from_email = from_email
    
    async def send_verification_email(
        self, 
        to_email: str, 
        verification_code: str,
        verification_url: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Envoie via Mailgun API"""
        try:
            import httpx
            import base64
            
            # Auth basique
            auth = base64.b64encode(f"api:{self.api_key}".encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth}",
            }
            
            data = {
                "from": self.from_email,
                "to": to_email,
                "subject": "Vérifiez votre email - LocAppart",
                "text": f"Votre code de vérification : {verification_code}\nLien : {verification_url}",
                "html": f"""
                <h2>Vérifiez votre email</h2>
                <p>Bonjour {user_name},</p>
                <p>Votre code de vérification : <strong>{verification_code}</strong></p>
                <a href="{verification_url}">Vérifier mon email</a>
                """
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.mailgun.net/v3/{self.domain}/messages",
                    headers=headers,
                    data=data,
                    timeout=30.0
                )
                
                return {
                    "success": response.status_code == 200,
                    "provider": "mailgun",
                    "data": response.json() if response.status_code == 200 else response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "provider": "mailgun",
                "error": str(e)
            }
    
    def get_provider_name(self) -> str:
        return "Mailgun"


class SMTPEmailProvider(IEmailProvider):
    """Provider SMTP classique (pour serveur personnel)"""
    
    def __init__(self, host: str, port: int, username: str, password: str, from_email: str, use_tls: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
    
    async def send_verification_email(
        self, 
        to_email: str, 
        verification_code: str,
        verification_url: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Envoie via SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Vérifiez votre email - LocAppart"
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Version texte
            text = f"""
            Vérification de votre email - LocAppart
            
            Bonjour {user_name},
            
            Votre code de vérification : {verification_code}
            Lien de vérification : {verification_url}
            
            Ce code expire dans 15 minutes.
            """
            
            # Version HTML
            html = f"""
            <html>
            <body>
                <h2>Vérifiez votre email</h2>
                <p>Bonjour {user_name},</p>
                <p>Votre code de vérification : <strong style="font-size: 24px;">{verification_code}</strong></p>
                <p><a href="{verification_url}" style="color: #2563eb;">Vérifier mon email</a></p>
                <p><small>Ce code expire dans 15 minutes.</small></p>
            </body>
            </html>
            """
            
            # Attacher les parties
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Envoyer
            server = smtplib.SMTP(self.host, self.port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            
            return {
                "success": True,
                "provider": "smtp",
                "message": "Email envoyé via SMTP"
            }
            
        except Exception as e:
            return {
                "success": False,
                "provider": "smtp",
                "error": str(e)
            }
    
    def get_provider_name(self) -> str:
        return "SMTP"


# ==================== FACTORY ====================

class EmailProviderFactory:
    """Factory pour créer les providers d'email selon la configuration"""
    
    @staticmethod
    def create_provider() -> IEmailProvider:
        """Crée le provider selon les variables d'environnement"""
        
        provider_type = os.getenv("EMAIL_PROVIDER", "resend").lower()
        
        if provider_type == "resend":
            api_key = os.getenv("RESEND_API_KEY")
            if not api_key:
                raise ValueError("RESEND_API_KEY manquante dans les variables d'environnement")
            
            from_email = os.getenv("RESEND_FROM_EMAIL", "noreply@locappart.fr")
            return ResendEmailProvider(api_key, from_email)
        
        elif provider_type == "mailgun":
            api_key = os.getenv("MAILGUN_API_KEY")
            domain = os.getenv("MAILGUN_DOMAIN")
            from_email = os.getenv("MAILGUN_FROM_EMAIL")
            
            if not all([api_key, domain, from_email]):
                raise ValueError("Variables Mailgun manquantes (MAILGUN_API_KEY, MAILGUN_DOMAIN, MAILGUN_FROM_EMAIL)")
            
            return MailgunEmailProvider(api_key, domain, from_email)
        
        elif provider_type == "smtp":
            host = os.getenv("SMTP_HOST")
            port = int(os.getenv("SMTP_PORT", "587"))
            username = os.getenv("SMTP_USERNAME")
            password = os.getenv("SMTP_PASSWORD")
            from_email = os.getenv("SMTP_FROM_EMAIL")
            use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            
            if not all([host, username, password, from_email]):
                raise ValueError("Variables SMTP manquantes")
            
            return SMTPEmailProvider(host, port, username, password, from_email, use_tls)
        
        else:
            raise ValueError(f"Provider d'email non supporté: {provider_type}")


# ==================== SERVICE PRINCIPAL ====================

class EmailVerificationService:
    """Service principal de vérification d'email"""
    
    def __init__(self, db: Session, email_provider: IEmailProvider = None, code_generator: IVerificationCodeGenerator = None):
        self.db = db
        self.email_provider = email_provider or EmailProviderFactory.create_provider()
        self.code_generator = code_generator or NumericCodeGenerator()
        self.verification_expiry_minutes = 15  # Expire dans 15 minutes
    
    async def send_verification_email(
        self, 
        user_id: int, 
        email: str, 
        user_name: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Envoie un email de vérification"""
        
        try:
            # Invalider les codes précédents pour cet utilisateur
            self.db.query(EmailVerification).filter(
                EmailVerification.user_id == user_id,
                EmailVerification.is_used == False
            ).update({"is_used": True})
            
            # Générer nouveau code et token
            verification_code = self.code_generator.generate_code()
            verification_token = self.code_generator.generate_token()
            
            # Créer l'enregistrement
            verification = EmailVerification(
                user_id=user_id,
                email=email,
                verification_code=verification_code,
                verification_token=verification_token,
                expires_at=datetime.utcnow() + timedelta(minutes=self.verification_expiry_minutes),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(verification)
            self.db.commit()
            self.db.refresh(verification)
            
            # URL de vérification
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            verification_url = f"{base_url}/verify-email?token={verification_token}"
            
            # Envoyer l'email
            result = await self.email_provider.send_verification_email(
                to_email=email,
                verification_code=verification_code,
                verification_url=verification_url,
                user_name=user_name
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Email de vérification envoyé",
                    "verification_id": verification.id,
                    "expires_at": verification.expires_at,
                    "provider": self.email_provider.get_provider_name()
                }
            else:
                # Marquer comme échoué
                verification.is_used = True
                self.db.commit()
                
                return {
                    "success": False,
                    "message": "Erreur lors de l'envoi de l'email",
                    "error": result.get("error", "Erreur inconnue")
                }
                
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": "Erreur système lors de l'envoi",
                "error": str(e)
            }
    
    def verify_code(self, user_id: int, code: str) -> Dict[str, Any]:
        """Vérifie un code de vérification"""
        
        # Récupérer la vérification en cours
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.is_used == False,
            EmailVerification.is_verified == False,
            EmailVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not verification:
            return {
                "success": False,
                "message": "Aucun code de vérification valide trouvé"
            }
        
        # Incrémenter les tentatives
        verification.attempts_count += 1
        
        # Vérifier si trop de tentatives
        if verification.attempts_count > verification.max_attempts:
            verification.is_used = True
            self.db.commit()
            return {
                "success": False,
                "message": "Trop de tentatives. Demandez un nouveau code."
            }
        
        # Vérifier le code
        if verification.verification_code == code:
            # Code correct
            verification.is_verified = True
            verification.verified_at = datetime.utcnow()
            
            # Marquer l'utilisateur comme vérifié
            from models import UserAuth
            user = self.db.query(UserAuth).filter(UserAuth.id == user_id).first()
            if user:
                user.email_verified = True
                user.email_verified_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Email vérifié avec succès!"
            }
        else:
            # Code incorrect
            self.db.commit()
            remaining_attempts = verification.max_attempts - verification.attempts_count
            
            return {
                "success": False,
                "message": f"Code incorrect. {remaining_attempts} tentatives restantes."
            }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Vérifie un token de vérification (via URL)"""
        
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.verification_token == token,
            EmailVerification.is_used == False,
            EmailVerification.is_verified == False,
            EmailVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not verification:
            return {
                "success": False,
                "message": "Token de vérification invalide ou expiré"
            }
        
        # Marquer comme vérifié
        verification.is_verified = True
        verification.verified_at = datetime.utcnow()
        
        # Marquer l'utilisateur comme vérifié
        from models import UserAuth
        user = self.db.query(UserAuth).filter(UserAuth.id == verification.user_id).first()
        if user:
            user.email_verified = True
            user.email_verified_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Email vérifié avec succès!",
            "user_id": verification.user_id
        }


# Factory pour créer le service
def create_verification_service(db: Session) -> EmailVerificationService:
    """Factory pour créer le service de vérification"""
    return EmailVerificationService(db)