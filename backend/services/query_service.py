"""
Service pour les requêtes optimisées
Centralisation des requêtes complexes avec optimisations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, func

from models import (
    UserAuth, Building, Apartment, ApartmentUserLink, Copro, SyndicatCopro,
    Photo, Room, Tenant, Lease, Document, DetailedInventory
)
from enums import UserRole, PhotoType


class QueryService:
    """
    Service pour les requêtes optimisées avec lazy loading intelligent
    """
    
    @staticmethod
    def get_user_buildings_optimized(db: Session, user_id: int) -> List[Building]:
        """
        Récupère les buildings d'un utilisateur avec optimisations
        """
        return db.query(Building).join(
            Apartment, Building.id == Apartment.building_id
        ).join(
            ApartmentUserLink, Apartment.id == ApartmentUserLink.apartment_id
        ).filter(
            ApartmentUserLink.user_id == user_id
        ).options(
            selectinload(Building.apartments).selectinload(Apartment.photos),
            selectinload(Building.apartments).selectinload(Apartment.apartment_user_links),
            selectinload(Building.photos)
        ).distinct().all()
    
    @staticmethod
    def get_user_apartments_with_permissions(
        db: Session, 
        user_id: int,
        required_role: Optional[UserRole] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les appartements avec les permissions de l'utilisateur
        """
        query = db.query(
            Apartment,
            ApartmentUserLink.role,
            Building.name.label('building_name'),
            func.count(Photo.id).label('photo_count')
        ).join(
            ApartmentUserLink, Apartment.id == ApartmentUserLink.apartment_id
        ).join(
            Building, Apartment.building_id == Building.id
        ).outerjoin(
            Photo, and_(
                Photo.entity_id == Apartment.id,
                Photo.photo_type == PhotoType.apartment
            )
        ).filter(
            ApartmentUserLink.user_id == user_id
        )
        
        if required_role:
            query = query.filter(ApartmentUserLink.role == required_role)
        
        results = query.group_by(
            Apartment.id, ApartmentUserLink.role, Building.name
        ).all()
        
        return [
            {
                "apartment": apartment,
                "role": role,
                "building_name": building_name,
                "photo_count": photo_count
            }
            for apartment, role, building_name, photo_count in results
        ]
    
    @staticmethod
    def get_apartment_full_details(db: Session, apartment_id: int) -> Optional[Apartment]:
        """
        Récupère un appartement avec tous ses détails en une requête
        """
        return db.query(Apartment).filter(
            Apartment.id == apartment_id
        ).options(
            joinedload(Apartment.building),
            selectinload(Apartment.photos),
            selectinload(Apartment.rooms).selectinload(Room.photos),
            selectinload(Apartment.apartment_user_links).joinedload(ApartmentUserLink.user),
            selectinload(Apartment.tenants).filter(Tenant.status == "active"),
            selectinload(Apartment.leases).filter(Lease.status == "active"),
            selectinload(Apartment.documents)
        ).first()
    
    @staticmethod
    def get_building_statistics(db: Session, building_id: int) -> Dict[str, Any]:
        """
        Récupère les statistiques d'un building
        """
        # Compter les appartements
        apartment_count = db.query(func.count(Apartment.id)).filter(
            Apartment.building_id == building_id
        ).scalar()
        
        # Compter les photos
        photo_count = db.query(func.count(Photo.id)).join(
            Apartment, Photo.entity_id == Apartment.id
        ).filter(
            Apartment.building_id == building_id,
            Photo.photo_type == PhotoType.apartment
        ).scalar()
        
        # Compter les locataires actifs
        active_tenant_count = db.query(func.count(Tenant.id)).join(
            Apartment, Tenant.apartment_id == Apartment.id
        ).filter(
            Apartment.building_id == building_id,
            Tenant.status == "active"
        ).scalar()
        
        # Surface totale
        total_surface = db.query(func.sum(Apartment.surface)).filter(
            Apartment.building_id == building_id
        ).scalar() or 0
        
        return {
            "apartment_count": apartment_count,
            "photo_count": photo_count,
            "active_tenant_count": active_tenant_count,
            "total_surface": float(total_surface)
        }
    
    @staticmethod
    def search_apartments(
        db: Session,
        user_id: int,
        search_term: Optional[str] = None,
        min_surface: Optional[float] = None,
        max_surface: Optional[float] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        building_id: Optional[int] = None,
        has_tenants: Optional[bool] = None
    ) -> List[Apartment]:
        """
        Recherche d'appartements avec filtres multiples
        """
        query = db.query(Apartment).join(
            ApartmentUserLink, Apartment.id == ApartmentUserLink.apartment_id
        ).filter(
            ApartmentUserLink.user_id == user_id
        )
        
        if search_term:
            query = query.join(Building).filter(
                or_(
                    Apartment.name.ilike(f"%{search_term}%"),
                    Building.name.ilike(f"%{search_term}%"),
                    Apartment.description.ilike(f"%{search_term}%")
                )
            )
        
        if min_surface is not None:
            query = query.filter(Apartment.surface >= min_surface)
        
        if max_surface is not None:
            query = query.filter(Apartment.surface <= max_surface)
        
        if min_rooms is not None:
            query = query.filter(Apartment.number_of_rooms >= min_rooms)
        
        if max_rooms is not None:
            query = query.filter(Apartment.number_of_rooms <= max_rooms)
        
        if building_id is not None:
            query = query.filter(Apartment.building_id == building_id)
        
        if has_tenants is not None:
            if has_tenants:
                query = query.join(Tenant).filter(Tenant.status == "active")
            else:
                query = query.outerjoin(Tenant).filter(
                    or_(Tenant.id.is_(None), Tenant.status != "active")
                )
        
        return query.options(
            joinedload(Apartment.building),
            selectinload(Apartment.photos)
        ).distinct().all()
    
    @staticmethod
    def get_user_permissions_summary(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère un résumé des permissions d'un utilisateur
        """
        permissions = db.query(
            ApartmentUserLink.role,
            func.count(ApartmentUserLink.apartment_id).label('count')
        ).filter(
            ApartmentUserLink.user_id == user_id
        ).group_by(ApartmentUserLink.role).all()
        
        return {
            role: count for role, count in permissions
        }
    
    @staticmethod
    def get_recent_activity(
        db: Session, 
        user_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'activité récente de l'utilisateur
        """
        from audit_logger import AuditLog
        
        activities = db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()
        
        return [
            {
                "action": activity.action,
                "entity_type": activity.entity_type,
                "description": activity.description,
                "timestamp": activity.timestamp
            }
            for activity in activities
        ]
    
    @staticmethod
    def get_copro_apartments_optimized(db: Session, copro_id: int) -> List[Apartment]:
        """
        Récupère les appartements d'une copro avec optimisations
        """
        return db.query(Apartment).join(
            Building, Apartment.building_id == Building.id
        ).filter(
            Building.copro_id == copro_id
        ).options(
            joinedload(Apartment.building),
            selectinload(Apartment.photos),
            selectinload(Apartment.apartment_user_links).joinedload(ApartmentUserLink.user)
        ).all()
    
    @staticmethod
    def get_syndicat_statistics(db: Session, syndicat_id: int) -> Dict[str, Any]:
        """
        Récupère les statistiques d'un syndicat
        """
        # Compter les copros gérées
        copro_count = db.query(func.count(Copro.id)).filter(
            Copro.syndicat_copro_id == syndicat_id
        ).scalar()
        
        # Compter les buildings
        building_count = db.query(func.count(Building.id)).join(
            Copro, Building.copro_id == Copro.id
        ).filter(
            Copro.syndicat_copro_id == syndicat_id
        ).scalar()
        
        # Compter les appartements
        apartment_count = db.query(func.count(Apartment.id)).join(
            Building, Apartment.building_id == Building.id
        ).join(
            Copro, Building.copro_id == Copro.id
        ).filter(
            Copro.syndicat_copro_id == syndicat_id
        ).scalar()
        
        return {
            "copro_count": copro_count,
            "building_count": building_count,
            "apartment_count": apartment_count
        }


class CacheableQueryService:
    """
    Service pour les requêtes avec mise en cache
    """
    
    @staticmethod
    def get_user_subscription_status(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Récupère le statut d'abonnement avec cache
        """
        from models import UserSubscription
        
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id
        ).first()
        
        if not subscription:
            return {
                "type": "FREE",
                "status": "ACTIVE",
                "apartment_count": 0,
                "max_apartments": 3
            }
        
        # Compter les appartements de l'utilisateur
        apartment_count = db.query(func.count(ApartmentUserLink.apartment_id)).filter(
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.role == UserRole.owner
        ).scalar()
        
        return {
            "type": subscription.subscription_type,
            "status": subscription.status,
            "apartment_count": apartment_count,
            "max_apartments": 3 if subscription.subscription_type == "FREE" else -1
        }
    
    @staticmethod
    def get_apartment_access_check(
        db: Session, 
        user_id: int, 
        apartment_id: int
    ) -> Optional[UserRole]:
        """
        Vérifie l'accès à un appartement (cacheable)
        """
        link = db.query(ApartmentUserLink).filter(
            ApartmentUserLink.user_id == user_id,
            ApartmentUserLink.apartment_id == apartment_id
        ).first()
        
        return link.role if link else None