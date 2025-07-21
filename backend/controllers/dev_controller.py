"""
Contrôleur pour les endpoints de développement
Uniquement accessible en mode développement
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from models import UserAuth, Building, Apartment
from auth import get_current_user
from constants import get_error_message

router = APIRouter(prefix="/dev", tags=["Développement"])


@router.delete("/reset-users")
async def reset_users_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAuth = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reset complet de la base de données (mode développement uniquement)
    ⚠️ ATTENTION: Supprime TOUTES les données de façon irréversible
    """
    import os
    
    # Vérifier que nous sommes en mode développement
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(
            status_code=403, 
            detail="Endpoint disponible uniquement en mode développement"
        )
    
    try:
        # Supprimer toutes les données dans l'ordre des dépendances
        tables_to_clear = [
            "audit_logs",
            "user_sessions", 
            "email_verifications",
            "detailed_inventory_items",
            "detailed_inventories",
            "tenant_invitations",
            "documents",
            "leases",
            "tenants",
            "photos",
            "rooms",
            "apartment_user_links",
            "apartments",
            "buildings",
            "copros",
            "syndicat_copros",
            "user_subscriptions",
            "user_auth"
        ]
        
        deleted_counts = {}
        
        for table in tables_to_clear:
            try:
                result = db.execute(f"DELETE FROM {table}")
                deleted_counts[table] = result.rowcount
            except Exception as e:
                deleted_counts[table] = f"Erreur: {str(e)}"
        
        # Reset des auto-increments
        for table in tables_to_clear:
            try:
                db.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
            except Exception:
                pass  # Ignorer les erreurs pour les tables sans auto-increment
        
        db.commit()
        
        return {
            "success": True,
            "message": "Base de données réinitialisée avec succès",
            "deleted_counts": deleted_counts,
            "warning": "⚠️ TOUTES LES DONNÉES ONT ÉTÉ SUPPRIMÉES"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la réinitialisation: {str(e)}"
        )


@router.get("/stats")
async def get_database_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Statistiques de la base de données pour le développement
    """
    import os
    
    # Vérifier que nous sommes en mode développement  
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(
            status_code=403,
            detail="Endpoint disponible uniquement en mode développement"
        )
    
    try:
        stats = {}
        
        # Compter les enregistrements dans chaque table
        tables_to_count = {
            "user_auth": "Utilisateurs",
            "buildings": "Bâtiments", 
            "apartments": "Appartements",
            "apartment_user_links": "Liens Appartement-Utilisateur",
            "copros": "Copros",
            "syndicat_copros": "Syndicats",
            "photos": "Photos",
            "rooms": "Pièces",
            "tenants": "Locataires",
            "leases": "Baux",
            "documents": "Documents",
            "audit_logs": "Logs d'audit",
            "user_sessions": "Sessions utilisateur",
            "email_verifications": "Vérifications email"
        }
        
        for table, label in tables_to_count.items():
            try:
                result = db.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                stats[label] = result
            except Exception as e:
                stats[label] = f"Erreur: {str(e)}"
        
        return {
            "success": True,
            "statistics": stats,
            "environment": os.getenv("ENVIRONMENT", "unknown")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du calcul des statistiques: {str(e)}"
        )


@router.get("/health")
async def health_check(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Vérification de santé pour le développement
    """
    try:
        # Test de connexion à la base
        db.execute("SELECT 1").scalar()
        
        # Test des services essentiels
        services_status = {}
        
        # Test du service d'email
        try:
            from email_verification_service import create_verification_service
            verification_service = create_verification_service(db)
            services_status["email_service"] = "OK" if verification_service else "FAILED"
        except Exception as e:
            services_status["email_service"] = f"ERROR: {str(e)}"
        
        # Test du service OAuth
        try:
            from oauth_service import OAuthProviderFactory
            factory = OAuthProviderFactory()
            services_status["oauth_service"] = "OK"
        except Exception as e:
            services_status["oauth_service"] = f"ERROR: {str(e)}"
        
        # Test du service d'audit
        try:
            from audit_logger import AuditLogger
            services_status["audit_service"] = "OK"
        except Exception as e:
            services_status["audit_service"] = f"ERROR: {str(e)}"
        
        return {
            "success": True,
            "database": "OK",
            "services": services_status,
            "timestamp": str(datetime.utcnow())
        }
        
    except Exception as e:
        return {
            "success": False,
            "database": f"ERROR: {str(e)}",
            "timestamp": str(datetime.utcnow())
        }


@router.post("/simulate-error")
async def simulate_error(
    error_type: str = "generic",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Simule différents types d'erreurs pour tester la gestion d'erreurs
    """
    import os
    
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(
            status_code=403,
            detail="Endpoint disponible uniquement en mode développement"
        )
    
    if error_type == "database":
        # Erreur de base de données
        db.execute("SELECT * FROM table_inexistante")
    elif error_type == "validation":
        # Erreur de validation
        raise HTTPException(status_code=422, detail="Erreur de validation simulée")
    elif error_type == "permission":
        # Erreur de permission
        raise HTTPException(status_code=403, detail="Accès refusé simulé")
    elif error_type == "not_found":
        # Erreur 404
        raise HTTPException(status_code=404, detail="Ressource non trouvée simulée")
    elif error_type == "server":
        # Erreur serveur
        raise Exception("Erreur serveur simulée")
    else:
        # Erreur générique
        raise HTTPException(status_code=400, detail="Erreur générique simulée")


from datetime import datetime