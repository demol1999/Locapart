"""
Service de gestion des photos avec redimensionnement et stockage hiérarchique
"""
import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from PIL import Image, ExifTags
import shutil

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from models import Photo, Room, Apartment, Building, PhotoType
from schemas import PhotoCreate, PhotoOut
from audit_logger import AuditLogger


class PhotoStorageService:
    """Service de stockage des photos (Single Responsibility)"""
    
    def __init__(self, base_upload_dir: str = "uploads"):
        self.base_upload_dir = Path(base_upload_dir)
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
        # Tailles de redimensionnement
        self.sizes = {
            'thumbnail': (300, 300),
            'medium': (800, 800),
            'large': (1920, 1920)
        }
    
    def validate_file(self, file: UploadFile) -> None:
        """Valide le fichier uploadé"""
        # Vérifier l'extension
        file_ext = Path(file.filename or '').suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Extension de fichier non supportée. Extensions autorisées: {', '.join(self.allowed_extensions)}"
            )
        
        # Vérifier le type MIME
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="Le fichier doit être une image"
            )
    
    def get_storage_path(self, photo_type: PhotoType, building_id: Optional[int] = None, 
                        apartment_id: Optional[int] = None, room_id: Optional[int] = None) -> Path:
        """Détermine le chemin de stockage selon la hiérarchie"""
        if photo_type == PhotoType.building and building_id:
            return self.base_upload_dir / "buildings" / str(building_id) / "building_photos"
        elif photo_type == PhotoType.apartment and building_id and apartment_id:
            return self.base_upload_dir / "buildings" / str(building_id) / "apartments" / str(apartment_id) / "apartment_photos"
        elif photo_type == PhotoType.room and building_id and apartment_id and room_id:
            return self.base_upload_dir / "buildings" / str(building_id) / "apartments" / str(apartment_id) / "rooms" / str(room_id)
        else:
            raise ValueError(f"Paramètres manquants pour le type {photo_type}")
    
    def generate_filename(self, user_id: int, original_filename: str) -> str:
        """Génère un nom de fichier unique"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{user_id}_{unique_id}{file_ext}"
    
    def create_directories(self, base_path: Path) -> None:
        """Crée la structure de dossiers"""
        for size in ['originals'] + list(self.sizes.keys()):
            (base_path / size).mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file: UploadFile, storage_path: Path, filename: str) -> Dict[str, Any]:
        """Sauvegarde le fichier et crée les différentes tailles"""
        self.create_directories(storage_path)
        
        # Sauvegarder le fichier original
        original_path = storage_path / "originals" / filename
        with open(original_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Analyser l'image
        try:
            with Image.open(original_path) as img:
                # Corriger l'orientation EXIF
                img = self._fix_image_orientation(img)
                
                # Récupérer les métadonnées
                width, height = img.size
                file_size = original_path.stat().st_size
                
                # Créer les différentes tailles
                for size_name, dimensions in self.sizes.items():
                    resized_img = self._resize_image(img, dimensions)
                    size_path = storage_path / size_name / filename
                    resized_img.save(size_path, optimize=True, quality=85)
                
                return {
                    'width': width,
                    'height': height,
                    'file_size': file_size,
                    'storage_path': str(storage_path),
                    'filename': filename
                }
                
        except Exception as e:
            # Nettoyer en cas d'erreur
            self.cleanup_files(storage_path, filename)
            raise HTTPException(status_code=400, detail=f"Erreur lors du traitement de l'image: {str(e)}")
    
    def _fix_image_orientation(self, img: Image.Image) -> Image.Image:
        """Corrige l'orientation de l'image selon les données EXIF"""
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            exif = img._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, TypeError):
            pass
        
        return img
    
    def _resize_image(self, img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """Redimensionne l'image en gardant les proportions"""
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    
    def cleanup_files(self, storage_path: Path, filename: str) -> None:
        """Supprime tous les fichiers associés"""
        for size in ['originals'] + list(self.sizes.keys()):
            file_path = storage_path / size / filename
            if file_path.exists():
                file_path.unlink()
    
    def get_photo_url(self, storage_path: str, filename: str, size: str = 'medium') -> str:
        """Génère l'URL d'accès à une photo"""
        # Convertir le chemin absolu en chemin relatif pour l'URL
        relative_path = Path(storage_path).relative_to(self.base_upload_dir)
        return f"/uploads/{relative_path}/{size}/{filename}"


class PhotoMetadataService:
    """Service de gestion des métadonnées des photos (Single Responsibility)"""
    
    def extract_metadata(self, image_path: Path, user_id: int) -> Dict[str, Any]:
        """Extrait les métadonnées d'une image"""
        metadata = {
            'uploaded_by': user_id,
            'upload_date': datetime.now().isoformat(),
            'processing_version': '1.0'
        }
        
        try:
            with Image.open(image_path) as img:
                # Métadonnées EXIF basiques
                exif = img._getexif()
                if exif:
                    # Extraire quelques métadonnées utiles
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        if tag in ['DateTime', 'Make', 'Model', 'Software']:
                            metadata[f'exif_{tag.lower()}'] = str(value)
        except Exception:
            pass
        
        return metadata


class PhotoManagementService:
    """Service principal de gestion des photos (Facade Pattern)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = PhotoStorageService()
        self.metadata_service = PhotoMetadataService()
        self.audit_logger = AuditLogger(db)
    
    def upload_photo(self, file: UploadFile, photo_type: PhotoType, user_id: int,
                    building_id: Optional[int] = None, apartment_id: Optional[int] = None,
                    room_id: Optional[int] = None, title: Optional[str] = None,
                    description: Optional[str] = None, is_main: bool = False) -> Photo:
        """Upload et traitement complet d'une photo"""
        
        # Validation
        self.storage_service.validate_file(file)
        
        # Vérifier les permissions et récupérer les entités
        building, apartment, room = self._validate_and_get_entities(
            photo_type, user_id, building_id, apartment_id, room_id
        )
        
        # Déterminer la hiérarchie pour le stockage
        if photo_type == PhotoType.room and room:
            building_id = room.apartment.building.id
            apartment_id = room.apartment.id
            room_id = room.id
        elif photo_type == PhotoType.apartment and apartment:
            building_id = apartment.building.id
            apartment_id = apartment.id
            room_id = None
        elif photo_type == PhotoType.building and building:
            building_id = building.id
            apartment_id = None
            room_id = None
        
        # Générer le nom de fichier et le chemin de stockage
        filename = self.storage_service.generate_filename(user_id, file.filename or "photo.jpg")
        storage_path = self.storage_service.get_storage_path(photo_type, building_id, apartment_id, room_id)
        
        # Sauvegarder et traiter l'image
        file_info = self.storage_service.save_file(file, storage_path, filename)
        
        # Extraire les métadonnées
        original_path = storage_path / "originals" / filename
        metadata = self.metadata_service.extract_metadata(original_path, user_id)
        
        # Gérer la photo principale
        if is_main:
            self._unset_main_photos(photo_type, building_id, apartment_id, room_id)
        
        # Déterminer l'ordre de tri
        sort_order = self._get_next_sort_order(photo_type, building_id, apartment_id, room_id)
        
        # Créer l'enregistrement en base
        photo = Photo(
            filename=filename,
            original_filename=file.filename,
            type=photo_type,
            title=title,
            description=description,
            file_size=file_info['file_size'],
            width=file_info['width'],
            height=file_info['height'],
            mime_type=file.content_type,
            is_main=is_main,
            sort_order=sort_order,
            metadata=json.dumps(metadata),
            building_id=building_id,
            apartment_id=apartment_id,
            room_id=room_id
        )
        
        self.db.add(photo)
        self.db.commit()
        self.db.refresh(photo)
        
        # Log de l'action
        entity_type = photo_type.value.upper()
        entity_id = room_id or apartment_id or building_id
        
        self.audit_logger.log_action(
            user_id=user_id,
            action="CREATE",
            entity_type=entity_type,
            entity_id=entity_id,
            description=f"Upload de photo '{title or filename}' ({photo_type.value})",
            details=json.dumps({
                "photo_id": photo.id,
                "filename": filename,
                "file_size": file_info['file_size'],
                "dimensions": f"{file_info['width']}x{file_info['height']}",
                "is_main": is_main
            })
        )
        
        return photo
    
    def _validate_and_get_entities(self, photo_type: PhotoType, user_id: int,
                                  building_id: Optional[int], apartment_id: Optional[int],
                                  room_id: Optional[int]) -> Tuple[Optional[Building], Optional[Apartment], Optional[Room]]:
        """Valide les permissions et récupère les entités"""
        building = apartment = room = None
        
        if photo_type == PhotoType.room:
            if not room_id:
                raise HTTPException(status_code=400, detail="room_id requis pour une photo de pièce")
            
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if not room:
                raise HTTPException(status_code=404, detail="Pièce introuvable")
            
            apartment = room.apartment
            building = apartment.building
            
        elif photo_type == PhotoType.apartment:
            if not apartment_id:
                raise HTTPException(status_code=400, detail="apartment_id requis pour une photo d'appartement")
            
            apartment = self.db.query(Apartment).filter(Apartment.id == apartment_id).first()
            if not apartment:
                raise HTTPException(status_code=404, detail="Appartement introuvable")
            
            building = apartment.building
            
        elif photo_type == PhotoType.building:
            if not building_id:
                raise HTTPException(status_code=400, detail="building_id requis pour une photo d'immeuble")
            
            building = self.db.query(Building).filter(Building.id == building_id).first()
            if not building:
                raise HTTPException(status_code=404, detail="Immeuble introuvable")
        
        # TODO: Vérifier les permissions utilisateur
        # Ici on pourrait ajouter la vérification des droits selon UserRole
        
        return building, apartment, room
    
    def _unset_main_photos(self, photo_type: PhotoType, building_id: Optional[int],
                          apartment_id: Optional[int], room_id: Optional[int]) -> None:
        """Désactive les autres photos principales du même contexte"""
        query = self.db.query(Photo).filter(
            Photo.type == photo_type,
            Photo.is_main == True
        )
        
        if photo_type == PhotoType.room and room_id:
            query = query.filter(Photo.room_id == room_id)
        elif photo_type == PhotoType.apartment and apartment_id:
            query = query.filter(Photo.apartment_id == apartment_id)
        elif photo_type == PhotoType.building and building_id:
            query = query.filter(Photo.building_id == building_id)
        
        for photo in query.all():
            photo.is_main = False
        
        self.db.commit()
    
    def _get_next_sort_order(self, photo_type: PhotoType, building_id: Optional[int],
                           apartment_id: Optional[int], room_id: Optional[int]) -> int:
        """Détermine le prochain ordre de tri"""
        query = self.db.query(Photo).filter(Photo.type == photo_type)
        
        if photo_type == PhotoType.room and room_id:
            query = query.filter(Photo.room_id == room_id)
        elif photo_type == PhotoType.apartment and apartment_id:
            query = query.filter(Photo.apartment_id == apartment_id)
        elif photo_type == PhotoType.building and building_id:
            query = query.filter(Photo.building_id == building_id)
        
        return query.count()
    
    def delete_photo(self, photo_id: int, user_id: int) -> bool:
        """Supprime une photo et ses fichiers"""
        photo = self.db.query(Photo).filter(Photo.id == photo_id).first()
        if not photo:
            raise HTTPException(status_code=404, detail="Photo introuvable")
        
        # TODO: Vérifier les permissions
        
        # Déterminer le chemin de stockage
        storage_path = self.storage_service.get_storage_path(
            photo.type, photo.building_id, photo.apartment_id, photo.room_id
        )
        
        # Supprimer les fichiers
        self.storage_service.cleanup_files(storage_path, photo.filename)
        
        # Supprimer l'enregistrement
        self.db.delete(photo)
        self.db.commit()
        
        # Log de l'action
        self.audit_logger.log_action(
            user_id=user_id,
            action="DELETE",
            entity_type=photo.type.value.upper(),
            entity_id=photo.room_id or photo.apartment_id or photo.building_id,
            description=f"Suppression de la photo '{photo.title or photo.filename}'",
            details=json.dumps({"photo_id": photo_id, "filename": photo.filename})
        )
        
        return True
    
    def get_photos_by_context(self, photo_type: PhotoType, building_id: Optional[int] = None,
                             apartment_id: Optional[int] = None, room_id: Optional[int] = None) -> List[Photo]:
        """Récupère les photos d'un contexte donné"""
        query = self.db.query(Photo).filter(Photo.type == photo_type)
        
        if photo_type == PhotoType.room and room_id:
            query = query.filter(Photo.room_id == room_id)
        elif photo_type == PhotoType.apartment and apartment_id:
            query = query.filter(Photo.apartment_id == apartment_id)
        elif photo_type == PhotoType.building and building_id:
            query = query.filter(Photo.building_id == building_id)
        
        return query.order_by(Photo.is_main.desc(), Photo.sort_order, Photo.created_at).all()
    
    def get_photo_url(self, photo: Photo, size: str = 'medium') -> str:
        """Génère l'URL d'accès à une photo"""
        storage_path = self.storage_service.get_storage_path(
            photo.type, photo.building_id, photo.apartment_id, photo.room_id
        )
        return self.storage_service.get_photo_url(str(storage_path), photo.filename, size)