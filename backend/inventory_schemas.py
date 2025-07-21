"""
Schémas Pydantic pour les états des lieux détaillés
"""
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum
from inventory_models import (
    InventoryStatus, RoomType, ItemCondition, ItemCategory
)


# ==================== SCHÉMAS DE BASE ====================

class ItemConditionEnum(str, Enum):
    """États des éléments pour validation Pydantic"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    DAMAGED = "DAMAGED"
    MISSING = "MISSING"
    NEW = "NEW"
    TO_REPLACE = "TO_REPLACE"


class ItemCategoryEnum(str, Enum):
    """Catégories d'éléments pour validation Pydantic"""
    WALL = "WALL"
    FLOOR = "FLOOR"
    CEILING = "CEILING"
    WINDOW = "WINDOW"
    DOOR = "DOOR"
    FIXTURE = "FIXTURE"
    FURNITURE = "FURNITURE"
    APPLIANCE = "APPLIANCE"
    LIGHTING = "LIGHTING"
    PLUMBING = "PLUMBING"
    ELECTRICAL = "ELECTRICAL"
    HEATING = "HEATING"
    OTHER = "OTHER"


class RoomTypeEnum(str, Enum):
    """Types de pièces pour validation Pydantic"""
    KITCHEN = "KITCHEN"
    LIVING_ROOM = "LIVING_ROOM"
    DINING_ROOM = "DINING_ROOM"
    BEDROOM = "BEDROOM"
    BATHROOM = "BATHROOM"
    TOILET = "TOILET"
    ENTRANCE = "ENTRANCE"
    HALLWAY = "HALLWAY"
    BALCONY = "BALCONY"
    TERRACE = "TERRACE"
    GARAGE = "GARAGE"
    CELLAR = "CELLAR"
    STORAGE = "STORAGE"
    OFFICE = "OFFICE"
    LAUNDRY = "LAUNDRY"
    COMMON_AREA = "COMMON_AREA"
    OTHER = "OTHER"


# ==================== SCHÉMAS POUR LES ÉLÉMENTS ====================

class InventoryItemDefect(BaseModel):
    """Défaut sur un élément"""
    description: str
    severity: str = Field(..., regex="^(minor|moderate|major|critical)$")
    location: Optional[str] = None
    estimated_repair_cost: Optional[float] = None


class InventoryItemDimensions(BaseModel):
    """Dimensions d'un élément"""
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    unit: str = "cm"


class InventoryItemCreate(BaseModel):
    """Schéma pour créer un élément d'inventaire"""
    name: str = Field(..., min_length=1, max_length=100)
    category: ItemCategoryEnum
    description: Optional[str] = None
    condition: ItemConditionEnum
    
    # Caractéristiques optionnelles
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_until: Optional[datetime] = None
    
    # Valeur
    estimated_value: Optional[float] = Field(None, ge=0)
    replacement_cost: Optional[float] = Field(None, ge=0)
    
    # Position
    position_x: Optional[float] = Field(None, ge=0)
    position_y: Optional[float] = Field(None, ge=0)
    
    # Mesures
    dimensions: Optional[InventoryItemDimensions] = None
    weight: Optional[float] = Field(None, ge=0)
    
    # Observations
    notes: Optional[str] = None
    defects: Optional[List[InventoryItemDefect]] = []
    improvements: Optional[List[str]] = []
    
    # Métadonnées
    order: int = Field(1, ge=1)
    is_mandatory: bool = False
    item_data: Optional[Dict[str, Any]] = {}


class InventoryItemUpdate(BaseModel):
    """Schéma pour mettre à jour un élément"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[ItemCategoryEnum] = None
    description: Optional[str] = None
    condition: Optional[ItemConditionEnum] = None
    
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    replacement_cost: Optional[float] = Field(None, ge=0)
    
    position_x: Optional[float] = Field(None, ge=0)
    position_y: Optional[float] = Field(None, ge=0)
    dimensions: Optional[InventoryItemDimensions] = None
    weight: Optional[float] = Field(None, ge=0)
    
    notes: Optional[str] = None
    defects: Optional[List[InventoryItemDefect]] = None
    improvements: Optional[List[str]] = None
    
    order: Optional[int] = Field(None, ge=1)
    is_mandatory: Optional[bool] = None
    item_data: Optional[Dict[str, Any]] = None


class InventoryItemOut(BaseModel):
    """Schéma de sortie pour un élément"""
    id: int
    room_id: int
    name: str
    category: str
    description: Optional[str]
    condition: str
    previous_condition: Optional[str]
    
    brand: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    purchase_date: Optional[datetime]
    warranty_until: Optional[datetime]
    
    estimated_value: Optional[float]
    replacement_cost: Optional[float]
    
    position_x: Optional[float]
    position_y: Optional[float]
    dimensions: Optional[Dict[str, Any]]
    weight: Optional[float]
    
    notes: Optional[str]
    defects: Optional[List[Dict[str, Any]]]
    improvements: Optional[List[str]]
    
    order: int
    is_mandatory: bool
    item_data: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LES PIÈCES ====================

class InventoryRoomCreate(BaseModel):
    """Schéma pour créer une pièce"""
    name: str = Field(..., min_length=1, max_length=100)
    room_type: RoomTypeEnum
    order: int = Field(1, ge=1)
    
    # Dimensions
    length: Optional[float] = Field(None, gt=0)
    width: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    area: Optional[float] = Field(None, gt=0)
    
    # État
    overall_condition: Optional[ItemConditionEnum] = None
    notes: Optional[str] = None
    room_data: Optional[Dict[str, Any]] = {}
    
    # Éléments de la pièce
    items: Optional[List[InventoryItemCreate]] = []


class InventoryRoomUpdate(BaseModel):
    """Schéma pour mettre à jour une pièce"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    room_type: Optional[RoomTypeEnum] = None
    order: Optional[int] = Field(None, ge=1)
    
    length: Optional[float] = Field(None, gt=0)
    width: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    area: Optional[float] = Field(None, gt=0)
    
    overall_condition: Optional[ItemConditionEnum] = None
    notes: Optional[str] = None
    room_data: Optional[Dict[str, Any]] = None


class InventoryRoomOut(BaseModel):
    """Schéma de sortie pour une pièce"""
    id: int
    inventory_id: int
    name: str
    room_type: str
    order: int
    
    length: Optional[float]
    width: Optional[float]
    height: Optional[float]
    area: Optional[float]
    
    overall_condition: Optional[str]
    notes: Optional[str]
    room_data: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    
    items: List[InventoryItemOut] = []
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LES PARTICIPANTS ====================

class ParticipantInfo(BaseModel):
    """Informations d'un participant"""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None


class UtilityReading(BaseModel):
    """Relevé de compteur"""
    name: str
    type: str = Field(..., regex="^(electricity|gas|water_cold|water_hot|heating)$")
    reading: float = Field(..., ge=0)
    unit: str = "kWh"
    location: Optional[str] = None
    notes: Optional[str] = None


# ==================== SCHÉMAS POUR L'ÉTAT DES LIEUX ====================

class DetailedInventoryCreate(BaseModel):
    """Schéma pour créer un état des lieux détaillé"""
    lease_id: int
    apartment_id: int
    inventory_type: str = Field(..., regex="^(ENTRY|EXIT|PERIODIC)$")
    
    # Planification
    scheduled_date: Optional[datetime] = None
    
    # Participants
    tenant_present: bool = True
    landlord_present: bool = True
    agent_present: bool = False
    witness_present: bool = False
    
    # Informations des participants
    tenant_contact_info: Optional[ParticipantInfo] = None
    landlord_contact_info: Optional[ParticipantInfo] = None
    agent_contact_info: Optional[ParticipantInfo] = None
    witness_contact_info: Optional[ParticipantInfo] = None
    
    # Conditions
    weather_conditions: Optional[str] = None
    temperature: Optional[str] = None
    overall_condition: Optional[ItemConditionEnum] = None
    
    # Observations
    general_notes: Optional[str] = None
    tenant_comments: Optional[str] = None
    landlord_comments: Optional[str] = None
    agent_comments: Optional[str] = None
    
    # Relevés
    utilities_data: Optional[List[UtilityReading]] = []
    
    # Pièces (peuvent être ajoutées après)
    rooms: Optional[List[InventoryRoomCreate]] = []


class DetailedInventoryUpdate(BaseModel):
    """Schéma pour mettre à jour un état des lieux"""
    status: Optional[str] = Field(None, regex="^(DRAFT|IN_PROGRESS|PENDING_SIGNATURE|SIGNED|COMPLETED|CANCELLED)$")
    scheduled_date: Optional[datetime] = None
    conducted_date: Optional[datetime] = None
    
    tenant_present: Optional[bool] = None
    landlord_present: Optional[bool] = None
    agent_present: Optional[bool] = None
    witness_present: Optional[bool] = None
    
    tenant_contact_info: Optional[ParticipantInfo] = None
    landlord_contact_info: Optional[ParticipantInfo] = None
    agent_contact_info: Optional[ParticipantInfo] = None
    witness_contact_info: Optional[ParticipantInfo] = None
    
    weather_conditions: Optional[str] = None
    temperature: Optional[str] = None
    overall_condition: Optional[ItemConditionEnum] = None
    
    general_notes: Optional[str] = None
    tenant_comments: Optional[str] = None
    landlord_comments: Optional[str] = None
    agent_comments: Optional[str] = None
    
    utilities_data: Optional[List[UtilityReading]] = None


class DetailedInventoryOut(BaseModel):
    """Schéma de sortie pour un état des lieux détaillé"""
    id: int
    lease_id: int
    conducted_by: int
    apartment_id: int
    
    inventory_type: str
    status: str
    scheduled_date: Optional[datetime]
    conducted_date: Optional[datetime]
    
    tenant_present: bool
    landlord_present: bool
    agent_present: bool
    witness_present: bool
    
    tenant_contact_info: Optional[Dict[str, Any]]
    landlord_contact_info: Optional[Dict[str, Any]]
    agent_contact_info: Optional[Dict[str, Any]]
    witness_contact_info: Optional[Dict[str, Any]]
    
    weather_conditions: Optional[str]
    temperature: Optional[str]
    overall_condition: Optional[str]
    
    general_notes: Optional[str]
    tenant_comments: Optional[str]
    landlord_comments: Optional[str]
    agent_comments: Optional[str]
    
    utilities_data: Optional[List[Dict[str, Any]]]
    
    # Signature
    signature_request_id: Optional[str]
    signature_status: Optional[str]
    signature_url: Optional[str]
    signed_document_url: Optional[str]
    
    # Documents
    pdf_document_path: Optional[str]
    pdf_document_hash: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # Relations
    rooms: List[InventoryRoomOut] = []
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LES PHOTOS ====================

class InventoryPhotoCreate(BaseModel):
    """Schéma pour créer une photo d'inventaire"""
    room_id: Optional[int] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    photo_type: Optional[str] = Field(None, regex="^(overview|detail|defect|comparison)$")
    position_in_room: Optional[str] = None
    angle: Optional[str] = None
    order: int = Field(1, ge=1)


class InventoryPhotoOut(BaseModel):
    """Schéma de sortie pour une photo"""
    id: int
    inventory_id: int
    room_id: Optional[int]
    filename: str
    original_filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    caption: Optional[str]
    description: Optional[str]
    photo_type: Optional[str]
    position_in_room: Optional[str]
    angle: Optional[str]
    taken_at: Optional[datetime]
    uploaded_at: datetime
    order: int
    
    class Config:
        from_attributes = True


class InventoryItemPhotoOut(BaseModel):
    """Schéma de sortie pour une photo d'élément"""
    id: int
    item_id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    caption: Optional[str]
    description: Optional[str]
    photo_type: Optional[str]
    taken_at: Optional[datetime]
    uploaded_at: datetime
    order: int
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LES TEMPLATES ====================

class InventoryTemplateItem(BaseModel):
    """Élément dans un template"""
    name: str
    category: ItemCategoryEnum
    description: Optional[str] = None
    is_mandatory: bool = False
    default_condition: Optional[ItemConditionEnum] = None
    estimated_value: Optional[float] = None


class InventoryTemplateRoom(BaseModel):
    """Pièce dans un template"""
    name: str
    room_type: RoomTypeEnum
    order: int = 1
    standard_items: List[InventoryTemplateItem] = []


class InventoryTemplateCreate(BaseModel):
    """Schéma pour créer un template"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    apartment_id: Optional[int] = None
    is_public: bool = False
    
    rooms: List[InventoryTemplateRoom] = []
    utilities: Optional[List[Dict[str, str]]] = []


class InventoryTemplateOut(BaseModel):
    """Schéma de sortie pour un template"""
    id: int
    created_by: int
    apartment_id: Optional[int]
    name: str
    description: Optional[str]
    is_public: bool
    template_data: Dict[str, Any]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== SCHÉMAS POUR LA SIGNATURE ====================

class SignatureRequestCreate(BaseModel):
    """Schéma pour créer une demande de signature"""
    inventory_id: int
    title: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    expires_in_days: int = Field(30, ge=1, le=365)
    
    # Signataires (déduits automatiquement des participants)
    include_tenant: bool = True
    include_landlord: bool = True
    include_agent: bool = False
    include_witness: bool = False


class SignatureStatusOut(BaseModel):
    """Schéma de sortie pour le statut de signature"""
    inventory_id: int
    signature_request_id: Optional[str]
    status: Optional[str]
    signing_url: Optional[str]
    signed_document_url: Optional[str]
    expires_at: Optional[datetime]
    error_message: Optional[str]


# ==================== SCHÉMAS POUR LES STATISTIQUES ====================

class InventoryStats(BaseModel):
    """Statistiques d'état des lieux"""
    total_inventories: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    pending_signatures: int
    completed_this_month: int
    average_duration_days: Optional[float]


class InventoryComparison(BaseModel):
    """Comparaison entre deux états des lieux"""
    entry_inventory_id: Optional[int]
    exit_inventory_id: Optional[int]
    
    # Changements détectés
    new_items: List[str] = []
    removed_items: List[str] = []
    condition_changes: List[Dict[str, Any]] = []
    
    # Résumé
    total_changes: int
    deterioration_score: Optional[float] = None  # 0-100, 100 = parfait état


# ==================== VALIDATIONS PERSONNALISÉES ====================

class DetailedInventoryCreate(DetailedInventoryCreate):
    """Version étendue avec validations"""
    
    @validator('scheduled_date')
    def validate_scheduled_date(cls, v):
        if v and v < datetime.now():
            raise ValueError('La date planifiée ne peut pas être dans le passé')
        return v
    
    @validator('rooms')
    def validate_rooms_order(cls, v):
        if v:
            orders = [room.order for room in v]
            if len(orders) != len(set(orders)):
                raise ValueError('Les ordres des pièces doivent être uniques')
        return v


class InventoryRoomCreate(InventoryRoomCreate):
    """Version étendue avec validations"""
    
    @validator('area')
    def validate_area(cls, v, values):
        if v and 'length' in values and 'width' in values:
            length = values.get('length')
            width = values.get('width')
            if length and width:
                calculated_area = length * width / 10000  # cm² vers m²
                if abs(v - calculated_area) > 0.1:  # Tolérance de 0.1 m²
                    raise ValueError('La surface ne correspond pas aux dimensions')
        return v


# ==================== SCHÉMAS POUR L'EXPORT ====================

class InventoryExportRequest(BaseModel):
    """Demande d'export d'état des lieux"""
    inventory_id: int
    format: str = Field("pdf", regex="^(pdf|excel|json)$")
    include_photos: bool = True
    include_signatures: bool = True
    language: str = Field("fr", regex="^(fr|en)$")


class InventoryExportResult(BaseModel):
    """Résultat d'export"""
    inventory_id: int
    format: str
    file_url: str
    file_size: int
    expires_at: datetime
    download_count: int = 0