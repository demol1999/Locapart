"""
Validateurs réutilisables pour l'application LocAppart
Centralisation de toute la logique de validation pour éviter la duplication
"""
import re
from typing import Optional
from pydantic import field_validator, ValidationInfo


class CommonValidators:
    """Validateurs communs utilisés dans plusieurs schémas"""
    
    @staticmethod
    def validate_password(password: str) -> str:
        """
        Valide la complexité du mot de passe
        """
        if len(password) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        
        if not re.search(r'[A-Z]', password):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        
        if not re.search(r'[a-z]', password):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        
        if not re.search(r'[0-9]', password):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
            raise ValueError('Le mot de passe doit contenir au moins un caractère spécial')
        
        return password
    
    @staticmethod
    def validate_phone(phone: Optional[str]) -> Optional[str]:
        """
        Valide le format du numéro de téléphone
        """
        if phone is None:
            return phone
        
        # Nettoyer le numéro (enlever espaces, tirets, points, parenthèses)
        cleaned_phone = re.sub(r'[\s\-\.\(\)]', '', phone)
        
        # Pattern pour numéros français et internationaux
        french_mobile_pattern = r'^(?:\+33|0)[1-9]\d{8}$'
        international_pattern = r'^\+\d{10,15}$'
        
        if not (re.match(french_mobile_pattern, cleaned_phone) or 
                re.match(international_pattern, cleaned_phone)):
            raise ValueError('Format de téléphone invalide. Utilisez le format français (06xxxxxxxx) ou international (+33xxxxxxxxx)')
        
        return cleaned_phone
    
    @staticmethod
    def validate_postal_code(postal_code: Optional[str]) -> Optional[str]:
        """
        Valide le code postal français
        """
        if postal_code is None:
            return postal_code
        
        # Pattern pour code postal français (5 chiffres)
        if not re.match(r'^\d{5}$', postal_code):
            raise ValueError('Le code postal doit contenir exactement 5 chiffres')
        
        return postal_code
    
    @staticmethod
    def validate_name(name: str, field_name: str = "nom") -> str:
        """
        Valide les noms (prénom, nom, nom de rue, etc.)
        """
        if not name or len(name.strip()) == 0:
            raise ValueError(f'Le {field_name} ne peut pas être vide')
        
        if len(name) < 2:
            raise ValueError(f'Le {field_name} doit contenir au moins 2 caractères')
        
        if len(name) > 100:
            raise ValueError(f'Le {field_name} ne peut pas dépasser 100 caractères')
        
        # Vérifier que le nom contient au moins une lettre
        if not re.search(r'[a-zA-ZàâäéèêëïîôöùûüÿñçÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÑÇ]', name):
            raise ValueError(f'Le {field_name} doit contenir au moins une lettre')
        
        return name.strip()
    
    @staticmethod
    def validate_city(city: Optional[str]) -> Optional[str]:
        """
        Valide le nom de ville
        """
        if city is None:
            return city
        
        return CommonValidators.validate_name(city, "nom de ville")
    
    @staticmethod
    def validate_street_name(street_name: Optional[str]) -> Optional[str]:
        """
        Valide le nom de rue
        """
        if street_name is None:
            return street_name
        
        return CommonValidators.validate_name(street_name, "nom de rue")
    
    @staticmethod
    def validate_building_name(building_name: str) -> str:
        """
        Valide le nom de bâtiment
        """
        return CommonValidators.validate_name(building_name, "nom du bâtiment")
    
    @staticmethod
    def validate_surface_area(surface: Optional[float]) -> Optional[float]:
        """
        Valide la surface (en m²)
        """
        if surface is None:
            return surface
        
        if surface <= 0:
            raise ValueError('La surface doit être positive')
        
        if surface > 10000:  # Surface maximale raisonnable
            raise ValueError('La surface ne peut pas dépasser 10000 m²')
        
        return round(surface, 2)
    
    @staticmethod
    def validate_positive_number(value: Optional[float], field_name: str = "valeur") -> Optional[float]:
        """
        Valide qu'un nombre est positif
        """
        if value is None:
            return value
        
        if value < 0:
            raise ValueError(f'La {field_name} ne peut pas être négative')
        
        return value
    
    @staticmethod
    def validate_price(price: Optional[float]) -> Optional[float]:
        """
        Valide un prix (en euros)
        """
        if price is None:
            return price
        
        if price < 0:
            raise ValueError('Le prix ne peut pas être négatif')
        
        if price > 1000000:  # Prix maximum raisonnable
            raise ValueError('Le prix ne peut pas dépasser 1 000 000 €')
        
        return round(price, 2)


class AddressValidators:
    """Validateurs spécifiques aux adresses"""
    
    @staticmethod
    def validate_street_number(street_number: Optional[str]) -> Optional[str]:
        """
        Valide le numéro de rue
        """
        if street_number is None:
            return street_number
        
        if not re.match(r'^\d+[a-zA-Z]?(?:\s*bis|ter|quater)?$', street_number.strip()):
            raise ValueError('Format de numéro de rue invalide (ex: 123, 123bis, 123 ter)')
        
        return street_number.strip()


class PropertyValidators:
    """Validateurs spécifiques aux propriétés immobilières"""
    
    @staticmethod
    def validate_room_count(room_count: Optional[int]) -> Optional[int]:
        """
        Valide le nombre de pièces
        """
        if room_count is None:
            return room_count
        
        if room_count < 1:
            raise ValueError('Le nombre de pièces doit être au moins 1')
        
        if room_count > 50:  # Nombre maximum raisonnable
            raise ValueError('Le nombre de pièces ne peut pas dépasser 50')
        
        return room_count
    
    @staticmethod
    def validate_floor_number(floor: Optional[int]) -> Optional[int]:
        """
        Valide le numéro d'étage
        """
        if floor is None:
            return floor
        
        if floor < -5:  # Sous-sols maximum raisonnable
            raise ValueError('L\'étage ne peut pas être inférieur à -5')
        
        if floor > 100:  # Étage maximum raisonnable
            raise ValueError('L\'étage ne peut pas dépasser 100')
        
        return floor


class FinancialValidators:
    """Validateurs spécifiques aux données financières"""
    
    @staticmethod
    def validate_amount(amount: float, field_name: str = "montant") -> float:
        """
        Valide un montant financier
        """
        if amount < 0:
            raise ValueError(f'Le {field_name} ne peut pas être négatif')
        
        # Limiter à 2 décimales pour les montants financiers
        return round(amount, 2)
    
    @staticmethod
    def validate_percentage(percentage: Optional[float]) -> Optional[float]:
        """
        Valide un pourcentage
        """
        if percentage is None:
            return percentage
        
        if percentage < 0 or percentage > 100:
            raise ValueError('Le pourcentage doit être entre 0 et 100')
        
        return round(percentage, 2)


def create_field_validator(validator_func, *args, **kwargs):
    """
    Utilitaire pour créer facilement des field_validator Pydantic
    """
    def validator(cls, v, info: ValidationInfo):
        return validator_func(v, *args, **kwargs)
    
    return field_validator('*', mode='before')(validator)