"""
Mixins pour les modèles SQLAlchemy
Séparation des responsabilités et réutilisabilité des fonctionnalités communes
"""
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from datetime import datetime


class TimestampMixin:
    """
    Mixin pour ajouter des timestamps automatiques
    """
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="Date de création")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="Date de dernière modification")


class AddressMixin:
    """
    Mixin pour les champs d'adresse
    Réutilisable pour UserAuth, Building, etc.
    """
    street_number = Column(String(100), nullable=True, comment="Numéro de rue")
    street_name = Column(String(500), nullable=True, comment="Nom de la rue")
    complement = Column(String(500), nullable=True, comment="Complément d'adresse")
    postal_code = Column(String(10), nullable=True, comment="Code postal")
    city = Column(String(200), nullable=True, comment="Ville")
    country = Column(String(100), nullable=True, default="France", comment="Pays")
    
    @property
    def full_address(self) -> str:
        """
        Retourne l'adresse complète formatée
        """
        address_parts = []
        
        if self.street_number:
            address_parts.append(self.street_number)
        if self.street_name:
            address_parts.append(self.street_name)
        if self.complement:
            address_parts.append(self.complement)
        
        street_address = " ".join(address_parts)
        
        city_parts = []
        if self.postal_code:
            city_parts.append(self.postal_code)
        if self.city:
            city_parts.append(self.city)
        
        city_address = " ".join(city_parts)
        
        full_parts = [part for part in [street_address, city_address, self.country] if part]
        return ", ".join(full_parts)


class ContactMixin:
    """
    Mixin pour les informations de contact
    """
    phone = Column(String(20), nullable=True, comment="Numéro de téléphone")
    
    def format_phone(self) -> str:
        """
        Formate le numéro de téléphone pour l'affichage
        """
        if not self.phone:
            return ""
        
        # Formatter les numéros français
        if self.phone.startswith("+33"):
            formatted = self.phone.replace("+33", "0")
            if len(formatted) == 10:
                return f"{formatted[:2]} {formatted[2:4]} {formatted[4:6]} {formatted[6:8]} {formatted[8:]}"
        
        return self.phone


class SoftDeleteMixin:
    """
    Mixin pour la suppression logique (soft delete)
    """
    deleted_at = Column(DateTime, nullable=True, comment="Date de suppression (soft delete)")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="Marqueur de suppression")
    
    def soft_delete(self):
        """
        Marque l'enregistrement comme supprimé
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """
        Restaure un enregistrement supprimé
        """
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """
    Mixin pour l'audit automatique
    """
    created_by = Column(String(100), nullable=True, comment="Créé par")
    updated_by = Column(String(100), nullable=True, comment="Modifié par")
    
    def set_created_by(self, user_identifier: str):
        """
        Définit qui a créé l'enregistrement
        """
        self.created_by = user_identifier
    
    def set_updated_by(self, user_identifier: str):
        """
        Définit qui a modifié l'enregistrement
        """
        self.updated_by = user_identifier


class NamedEntityMixin:
    """
    Mixin pour les entités nommées avec description
    """
    name = Column(String(200), nullable=False, comment="Nom")
    description = Column(String(1000), nullable=True, comment="Description")
    
    def __str__(self):
        return self.name or f"{self.__class__.__name__}#{self.id}"


class MetadataMixin:
    """
    Mixin pour les métadonnées JSON
    """
    metadata = Column(String(2000), nullable=True, comment="Métadonnées JSON")
    
    def get_metadata(self) -> dict:
        """
        Récupère les métadonnées sous forme de dictionnaire
        """
        if not self.metadata:
            return {}
        
        try:
            import json
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, data: dict):
        """
        Définit les métadonnées à partir d'un dictionnaire
        """
        if data is None:
            self.metadata = None
        else:
            import json
            self.metadata = json.dumps(data, ensure_ascii=False)
    
    def add_metadata(self, key: str, value):
        """
        Ajoute une clé aux métadonnées
        """
        current_metadata = self.get_metadata()
        current_metadata[key] = value
        self.set_metadata(current_metadata)


class VersionMixin:
    """
    Mixin pour le versioning optimiste
    """
    version = Column(String(50), nullable=True, comment="Version de l'enregistrement")
    
    def increment_version(self):
        """
        Incrémente la version
        """
        if not self.version:
            self.version = "1.0.0"
        else:
            try:
                major, minor, patch = map(int, self.version.split('.'))
                self.version = f"{major}.{minor}.{patch + 1}"
            except (ValueError, AttributeError):
                self.version = "1.0.0"


class StatusMixin:
    """
    Mixin pour les entités avec statut
    """
    status = Column(String(50), nullable=False, default="active", comment="Statut")
    status_changed_at = Column(DateTime, nullable=True, comment="Date de changement de statut")
    
    def change_status(self, new_status: str):
        """
        Change le statut et met à jour la date
        """
        if self.status != new_status:
            self.status = new_status
            self.status_changed_at = datetime.utcnow()
    
    @property
    def is_active(self) -> bool:
        """
        Vérifie si l'entité est active
        """
        return self.status == "active"


class GeolocationMixin:
    """
    Mixin pour la géolocalisation
    """
    latitude = Column(String(20), nullable=True, comment="Latitude")
    longitude = Column(String(20), nullable=True, comment="Longitude")
    
    @property
    def has_coordinates(self) -> bool:
        """
        Vérifie si les coordonnées sont définies
        """
        return self.latitude is not None and self.longitude is not None
    
    def set_coordinates(self, lat: float, lng: float):
        """
        Définit les coordonnées géographiques
        """
        self.latitude = str(lat)
        self.longitude = str(lng)
    
    def get_coordinates(self) -> tuple:
        """
        Retourne les coordonnées sous forme de tuple (lat, lng)
        """
        if not self.has_coordinates:
            return None, None
        
        try:
            return float(self.latitude), float(self.longitude)
        except (ValueError, TypeError):
            return None, None


class FinancialMixin:
    """
    Mixin pour les données financières
    """
    currency = Column(String(3), nullable=False, default="EUR", comment="Devise")
    
    def format_price(self, amount: float) -> str:
        """
        Formate un montant selon la devise
        """
        if self.currency == "EUR":
            return f"{amount:.2f} €"
        elif self.currency == "USD":
            return f"${amount:.2f}"
        else:
            return f"{amount:.2f} {self.currency}"


class FileAttachmentMixin:
    """
    Mixin pour les pièces jointes
    """
    file_path = Column(String(500), nullable=True, comment="Chemin du fichier")
    file_name = Column(String(255), nullable=True, comment="Nom original du fichier")
    file_size = Column(String(20), nullable=True, comment="Taille du fichier")
    mime_type = Column(String(100), nullable=True, comment="Type MIME du fichier")
    
    @property
    def has_file(self) -> bool:
        """
        Vérifie si un fichier est attaché
        """
        return self.file_path is not None
    
    def set_file_info(self, file_path: str, original_name: str, size: int, mime_type: str):
        """
        Définit les informations du fichier
        """
        self.file_path = file_path
        self.file_name = original_name
        self.file_size = str(size)
        self.mime_type = mime_type
    
    def format_file_size(self) -> str:
        """
        Formate la taille du fichier pour l'affichage
        """
        if not self.file_size:
            return ""
        
        try:
            size_bytes = int(self.file_size)
            
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except (ValueError, TypeError):
            return self.file_size