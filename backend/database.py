from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Charge les variables d'environnement depuis le fichier .env
load_dotenv()

# Utilisation de MariaDB/MySQL avec le driver PyMySQL
# Récupère l'URL depuis les variables d'environnement, avec fallback
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://maria_user:monpassword@localhost/locappart_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Ajoute ça explicitement ici ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_url():
    """Retourne l'URL de la base de données"""
    return DATABASE_URL
