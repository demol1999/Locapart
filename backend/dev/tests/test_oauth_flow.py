#!/usr/bin/env python3
"""
Script pour tester le flow OAuth et identifier les erreurs
"""

import requests
import json
from database import SessionLocal
import models

def test_oauth_endpoints():
    """Teste les endpoints OAuth"""
    
    base_url = "http://localhost:8000"
    
    print("=== TEST OAUTH ENDPOINTS ===\n")
    
    # 1. Tester l'endpoint d'initiation Google OAuth
    print("1. Test de l'endpoint d'initiation Google OAuth:")
    try:
        response = requests.get(f"{base_url}/auth/google/login")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ URL d'autorisation générée")
            print(f"   URL: {data.get('authorization_url', 'N/A')[:100]}...")
            print(f"   State: {data.get('state', 'N/A')}")
        else:
            print(f"   ✗ Erreur: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Erreur de connexion: {str(e)}")
    
    # 2. Tester les stats de développement
    print(f"\n2. Test des stats de développement:")
    try:
        response = requests.get(f"{base_url}/dev/stats")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   Utilisateurs: {stats.get('users', 0)}")
            print(f"   Sessions: {stats.get('sessions', 0)}")
            print(f"   Logs d'audit: {stats.get('audit_logs', 0)}")
        else:
            print(f"   Erreur: {response.text}")
            
    except Exception as e:
        print(f"   Erreur de connexion: {str(e)}")
    
    # 3. Vérifier la base de données directement
    print(f"\n3. Vérification base de données:")
    try:
        db = SessionLocal()
        user_count = db.query(models.UserAuth).count()
        session_count = db.query(models.UserSession).count()
        audit_count = db.query(models.AuditLog).count()
        
        print(f"   Utilisateurs: {user_count}")
        print(f"   Sessions: {session_count}")
        print(f"   Logs d'audit: {audit_count}")
        
        # Afficher les derniers logs d'erreur
        recent_errors = db.query(models.AuditLog).filter(
            models.AuditLog.action == models.ActionType.ERROR
        ).order_by(models.AuditLog.created_at.desc()).limit(5).all()
        
        if recent_errors:
            print(f"\n   Dernières erreurs dans les logs:")
            for error in recent_errors:
                print(f"     - {error.created_at}: {error.description}")
                if error.details:
                    print(f"       Détails: {error.details[:100]}...")
        
        db.close()
        
    except Exception as e:
        print(f"   Erreur DB: {str(e)}")
    
    print(f"\n=== FIN TEST ===")

def check_server_running():
    """Vérifie si le serveur backend est en cours d'exécution"""
    
    print("=== VERIFICATION SERVEUR ===\n")
    
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"✓ Serveur backend accessible sur le port 8000")
        return True
    except requests.exceptions.ConnectionError:
        print(f"✗ Serveur backend non accessible sur le port 8000")
        print(f"  Assurez-vous que le serveur est démarré avec:")
        print(f"  cd backend && uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"✗ Erreur: {str(e)}")
        return False

if __name__ == "__main__":
    if check_server_running():
        test_oauth_endpoints()
    else:
        print("\nImpossible de tester - serveur non accessible")