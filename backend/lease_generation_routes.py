"""
Routes API pour la génération et gestion des baux
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
from models import UserAuth, Apartment
from lease_template_models import (
    LeaseTemplate, GeneratedLease, LeaseSignature, LeaseClause,
    LeaseType, LeaseStatus
)
from lease_template_schemas import (
    LeaseTemplateCreate, LeaseTemplateUpdate, LeaseTemplateOut,
    GeneratedLeaseCreate, GeneratedLeaseUpdate, GeneratedLeaseOut,
    LeaseUploadCreate, LeaseSignatureCreate, LeaseSignatureOut,
    LeaseSignatureRequest, LeaseSignatureStatus,
    LeaseClauseCreate, LeaseClauseOut,
    LeaseGenerationRequest, LeaseGenerationResult,
    LeaseStats
)
from lease_pdf_service import create_lease_document_service
from electronic_signature_service import ElectronicSignatureServiceFactory
from audit_logger import AuditLogger

router = APIRouter(prefix="/api/lease-generation", tags=["Génération de Baux"])

# Répertoires de stockage
LEASE_TEMPLATES_DIR = "lease_templates"
GENERATED_LEASES_DIR = "generated_leases"
UPLOADED_LEASES_DIR = "uploaded_leases"
SIGNED_LEASES_DIR = "signed_leases"

# Créer les répertoires nécessaires
for directory in [LEASE_TEMPLATES_DIR, GENERATED_LEASES_DIR, UPLOADED_LEASES_DIR, SIGNED_LEASES_DIR]:
    os.makedirs(directory, exist_ok=True)


# ==================== TEMPLATES DE BAUX ====================

@router.post("/templates", response_model=LeaseTemplateOut)
async def create_lease_template(
    template: LeaseTemplateCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Créer un nouveau template de bail"""
    
    # Vérifier que l'appartement appartient à l'utilisateur (si spécifié)
    if template.apartment_id:
        apartment = db.query(Apartment).filter(
            Apartment.id == template.apartment_id
        ).first()
        
        if not apartment:
            raise HTTPException(status_code=404, detail="Appartement introuvable")
        
        # Vérifier les droits sur l'appartement
        # TODO: Implémenter la vérification des droits
    
    template_obj = LeaseTemplate(
        created_by=current_user.id,
        **template.dict()
    )
    
    db.add(template_obj)
    db.commit()
    db.refresh(template_obj)
    
    return template_obj


@router.get("/templates", response_model=List[LeaseTemplateOut])
async def list_lease_templates(
    lease_type: Optional[LeaseType] = None,
    apartment_id: Optional[int] = None,
    is_public: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Lister les templates de baux disponibles"""
    
    query = db.query(LeaseTemplate).filter(
        (LeaseTemplate.created_by == current_user.id) | 
        (LeaseTemplate.is_public == True)
    )
    
    if lease_type:
        query = query.filter(LeaseTemplate.lease_type == lease_type)
    
    if apartment_id is not None:
        query = query.filter(
            (LeaseTemplate.apartment_id == apartment_id) |
            (LeaseTemplate.apartment_id.is_(None))
        )
    
    if is_public is not None:
        query = query.filter(LeaseTemplate.is_public == is_public)
    
    templates = query.order_by(LeaseTemplate.created_at.desc()).all()
    return templates


@router.get("/templates/{template_id}", response_model=LeaseTemplateOut)
async def get_lease_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Récupérer un template de bail"""
    
    template = db.query(LeaseTemplate).filter(
        LeaseTemplate.id == template_id,
        (LeaseTemplate.created_by == current_user.id) | 
        (LeaseTemplate.is_public == True)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template introuvable")
    
    return template


@router.put("/templates/{template_id}", response_model=LeaseTemplateOut)
async def update_lease_template(
    template_id: int,
    template_update: LeaseTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Mettre à jour un template de bail"""
    
    template = db.query(LeaseTemplate).filter(
        LeaseTemplate.id == template_id,
        LeaseTemplate.created_by == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template introuvable ou pas autorisé")
    
    for key, value in template_update.dict(exclude_unset=True).items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/templates/{template_id}")
async def delete_lease_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Supprimer un template de bail"""
    
    template = db.query(LeaseTemplate).filter(
        LeaseTemplate.id == template_id,
        LeaseTemplate.created_by == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template introuvable ou pas autorisé")
    
    # Vérifier qu'aucun bail généré n'utilise ce template
    generated_count = db.query(GeneratedLease).filter(
        GeneratedLease.template_id == template_id
    ).count()
    
    if generated_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer : {generated_count} baux utilisent ce template"
        )
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template supprimé avec succès"}


# ==================== GÉNÉRATION DE BAUX ====================

@router.post("/generate", response_model=GeneratedLeaseOut)
async def generate_lease(
    lease_data: GeneratedLeaseCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Générer un nouveau bail à partir d'un template ou manuellement"""
    
    # Vérifier l'appartement
    apartment = db.query(Apartment).filter(
        Apartment.id == lease_data.apartment_id
    ).first()
    
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # TODO: Vérifier les droits sur l'appartement
    
    # Récupérer le template si spécifié
    template = None
    if lease_data.template_id:
        template = db.query(LeaseTemplate).filter(
            LeaseTemplate.id == lease_data.template_id,
            (LeaseTemplate.created_by == current_user.id) | 
            (LeaseTemplate.is_public == True)
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template introuvable")
        
        # Incrémenter le compteur d'utilisation
        template.usage_count += 1
    
    # Préparer les données du bail
    lease_dict = lease_data.dict()
    
    # Ajouter les informations de l'appartement
    lease_dict['apartment_data'] = {
        'address': apartment.address,
        'postal_code': apartment.postal_code,
        'city': apartment.city,
        'apartment_type': apartment.apartment_type,
        'surface_area': apartment.surface_area,
        'room_count': apartment.room_count,
        'floor': apartment.floor,
        'building_year': getattr(apartment, 'building_year', None)
    }
    
    # Calculer la date de fin
    end_date = None
    if lease_data.start_date and lease_data.duration_months:
        start_date = lease_data.start_date
        end_year = start_date.year + (lease_data.duration_months // 12)
        end_month = start_date.month + (lease_data.duration_months % 12)
        
        if end_month > 12:
            end_year += 1
            end_month -= 12
        
        try:
            end_date = start_date.replace(year=end_year, month=end_month)
        except ValueError:
            end_date = start_date.replace(year=end_year, month=end_month, day=28)
    
    # Créer le bail généré
    generated_lease = GeneratedLease(
        template_id=lease_data.template_id,
        created_by=current_user.id,
        apartment_id=lease_data.apartment_id,
        lease_type=lease_data.lease_type,
        title=lease_data.title,
        lease_data=lease_dict,
        tenant_preferences=lease_data.tenant_preferences.dict() if lease_data.tenant_preferences else None,
        monthly_rent=lease_data.financial_terms.monthly_rent,
        charges=lease_data.financial_terms.charges,
        deposit=lease_data.financial_terms.deposit,
        fees=lease_data.financial_terms.agency_fees,
        start_date=lease_data.start_date,
        end_date=end_date,
        duration_months=lease_data.duration_months,
        status=LeaseStatus.DRAFT
    )
    
    db.add(generated_lease)
    db.commit()
    db.refresh(generated_lease)
    
    # Log de création
    AuditLogger.log_crud_action(
        db=db,
        action="CREATE",
        entity_type="LEASE",
        entity_id=generated_lease.id,
        user_id=current_user.id,
        description=f"Création du bail: {generated_lease.title}"
    )
    
    return generated_lease


@router.get("/leases", response_model=List[GeneratedLeaseOut])
async def list_generated_leases(
    apartment_id: Optional[int] = None,
    status: Optional[LeaseStatus] = None,
    lease_type: Optional[LeaseType] = None,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Lister les baux générés"""
    
    query = db.query(GeneratedLease).filter(
        GeneratedLease.created_by == current_user.id
    )
    
    if apartment_id:
        query = query.filter(GeneratedLease.apartment_id == apartment_id)
    
    if status:
        query = query.filter(GeneratedLease.status == status)
    
    if lease_type:
        query = query.filter(GeneratedLease.lease_type == lease_type)
    
    leases = query.order_by(GeneratedLease.created_at.desc()).all()
    return leases


@router.get("/leases/{lease_id}", response_model=GeneratedLeaseOut)
async def get_generated_lease(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Récupérer un bail généré"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    return lease


@router.put("/leases/{lease_id}", response_model=GeneratedLeaseOut)
async def update_generated_lease(
    lease_id: int,
    lease_update: GeneratedLeaseUpdate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Mettre à jour un bail généré"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    # Ne pas permettre la modification si déjà signé
    if lease.status in [LeaseStatus.FULLY_SIGNED, LeaseStatus.ACTIVE]:
        raise HTTPException(
            status_code=400, 
            detail="Impossible de modifier un bail signé ou actif"
        )
    
    # Mettre à jour les champs
    update_data = lease_update.dict(exclude_unset=True)
    
    # Mettre à jour lease_data si nécessaire
    if any(key in update_data for key in ['landlord_info', 'tenant_info', 'guarantor_info', 'financial_terms']):
        lease_data = lease.lease_data.copy()
        
        for key in ['landlord_info', 'tenant_info', 'guarantor_info']:
            if key in update_data:
                lease_data[key] = update_data.pop(key).dict()
        
        if 'financial_terms' in update_data:
            financial_terms = update_data.pop('financial_terms')
            lease_data['financial_terms'] = financial_terms.dict()
            
            # Mettre à jour aussi les champs directs
            lease.monthly_rent = financial_terms.monthly_rent
            lease.charges = financial_terms.charges
            lease.deposit = financial_terms.deposit
            lease.fees = financial_terms.agency_fees
        
        lease.lease_data = lease_data
    
    # Mettre à jour les autres champs
    for key, value in update_data.items():
        if hasattr(lease, key):
            setattr(lease, key, value)
    
    # Recalculer la date de fin si nécessaire
    if lease_update.start_date or lease_update.duration_months:
        start_date = lease_update.start_date or lease.start_date
        duration_months = lease_update.duration_months or lease.duration_months
        
        if start_date and duration_months:
            end_year = start_date.year + (duration_months // 12)
            end_month = start_date.month + (duration_months % 12)
            
            if end_month > 12:
                end_year += 1
                end_month -= 12
            
            try:
                lease.end_date = start_date.replace(year=end_year, month=end_month)
            except ValueError:
                lease.end_date = start_date.replace(year=end_year, month=end_month, day=28)
    
    db.commit()
    db.refresh(lease)
    
    return lease


@router.delete("/leases/{lease_id}")
async def delete_generated_lease(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Supprimer un bail généré"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    # Ne pas permettre la suppression si signé ou actif
    if lease.status in [LeaseStatus.FULLY_SIGNED, LeaseStatus.ACTIVE]:
        raise HTTPException(
            status_code=400, 
            detail="Impossible de supprimer un bail signé ou actif"
        )
    
    # Supprimer les fichiers associés
    if lease.pdf_document_path and os.path.exists(lease.pdf_document_path):
        os.remove(lease.pdf_document_path)
    
    if lease.uploaded_document_path and os.path.exists(lease.uploaded_document_path):
        os.remove(lease.uploaded_document_path)
    
    if lease.signed_document_path and os.path.exists(lease.signed_document_path):
        os.remove(lease.signed_document_path)
    
    db.delete(lease)
    db.commit()
    
    return {"message": "Bail supprimé avec succès"}


# ==================== GÉNÉRATION DE DOCUMENTS ====================

@router.post("/leases/{lease_id}/generate-pdf", response_model=LeaseGenerationResult)
async def generate_lease_pdf(
    lease_id: int,
    generation_request: LeaseGenerationRequest,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Générer le PDF d'un bail"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    try:
        # Utiliser le service de génération de documents
        document_service = create_lease_document_service()
        
        if not document_service.validate_lease_data(lease.lease_data, generation_request.format):
            raise HTTPException(
                status_code=400, 
                detail="Données du bail incomplètes pour la génération"
            )
        
        # Générer le document
        result = document_service.generate_lease_document(
            lease_data=lease.lease_data,
            format=generation_request.format,
            output_dir=GENERATED_LEASES_DIR
        )
        
        # Mettre à jour le bail avec les informations du document
        lease.pdf_document_path = result['file_path']
        lease.pdf_document_hash = result['file_hash']
        lease.pdf_document_size = result['file_size']
        lease.generated_at = result['generated_at']
        lease.status = LeaseStatus.GENERATED
        
        db.commit()
        
        # Créer l'URL de téléchargement
        file_url = f"/api/lease-generation/leases/{lease_id}/download"
        
        return LeaseGenerationResult(
            lease_id=lease_id,
            format=generation_request.format,
            file_url=file_url,
            file_size=result['file_size'],
            generated_at=result['generated_at']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération: {str(e)}")


@router.get("/leases/{lease_id}/download")
async def download_lease_document(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Télécharger le document d'un bail"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    # Déterminer le fichier à télécharger
    file_path = None
    filename = None
    
    if lease.signed_document_path and os.path.exists(lease.signed_document_path):
        file_path = lease.signed_document_path
        filename = f"bail_signe_{lease_id}.pdf"
    elif lease.pdf_document_path and os.path.exists(lease.pdf_document_path):
        file_path = lease.pdf_document_path
        filename = f"bail_{lease_id}.pdf"
    elif lease.uploaded_document_path and os.path.exists(lease.uploaded_document_path):
        file_path = lease.uploaded_document_path
        filename = lease.original_filename or f"bail_upload_{lease_id}.pdf"
    
    if not file_path:
        raise HTTPException(status_code=404, detail="Aucun document disponible")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        file_path, 
        filename=filename,
        media_type='application/pdf'
    )


# ==================== UPLOAD DE BAUX EXISTANTS ====================

@router.post("/upload", response_model=GeneratedLeaseOut)
async def upload_existing_lease(
    file: UploadFile = File(...),
    apartment_id: int = Form(...),
    lease_type: LeaseType = Form(...),
    title: str = Form(...),
    monthly_rent: Optional[float] = Form(None),
    start_date: Optional[str] = Form(None),
    duration_months: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Upload d'un bail existant (PDF ou image)"""
    
    # Vérifier l'appartement
    apartment = db.query(Apartment).filter(
        Apartment.id == apartment_id
    ).first()
    
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    
    # Vérifier le type de fichier
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Type de fichier non supporté: {file.content_type}"
        )
    
    # Générer un nom de fichier unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"upload_{current_user.id}_{timestamp}_{uuid4().hex[:8]}{file_extension}"
    file_path = os.path.join(UPLOADED_LEASES_DIR, unique_filename)
    
    # Sauvegarder le fichier
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )
    
    # Convertir start_date si fourni
    parsed_start_date = None
    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide")
    
    # Créer l'enregistrement de bail
    generated_lease = GeneratedLease(
        created_by=current_user.id,
        apartment_id=apartment_id,
        lease_type=lease_type,
        title=title,
        lease_data={
            'title': title,
            'lease_type': lease_type,
            'description': description,
            'apartment_data': {
                'address': apartment.address,
                'postal_code': apartment.postal_code,
                'city': apartment.city
            }
        },
        monthly_rent=monthly_rent,
        start_date=parsed_start_date,
        duration_months=duration_months,
        is_uploaded=True,
        original_filename=file.filename,
        uploaded_document_path=file_path,
        status=LeaseStatus.GENERATED
    )
    
    db.add(generated_lease)
    db.commit()
    db.refresh(generated_lease)
    
    return generated_lease


# ==================== SIGNATURE ÉLECTRONIQUE ====================

@router.post("/leases/{lease_id}/request-signature", response_model=LeaseSignatureStatus)
async def request_lease_signature(
    lease_id: int,
    signature_request: LeaseSignatureRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Demander la signature électronique d'un bail"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    if lease.status not in [LeaseStatus.GENERATED, LeaseStatus.DRAFT]:
        raise HTTPException(
            status_code=400, 
            detail="Le bail doit être généré avant de demander la signature"
        )
    
    # Vérifier qu'un document existe
    if not lease.pdf_document_path and not lease.uploaded_document_path:
        raise HTTPException(
            status_code=400, 
            detail="Aucun document à signer. Générez d'abord le PDF ou uploadez un document."
        )
    
    try:
        # Créer le service de signature
        signature_service = ElectronicSignatureServiceFactory.create_service()
        
        # Préparer le document à signer
        document_path = lease.pdf_document_path or lease.uploaded_document_path
        
        # Créer les enregistrements de signature
        signatures = []
        for signer_data in signature_request.signers:
            signature = LeaseSignature(
                lease_id=lease_id,
                signer_name=signer_data.signer_name,
                signer_email=signer_data.signer_email,
                signer_role=signer_data.signer_role,
                signer_phone=signer_data.signer_phone,
                signing_order=signer_data.signing_order,
                status="PENDING"
            )
            signatures.append(signature)
        
        db.add_all(signatures)
        db.commit()
        
        # Préparer la demande de signature
        from electronic_signature_service import SignatureRequest as ESignRequest, SignerInfo
        
        signers = [
            SignerInfo(
                name=sig.signer_name,
                email=sig.signer_email,
                role=sig.signer_role,
                order=sig.signing_order
            )
            for sig in signatures
        ]
        
        esign_request = ESignRequest(
            document_path=document_path,
            title=signature_request.title or lease.title,
            subject=signature_request.subject or f"Signature du bail: {lease.title}",
            message=signature_request.message or "Veuillez signer ce document de bail.",
            signers=signers,
            expires_in_days=signature_request.expires_in_days
        )
        
        # Envoyer la demande de signature
        result = await signature_service.send_signature_request(esign_request)
        
        if result.success:
            # Mettre à jour le bail
            lease.signature_request_id = result.request_id
            lease.signature_status = "PENDING"
            lease.signature_url = result.signing_url
            lease.status = LeaseStatus.PENDING_SIGNATURE
            
            # Mettre à jour les signatures avec les URLs
            for signature, signer_url in zip(signatures, result.signer_urls or []):
                signature.signature_url = signer_url
                signature.invitation_sent_at = datetime.now()
            
            db.commit()
            
            return LeaseSignatureStatus(
                lease_id=lease_id,
                signature_request_id=result.request_id,
                status="PENDING",
                signing_url=result.signing_url,
                expires_at=result.expires_at,
                total_signers=len(signatures),
                signed_count=0,
                pending_count=len(signatures)
            )
        else:
            # Supprimer les signatures créées en cas d'erreur
            for signature in signatures:
                db.delete(signature)
            db.commit()
            
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors de l'envoi de la demande de signature: {result.error_message}"
            )
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la demande de signature: {str(e)}"
        )


@router.get("/leases/{lease_id}/signature-status", response_model=LeaseSignatureStatus)
async def get_lease_signature_status(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Récupérer le statut de signature d'un bail"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    signatures = db.query(LeaseSignature).filter(
        LeaseSignature.lease_id == lease_id
    ).all()
    
    signed_count = len([s for s in signatures if s.status == "SIGNED"])
    pending_count = len([s for s in signatures if s.status == "PENDING"])
    
    return LeaseSignatureStatus(
        lease_id=lease_id,
        signature_request_id=lease.signature_request_id,
        status=lease.signature_status,
        signing_url=lease.signature_url,
        signed_document_url=lease.signed_document_url,
        total_signers=len(signatures),
        signed_count=signed_count,
        pending_count=pending_count
    )


@router.get("/leases/{lease_id}/signatures", response_model=List[LeaseSignatureOut])
async def get_lease_signatures(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Récupérer les signatures d'un bail"""
    
    lease = db.query(GeneratedLease).filter(
        GeneratedLease.id == lease_id,
        GeneratedLease.created_by == current_user.id
    ).first()
    
    if not lease:
        raise HTTPException(status_code=404, detail="Bail introuvable")
    
    signatures = db.query(LeaseSignature).filter(
        LeaseSignature.lease_id == lease_id
    ).order_by(LeaseSignature.signing_order).all()
    
    return signatures


# ==================== CLAUSES RÉUTILISABLES ====================

@router.post("/clauses", response_model=LeaseClauseOut)
async def create_lease_clause(
    clause: LeaseClauseCreate,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Créer une nouvelle clause de bail"""
    
    clause_obj = LeaseClause(
        created_by=current_user.id,
        **clause.dict()
    )
    
    db.add(clause_obj)
    db.commit()
    db.refresh(clause_obj)
    
    return clause_obj


@router.get("/clauses", response_model=List[LeaseClauseOut])
async def list_lease_clauses(
    category: Optional[str] = None,
    lease_type: Optional[LeaseType] = None,
    is_public: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Lister les clauses disponibles"""
    
    query = db.query(LeaseClause).filter(
        (LeaseClause.created_by == current_user.id) | 
        (LeaseClause.is_public == True)
    )
    
    if category:
        query = query.filter(LeaseClause.category == category)
    
    if is_public is not None:
        query = query.filter(LeaseClause.is_public == is_public)
    
    clauses = query.order_by(LeaseClause.category, LeaseClause.title).all()
    
    # Filtrer par type de bail si spécifié
    if lease_type:
        filtered_clauses = []
        for clause in clauses:
            applies_to = clause.applies_to_types or []
            if not applies_to or lease_type in applies_to:
                filtered_clauses.append(clause)
        clauses = filtered_clauses
    
    return clauses


# ==================== STATISTIQUES ====================

@router.get("/stats", response_model=LeaseStats)
async def get_lease_stats(
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
):
    """Récupérer les statistiques des baux"""
    
    from sqlalchemy import func
    
    # Statistiques par statut
    stats_by_status = db.query(
        GeneratedLease.status,
        func.count(GeneratedLease.id).label('count')
    ).filter(
        GeneratedLease.created_by == current_user.id
    ).group_by(GeneratedLease.status).all()
    
    # Statistiques par type
    stats_by_type = db.query(
        GeneratedLease.lease_type,
        func.count(GeneratedLease.id).label('count')
    ).filter(
        GeneratedLease.created_by == current_user.id
    ).group_by(GeneratedLease.lease_type).all()
    
    # Baux en attente de signature
    pending_signatures = db.query(GeneratedLease).filter(
        GeneratedLease.created_by == current_user.id,
        GeneratedLease.status == LeaseStatus.PENDING_SIGNATURE
    ).count()
    
    # Baux signés ce mois
    from datetime import datetime, timedelta
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    signed_this_month = db.query(GeneratedLease).filter(
        GeneratedLease.created_by == current_user.id,
        GeneratedLease.status.in_([LeaseStatus.FULLY_SIGNED, LeaseStatus.ACTIVE]),
        GeneratedLease.signed_at >= start_of_month
    ).count()
    
    # Loyer moyen et chiffre d'affaires
    rent_stats = db.query(
        func.avg(GeneratedLease.monthly_rent).label('avg_rent'),
        func.sum(GeneratedLease.monthly_rent).label('total_revenue')
    ).filter(
        GeneratedLease.created_by == current_user.id,
        GeneratedLease.status == LeaseStatus.ACTIVE,
        GeneratedLease.monthly_rent.isnot(None)
    ).first()
    
    return LeaseStats(
        total_leases=sum(stat.count for stat in stats_by_status),
        by_status={stat.status: stat.count for stat in stats_by_status},
        by_type={stat.lease_type: stat.count for stat in stats_by_type},
        pending_signatures=pending_signatures,
        signed_this_month=signed_this_month,
        average_rent=float(rent_stats.avg_rent) if rent_stats.avg_rent else None,
        total_revenue=float(rent_stats.total_revenue) if rent_stats.total_revenue else None
    )