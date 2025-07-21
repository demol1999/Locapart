#!/usr/bin/env python3
"""
Script de diagnostic pour la configuration OAuth
"""

import os
from database import SessionLocal
from oauth_service import OAuthProviderFactory

def diagnose_oauth_config():
    """Diagnostique la configuration OAuth"""
    
    print("=== DIAGNOSTIC OAuth CONFIGURATION ===\n")
    
    # 1. Vérifier les variables d'environnement
    print("1. Variables d'environnement:")
    env_vars = {
        "Google": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "Facebook": ["FACEBOOK_CLIENT_ID", "FACEBOOK_CLIENT_SECRET"], 
        "Microsoft": ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_TENANT_ID"]
    }
    
    for provider, vars_list in env_vars.items():
        print(f"\n   {provider}:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Masquer la valeur pour la sécurité
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"     OK {var} = {masked}")
            else:
                print(f"     MANQUE {var} = NON DEFINIE")
    
    # 2. Tester la création des providers
    print(f"\n2. Test de création des providers:")
    
    for provider in ["google", "facebook", "microsoft"]:
        try:
            oauth_provider = OAuthProviderFactory.get_provider(provider)
            print(f"   OK {provider.capitalize()}: {oauth_provider.__class__.__name__}")
            
            # Tester la génération d'URL d'autorisation
            try:
                redirect_uri = f"http://localhost:3000/auth/{provider}/callback"
                auth_url, state = oauth_provider.get_authorization_url(redirect_uri)
                print(f"     OK URL d'autorisation generee")
                print(f"     - URL: {auth_url[:100]}...")
                print(f"     - State: {state}")
            except Exception as e:
                print(f"     ERREUR generation URL: {str(e)}")
                
        except Exception as e:
            print(f"   ERREUR {provider.capitalize()}: {str(e)}")
    
    # 3. Vérifier la base de données
    print(f"\n3. Test de connexion base de données:")
    try:
        db = SessionLocal()
        print("   OK Connexion DB reussie")
        db.close()
    except Exception as e:
        print(f"   ERREUR DB: {str(e)}")
    
    # 4. URLs de redirection recommandées
    print(f"\n4. URLs de redirection a configurer dans Google Console:")
    print("   Pour le developpement local:")
    print("     - http://localhost:5173")
    print("     - http://localhost:5173/auth/google/callback")
    print("     - http://127.0.0.1:5173")
    print("     - http://127.0.0.1:5173/auth/google/callback")
    print("     - http://localhost:8000/auth/google/callback")
    print("     - http://127.0.0.1:8000/auth/google/callback")
    
    print(f"\n5. Verifications a faire dans Google Console:")
    print("   - Projet cree et OAuth consent screen configure")
    print("   - Credentials > OAuth 2.0 Client IDs cree")
    print("   - Type d'application: Application web")
    print("   - URLs de redirection autorisees ajoutees")
    print("   - Domaines autorises configures")
    
    print(f"\n=== FIN DIAGNOSTIC ===")

if __name__ == "__main__":
    diagnose_oauth_config()