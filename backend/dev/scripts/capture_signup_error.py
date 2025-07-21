#!/usr/bin/env python3
"""
Capture l'erreur exacte lors de l'inscription
"""

import requests
import json
import traceback

def test_signup_with_real_data():
    """Teste l'inscription avec des données réelles similaires au frontend"""
    
    print("=== TEST INSCRIPTION AVEC DONNEES REELLES ===\n")
    
    # Données exactement comme le frontend les envoie
    signup_data = {
        "email": "test@example.com",
        "password": "password123", 
        "first_name": "John",
        "last_name": "Doe",
        "phone": "0123456789",
        "street_number": "123",
        "street_name": "Main Street",
        "complement": "",
        "postal_code": "75001", 
        "city": "Paris",
        "country": "France"
    }
    
    try:
        print("1. Envoi de la requête POST /signup/...")
        print(f"   Données: {json.dumps(signup_data, indent=2)}")
        
        response = requests.post(
            "http://localhost:8000/signup/",
            json=signup_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n2. Réponse du serveur:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"   ✓ SUCCÈS!")
            user_data = response.json()
            print(f"   Utilisateur créé: ID={user_data.get('id')}, Email={user_data.get('email')}")
            
        else:
            print(f"   ✗ ERREUR!")
            print(f"   Contenu de la réponse:")
            try:
                error_data = response.json()
                print(f"   {json.dumps(error_data, indent=2)}")
            except:
                print(f"   {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("   ✗ ERREUR: Impossible de se connecter au serveur backend")
        print("   Vérifiez que le serveur est démarré avec:")
        print("   cd backend && uvicorn main:app --reload")
        
    except requests.exceptions.Timeout:
        print("   ✗ ERREUR: Timeout - le serveur ne répond pas")
        
    except Exception as e:
        print(f"   ✗ ERREUR INATTENDUE: {str(e)}")
        traceback.print_exc()

def test_server_health():
    """Teste la santé du serveur"""
    
    print("=== TEST SANTE DU SERVEUR ===\n")
    
    try:
        # Test endpoint simple
        response = requests.get("http://localhost:8000/dev/stats", timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            print("✓ Serveur accessible")
            print(f"  Utilisateurs en DB: {stats.get('users', 0)}")
            print(f"  Logs d'audit: {stats.get('audit_logs', 0)}")
        else:
            print(f"✗ Serveur répond mais erreur: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Serveur non accessible: {str(e)}")

if __name__ == "__main__":
    test_server_health()
    print()
    test_signup_with_real_data()