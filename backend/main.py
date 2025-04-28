from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import engine, get_db
import models
from auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)
import schemas
import os
import shutil
from typing import List
from uuid import uuid4
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:52388",
        "http://127.0.0.1:52388"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ---------------------- AUTH ----------------------
@app.post("/signup/", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.UserAuth).filter(models.UserAuth.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    hashed_password = get_password_hash(user.password)
    user_obj = models.UserAuth(
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        street_number=user.street_number,
        street_name=user.street_name,
        complement=user.complement,
        postal_code=user.postal_code,
        city=user.city,
        country=user.country
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj


@app.post("/login/")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.UserAuth).filter(models.UserAuth.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------- USER PROFILE ----------------------
@app.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.UserAuth = Depends(get_current_user)):
    return current_user

# ---------------------- COPROPRIÉTÉS ----------------------

@app.post("/copros/", response_model=schemas.CoproOut)
def create_copro(copro: schemas.CoproCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro_obj = models.Copro(**copro.dict())
    db.add(copro_obj)
    db.commit()
    db.refresh(copro_obj)
    return copro_obj

@app.get("/copros/", response_model=List[schemas.CoproOut])
def list_copros(db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    return db.query(models.Copro).all()

@app.get("/copros/{copro_id}", response_model=schemas.CoproOut)
def get_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro = db.query(models.Copro).filter(models.Copro.id == copro_id).first()
    if not copro:
        raise HTTPException(status_code=404, detail="Copropriété introuvable")
    return copro

@app.put("/copros/{copro_id}", response_model=schemas.CoproOut)
def update_copro(copro_id: int, copro: schemas.CoproUpdate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro_obj = db.query(models.Copro).filter(models.Copro.id == copro_id).first()
    if not copro_obj:
        raise HTTPException(status_code=404, detail="Copropriété introuvable")
    for key, value in copro.dict(exclude_unset=True).items():
        setattr(copro_obj, key, value)
    db.commit()
    db.refresh(copro_obj)
    return copro_obj

@app.delete("/copros/{copro_id}")
def delete_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    copro_obj = db.query(models.Copro).filter(models.Copro.id == copro_id).first()
    if not copro_obj:
        raise HTTPException(status_code=404, detail="Copropriété introuvable")
    db.delete(copro_obj)
    db.commit()
    return {"ok": True}

# ---------------------- SYNDICAT COPRO ----------------------

@app.post("/copros/{copro_id}/syndicat", response_model=schemas.SyndicatCoproOut)
def create_syndicat_copro(copro_id: int, syndicat: schemas.SyndicatCoproCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    if db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first():
        raise HTTPException(status_code=400, detail="Syndicat déjà existant pour cette copropriété")
    syndicat_obj = models.SyndicatCopro(**syndicat.dict(), copro_id=copro_id, user_id=current_user.id)
    db.add(syndicat_obj)
    db.commit()
    db.refresh(syndicat_obj)
    return syndicat_obj

@app.get("/copros/{copro_id}/syndicat", response_model=schemas.SyndicatCoproOut)
def get_syndicat_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    syndicat = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first()
    if not syndicat:
        raise HTTPException(status_code=404, detail="Syndicat introuvable")
    return syndicat

@app.put("/copros/{copro_id}/syndicat", response_model=schemas.SyndicatCoproOut)
def update_syndicat_copro(copro_id: int, syndicat: schemas.SyndicatCoproUpdate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    syndicat_obj = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first()
    if not syndicat_obj:
        raise HTTPException(status_code=404, detail="Syndicat introuvable")
    for key, value in syndicat.dict(exclude_unset=True).items():
        setattr(syndicat_obj, key, value)
    db.commit()
    db.refresh(syndicat_obj)
    return syndicat_obj

# Liste de tous les syndicats de copropriété
@app.get("/syndicats_copro/", response_model=List[schemas.SyndicatCoproOut])
def list_syndicats_copro(db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    # Syndicats créés par l'utilisateur
    syndicats_user = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.user_id == current_user.id)
    # Copros visibles par l'utilisateur
    # 1. Immeubles créés par l'utilisateur
    my_buildings = db.query(models.Building).filter(models.Building.user_id == current_user.id).all()
    copro_ids_from_buildings = [b.copro_id for b in my_buildings if b.copro_id]
    # 2. Copros où l'utilisateur est owner/gestionnaire d'au moins un appartement
    links = db.query(models.ApartmentUserLink).filter(models.ApartmentUserLink.user_id == current_user.id, models.ApartmentUserLink.role.in_(["owner","gestionnaire"]))
    apartment_ids = [l.apartment_id for l in links]
    building_ids = db.query(models.Apartment.building_id).filter(models.Apartment.id.in_(apartment_ids)).distinct()
    copros_from_apartments = db.query(models.Building.copro_id).filter(models.Building.id.in_(building_ids)).distinct()
    copro_ids_from_apartments = [c[0] for c in copros_from_apartments if c[0]]
    # Unifie les copro_id
    copro_ids = set(copro_ids_from_buildings) | set(copro_ids_from_apartments)
    syndicats_copros = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id.in_(copro_ids))
    # Union sans doublons
    syndicats = syndicats_user.union(syndicats_copros).all()
    return syndicats

@app.delete("/copros/{copro_id}/syndicat")
def delete_syndicat_copro(copro_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    syndicat_obj = db.query(models.SyndicatCopro).filter(models.SyndicatCopro.copro_id == copro_id).first()
    if not syndicat_obj:
        raise HTTPException(status_code=404, detail="Syndicat introuvable")
    db.delete(syndicat_obj)
    db.commit()
    return {"ok": True}

# ---------------------- BUILDINGS ----------------------

@app.get("/buildings/{building_id}", response_model=schemas.BuildingOut)
def get_building(building_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    return building

@app.post("/buildings/", response_model=schemas.BuildingOut)
def create_building(building: schemas.BuildingCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    new_building = models.Building(**building.dict(), user_id=current_user.id)
    db.add(new_building)
    db.commit()
    db.refresh(new_building)
    return new_building


@app.get("/buildings/", response_model=List[schemas.BuildingOut])
def get_my_buildings(db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    # Immeubles où l'utilisateur a un appartement
    links = db.query(models.ApartmentUserLink).filter(models.ApartmentUserLink.user_id == current_user.id).all()
    apartment_ids = [link.apartment_id for link in links]
    building_ids = db.query(models.Apartment.building_id).filter(models.Apartment.id.in_(apartment_ids)).distinct()
    # Immeubles créés par l'utilisateur
    my_buildings = db.query(models.Building).filter(models.Building.user_id == current_user.id)
    # Union des deux
    buildings = db.query(models.Building).filter(
        (models.Building.id.in_(building_ids)) | (models.Building.user_id == current_user.id)
    ).all()
    return buildings


@app.put("/buildings/{building_id}", response_model=schemas.BuildingOut)
def update_building(building_id: int, updated: schemas.BuildingCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    apartments = db.query(models.Apartment).filter(models.Apartment.building_id == building_id).all()
    links = db.query(models.ApartmentUserLink).filter(
        models.ApartmentUserLink.user_id == current_user.id,
        models.ApartmentUserLink.apartment_id.in_([a.id for a in apartments])
    ).all()
    if not links or not any(link.role in ["owner", "gestionnaire"] for link in links):
        raise HTTPException(status_code=403, detail="Pas autorisé à modifier ce bâtiment")
    for key, value in updated.dict().items():
        setattr(building, key, value)
    db.commit()
    db.refresh(building)
    return building


@app.delete("/buildings/{building_id}")
def delete_building(building_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    apartments = db.query(models.Apartment).filter(models.Apartment.building_id == building_id).all()
    if apartments:
        raise HTTPException(status_code=400, detail="Immeuble non vide, supprimez d'abord les appartements")
    db.delete(building)
    db.commit()
    return {"msg": "Immeuble supprimé avec succès"}


@app.get("/buildings/{building_id}/apartments", response_model=List[schemas.ApartmentOut])
def get_my_apartments_in_building(building_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    if building.user_id == current_user.id:
        # Propriétaire : voit tous les appartements
        apartments = db.query(models.Apartment).filter(models.Apartment.building_id == building_id).all()
    else:
        # Sinon, ne voit que ceux où il est lié
        apartments = db.query(models.Apartment).join(models.ApartmentUserLink).filter(
            models.Apartment.building_id == building_id,
            models.ApartmentUserLink.user_id == current_user.id
        ).all()
    return apartments


# ---------------------- APARTMENTS ----------------------
@app.post("/apartments/", response_model=schemas.ApartmentOut)
def create_apartment(apartment: schemas.ApartmentCreate, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    building = db.query(models.Building).filter(models.Building.id == apartment.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Immeuble introuvable")
    existing_apartments = db.query(models.Apartment).filter(models.Apartment.building_id == apartment.building_id).count()
    if existing_apartments > 0:
        # Autoriser si propriétaire de l'immeuble
        if building.user_id != current_user.id:
            links = db.query(models.ApartmentUserLink).join(models.Apartment).filter(
                models.Apartment.building_id == apartment.building_id,
                models.ApartmentUserLink.user_id == current_user.id,
                models.ApartmentUserLink.role.in_(["owner", "gestionnaire"])
            ).all()
            if not links:
                raise HTTPException(status_code=403, detail="Pas autorisé à ajouter un appartement")
    new_apartment = models.Apartment(**apartment.dict())
    db.add(new_apartment)
    db.commit()
    db.refresh(new_apartment)
    db.add(models.ApartmentUserLink(apartment_id=new_apartment.id, user_id=current_user.id, role="owner"))
    db.commit()
    return new_apartment


@app.get("/apartments/{apartment_id}/users", response_model=List[schemas.ApartmentUserFullOut])
def get_users_for_apartment(apartment_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    apartment = db.query(models.Apartment).filter_by(id=apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    current_link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=current_user.id).first()
    if not current_link:
        raise HTTPException(status_code=403, detail="Accès interdit")
    links = (
        db.query(models.ApartmentUserLink, models.UserAuth)
        .join(models.UserAuth, models.ApartmentUserLink.user_id == models.UserAuth.id)
        .filter(models.ApartmentUserLink.apartment_id == apartment_id)
        .all()
    )
    return [
        schemas.ApartmentUserFullOut(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=link.role
        )
        for link, user in links
    ]


@app.post("/apartments/{apartment_id}/roles")
def add_user_role_to_apartment(apartment_id: int, payload: schemas.RoleAssignment, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    user_id = payload.user_id
    role = payload.role
    apartment = db.query(models.Apartment).filter_by(id=apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable")
    current_link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=current_user.id).first()
    if not current_link or current_link.role != "owner":
        raise HTTPException(status_code=403, detail="Seul un propriétaire peut gérer les accès")
    if db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=user_id).first():
        raise HTTPException(status_code=400, detail="Utilisateur déjà lié")
    db.add(models.ApartmentUserLink(apartment_id=apartment_id, user_id=user_id, role=role))
    db.commit()
    return {"msg": f"Rôle {role} ajouté pour l'utilisateur {user_id}"}


@app.delete("/apartments/{apartment_id}/roles/{user_id}")
def remove_user_role_from_apartment(apartment_id: int, user_id: int, db: Session = Depends(get_db), current_user: models.UserAuth = Depends(get_current_user)):
    link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=current_user.id).first()
    if not link or link.role != "owner":
        raise HTTPException(status_code=403, detail="Seul un propriétaire peut supprimer")
    if user_id == current_user.id:
        owner_count = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, role="owner").count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Vous êtes le seul owner")
    target_link = db.query(models.ApartmentUserLink).filter_by(apartment_id=apartment_id, user_id=user_id).first()
    if not target_link:
        raise HTTPException(status_code=404, detail="Aucun lien trouvé")
    db.delete(target_link)
    db.commit()
    return {"msg": "Rôle supprimé avec succès"}


@app.post("/upload-photo/", response_model=schemas.PhotoOut)
def upload_photo(
    file: UploadFile = File(...),
    type: models.PhotoType = Form(...),
    target_id: int = Form(...),
    title: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.UserAuth = Depends(get_current_user)
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"user_{current_user.id}_{timestamp}_{uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    photo = models.Photo(filename=file_path, type=type, title=title, description=description)
    if type == models.PhotoType.building:
        if not db.query(models.Building).filter_by(id=target_id).first():
            raise HTTPException(status_code=404, detail="Immeuble non trouvé")
        photo.building_id = target_id
    elif type == models.PhotoType.apartment:
        if not db.query(models.Apartment).filter_by(id=target_id).first():
            raise HTTPException(status_code=404, detail="Appartement non trouvé")
        photo.apartment_id = target_id
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@app.get("/buildings/{building_id}/photos", response_model=List[schemas.PhotoOut])
def get_building_photos(building_id: int, db: Session = Depends(get_db)):
    return db.query(models.Photo).filter_by(building_id=building_id).all()


@app.get("/apartments/{apartment_id}/photos", response_model=List[schemas.PhotoOut])
def get_apartment_photos(apartment_id: int, db: Session = Depends(get_db)):
    return db.query(models.Photo).filter_by(apartment_id=apartment_id).all()