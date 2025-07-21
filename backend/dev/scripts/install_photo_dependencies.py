#!/usr/bin/env python3
"""
Script pour installer les dépendances de traitement d'images
"""
import subprocess
import sys

def install_pillow():
    """Installe Pillow pour le traitement d'images"""
    print("📦 Installation de Pillow...")
    
    try:
        # Installer Pillow
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        print("✅ Pillow installé avec succès")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation de Pillow: {e}")
        return False

def verify_installation():
    """Vérifie que Pillow est correctement installé"""
    print("🔍 Vérification de l'installation...")
    
    try:
        from PIL import Image, ExifTags
        import PIL
        print(f"✅ Pillow version {PIL.__version__} installé correctement")
        
        # Test rapide
        print("🧪 Test de fonctionnalité...")
        
        # Test création d'une image de test
        test_img = Image.new('RGB', (100, 100), color='red')
        print("✅ Création d'image: OK")
        
        # Test redimensionnement
        test_img.thumbnail((50, 50))
        print("✅ Redimensionnement: OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 50)
    print("📦 INSTALLATION DES DÉPENDANCES PHOTO")
    print("=" * 50)
    
    # Installer Pillow
    if not install_pillow():
        print("❌ Échec de l'installation")
        return
    
    # Vérifier l'installation
    if not verify_installation():
        print("❌ Installation échouée")
        return
    
    print("=" * 50)
    print("✅ INSTALLATION TERMINÉE AVEC SUCCÈS")
    print("=" * 50)
    print()
    print("📋 Fonctionnalités disponibles:")
    print("- Redimensionnement automatique des images")
    print("- Correction de l'orientation EXIF")
    print("- Génération de thumbnails")
    print("- Support des formats JPEG, PNG, WebP")
    print("- Extraction de métadonnées")

if __name__ == "__main__":
    main()