from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime, Text, Numeric, Index, DECIMAL
from sqlalchemy.orm import relationship
from database import Base
import datetime

# Import centralisé des enums
from enums import (
    UserRole, PhotoType, RoomType, ActionType, EntityType,
    SubscriptionType, SubscriptionStatus, PaymentStatus, AuthType,
    FloorPlanType, DocumentType, LeaseStatus, TenantStatus,
    InvitationStatus, InventoryItemCondition, PropertyCondition, InventoryType
)

class UserAuth(Base):
    __tablename__ = "user_auth"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable pour OAuth
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(50), nullable=True)

    # Adresse (Open/Closed Principle - extensible)
    street_number = Column(String(100), nullable=True)
    street_name = Column(String(500), nullable=True)
    complement = Column(String(500), nullable=True)
    postal_code = Column(String(50), nullable=True)
    city = Column(String(200), nullable=True)
    country = Column(String(200), nullable=True)
    
    # OAuth fields (Interface Segregation - séparé des champs classiques)
    auth_type = Column(Enum(AuthType), default=AuthType.EMAIL_PASSWORD)
    oauth_provider_id = Column(String(255), nullable=True)  # ID chez le provider OAuth
    oauth_avatar_url = Column(String(500), nullable=True)   # Photo de profil
    email_verified = Column(Boolean, default=False)        # Email vérifié
    email_verified_at = Column(DateTime, nullable=True)    # Date de vérification
    
    # Relations (Dependency Inversion)
    apartment_links = relationship("ApartmentUserLink", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("UserSubscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    floor_plans = relationship("FloorPlan", back_populates="creator", cascade="all, delete-orphan")
    
    # Relations gestion locative
    leases = relationship("Lease", back_populates="creator", cascade="all, delete-orphan")
    tenant_documents = relationship("TenantDocument", back_populates="uploader", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="conductor", cascade="all, delete-orphan")
    
    # Relations gestion multi-acteurs (système de multipropriété)
    # Ces relations sont définies dynamiquement après import des modèles

class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    street_number = Column(String(20))
    street_name = Column(String(255))
    complement = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))
    floors = Column(Integer)
    is_copro = Column(Boolean)
    user_id = Column(Integer, ForeignKey("user_auth.id"))  # Créateur de l'immeuble
    copro_id = Column(Integer, ForeignKey("copros.id"), nullable=True)

    apartments = relationship("Apartment", back_populates="building")
    photos = relationship("Photo", back_populates="building")
    copro = relationship("Copro", back_populates="buildings")

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    type_logement = Column(String(50))
    layout = Column(String(50))
    floor = Column(Integer, nullable=True)
    building_id = Column(Integer, ForeignKey("buildings.id"))
    
    # Multipropriété - Foreign key ajoutée par migration
    # property_group_id = Column(Integer, ForeignKey("property_groups.id"), nullable=True)

    building = relationship("Building", back_populates="apartments")
    user_links = relationship("ApartmentUserLink", back_populates="apartment")
    photos = relationship("Photo", back_populates="apartment")
    rooms = relationship("Room", back_populates="apartment", cascade="all, delete-orphan")
    floor_plans = relationship("FloorPlan", back_populates="apartment", cascade="all, delete-orphan")
    leases = relationship("Lease", back_populates="apartment", cascade="all, delete-orphan")

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"))
    name = Column(String(100))  # Ex: "Cuisine", "Chambre 1", "Salon"
    room_type = Column(Enum(RoomType))
    area_m2 = Column(DECIMAL(8, 2), nullable=True)  # Surface en m²
    description = Column(Text, nullable=True)
    floor_level = Column(Integer, default=0)  # Étage dans l'appartement (pour duplex)
    sort_order = Column(Integer, default=0)  # Ordre d'affichage
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    apartment = relationship("Apartment", back_populates="rooms")
    photos = relationship("Photo", back_populates="room", cascade="all, delete-orphan")
    floor_plans = relationship("FloorPlan", back_populates="room", cascade="all, delete-orphan")
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        Index('idx_room_apartment', 'apartment_id'),
        Index('idx_room_type', 'room_type'),
        Index('idx_room_sort', 'apartment_id', 'sort_order'),
    )

class ApartmentUserLink(Base):
    __tablename__ = "apartment_user_link"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"))
    apartment_id = Column(Integer, ForeignKey("apartments.id"))
    role = Column(Enum(UserRole))

    user = relationship("UserAuth", back_populates="apartment_links")
    apartment = relationship("Apartment", back_populates="user_links")

class Copro(Base):
    __tablename__ = "copros"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(255))
    adresse_rue = Column(String(255))
    adresse_code_postal = Column(String(20))
    adresse_ville = Column(String(100))
    annee_construction = Column(Integer)
    nb_batiments = Column(Integer)
    nb_lots_total = Column(Integer)
    nb_lots_principaux = Column(Integer)
    nb_lots_secondaires = Column(Integer)
    surface_totale_m2 = Column(Integer)
    type_construction = Column(String(100))
    nb_etages = Column(Integer)
    ascenseur = Column(Boolean)
    nb_ascenseurs = Column(Integer)
    chauffage_collectif_type = Column(String(100))
    chauffage_individuel_type = Column(String(100))
    clim_centralisee = Column(Boolean)
    eau_chaude_collective = Column(Boolean)
    isolation_thermique = Column(String(255))
    isolation_annee = Column(Integer)
    rt2012_re2020 = Column(Boolean)
    accessibilite_pmr = Column(Boolean)
    toiture_type = Column(String(100))
    toiture_materiaux = Column(String(100))
    gardien = Column(Boolean)
    local_velos = Column(Boolean)
    parkings_ext = Column(Boolean)
    nb_parkings_ext = Column(Integer)
    parkings_int = Column(Boolean)
    nb_parkings_int = Column(Integer)
    caves = Column(Boolean)
    nb_caves = Column(Integer)
    espaces_verts = Column(Boolean)
    jardins_partages = Column(Boolean)
    piscine = Column(Boolean)
    salle_sport = Column(Boolean)
    aire_jeux = Column(Boolean)
    salle_reunion = Column(Boolean)
    dpe_collectif = Column(String(1))  # A-G
    audit_energetique = Column(Boolean)
    audit_energetique_date = Column(String(20))
    energie_utilisee = Column(String(100))
    panneaux_solaires = Column(Boolean)
    bornes_recharge = Column(Boolean)

    # Relations
    buildings = relationship("Building", back_populates="copro")
    syndicat = relationship("SyndicatCopro", uselist=False, back_populates="copro")

class SyndicatCopro(Base):
    __tablename__ = "syndicats_copro"

    id = Column(Integer, primary_key=True, index=True)
    copro_id = Column(Integer, ForeignKey("copros.id"))
    user_id = Column(Integer, ForeignKey("user_auth.id"))  # Créateur du syndicat
    statut_juridique = Column(String(100))
    date_creation = Column(String(20))
    reglement_copro = Column(Boolean)
    carnet_entretien = Column(Boolean)
    nom_syndic = Column(String(255))
    type_syndic = Column(String(50))
    societe_syndic = Column(String(255))
    date_derniere_ag = Column(String(20))
    assurance_compagnie = Column(String(255))
    assurance_num_police = Column(String(100))
    assurance_validite = Column(String(20))
    procedures_judiciaires = Column(Boolean)
    procedures_details = Column(String(255))
    budget_annuel_previsionnel = Column(Integer)
    charges_annuelles_par_lot = Column(Integer)
    charges_speciales = Column(Integer)
    emprunt_collectif = Column(Boolean)
    emprunt_montant = Column(Integer)
    emprunt_echeance = Column(String(20))
    taux_impayes_charges = Column(Integer)
    fonds_roulement = Column(Integer)
    fonds_travaux = Column(Integer)
    travaux_votes = Column(String(1000))
    travaux_en_cours = Column(String(1000))

    copro = relationship("Copro", back_populates="syndicat")
    user = relationship("UserAuth")  # Créateur

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    original_filename = Column(String(255), nullable=True)  # Nom original du fichier
    type = Column(Enum(PhotoType))
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Métadonnées de l'image
    file_size = Column(Integer, nullable=True)  # Taille en bytes
    width = Column(Integer, nullable=True)      # Largeur en pixels
    height = Column(Integer, nullable=True)     # Hauteur en pixels
    mime_type = Column(String(100), nullable=True)  # image/jpeg, image/png, etc.
    
    # Organisation et affichage
    is_main = Column(Boolean, default=False)   # Photo principale
    sort_order = Column(Integer, default=0)    # Ordre d'affichage
    
    # Métadonnées JSON pour données supplémentaires
    photo_metadata = Column(Text, nullable=True)     # JSON: géolocalisation, EXIF, etc.
    
    # Dates
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relations
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)

    building = relationship("Building", back_populates="photos")
    apartment = relationship("Apartment", back_populates="photos")
    room = relationship("Room", back_populates="photos")
    inventories = relationship("Inventory", secondary="inventory_photos", back_populates="photos")
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        Index('idx_photo_building', 'building_id'),
        Index('idx_photo_apartment', 'apartment_id'),
        Index('idx_photo_room', 'room_id'),
        Index('idx_photo_type', 'type'),
        Index('idx_photo_main', 'is_main'),
        Index('idx_photo_sort', 'type', 'sort_order'),
    )

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"))
    session_id = Column(String(255), unique=True, index=True)  # UUID unique pour cette session
    refresh_token = Column(Text)  # Token de rafraîchissement
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)  # Expiration du refresh token (30 jours)
    user_agent = Column(String(500), nullable=True)  # Navigateur/device info
    ip_address = Column(String(50), nullable=True)  # Adresse IP
    is_active = Column(Boolean, default=True)
    
    user = relationship("UserAuth", back_populates="user_sessions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"), nullable=True)  # Peut être null pour les actions anonymes
    action = Column(Enum(ActionType))  # Type d'action effectuée
    entity_type = Column(Enum(EntityType))  # Type d'entité concernée
    entity_id = Column(Integer, nullable=True)  # ID de l'entité concernée
    description = Column(String(500))  # Description de l'action
    details = Column(Text, nullable=True)  # Détails JSON de l'action (données avant/après)
    ip_address = Column(String(50), nullable=True)  # Adresse IP
    user_agent = Column(String(500), nullable=True)  # Navigateur/device
    endpoint = Column(String(200), nullable=True)  # Endpoint API appelé
    method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    status_code = Column(Integer, nullable=True)  # Code de réponse HTTP
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relation avec l'utilisateur
    user = relationship("UserAuth")

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"), unique=True)  # Un seul abonnement par utilisateur
    subscription_type = Column(Enum(SubscriptionType), default=SubscriptionType.FREE)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    
    # Stripe fields
    stripe_customer_id = Column(String(255), nullable=True, index=True)  # ID client Stripe
    stripe_subscription_id = Column(String(255), nullable=True, index=True)  # ID abonnement Stripe
    stripe_price_id = Column(String(255), nullable=True)  # ID du prix Stripe
    
    # Dates importantes
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    current_period_start = Column(DateTime, nullable=True)  # Début de la période actuelle
    current_period_end = Column(DateTime, nullable=True)    # Fin de la période actuelle
    trial_end = Column(DateTime, nullable=True)             # Fin d'essai gratuit
    cancel_at = Column(DateTime, nullable=True)             # Date d'annulation programmée
    cancelled_at = Column(DateTime, nullable=True)          # Date d'annulation effective
    
    # Métadonnées
    apartment_limit = Column(Integer, default=3)           # Limite d'appartements (3 pour FREE, -1 pour illimité)
    subscription_metadata = Column(Text, nullable=True)                 # JSON pour données supplémentaires
    
    # Relations
    user = relationship("UserAuth", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        Index('idx_user_subscription_status', 'user_id', 'status'),
        Index('idx_stripe_customer', 'stripe_customer_id'),
        Index('idx_stripe_subscription', 'stripe_subscription_id'),
    )

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"))
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True)
    
    # Stripe fields
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)  # ID PaymentIntent Stripe
    stripe_invoice_id = Column(String(255), nullable=True, index=True)       # ID facture Stripe
    stripe_charge_id = Column(String(255), nullable=True, index=True)        # ID charge Stripe
    
    # Détails du paiement
    amount = Column(Numeric(10, 2))                        # Montant en euros (ex: 9.99)
    currency = Column(String(3), default="EUR")           # Devise
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Métadonnées
    description = Column(String(500), nullable=True)      # Description du paiement
    failure_reason = Column(String(500), nullable=True)   # Raison d'échec si applicable
    receipt_url = Column(String(500), nullable=True)      # URL du reçu Stripe
    
    # Dates
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)             # Date de paiement réussi
    
    # Données JSON pour webhook Stripe
    stripe_event_data = Column(Text, nullable=True)       # Données complètes de l'événement Stripe
    
    # Relations
    user = relationship("UserAuth", back_populates="payments")
    subscription = relationship("UserSubscription", back_populates="payments")
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        Index('idx_payment_user_status', 'user_id', 'status'),
        Index('idx_payment_stripe_intent', 'stripe_payment_intent_id'),
        Index('idx_payment_created_at', 'created_at'),
    )

# Les enums sont maintenant dans enums.py

class FloorPlan(Base):
    __tablename__ = "floor_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(FloorPlanType), nullable=False)
    
    # Relations
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Données du plan
    xml_data = Column(Text, nullable=True)  # Structure XML du plan
    scale = Column(Numeric(5, 2), default=1.0)  # Échelle du plan
    grid_size = Column(Integer, default=20)  # Taille de la grille en pixels
    
    # Métadonnées
    thumbnail_url = Column(String(500), nullable=True)  # URL de la miniature
    
    # Dates
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    room = relationship("Room", back_populates="floor_plans")
    apartment = relationship("Apartment", back_populates="floor_plans")
    creator = relationship("UserAuth", back_populates="floor_plans")
    
    # Index pour optimiser les requêtes
    __table_args__ = (
        Index('idx_floor_plan_room', 'room_id'),
        Index('idx_floor_plan_apartment', 'apartment_id'),
        Index('idx_floor_plan_creator', 'created_by'),
        Index('idx_floor_plan_type', 'type'),
        Index('idx_floor_plan_updated', 'updated_at'),
    )

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Informations personnelles
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    
    # Adresse précédente (optionnel)
    previous_address = Column(Text, nullable=True)
    
    # Informations professionnelles
    occupation = Column(String(200), nullable=True)
    employer = Column(String(200), nullable=True)
    monthly_income = Column(Numeric(10, 2), nullable=True)
    
    # Contact d'urgence
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    emergency_contact_relation = Column(String(100), nullable=True)
    
    # Métadonnées
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    leases = relationship("Lease", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("TenantDocument", back_populates="tenant", cascade="all, delete-orphan")
    
    # Index
    __table_args__ = (
        Index('idx_tenant_email', 'email'),
        Index('idx_tenant_name', 'last_name', 'first_name'),
    )

class Lease(Base):
    __tablename__ = "leases"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)  # Propriétaire/gestionnaire
    
    # Informations du bail
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    monthly_rent = Column(Numeric(10, 2), nullable=False)
    charges = Column(Numeric(10, 2), default=0.00)  # Charges mensuelles
    deposit = Column(Numeric(10, 2), nullable=False)  # Dépôt de garantie
    
    # Statut et conditions
    status = Column(Enum(LeaseStatus), default=LeaseStatus.PENDING)
    renewable = Column(Boolean, default=True)
    furnished = Column(Boolean, default=False)
    
    # Informations légales
    lease_type = Column(String(50), default="RESIDENTIAL")  # RESIDENTIAL, COMMERCIAL, etc.
    notice_period_days = Column(Integer, default=30)  # Préavis en jours
    
    # Adresse de facturation (si différente)
    billing_address = Column(Text, nullable=True)
    
    # Métadonnées
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    tenant = relationship("Tenant", back_populates="leases")
    apartment = relationship("Apartment", back_populates="leases")
    creator = relationship("UserAuth", back_populates="leases")
    documents = relationship("TenantDocument", back_populates="lease", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="lease", cascade="all, delete-orphan")
    
    # Index
    __table_args__ = (
        Index('idx_lease_tenant', 'tenant_id'),
        Index('idx_lease_apartment', 'apartment_id'),
        Index('idx_lease_status', 'status'),
        Index('idx_lease_dates', 'start_date', 'end_date'),
    )

class TenantDocument(Base):
    __tablename__ = "tenant_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=True)  # Peut être lié à un bail spécifique
    uploaded_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Informations du document
    document_type = Column(Enum(DocumentType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Fichier
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Dates importantes
    document_date = Column(DateTime, nullable=True)  # Date du document
    expiry_date = Column(DateTime, nullable=True)    # Date d'expiration si applicable
    
    # Métadonnées
    is_verified = Column(Boolean, default=False)     # Document vérifié
    verification_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    tenant = relationship("Tenant", back_populates="documents")
    lease = relationship("Lease", back_populates="documents")
    uploader = relationship("UserAuth", back_populates="tenant_documents")
    
    # Index
    __table_args__ = (
        Index('idx_document_tenant', 'tenant_id'),
        Index('idx_document_lease', 'lease_id'),
        Index('idx_document_type', 'document_type'),
        Index('idx_document_expiry', 'expiry_date'),
    )

class Inventory(Base):
    __tablename__ = "inventories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=False)
    conducted_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)
    
    # Type et informations
    inventory_type = Column(Enum(InventoryType), nullable=False)
    conducted_date = Column(DateTime, nullable=False)
    
    # Participants
    tenant_present = Column(Boolean, default=True)
    landlord_present = Column(Boolean, default=True)
    agent_present = Column(Boolean, default=False)
    
    # Données de l'état des lieux (JSON)
    rooms_data = Column(Text, nullable=True)  # JSON des pièces et leurs états
    overall_condition = Column(String(50), nullable=True)  # EXCELLENT, GOOD, FAIR, POOR
    
    # Observations générales
    general_notes = Column(Text, nullable=True)
    tenant_comments = Column(Text, nullable=True)
    landlord_comments = Column(Text, nullable=True)
    
    # Signatures (base64 ou références fichiers)
    tenant_signature = Column(Text, nullable=True)
    landlord_signature = Column(Text, nullable=True)
    agent_signature = Column(Text, nullable=True)
    
    # Métadonnées
    is_finalized = Column(Boolean, default=False)  # État des lieux finalisé
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    lease = relationship("Lease", back_populates="inventories")
    conductor = relationship("UserAuth", back_populates="inventories")
    photos = relationship("Photo", secondary="inventory_photos", back_populates="inventories")
    
    # Index
    __table_args__ = (
        Index('idx_inventory_lease', 'lease_id'),
        Index('idx_inventory_type', 'inventory_type'),
        Index('idx_inventory_date', 'conducted_date'),
    )

# Table de liaison pour les photos d'état des lieux
class InventoryPhoto(Base):
    __tablename__ = "inventory_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventories.id"), nullable=False)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False)
    room_name = Column(String(100), nullable=True)  # Pièce concernée
    description = Column(String(255), nullable=True)  # Description de la photo
    
    # Index
    __table_args__ = (
        Index('idx_inventory_photo_inventory', 'inventory_id'),
        Index('idx_inventory_photo_photo', 'photo_id'),
    )

class TenantInvitation(Base):
    """Modèle pour les invitations de locataires"""
    __tablename__ = "tenant_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    invited_by = Column(Integer, ForeignKey("user_auth.id"), nullable=False)  # ID de l'utilisateur qui invite
    
    # Token d'invitation
    invitation_token = Column(String(255), unique=True, nullable=False, index=True)
    token_expires_at = Column(DateTime, nullable=False)
    
    # État de l'invitation
    is_sent = Column(Boolean, default=False)
    is_used = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    used_at = Column(DateTime, nullable=True)
    
    # Informations d'envoi
    email_sent_to = Column(String(255), nullable=True)
    email_message_id = Column(String(255), nullable=True)
    
    # Métadonnées
    invitation_data = Column(Text, nullable=True)  # JSON avec infos additionnelles
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    tenant = relationship("Tenant", backref="invitations")
    inviter = relationship("UserAuth", foreign_keys=[invited_by])
    
    # Index
    __table_args__ = (
        Index('idx_invitation_token', 'invitation_token'),
        Index('idx_invitation_tenant', 'tenant_id'),
        Index('idx_invitation_expires', 'token_expires_at'),
        Index('idx_invitation_status', 'is_used', 'is_sent'),
    )