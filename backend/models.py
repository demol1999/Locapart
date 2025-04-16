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
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)

    street_number = Column(String)
    street_name = Column(String)
    complement = Column(String)
    postal_code = Column(String)
    city = Column(String)
    country = Column(String)

    apartment_links = relationship("ApartmentUserLink", back_populates="user")

class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    street_number = Column(String)
    street_name = Column(String)
    complement = Column(String)
    postal_code = Column(String)
    city = Column(String)
    country = Column(String)
    floors = Column(Integer)
    is_copro = Column(Boolean)

    apartments = relationship("Apartment", back_populates="building")
    photos = relationship("Photo", back_populates="building")

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    type_logement = Column(String)
    layout = Column(String)
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

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    type = Column(Enum(PhotoType))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)

    building = relationship("Building", back_populates="photos")
    apartment = relationship("Apartment", back_populates="photos")