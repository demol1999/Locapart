"""
Routes API pour la gestion avancée des photos
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from database import get_db
from auth import get_current_user
from models import UserAuth, Photo, Room, PhotoType
from schemas import PhotoOut, PhotoUpdate, PhotoBatch
from photo_service import PhotoManagementService

router = APIRouter(prefix="/api/photos", tags=["photos"])

@router.post("/upload", response_model=PhotoOut)
async def upload_photo(
    file: UploadFile = File(...),
    type: PhotoType = Form(...),
    building_id: Optional[int] = Form(None),
    apartment_id: Optional[int] = Form(None),
    room_id: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_main: bool = Form(False),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload une nouvelle photo avec traitement automatique"""
    
    photo_service = PhotoManagementService(db)
    
    try:
        photo = photo_service.upload_photo(
            file=file,
            photo_type=type,
            user_id=current_user.id,
            building_id=building_id,
            apartment_id=apartment_id,
            room_id=room_id,
            title=title,
            description=description,
            is_main=is_main
        )
        
        return photo
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/buildings/{building_id}", response_model=PhotoBatch)
async def get_building_photos(
    building_id: int,
    include_url: bool = Query(True, description="Inclure les URLs des photos"),
    size: str = Query("medium", description="Taille des images (thumbnail, medium, large)"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les photos d'un immeuble"""
    
    photo_service = PhotoManagementService(db)
    photos = photo_service.get_photos_by_context(
        PhotoType.building, 
        building_id=building_id
    )
    
    # Ajouter les URLs si demandé
    photo_list = []
    for photo in photos:
        photo_dict = photo.__dict__.copy()
        if include_url:
            photo_dict['url'] = photo_service.get_photo_url(photo, size)
        photo_list.append(PhotoOut(**photo_dict))
    
    has_main = any(photo.is_main for photo in photos)
    
    return PhotoBatch(
        photos=photo_list,
        total=len(photos),
        has_main=has_main
    )

@router.get("/apartments/{apartment_id}", response_model=PhotoBatch)
async def get_apartment_photos(
    apartment_id: int,
    include_url: bool = Query(True, description="Inclure les URLs des photos"),
    size: str = Query("medium", description="Taille des images"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les photos d'un appartement"""
    
    photo_service = PhotoManagementService(db)
    photos = photo_service.get_photos_by_context(
        PhotoType.apartment,
        apartment_id=apartment_id
    )
    
    photo_list = []
    for photo in photos:
        photo_dict = photo.__dict__.copy()
        if include_url:
            photo_dict['url'] = photo_service.get_photo_url(photo, size)
        photo_list.append(PhotoOut(**photo_dict))
    
    has_main = any(photo.is_main for photo in photos)
    
    return PhotoBatch(
        photos=photo_list,
        total=len(photos),
        has_main=has_main
    )

@router.get("/rooms/{room_id}", response_model=PhotoBatch)
async def get_room_photos(
    room_id: int,
    include_url: bool = Query(True, description="Inclure les URLs des photos"),
    size: str = Query("medium", description="Taille des images"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les photos d'une pièce"""
    
    photo_service = PhotoManagementService(db)
    photos = photo_service.get_photos_by_context(
        PhotoType.room,
        room_id=room_id
    )
    
    photo_list = []
    for photo in photos:
        photo_dict = photo.__dict__.copy()
        if include_url:
            photo_dict['url'] = photo_service.get_photo_url(photo, size)
        photo_list.append(PhotoOut(**photo_dict))
    
    has_main = any(photo.is_main for photo in photos)
    
    return PhotoBatch(
        photos=photo_list,
        total=len(photos),
        has_main=has_main
    )

@router.get("/apartments/{apartment_id}/gallery")
async def get_apartment_gallery(
    apartment_id: int,
    include_url: bool = Query(True, description="Inclure les URLs des photos"),
    size: str = Query("medium", description="Taille des images"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère la galerie complète d'un appartement (appartement + toutes les pièces)"""
    
    photo_service = PhotoManagementService(db)
    
    # Photos de l'appartement
    apartment_photos = photo_service.get_photos_by_context(
        PhotoType.apartment,
        apartment_id=apartment_id
    )
    
    # Photos des pièces
    rooms = db.query(Room).filter(Room.apartment_id == apartment_id).order_by(Room.sort_order).all()
    
    gallery = {
        "apartment": {
            "photos": [],
            "total": len(apartment_photos),
            "has_main": any(photo.is_main for photo in apartment_photos)
        },
        "rooms": []
    }
    
    # Ajouter les photos d'appartement
    for photo in apartment_photos:
        photo_dict = photo.__dict__.copy()
        if include_url:
            photo_dict['url'] = photo_service.get_photo_url(photo, size)
        gallery["apartment"]["photos"].append(PhotoOut(**photo_dict))
    
    # Ajouter les photos de chaque pièce
    for room in rooms:
        room_photos = photo_service.get_photos_by_context(
            PhotoType.room,
            room_id=room.id
        )
        
        room_data = {
            "room": {
                "id": room.id,
                "name": room.name,
                "room_type": room.room_type.value,
                "sort_order": room.sort_order
            },
            "photos": [],
            "total": len(room_photos),
            "has_main": any(photo.is_main for photo in room_photos)
        }
        
        for photo in room_photos:
            photo_dict = photo.__dict__.copy()
            if include_url:
                photo_dict['url'] = photo_service.get_photo_url(photo, size)
            room_data["photos"].append(PhotoOut(**photo_dict))
        
        gallery["rooms"].append(room_data)
    
    return gallery

@router.put("/{photo_id}", response_model=PhotoOut)
async def update_photo(
    photo_id: int,
    photo_update: PhotoUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour les métadonnées d'une photo"""
    
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    
    # TODO: Vérifier les permissions
    
    # Gérer la photo principale
    if photo_update.is_main is True and not photo.is_main:
        # Désactiver les autres photos principales du même contexte
        query = db.query(Photo).filter(
            Photo.type == photo.type,
            Photo.is_main == True
        )
        
        if photo.type == PhotoType.room:
            query = query.filter(Photo.room_id == photo.room_id)
        elif photo.type == PhotoType.apartment:
            query = query.filter(Photo.apartment_id == photo.apartment_id)
        elif photo.type == PhotoType.building:
            query = query.filter(Photo.building_id == photo.building_id)
        
        for other_photo in query.all():
            other_photo.is_main = False
    
    # Mettre à jour les champs fournis
    update_data = photo_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(photo, field):
            setattr(photo, field, value)
    
    db.commit()
    db.refresh(photo)
    
    return photo

@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime une photo et ses fichiers"""
    
    photo_service = PhotoManagementService(db)
    
    try:
        photo_service.delete_photo(photo_id, current_user.id)
        return {"message": "Photo supprimée avec succès"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reorder")
async def reorder_photos(
    photo_ids: List[int],
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Réorganise l'ordre des photos"""
    
    if not photo_ids:
        raise HTTPException(status_code=400, detail="Liste des IDs vide")
    
    # Récupérer toutes les photos
    photos = db.query(Photo).filter(Photo.id.in_(photo_ids)).all()
    
    if len(photos) != len(photo_ids):
        raise HTTPException(status_code=400, detail="Certaines photos sont introuvables")
    
    # Vérifier que toutes les photos appartiennent au même contexte
    first_photo = photos[0]
    for photo in photos[1:]:
        if (photo.type != first_photo.type or 
            photo.building_id != first_photo.building_id or
            photo.apartment_id != first_photo.apartment_id or
            photo.room_id != first_photo.room_id):
            raise HTTPException(
                status_code=400,
                detail="Toutes les photos doivent appartenir au même contexte"
            )
    
    # TODO: Vérifier les permissions
    
    # Mettre à jour l'ordre
    photo_dict = {photo.id: photo for photo in photos}
    for index, photo_id in enumerate(photo_ids):
        photo_dict[photo_id].sort_order = index
    
    db.commit()
    
    return {"message": f"Ordre de {len(photo_ids)} photos mis à jour"}

@router.get("/{photo_id}/url")
async def get_photo_url(
    photo_id: int,
    size: str = Query("medium", description="Taille de l'image"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'URL d'une photo spécifique"""
    
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    
    # TODO: Vérifier les permissions
    
    photo_service = PhotoManagementService(db)
    url = photo_service.get_photo_url(photo, size)
    
    return {
        "photo_id": photo_id,
        "url": url,
        "size": size,
        "filename": photo.filename
    }

@router.get("/{photo_id}/metadata")
async def get_photo_metadata(
    photo_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les métadonnées d'une photo"""
    
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    
    # TODO: Vérifier les permissions
    
    import json
    metadata = json.loads(photo.metadata) if photo.metadata else {}
    
    return {
        "photo_id": photo_id,
        "filename": photo.filename,
        "original_filename": photo.original_filename,
        "type": photo.type.value,
        "title": photo.title,
        "description": photo.description,
        "file_size": photo.file_size,
        "dimensions": {
            "width": photo.width,
            "height": photo.height
        },
        "mime_type": photo.mime_type,
        "is_main": photo.is_main,
        "sort_order": photo.sort_order,
        "created_at": photo.created_at,
        "updated_at": photo.updated_at,
        "metadata": metadata,
        "context": {
            "building_id": photo.building_id,
            "apartment_id": photo.apartment_id,
            "room_id": photo.room_id
        }
    }