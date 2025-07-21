#!/usr/bin/env python3
"""
Test direct de l'inscription pour voir l'erreur complète
"""

from database import SessionLocal
import models
from auth import get_password_hash
from audit_logger import AuditLogger, get_model_data

def test_signup_direct():
    """Teste l'inscription directement via la base de données"""
    
    print("Test d'inscription directe...")
    
    db = SessionLocal()
    
    try:
        # Données de test
        test_email = "test@example.com"
        test_password = "testpassword123"
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(models.UserAuth).filter(
            models.UserAuth.email == test_email
        ).first()
        
        if existing_user:
            print(f"Utilisateur {test_email} existe déjà - suppression...")
            db.delete(existing_user)
            db.commit()
        
        # Tester le hachage du mot de passe
        print("Test du hachage du mot de passe...")
        try:
            hashed_password = get_password_hash(test_password)
            print(f"✓ Hachage réussi: {hashed_password[:20]}...")
        except Exception as e:
            print(f"✗ Erreur de hachage: {str(e)}")
            return
        
        # Créer l'utilisateur
        print("Création de l'utilisateur...")
        user_obj = models.UserAuth(
            email=test_email,
            hashed_password=hashed_password,
            first_name="Test",
            last_name="User",
            phone="0123456789",
            street_number="123",
            street_name="Rue de Test",
            complement="",
            postal_code="12345",
            city="Test City",
            country="France"
        )
        
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)
        
        print(f"✓ Utilisateur créé avec ID: {user_obj.id}")
        
        # Tester le log d'audit
        print("Test du log d'audit...")
        try:
            AuditLogger.log_crud_action(
                db=db,
                action=models.ActionType.CREATE,
                entity_type=models.EntityType.USER,
                entity_id=user_obj.id,
                user_id=user_obj.id,
                description=f"Test inscription: {user_obj.email}",
                after_data=get_model_data(user_obj),
                request=None
            )
            print("✓ Log d'audit réussi")
        except Exception as e:
            print(f"✗ Erreur log d'audit: {str(e)}")
        
        # Nettoyer
        db.delete(user_obj)
        db.commit()
        print("✓ Utilisateur de test supprimé")
        
    except Exception as e:
        print(f"✗ Erreur globale: {str(e)}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    test_signup_direct()