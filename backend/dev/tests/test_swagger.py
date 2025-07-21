#!/usr/bin/env python3
"""
Test de l'endpoint signup via requête directe comme Swagger
"""

import requests
import json

def test_signup_endpoint():
    """Teste l'endpoint signup directement"""
    
    print("Test de l'endpoint /signup/ directement")
    
    # Test avec données valides pour vérifier que ça marche
    user_data = {
        "email": "test-validation@example.com",
        "password": "testpassword123",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "0123456789",
        "street_number": "123",
        "street_name": "Test Street",
        "complement": "Apt 4B",
        "postal_code": "75001",
        "city": "Paris",
        "country": "France"
    }
    
    try:
        print(f"Envoi des donnees: {json.dumps(user_data, indent=2)}")
        
        response = requests.post(
            "http://localhost:8000/signup/",
            json=user_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCES!")
            print(f"ID utilisateur: {result.get('id')}")
            print(f"Email: {result.get('email')}")
        else:
            print("ERREUR!")
            print(f"Reponse: {response.text}")
            
            # Essayer de parser le JSON d'erreur
            try:
                error_detail = response.json()
                print(f"Detail erreur: {json.dumps(error_detail, indent=2)}")
            except:
                pass
                
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    test_signup_endpoint()