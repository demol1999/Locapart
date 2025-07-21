#!/usr/bin/env python3
"""
Script de migration pour ajouter les tables Room et améliorer la table Photo
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from database import engine, SessionLocal
from models import Base, Room, Photo, RoomType, PhotoType
import models

def check_table_exists(table_name):
    """Vérifie si une table existe"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def check_column_exists(table_name, column_name):
    """Vérifie si une colonne existe dans une table"""
    inspector = inspect(engine)
    if not check_table_exists(table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_rooms_table():
    """Crée la table rooms"""
    print("📋 Migration de la table 'rooms'...")
    
    if check_table_exists('rooms'):
        print("✅ Table 'rooms' existe déjà")
        return True
    
    try:
        # Créer la table rooms
        Room.__table__.create(engine)
        print("✅ Table 'rooms' créée avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table 'rooms': {e}")
        return False

def migrate_photos_table():
    """Ajoute les nouvelles colonnes à la table photos"""
    print("📋 Migration de la table 'photos'...")
    
    db = SessionLocal()
    try:
        # Liste des nouvelles colonnes à ajouter
        new_columns = {
            'original_filename': 'VARCHAR(255)',
            'file_size': 'INTEGER',
            'width': 'INTEGER', 
            'height': 'INTEGER',
            'mime_type': 'VARCHAR(100)',
            'is_main': 'BOOLEAN DEFAULT FALSE',
            'sort_order': 'INTEGER DEFAULT 0',
            'metadata': 'TEXT',
            'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
            'room_id': 'INTEGER'
        }
        
        columns_added = 0
        
        for column_name, column_type in new_columns.items():
            if not check_column_exists('photos', column_name):
                try:
                    if column_name == 'room_id':
                        # Ajouter la colonne room_id avec contrainte de clé étrangère
                        db.execute(text(f"ALTER TABLE photos ADD COLUMN {column_name} {column_type}"))
                        db.execute(text("ALTER TABLE photos ADD CONSTRAINT fk_photos_room_id FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE"))
                    else:
                        db.execute(text(f"ALTER TABLE photos ADD COLUMN {column_name} {column_type}"))
                    
                    columns_added += 1
                    print(f"✅ Colonne '{column_name}' ajoutée")
                    
                except Exception as e:
                    print(f"⚠️  Erreur lors de l'ajout de la colonne '{column_name}': {e}")
            else:
                print(f"ℹ️  Colonne '{column_name}' existe déjà")
        
        # Mettre à jour l'enum PhotoType pour inclure 'room'
        try:
            # Vérifier si 'room' est déjà dans l'enum
            result = db.execute(text("SHOW COLUMNS FROM photos LIKE 'type'")).fetchone()
            if result and 'room' not in str(result[1]):
                db.execute(text("ALTER TABLE photos MODIFY COLUMN type ENUM('building', 'apartment', 'room')"))
                print("✅ Enum PhotoType mis à jour avec 'room'")
            else:
                print("ℹ️  Enum PhotoType déjà à jour")
                
        except Exception as e:
            print(f"⚠️  Erreur lors de la mise à jour de l'enum PhotoType: {e}")
        
        db.commit()
        print(f"✅ {columns_added} nouvelles colonnes ajoutées à la table 'photos'")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration de la table 'photos': {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_indexes():
    """Crée les index pour optimiser les performances"""
    print("📊 Création des index...")
    
    db = SessionLocal()
    try:
        indexes = [
            # Index pour la table rooms
            "CREATE INDEX IF NOT EXISTS idx_room_apartment ON rooms(apartment_id)",
            "CREATE INDEX IF NOT EXISTS idx_room_type ON rooms(room_type)",
            "CREATE INDEX IF NOT EXISTS idx_room_sort ON rooms(apartment_id, sort_order)",
            
            # Index pour la table photos
            "CREATE INDEX IF NOT EXISTS idx_photo_building ON photos(building_id)",
            "CREATE INDEX IF NOT EXISTS idx_photo_apartment ON photos(apartment_id)",
            "CREATE INDEX IF NOT EXISTS idx_photo_room ON photos(room_id)",
            "CREATE INDEX IF NOT EXISTS idx_photo_type ON photos(type)",
            "CREATE INDEX IF NOT EXISTS idx_photo_main ON photos(is_main)",
            "CREATE INDEX IF NOT EXISTS idx_photo_sort ON photos(type, sort_order)"
        ]
        
        for index_sql in indexes:
            try:
                db.execute(text(index_sql))
                index_name = index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'
                print(f"✅ Index 'idx_{index_name}' créé")
            except Exception as e:
                print(f"⚠️  Erreur lors de la création d'un index: {e}")
        
        db.commit()
        print("✅ Index créés avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des index: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_sample_rooms():
    """Crée des pièces d'exemple pour les appartements existants"""
    print("🏠 Création de pièces d'exemple...")
    
    db = SessionLocal()
    try:
        # Récupérer tous les appartements qui n'ont pas de pièces
        apartments = db.execute(text("""
            SELECT a.id, a.type_logement, a.layout 
            FROM apartments a 
            LEFT JOIN rooms r ON a.id = r.apartment_id 
            WHERE r.id IS NULL
        """)).fetchall()
        
        if not apartments:
            print("ℹ️  Aucun appartement sans pièces trouvé")
            return True
        
        print(f"📊 {len(apartments)} appartements sans pièces trouvés")
        
        rooms_created = 0
        
        for apartment_id, type_logement, layout in apartments:
            # Créer des pièces de base selon le type de logement
            sample_rooms = []
            
            if 'T1' in type_logement or 'studio' in type_logement.lower():
                sample_rooms = [
                    ('Pièce principale', RoomType.living_room, 0),
                    ('Cuisine', RoomType.kitchen, 1),
                    ('Salle de bain', RoomType.bathroom, 2)
                ]
            elif 'T2' in type_logement:
                sample_rooms = [
                    ('Salon', RoomType.living_room, 0),
                    ('Chambre', RoomType.bedroom, 1),
                    ('Cuisine', RoomType.kitchen, 2),
                    ('Salle de bain', RoomType.bathroom, 3)
                ]
            elif 'T3' in type_logement:
                sample_rooms = [
                    ('Salon', RoomType.living_room, 0),
                    ('Chambre 1', RoomType.bedroom, 1),
                    ('Chambre 2', RoomType.bedroom, 2),
                    ('Cuisine', RoomType.kitchen, 3),
                    ('Salle de bain', RoomType.bathroom, 4)
                ]
            else:
                # Type d'appartement non reconnu, créer des pièces génériques
                sample_rooms = [
                    ('Salon', RoomType.living_room, 0),
                    ('Cuisine', RoomType.kitchen, 1),
                    ('Salle de bain', RoomType.bathroom, 2)
                ]
            
            # Créer les pièces
            for room_name, room_type, sort_order in sample_rooms:
                room = Room(
                    apartment_id=apartment_id,
                    name=room_name,
                    room_type=room_type,
                    sort_order=sort_order
                )
                db.add(room)
                rooms_created += 1
        
        db.commit()
        print(f"✅ {rooms_created} pièces d'exemple créées")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des pièces d'exemple: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_migration():
    """Vérifie que la migration s'est bien déroulée"""
    print("🔍 Vérification de la migration...")
    
    db = SessionLocal()
    try:
        # Vérifier la table rooms
        room_count = db.query(Room).count()
        print(f"📊 Nombre de pièces: {room_count}")
        
        # Vérifier les nouvelles colonnes de photos
        photo_count = db.query(Photo).count()
        print(f"📷 Nombre de photos: {photo_count}")
        
        # Statistiques par type de pièce
        room_stats = db.execute(text("""
            SELECT room_type, COUNT(*) as count 
            FROM rooms 
            GROUP BY room_type 
            ORDER BY count DESC
        """)).fetchall()
        
        print("📈 Répartition par type de pièce:")
        for room_type, count in room_stats:
            print(f"  - {room_type}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False
    finally:
        db.close()

def main():
    """Fonction principale de migration"""
    print("=" * 60)
    print("🔄 MIGRATION ROOMS & PHOTOS")
    print("=" * 60)
    
    success_steps = 0
    total_steps = 5
    
    # Étape 1: Créer la table rooms
    if migrate_rooms_table():
        success_steps += 1
    
    # Étape 2: Migrer la table photos
    if migrate_photos_table():
        success_steps += 1
    
    # Étape 3: Créer les index
    if create_indexes():
        success_steps += 1
    
    # Étape 4: Créer des pièces d'exemple
    if create_sample_rooms():
        success_steps += 1
    
    # Étape 5: Vérifier la migration
    if verify_migration():
        success_steps += 1
    
    print("=" * 60)
    if success_steps == total_steps:
        print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
        print("=" * 60)
        print()
        print("📋 Prochaines étapes:")
        print("1. Redémarrer l'application backend")
        print("2. Tester les nouvelles APIs de gestion des pièces")
        print("3. Tester l'upload de photos avec sélection de pièce")
        print("4. Vérifier l'affichage des galeries organisées")
    else:
        print(f"⚠️  MIGRATION PARTIELLE ({success_steps}/{total_steps} étapes réussies)")
        print("=" * 60)
        print("Consultez les messages d'erreur ci-dessus pour plus de détails.")

if __name__ == "__main__":
    main()