"""
Service de signature électronique avec architecture SOLID
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
import os
from datetime import datetime, timedelta
import base64
import hashlib


class SignatureProvider(Enum):
    """Types de providers de signature électronique supportés"""
    DOCUSIGN = "docusign"
    HELLOSIGN = "hellosign"  # Dropbox Sign
    ADOBE_SIGN = "adobe_sign"
    SIGNREQUEST = "signrequest"
    MOCK = "mock"  # Pour les tests


class DocumentStatus(Enum):
    """Statuts d'un document à signer"""
    DRAFT = "draft"
    SENT = "sent"
    SIGNED = "signed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class Signer:
    """Signataire d'un document"""
    name: str
    email: str
    role: str = "signer"  # signer, approver, viewer
    order: int = 1  # Ordre de signature
    client_id: Optional[str] = None  # ID client pour tracking


@dataclass
class SignatureField:
    """Champ de signature sur un document"""
    page: int
    x: float  # Position X (0-1)
    y: float  # Position Y (0-1)
    width: float = 0.2
    height: float = 0.1
    type: str = "signature"  # signature, initial, date, text
    required: bool = True
    signer_email: Optional[str] = None


@dataclass
class SignatureDocument:
    """Document à faire signer"""
    name: str
    content: bytes  # Contenu du document (PDF)
    content_type: str = "application/pdf"
    fields: List[SignatureField] = None


@dataclass
class SignatureRequest:
    """Demande de signature"""
    title: str
    subject: str
    message: Optional[str] = None
    documents: List[SignatureDocument] = None
    signers: List[Signer] = None
    expires_in_days: int = 30
    test_mode: bool = False
    client_id: Optional[str] = None  # ID pour tracking côté client


@dataclass
class SignatureResult:
    """Résultat d'une demande de signature"""
    success: bool
    signature_request_id: Optional[str] = None
    status: Optional[DocumentStatus] = None
    signing_url: Optional[str] = None  # URL pour signer
    error_message: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


@dataclass
class SignedDocument:
    """Document signé"""
    document_id: str
    name: str
    content: bytes
    content_type: str = "application/pdf"
    signed_at: Optional[datetime] = None
    signers: List[Dict[str, Any]] = None


class ISignatureProvider(ABC):
    """Interface pour les providers de signature électronique"""
    
    @abstractmethod
    async def send_signature_request(self, request: SignatureRequest) -> SignatureResult:
        """Envoie une demande de signature"""
        pass
    
    @abstractmethod
    async def get_signature_status(self, signature_request_id: str) -> SignatureResult:
        """Récupère le statut d'une demande de signature"""
        pass
    
    @abstractmethod
    async def get_signed_document(self, signature_request_id: str) -> Optional[SignedDocument]:
        """Récupère le document signé"""
        pass
    
    @abstractmethod
    async def cancel_signature_request(self, signature_request_id: str) -> bool:
        """Annule une demande de signature"""
        pass
    
    @abstractmethod
    def validate_configuration(self) -> bool:
        """Valide la configuration du provider"""
        pass


class DocuSignProvider(ISignatureProvider):
    """Provider de signature électronique utilisant DocuSign"""
    
    def __init__(self, api_key: str, account_id: str, base_url: str = "https://demo.docusign.net/restapi"):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = base_url
        
        # Import optionnel de docusign
        try:
            from docusign_esign import ApiClient, EnvelopesApi, Configuration
            self.docusign_available = True
            self.api_client = None
            self.config = Configuration()
            self.config.host = base_url
        except ImportError:
            self.docusign_available = False
    
    def validate_configuration(self) -> bool:
        """Valide la configuration DocuSign"""
        return bool(self.api_key and self.account_id and self.docusign_available)
    
    async def send_signature_request(self, request: SignatureRequest) -> SignatureResult:
        """Envoie une demande de signature via DocuSign"""
        if not self.validate_configuration():
            return SignatureResult(
                success=False,
                error_message="Configuration DocuSign invalide ou SDK non installé"
            )
        
        try:
            # Implémentation DocuSign ici
            # Pour l'instant, simulation
            return SignatureResult(
                success=True,
                signature_request_id=f"docusign_{hash(request.title)}",
                status=DocumentStatus.SENT,
                signing_url=f"https://demo.docusign.net/signing/{hash(request.title)}",
                expires_at=datetime.utcnow() + timedelta(days=request.expires_in_days)
            )
            
        except Exception as e:
            return SignatureResult(
                success=False,
                error_message=f"Erreur DocuSign: {str(e)}"
            )
    
    async def get_signature_status(self, signature_request_id: str) -> SignatureResult:
        """Récupère le statut DocuSign"""
        # Simulation pour l'instant
        return SignatureResult(
            success=True,
            signature_request_id=signature_request_id,
            status=DocumentStatus.SENT
        )
    
    async def get_signed_document(self, signature_request_id: str) -> Optional[SignedDocument]:
        """Récupère le document signé depuis DocuSign"""
        # Simulation pour l'instant
        return None
    
    async def cancel_signature_request(self, signature_request_id: str) -> bool:
        """Annule une demande DocuSign"""
        return True


class HelloSignProvider(ISignatureProvider):
    """Provider de signature électronique utilisant HelloSign/Dropbox Sign"""
    
    def __init__(self, api_key: str, test_mode: bool = True):
        self.api_key = api_key
        self.test_mode = test_mode
        
        # Import optionnel de dropbox-sign
        try:
            import dropbox_sign
            self.hellosign_available = True
        except ImportError:
            self.hellosign_available = False
    
    def validate_configuration(self) -> bool:
        """Valide la configuration HelloSign"""
        return bool(self.api_key and self.hellosign_available)
    
    async def send_signature_request(self, request: SignatureRequest) -> SignatureResult:
        """Envoie une demande de signature via HelloSign"""
        if not self.validate_configuration():
            return SignatureResult(
                success=False,
                error_message="Configuration HelloSign invalide ou SDK non installé"
            )
        
        try:
            # Implémentation HelloSign ici
            # Pour l'instant, simulation
            return SignatureResult(
                success=True,
                signature_request_id=f"hellosign_{hash(request.title)}",
                status=DocumentStatus.SENT,
                signing_url=f"https://app.hellosign.com/sign/{hash(request.title)}",
                expires_at=datetime.utcnow() + timedelta(days=request.expires_in_days)
            )
            
        except Exception as e:
            return SignatureResult(
                success=False,
                error_message=f"Erreur HelloSign: {str(e)}"
            )
    
    async def get_signature_status(self, signature_request_id: str) -> SignatureResult:
        """Récupère le statut HelloSign"""
        return SignatureResult(
            success=True,
            signature_request_id=signature_request_id,
            status=DocumentStatus.SENT
        )
    
    async def get_signed_document(self, signature_request_id: str) -> Optional[SignedDocument]:
        """Récupère le document signé depuis HelloSign"""
        return None
    
    async def cancel_signature_request(self, signature_request_id: str) -> bool:
        """Annule une demande HelloSign"""
        return True


class MockSignatureProvider(ISignatureProvider):
    """Provider de signature électronique simulé pour les tests"""
    
    def __init__(self):
        self.requests = {}  # Stockage en mémoire pour les tests
    
    def validate_configuration(self) -> bool:
        """Toujours valide pour les tests"""
        return True
    
    async def send_signature_request(self, request: SignatureRequest) -> SignatureResult:
        """Simule l'envoi d'une demande de signature"""
        
        request_id = f"mock_{datetime.utcnow().timestamp()}_{hash(request.title)}"
        
        # Stocker la demande
        self.requests[request_id] = {
            "request": request,
            "status": DocumentStatus.SENT,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=request.expires_in_days)
        }
        
        return SignatureResult(
            success=True,
            signature_request_id=request_id,
            status=DocumentStatus.SENT,
            signing_url=f"https://mock-signature.locappart.com/sign/{request_id}",
            expires_at=datetime.utcnow() + timedelta(days=request.expires_in_days)
        )
    
    async def get_signature_status(self, signature_request_id: str) -> SignatureResult:
        """Simule la récupération du statut"""
        
        if signature_request_id not in self.requests:
            return SignatureResult(
                success=False,
                error_message="Demande de signature introuvable"
            )
        
        stored_request = self.requests[signature_request_id]
        
        return SignatureResult(
            success=True,
            signature_request_id=signature_request_id,
            status=stored_request["status"],
            expires_at=stored_request["expires_at"]
        )
    
    async def get_signed_document(self, signature_request_id: str) -> Optional[SignedDocument]:
        """Simule la récupération d'un document signé"""
        
        if signature_request_id not in self.requests:
            return None
        
        stored_request = self.requests[signature_request_id]
        
        # Créer un document PDF simulé
        mock_pdf_content = b"%PDF-1.4 Mock signed document content"
        
        return SignedDocument(
            document_id=signature_request_id,
            name=f"{stored_request['request'].title}_signed.pdf",
            content=mock_pdf_content,
            signed_at=datetime.utcnow(),
            signers=[
                {
                    "name": signer.name,
                    "email": signer.email,
                    "signed_at": datetime.utcnow().isoformat()
                }
                for signer in stored_request['request'].signers or []
            ]
        )
    
    async def cancel_signature_request(self, signature_request_id: str) -> bool:
        """Simule l'annulation d'une demande"""
        
        if signature_request_id in self.requests:
            self.requests[signature_request_id]["status"] = DocumentStatus.CANCELLED
            return True
        
        return False
    
    def simulate_signing(self, signature_request_id: str) -> bool:
        """Méthode utilitaire pour simuler la signature (tests uniquement)"""
        
        if signature_request_id in self.requests:
            self.requests[signature_request_id]["status"] = DocumentStatus.COMPLETED
            return True
        
        return False


class SignatureProviderFactory:
    """Factory pour créer les providers de signature électronique"""
    
    @staticmethod
    def create_provider(provider_type: SignatureProvider, **config) -> ISignatureProvider:
        """Crée un provider de signature selon le type"""
        
        if provider_type == SignatureProvider.DOCUSIGN:
            return DocuSignProvider(
                api_key=config.get("api_key", ""),
                account_id=config.get("account_id", ""),
                base_url=config.get("base_url", "https://demo.docusign.net/restapi")
            )
        
        elif provider_type == SignatureProvider.HELLOSIGN:
            return HelloSignProvider(
                api_key=config.get("api_key", ""),
                test_mode=config.get("test_mode", True)
            )
        
        elif provider_type == SignatureProvider.MOCK:
            return MockSignatureProvider()
        
        else:
            raise ValueError(f"Provider de signature non supporté: {provider_type}")


class ElectronicSignatureService:
    """Service principal de signature électronique"""
    
    def __init__(self, provider: ISignatureProvider):
        self.provider = provider
    
    async def send_signature_request(self, request: SignatureRequest) -> SignatureResult:
        """Envoie une demande de signature via le provider configuré"""
        return await self.provider.send_signature_request(request)
    
    async def get_signature_status(self, signature_request_id: str) -> SignatureResult:
        """Récupère le statut d'une demande de signature"""
        return await self.provider.get_signature_status(signature_request_id)
    
    async def get_signed_document(self, signature_request_id: str) -> Optional[SignedDocument]:
        """Récupère le document signé"""
        return await self.provider.get_signed_document(signature_request_id)
    
    async def cancel_signature_request(self, signature_request_id: str) -> bool:
        """Annule une demande de signature"""
        return await self.provider.cancel_signature_request(signature_request_id)
    
    def validate_provider(self) -> bool:
        """Valide que le provider est correctement configuré"""
        return self.provider.validate_configuration()


def create_signature_service_from_env() -> ElectronicSignatureService:
    """Crée un service de signature à partir des variables d'environnement"""
    
    # Déterminer le provider à utiliser
    provider_name = os.getenv("SIGNATURE_PROVIDER", "mock").lower()
    
    try:
        provider_type = SignatureProvider(provider_name)
    except ValueError:
        provider_type = SignatureProvider.MOCK
    
    # Configuration selon le provider
    if provider_type == SignatureProvider.DOCUSIGN:
        config = {
            "api_key": os.getenv("DOCUSIGN_API_KEY", ""),
            "account_id": os.getenv("DOCUSIGN_ACCOUNT_ID", ""),
            "base_url": os.getenv("DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi")
        }
    
    elif provider_type == SignatureProvider.HELLOSIGN:
        config = {
            "api_key": os.getenv("HELLOSIGN_API_KEY", ""),
            "test_mode": os.getenv("HELLOSIGN_TEST_MODE", "true").lower() == "true"
        }
    
    else:  # MOCK
        config = {}
    
    # Créer le provider
    provider = SignatureProviderFactory.create_provider(provider_type, **config)
    
    return ElectronicSignatureService(provider)


# Utilitaires pour générer des documents PDF
def create_inventory_pdf(inventory_data: Dict[str, Any], template_path: Optional[str] = None) -> bytes:
    """Crée un PDF d'état des lieux à partir des données"""
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from io import BytesIO
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        # Titre
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 750, f"État des lieux - {inventory_data.get('type', 'Entrée')}")
        
        # Informations générales
        p.setFont("Helvetica", 12)
        y = 700
        
        if inventory_data.get('apartment_info'):
            p.drawString(50, y, f"Appartement: {inventory_data['apartment_info']}")
            y -= 20
        
        if inventory_data.get('tenant_info'):
            p.drawString(50, y, f"Locataire: {inventory_data['tenant_info']}")
            y -= 20
        
        if inventory_data.get('conducted_date'):
            p.drawString(50, y, f"Date: {inventory_data['conducted_date']}")
            y -= 20
        
        y -= 20
        
        # Détail des pièces
        if inventory_data.get('rooms'):
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, y, "Détail des pièces:")
            y -= 30
            
            for room in inventory_data['rooms']:
                p.setFont("Helvetica-Bold", 12)
                p.drawString(50, y, f"{room.get('name', 'Pièce inconnue')}")
                y -= 20
                
                p.setFont("Helvetica", 10)
                if room.get('items'):
                    for item in room['items']:
                        item_text = f"• {item.get('name', 'Élément')} - État: {item.get('condition', 'Non renseigné')}"
                        p.drawString(70, y, item_text)
                        y -= 15
                        
                        if y < 50:  # Nouvelle page si nécessaire
                            p.showPage()
                            y = 750
                
                y -= 10
        
        # Signatures
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Signatures:")
        y -= 30
        
        p.setFont("Helvetica", 10)
        p.drawString(50, y, "Propriétaire/Gestionnaire: ________________________")
        p.drawString(350, y, "Locataire: ________________________")
        y -= 30
        p.drawString(50, y, "Date: ________________")
        p.drawString(350, y, "Date: ________________")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return buffer.read()
        
    except ImportError:
        # Fallback: créer un PDF simple avec du texte
        content = f"""
État des lieux - {inventory_data.get('type', 'Entrée')}

Appartement: {inventory_data.get('apartment_info', 'Non renseigné')}
Locataire: {inventory_data.get('tenant_info', 'Non renseigné')}
Date: {inventory_data.get('conducted_date', 'Non renseigné')}

Ce document nécessite une signature électronique.
        """.strip()
        
        return content.encode('utf-8')


def get_signature_fields_for_inventory() -> List[SignatureField]:
    """Retourne les champs de signature standards pour un état des lieux"""
    
    return [
        # Signature du propriétaire/gestionnaire
        SignatureField(
            page=1,
            x=0.1,  # 10% de la largeur
            y=0.15,  # 15% de la hauteur (bas de page)
            width=0.3,
            height=0.1,
            type="signature",
            required=True
        ),
        # Date propriétaire
        SignatureField(
            page=1,
            x=0.1,
            y=0.05,
            width=0.2,
            height=0.05,
            type="date",
            required=True
        ),
        # Signature du locataire
        SignatureField(
            page=1,
            x=0.6,  # 60% de la largeur
            y=0.15,
            width=0.3,
            height=0.1,
            type="signature",
            required=True
        ),
        # Date locataire
        SignatureField(
            page=1,
            x=0.6,
            y=0.05,
            width=0.2,
            height=0.05,
            type="date",
            required=True
        )
    ]