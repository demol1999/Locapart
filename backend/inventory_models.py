"""
Modèles étendus pour les états des lieux détaillés
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Numeric, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class InventoryStatus(str, Enum):
    """Statuts d'un état des lieux"""
    DRAFT = "DRAFT"                    # En cours de création
    IN_PROGRESS = "IN_PROGRESS"        # En cours de réalisation
    PENDING_SIGNATURE = "PENDING_SIGNATURE"  # En attente de signature
    SIGNED = "SIGNED"                  # Signé par toutes les parties
    COMPLETED = "COMPLETED"            # Finalisé et archivé
    CANCELLED = "CANCELLED"            # Annulé


class RoomType(str, Enum):
    """Types de pièces étendus"""
    KITCHEN = "KITCHEN"                # Cuisine
    LIVING_ROOM = "LIVING_ROOM"        # Salon
    DINING_ROOM = "DINING_ROOM"        # Salle à manger
    BEDROOM = "BEDROOM"                # Chambre
    BATHROOM = "BATHROOM"              # Salle de bain
    TOILET = "TOILET"                  # WC
    ENTRANCE = "ENTRANCE"              # Entrée
    HALLWAY = "HALLWAY"                # Couloir
    BALCONY = "BALCONY"                # Balcon
    TERRACE = "TERRACE"                # Terrasse
    GARAGE = "GARAGE"                  # Garage
    CELLAR = "CELLAR"                  # Cave
    STORAGE = "STORAGE"                # Débarras
    OFFICE = "OFFICE"                  # Bureau
    LAUNDRY = "LAUNDRY"                # Buanderie
    COMMON_AREA = "COMMON_AREA"        # Partie commune
    OTHER = "OTHER"                    # Autre


class ItemCondition(str, Enum):
    """États des éléments"""
    EXCELLENT = "EXCELLENT"            # Excellent
    GOOD = "GOOD"                      # Bon
    FAIR = "FAIR"                      # Moyen
    POOR = "POOR"                      # Mauvais
    DAMAGED = "DAMAGED"                # Endommagé
    MISSING = "MISSING"                # Manquant
    NEW = "NEW"                        # Neuf
    TO_REPLACE = "TO_REPLACE"          # À remplacer


class ItemCategory(str, Enum):
    """Catégories d'éléments"""
    WALL = "WALL"                      # Mur
    FLOOR = "FLOOR"                    # Sol
    CEILING = "CEILING"                # Plafond
    WINDOW = "WINDOW"                  # Fenêtre
    DOOR = "DOOR"                      # Porte
    FIXTURE = "FIXTURE"                # Équipement fixe
    FURNITURE = "FURNITURE"            # Mobilier
    APPLIANCE = "APPLIANCE"            # Électroménager
    LIGHTING = "LIGHTING"              # Éclairage
    PLUMBING = "PLUMBING"              # Plomberie
    ELECTRICAL = "ELECTRICAL"          # Électricité
    HEATING = "HEATING"                # Chauffage
    OTHER = "OTHER"                    # Autre


class DetailedInventory(Base):
    """État des lieux détaillé avec workflow complet"""
    __tablename__ = "detailed_inventories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=False)
    conducted_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    
    # Informations générales
    inventory_type = Column(String(20), nullable=False)  # "ENTRY", "EXIT", "PERIODIC"
    status = Column(String(20), default=InventoryStatus.DRAFT)
    scheduled_date = Column(DateTime, nullable=True)      # Date prévue
    conducted_date = Column(DateTime, nullable=True)      # Date réelle
    
    # Participants
    tenant_present = Column(Boolean, default=True)
    landlord_present = Column(Boolean, default=True)
    agent_present = Column(Boolean, default=False)
    witness_present = Column(Boolean, default=False)
    
    # Informations de contact des participants
    tenant_contact_info = Column(JSON, nullable=True)     # Nom, téléphone, etc.
    landlord_contact_info = Column(JSON, nullable=True)
    agent_contact_info = Column(JSON, nullable=True)
    witness_contact_info = Column(JSON, nullable=True)
    
    # Conditions générales
    weather_conditions = Column(String(100), nullable=True)
    temperature = Column(String(50), nullable=True)
    overall_condition = Column(String(20), nullable=True)
    
    # Observations générales
    general_notes = Column(Text, nullable=True)
    tenant_comments = Column(Text, nullable=True)
    landlord_comments = Column(Text, nullable=True)
    agent_comments = Column(Text, nullable=True)
    
    # Données détaillées (JSON pour flexibilité)
    rooms_data = Column(JSON, nullable=True)              # Structure des pièces
    utilities_data = Column(JSON, nullable=True)          # Compteurs, etc.
    
    # Workflow de signature
    signature_request_id = Column(String(255), nullable=True)  # ID de la demande de signature
    signature_status = Column(String(50), nullable=True)       # Statut de la signature
    signature_url = Column(String(500), nullable=True)         # URL de signature
    signed_document_url = Column(String(500), nullable=True)   # URL du document signé
    
    # Documents générés
    pdf_document_path = Column(String(500), nullable=True)     # Chemin du PDF généré
    pdf_document_hash = Column(String(64), nullable=True)      # Hash du PDF pour intégrité
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)             # Date de finalisation
    
    # Relations
    lease = relationship("Lease", backref="detailed_inventories")
    conductor = relationship("UserAuth", foreign_keys=[conducted_by])
    apartment = relationship("Apartment", backref="detailed_inventories")
    rooms = relationship("InventoryRoom", back_populates="inventory", cascade="all, delete-orphan")
    photos = relationship("DetailedInventoryPhoto", back_populates="inventory", cascade="all, delete-orphan")


class InventoryRoom(Base):
    """Pièce dans un état des lieux détaillé"""
    __tablename__ = "inventory_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("detailed_inventories.id"), nullable=False)
    
    # Informations de la pièce
    name = Column(String(100), nullable=False)            # Nom de la pièce
    room_type = Column(String(20), nullable=False)        # Type de pièce
    order = Column(Integer, default=1)                    # Ordre de visite
    
    # Dimensions
    length = Column(Numeric(5, 2), nullable=True)         # Longueur en mètres
    width = Column(Numeric(5, 2), nullable=True)          # Largeur en mètres
    height = Column(Numeric(5, 2), nullable=True)         # Hauteur en mètres
    area = Column(Numeric(7, 2), nullable=True)           # Surface en m²
    
    # État général
    overall_condition = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Données spécifiques (JSON pour flexibilité)
    room_data = Column(JSON, nullable=True)               # Configuration spécifique
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    inventory = relationship("DetailedInventory", back_populates="rooms")
    items = relationship("InventoryItem", back_populates="room", cascade="all, delete-orphan")


class InventoryItem(Base):
    """Élément/équipement dans une pièce"""
    __tablename__ = "inventory_items"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("inventory_rooms.id"), nullable=False)
    
    # Informations de l'élément
    name = Column(String(100), nullable=False)            # Nom de l'élément
    category = Column(String(20), nullable=False)         # Catégorie
    description = Column(Text, nullable=True)             # Description détaillée
    
    # État et condition
    condition = Column(String(20), nullable=False)        # État actuel
    previous_condition = Column(String(20), nullable=True) # État précédent (pour comparaison)
    
    # Caractéristiques
    brand = Column(String(100), nullable=True)            # Marque
    model = Column(String(100), nullable=True)            # Modèle
    serial_number = Column(String(100), nullable=True)    # Numéro de série
    purchase_date = Column(DateTime, nullable=True)       # Date d'achat
    warranty_until = Column(DateTime, nullable=True)      # Garantie jusqu'à
    
    # Valeur
    estimated_value = Column(Numeric(10, 2), nullable=True)  # Valeur estimée
    replacement_cost = Column(Numeric(10, 2), nullable=True) # Coût de remplacement
    
    # Position dans la pièce
    position_x = Column(Numeric(5, 2), nullable=True)     # Position X dans la pièce
    position_y = Column(Numeric(5, 2), nullable=True)     # Position Y dans la pièce
    
    # Mesures
    dimensions = Column(JSON, nullable=True)              # Dimensions (L x l x h)
    weight = Column(Numeric(7, 2), nullable=True)         # Poids en kg
    
    # Observations
    notes = Column(Text, nullable=True)                   # Notes spécifiques
    defects = Column(JSON, nullable=True)                 # Liste des défauts
    improvements = Column(JSON, nullable=True)            # Améliorations apportées
    
    # Données étendues (JSON pour flexibilité)
    item_data = Column(JSON, nullable=True)               # Données spécifiques au type
    
    # Métadonnées
    order = Column(Integer, default=1)                    # Ordre dans la pièce
    is_mandatory = Column(Boolean, default=False)         # Élément obligatoire à vérifier
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    room = relationship("InventoryRoom", back_populates="items")
    photos = relationship("InventoryItemPhoto", back_populates="item", cascade="all, delete-orphan")


class DetailedInventoryPhoto(Base):
    """Photo associée à un état des lieux détaillé"""
    __tablename__ = "detailed_inventory_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("detailed_inventories.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("inventory_rooms.id"), nullable=True)
    
    # Informations de la photo
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Métadonnées de la photo
    caption = Column(String(255), nullable=True)          # Légende
    description = Column(Text, nullable=True)             # Description
    photo_type = Column(String(50), nullable=True)        # Type de photo (overview, detail, defect)
    
    # Position et angle
    position_in_room = Column(String(100), nullable=True) # Position dans la pièce
    angle = Column(String(50), nullable=True)             # Angle de prise de vue
    
    # Données EXIF
    exif_data = Column(JSON, nullable=True)               # Données EXIF de l'image
    gps_coordinates = Column(JSON, nullable=True)         # Coordonnées GPS si disponibles
    
    # Métadonnées
    taken_at = Column(DateTime, nullable=True)            # Date de prise de vue
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    order = Column(Integer, default=1)                    # Ordre d'affichage
    
    # Relations
    inventory = relationship("DetailedInventory", back_populates="photos")
    room = relationship("InventoryRoom")


class InventoryItemPhoto(Base):
    """Photo spécifique à un élément"""
    __tablename__ = "inventory_item_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    
    # Informations de la photo
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Métadonnées
    caption = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    photo_type = Column(String(50), nullable=True)        # before, after, defect, detail
    
    # Métadonnées
    taken_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    order = Column(Integer, default=1)
    
    # Relations
    item = relationship("InventoryItem", back_populates="photos")


class InventoryTemplate(Base):
    """Template d'état des lieux réutilisable"""
    __tablename__ = "inventory_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)  # Spécifique à un appartement ou général
    
    # Informations du template
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)            # Accessible à tous les utilisateurs
    
    # Structure du template (JSON)
    template_data = Column(JSON, nullable=False)          # Structure des pièces et éléments
    
    # Statistiques d'utilisation
    usage_count = Column(Integer, default=0)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    creator = relationship("UserAuth")
    apartment = relationship("Apartment")


class InventorySignature(Base):
    """Signatures associées à un état des lieux"""
    __tablename__ = "inventory_signatures"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("detailed_inventories.id"), nullable=False)
    
    # Informations du signataire
    signer_name = Column(String(200), nullable=False)
    signer_email = Column(String(255), nullable=False)
    signer_role = Column(String(50), nullable=False)      # tenant, landlord, agent, witness
    
    # Données de signature
    signature_data = Column(Text, nullable=True)          # Signature au format base64 ou référence
    signature_method = Column(String(50), nullable=True)  # electronic, manual, biometric
    signature_ip = Column(String(45), nullable=True)      # Adresse IP du signataire
    signature_device = Column(String(200), nullable=True) # Informations sur l'appareil
    
    # Validation
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(100), nullable=True)
    verification_method = Column(String(50), nullable=True) # sms, email, call
    
    # Métadonnées
    signed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relations
    inventory = relationship("DetailedInventory")


# Fonctions utilitaires pour les templates

def create_standard_apartment_template() -> Dict[str, Any]:
    """Crée un template standard pour un appartement"""
    
    return {
        "name": "Appartement standard",
        "description": "Template standard pour un appartement avec pièces principales",
        "rooms": [
            {
                "name": "Entrée",
                "room_type": "ENTRANCE",
                "order": 1,
                "standard_items": [
                    {"name": "Porte d'entrée", "category": "DOOR", "is_mandatory": True},
                    {"name": "Sol", "category": "FLOOR", "is_mandatory": True},
                    {"name": "Murs", "category": "WALL", "is_mandatory": True},
                    {"name": "Plafond", "category": "CEILING", "is_mandatory": True},
                    {"name": "Éclairage", "category": "LIGHTING", "is_mandatory": True},
                    {"name": "Interphone", "category": "ELECTRICAL", "is_mandatory": False}
                ]
            },
            {
                "name": "Salon",
                "room_type": "LIVING_ROOM",
                "order": 2,
                "standard_items": [
                    {"name": "Sol", "category": "FLOOR", "is_mandatory": True},
                    {"name": "Murs", "category": "WALL", "is_mandatory": True},
                    {"name": "Plafond", "category": "CEILING", "is_mandatory": True},
                    {"name": "Fenêtres", "category": "WINDOW", "is_mandatory": True},
                    {"name": "Éclairage central", "category": "LIGHTING", "is_mandatory": True},
                    {"name": "Prises électriques", "category": "ELECTRICAL", "is_mandatory": True},
                    {"name": "Radiateur", "category": "HEATING", "is_mandatory": False}
                ]
            },
            {
                "name": "Cuisine",
                "room_type": "KITCHEN",
                "order": 3,
                "standard_items": [
                    {"name": "Sol", "category": "FLOOR", "is_mandatory": True},
                    {"name": "Murs", "category": "WALL", "is_mandatory": True},
                    {"name": "Plan de travail", "category": "FIXTURE", "is_mandatory": True},
                    {"name": "Évier", "category": "PLUMBING", "is_mandatory": True},
                    {"name": "Robinetterie", "category": "PLUMBING", "is_mandatory": True},
                    {"name": "Plaques de cuisson", "category": "APPLIANCE", "is_mandatory": False},
                    {"name": "Four", "category": "APPLIANCE", "is_mandatory": False},
                    {"name": "Réfrigérateur", "category": "APPLIANCE", "is_mandatory": False},
                    {"name": "Hotte", "category": "APPLIANCE", "is_mandatory": False}
                ]
            },
            {
                "name": "Chambre",
                "room_type": "BEDROOM",
                "order": 4,
                "standard_items": [
                    {"name": "Sol", "category": "FLOOR", "is_mandatory": True},
                    {"name": "Murs", "category": "WALL", "is_mandatory": True},
                    {"name": "Plafond", "category": "CEILING", "is_mandatory": True},
                    {"name": "Fenêtre", "category": "WINDOW", "is_mandatory": True},
                    {"name": "Éclairage", "category": "LIGHTING", "is_mandatory": True},
                    {"name": "Prises électriques", "category": "ELECTRICAL", "is_mandatory": True},
                    {"name": "Placards", "category": "FIXTURE", "is_mandatory": False}
                ]
            },
            {
                "name": "Salle de bain",
                "room_type": "BATHROOM",
                "order": 5,
                "standard_items": [
                    {"name": "Sol", "category": "FLOOR", "is_mandatory": True},
                    {"name": "Murs", "category": "WALL", "is_mandatory": True},
                    {"name": "Baignoire/Douche", "category": "PLUMBING", "is_mandatory": True},
                    {"name": "Lavabo", "category": "PLUMBING", "is_mandatory": True},
                    {"name": "Robinetterie", "category": "PLUMBING", "is_mandatory": True},
                    {"name": "Miroir", "category": "FIXTURE", "is_mandatory": False},
                    {"name": "Éclairage", "category": "LIGHTING", "is_mandatory": True},
                    {"name": "Aération", "category": "OTHER", "is_mandatory": True}
                ]
            }
        ],
        "utilities": [
            {"name": "Compteur électrique", "type": "electricity"},
            {"name": "Compteur gaz", "type": "gas"},
            {"name": "Compteur eau froide", "type": "water_cold"},
            {"name": "Compteur eau chaude", "type": "water_hot"}
        ]
    }


def create_house_template() -> Dict[str, Any]:
    """Crée un template pour une maison"""
    
    apartment_template = create_standard_apartment_template()
    
    # Ajouter des pièces spécifiques à une maison
    house_specific_rooms = [
        {
            "name": "Garage",
            "room_type": "GARAGE",
            "order": 10,
            "standard_items": [
                {"name": "Porte de garage", "category": "DOOR", "is_mandatory": True},
                {"name": "Sol", "category": "FLOOR", "is_mandatory": True},
                {"name": "Éclairage", "category": "LIGHTING", "is_mandatory": True}
            ]
        },
        {
            "name": "Jardin",
            "room_type": "OTHER",
            "order": 11,
            "standard_items": [
                {"name": "Clôture", "category": "OTHER", "is_mandatory": False},
                {"name": "Portail", "category": "OTHER", "is_mandatory": False},
                {"name": "Pelouse", "category": "OTHER", "is_mandatory": False}
            ]
        }
    ]
    
    apartment_template["rooms"].extend(house_specific_rooms)
    apartment_template["name"] = "Maison standard"
    apartment_template["description"] = "Template standard pour une maison individuelle"
    
    return apartment_template