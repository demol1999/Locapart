"""
Constantes centralisées pour l'application LocAppart
Standardisation des valeurs et conventions utilisées dans l'application
"""

# ==================== CONFIGURATION GÉNÉRALE ====================

APP_NAME = "LocAppart"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Système de gestion locative"

# ==================== CONFIGURATION DE SÉCURITÉ ====================

# JWT
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
JWT_ALGORITHM = "HS256"

# Mots de passe
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Rate limiting
RATE_LIMITS = {
    "login": {"requests": 5, "window": 300},      # 5 tentatives par 5 minutes
    "signup": {"requests": 3, "window": 3600},    # 3 tentatives par heure
    "verification": {"requests": 10, "window": 600}, # 10 tentatives par 10 minutes
    "password_reset": {"requests": 3, "window": 3600}, # 3 tentatives par heure
}

# ==================== CONFIGURATION DE FICHIERS ====================

# Upload
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

# Dossiers
UPLOAD_DIR = "uploads"
PHOTOS_DIR = f"{UPLOAD_DIR}/photos"
DOCUMENTS_DIR = f"{UPLOAD_DIR}/documents"
FLOOR_PLANS_DIR = f"{UPLOAD_DIR}/floor_plans"

# ==================== CONFIGURATION D'EMAIL ====================

# Providers
EMAIL_PROVIDERS = {
    "resend": "Resend",
    "mailgun": "Mailgun", 
    "smtp": "SMTP"
}

# Templates
EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES = 15
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# ==================== LIMITES MÉTIER ====================

# Abonnements
FREE_SUBSCRIPTION_LIMITS = {
    "max_apartments": 3,
    "max_photos_per_apartment": 10,
    "max_documents_per_apartment": 5,
    "max_tenants_per_apartment": 2
}

PREMIUM_SUBSCRIPTION_LIMITS = {
    "max_apartments": -1,  # Illimité
    "max_photos_per_apartment": 50,
    "max_documents_per_apartment": 20,
    "max_tenants_per_apartment": 10
}

# Propriétés
MAX_SURFACE_AREA = 10000  # m²
MAX_ROOMS = 50
MAX_FLOOR = 100
MIN_FLOOR = -5

# Prix
MAX_PRICE = 1000000  # €
MAX_RENT = 50000  # €/mois

# ==================== MESSAGES D'ERREUR STANDARDS ====================

ERROR_MESSAGES = {
    # Authentification
    "INVALID_CREDENTIALS": "Email ou mot de passe incorrect",
    "ACCOUNT_DISABLED": "Compte désactivé",
    "EMAIL_NOT_VERIFIED": "Email non vérifié",
    "TOKEN_EXPIRED": "Token expiré",
    "TOKEN_INVALID": "Token invalide",
    
    # Permissions
    "ACCESS_DENIED": "Accès refusé",
    "INSUFFICIENT_PERMISSIONS": "Permissions insuffisantes",
    "RESOURCE_NOT_FOUND": "Ressource non trouvée",
    
    # Validation
    "INVALID_EMAIL": "Format d'email invalide",
    "INVALID_PHONE": "Format de téléphone invalide",
    "INVALID_POSTAL_CODE": "Code postal invalide",
    "PASSWORD_TOO_WEAK": "Mot de passe trop faible",
    
    # Métier
    "SUBSCRIPTION_LIMIT_EXCEEDED": "Limite d'abonnement dépassée",
    "DUPLICATE_ENTRY": "Cette valeur existe déjà",
    "FOREIGN_KEY_VIOLATION": "Référence invalide",
    "PARENT_ROW_CONSTRAINT": "Impossible de supprimer: des éléments dépendants existent",
    
    # Fichiers
    "FILE_TOO_LARGE": "Fichier trop volumineux",
    "INVALID_FILE_TYPE": "Type de fichier non autorisé",
    "FILE_UPLOAD_ERROR": "Erreur lors de l'upload du fichier",
}

# ==================== MESSAGES DE SUCCÈS STANDARDS ====================

SUCCESS_MESSAGES = {
    # Authentification
    "LOGIN_SUCCESS": "Connexion réussie",
    "LOGOUT_SUCCESS": "Déconnexion réussie",
    "SIGNUP_SUCCESS": "Inscription réussie",
    "EMAIL_VERIFIED": "Email vérifié avec succès",
    "PASSWORD_CHANGED": "Mot de passe modifié avec succès",
    
    # CRUD
    "CREATED_SUCCESS": "Créé avec succès",
    "UPDATED_SUCCESS": "Modifié avec succès", 
    "DELETED_SUCCESS": "Supprimé avec succès",
    
    # Fichiers
    "FILE_UPLOADED": "Fichier uploadé avec succès",
    "FILE_DELETED": "Fichier supprimé avec succès",
    
    # Email
    "VERIFICATION_EMAIL_SENT": "Email de vérification envoyé",
    "PASSWORD_RESET_EMAIL_SENT": "Email de réinitialisation envoyé",
}

# ==================== CONFIGURATION RÉGIONALE ====================

# Formats
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"
TIME_FORMAT = "%H:%M"

# Devises
DEFAULT_CURRENCY = "EUR"
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP"]

# Pays
DEFAULT_COUNTRY = "France"
SUPPORTED_COUNTRIES = [
    "France", "Belgique", "Suisse", "Canada", "Luxembourg"
]

# ==================== CONFIGURATION API ====================

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache
CACHE_EXPIRY_SECONDS = {
    "user_permissions": 300,     # 5 minutes
    "subscription_status": 600,  # 10 minutes
    "apartment_list": 180,       # 3 minutes
    "building_details": 900,     # 15 minutes
}

# ==================== PATTERNS DE VALIDATION ====================

VALIDATION_PATTERNS = {
    "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    "phone_fr": r'^(?:\+33|0)[1-9]\d{8}$',
    "phone_international": r'^\+\d{10,15}$',
    "postal_code_fr": r'^\d{5}$',
    "street_number": r'^\d+[a-zA-Z]?(?:\s*bis|ter|quater)?$',
    "password_strong": r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]).{8,}$',
}

# ==================== STATUTS STANDARDS ====================

STANDARD_STATUSES = {
    # Général
    "ACTIVE": "active",
    "INACTIVE": "inactive",
    "PENDING": "pending",
    "CANCELLED": "cancelled",
    "DELETED": "deleted",
    
    # Spécifiques
    "DRAFT": "draft",
    "PUBLISHED": "published",
    "ARCHIVED": "archived",
    "EXPIRED": "expired",
    "APPROVED": "approved",
    "REJECTED": "rejected",
}

# ==================== CONFIGURATION AUDIT ====================

# Types d'événements à logger
AUDIT_EVENTS = {
    "USER_LOGIN": "Connexion utilisateur",
    "USER_LOGOUT": "Déconnexion utilisateur", 
    "USER_SIGNUP": "Inscription utilisateur",
    "EMAIL_VERIFICATION": "Vérification email",
    "PASSWORD_CHANGE": "Changement mot de passe",
    "APARTMENT_ACCESS": "Accès appartement",
    "DOCUMENT_DOWNLOAD": "Téléchargement document",
    "PAYMENT_PROCESSED": "Paiement traité",
    "SUBSCRIPTION_CHANGE": "Changement abonnement",
}

# Niveaux de log
LOG_LEVELS = {
    "DEBUG": "debug",
    "INFO": "info", 
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "critical",
}

# ==================== CONFIGURATION NOTIFICATIONS ====================

NOTIFICATION_TYPES = {
    "EMAIL_VERIFICATION": "email_verification",
    "PASSWORD_RESET": "password_reset",
    "PAYMENT_SUCCESS": "payment_success",
    "PAYMENT_FAILED": "payment_failed",
    "SUBSCRIPTION_EXPIRY": "subscription_expiry",
    "LEASE_EXPIRY": "lease_expiry",
    "MAINTENANCE_ALERT": "maintenance_alert",
}

# ==================== HELPERS ====================

def get_error_message(error_code: str, default: str = "Une erreur est survenue") -> str:
    """
    Récupère un message d'erreur standardisé
    """
    return ERROR_MESSAGES.get(error_code, default)


def get_success_message(success_code: str, default: str = "Opération réussie") -> str:
    """
    Récupère un message de succès standardisé
    """
    return SUCCESS_MESSAGES.get(success_code, default)


def get_subscription_limit(subscription_type: str, limit_type: str) -> int:
    """
    Récupère une limite d'abonnement
    """
    if subscription_type.upper() == "FREE":
        return FREE_SUBSCRIPTION_LIMITS.get(limit_type, 0)
    elif subscription_type.upper() == "PREMIUM":
        return PREMIUM_SUBSCRIPTION_LIMITS.get(limit_type, -1)
    else:
        return 0


def is_supported_currency(currency: str) -> bool:
    """
    Vérifie si une devise est supportée
    """
    return currency.upper() in SUPPORTED_CURRENCIES


def is_supported_country(country: str) -> bool:
    """
    Vérifie si un pays est supporté
    """
    return country in SUPPORTED_COUNTRIES