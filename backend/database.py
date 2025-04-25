from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Utilisation de MariaDB/MySQL avec le driver PyMySQL
# Syntaxe : mysql+pymysql://<utilisateur>:<motdepasse>@<host>/<nom_base>
DATABASE_URL = "mysql+pymysql://maria_user:monpassword@localhost/locappart_db"

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
