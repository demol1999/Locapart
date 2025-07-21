"""
Service d'invitation des locataires avec tokens d'accès
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text

from database import get_db, Base
from models import Tenant, Lease, UserAuth, TenantInvitation
from email_service import EmailService, EmailRecipient, EmailMessage
from audit_logger import AuditLogger


# Le modèle TenantInvitation est maintenant dans models.py


class TenantInvitationService:
    """Service pour gérer les invitations de locataires"""
    
    def __init__(self, db: Session, email_service: EmailService, audit_logger: AuditLogger):
        self.db = db
        self.email_service = email_service
        self.audit_logger = audit_logger
    
    def generate_invitation_token(self) -> str:
        """Génère un token d'invitation sécurisé"""
        # Générer un token random
        random_part = secrets.token_urlsafe(32)
        
        # Ajouter un timestamp pour éviter les collisions
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        # Combiner et hasher pour plus de sécurité
        token_data = f"{random_part}_{timestamp}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()
        
        return f"{random_part}_{token_hash[:16]}"
    
    def create_invitation(self, tenant_id: int, invited_by_user_id: int, 
                         expires_in_hours: int = 168) -> Optional[TenantInvitation]:
        """
        Crée une invitation pour un locataire
        expires_in_hours: durée de validité du token (défaut: 7 jours)
        """
        
        # Vérifier que le locataire existe
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Locataire avec ID {tenant_id} introuvable")
        
        # Vérifier que l'utilisateur qui invite existe
        inviting_user = self.db.query(UserAuth).filter(UserAuth.id == invited_by_user_id).first()
        if not inviting_user:
            raise ValueError(f"Utilisateur invitant avec ID {invited_by_user_id} introuvable")
        
        # Vérifier qu'il n'y a pas déjà une invitation active
        existing_invitation = self.db.query(TenantInvitation).filter(
            TenantInvitation.tenant_id == tenant_id,
            TenantInvitation.is_used == False,
            TenantInvitation.token_expires_at > datetime.utcnow()
        ).first()
        
        if existing_invitation:
            raise ValueError("Une invitation active existe déjà pour ce locataire")
        
        # Générer le token
        token = self.generate_invitation_token()
        
        # Calculer la date d'expiration
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        # Créer l'invitation
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            invited_by=invited_by_user_id,
            invitation_token=token,
            token_expires_at=expires_at,
            email_sent_to=tenant.email,
            invitation_data=json.dumps({
                "tenant_name": f"{tenant.first_name} {tenant.last_name}",
                "tenant_email": tenant.email,
                "inviting_user": inviting_user.email,
                "created_at": datetime.utcnow().isoformat()
            })
        )
        
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        
        # Log de l'action
        self.audit_logger.log_action(
            user_id=invited_by_user_id,
            action="CREATE",
            entity_type="TENANT_INVITATION",
            entity_id=invitation.id,
            description=f"Création d'invitation pour {tenant.first_name} {tenant.last_name}",
            details=json.dumps({
                "invitation_id": invitation.id,
                "tenant_id": tenant_id,
                "tenant_email": tenant.email,
                "expires_at": expires_at.isoformat()
            })
        )
        
        return invitation
    
    async def send_invitation_email(self, invitation_id: int, 
                                  base_url: str = "http://localhost:3000") -> bool:
        """
        Envoie l'email d'invitation au locataire
        """
        
        # Récupérer l'invitation
        invitation = self.db.query(TenantInvitation).filter(
            TenantInvitation.id == invitation_id
        ).first()
        
        if not invitation:
            raise ValueError(f"Invitation avec ID {invitation_id} introuvable")
        
        if invitation.is_sent:
            raise ValueError("Cette invitation a déjà été envoyée")
        
        if invitation.token_expires_at <= datetime.utcnow():
            raise ValueError("Cette invitation a expiré")
        
        # Récupérer les informations du locataire
        tenant = self.db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if not tenant:
            raise ValueError("Locataire introuvable")
        
        # Récupérer le bail actif pour avoir les infos de l'appartement
        lease = self.db.query(Lease).filter(
            Lease.tenant_id == tenant.id,
            Lease.status == "ACTIVE"
        ).first()
        
        # Construire l'URL d'accès
        access_url = f"{base_url}/tenant-portal/access?token={invitation.invitation_token}"
        
        # Préparer les variables pour le template
        template_variables = {
            "tenant_name": f"{tenant.first_name} {tenant.last_name}",
            "tenant_first_name": tenant.first_name,
            "access_url": access_url,
            "expires_at": invitation.token_expires_at.strftime("%d/%m/%Y à %H:%M"),
            "company_name": "LocAppart",
            "support_email": "support@locappart.com"
        }
        
        # Ajouter les infos de l'appartement si disponible
        if lease and lease.apartment:
            template_variables.update({
                "apartment_info": f"Appartement {lease.apartment.apartment_number or 'N/A'}",
                "building_address": lease.apartment.building.address if lease.apartment.building else "Adresse non disponible"
            })
        
        # Préparer le destinataire
        recipient = EmailRecipient(email=tenant.email, name=f"{tenant.first_name} {tenant.last_name}")
        
        try:
            # Envoyer l'email avec template si disponible
            if self.email_service.template_engine:
                result = await self.email_service.send_template_email(
                    template_name="tenant_invitation",
                    recipients=[recipient],
                    subject="Accès à votre espace locataire - LocAppart",
                    variables=template_variables
                )
            else:
                # Fallback: email HTML simple
                html_content = self._generate_simple_invitation_html(template_variables)
                text_content = self._generate_simple_invitation_text(template_variables)
                
                message = EmailMessage(
                    to=[recipient],
                    subject="Accès à votre espace locataire - LocAppart",
                    html_content=html_content,
                    text_content=text_content
                )
                
                result = await self.email_service.send_email(message)
            
            if result.success:
                # Marquer l'invitation comme envoyée
                invitation.is_sent = True
                invitation.sent_at = datetime.utcnow()
                invitation.email_message_id = result.message_id
                invitation.updated_at = datetime.utcnow()
                
                self.db.commit()
                
                # Log de l'action
                self.audit_logger.log_action(
                    user_id=invitation.invited_by,
                    action="SEND",
                    entity_type="TENANT_INVITATION",
                    entity_id=invitation.id,
                    description=f"Envoi d'invitation par email à {tenant.email}",
                    details=json.dumps({
                        "invitation_id": invitation.id,
                        "tenant_email": tenant.email,
                        "message_id": result.message_id
                    })
                )
                
                return True
            else:
                # Log de l'erreur
                self.audit_logger.log_action(
                    user_id=invitation.invited_by,
                    action="ERROR",
                    entity_type="TENANT_INVITATION",
                    entity_id=invitation.id,
                    description=f"Échec d'envoi d'invitation à {tenant.email}",
                    details=json.dumps({
                        "invitation_id": invitation.id,
                        "error": result.error_message
                    })
                )
                
                return False
                
        except Exception as e:
            # Log de l'erreur
            self.audit_logger.log_action(
                user_id=invitation.invited_by,
                action="ERROR",
                entity_type="TENANT_INVITATION",
                entity_id=invitation.id,
                description=f"Erreur lors de l'envoi d'invitation à {tenant.email}",
                details=json.dumps({
                    "invitation_id": invitation.id,
                    "error": str(e)
                })
            )
            
            raise e
    
    def validate_invitation_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valide un token d'invitation et retourne les informations du locataire
        """
        
        # Rechercher l'invitation
        invitation = self.db.query(TenantInvitation).filter(
            TenantInvitation.invitation_token == token
        ).first()
        
        if not invitation:
            return None
        
        # Vérifier que le token n'a pas expiré
        if invitation.token_expires_at <= datetime.utcnow():
            return None
        
        # Vérifier que l'invitation n'a pas déjà été utilisée
        if invitation.is_used:
            return None
        
        # Récupérer les informations du locataire
        tenant = self.db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if not tenant:
            return None
        
        return {
            "invitation_id": invitation.id,
            "tenant_id": tenant.id,
            "tenant_email": tenant.email,
            "tenant_name": f"{tenant.first_name} {tenant.last_name}",
            "expires_at": invitation.token_expires_at,
            "is_valid": True
        }
    
    def use_invitation_token(self, token: str) -> bool:
        """
        Marque un token d'invitation comme utilisé
        """
        
        invitation = self.db.query(TenantInvitation).filter(
            TenantInvitation.invitation_token == token,
            TenantInvitation.is_used == False,
            TenantInvitation.token_expires_at > datetime.utcnow()
        ).first()
        
        if not invitation:
            return False
        
        # Marquer comme utilisé
        invitation.is_used = True
        invitation.used_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Log de l'action
        self.audit_logger.log_action(
            user_id=None,  # Aucun utilisateur connecté
            action="USE",
            entity_type="TENANT_INVITATION",
            entity_id=invitation.id,
            description=f"Utilisation du token d'invitation",
            details=json.dumps({
                "invitation_id": invitation.id,
                "tenant_id": invitation.tenant_id,
                "used_at": invitation.used_at.isoformat()
            })
        )
        
        return True
    
    def get_tenant_invitations(self, user_id: int, include_expired: bool = False) -> list:
        """
        Récupère toutes les invitations créées par un utilisateur
        """
        
        query = self.db.query(TenantInvitation).filter(
            TenantInvitation.invited_by == user_id
        )
        
        if not include_expired:
            query = query.filter(TenantInvitation.token_expires_at > datetime.utcnow())
        
        invitations = query.order_by(TenantInvitation.created_at.desc()).all()
        
        return invitations
    
    def _generate_simple_invitation_html(self, variables: Dict[str, Any]) -> str:
        """Génère un email HTML simple sans template engine"""
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Accès à votre espace locataire</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h1 style="color: #2c3e50; text-align: center;">Accès à votre espace locataire</h1>
                
                <p>Bonjour {variables.get('tenant_first_name', '')},</p>
                
                <p>Votre propriétaire vous a donné accès à votre espace locataire sur <strong>{variables.get('company_name', 'LocAppart')}</strong>.</p>
                
                <p>Dans cet espace, vous pourrez consulter :</p>
                <ul>
                    <li>Les informations de votre bail</li>
                    <li>Les documents liés à votre location</li>
                    <li>Les états des lieux</li>
                    <li>Les informations de votre appartement</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{variables.get('access_url', '#')}" 
                       style="background-color: #3498db; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Accéder à mon espace locataire
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">
                    <strong>Important :</strong> Ce lien d'accès expire le {variables.get('expires_at', 'N/A')}.
                </p>
                
                <p style="font-size: 14px; color: #666;">
                    Si vous avez des questions, contactez-nous à : {variables.get('support_email', 'support@locappart.com')}
                </p>
                
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                <p style="font-size: 12px; color: #999; text-align: center;">
                    {variables.get('company_name', 'LocAppart')} - Gestion locative simplifiée
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_simple_invitation_text(self, variables: Dict[str, Any]) -> str:
        """Génère un email texte simple sans template engine"""
        
        return f"""
        Accès à votre espace locataire - {variables.get('company_name', 'LocAppart')}
        
        Bonjour {variables.get('tenant_first_name', '')},
        
        Votre propriétaire vous a donné accès à votre espace locataire sur {variables.get('company_name', 'LocAppart')}.
        
        Dans cet espace, vous pourrez consulter :
        - Les informations de votre bail
        - Les documents liés à votre location
        - Les états des lieux
        - Les informations de votre appartement
        
        Pour accéder à votre espace, cliquez sur ce lien :
        {variables.get('access_url', '#')}
        
        IMPORTANT : Ce lien d'accès expire le {variables.get('expires_at', 'N/A')}.
        
        Si vous avez des questions, contactez-nous à : {variables.get('support_email', 'support@locappart.com')}
        
        Cordialement,
        L'équipe {variables.get('company_name', 'LocAppart')}
        """


def get_tenant_invitation_service(db: Session = None) -> TenantInvitationService:
    """Factory pour créer le service d'invitation des locataires"""
    
    if db is None:
        db = next(get_db())
    
    # Créer le service d'email
    from email_service import create_email_service_from_env
    email_service = create_email_service_from_env()
    
    # Créer l'audit logger
    audit_logger = AuditLogger(db)
    
    return TenantInvitationService(db, email_service, audit_logger)