"""
Routes API pour les états des lieux détaillés avec formulaire pièce par pièce
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import json
import os
import shutil
from datetime import datetime
from uuid import uuid4

from database import get_db
from auth import get_current_user
from models import UserAuth, Lease, Apartment
from inventory_models import (
    DetailedInventory, InventoryRoom, InventoryItem, 
    DetailedInventoryPhoto, InventoryItemPhoto, InventoryTemplate,
    InventoryStatus, RoomType, ItemCondition, ItemCategory
)
from inventory_schemas import (
    DetailedInventoryCreate, DetailedInventoryUpdate, DetailedInventoryOut,
    InventoryRoomCreate, InventoryRoomUpdate, InventoryRoomOut,
    InventoryItemCreate, InventoryItemUpdate, InventoryItemOut,
    InventoryPhotoCreate, InventoryPhotoOut, InventoryItemPhotoOut,
    InventoryTemplateCreate, InventoryTemplateOut,
    SignatureRequestCreate, SignatureStatusOut,
    InventoryStats, InventoryComparison, InventoryExportRequest
)
from electronic_signature_service import (
    create_signature_service_from_env, SignatureRequest, SignatureDocument,
    Signer, get_signature_fields_for_inventory, create_inventory_pdf
)
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/detailed-inventories", tags=["detailed-inventories"])

# Configuration des uploads
UPLOAD_DIR = "uploads/inventories"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


def check_inventory_access(inventory_id: int, user: UserAuth, db: Session) -> DetailedInventory:
    """Vérifie que l'utilisateur a accès à l'état des lieux"""
    inventory = db.query(DetailedInventory).filter(
        DetailedInventory.id == inventory_id
    ).first()
    
    if not inventory:
        raise HTTPException(status_code=404, detail="État des lieux introuvable")
    
    if inventory.conducted_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à cet état des lieux"
        )
    
    return inventory


def check_lease_access(lease_id: int, user: UserAuth, db: Session) -> Lease:
    """Vérifie que l'utilisateur a accès au bail"""
    lease = db.query(Lease).filter(
        Lease.id == lease_id,
        Lease.created_by == user.id
    ).first()
    
    if not lease:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce bail"
        )
    
    return lease


# ==================== GESTION DES ÉTATS DES LIEUX ====================

@router.post("/", response_model=DetailedInventoryOut)
async def create_detailed_inventory(
    inventory_data: DetailedInventoryCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un nouvel état des lieux détaillé"""
    
    # Vérifier l'accès au bail
    lease = check_lease_access(inventory_data.lease_id, current_user, db)
    
    # Vérifier que l'appartement existe
    apartment = db.query(Apartment).filter(
        Apartment.id == inventory_data.apartment_id
    ).first()
    
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # Créer l'état des lieux
    inventory = DetailedInventory(
        lease_id=inventory_data.lease_id,
        conducted_by=current_user.id,
        apartment_id=inventory_data.apartment_id,
        inventory_type=inventory_data.inventory_type,
        status=InventoryStatus.DRAFT,
        scheduled_date=inventory_data.scheduled_date,
        tenant_present=inventory_data.tenant_present,
        landlord_present=inventory_data.landlord_present,
        agent_present=inventory_data.agent_present,
        witness_present=inventory_data.witness_present,
        tenant_contact_info=inventory_data.tenant_contact_info.dict() if inventory_data.tenant_contact_info else None,
        landlord_contact_info=inventory_data.landlord_contact_info.dict() if inventory_data.landlord_contact_info else None,
        agent_contact_info=inventory_data.agent_contact_info.dict() if inventory_data.agent_contact_info else None,
        witness_contact_info=inventory_data.witness_contact_info.dict() if inventory_data.witness_contact_info else None,
        weather_conditions=inventory_data.weather_conditions,
        temperature=inventory_data.temperature,
        overall_condition=inventory_data.overall_condition,
        general_notes=inventory_data.general_notes,
        tenant_comments=inventory_data.tenant_comments,
        landlord_comments=inventory_data.landlord_comments,
        agent_comments=inventory_data.agent_comments,
        utilities_data=[reading.dict() for reading in inventory_data.utilities_data] if inventory_data.utilities_data else None
    )
    
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    
    # Créer les pièces si fournies
    if inventory_data.rooms:
        for room_data in inventory_data.rooms:
            room = InventoryRoom(
                inventory_id=inventory.id,
                name=room_data.name,
                room_type=room_data.room_type,
                order=room_data.order,
                length=room_data.length,
                width=room_data.width,
                height=room_data.height,
                area=room_data.area,
                overall_condition=room_data.overall_condition,
                notes=room_data.notes,
                room_data=room_data.room_data
            )
            
            db.add(room)
            db.commit()
            db.refresh(room)
            
            # Créer les éléments de la pièce
            if room_data.items:
                for item_data in room_data.items:
                    item = InventoryItem(
                        room_id=room.id,
                        name=item_data.name,
                        category=item_data.category,
                        description=item_data.description,
                        condition=item_data.condition,
                        brand=item_data.brand,
                        model=item_data.model,
                        serial_number=item_data.serial_number,
                        purchase_date=item_data.purchase_date,
                        warranty_until=item_data.warranty_until,
                        estimated_value=item_data.estimated_value,
                        replacement_cost=item_data.replacement_cost,
                        position_x=item_data.position_x,
                        position_y=item_data.position_y,
                        dimensions=item_data.dimensions.dict() if item_data.dimensions else None,
                        weight=item_data.weight,
                        notes=item_data.notes,
                        defects=[defect.dict() for defect in item_data.defects] if item_data.defects else None,
                        improvements=item_data.improvements,
                        order=item_data.order,
                        is_mandatory=item_data.is_mandatory,
                        item_data=item_data.item_data
                    )
                    
                    db.add(item)
        
        db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="DETAILED_INVENTORY",
        entity_id=inventory.id,
        description=f"Création d'un état des lieux détaillé {inventory_data.inventory_type}",
        details=json.dumps({
            "inventory_id": inventory.id,
            "lease_id": inventory_data.lease_id,
            "apartment_id": inventory_data.apartment_id,
            "type": inventory_data.inventory_type
        })
    )
    
    return inventory


@router.get("/", response_model=List[DetailedInventoryOut])
async def get_user_inventories(
    status: Optional[str] = None,
    inventory_type: Optional[str] = None,
    apartment_id: Optional[int] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les états des lieux de l'utilisateur"""
    
    query = db.query(DetailedInventory).filter(
        DetailedInventory.conducted_by == current_user.id
    ).options(
        joinedload(DetailedInventory.rooms).joinedload(InventoryRoom.items)
    )
    
    if status:
        query = query.filter(DetailedInventory.status == status)
    if inventory_type:
        query = query.filter(DetailedInventory.inventory_type == inventory_type)
    if apartment_id:
        query = query.filter(DetailedInventory.apartment_id == apartment_id)
    
    inventories = query.order_by(DetailedInventory.created_at.desc()).all()
    
    return inventories


@router.get("/{inventory_id}", response_model=DetailedInventoryOut)
async def get_inventory(
    inventory_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un état des lieux spécifique avec tous ses détails"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    # Charger toutes les relations
    inventory = db.query(DetailedInventory).options(
        joinedload(DetailedInventory.rooms).joinedload(InventoryRoom.items).joinedload(InventoryItem.photos),
        joinedload(DetailedInventory.photos)
    ).filter(DetailedInventory.id == inventory_id).first()
    
    return inventory


@router.put("/{inventory_id}", response_model=DetailedInventoryOut)
async def update_inventory(
    inventory_id: int,
    inventory_update: DetailedInventoryUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    # Vérifier que l'état des lieux peut être modifié
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible de modifier un état des lieux signé ou complété"
        )
    
    # Mettre à jour les champs
    update_data = inventory_update.dict(exclude_unset=True)
    
    # Traitement spécial pour les données des participants
    for field in ['tenant_contact_info', 'landlord_contact_info', 'agent_contact_info', 'witness_contact_info']:
        if field in update_data and update_data[field]:
            update_data[field] = update_data[field].dict() if hasattr(update_data[field], 'dict') else update_data[field]
    
    # Traitement spécial pour utilities_data
    if 'utilities_data' in update_data and update_data['utilities_data']:
        update_data['utilities_data'] = [reading.dict() for reading in update_data['utilities_data']]
    
    for field, value in update_data.items():
        if hasattr(inventory, field):
            setattr(inventory, field, value)
    
    inventory.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inventory)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="DETAILED_INVENTORY",
        entity_id=inventory_id,
        description=f"Modification de l'état des lieux #{inventory_id}",
        details=json.dumps({
            "inventory_id": inventory_id,
            "updated_fields": list(update_data.keys())
        })
    )
    
    return inventory


# ==================== GESTION DES PIÈCES ====================

@router.post("/{inventory_id}/rooms", response_model=InventoryRoomOut)
async def add_room_to_inventory(
    inventory_id: int,
    room_data: InventoryRoomCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ajoute une pièce à un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    # Vérifier que l'état des lieux peut être modifié
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'ajouter une pièce à un état des lieux signé"
        )
    
    # Créer la pièce
    room = InventoryRoom(
        inventory_id=inventory_id,
        name=room_data.name,
        room_type=room_data.room_type,
        order=room_data.order,
        length=room_data.length,
        width=room_data.width,
        height=room_data.height,
        area=room_data.area,
        overall_condition=room_data.overall_condition,
        notes=room_data.notes,
        room_data=room_data.room_data
    )
    
    db.add(room)
    db.commit()
    db.refresh(room)
    
    # Créer les éléments si fournis
    if room_data.items:
        for item_data in room_data.items:
            item = InventoryItem(
                room_id=room.id,
                name=item_data.name,
                category=item_data.category,
                description=item_data.description,
                condition=item_data.condition,
                brand=item_data.brand,
                model=item_data.model,
                serial_number=item_data.serial_number,
                purchase_date=item_data.purchase_date,
                warranty_until=item_data.warranty_until,
                estimated_value=item_data.estimated_value,
                replacement_cost=item_data.replacement_cost,
                position_x=item_data.position_x,
                position_y=item_data.position_y,
                dimensions=item_data.dimensions.dict() if item_data.dimensions else None,
                weight=item_data.weight,
                notes=item_data.notes,
                defects=[defect.dict() for defect in item_data.defects] if item_data.defects else None,
                improvements=item_data.improvements,
                order=item_data.order,
                is_mandatory=item_data.is_mandatory,
                item_data=item_data.item_data
            )
            
            db.add(item)
    
    db.commit()
    
    # Marquer l'inventaire comme en cours
    if inventory.status == InventoryStatus.DRAFT:
        inventory.status = InventoryStatus.IN_PROGRESS
        db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="INVENTORY_ROOM",
        entity_id=room.id,
        description=f"Ajout de la pièce '{room_data.name}' à l'état des lieux #{inventory_id}",
        details=json.dumps({
            "room_id": room.id,
            "inventory_id": inventory_id,
            "room_name": room_data.name,
            "room_type": room_data.room_type
        })
    )
    
    return room


@router.get("/{inventory_id}/rooms", response_model=List[InventoryRoomOut])
async def get_inventory_rooms(
    inventory_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère toutes les pièces d'un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    rooms = db.query(InventoryRoom).options(
        joinedload(InventoryRoom.items).joinedload(InventoryItem.photos)
    ).filter(
        InventoryRoom.inventory_id == inventory_id
    ).order_by(InventoryRoom.order).all()
    
    return rooms


@router.put("/rooms/{room_id}", response_model=InventoryRoomOut)
async def update_room(
    room_id: int,
    room_update: InventoryRoomUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour une pièce"""
    
    room = db.query(InventoryRoom).filter(InventoryRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    
    # Vérifier l'accès via l'état des lieux
    inventory = check_inventory_access(room.inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible de modifier une pièce dans un état des lieux signé"
        )
    
    # Mettre à jour les champs
    update_data = room_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(room, field):
            setattr(room, field, value)
    
    room.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(room)
    
    return room


# ==================== GESTION DES ÉLÉMENTS ====================

@router.post("/rooms/{room_id}/items", response_model=InventoryItemOut)
async def add_item_to_room(
    room_id: int,
    item_data: InventoryItemCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ajoute un élément à une pièce"""
    
    room = db.query(InventoryRoom).filter(InventoryRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    
    # Vérifier l'accès
    inventory = check_inventory_access(room.inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'ajouter un élément dans un état des lieux signé"
        )
    
    # Créer l'élément
    item = InventoryItem(
        room_id=room_id,
        name=item_data.name,
        category=item_data.category,
        description=item_data.description,
        condition=item_data.condition,
        brand=item_data.brand,
        model=item_data.model,
        serial_number=item_data.serial_number,
        purchase_date=item_data.purchase_date,
        warranty_until=item_data.warranty_until,
        estimated_value=item_data.estimated_value,
        replacement_cost=item_data.replacement_cost,
        position_x=item_data.position_x,
        position_y=item_data.position_y,
        dimensions=item_data.dimensions.dict() if item_data.dimensions else None,
        weight=item_data.weight,
        notes=item_data.notes,
        defects=[defect.dict() for defect in item_data.defects] if item_data.defects else None,
        improvements=item_data.improvements,
        order=item_data.order,
        is_mandatory=item_data.is_mandatory,
        item_data=item_data.item_data
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="INVENTORY_ITEM",
        entity_id=item.id,
        description=f"Ajout de l'élément '{item_data.name}' dans la pièce '{room.name}'",
        details=json.dumps({
            "item_id": item.id,
            "room_id": room_id,
            "inventory_id": room.inventory_id,
            "item_name": item_data.name,
            "category": item_data.category,
            "condition": item_data.condition
        })
    )
    
    return item


@router.put("/items/{item_id}", response_model=InventoryItemOut)
async def update_item(
    item_id: int,
    item_update: InventoryItemUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour un élément"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    
    # Vérifier l'accès
    room = db.query(InventoryRoom).filter(InventoryRoom.id == item.room_id).first()
    inventory = check_inventory_access(room.inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible de modifier un élément dans un état des lieux signé"
        )
    
    # Sauvegarder l'ancienne condition
    old_condition = item.condition
    
    # Mettre à jour les champs
    update_data = item_update.dict(exclude_unset=True)
    
    # Traitement spécial pour les données complexes
    if 'dimensions' in update_data and update_data['dimensions']:
        update_data['dimensions'] = update_data['dimensions'].dict()
    
    if 'defects' in update_data and update_data['defects']:
        update_data['defects'] = [defect.dict() for defect in update_data['defects']]
    
    for field, value in update_data.items():
        if hasattr(item, field):
            setattr(item, field, value)
    
    # Mettre à jour la condition précédente si la condition change
    if 'condition' in update_data and update_data['condition'] != old_condition:
        item.previous_condition = old_condition
    
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    return item


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un élément"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    
    # Vérifier l'accès
    room = db.query(InventoryRoom).filter(InventoryRoom.id == item.room_id).first()
    inventory = check_inventory_access(room.inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un élément dans un état des lieux signé"
        )
    
    # Supprimer les photos associées
    for photo in item.photos:
        try:
            if os.path.exists(photo.file_path):
                os.remove(photo.file_path)
        except Exception as e:
            print(f"Erreur lors de la suppression de la photo: {e}")
    
    db.delete(item)
    db.commit()
    
    return {"message": f"Élément '{item.name}' supprimé avec succès"}


# ==================== GESTION DES PHOTOS ====================

@router.post("/{inventory_id}/photos", response_model=InventoryPhotoOut)
async def upload_inventory_photo(
    inventory_id: int,
    file: UploadFile = File(...),
    room_id: Optional[int] = Form(None),
    caption: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo_type: Optional[str] = Form("overview"),
    position_in_room: Optional[str] = Form(None),
    angle: Optional[str] = Form(None),
    order: int = Form(1),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload une photo pour un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'ajouter des photos à un état des lieux signé"
        )
    
    # Vérifier le fichier
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension non autorisée. Extensions autorisées: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Lire le contenu du fichier
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Générer un nom de fichier unique
    unique_filename = f"{uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Sauvegarder le fichier
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )
    
    # Créer l'enregistrement en base
    photo = DetailedInventoryPhoto(
        inventory_id=inventory_id,
        room_id=room_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        mime_type=file.content_type,
        caption=caption,
        description=description,
        photo_type=photo_type,
        position_in_room=position_in_room,
        angle=angle,
        taken_at=datetime.utcnow(),
        order=order
    )
    
    db.add(photo)
    db.commit()
    db.refresh(photo)
    
    return photo


@router.post("/items/{item_id}/photos", response_model=InventoryItemPhotoOut)
async def upload_item_photo(
    item_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo_type: Optional[str] = Form("detail"),
    order: int = Form(1),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload une photo pour un élément spécifique"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    
    # Vérifier l'accès
    room = db.query(InventoryRoom).filter(InventoryRoom.id == item.room_id).first()
    inventory = check_inventory_access(room.inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'ajouter des photos à un état des lieux signé"
        )
    
    # Vérifier et sauvegarder le fichier (même logique que pour les photos d'inventaire)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension non autorisée. Extensions autorisées: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Sauvegarder le fichier
    unique_filename = f"{uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )
    
    # Créer l'enregistrement
    photo = InventoryItemPhoto(
        item_id=item_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        mime_type=file.content_type,
        caption=caption,
        description=description,
        photo_type=photo_type,
        taken_at=datetime.utcnow(),
        order=order
    )
    
    db.add(photo)
    db.commit()
    db.refresh(photo)
    
    return photo


# ==================== WORKFLOW DE SIGNATURE ====================

@router.post("/{inventory_id}/request-signature", response_model=SignatureStatusOut)
async def request_signature(
    inventory_id: int,
    signature_request: SignatureRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Demande la signature électronique d'un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    # Vérifier que l'état des lieux peut être envoyé en signature
    if inventory.status != InventoryStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="L'état des lieux doit être en cours pour demander une signature"
        )
    
    # Vérifier qu'il y a au moins une pièce avec des éléments
    rooms_count = db.query(InventoryRoom).filter(
        InventoryRoom.inventory_id == inventory_id
    ).count()
    
    if rooms_count == 0:
        raise HTTPException(
            status_code=400,
            detail="L'état des lieux doit contenir au moins une pièce"
        )
    
    # Programmer la création et envoi de la demande de signature en arrière-plan
    background_tasks.add_task(
        create_and_send_signature_request,
        inventory_id,
        signature_request,
        db
    )
    
    # Marquer l'état des lieux comme en attente de signature
    inventory.status = InventoryStatus.PENDING_SIGNATURE
    inventory.updated_at = datetime.utcnow()
    db.commit()
    
    return SignatureStatusOut(
        inventory_id=inventory_id,
        signature_request_id=None,  # Sera mis à jour par la tâche en arrière-plan
        status="PENDING",
        signing_url=None,
        signed_document_url=None,
        expires_at=None,
        error_message=None
    )


async def create_and_send_signature_request(
    inventory_id: int,
    signature_request: SignatureRequestCreate,
    db: Session
):
    """Tâche en arrière-plan pour créer et envoyer la demande de signature"""
    
    try:
        # Récupérer l'état des lieux avec toutes les données
        inventory = db.query(DetailedInventory).options(
            joinedload(DetailedInventory.rooms).joinedload(InventoryRoom.items),
            joinedload(DetailedInventory.lease).joinedload(Lease.tenant),
            joinedload(DetailedInventory.apartment).joinedload(Apartment.building)
        ).filter(DetailedInventory.id == inventory_id).first()
        
        if not inventory:
            return
        
        # Préparer les données pour le PDF
        pdf_data = {
            "type": inventory.inventory_type,
            "apartment_info": f"Appartement {inventory.apartment.apartment_number or 'N/A'}",
            "tenant_info": f"{inventory.lease.tenant.first_name} {inventory.lease.tenant.last_name}",
            "conducted_date": inventory.conducted_date.strftime("%d/%m/%Y") if inventory.conducted_date else datetime.now().strftime("%d/%m/%Y"),
            "rooms": []
        }
        
        # Ajouter les détails des pièces
        for room in inventory.rooms:
            room_data = {
                "name": room.name,
                "items": []
            }
            
            for item in room.items:
                room_data["items"].append({
                    "name": item.name,
                    "condition": item.condition,
                    "notes": item.notes or ""
                })
            
            pdf_data["rooms"].append(room_data)
        
        # Générer le PDF
        pdf_content = create_inventory_pdf(pdf_data)
        
        # Préparer les signataires
        signers = []
        
        if signature_request.include_tenant and inventory.tenant_contact_info:
            signers.append(Signer(
                name=inventory.tenant_contact_info.get("name", "Locataire"),
                email=inventory.tenant_contact_info.get("email", inventory.lease.tenant.email),
                role="tenant",
                order=1
            ))
        
        if signature_request.include_landlord and inventory.landlord_contact_info:
            signers.append(Signer(
                name=inventory.landlord_contact_info.get("name", "Propriétaire"),
                email=inventory.landlord_contact_info.get("email", "proprietaire@locappart.com"),
                role="landlord",
                order=2
            ))
        
        if signature_request.include_agent and inventory.agent_contact_info:
            signers.append(Signer(
                name=inventory.agent_contact_info.get("name", "Agent"),
                email=inventory.agent_contact_info.get("email", "agent@locappart.com"),
                role="agent",
                order=3
            ))
        
        # Créer le document à signer
        document = SignatureDocument(
            name=f"Etat_des_lieux_{inventory.inventory_type}_{inventory_id}.pdf",
            content=pdf_content,
            fields=get_signature_fields_for_inventory()
        )
        
        # Créer la demande de signature
        signature_service = create_signature_service_from_env()
        
        request = SignatureRequest(
            title=signature_request.title or f"État des lieux {inventory.inventory_type}",
            subject=signature_request.subject or f"Signature requise - État des lieux {inventory.inventory_type}",
            message=signature_request.message,
            documents=[document],
            signers=signers,
            expires_in_days=signature_request.expires_in_days,
            client_id=str(inventory_id)
        )
        
        # Envoyer la demande
        result = await signature_service.send_signature_request(request)
        
        # Mettre à jour l'état des lieux avec les résultats
        if result.success:
            inventory.signature_request_id = result.signature_request_id
            inventory.signature_status = result.status.value if result.status else None
            inventory.signature_url = result.signing_url
            
            if result.expires_at:
                # La date d'expiration peut être stockée dans les métadonnées
                pass
        else:
            inventory.signature_status = "ERROR"
            # Log de l'erreur
            audit_logger = AuditLogger(db)
            audit_logger.log_action(
                user_id=inventory.conducted_by,
                action="ERROR",
                entity_type="DETAILED_INVENTORY",
                entity_id=inventory_id,
                description=f"Erreur lors de la demande de signature pour l'état des lieux #{inventory_id}",
                details=json.dumps({
                    "error": result.error_message,
                    "inventory_id": inventory_id
                })
            )
        
        db.commit()
        
    except Exception as e:
        print(f"Erreur lors de la création de la demande de signature: {e}")
        
        # Marquer l'état des lieux en erreur
        inventory = db.query(DetailedInventory).filter(
            DetailedInventory.id == inventory_id
        ).first()
        
        if inventory:
            inventory.signature_status = "ERROR"
            inventory.status = InventoryStatus.IN_PROGRESS  # Retour à l'état précédent
            db.commit()


@router.get("/{inventory_id}/signature-status", response_model=SignatureStatusOut)
async def get_signature_status(
    inventory_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère le statut de signature d'un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    return SignatureStatusOut(
        inventory_id=inventory_id,
        signature_request_id=inventory.signature_request_id,
        status=inventory.signature_status,
        signing_url=inventory.signature_url,
        signed_document_url=inventory.signed_document_url,
        expires_at=None,  # À récupérer depuis le service de signature si nécessaire
        error_message=None
    )


# ==================== TEMPLATES ====================

@router.get("/templates", response_model=List[InventoryTemplateOut])
async def get_inventory_templates(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les templates d'état des lieux disponibles"""
    
    templates = db.query(InventoryTemplate).filter(
        (InventoryTemplate.created_by == current_user.id) | 
        (InventoryTemplate.is_public == True)
    ).order_by(InventoryTemplate.usage_count.desc()).all()
    
    return templates


@router.post("/templates", response_model=InventoryTemplateOut)
async def create_inventory_template(
    template_data: InventoryTemplateCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau template d'état des lieux"""
    
    template = InventoryTemplate(
        created_by=current_user.id,
        apartment_id=template_data.apartment_id,
        name=template_data.name,
        description=template_data.description,
        is_public=template_data.is_public,
        template_data={
            "rooms": [room.dict() for room in template_data.rooms],
            "utilities": template_data.utilities or []
        }
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.post("/{inventory_id}/apply-template/{template_id}")
async def apply_template_to_inventory(
    inventory_id: int,
    template_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Applique un template à un état des lieux existant"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    if inventory.status in [InventoryStatus.SIGNED, InventoryStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'appliquer un template à un état des lieux signé"
        )
    
    # Récupérer le template
    template = db.query(InventoryTemplate).filter(
        InventoryTemplate.id == template_id,
        (InventoryTemplate.created_by == current_user.id) | 
        (InventoryTemplate.is_public == True)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template introuvable")
    
    # Appliquer le template
    template_rooms = template.template_data.get("rooms", [])
    
    for room_data in template_rooms:
        # Créer la pièce
        room = InventoryRoom(
            inventory_id=inventory_id,
            name=room_data["name"],
            room_type=room_data["room_type"],
            order=room_data["order"]
        )
        
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Créer les éléments standards
        for item_data in room_data.get("standard_items", []):
            item = InventoryItem(
                room_id=room.id,
                name=item_data["name"],
                category=item_data["category"],
                condition=item_data.get("default_condition", "GOOD"),
                estimated_value=item_data.get("estimated_value"),
                is_mandatory=item_data.get("is_mandatory", False),
                order=len(room_data.get("standard_items", [])) + 1
            )
            
            db.add(item)
    
    db.commit()
    
    # Incrémenter le compteur d'utilisation du template
    template.usage_count += 1
    db.commit()
    
    # Marquer l'inventaire comme en cours s'il était en brouillon
    if inventory.status == InventoryStatus.DRAFT:
        inventory.status = InventoryStatus.IN_PROGRESS
        db.commit()
    
    return {"message": f"Template '{template.name}' appliqué avec succès"}


# ==================== STATISTIQUES ====================

@router.get("/stats", response_model=InventoryStats)
async def get_inventory_statistics(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques des états des lieux"""
    
    from sqlalchemy import func, extract
    
    # Statistiques générales
    total = db.query(DetailedInventory).filter(
        DetailedInventory.conducted_by == current_user.id
    ).count()
    
    # Par statut
    status_stats = db.query(
        DetailedInventory.status,
        func.count(DetailedInventory.id)
    ).filter(
        DetailedInventory.conducted_by == current_user.id
    ).group_by(DetailedInventory.status).all()
    
    by_status = {status: count for status, count in status_stats}
    
    # Par type
    type_stats = db.query(
        DetailedInventory.inventory_type,
        func.count(DetailedInventory.id)
    ).filter(
        DetailedInventory.conducted_by == current_user.id
    ).group_by(DetailedInventory.inventory_type).all()
    
    by_type = {inv_type: count for inv_type, count in type_stats}
    
    # En attente de signature
    pending_signatures = db.query(DetailedInventory).filter(
        DetailedInventory.conducted_by == current_user.id,
        DetailedInventory.status == InventoryStatus.PENDING_SIGNATURE
    ).count()
    
    # Complétés ce mois
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    completed_this_month = db.query(DetailedInventory).filter(
        DetailedInventory.conducted_by == current_user.id,
        DetailedInventory.status == InventoryStatus.COMPLETED,
        extract('month', DetailedInventory.completed_at) == current_month,
        extract('year', DetailedInventory.completed_at) == current_year
    ).count()
    
    return InventoryStats(
        total_inventories=total,
        by_status=by_status,
        by_type=by_type,
        pending_signatures=pending_signatures,
        completed_this_month=completed_this_month,
        average_duration_days=None  # À calculer si nécessaire
    )