"""Catálogos públicos para los filtros del buscador."""
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter

from app.core.deps import DbSession
from app.features.catalogos.infrastructure import CatalogoRepository

router = APIRouter(prefix="/publico/catalogos", tags=["Catálogos"])


class CiudadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    estado: str


class ZonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ciudad_id: int
    nombre: str


class AmenidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


@router.get("/ciudades", response_model=list[CiudadOut], summary="Ciudades disponibles")
def ciudades(db: DbSession):
    return CatalogoRepository(db).ciudades()


@router.get("/zonas", response_model=list[ZonaOut], summary="Zonas o colonias, opcionalmente por ciudad")
def zonas(db: DbSession, ciudad_id: int | None = None):
    return CatalogoRepository(db).zonas(ciudad_id)


@router.get("/amenidades", response_model=list[AmenidadOut], summary="Amenidades")
def amenidades(db: DbSession):
    return CatalogoRepository(db).amenidades()


class BienOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class CategoriaBienesOut(BaseModel):
    categoria: str
    bienes: list[BienOut]


@router.get("/bienes", response_model=list[CategoriaBienesOut], summary="Bienes incluidos, agrupados por categoría")
def bienes(db: DbSession):
    grupos: dict[str, list] = {}
    for b in CatalogoRepository(db).bienes():
        grupos.setdefault(b.categoria, []).append(b)
    return [CategoriaBienesOut(categoria=c, bienes=[BienOut.model_validate(b) for b in bs]) for c, bs in grupos.items()]
