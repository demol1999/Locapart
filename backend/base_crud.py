"""
Classes de base pour les opérations CRUD
Réduction de la duplication de code pour les opérations courantes
"""
from typing import Type, TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, Request
from pydantic import BaseModel
from database import Base
from audit_logger import AuditLogger, get_model_data
from enums import ActionType, EntityType

# Types génériques pour les modèles et schémas
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseCRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Service de base pour les opérations CRUD
    Implémente les opérations courantes avec audit logging automatique
    """
    
    def __init__(
        self, 
        model: Type[ModelType], 
        entity_type: EntityType,
        entity_name: str = None
    ):
        self.model = model
        self.entity_type = entity_type
        self.entity_name = entity_name or model.__name__
    
    def create(
        self, 
        db: Session, 
        obj_in: CreateSchemaType, 
        user_id: int,
        request: Request = None
    ) -> ModelType:
        """
        Crée un nouvel objet avec audit logging
        """
        try:
            # Créer l'objet
            obj_data = obj_in.model_dump(exclude_unset=True)
            db_obj = self.model(**obj_data)
            
            db.add(db_obj)
            db.flush()  # Pour obtenir l'ID sans commit
            
            # Audit logging
            if request:
                AuditLogger.log_crud_action(
                    db=db,
                    action=ActionType.CREATE,
                    entity_type=self.entity_type,
                    entity_id=db_obj.id,
                    user_id=user_id,
                    description=f"Création de {self.entity_name.lower()}: {getattr(db_obj, 'name', db_obj.id)}",
                    after_data=get_model_data(db_obj),
                    request=request
                )
            
            db.commit()
            db.refresh(db_obj)
            return db_obj
            
        except IntegrityError as e:
            db.rollback()
            
            if request:
                AuditLogger.log_error(
                    db=db,
                    description=f"Erreur d'intégrité lors de la création de {self.entity_name.lower()}",
                    error_details=str(e),
                    request=request,
                    status_code=400
                )
            
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la création: contrainte d'intégrité violée"
            )
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """
        Récupère un objet par son ID
        """
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        filters: Dict[str, Any] = None
    ) -> List[ModelType]:
        """
        Récupère plusieurs objets avec pagination et filtres optionnels
        """
        query = db.query(self.model)
        
        # Appliquer les filtres
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def update(
        self, 
        db: Session, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType,
        user_id: int,
        request: Request = None
    ) -> ModelType:
        """
        Met à jour un objet avec audit logging
        """
        try:
            # Sauvegarder l'état avant
            before_data = get_model_data(db_obj) if request else None
            
            # Mettre à jour les champs
            obj_data = obj_in.model_dump(exclude_unset=True)
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.flush()  # Pour valider sans commit
            
            # Audit logging
            if request:
                AuditLogger.log_crud_action(
                    db=db,
                    action=ActionType.UPDATE,
                    entity_type=self.entity_type,
                    entity_id=db_obj.id,
                    user_id=user_id,
                    description=f"Modification de {self.entity_name.lower()}: {getattr(db_obj, 'name', db_obj.id)}",
                    before_data=before_data,
                    after_data=get_model_data(db_obj),
                    request=request
                )
            
            db.commit()
            db.refresh(db_obj)
            return db_obj
            
        except IntegrityError as e:
            db.rollback()
            
            if request:
                AuditLogger.log_error(
                    db=db,
                    description=f"Erreur d'intégrité lors de la modification de {self.entity_name.lower()}",
                    error_details=str(e),
                    request=request,
                    status_code=400
                )
            
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la modification: contrainte d'intégrité violée"
            )
    
    def delete(
        self, 
        db: Session, 
        id: int,
        user_id: int,
        request: Request = None
    ) -> Optional[ModelType]:
        """
        Supprime un objet avec audit logging
        """
        db_obj = self.get(db, id)
        if not db_obj:
            return None
        
        try:
            # Sauvegarder les données avant suppression
            before_data = get_model_data(db_obj) if request else None
            
            db.delete(db_obj)
            db.flush()
            
            # Audit logging
            if request:
                AuditLogger.log_crud_action(
                    db=db,
                    action=ActionType.DELETE,
                    entity_type=self.entity_type,
                    entity_id=id,
                    user_id=user_id,
                    description=f"Suppression de {self.entity_name.lower()}: {getattr(db_obj, 'name', id)}",
                    before_data=before_data,
                    request=request
                )
            
            db.commit()
            return db_obj
            
        except IntegrityError as e:
            db.rollback()
            
            if request:
                AuditLogger.log_error(
                    db=db,
                    description=f"Erreur lors de la suppression de {self.entity_name.lower()}",
                    error_details=str(e),
                    request=request,
                    status_code=400
                )
            
            raise HTTPException(
                status_code=400, 
                detail=f"Impossible de supprimer: des éléments dépendants existent"
            )


class BasePermissionMixin:
    """
    Mixin pour gérer les permissions sur les entités
    """
    
    @staticmethod
    def check_user_permission(
        db: Session,
        user_id: int,
        entity_id: int,
        required_roles: List[str] = None
    ) -> bool:
        """
        Vérifie si un utilisateur a les permissions sur une entité
        À surcharger dans les classes dérivées selon le modèle de permissions
        """
        raise NotImplementedError("Cette méthode doit être implémentée dans la classe dérivée")
    
    def get_user_entities(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Récupère les entités accessibles par un utilisateur
        À surcharger selon le modèle de permissions
        """
        raise NotImplementedError("Cette méthode doit être implémentée dans la classe dérivée")


class UserOwnedCRUDService(BaseCRUDService[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Service CRUD pour les entités possédées par un utilisateur
    """
    
    def __init__(
        self, 
        model: Type[ModelType], 
        entity_type: EntityType,
        entity_name: str = None,
        user_field: str = "user_id"
    ):
        super().__init__(model, entity_type, entity_name)
        self.user_field = user_field
    
    def get_user_entities(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Récupère les entités d'un utilisateur
        """
        return db.query(self.model).filter(
            getattr(self.model, self.user_field) == user_id
        ).offset(skip).limit(limit).all()
    
    def check_user_permission(
        self,
        db: Session,
        user_id: int,
        entity_id: int
    ) -> bool:
        """
        Vérifie si un utilisateur possède une entité
        """
        entity = self.get(db, entity_id)
        if not entity:
            return False
        
        return getattr(entity, self.user_field) == user_id


class ApartmentLinkedCRUDService(BaseCRUDService[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Service CRUD pour les entités liées aux appartements (avec permissions via ApartmentUserLink)
    """
    
    def __init__(
        self, 
        model: Type[ModelType], 
        entity_type: EntityType,
        entity_name: str = None,
        apartment_field: str = "apartment_id"
    ):
        super().__init__(model, entity_type, entity_name)
        self.apartment_field = apartment_field
    
    def check_user_permission(
        self,
        db: Session,
        user_id: int,
        entity_id: int,
        required_roles: List[str] = None
    ) -> bool:
        """
        Vérifie si un utilisateur a accès à une entité via ses permissions d'appartement
        """
        from models import ApartmentUserLink
        
        entity = self.get(db, entity_id)
        if not entity:
            return False
        
        apartment_id = getattr(entity, self.apartment_field)
        
        query = db.query(ApartmentUserLink).filter(
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.apartment_id == apartment_id
        )
        
        if required_roles:
            from enums import UserRole
            query = query.filter(ApartmentUserLink.role.in_(required_roles))
        
        return query.first() is not None
    
    def get_user_entities(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        required_roles: List[str] = None
    ) -> List[ModelType]:
        """
        Récupère les entités accessibles par un utilisateur via ses appartements
        """
        from models import ApartmentUserLink
        
        query = db.query(self.model).join(
            ApartmentUserLink,
            getattr(self.model, self.apartment_field) == ApartmentUserLink.apartment_id
        ).filter(
            ApartmentUserLink.user_id == user_id
        )
        
        if required_roles:
            query = query.filter(ApartmentUserLink.role.in_(required_roles))
        
        return query.offset(skip).limit(limit).all()