from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
import re

# Import centralisé des enums
from enums import (
    UserRole, PhotoType, RoomType, ActionType, EntityType,
    SubscriptionType, SubscriptionStatus, PaymentStatus, AuthType,
    FloorPlanType, DocumentType, LeaseStatus, TenantStatus,
    InvitationStatus, InventoryItemCondition, PropertyCondition
)

class AddressBase(BaseModel):
    street_number: Optional[str] = Field(None, max_length=100, description="Numéro de rue")
    street_name: Optional[str] = Field(None, max_length=500, description="Nom de la rue")
    complement: Optional[str] = Field(None, max_length=500, description="Complément d'adresse")
    postal_code: Optional[str] = Field(None, max_length=50, description="Code postal")
    city: Optional[str] = Field(None, max_length=200, description="Ville")
    country: Optional[str] = Field(None, max_length=200, description="Pays")
    
    @field_validator('postal_code')
    @classmethod
    def validate_postal_code(cls, v):
        if v and not re.match(r'^[0-9]{5}$', v):
            raise ValueError('Le code postal doit contenir exactement 5 chiffres')
        return v

class UserCreate(AddressBase):
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=8, max_length=255, description="Mot de passe")
    first_name: str = Field(..., max_length=100, description="Prénom")
    last_name: str = Field(..., max_length=100, description="Nom de famille")
    phone: str = Field(..., max_length=50, description="Numéro de téléphone")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        
        # Vérifier la complexité du mot de passe
        if not re.search(r'[A-Z]', v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        
        if not re.search(r'\d', v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Le mot de passe doit contenir au moins un caractère spécial')
            
        # Vérifier les mots de passe communs
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123', 
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        if v.lower() in common_passwords:
            raise ValueError('Ce mot de passe est trop commun, veuillez en choisir un autre')
        
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r'^[0-9+\-\s\(\)]{10,20}$', v):
            raise ValueError('Format de téléphone invalide')
        return v
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        if not v.strip():
            raise ValueError('Ce champ ne peut pas être vide')
        return v.strip()

class UserOut(AddressBase):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str

    model_config = {"from_attributes": True}

class BuildingBase(AddressBase):
    name: str = Field(..., max_length=255, description="Nom de l'immeuble")
    floors: int = Field(..., ge=1, le=200, description="Nombre d'étages")
    is_copro: bool = Field(default=False, description="Est-ce une copropriété")
    copro_id: Optional[int] = Field(None, description="ID de la copropriété")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Le nom de l\'immeuble ne peut pas être vide')
        return v.strip()
    
    @field_validator('floors')
    @classmethod
    def validate_floors(cls, v):
        if v < 1:
            raise ValueError('Le nombre d\'étages doit être supérieur à 0')
        if v > 200:
            raise ValueError('Le nombre d\'étages ne peut pas dépasser 200')
        return v

class BuildingCreate(BuildingBase):
    pass

class BuildingOut(BuildingBase):
    id: int
    copro: Optional['CoproOut'] = None
    model_config = {"from_attributes": True}

class ApartmentBase(BaseModel):
    type_logement: str = Field(..., max_length=50, description="Type de logement")
    layout: str = Field(..., max_length=50, description="Agencement")
    floor: Optional[int] = Field(None, ge=-5, le=200, description="Étage")
    
    @field_validator('type_logement', 'layout')
    @classmethod
    def validate_required_fields(cls, v):
        if not v.strip():
            raise ValueError('Ce champ ne peut pas être vide')
        return v.strip()
    
    @field_validator('floor')
    @classmethod
    def validate_floor(cls, v):
        if v is not None:
            if v < -5:
                raise ValueError('L\'étage ne peut pas être inférieur à -5')
            if v > 200:
                raise ValueError('L\'étage ne peut pas dépasser 200')
        return v

class ApartmentCreate(ApartmentBase):
    building_id: int

class ApartmentOut(ApartmentBase):
    id: int
    building_id: int

    model_config = {"from_attributes": True}

class ApartmentUserLinkOut(BaseModel):
    id: int
    user_id: int
    apartment_id: int
    role: UserRole

    model_config = {"from_attributes": True}

class RoleAssignment(BaseModel):
    user_id: int
    role: UserRole

class CoproBase(BaseModel):
    nom: Optional[str] = None
    adresse_rue: Optional[str] = None
    adresse_code_postal: Optional[str] = None
    adresse_ville: Optional[str] = None
    annee_construction: Optional[int] = None
    nb_batiments: Optional[int] = None
    nb_lots_total: Optional[int] = None
    nb_lots_principaux: Optional[int] = None
    nb_lots_secondaires: Optional[int] = None
    surface_totale_m2: Optional[int] = None
    type_construction: Optional[str] = None
    nb_etages: Optional[int] = None
    ascenseur: Optional[bool] = None
    nb_ascenseurs: Optional[int] = None
    chauffage_collectif_type: Optional[str] = None
    chauffage_individuel_type: Optional[str] = None
    clim_centralisee: Optional[bool] = None
    eau_chaude_collective: Optional[bool] = None
    isolation_thermique: Optional[str] = None
    isolation_annee: Optional[int] = None
    rt2012_re2020: Optional[bool] = None
    accessibilite_pmr: Optional[bool] = None
    toiture_type: Optional[str] = None
    toiture_materiaux: Optional[str] = None
    gardien: Optional[bool] = None
    local_velos: Optional[bool] = None
    parkings_ext: Optional[bool] = None
    nb_parkings_ext: Optional[int] = None
    parkings_int: Optional[bool] = None
    nb_parkings_int: Optional[int] = None
    caves: Optional[bool] = None
    nb_caves: Optional[int] = None
    espaces_verts: Optional[bool] = None
    jardins_partages: Optional[bool] = None
    piscine: Optional[bool] = None
    salle_sport: Optional[bool] = None
    aire_jeux: Optional[bool] = None
    salle_reunion: Optional[bool] = None
    dpe_collectif: Optional[str] = None
    audit_energetique: Optional[bool] = None
    audit_energetique_date: Optional[str] = None
    energie_utilisee: Optional[str] = None
    panneaux_solaires: Optional[bool] = None
    bornes_recharge: Optional[bool] = None

class CoproCreate(CoproBase):
    pass

class CoproUpdate(CoproBase):
    pass

class CoproOut(CoproBase):
    id: int
    model_config = {"from_attributes": True}

class SyndicatCoproBase(BaseModel):
    copro_id: int
    statut_juridique: Optional[str] = None
    date_creation: Optional[str] = None
    reglement_copro: Optional[bool] = None
    carnet_entretien: Optional[bool] = None
    nom_syndic: Optional[str] = None
    type_syndic: Optional[str] = None
    societe_syndic: Optional[str] = None
    date_derniere_ag: Optional[str] = None
    assurance_compagnie: Optional[str] = None
    assurance_num_police: Optional[str] = None
    assurance_validite: Optional[str] = None
    procedures_judiciaires: Optional[bool] = None
    procedures_details: Optional[str] = None
    budget_annuel_previsionnel: Optional[int] = None
    charges_annuelles_par_lot: Optional[int] = None
    charges_speciales: Optional[int] = None
    emprunt_collectif: Optional[bool] = None
    emprunt_montant: Optional[int] = None
    emprunt_echeance: Optional[str] = None
    taux_impayes_charges: Optional[int] = None
    fonds_roulement: Optional[int] = None
    fonds_travaux: Optional[int] = None
    travaux_votes: Optional[str] = None
    travaux_en_cours: Optional[str] = None

class SyndicatCoproCreate(SyndicatCoproBase):
    pass

class SyndicatCoproUpdate(SyndicatCoproBase):
    pass

class SyndicatCoproOut(SyndicatCoproBase):
    id: int
    model_config = {"from_attributes": True}

class ApartmentUserFullOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole

    model_config = {"from_attributes": True}

# ---------------------- ROOM SCHEMAS ----------------------

class RoomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nom de la pièce")
    room_type: RoomType = Field(..., description="Type de pièce")
    area_m2: Optional[Decimal] = Field(None, ge=0, description="Surface en m²")
    description: Optional[str] = Field(None, max_length=1000, description="Description de la pièce")
    floor_level: int = Field(0, ge=-5, le=50, description="Étage dans l'appartement")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Le nom de la pièce ne peut pas être vide')
        return v.strip()

class RoomCreate(RoomBase):
    apartment_id: int = Field(..., description="ID de l'appartement")

class RoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    room_type: Optional[RoomType] = None
    area_m2: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=1000)
    floor_level: Optional[int] = Field(None, ge=-5, le=50)
    sort_order: Optional[int] = Field(None, ge=0)

class RoomOut(RoomBase):
    id: int
    apartment_id: int
    sort_order: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class RoomWithPhotos(RoomOut):
    photos: List['PhotoOut'] = []
    
    model_config = {"from_attributes": True}

# ---------------------- PHOTO SCHEMAS ----------------------

class PhotoUpload(BaseModel):
    type: PhotoType = Field(..., description="Type de photo")
    building_id: Optional[int] = Field(None, description="ID de l'immeuble")
    apartment_id: Optional[int] = Field(None, description="ID de l'appartement")
    room_id: Optional[int] = Field(None, description="ID de la pièce")
    title: Optional[str] = Field(None, max_length=255, description="Titre de la photo")
    description: Optional[str] = Field(None, max_length=1000, description="Description de la photo")
    is_main: bool = Field(False, description="Photo principale")

class PhotoCreate(BaseModel):
    filename: str
    original_filename: Optional[str] = None
    type: PhotoType
    title: Optional[str] = None
    description: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: Optional[str] = None
    is_main: bool = False
    sort_order: int = 0
    building_id: Optional[int] = None
    apartment_id: Optional[int] = None
    room_id: Optional[int] = None

class PhotoUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_main: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)

class PhotoOut(BaseModel):
    id: int
    filename: str
    original_filename: Optional[str] = None
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: Optional[str] = None
    is_main: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    building_id: Optional[int] = None
    apartment_id: Optional[int] = None
    room_id: Optional[int] = None

    model_config = {"from_attributes": True}

class PhotoBatch(BaseModel):
    photos: List[PhotoOut]
    total: int
    has_main: bool

# ---------------------- AUDIT LOG SCHEMAS ----------------------

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: ActionType
    entity_type: EntityType
    entity_id: Optional[int] = None
    description: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    created_at: datetime
    
    # Informations utilisateur si disponible
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    model_config = {"from_attributes": True}

class AuditLogFilter(BaseModel):
    user_id: Optional[int] = None
    action: Optional[ActionType] = None
    entity_type: Optional[EntityType] = None
    entity_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

# ---------------------- SUBSCRIPTION SCHEMAS ----------------------

class UserSubscriptionOut(BaseModel):
    id: int
    user_id: int
    subscription_type: SubscriptionType
    status: SubscriptionStatus
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancel_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    apartment_limit: int
    
    model_config = {"from_attributes": True}

class SubscriptionUpgradeRequest(BaseModel):
    subscription_type: SubscriptionType = Field(..., description="Type d'abonnement souhaité")

class CheckoutSessionCreate(BaseModel):
    subscription_type: SubscriptionType = Field(..., description="Type d'abonnement")
    success_url: str = Field(..., description="URL de succès")
    cancel_url: str = Field(..., description="URL d'annulation")

# ---------------------- PAYMENT SCHEMAS ----------------------

class PaymentOut(BaseModel):
    id: int
    user_id: int
    subscription_id: Optional[int] = None
    stripe_payment_intent_id: str
    stripe_invoice_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: PaymentStatus
    description: Optional[str] = None
    failure_reason: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class PaymentHistoryFilter(BaseModel):
    status: Optional[PaymentStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class SubscriptionStats(BaseModel):
    total_users: int
    free_users: int
    premium_users: int
    active_subscriptions: int
    cancelled_subscriptions: int
    monthly_revenue: Decimal
    
class ApartmentLimitCheck(BaseModel):
    current_count: int
    limit: int
    can_add: bool
    subscription_type: SubscriptionType
    needs_upgrade: bool

# ---------------------- FLOOR PLAN SCHEMAS ----------------------

class FloorPlanType(str, Enum):
    room = "room"
    apartment = "apartment"

class FloorPlanElement(BaseModel):
    id: str = Field(..., description="ID unique de l'élément")
    type: str = Field(..., description="Type d'élément (wall, door, window)")
    startPoint: Optional[dict] = Field(None, description="Point de départ pour les murs")
    endPoint: Optional[dict] = Field(None, description="Point de fin pour les murs")
    wallId: Optional[str] = Field(None, description="ID du mur parent pour portes/fenêtres")
    position: Optional[dict] = Field(None, description="Position sur le mur")
    width: Optional[int] = Field(None, description="Largeur de l'élément")
    thickness: Optional[int] = Field(None, description="Épaisseur pour les murs")
    properties: Optional[dict] = Field(default={}, description="Propriétés spécifiques")

class FloorPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nom du plan")
    type: FloorPlanType = Field(..., description="Type de plan")
    room_id: Optional[int] = Field(None, description="ID de la pièce associée")
    apartment_id: Optional[int] = Field(None, description="ID de l'appartement associé")
    xml_data: Optional[str] = Field(None, description="Données XML du plan")
    scale: float = Field(1.0, ge=0.1, le=10.0, description="Échelle du plan")
    grid_size: int = Field(20, ge=5, le=100, description="Taille de la grille")
    elements: Optional[List[FloorPlanElement]] = Field(default=[], description="Éléments du plan")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Le nom du plan ne peut pas être vide')
        return v.strip()

class FloorPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    xml_data: Optional[str] = None
    scale: Optional[float] = Field(None, ge=0.1, le=10.0)
    grid_size: Optional[int] = Field(None, ge=5, le=100)
    elements: Optional[List[FloorPlanElement]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Le nom du plan ne peut pas être vide')
        return v.strip() if v else v

class FloorPlanOut(BaseModel):
    id: int
    name: str
    type: str
    room_id: Optional[int] = None
    apartment_id: Optional[int] = None
    xml_data: Optional[str] = None
    scale: float
    grid_size: int
    thumbnail_url: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class FloorPlanWithElements(FloorPlanOut):
    elements: List[FloorPlanElement] = []
    metadata: Optional[dict] = None

class FloorPlanTemplate(BaseModel):
    name: str
    elements: List[FloorPlanElement]

# ---------------------- RENTAL MANAGEMENT SCHEMAS ----------------------

class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    PENDING = "PENDING"

class DocumentType(str, Enum):
    LEASE = "LEASE"
    INVENTORY = "INVENTORY"
    INSURANCE = "INSURANCE"
    INCOME_PROOF = "INCOME_PROOF"
    ID_DOCUMENT = "ID_DOCUMENT"
    BANK_DETAILS = "BANK_DETAILS"
    DEPOSIT_RECEIPT = "DEPOSIT_RECEIPT"
    RENT_RECEIPT = "RENT_RECEIPT"
    OTHER = "OTHER"

class InventoryType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    PERIODIC = "PERIODIC"

# ---------------------- TENANT SCHEMAS ----------------------

class TenantBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom de famille")
    email: EmailStr = Field(..., description="Adresse email")
    phone: Optional[str] = Field(None, max_length=50, description="Numéro de téléphone")
    date_of_birth: Optional[datetime] = Field(None, description="Date de naissance")
    previous_address: Optional[str] = Field(None, max_length=1000, description="Adresse précédente")
    occupation: Optional[str] = Field(None, max_length=200, description="Profession")
    employer: Optional[str] = Field(None, max_length=200, description="Employeur")
    monthly_income: Optional[Decimal] = Field(None, ge=0, description="Revenus mensuels")
    emergency_contact_name: Optional[str] = Field(None, max_length=200, description="Contact d'urgence - Nom")
    emergency_contact_phone: Optional[str] = Field(None, max_length=50, description="Contact d'urgence - Téléphone")
    emergency_contact_relation: Optional[str] = Field(None, max_length=100, description="Contact d'urgence - Relation")
    notes: Optional[str] = Field(None, max_length=2000, description="Notes")
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        if not v.strip():
            raise ValueError('Ce champ ne peut pas être vide')
        return v.strip()

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[datetime] = None
    previous_address: Optional[str] = Field(None, max_length=1000)
    occupation: Optional[str] = Field(None, max_length=200)
    employer: Optional[str] = Field(None, max_length=200)
    monthly_income: Optional[Decimal] = Field(None, ge=0)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)
    emergency_contact_relation: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=2000)

class TenantOut(TenantBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# ---------------------- LEASE SCHEMAS ----------------------

class LeaseBase(BaseModel):
    start_date: datetime = Field(..., description="Date de début du bail")
    end_date: datetime = Field(..., description="Date de fin du bail")
    monthly_rent: Decimal = Field(..., ge=0, description="Loyer mensuel")
    charges: Decimal = Field(0.00, ge=0, description="Charges mensuelles")
    deposit: Decimal = Field(..., ge=0, description="Dépôt de garantie")
    renewable: bool = Field(True, description="Bail renouvelable")
    furnished: bool = Field(False, description="Logement meublé")
    lease_type: str = Field("RESIDENTIAL", max_length=50, description="Type de bail")
    notice_period_days: int = Field(30, ge=1, le=365, description="Préavis en jours")
    billing_address: Optional[str] = Field(None, max_length=1000, description="Adresse de facturation")
    notes: Optional[str] = Field(None, max_length=2000, description="Notes")
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, values):
        if 'start_date' in values.data and v <= values.data['start_date']:
            raise ValueError('La date de fin doit être postérieure à la date de début')
        return v

class LeaseCreate(LeaseBase):
    tenant_id: int = Field(..., description="ID du locataire")
    apartment_id: int = Field(..., description="ID de l'appartement")

class LeaseUpdate(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    monthly_rent: Optional[Decimal] = Field(None, ge=0)
    charges: Optional[Decimal] = Field(None, ge=0)
    deposit: Optional[Decimal] = Field(None, ge=0)
    status: Optional[LeaseStatus] = None
    renewable: Optional[bool] = None
    furnished: Optional[bool] = None
    lease_type: Optional[str] = Field(None, max_length=50)
    notice_period_days: Optional[int] = Field(None, ge=1, le=365)
    billing_address: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=2000)

class LeaseOut(LeaseBase):
    id: int
    tenant_id: int
    apartment_id: int
    created_by: int
    status: LeaseStatus
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class LeaseWithDetails(LeaseOut):
    tenant: TenantOut
    apartment: 'ApartmentOut'
    
    model_config = {"from_attributes": True}

# ---------------------- DOCUMENT SCHEMAS ----------------------

class TenantDocumentBase(BaseModel):
    document_type: DocumentType = Field(..., description="Type de document")
    title: str = Field(..., min_length=1, max_length=255, description="Titre du document")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    document_date: Optional[datetime] = Field(None, description="Date du document")
    expiry_date: Optional[datetime] = Field(None, description="Date d'expiration")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Le titre ne peut pas être vide')
        return v.strip()

class TenantDocumentCreate(TenantDocumentBase):
    tenant_id: int = Field(..., description="ID du locataire")
    lease_id: Optional[int] = Field(None, description="ID du bail (optionnel)")

class TenantDocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    document_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    is_verified: Optional[bool] = None
    verification_notes: Optional[str] = Field(None, max_length=1000)

class TenantDocumentOut(TenantDocumentBase):
    id: int
    tenant_id: int
    lease_id: Optional[int] = None
    uploaded_by: int
    filename: str
    original_filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_verified: bool
    verification_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# ---------------------- INVENTORY SCHEMAS ----------------------

class InventoryRoomData(BaseModel):
    room_name: str = Field(..., description="Nom de la pièce")
    condition: str = Field(..., description="État de la pièce")
    items: List[dict] = Field(default=[], description="Éléments de la pièce")
    notes: Optional[str] = Field(None, description="Notes spécifiques")

class InventoryBase(BaseModel):
    inventory_type: InventoryType = Field(..., description="Type d'état des lieux")
    conducted_date: datetime = Field(..., description="Date de réalisation")
    tenant_present: bool = Field(True, description="Locataire présent")
    landlord_present: bool = Field(True, description="Propriétaire présent")
    agent_present: bool = Field(False, description="Agent présent")
    overall_condition: Optional[str] = Field(None, max_length=50, description="État général")
    general_notes: Optional[str] = Field(None, max_length=2000, description="Notes générales")
    tenant_comments: Optional[str] = Field(None, max_length=2000, description="Commentaires locataire")
    landlord_comments: Optional[str] = Field(None, max_length=2000, description="Commentaires propriétaire")

class InventoryCreate(InventoryBase):
    lease_id: int = Field(..., description="ID du bail")
    rooms_data: Optional[List[InventoryRoomData]] = Field(default=[], description="Données des pièces")

class InventoryUpdate(BaseModel):
    conducted_date: Optional[datetime] = None
    tenant_present: Optional[bool] = None
    landlord_present: Optional[bool] = None
    agent_present: Optional[bool] = None
    overall_condition: Optional[str] = Field(None, max_length=50)
    general_notes: Optional[str] = Field(None, max_length=2000)
    tenant_comments: Optional[str] = Field(None, max_length=2000)
    landlord_comments: Optional[str] = Field(None, max_length=2000)
    rooms_data: Optional[List[InventoryRoomData]] = None
    tenant_signature: Optional[str] = None
    landlord_signature: Optional[str] = None
    agent_signature: Optional[str] = None
    is_finalized: Optional[bool] = None

class InventoryOut(InventoryBase):
    id: int
    lease_id: int
    conducted_by: int
    rooms_data: Optional[List[dict]] = None
    tenant_signature: Optional[str] = None
    landlord_signature: Optional[str] = None
    agent_signature: Optional[str] = None
    is_finalized: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# ---------------------- TENANT PORTAL SCHEMAS ----------------------

class TenantPortalInfo(BaseModel):
    """Informations pour l'espace locataire"""
    tenant: TenantOut
    current_lease: Optional[LeaseOut] = None
    apartment_info: Optional['ApartmentOut'] = None
    building_info: Optional['BuildingOut'] = None
    documents: List[TenantDocumentOut] = []
    inventories: List[InventoryOut] = []

class TenantLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email du locataire")
    lease_reference: Optional[str] = Field(None, description="Référence du bail (optionnel)")

# ---------------------- STATISTICS SCHEMAS ----------------------

class RentalStats(BaseModel):
    total_tenants: int
    active_leases: int
    pending_leases: int
    expired_leases: int
    total_monthly_revenue: Decimal
    occupancy_rate: float  # Pourcentage d'occupation

# ---------------------- STRIPE WEBHOOK SCHEMAS ----------------------

class StripeWebhookEvent(BaseModel):
    id: str
    type: str
    data: dict
    created: int