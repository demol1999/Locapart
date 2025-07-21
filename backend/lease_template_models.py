"""
Modèles pour la génération et gestion des baux
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Numeric, JSON, LargeBinary
from sqlalchemy.orm import relationship
from database import Base
import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class LeaseType(str, Enum):
    """Types de baux"""
    UNFURNISHED = "UNFURNISHED"        # Nu
    FURNISHED = "FURNISHED"            # Meublé
    SEASONAL = "SEASONAL"              # Saisonnier
    STUDENT = "STUDENT"                # Étudiant
    COMMERCIAL = "COMMERCIAL"          # Commercial
    GARAGE = "GARAGE"                  # Garage/Parking
    PROFESSIONAL = "PROFESSIONAL"     # Professionnel


class LeaseStatus(str, Enum):
    """Statuts des baux générés"""
    DRAFT = "DRAFT"                    # Brouillon
    GENERATED = "GENERATED"            # Généré, prêt à signer
    PENDING_SIGNATURE = "PENDING_SIGNATURE"  # En attente de signature
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED"    # Partiellement signé
    FULLY_SIGNED = "FULLY_SIGNED"            # Entièrement signé
    ACTIVE = "ACTIVE"                        # Actif (en cours)
    TERMINATED = "TERMINATED"                # Résilié
    EXPIRED = "EXPIRED"                      # Expiré


class TenantProfile(str, Enum):
    """Profils de locataires souhaités"""
    STUDENT = "STUDENT"                # Étudiant
    YOUNG_PROFESSIONAL = "YOUNG_PROFESSIONAL"  # Jeune actif
    FAMILY = "FAMILY"                  # Famille
    SENIOR = "SENIOR"                  # Senior
    ANY = "ANY"                        # Peu importe


class LeaseTemplate(Base):
    """Template de bail personnalisable"""
    __tablename__ = "lease_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)  # Spécifique à un appartement ou général
    
    # Informations générales du template
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    lease_type = Column(String(20), nullable=False)        # Type de bail
    is_public = Column(Boolean, default=False)             # Accessible à tous les utilisateurs
    is_default = Column(Boolean, default=False)            # Template par défaut
    
    # Configuration du bail
    template_data = Column(JSON, nullable=False)           # Structure et clauses du bail
    
    # Statistiques d'utilisation
    usage_count = Column(Integer, default=0)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    creator = relationship("UserAuth")
    apartment = relationship("Apartment")
    generated_leases = relationship("GeneratedLease", back_populates="template")


class GeneratedLease(Base):
    """Bail généré à partir d'un template"""
    __tablename__ = "generated_leases"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("lease_templates.id"), nullable=True)  # Peut être null si upload direct
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    
    # Informations du bail
    lease_type = Column(String(20), nullable=False)
    status = Column(String(20), default=LeaseStatus.DRAFT)
    
    # Données du bail
    title = Column(String(300), nullable=False)
    lease_data = Column(JSON, nullable=False)              # Toutes les données du bail
    
    # Préférences de locataire
    tenant_preferences = Column(JSON, nullable=True)       # Critères souhaités
    
    # Conditions financières
    monthly_rent = Column(Numeric(10, 2), nullable=True)
    charges = Column(Numeric(10, 2), nullable=True)
    deposit = Column(Numeric(10, 2), nullable=True)
    fees = Column(Numeric(10, 2), nullable=True)
    
    # Durée
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    duration_months = Column(Integer, nullable=True)
    
    # Documents générés
    pdf_document_path = Column(String(500), nullable=True)     # Chemin du PDF généré
    pdf_document_hash = Column(String(64), nullable=True)      # Hash du PDF pour intégrité
    pdf_document_size = Column(Integer, nullable=True)         # Taille du fichier
    
    # Workflow de signature
    signature_request_id = Column(String(255), nullable=True)  # ID de la demande de signature
    signature_status = Column(String(50), nullable=True)       # Statut de la signature
    signature_url = Column(String(500), nullable=True)         # URL de signature
    signed_document_url = Column(String(500), nullable=True)   # URL du document signé
    signed_document_path = Column(String(500), nullable=True)  # Chemin local du document signé
    
    # Upload direct (alternative au template)
    is_uploaded = Column(Boolean, default=False)              # Document uploadé vs généré
    original_filename = Column(String(255), nullable=True)    # Nom original si uploadé
    uploaded_document_path = Column(String(500), nullable=True) # Chemin du document uploadé
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    generated_at = Column(DateTime, nullable=True)             # Date de génération du PDF
    signed_at = Column(DateTime, nullable=True)                # Date de signature complète
    
    # Relations
    template = relationship("LeaseTemplate", back_populates="generated_leases")
    creator = relationship("UserAuth", foreign_keys=[created_by])
    apartment = relationship("Apartment", backref="generated_leases")
    signatures = relationship("LeaseSignature", back_populates="lease", cascade="all, delete-orphan")


class LeaseSignature(Base):
    """Signatures associées à un bail"""
    __tablename__ = "lease_signatures"
    
    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("generated_leases.id"), nullable=False)
    
    # Informations du signataire
    signer_name = Column(String(200), nullable=False)
    signer_email = Column(String(255), nullable=False)
    signer_role = Column(String(50), nullable=False)      # landlord, tenant, guarantor, witness
    signer_phone = Column(String(20), nullable=True)
    
    # Ordre de signature
    signing_order = Column(Integer, default=1)            # Ordre dans lequel la personne doit signer
    
    # Données de signature
    signature_data = Column(Text, nullable=True)          # Signature au format base64 ou référence
    signature_method = Column(String(50), nullable=True)  # electronic, manual, biometric
    signature_ip = Column(String(45), nullable=True)      # Adresse IP du signataire
    signature_device = Column(String(200), nullable=True) # Informations sur l'appareil
    signature_location = Column(String(200), nullable=True) # Lieu de signature
    
    # Statut
    status = Column(String(20), default="PENDING")        # PENDING, SIGNED, DECLINED, EXPIRED
    signature_url = Column(String(500), nullable=True)    # URL personnalisée pour ce signataire
    
    # Validation et sécurité
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(100), nullable=True)
    verification_method = Column(String(50), nullable=True) # sms, email, call
    
    # Notifications
    invitation_sent_at = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)
    last_reminder_at = Column(DateTime, nullable=True)
    
    # Métadonnées
    signed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)           # Expiration de l'invitation
    
    # Relations
    lease = relationship("GeneratedLease", back_populates="signatures")


class LeaseClause(Base):
    """Clauses réutilisables pour les baux"""
    __tablename__ = "lease_clauses"
    
    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Informations de la clause
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)         # rent, charges, deposit, rules, etc.
    content = Column(Text, nullable=False)                # Texte de la clause
    
    # Configuration
    is_mandatory = Column(Boolean, default=False)         # Clause obligatoire
    is_public = Column(Boolean, default=False)            # Accessible à tous
    applies_to_types = Column(JSON, nullable=True)        # Types de baux auxquels s'applique
    
    # Variables dans la clause
    variables = Column(JSON, nullable=True)               # Variables à remplacer (ex: {{monthly_rent}})
    
    # Métadonnées
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    creator = relationship("UserAuth")


# Fonctions utilitaires pour créer des templates par défaut

def create_standard_unfurnished_lease_template() -> Dict[str, Any]:
    """Crée un template standard pour bail nu"""
    
    return {
        "name": "Bail nu standard",
        "description": "Template standard pour location vide (loi du 6 juillet 1989)",
        "lease_type": "UNFURNISHED",
        "duration_months": 36,  # 3 ans par défaut
        "sections": [
            {
                "title": "DESIGNATION DES PARTIES",
                "order": 1,
                "fields": [
                    {"name": "landlord_info", "type": "object", "required": True},
                    {"name": "tenant_info", "type": "object", "required": True},
                    {"name": "guarantor_info", "type": "object", "required": False}
                ]
            },
            {
                "title": "DESIGNATION DU LOGEMENT",
                "order": 2,
                "fields": [
                    {"name": "apartment_address", "type": "string", "required": True},
                    {"name": "apartment_type", "type": "string", "required": True},
                    {"name": "surface_area", "type": "number", "required": True},
                    {"name": "room_count", "type": "number", "required": True},
                    {"name": "floor", "type": "number", "required": False},
                    {"name": "building_year", "type": "number", "required": False}
                ]
            },
            {
                "title": "CONDITIONS FINANCIÈRES",
                "order": 3,
                "fields": [
                    {"name": "monthly_rent", "type": "number", "required": True},
                    {"name": "charges", "type": "number", "required": True},
                    {"name": "deposit", "type": "number", "required": True},
                    {"name": "agency_fees", "type": "number", "required": False},
                    {"name": "indexation_reference", "type": "string", "required": True}
                ]
            },
            {
                "title": "DURÉE ET RENOUVELLEMENT",
                "order": 4,
                "fields": [
                    {"name": "start_date", "type": "date", "required": True},
                    {"name": "duration_months", "type": "number", "required": True},
                    {"name": "renewal_conditions", "type": "text", "required": True}
                ]
            },
            {
                "title": "ÉTAT DES LIEUX",
                "order": 5,
                "fields": [
                    {"name": "entry_inventory_date", "type": "date", "required": False},
                    {"name": "exit_inventory_date", "type": "date", "required": False},
                    {"name": "inventory_notes", "type": "text", "required": False}
                ]
            }
        ],
        "standard_clauses": [
            {
                "category": "obligations_tenant",
                "title": "Obligations du locataire",
                "content": "Le locataire s'engage à :\n- Payer le loyer et les charges aux échéances convenues\n- Occuper paisiblement les lieux\n- Entretenir le logement en bon père de famille\n- Ne pas sous-louer sans autorisation écrite"
            },
            {
                "category": "obligations_landlord", 
                "title": "Obligations du bailleur",
                "content": "Le bailleur s'engage à :\n- Délivrer un logement décent et en bon état\n- Assurer la jouissance paisible du bien\n- Effectuer les réparations locatives nécessaires\n- Respecter le droit au maintien dans les lieux"
            }
        ],
        "tenant_preferences": {
            "income_multiplier": 3,  # Revenus minimum = 3x le loyer
            "allowed_profiles": ["YOUNG_PROFESSIONAL", "FAMILY", "ANY"],
            "max_occupants": None,
            "pets_allowed": False,
            "smoking_allowed": False,
            "guarantor_required": True
        }
    }


def create_furnished_lease_template() -> Dict[str, Any]:
    """Crée un template pour bail meublé"""
    
    template = create_standard_unfurnished_lease_template()
    template.update({
        "name": "Bail meublé standard",
        "description": "Template standard pour location meublée",
        "lease_type": "FURNISHED",
        "duration_months": 12,  # 1 an pour le meublé
    })
    
    # Ajouter section mobilier
    furniture_section = {
        "title": "INVENTAIRE DU MOBILIER",
        "order": 6,
        "fields": [
            {"name": "furniture_inventory", "type": "array", "required": True},
            {"name": "appliances_inventory", "type": "array", "required": True},
            {"name": "furniture_value", "type": "number", "required": False}
        ]
    }
    template["sections"].append(furniture_section)
    
    return template


def create_student_lease_template() -> Dict[str, Any]:
    """Crée un template pour bail étudiant"""
    
    template = create_furnished_lease_template()
    template.update({
        "name": "Bail étudiant",
        "description": "Template spécialisé pour location étudiante",
        "lease_type": "STUDENT",
        "duration_months": 9,  # Année scolaire
    })
    
    template["tenant_preferences"].update({
        "allowed_profiles": ["STUDENT"],
        "student_status_required": True,
        "guarantor_required": True,
        "income_multiplier": 2.5  # Moins strict pour les étudiants
    })
    
    return template