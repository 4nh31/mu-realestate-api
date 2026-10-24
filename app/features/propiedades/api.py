"""Endpoints de propiedades: panel administrativo (protegido) y consulta pública."""
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import DbSession, require_permission
from app.core.exceptions import NoEncontrado
from app.features.auditoria.application import Auditor
from app.features.propiedades import application as casos
from app.features.propiedades.domain import Disponibilidad, EstadoPublicacion, Operacion, TipoPropiedad
from app.features.propiedades.infrastructure import FiltrosBusqueda, PropiedadRepository
from app.features.propiedades.schemas import (CambioPublicacion, DatosInternosIn, DatosInternosOut, Pagina,
                                              PropiedadActualizar, PropiedadCrear, PropiedadPanel,
                                              PropiedadPublica)
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario

panel = APIRouter(prefix="/propiedades", tags=["Propiedades (panel)"])
publico = APIRouter(prefix="/publico/propiedades", tags=["Propiedades (público)"])


def permiso(clave: str):
    return Annotated[Usuario, Depends(require_permission(clave))]


def filtros(
    operacion: Operacion | None = None,
    tipo: TipoPropiedad | None = None,
    ciudad_id: int | None = None,
    zona_id: int | None = None,
    recamaras_min: int | None = Query(default=None, ge=0),
    banos_min: Decimal | None = Query(default=None, ge=0),
    estacionamientos_min: int | None = Query(default=None, ge=0),
    precio_min: Decimal | None = Query(default=None, ge=0),
    precio_max: Decimal | None = Query(default=None, ge=0),
    amenidad_ids: Annotated[list[int] | None, Query()] = None,
) -> FiltrosBusqueda:
    return FiltrosBusqueda(operacion, tipo, ciudad_id, zona_id, recamaras_min, banos_min, precio_min, precio_max,
                           estacionamientos_min, amenidad_ids)


Filtros = Annotated[FiltrosBusqueda, Depends(filtros)]
Limite = Annotated[int, Query(ge=1, le=100)]
Desplazamiento = Annotated[int, Query(ge=0)]


# ---------- Público ----------
@publico.get("", response_model=Pagina[PropiedadPublica], summary="Buscar propiedades publicadas")
def buscar(db: DbSession, f: Filtros, limite: Limite = 20, desplazamiento: Desplazamiento = 0):
    filas, total = PropiedadRepository(db).buscar_publicas(f, limite, desplazamiento)
    return Pagina(total=total, limite=limite, desplazamiento=desplazamiento,
                  elementos=[PropiedadPublica.desde(p) for p in filas])


@publico.get("/{propiedad_id}", response_model=PropiedadPublica, summary="Ficha pública de una propiedad")
def ficha(propiedad_id: int, db: DbSession):
    p = PropiedadRepository(db).obtener(propiedad_id)
    if p is None or not p.activo or p.estado_publicacion != EstadoPublicacion.PUBLICADA:
        raise NoEncontrado("Propiedad no encontrada")
    return PropiedadPublica.desde(p)


# ---------- Panel ----------
@panel.get("", response_model=Pagina[PropiedadPanel], summary="Listar propiedades en el panel")
def listar(db: DbSession, _: permiso(Permisos.PROPIEDADES_VER), f: Filtros,
           estado: EstadoPublicacion | None = None, disponibilidad: Disponibilidad | None = None,
           incluir_inactivas: bool = False, limite: Limite = 20, desplazamiento: Desplazamiento = 0):
    filas, total = PropiedadRepository(db).listar_panel(f, estado, disponibilidad, incluir_inactivas, limite,
                                                         desplazamiento)
    return Pagina(total=total, limite=limite, desplazamiento=desplazamiento,
                  elementos=[PropiedadPanel.desde(p) for p in filas])


@panel.post("", response_model=PropiedadPanel, status_code=status.HTTP_201_CREATED, summary="Registrar propiedad")
def crear(datos: PropiedadCrear, db: DbSession, actor: permiso(Permisos.PROPIEDADES_EDITAR)):
    p = casos.crear_propiedad(PropiedadRepository(db), Auditor(db, actor.id), datos)
    db.commit()
    db.refresh(p)
    return PropiedadPanel.desde(p)


@panel.get("/{propiedad_id}", response_model=PropiedadPanel, summary="Detalle de una propiedad (sin datos internos)")
def detalle(propiedad_id: int, db: DbSession, _: permiso(Permisos.PROPIEDADES_VER)):
    p = PropiedadRepository(db).obtener(propiedad_id)
    if p is None:
        raise NoEncontrado("Propiedad no encontrada")
    return PropiedadPanel.desde(p)


@panel.patch("/{propiedad_id}", response_model=PropiedadPanel, summary="Modificar datos públicos")
def actualizar(propiedad_id: int, datos: PropiedadActualizar, db: DbSession,
               actor: permiso(Permisos.PROPIEDADES_EDITAR)):
    p = casos.actualizar_propiedad(PropiedadRepository(db), Auditor(db, actor.id), propiedad_id, datos)
    db.commit()
    db.refresh(p)
    return PropiedadPanel.desde(p)


@panel.delete("/{propiedad_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desactivar propiedad (baja lógica)")
def desactivar(propiedad_id: int, db: DbSession, actor: permiso(Permisos.PROPIEDADES_PUBLICAR)):
    casos.desactivar_propiedad(PropiedadRepository(db), Auditor(db, actor.id), propiedad_id)
    db.commit()


@panel.patch("/{propiedad_id}/publicacion", response_model=PropiedadPanel,
             summary="Cambiar estado de publicación (enviar a revisión, publicar, ocultar, rechazar)")
def publicacion(propiedad_id: int, cambio: CambioPublicacion, db: DbSession,
                actor: permiso(Permisos.PROPIEDADES_PUBLICAR)):
    p = casos.cambiar_publicacion(PropiedadRepository(db), Auditor(db, actor.id), propiedad_id, cambio)
    db.commit()
    db.refresh(p)
    return PropiedadPanel.desde(p)


@panel.get("/{propiedad_id}/interno", response_model=DatosInternosOut,
           summary="Consultar datos internos (precio real, valor mínimo, propietario, comisión...)")
def ver_internos(propiedad_id: int, db: DbSession, _: permiso(Permisos.PROPIEDADES_VER_INTERNO)):
    internos = PropiedadRepository(db).obtener_internos(propiedad_id)
    if internos is None:
        raise NoEncontrado("La propiedad no tiene datos internos registrados")
    return internos


@panel.put("/{propiedad_id}/interno", response_model=DatosInternosOut, summary="Registrar o modificar datos internos")
def guardar_internos(propiedad_id: int, datos: DatosInternosIn, db: DbSession,
                     actor: permiso(Permisos.PROPIEDADES_EDITAR_INTERNO)):
    internos = casos.guardar_datos_internos(PropiedadRepository(db), Auditor(db, actor.id), propiedad_id, datos)
    db.commit()
    db.refresh(internos)
    return internos
