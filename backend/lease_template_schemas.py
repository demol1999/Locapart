"""
Schémas Pydantic pour la génération et gestion des baux
"""
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, date
from enum import Enum
from lease_template_models import LeaseType, LeaseStatus, TenantProfile


# ==================== ÉNUMÉRATIONS ====================

class LeaseTypeEnum(str, Enum):
    """Types de baux pour validation Pydantic"""
    UNFURNISHED = "UNFURNISHED"
    FURNISHED = "FURNISHED"
    SEASONAL = "SEASONAL"
    STUDENT = "STUDENT"
    COMMERCIAL = "COMMERCIAL"
    GARAGE = "GARAGE"
    PROFESSIONAL = "PROFESSIONAL"


class LeaseStatusEnum(str, Enum):
    """Statuts des baux pour validation Pydantic"""
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED"
    FULLY_SIGNED = "FULLY_SIGNED"
    ACTIVE = "ACTIVE"
    TERMINATED = "TERMINATED"
    EXPIRED = "EXPIRED"


class TenantProfileEnum(str, Enum):
    """Profils de locataires pour validation Pydantic"""
    STUDENT = "STUDENT"
    YOUNG_PROFESSIONAL = "YOUNG_PROFESSIONAL"
    FAMILY = "FAMILY"
    SENIOR = "SENIOR"
    ANY = "ANY"


class SignerRoleEnum(str, Enum):
    """Rôles des signataires"""
    LANDLORD = "landlord"
    TENANT = "tenant"
    GUARANTOR = "guarantor"
    WITNESS = "witness"
    AGENT = "agent"


# ==================== SCHÉMAS DE BASE ====================

class ContactInfo(BaseModel):
    """Informations de contact d'une personne"""
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: str = "France"
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    id_number: Optional[str] = None  # Numéro de pièce d'identité


class TenantPreferences(BaseModel):
    """Préférences pour le type de locataire souhaité"""
    income_multiplier: float = Field(3.0, ge=1.0, le=10.0)  # Revenus minimum en multiple du loyer
    allowed_profiles: List[TenantProfileEnum] = [TenantProfileEnum.ANY]
    max_occupants: Optional[int] = Field(None, ge=1, le=10)
    pets_allowed: bool = False
    smoking_allowed: bool = False
    guarantor_required: bool = True
    student_status_required: bool = False
    minimum_age: Optional[int] = Field(None, ge=18, le=99)
    maximum_age: Optional[int] = Field(None, ge=18, le=99)
    preferred_gender: Optional[str] = Field(None, regex="^(male|female|any)$")
    
    @validator('maximum_age')
    def validate_age_range(cls, v, values):
        if v and 'minimum_age' in values and values['minimum_age']:
            if v < values['minimum_age']:
                raise ValueError('L\'âge maximum doit être supérieur à l\'âge minimum')
        return v


class FinancialTerms(BaseModel):
    """Conditions financières du bail"""
    monthly_rent: float = Field(..., gt=0)
    charges: float = Field(0, ge=0)
    deposit: float = Field(..., ge=0)
    agency_fees: Optional[float] = Field(None, ge=0)
    other_fees: Optional[float] = Field(None, ge=0)
    indexation_reference: str = "IRL"  # Indice de Référence des Loyers
    rent_payment_day: int = Field(1, ge=1, le=31)  # Jour du mois pour paiement


class FurnitureItem(BaseModel):
    """Élément de mobilier"""
    name: str
    category: str  # bedroom, kitchen, living_room, etc.
    description: Optional[str] = None
    quantity: int = Field(1, ge=1)
    estimated_value: Optional[float] = Field(None, ge=0)
    condition: str = "good"  # excellent, good, fair, poor
    brand: Optional[str] = None
    purchase_date: Optional[date] = None


# ==================== SCHÉMAS POUR LES TEMPLATES ====================

class LeaseTemplateCreate(BaseModel):
    """Schéma pour créer un template de bail"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    lease_type: LeaseTypeEnum
    apartment_id: Optional[int] = None
    is_public: bool = False
    
    # Configuration du template
    template_data: Dict[str, Any]
    
    @validator('template_data')
    def validate_template_data(cls, v):
        required_keys = ['sections', 'standard_clauses']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Le template doit contenir la clé: {key}')
        return v


class LeaseTemplateUpdate(BaseModel):
    """Schéma pour mettre à jour un template"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    lease_type: Optional[LeaseTypeEnum] = None
    is_public: Optional[bool] = None
    template_data: Optional[Dict[str, Any]] = None


class LeaseTemplateOut(BaseModel):
    """Schéma de sortie pour un template"""
    id: int
    created_by: int
    apartment_id: Optional[int]
    name: str
    description: Optional[str]
    lease_type: str
    is_public: bool
    is_default: bool
    template_data: Dict[str, Any]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LES BAUX GÉNÉRÉS ====================

class GeneratedLeaseCreate(BaseModel):
    """Schéma pour générer un bail"""
    template_id: Optional[int] = None  # Si null, création manuelle
    apartment_id: int
    lease_type: LeaseTypeEnum
    title: str = Field(..., min_length=1, max_length=300)
    
    # Informations des parties
    landlord_info: ContactInfo
    tenant_info: Optional[ContactInfo] = None  # Peut être ajouté plus tard
    guarantor_info: Optional[ContactInfo] = None
    agent_info: Optional[ContactInfo] = None
    
    # Conditions financières
    financial_terms: FinancialTerms
    
    # Durée
    start_date: date
    duration_months: int = Field(..., ge=1, le=120)  # Max 10 ans
    
    # Préférences de locataire (si pas encore de locataire)
    tenant_preferences: Optional[TenantPreferences] = None
    
    # Mobilier (pour baux meublés)
    furniture_inventory: Optional[List[FurnitureItem]] = []
    
    # Clauses personnalisées
    custom_clauses: Optional[List[str]] = []
    additional_notes: Optional[str] = None
    
    @validator('start_date')
    def validate_start_date(cls, v):
        if v < date.today():
            raise ValueError('La date de début ne peut pas être dans le passé')
        return v


class GeneratedLeaseUpdate(BaseModel):
    """Schéma pour mettre à jour un bail généré"""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    status: Optional[LeaseStatusEnum] = None
    
    # Informations des parties
    landlord_info: Optional[ContactInfo] = None
    tenant_info: Optional[ContactInfo] = None
    guarantor_info: Optional[ContactInfo] = None
    agent_info: Optional[ContactInfo] = None
    
    # Conditions financières
    financial_terms: Optional[FinancialTerms] = None
    
    # Durée
    start_date: Optional[date] = None
    duration_months: Optional[int] = Field(None, ge=1, le=120)
    
    # Préférences
    tenant_preferences: Optional[TenantPreferences] = None
    
    # Mobilier
    furniture_inventory: Optional[List[FurnitureItem]] = None
    
    # Clauses
    custom_clauses: Optional[List[str]] = None
    additional_notes: Optional[str] = None


class GeneratedLeaseOut(BaseModel):
    """Schéma de sortie pour un bail généré"""
    id: int
    template_id: Optional[int]
    created_by: int
    apartment_id: int
    
    lease_type: str
    status: str
    title: str
    
    # Données du bail
    lease_data: Dict[str, Any]
    tenant_preferences: Optional[Dict[str, Any]]
    
    # Conditions financières
    monthly_rent: Optional[float]
    charges: Optional[float]
    deposit: Optional[float]
    fees: Optional[float]
    
    # Durée
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    duration_months: Optional[int]
    
    # Documents
    pdf_document_path: Optional[str]
    pdf_document_hash: Optional[str]
    pdf_document_size: Optional[int]
    
    # Signature
    signature_request_id: Optional[str]
    signature_status: Optional[str]
    signature_url: Optional[str]
    signed_document_url: Optional[str]
    signed_document_path: Optional[str]
    
    # Upload
    is_uploaded: bool
    original_filename: Optional[str]
    uploaded_document_path: Optional[str]
    
    # Métadonnées
    created_at: datetime
    updated_at: datetime
    generated_at: Optional[datetime]
    signed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR L'UPLOAD ====================

class LeaseUploadCreate(BaseModel):
    """Schéma pour upload d'un bail existant"""
    apartment_id: int
    lease_type: LeaseTypeEnum
    title: str = Field(..., min_length=1, max_length=300)
    
    # Informations minimales
    monthly_rent: Optional[float] = Field(None, gt=0)
    start_date: Optional[date] = None
    duration_months: Optional[int] = Field(None, ge=1, le=120)
    
    # Parties impliquées (pour la signature)
    landlord_email: Optional[str] = None
    tenant_email: Optional[str] = None
    guarantor_email: Optional[str] = None
    
    description: Optional[str] = None


# ==================== SCHÉMAS POUR LES SIGNATURES ====================

class LeaseSignatureCreate(BaseModel):
    """Schéma pour ajouter un signataire"""
    signer_name: str = Field(..., min_length=1, max_length=200)
    signer_email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    signer_role: SignerRoleEnum
    signer_phone: Optional[str] = None
    signing_order: int = Field(1, ge=1, le=10)


class LeaseSignatureOut(BaseModel):
    """Schéma de sortie pour une signature"""
    id: int
    lease_id: int
    signer_name: str
    signer_email: str
    signer_role: str
    signer_phone: Optional[str]
    signing_order: int
    status: str
    signature_url: Optional[str]
    is_verified: bool
    invitation_sent_at: Optional[datetime]
    reminder_count: int
    last_reminder_at: Optional[datetime]
    signed_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LA SIGNATURE ÉLECTRONIQUE ====================

class LeaseSignatureRequest(BaseModel):
    """Schéma pour demander la signature d'un bail"""
    lease_id: int
    title: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    expires_in_days: int = Field(30, ge=1, le=365)
    
    # Signataires
    signers: List[LeaseSignatureCreate]
    
    # Options
    send_notifications: bool = True
    require_all_signatures: bool = True
    signing_order_enforced: bool = False
    
    @validator('signers')
    def validate_signers(cls, v):
        if not v:
            raise ValueError('Au moins un signataire est requis')
        
        # Vérifier l'unicité des emails
        emails = [s.signer_email for s in v]
        if len(emails) != len(set(emails)):
            raise ValueError('Les emails des signataires doivent être uniques')
        
        # Vérifier l'ordre de signature
        orders = [s.signing_order for s in v]
        if len(orders) != len(set(orders)):
            raise ValueError('Les ordres de signature doivent être uniques')
        
        return v


class LeaseSignatureStatus(BaseModel):
    """Schéma de statut de signature d'un bail"""
    lease_id: int
    signature_request_id: Optional[str]
    status: Optional[str]
    signing_url: Optional[str]
    signed_document_url: Optional[str]
    expires_at: Optional[datetime]
    total_signers: int
    signed_count: int
    pending_count: int
    error_message: Optional[str]


# ==================== SCHÉMAS POUR LES CLAUSES ====================

class LeaseClauseCreate(BaseModel):
    """Schéma pour créer une clause"""
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    is_mandatory: bool = False
    is_public: bool = False
    applies_to_types: Optional[List[LeaseTypeEnum]] = []
    variables: Optional[Dict[str, str]] = {}


class LeaseClauseOut(BaseModel):
    """Schéma de sortie pour une clause"""
    id: int
    created_by: int
    title: str
    category: str
    content: str
    is_mandatory: bool
    is_public: bool
    applies_to_types: Optional[List[str]]
    variables: Optional[Dict[str, str]]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR L'EXPORT ET LA GÉNÉRATION ====================

class LeaseGenerationRequest(BaseModel):
    """Demande de génération de PDF"""
    lease_id: int
    format: str = Field("pdf", regex="^(pdf|docx|html)$")
    include_attachments: bool = True
    language: str = Field("fr", regex="^(fr|en)$")
    watermark: Optional[str] = None


class LeaseGenerationResult(BaseModel):
    """Résultat de génération"""
    lease_id: int
    format: str
    file_url: str
    file_size: int
    generated_at: datetime
    expires_at: Optional[datetime]
    download_count: int = 0


# ==================== SCHÉMAS POUR LES STATISTIQUES ====================

class LeaseStats(BaseModel):
    """Statistiques des baux"""
    total_leases: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    pending_signatures: int
    signed_this_month: int
    average_rent: Optional[float]
    total_revenue: Optional[float]


# ==================== VALIDATIONS PERSONNALISÉES ====================

class GeneratedLeaseCreate(GeneratedLeaseCreate):
    """Version étendue avec validations"""
    
    @validator('duration_months')
    def validate_duration_for_type(cls, v, values):
        if 'lease_type' in values:
            lease_type = values['lease_type']
            if lease_type == LeaseTypeEnum.UNFURNISHED and v < 36:
                raise ValueError('Un bail nu doit être d\'au moins 3 ans (36 mois)')
            elif lease_type == LeaseTypeEnum.FURNISHED and v < 12:
                raise ValueError('Un bail meublé doit être d\'au moins 1 an (12 mois)')
            elif lease_type == LeaseTypeEnum.STUDENT and v > 12:
                raise ValueError('Un bail étudiant ne peut excéder 1 an (12 mois)')
        return v
    
    @validator('financial_terms')
    def validate_financial_terms(cls, v):
        # Le dépôt de garantie ne peut excéder 2 mois de loyer pour un bail nu
        # ou 1 mois pour un bail meublé
        if v.deposit > v.monthly_rent * 2:
            raise ValueError('Le dépôt de garantie ne peut excéder 2 mois de loyer')
        return v