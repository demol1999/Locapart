#!/usr/bin/env python3
"""
Test d'inscription simple pour identifier les erreurs
"""

import requests
import json

def test_normal_registration():
    """Teste l'inscription normale (email/password)"""
    
    print("=== TEST INSCRIPTION NORMALE ===\n")
    
    # Données de test
    test_user = {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "phone": "0123456789",
        "street_number": "123",
        "street_name": "Rue de Test",
        "complement": "",
        "postal_code": "12345",
        "city": "Test City",
        "country": "France"
    }
    
    try:
        print("1. Test d'inscription avec email/password:")
        response = requests.post(
            "http://localhost:8000/signup/",
            json=test_user,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ Inscription réussie")
            user_data = response.json()
            print(f"   ID utilisateur: {user_data.get('id')}")
            print(f"   Email: {user_data.get('email')}")
        else:
            print(f"   ✗ Erreur d'inscription")
            print(f"   Réponse: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("   ✗ Impossible de se connecter au serveur backend")
        print("   Assurez-vous que le serveur est démarré:")
        print("   cd backend && uvicorn main:app --reload")
        
    except Exception as e:
        print(f"   ✗ Erreur: {str(e)}")

def test_server_status():
    """Teste le statut du serveur"""
    
    print("=== TEST SERVEUR ===\n")
    
    try:
        # Test de la route racine
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"✓ Serveur accessible - Status: {response.status_code}")
        
        # Test des stats de développement
        response = requests.get("http://localhost:8000/dev/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Stats DB - Utilisateurs: {stats.get('users', 0)}")
        
    except Exception as e:
        print(f"✗ Serveur non accessible: {str(e)}")

if __name__ == "__main__":
    test_server_status()
    print()
    test_normal_registration()