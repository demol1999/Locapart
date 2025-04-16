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

class BuildingCreate(BuildingBase):
    pass

class BuildingOut(BuildingBase):
    id: int
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

class ApartmentUserFullOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole

    class Config:
        orm_mode = True

class PhotoOut(BaseModel):
    id: int
    filename: str
    type: str
    created_at: datetime

    class Config:
        orm_mode = True