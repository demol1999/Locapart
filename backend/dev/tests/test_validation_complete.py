#!/usr/bin/env python3
"""
Test complet du système de validation frontend + backend
"""

import requests
import json
import time

def test_validation_case(test_name, user_data, expected_status=422):
    """Teste un cas de validation spécifique"""
    print(f"\n=== {test_name} ===")
    
    try:
        response = requests.post(
            "http://localhost:8000/signup/",
            json=user_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print("Status attendu")
        else:
            print(f"Status inattendu (attendu: {expected_status})")
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"Erreur retournée: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Erreur text: {response.text}")
        else:
            result = response.json()
            print(f"Succes: Utilisateur cree ID={result.get('id')}")
            
    except Exception as e:
        print(f"Exception: {str(e)}")

def run_validation_tests():
    """Lance tous les tests de validation"""
    
    print("=== TESTS DE VALIDATION COMPLETS ===")
    
    # Test 1: Email invalide
    test_validation_case(
        "Email invalide",
        {
            "email": "invalid-email",
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "0123456789"
        }
    )
    
    # Test 2: Mot de passe trop court
    test_validation_case(
        "Mot de passe trop court",
        {
            "email": f"test-pwd-{int(time.time())}@example.com",
            "password": "123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "0123456789"
        }
    )
    
    # Test 3: Téléphone invalide
    test_validation_case(
        "Téléphone invalide",
        {
            "email": f"test-phone-{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "invalid-phone"
        }
    )
    
    # Test 4: Code postal invalide
    test_validation_case(
        "Code postal invalide",
        {
            "email": f"test-postal-{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "0123456789",
            "postal_code": "1234"  # Doit être 5 chiffres
        }
    )
    
    # Test 5: Champ trop long
    test_validation_case(
        "Street number trop long",
        {
            "email": f"test-long-{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "0123456789",
            "street_number": "A" * 150  # Dépasse 100 caractères
        }
    )
    
    # Test 6: Prénom vide
    test_validation_case(
        "Prénom vide",
        {
            "email": f"test-name-{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "",
            "last_name": "Doe",
            "phone": "0123456789"
        }
    )
    
    # Test 7: Données complètement valides
    test_validation_case(
        "Données valides",
        {
            "email": f"test-valid-{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "0123456789",
            "street_number": "123",
            "street_name": "Main Street",
            "complement": "Apt 4B",
            "postal_code": "75001",
            "city": "Paris",
            "country": "France"
        },
        expected_status=200
    )
    
    # Test 8: Email en double
    test_validation_case(
        "Email déjà utilisé",
        {
            "email": "test-validation@example.com",  # Email déjà utilisé dans le test précédent
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "0123456789"
        },
        expected_status=400
    )
    
    print("\n=== FIN DES TESTS ===")

if __name__ == "__main__":
    run_validation_tests()