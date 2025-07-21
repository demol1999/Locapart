#!/usr/bin/env python3
"""
Script de développement pour supprimer tous les utilisateurs
Usage: python dev_reset_users.py
"""

import os
import sys
from database import SessionLocal, engine
import models
from audit_logger import AuditLogger

def reset_all_users():
    """Supprime tous les utilisateurs et données associées"""
    
    # Définir l'environnement en développement
    os.environ['ENVIRONMENT'] = 'development'
    
    # Créer une session de base de données
    db = SessionLocal()
    
    try:
        print("Demarrage du reset de la base de donnees...")
        
        # Compter les données avant suppression
        user_count = db.query(models.UserAuth).count()
        session_count = db.query(models.UserSession).count()
        audit_count = db.query(models.AuditLog).count()
        apartment_link_count = db.query(models.ApartmentUserLink).count()
        
        print(f"Donnees trouvees:")
        print(f"   - Utilisateurs: {user_count}")
        print(f"   - Sessions: {session_count}")
        print(f"   - Logs d'audit: {audit_count}")
        print(f"   - Liens appartement-utilisateur: {apartment_link_count}")
        
        if user_count == 0:
            print("Aucun utilisateur a supprimer")
            return
        
        # Demander confirmation
        confirm = input(f"\nConfirmer la suppression de {user_count} utilisateurs ? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation annulee")
            return
        
        print("\nSuppression en cours...")
        
        # Supprimer dans l'ordre pour respecter les contraintes de clés étrangères
        
        # 1. Photos (peuvent référencer buildings/apartments)
        photo_count = db.query(models.Photo).count()
        if photo_count > 0:
            db.query(models.Photo).delete()
            print(f"   {photo_count} photos supprimees")
        
        # 2. Syndicats copro (référencent users et copros)
        syndicat_count = db.query(models.SyndicatCopro).count()
        if syndicat_count > 0:
            db.query(models.SyndicatCopro).delete()
            print(f"   {syndicat_count} syndicats supprimes")
        
        # 3. Liens appartement-utilisateur (AVANT les appartements)
        if apartment_link_count > 0:
            db.query(models.ApartmentUserLink).delete()
            print(f"   {apartment_link_count} liens appartement-utilisateur supprimes")
        
        # 4. Appartements (peuvent référencer buildings)
        apartment_count = db.query(models.Apartment).count()
        if apartment_count > 0:
            db.query(models.Apartment).delete()
            print(f"   {apartment_count} appartements supprimes")
        
        # 5. Buildings (référencent users)
        building_count = db.query(models.Building).count()
        if building_count > 0:
            db.query(models.Building).delete()
            print(f"   {building_count} immeubles supprimes")
        
        # 6. Copros
        copro_count = db.query(models.Copro).count()
        if copro_count > 0:
            db.query(models.Copro).delete()
            print(f"   {copro_count} copros supprimees")
        
        # 7. Sessions utilisateur
        if session_count > 0:
            db.query(models.UserSession).delete()
            print(f"   {session_count} sessions supprimees")
        
        # 8. Logs d'audit
        if audit_count > 0:
            db.query(models.AuditLog).delete()
            print(f"   {audit_count} logs d'audit supprimes")
        
        # 9. Utilisateurs (en dernier)
        db.query(models.UserAuth).delete()
        print(f"   {user_count} utilisateurs supprimes")
        
        # Valider les changements
        db.commit()
        
        print(f"\nReset termine avec succes!")
        print(f"   - {user_count} utilisateurs supprimes")
        print(f"   - {session_count} sessions supprimees")
        print(f"   - {audit_count} logs d'audit supprimes")
        print(f"   - {apartment_link_count} liens supprimes")
        
        # Vérifier que tout est supprimé
        remaining_users = db.query(models.UserAuth).count()
        print(f"\nVerification: {remaining_users} utilisateurs restants")
        
    except Exception as e:
        db.rollback()
        print(f"Erreur lors du reset: {str(e)}")
        sys.exit(1)
        
    finally:
        db.close()

if __name__ == "__main__":
    reset_all_users()