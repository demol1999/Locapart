#!/usr/bin/env python3
"""
Debug de l'endpoint signup pour identifier l'erreur exacte
"""

from fastapi import Request
from database import SessionLocal
import models
from auth import get_password_hash
from audit_logger import AuditLogger, get_model_data
import schemas

def debug_signup_process():
    """Simule le processus d'inscription étape par étape"""
    
    print("=== DEBUG PROCESSUS INSCRIPTION ===")
    
    # Données de test similaires à celles du frontend
    user_data = {
        "email": "debug@test.com",
        "password": "password123",
        "first_name": "Debug",
        "last_name": "User", 
        "phone": "0123456789",
        "street_number": "123",
        "street_name": "Rue Debug",
        "complement": "",
        "postal_code": "75001",
        "city": "Paris",
        "country": "France"
    }
    
    db = SessionLocal()
    
    try:
        print("1. Validation des données avec Pydantic...")
        try:
            user_schema = schemas.UserCreate(**user_data)
            print(f"   OK - Email: {user_schema.email}")
        except Exception as e:
            print(f"   ERREUR Pydantic: {str(e)}")
            return
        
        print("2. Vérification email existant...")
        try:
            existing_user = db.query(models.UserAuth).filter(
                models.UserAuth.email == user_data["email"]
            ).first()
            
            if existing_user:
                print("   Utilisateur existant trouvé - suppression...")
                db.delete(existing_user)
                db.commit()
            else:
                print("   OK - Email disponible")
        except Exception as e:
            print(f"   ERREUR vérification: {str(e)}")
            return
        
        print("3. Hachage du mot de passe...")
        try:
            hashed_password = get_password_hash(user_data["password"])
            print(f"   OK - Hash généré: {hashed_password[:20]}...")
        except Exception as e:
            print(f"   ERREUR hachage: {str(e)}")
            return
        
        print("4. Création de l'objet UserAuth...")
        try:
            user_obj = models.UserAuth(
                email=user_data["email"],
                hashed_password=hashed_password,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone=user_data["phone"],
                street_number=user_data["street_number"],
                street_name=user_data["street_name"],
                complement=user_data["complement"],
                postal_code=user_data["postal_code"],
                city=user_data["city"],
                country=user_data["country"]
            )
            print("   OK - Objet UserAuth créé")
        except Exception as e:
            print(f"   ERREUR création objet: {str(e)}")
            return
        
        print("5. Ajout à la base de données...")
        try:
            db.add(user_obj)
            db.commit()
            db.refresh(user_obj)
            print(f"   OK - Utilisateur créé avec ID: {user_obj.id}")
        except Exception as e:
            print(f"   ERREUR DB commit: {str(e)}")
            db.rollback()
            return
        
        print("6. Log d'audit...")
        try:
            AuditLogger.log_crud_action(
                db=db,
                action=models.ActionType.CREATE,
                entity_type=models.EntityType.USER,
                entity_id=user_obj.id,
                user_id=user_obj.id,
                description=f"Debug inscription: {user_obj.email}",
                after_data=get_model_data(user_obj),
                request=None
            )
            print("   OK - Log d'audit créé")
        except Exception as e:
            print(f"   ERREUR log audit: {str(e)}")
        
        print("7. Nettoyage...")
        try:
            db.delete(user_obj)
            db.commit()
            print("   OK - Utilisateur de test supprimé")
        except Exception as e:
            print(f"   ERREUR nettoyage: {str(e)}")
        
        print("\n=== PROCESSUS COMPLET REUSSI ===")
        
    except Exception as e:
        print(f"\nERREUR GLOBALE: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

def check_schemas():
    """Vérifie que les schémas Pydantic sont corrects"""
    
    print("\n=== VERIFICATION SCHEMAS ===")
    
    try:
        # Test avec des données valides
        valid_data = {
            "email": "test@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
            "phone": "0123456789",
            "street_number": "123",
            "street_name": "Rue Test",
            "complement": "",
            "postal_code": "75001",
            "city": "Paris",
            "country": "France"
        }
        
        user_create = schemas.UserCreate(**valid_data)
        print("   OK - UserCreate valide")
        
        # Simuler un UserOut
        user_out_data = {
            "id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "phone": "0123456789",
            "street_number": "123",
            "street_name": "Rue Test",
            "complement": "",
            "postal_code": "75001",
            "city": "Paris",
            "country": "France"
        }
        
        user_out = schemas.UserOut(**user_out_data)
        print("   OK - UserOut valide")
        
    except Exception as e:
        print(f"   ERREUR schema: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_schemas()
    debug_signup_process()