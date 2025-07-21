"""
Routes API pour la gestion des pièces
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from database import get_db
from auth import get_current_user
from models import UserAuth, Room, Apartment, ApartmentUserLink, UserRole, RoomType
from schemas import RoomCreate, RoomUpdate, RoomOut, RoomWithPhotos
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/rooms", tags=["rooms"])

def check_apartment_access(apartment_id: int, user: UserAuth, db: Session) -> Apartment:
    """Vérifie que l'utilisateur a accès à l'appartement"""
    apartment = db.query(Apartment).filter(Apartment.id == apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # Vérifier si l'utilisateur est propriétaire de l'immeuble
    if apartment.building.user_id == user.id:
        return apartment
    
    # Vérifier si l'utilisateur a des droits sur l'appartement
    user_link = db.query(ApartmentUserLink).filter(
        ApartmentUserLink.apartment_id == apartment_id,
        ApartmentUserLink.user_id == user.id,
        ApartmentUserLink.role.in_([UserRole.owner, UserRole.gestionnaire])
    ).first()
    
    if not user_link:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cet appartement")
    
    return apartment

def check_room_access(room_id: int, user: UserAuth, db: Session) -> Room:
    """Vérifie que l'utilisateur a accès à la pièce"""
    room = db.query(Room).options(joinedload(Room.apartment)).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    
    # Vérifier l'accès via l'appartement
    check_apartment_access(room.apartment_id, user, db)
    return room

@router.get("/apartments/{apartment_id}/rooms", response_model=List[RoomOut])
async def get_apartment_rooms(
    apartment_id: int,
    include_photos: bool = Query(False, description="Inclure les photos de chaque pièce"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les pièces d'un appartement"""
    # Vérifier l'accès à l'appartement
    check_apartment_access(apartment_id, current_user, db)
    
    # Récupérer les pièces
    query = db.query(Room).filter(Room.apartment_id == apartment_id)
    
    if include_photos:
        query = query.options(joinedload(Room.photos))
    
    rooms = query.order_by(Room.sort_order, Room.created_at).all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="APARTMENT",
        entity_id=apartment_id,
        description=f"Consultation des pièces ({len(rooms)} pièces)"
    )
    
    return rooms

@router.get("/apartments/{apartment_id}/rooms/with-photos", response_model=List[RoomWithPhotos])
async def get_apartment_rooms_with_photos(
    apartment_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les pièces d'un appartement avec leurs photos"""
    # Vérifier l'accès à l'appartement
    check_apartment_access(apartment_id, current_user, db)
    
    # Récupérer les pièces avec leurs photos
    rooms = db.query(Room).options(
        joinedload(Room.photos)
    ).filter(
        Room.apartment_id == apartment_id
    ).order_by(Room.sort_order, Room.created_at).all()
    
    return rooms

@router.post("/apartments/{apartment_id}/rooms", response_model=RoomOut)
async def create_room(
    apartment_id: int,
    room_data: RoomCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée une nouvelle pièce dans un appartement"""
    # Vérifier l'accès à l'appartement
    apartment = check_apartment_access(apartment_id, current_user, db)
    
    # Vérifier que l'apartment_id correspond
    if room_data.apartment_id != apartment_id:
        raise HTTPException(status_code=400, detail="L'ID d'appartement ne correspond pas")
    
    # Déterminer le sort_order automatiquement
    max_sort = db.query(Room).filter(Room.apartment_id == apartment_id).count()
    
    # Créer la pièce
    room = Room(
        apartment_id=apartment_id,
        name=room_data.name,
        room_type=room_data.room_type,
        area_m2=room_data.area_m2,
        description=room_data.description,
        floor_level=room_data.floor_level,
        sort_order=max_sort
    )
    
    db.add(room)
    db.commit()
    db.refresh(room)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="APARTMENT",
        entity_id=apartment_id,
        description=f"Création de la pièce '{room.name}' ({room.room_type.value})",
        details=f"{{\"room_id\": {room.id}, \"room_name\": \"{room.name}\", \"room_type\": \"{room.room_type.value}\"}}"
    )
    
    return room

@router.get("/rooms/{room_id}", response_model=RoomOut)
async def get_room(
    room_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère une pièce par son ID"""
    room = check_room_access(room_id, current_user, db)
    return room

@router.put("/rooms/{room_id}", response_model=RoomOut)
async def update_room(
    room_id: int,
    room_update: RoomUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour une pièce"""
    room = check_room_access(room_id, current_user, db)
    
    # Garder les anciennes valeurs pour l'audit
    old_values = {
        "name": room.name,
        "room_type": room.room_type.value,
        "area_m2": str(room.area_m2) if room.area_m2 else None,
        "description": room.description,
        "floor_level": room.floor_level,
        "sort_order": room.sort_order
    }
    
    # Mettre à jour les champs fournis
    update_data = room_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(room, field):
            setattr(room, field, value)
    
    db.commit()
    db.refresh(room)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    new_values = {
        "name": room.name,
        "room_type": room.room_type.value,
        "area_m2": str(room.area_m2) if room.area_m2 else None,
        "description": room.description,
        "floor_level": room.floor_level,
        "sort_order": room.sort_order
    }
    
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="APARTMENT",
        entity_id=room.apartment_id,
        description=f"Modification de la pièce '{room.name}'",
        details=f"{{\"room_id\": {room.id}, \"old_values\": {old_values}, \"new_values\": {new_values}}}"
    )
    
    return room

@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime une pièce"""
    room = check_room_access(room_id, current_user, db)
    
    # Vérifier qu'il n'y a pas de photos associées
    if room.photos:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer la pièce : {len(room.photos)} photo(s) associée(s). Supprimez d'abord les photos."
        )
    
    room_name = room.name
    room_type = room.room_type.value
    apartment_id = room.apartment_id
    
    db.delete(room)
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="APARTMENT",
        entity_id=apartment_id,
        description=f"Suppression de la pièce '{room_name}' ({room_type})",
        details=f"{{\"room_id\": {room_id}, \"room_name\": \"{room_name}\", \"room_type\": \"{room_type}\"}}"
    )
    
    return {"message": f"Pièce '{room_name}' supprimée avec succès"}

@router.post("/apartments/{apartment_id}/rooms/reorder")
async def reorder_rooms(
    apartment_id: int,
    room_ids: List[int],
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Réorganise l'ordre des pièces dans un appartement"""
    # Vérifier l'accès à l'appartement
    check_apartment_access(apartment_id, current_user, db)
    
    # Récupérer toutes les pièces de l'appartement
    rooms = db.query(Room).filter(Room.apartment_id == apartment_id).all()
    room_dict = {room.id: room for room in rooms}
    
    # Vérifier que tous les IDs fournis appartiennent à cet appartement
    for room_id in room_ids:
        if room_id not in room_dict:
            raise HTTPException(
                status_code=400, 
                detail=f"La pièce {room_id} n'appartient pas à cet appartement"
            )
    
    # Vérifier qu'on a tous les IDs de pièces
    if set(room_ids) != set(room_dict.keys()):
        raise HTTPException(
            status_code=400,
            detail="La liste des IDs ne correspond pas aux pièces de l'appartement"
        )
    
    # Mettre à jour l'ordre
    for index, room_id in enumerate(room_ids):
        room_dict[room_id].sort_order = index
    
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="APARTMENT",
        entity_id=apartment_id,
        description=f"Réorganisation de {len(room_ids)} pièces",
        details=f"{{\"new_order\": {room_ids}}}"
    )
    
    return {"message": f"Ordre de {len(room_ids)} pièces mis à jour"}

@router.get("/room-types")
async def get_room_types():
    """Récupère la liste des types de pièces disponibles"""
    return {
        "room_types": [
            {"value": room_type.value, "label": get_room_type_label(room_type)} 
            for room_type in RoomType
        ]
    }

def get_room_type_label(room_type: RoomType) -> str:
    """Retourne le label français pour un type de pièce"""
    labels = {
        RoomType.kitchen: "Cuisine",
        RoomType.bedroom: "Chambre",
        RoomType.living_room: "Salon",
        RoomType.bathroom: "Salle de bain",
        RoomType.office: "Bureau",
        RoomType.storage: "Rangement",
        RoomType.balcony: "Balcon/Terrasse",
        RoomType.dining_room: "Salle à manger",
        RoomType.entrance: "Entrée/Hall",
        RoomType.toilet: "WC",
        RoomType.laundry: "Buanderie",
        RoomType.cellar: "Cave",
        RoomType.garage: "Garage",
        RoomType.other: "Autre"
    }
    return labels.get(room_type, room_type.value)

@router.post("/apartments/{apartment_id}/rooms/templates/{template_type}")
async def create_rooms_from_template(
    apartment_id: int,
    template_type: str,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée des pièces à partir d'un template (T1, T2, T3, etc.)"""
    # Vérifier l'accès à l'appartement
    check_apartment_access(apartment_id, current_user, db)
    
    # Vérifier qu'il n'y a pas déjà de pièces
    existing_rooms = db.query(Room).filter(Room.apartment_id == apartment_id).count()
    if existing_rooms > 0:
        raise HTTPException(
            status_code=400,
            detail=f"L'appartement a déjà {existing_rooms} pièce(s). Supprimez-les d'abord ou ajoutez les pièces manuellement."
        )
    
    # Définir les templates
    templates = {
        "T1": [
            ("Pièce principale", RoomType.living_room),
            ("Cuisine", RoomType.kitchen),
            ("Salle de bain", RoomType.bathroom)
        ],
        "T2": [
            ("Salon", RoomType.living_room),
            ("Chambre", RoomType.bedroom),
            ("Cuisine", RoomType.kitchen),
            ("Salle de bain", RoomType.bathroom)
        ],
        "T3": [
            ("Salon", RoomType.living_room),
            ("Chambre 1", RoomType.bedroom),
            ("Chambre 2", RoomType.bedroom),
            ("Cuisine", RoomType.kitchen),
            ("Salle de bain", RoomType.bathroom)
        ],
        "T4": [
            ("Salon", RoomType.living_room),
            ("Chambre 1", RoomType.bedroom),
            ("Chambre 2", RoomType.bedroom),
            ("Chambre 3", RoomType.bedroom),
            ("Cuisine", RoomType.kitchen),
            ("Salle de bain", RoomType.bathroom)
        ],
        "T5": [
            ("Salon", RoomType.living_room),
            ("Chambre 1", RoomType.bedroom),
            ("Chambre 2", RoomType.bedroom),
            ("Chambre 3", RoomType.bedroom),
            ("Chambre 4", RoomType.bedroom),
            ("Cuisine", RoomType.kitchen),
            ("Salle de bain", RoomType.bathroom)
        ]
    }
    
    if template_type not in templates:
        raise HTTPException(
            status_code=400,
            detail=f"Template '{template_type}' non reconnu. Templates disponibles: {list(templates.keys())}"
        )
    
    # Créer les pièces
    rooms_created = []
    for index, (room_name, room_type) in enumerate(templates[template_type]):
        room = Room(
            apartment_id=apartment_id,
            name=room_name,
            room_type=room_type,
            sort_order=index
        )
        db.add(room)
        rooms_created.append(room)
    
    db.commit()
    
    # Refresh pour récupérer les IDs
    for room in rooms_created:
        db.refresh(room)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="APARTMENT",
        entity_id=apartment_id,
        description=f"Création de {len(rooms_created)} pièces depuis le template {template_type}",
        details=f"{{\"template\": \"{template_type}\", \"rooms_created\": {len(rooms_created)}}}"
    )
    
    return {
        "message": f"{len(rooms_created)} pièces créées depuis le template {template_type}",
        "rooms": rooms_created
    }