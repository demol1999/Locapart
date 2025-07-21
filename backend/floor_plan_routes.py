"""
Routes API pour la gestion des plans 2D
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import xml.etree.ElementTree as ET
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import UserAuth, FloorPlan, Room, Apartment, Building
from schemas import FloorPlanCreate, FloorPlanUpdate, FloorPlanOut, FloorPlanWithElements
from floor_plan_service import FloorPlanService
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/floor-plans", tags=["floor-plans"])

def check_plan_access(plan_id: int, user: UserAuth, db: Session) -> FloorPlan:
    """Vérifie que l'utilisateur a accès au plan"""
    plan = db.query(FloorPlan).filter(FloorPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    
    # Vérifier les permissions selon le contexte
    if plan.room_id:
        room = db.query(Room).options(joinedload(Room.apartment)).filter(Room.id == plan.room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Pièce associée introuvable")
        
        # TODO: Vérifier les permissions sur la pièce/appartement
        
    elif plan.apartment_id:
        apartment = db.query(Apartment).options(joinedload(Apartment.building)).filter(Apartment.id == plan.apartment_id).first()
        if not apartment:
            raise HTTPException(status_code=404, detail="Appartement associé introuvable")
        
        # TODO: Vérifier les permissions sur l'appartement
    
    # Vérifier que l'utilisateur est le créateur ou a les droits
    if plan.created_by != user.id:
        # TODO: Implémenter la vérification des permissions partagées
        pass
    
    return plan

@router.get("/", response_model=List[FloorPlanOut])
async def get_user_floor_plans(
    room_id: Optional[int] = None,
    apartment_id: Optional[int] = None,
    plan_type: Optional[str] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les plans de l'utilisateur avec filtres optionnels"""
    
    query = db.query(FloorPlan).filter(FloorPlan.created_by == current_user.id)
    
    if room_id:
        query = query.filter(FloorPlan.room_id == room_id)
    
    if apartment_id:
        query = query.filter(FloorPlan.apartment_id == apartment_id)
    
    if plan_type:
        query = query.filter(FloorPlan.type == plan_type)
    
    plans = query.order_by(FloorPlan.updated_at.desc()).all()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="READ",
        entity_type="BUILDING",  # Ou autre selon le contexte
        description=f"Consultation des plans ({len(plans)} plans)",
        details=json.dumps({
            "filters": {
                "room_id": room_id,
                "apartment_id": apartment_id,
                "plan_type": plan_type
            },
            "results_count": len(plans)
        })
    )
    
    return plans

@router.get("/{plan_id}", response_model=FloorPlanWithElements)
async def get_floor_plan(
    plan_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un plan spécifique avec ses éléments"""
    
    plan = check_plan_access(plan_id, current_user, db)
    
    # Utiliser le service pour parser les données XML et enrichir
    floor_plan_service = FloorPlanService()
    plan_with_elements = floor_plan_service.parse_plan_data(plan)
    
    return plan_with_elements

@router.post("/", response_model=FloorPlanOut)
async def create_floor_plan(
    plan_data: FloorPlanCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau plan"""
    
    # Vérifier les permissions sur le contexte (room/apartment)
    if plan_data.room_id:
        room = db.query(Room).filter(Room.id == plan_data.room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Pièce introuvable")
        # TODO: Vérifier permissions
    
    if plan_data.apartment_id:
        apartment = db.query(Apartment).filter(Apartment.id == plan_data.apartment_id).first()
        if not apartment:
            raise HTTPException(status_code=404, detail="Appartement introuvable")
        # TODO: Vérifier permissions
    
    # Convertir les éléments en XML si fournis
    floor_plan_service = FloorPlanService()
    xml_data = floor_plan_service.elements_to_xml(plan_data.elements or [])
    
    # Créer le plan
    plan = FloorPlan(
        name=plan_data.name,
        type=plan_data.type,
        room_id=plan_data.room_id,
        apartment_id=plan_data.apartment_id,
        xml_data=xml_data,
        scale=plan_data.scale,
        grid_size=plan_data.grid_size,
        created_by=current_user.id
    )
    
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Générer une miniature
    try:
        thumbnail_url = floor_plan_service.generate_thumbnail(plan)
        plan.thumbnail_url = thumbnail_url
        db.commit()
    except Exception as e:
        # Log l'erreur mais ne fait pas échouer la création
        print(f"Erreur génération miniature: {e}")
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="BUILDING",
        entity_id=plan_data.apartment_id or plan_data.room_id,
        description=f"Création du plan '{plan.name}' ({plan.type})",
        details=json.dumps({
            "plan_id": plan.id,
            "plan_type": plan.type,
            "room_id": plan.room_id,
            "apartment_id": plan.apartment_id
        })
    )
    
    return plan

@router.put("/{plan_id}", response_model=FloorPlanOut)
async def update_floor_plan(
    plan_id: int,
    plan_update: FloorPlanUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour un plan existant"""
    
    plan = check_plan_access(plan_id, current_user, db)
    
    # Sauvegarder les anciennes valeurs pour l'audit
    old_values = {
        "name": plan.name,
        "xml_data_length": len(plan.xml_data or ""),
        "scale": plan.scale,
        "grid_size": plan.grid_size
    }
    
    # Mettre à jour les champs fournis
    update_data = plan_update.dict(exclude_unset=True)
    
    # Traitement spécial pour les éléments -> XML
    if 'elements' in update_data:
        floor_plan_service = FloorPlanService()
        plan.xml_data = floor_plan_service.elements_to_xml(update_data['elements'])
        del update_data['elements']
    
    # Mettre à jour les autres champs
    for field, value in update_data.items():
        if hasattr(plan, field):
            setattr(plan, field, value)
    
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    
    # Régénérer la miniature si nécessaire
    try:
        floor_plan_service = FloorPlanService()
        thumbnail_url = floor_plan_service.generate_thumbnail(plan)
        plan.thumbnail_url = thumbnail_url
        db.commit()
    except Exception as e:
        print(f"Erreur régénération miniature: {e}")
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    new_values = {
        "name": plan.name,
        "xml_data_length": len(plan.xml_data or ""),
        "scale": plan.scale,
        "grid_size": plan.grid_size
    }
    
    audit_logger.log_action(
        user_id=current_user.id,
        action="UPDATE",
        entity_type="BUILDING",
        entity_id=plan.apartment_id or plan.room_id,
        description=f"Modification du plan '{plan.name}'",
        details=json.dumps({
            "plan_id": plan.id,
            "old_values": old_values,
            "new_values": new_values
        })
    )
    
    return plan

@router.delete("/{plan_id}")
async def delete_floor_plan(
    plan_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un plan"""
    
    plan = check_plan_access(plan_id, current_user, db)
    
    plan_name = plan.name
    plan_type = plan.type
    
    # Supprimer les fichiers associés (miniature, exports, etc.)
    floor_plan_service = FloorPlanService()
    floor_plan_service.cleanup_plan_files(plan)
    
    db.delete(plan)
    db.commit()
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="DELETE",
        entity_type="BUILDING",
        entity_id=plan.apartment_id or plan.room_id,
        description=f"Suppression du plan '{plan_name}' ({plan_type})",
        details=json.dumps({
            "plan_id": plan_id,
            "plan_name": plan_name,
            "plan_type": plan_type
        })
    )
    
    return {"message": f"Plan '{plan_name}' supprimé avec succès"}

@router.get("/{plan_id}/export/{format}")
async def export_floor_plan(
    plan_id: int,
    format: str,  # svg, png, pdf, xml
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exporte un plan dans différents formats"""
    
    plan = check_plan_access(plan_id, current_user, db)
    
    if format not in ['svg', 'png', 'pdf', 'xml']:
        raise HTTPException(status_code=400, detail="Format non supporté")
    
    floor_plan_service = FloorPlanService()
    
    try:
        if format == 'xml':
            # Export XML brut
            content = plan.xml_data or "<floorplan></floorplan>"
            media_type = "application/xml"
            filename = f"{plan.name}.xml"
            
        elif format == 'svg':
            # Conversion en SVG
            content = floor_plan_service.export_to_svg(plan)
            media_type = "image/svg+xml"
            filename = f"{plan.name}.svg"
            
        elif format == 'png':
            # Conversion en PNG
            content = floor_plan_service.export_to_png(plan)
            media_type = "image/png"
            filename = f"{plan.name}.png"
            
        elif format == 'pdf':
            # Génération PDF
            content = floor_plan_service.export_to_pdf(plan)
            media_type = "application/pdf"
            filename = f"{plan.name}.pdf"
        
        # Log de l'action
        audit_logger = AuditLogger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action="READ",
            entity_type="BUILDING",
            entity_id=plan.apartment_id or plan.room_id,
            description=f"Export du plan '{plan.name}' en {format.upper()}",
            details=json.dumps({
                "plan_id": plan.id,
                "export_format": format,
                "file_size": len(content) if isinstance(content, (str, bytes)) else 0
            })
        )
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")

@router.post("/{plan_id}/duplicate", response_model=FloorPlanOut)
async def duplicate_floor_plan(
    plan_id: int,
    new_name: Optional[str] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplique un plan existant"""
    
    original_plan = check_plan_access(plan_id, current_user, db)
    
    # Créer une copie
    duplicate_name = new_name or f"{original_plan.name} (Copie)"
    
    new_plan = FloorPlan(
        name=duplicate_name,
        type=original_plan.type,
        room_id=original_plan.room_id,
        apartment_id=original_plan.apartment_id,
        xml_data=original_plan.xml_data,
        scale=original_plan.scale,
        grid_size=original_plan.grid_size,
        created_by=current_user.id
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    # Générer une miniature pour la copie
    try:
        floor_plan_service = FloorPlanService()
        thumbnail_url = floor_plan_service.generate_thumbnail(new_plan)
        new_plan.thumbnail_url = thumbnail_url
        db.commit()
    except Exception as e:
        print(f"Erreur génération miniature: {e}")
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="BUILDING",
        entity_id=new_plan.apartment_id or new_plan.room_id,
        description=f"Duplication du plan '{original_plan.name}' → '{duplicate_name}'",
        details=json.dumps({
            "original_plan_id": plan_id,
            "new_plan_id": new_plan.id,
            "new_name": duplicate_name
        })
    )
    
    return new_plan

@router.get("/{plan_id}/thumbnail")
async def get_floor_plan_thumbnail(
    plan_id: int,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère la miniature d'un plan"""
    
    plan = check_plan_access(plan_id, current_user, db)
    
    if not plan.thumbnail_url:
        # Générer la miniature à la demande
        floor_plan_service = FloorPlanService()
        try:
            thumbnail_url = floor_plan_service.generate_thumbnail(plan)
            plan.thumbnail_url = thumbnail_url
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur génération miniature: {str(e)}")
    
    # Retourner l'URL ou rediriger vers le fichier
    return {"thumbnail_url": plan.thumbnail_url}

@router.get("/templates/{template_type}")
async def get_floor_plan_template(
    template_type: str,  # T1, T2, T3, etc.
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère un template de plan prédéfini"""
    
    floor_plan_service = FloorPlanService()
    
    try:
        template_data = floor_plan_service.get_template(template_type)
        return template_data
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du chargement du template: {str(e)}")

@router.post("/import-xml", response_model=FloorPlanOut)
async def import_floor_plan_from_xml(
    xml_content: str,
    name: str,
    plan_type: str,
    room_id: Optional[int] = None,
    apartment_id: Optional[int] = None,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Importe un plan depuis des données XML"""
    
    # Valider le XML
    try:
        ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"XML invalide: {str(e)}")
    
    # Créer le plan
    plan = FloorPlan(
        name=name,
        type=plan_type,
        room_id=room_id,
        apartment_id=apartment_id,
        xml_data=xml_content,
        scale=1.0,
        grid_size=20,
        created_by=current_user.id
    )
    
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Log de l'action
    audit_logger = AuditLogger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action="CREATE",
        entity_type="BUILDING",
        entity_id=apartment_id or room_id,
        description=f"Import XML du plan '{name}'",
        details=json.dumps({
            "plan_id": plan.id,
            "xml_length": len(xml_content),
            "plan_type": plan_type
        })
    )
    
    return plan