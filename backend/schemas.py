from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    owner = "owner"
    gestionnaire = "gestionnaire"
    lecteur = "lecteur"

class PhotoType(str, Enum):
    building = "building"
    apartment = "apartment"

class AddressBase(BaseModel):
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    complement: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class UserCreate(AddressBase):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str

class UserOut(AddressBase):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str

    class Config:
        orm_mode = True

class BuildingBase(AddressBase):
    name: str
    floors: int
    is_copro: bool
    copro_id: Optional[int] = None

class BuildingCreate(BuildingBase):
    pass

class BuildingOut(BuildingBase):
    id: int
    copro: Optional['CoproOut'] = None
    class Config:
        orm_mode = True

class ApartmentBase(BaseModel):
    type_logement: str
    layout: str
    floor: Optional[int] = None

class ApartmentCreate(ApartmentBase):
    building_id: int

class ApartmentOut(ApartmentBase):
    id: int
    building_id: int

    class Config:
        orm_mode = True

class ApartmentUserLinkOut(BaseModel):
    id: int
    user_id: int
    apartment_id: int
    role: UserRole

    class Config:
        orm_mode = True

class RoleAssignment(BaseModel):
    user_id: int
    role: UserRole

class CoproBase(BaseModel):
    nom: Optional[str] = None
    adresse_rue: Optional[str] = None
    adresse_code_postal: Optional[str] = None
    adresse_ville: Optional[str] = None
    annee_construction: Optional[int] = None
    nb_batiments: Optional[int] = None
    nb_lots_total: Optional[int] = None
    nb_lots_principaux: Optional[int] = None
    nb_lots_secondaires: Optional[int] = None
    surface_totale_m2: Optional[int] = None
    type_construction: Optional[str] = None
    nb_etages: Optional[int] = None
    ascenseur: Optional[bool] = None
    nb_ascenseurs: Optional[int] = None
    chauffage_collectif_type: Optional[str] = None
    chauffage_individuel_type: Optional[str] = None
    clim_centralisee: Optional[bool] = None
    eau_chaude_collective: Optional[bool] = None
    isolation_thermique: Optional[str] = None
    isolation_annee: Optional[int] = None
    rt2012_re2020: Optional[bool] = None
    accessibilite_pmr: Optional[bool] = None
    toiture_type: Optional[str] = None
    toiture_materiaux: Optional[str] = None
    gardien: Optional[bool] = None
    local_velos: Optional[bool] = None
    parkings_ext: Optional[bool] = None
    nb_parkings_ext: Optional[int] = None
    parkings_int: Optional[bool] = None
    nb_parkings_int: Optional[int] = None
    caves: Optional[bool] = None
    nb_caves: Optional[int] = None
    espaces_verts: Optional[bool] = None
    jardins_partages: Optional[bool] = None
    piscine: Optional[bool] = None
    salle_sport: Optional[bool] = None
    aire_jeux: Optional[bool] = None
    salle_reunion: Optional[bool] = None
    dpe_collectif: Optional[str] = None
    audit_energetique: Optional[bool] = None
    audit_energetique_date: Optional[str] = None
    energie_utilisee: Optional[str] = None
    panneaux_solaires: Optional[bool] = None
    bornes_recharge: Optional[bool] = None

class CoproCreate(CoproBase):
    pass

class CoproUpdate(CoproBase):
    pass

class CoproOut(CoproBase):
    id: int
    class Config:
        orm_mode = True

class SyndicatCoproBase(BaseModel):
    copro_id: int
    statut_juridique: Optional[str] = None
    date_creation: Optional[str] = None
    reglement_copro: Optional[bool] = None
    carnet_entretien: Optional[bool] = None
    nom_syndic: Optional[str] = None
    type_syndic: Optional[str] = None
    societe_syndic: Optional[str] = None
    date_derniere_ag: Optional[str] = None
    assurance_compagnie: Optional[str] = None
    assurance_num_police: Optional[str] = None
    assurance_validite: Optional[str] = None
    procedures_judiciaires: Optional[bool] = None
    procedures_details: Optional[str] = None
    budget_annuel_previsionnel: Optional[int] = None
    charges_annuelles_par_lot: Optional[int] = None
    charges_speciales: Optional[int] = None
    emprunt_collectif: Optional[bool] = None
    emprunt_montant: Optional[int] = None
    emprunt_echeance: Optional[str] = None
    taux_impayes_charges: Optional[int] = None
    fonds_roulement: Optional[int] = None
    fonds_travaux: Optional[int] = None
    travaux_votes: Optional[str] = None
    travaux_en_cours: Optional[str] = None

class SyndicatCoproCreate(SyndicatCoproBase):
    pass

class SyndicatCoproUpdate(SyndicatCoproBase):
    pass

class SyndicatCoproOut(SyndicatCoproBase):
    id: int
    class Config:
        orm_mode = True

class ApartmentUserFullOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole

    class Config:
        orm_mode = True

class PhotoCreate(BaseModel):
    type: PhotoType
    target_id: int
    title: Optional[str] = None
    description: Optional[str] = None

class PhotoOut(BaseModel):
    id: int
    filename: str
    type: str
    created_at: datetime
    title: Optional[str] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True