from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from database import Base
import enum
import datetime

# Enum pour les rôles utilisateurs
class UserRole(str, enum.Enum):
    owner = "owner"
    gestionnaire = "gestionnaire"
    lecteur = "lecteur"

# Enum pour le type de photo
class PhotoType(str, enum.Enum):
    building = "building"
    apartment = "apartment"

class UserAuth(Base):
    __tablename__ = "user_auth"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(50))

    street_number = Column(String(20))
    street_name = Column(String(255))
    complement = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))

    apartment_links = relationship("ApartmentUserLink", back_populates="user")

class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    street_number = Column(String(20))
    street_name = Column(String(255))
    complement = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))
    floors = Column(Integer)
    is_copro = Column(Boolean)
    user_id = Column(Integer, ForeignKey("user_auth.id"))  # Créateur de l'immeuble
    copro_id = Column(Integer, ForeignKey("copros.id"), nullable=True)

    apartments = relationship("Apartment", back_populates="building")
    photos = relationship("Photo", back_populates="building")
    copro = relationship("Copro", back_populates="buildings")

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    type_logement = Column(String(50))
    layout = Column(String(50))
    floor = Column(Integer, nullable=True)
    building_id = Column(Integer, ForeignKey("buildings.id"))

    building = relationship("Building", back_populates="apartments")
    user_links = relationship("ApartmentUserLink", back_populates="apartment")
    photos = relationship("Photo", back_populates="apartment")

class ApartmentUserLink(Base):
    __tablename__ = "apartment_user_link"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_auth.id"))
    apartment_id = Column(Integer, ForeignKey("apartments.id"))
    role = Column(Enum(UserRole))

    user = relationship("UserAuth", back_populates="apartment_links")
    apartment = relationship("Apartment", back_populates="user_links")

class Copro(Base):
    __tablename__ = "copros"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(255))
    adresse_rue = Column(String(255))
    adresse_code_postal = Column(String(20))
    adresse_ville = Column(String(100))
    annee_construction = Column(Integer)
    nb_batiments = Column(Integer)
    nb_lots_total = Column(Integer)
    nb_lots_principaux = Column(Integer)
    nb_lots_secondaires = Column(Integer)
    surface_totale_m2 = Column(Integer)
    type_construction = Column(String(100))
    nb_etages = Column(Integer)
    ascenseur = Column(Boolean)
    nb_ascenseurs = Column(Integer)
    chauffage_collectif_type = Column(String(100))
    chauffage_individuel_type = Column(String(100))
    clim_centralisee = Column(Boolean)
    eau_chaude_collective = Column(Boolean)
    isolation_thermique = Column(String(255))
    isolation_annee = Column(Integer)
    rt2012_re2020 = Column(Boolean)
    accessibilite_pmr = Column(Boolean)
    toiture_type = Column(String(100))
    toiture_materiaux = Column(String(100))
    gardien = Column(Boolean)
    local_velos = Column(Boolean)
    parkings_ext = Column(Boolean)
    nb_parkings_ext = Column(Integer)
    parkings_int = Column(Boolean)
    nb_parkings_int = Column(Integer)
    caves = Column(Boolean)
    nb_caves = Column(Integer)
    espaces_verts = Column(Boolean)
    jardins_partages = Column(Boolean)
    piscine = Column(Boolean)
    salle_sport = Column(Boolean)
    aire_jeux = Column(Boolean)
    salle_reunion = Column(Boolean)
    dpe_collectif = Column(String(1))  # A-G
    audit_energetique = Column(Boolean)
    audit_energetique_date = Column(String(20))
    energie_utilisee = Column(String(100))
    panneaux_solaires = Column(Boolean)
    bornes_recharge = Column(Boolean)

    # Relations
    buildings = relationship("Building", back_populates="copro")
    syndicat = relationship("SyndicatCopro", uselist=False, back_populates="copro")

class SyndicatCopro(Base):
    __tablename__ = "syndicats_copro"

    id = Column(Integer, primary_key=True, index=True)
    copro_id = Column(Integer, ForeignKey("copros.id"))
    user_id = Column(Integer, ForeignKey("user_auth.id"))  # Créateur du syndicat
    statut_juridique = Column(String(100))
    date_creation = Column(String(20))
    reglement_copro = Column(Boolean)
    carnet_entretien = Column(Boolean)
    nom_syndic = Column(String(255))
    type_syndic = Column(String(50))
    societe_syndic = Column(String(255))
    date_derniere_ag = Column(String(20))
    assurance_compagnie = Column(String(255))
    assurance_num_police = Column(String(100))
    assurance_validite = Column(String(20))
    procedures_judiciaires = Column(Boolean)
    procedures_details = Column(String(255))
    budget_annuel_previsionnel = Column(Integer)
    charges_annuelles_par_lot = Column(Integer)
    charges_speciales = Column(Integer)
    emprunt_collectif = Column(Boolean)
    emprunt_montant = Column(Integer)
    emprunt_echeance = Column(String(20))
    taux_impayes_charges = Column(Integer)
    fonds_roulement = Column(Integer)
    fonds_travaux = Column(Integer)
    travaux_votes = Column(String(1000))
    travaux_en_cours = Column(String(1000))

    copro = relationship("Copro", back_populates="syndicat")
    user = relationship("UserAuth")  # Créateur

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    type = Column(Enum(PhotoType))
    title = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)

    building = relationship("Building", back_populates="photos")
    apartment = relationship("Apartment", back_populates="photos")