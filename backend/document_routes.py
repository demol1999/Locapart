"""
Routes API pour la gestion des documents locataires et états des lieux
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import os
import shutil
from datetime import datetime
from uuid import uuid4

from database import get_db
from auth import get_current_user
from models import (
    UserAuth, TenantDocument, Inventory, InventoryPhoto, 
    Tenant, Lease, Photo, DocumentType, InventoryType
)
from schemas import (
    TenantDocumentCreate, TenantDocumentUpdate, TenantDocumentOut,
    InventoryCreate, InventoryUpdate, InventoryOut, InventoryRoomData
)
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Configuration des uploads
UPLOAD_DIR = "uploads/documents"
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

def check_document_access(document_id: int, user: UserAuth, db: Session) -> TenantDocument:
    """Vérifie que l'utilisateur a accès au document"""
    document = db.query(TenantDocument).filter(TenantDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable")
    
    if document.uploaded_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce document"
        )
    
    return document

def check_inventory_access(inventory_id: int, user: UserAuth, db: Session) -> Inventory:
    """Vérifie que l'utilisateur a accès à l'état des lieux"""
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="État des lieux introuvable")
    
    if inventory.conducted_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à cet état des lieux"
        )
    
    return inventory

@router.post("/upload", response_model=TenantDocumentOut)
async def upload_document(
    tenant_id: int = Form(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    lease_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload un document pour un locataire"""
    
    # Vérifier que le locataire existe et que l'utilisateur y a accès
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")
    
    # Vérifier l'accès via un bail
    lease = db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.created_by == current_user.id
    ).first()
    if not lease:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce locataire"
        )
    
    # Vérifier le fichier
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension de fichier non autorisée. Extensions autorisées: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Vérifier la taille
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
            detail=f"Erreur lors de la sauvegarde du fichier: {str(e)}"
        )
    
    # Créer l'enregistrement en base
    document = TenantDocument(
        tenant_id=tenant_id,
        lease_id=lease_id,
        uploaded_by=current_user.id,
        document_type=document_type,
        title=title,
        description=description,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        mime_type=file.content_type
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="DOCUMENT",
        entity_id=document.id,
        description=f"Upload du document '{title}' pour {tenant.first_name} {tenant.last_name}",
        details=json.dumps({
            "document_id": document.id,
            "tenant_id": tenant_id,
            "document_type": document_type.value,
            "filename": file.filename,
            "file_size": len(file_content)
        })
    )
    
    return document

@router.get("/tenant/{tenant_id}", response_model=List[TenantDocumentOut])
async def get_tenant_documents(
    tenant_id: int,
    document_type: Optional[DocumentType] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les documents d'un locataire"""
    
    # Vérifier l'accès au locataire
    lease = db.query(Lease).filter(
        Lease.tenant_id == tenant_id,
        Lease.created_by == current_user.id
    ).first()
    if not lease:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé à ce locataire"
        )
    
    query = db.query(TenantDocument).filter(TenantDocument.tenant_id == tenant_id)
    
    if document_type:
        query = query.filter(TenantDocument.document_type == document_type)
    
    documents = query.order_by(TenantDocument.created_at.desc()).all()
    
    return documents

@router.get("/{document_id}", response_model=TenantDocumentOut)
async def get_document(
    document_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un document spécifique"""
    
    document = check_document_access(document_id, current_user, db)
    return document

@router.put("/{document_id}", response_model=TenantDocumentOut)
async def update_document(
    document_id: int,
    document_update: TenantDocumentUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour les métadonnées d'un document"""
    
    document = check_document_access(document_id, current_user, db)
    
    # Sauvegarder les anciennes valeurs
    old_values = {
        "title": document.title,
        "description": document.description,
        "is_verified": document.is_verified
    }
    
    # Mettre à jour les champs
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(document, field):
            setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="DOCUMENT",
        entity_id=document_id,
        description=f"Modification du document '{document.title}'",
        details=json.dumps({
            "document_id": document_id,
            "old_values": old_values,
            "new_values": {
                "title": document.title,
                "description": document.description,
                "is_verified": document.is_verified
            }
        })
    )
    
    return document

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un document"""
    
    document = check_document_access(document_id, current_user, db)
    
    document_info = {
        "document_id": document_id,
        "title": document.title,
        "filename": document.filename
    }
    
    # Supprimer le fichier physique
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier: {e}")
    
    # Supprimer l'enregistrement
    db.delete(document)
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="DOCUMENT",
        entity_id=document_id,
        description=f"Suppression du document '{document.title}'",
        details=json.dumps(document_info)
    )
    
    return {"message": f"Document '{document.title}' supprimé avec succès"}

# ==================== ÉTATS DES LIEUX ====================

@router.post("/inventories/", response_model=InventoryOut)
async def create_inventory(
    inventory_data: InventoryCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un nouvel état des lieux"""
    
    # Vérifier que le bail existe et appartient à l'utilisateur
    lease = db.query(Lease).filter(
        Lease.id == inventory_data.lease_id,
        Lease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(
            status_code=404,
            detail="Bail introuvable ou accès non autorisé"
        )
    
    # Convertir les données des pièces en JSON
    rooms_data_json = None
    if inventory_data.rooms_data:
        rooms_data_json = json.dumps([room.dict() for room in inventory_data.rooms_data])
    
    # Créer l'état des lieux
    inventory = Inventory(
        lease_id=inventory_data.lease_id,
        conducted_by=current_user.id,
        inventory_type=inventory_data.inventory_type,
        conducted_date=inventory_data.conducted_date,
        tenant_present=inventory_data.tenant_present,
        landlord_present=inventory_data.landlord_present,
        agent_present=inventory_data.agent_present,
        overall_condition=inventory_data.overall_condition,
        general_notes=inventory_data.general_notes,
        tenant_comments=inventory_data.tenant_comments,
        landlord_comments=inventory_data.landlord_comments,
        rooms_data=rooms_data_json
    )
    
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="INVENTORY",
        entity_id=inventory.id,
        description=f"Création d'un état des lieux {inventory_data.inventory_type.value}",
        details=json.dumps({
            "inventory_id": inventory.id,
            "lease_id": inventory_data.lease_id,
            "inventory_type": inventory_data.inventory_type.value,
            "conducted_date": inventory_data.conducted_date.isoformat()
        })
    )
    
    return inventory

@router.get("/inventories/lease/{lease_id}", response_model=List[InventoryOut])
async def get_lease_inventories(
    lease_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les états des lieux d'un bail"""
    
    # Vérifier l'accès au bail
    lease = db.query(Lease).filter(
        Lease.id == lease_id,
        Lease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(
            status_code=404,
            detail="Bail introuvable ou accès non autorisé"
        )
    
    inventories = db.query(Inventory).filter(
        Inventory.lease_id == lease_id
    ).order_by(Inventory.conducted_date.desc()).all()
    
    return inventories

@router.get("/inventories/{inventory_id}", response_model=InventoryOut)
async def get_inventory(
    inventory_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un état des lieux spécifique"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    # Convertir les données JSON des pièces
    if inventory.rooms_data:
        try:
            rooms_data = json.loads(inventory.rooms_data)
            inventory.rooms_data = rooms_data
        except json.JSONDecodeError:
            inventory.rooms_data = []
    
    return inventory

@router.put("/inventories/{inventory_id}", response_model=InventoryOut)
async def update_inventory(
    inventory_id: int,
    inventory_update: InventoryUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    # Vérifier que l'état des lieux n'est pas finalisé
    if inventory.is_finalized:
        raise HTTPException(
            status_code=400,
            detail="Impossible de modifier un état des lieux finalisé"
        )
    
    # Mettre à jour les champs
    update_data = inventory_update.dict(exclude_unset=True)
    
    # Traitement spécial pour les données des pièces
    if 'rooms_data' in update_data and update_data['rooms_data']:
        update_data['rooms_data'] = json.dumps([room.dict() for room in update_data['rooms_data']])
    
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
        entity_type="INVENTORY",
        entity_id=inventory_id,
        description=f"Modification de l'état des lieux #{inventory_id}",
        details=json.dumps({
            "inventory_id": inventory_id,
            "is_finalized": inventory.is_finalized
        })
    )
    
    return inventory

@router.post("/inventories/{inventory_id}/finalize")
async def finalize_inventory(
    inventory_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Finalise un état des lieux (plus de modifications possibles)"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    if inventory.is_finalized:
        raise HTTPException(
            status_code=400,
            detail="Cet état des lieux est déjà finalisé"
        )
    
    inventory.is_finalized = True
    inventory.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inventory)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="INVENTORY",
        entity_id=inventory_id,
        description=f"Finalisation de l'état des lieux #{inventory_id}",
        details=json.dumps({
            "inventory_id": inventory_id,
            "finalized_at": datetime.utcnow().isoformat()
        })
    )
    
    return {"message": "État des lieux finalisé avec succès", "inventory": inventory}

@router.delete("/inventories/{inventory_id}")
async def delete_inventory(
    inventory_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un état des lieux"""
    
    inventory = check_inventory_access(inventory_id, current_user, db)
    
    if inventory.is_finalized:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un état des lieux finalisé"
        )
    
    inventory_info = {
        "inventory_id": inventory_id,
        "inventory_type": inventory.inventory_type.value,
        "lease_id": inventory.lease_id
    }
    
    db.delete(inventory)
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="INVENTORY",
        entity_id=inventory_id,
        description=f"Suppression de l'état des lieux #{inventory_id}",
        details=json.dumps(inventory_info)
    )
    
    return {"message": f"État des lieux #{inventory_id} supprimé avec succès"}

@router.get("/types/document", response_model=List[dict])
async def get_document_types():
    """Récupère la liste des types de documents disponibles"""
    
    types = [
        {"value": doc_type.value, "label": doc_type.value.replace("_", " ").title()}
        for doc_type in DocumentType
    ]
    
    return types

@router.get("/types/inventory", response_model=List[dict])
async def get_inventory_types():
    """Récupère la liste des types d'états des lieux disponibles"""
    
    types = [
        {"value": inv_type.value, "label": inv_type.value.replace("_", " ").title()}
        for inv_type in InventoryType
    ]
    
    return types