"""
Enums partagés pour l'application LocAppart
Centralisation de toutes les énumérations pour éviter la duplication
"""
import enum


class UserRole(str, enum.Enum):
    """Rôles des utilisateurs pour un appartement"""
    owner = "owner"
    gestionnaire = "gestionnaire"
    lecteur = "lecteur"


class PhotoType(str, enum.Enum):
    """Types de photos dans l'application"""
    building = "building"
    apartment = "apartment"
    room = "room"


class RoomType(str, enum.Enum):
    """Types de pièces dans un appartement"""
    kitchen = "kitchen"          # Cuisine
    bedroom = "bedroom"          # Chambre
    living_room = "living_room"  # Salon
    bathroom = "bathroom"        # Salle de bain
    office = "office"           # Bureau
    storage = "storage"         # Rangement/placard
    balcony = "balcony"         # Balcon/terrasse
    dining_room = "dining_room" # Salle à manger
    entrance = "entrance"       # Entrée/hall
    toilet = "toilet"           # WC séparé
    laundry = "laundry"         # Buanderie
    cellar = "cellar"           # Cave
    garage = "garage"           # Garage
    other = "other"             # Autre


class ActionType(str, enum.Enum):
    """Types d'actions pour l'audit logging"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REFRESH_TOKEN = "REFRESH_TOKEN"
    ACCESS_DENIED = "ACCESS_DENIED"
    ERROR = "ERROR"


class EntityType(str, enum.Enum):
    """Types d'entités dans l'application"""
    USER = "USER"
    BUILDING = "BUILDING"
    APARTMENT = "APARTMENT"
    COPRO = "COPRO"
    SYNDICAT_COPRO = "SYNDICAT_COPRO"
    PHOTO = "PHOTO"
    SESSION = "SESSION"
    SUBSCRIPTION = "SUBSCRIPTION"
    PAYMENT = "PAYMENT"
    TENANT = "TENANT"
    LEASE = "LEASE"
    DOCUMENT = "DOCUMENT"
    INVENTORY = "INVENTORY"
    TENANT_INVITATION = "TENANT_INVITATION"


class SubscriptionType(str, enum.Enum):
    """Types d'abonnements"""
    FREE = "FREE"           # Gratuit: 3 appartements max
    PREMIUM = "PREMIUM"     # Premium: illimité


class SubscriptionStatus(str, enum.Enum):
    """Statuts d'abonnement"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CANCELLED = "CANCELLED"
    PAST_DUE = "PAST_DUE"


class PaymentStatus(str, enum.Enum):
    """Statuts de paiement"""
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class AuthType(str, enum.Enum):
    """Types d'authentification"""
    EMAIL_PASSWORD = "EMAIL_PASSWORD"
    GOOGLE_OAUTH = "GOOGLE_OAUTH"
    FACEBOOK_OAUTH = "FACEBOOK_OAUTH"
    MICROSOFT_OAUTH = "MICROSOFT_OAUTH"


class AdminRole(str, enum.Enum):
    """Rôles administrateur"""
    SUPER_ADMIN = "super_admin"        # Accès complet
    USER_MANAGER = "user_manager"      # Gestion des utilisateurs
    SUPPORT = "support"                # Support client
    MODERATOR = "moderator"            # Modération de contenu
    VIEWER = "viewer"                  # Lecture seule


class UserStatus(str, enum.Enum):
    """Statuts des utilisateurs"""
    ACTIVE = "active"                  # Actif
    INACTIVE = "inactive"              # Inactif
    SUSPENDED = "suspended"            # Suspendu
    BANNED = "banned"                  # Banni
    PENDING_VERIFICATION = "pending_verification"  # En attente de vérification


class AccountAction(str, enum.Enum):
    """Actions administratives sur les comptes"""
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    BAN = "ban"
    UNBAN = "unban"
    RESET_PASSWORD = "reset_password"
    FORCE_EMAIL_VERIFICATION = "force_email_verification"
    UPGRADE_TO_PREMIUM = "upgrade_to_premium"
    DOWNGRADE_TO_FREE = "downgrade_to_free"


class FloorPlanType(str, enum.Enum):
    """Types de plans d'étage"""
    FLOOR_PLAN = "floor_plan"
    ROOM_LAYOUT = "room_layout"
    TECHNICAL_PLAN = "technical_plan"


class DocumentType(str, enum.Enum):
    """Types de documents"""
    CONTRACT = "contract"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    INVENTORY = "inventory"
    INSURANCE = "insurance"
    OTHER = "other"


class LeaseStatus(str, enum.Enum):
    """Statuts de bail"""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class TenantStatus(str, enum.Enum):
    """Statuts de locataire"""
    ACTIVE = "active"
    FORMER = "former"
    PENDING = "pending"


class InvitationStatus(str, enum.Enum):
    """Statuts d'invitation locataire"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InventoryItemCondition(str, enum.Enum):
    """Conditions d'éléments d'inventaire"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"


class PropertyCondition(str, enum.Enum):
    """Conditions générales de propriété"""
    NEW = "new"
    RENOVATED = "renovated"
    GOOD = "good"
    TO_RENOVATE = "to_renovate"
    POOR = "poor"


class InventoryType(str, enum.Enum):
    """Types d'états des lieux"""
    ENTRY = "ENTRY"         # État des lieux d'entrée
    EXIT = "EXIT"           # État des lieux de sortie
    PERIODIC = "PERIODIC"   # État des lieux périodique