#!/usr/bin/env python3
"""
Script pour installer les dépendances Stripe
"""
import subprocess
import sys

def install_stripe():
    """Installe la librairie Stripe pour Python"""
    print("📦 Installation de la librairie Stripe...")
    
    try:
        # Installer stripe
        subprocess.check_call([sys.executable, "-m", "pip", "install", "stripe"])
        print("✅ Stripe installé avec succès")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation de Stripe: {e}")
        return False

def verify_installation():
    """Vérifie que Stripe est correctement installé"""
    print("🔍 Vérification de l'installation...")
    
    try:
        import stripe
        print(f"✅ Stripe version {stripe.version.VERSION} installé correctement")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 50)
    print("📦 INSTALLATION DES DÉPENDANCES STRIPE")
    print("=" * 50)
    
    # Installer Stripe
    if not install_stripe():
        print("❌ Échec de l'installation")
        return
    
    # Vérifier l'installation
    if not verify_installation():
        print("❌ Installation échouée")
        return
    
    print("=" * 50)
    print("✅ INSTALLATION TERMINÉE AVEC SUCCÈS")
    print("=" * 50)

if __name__ == "__main__":
    main()