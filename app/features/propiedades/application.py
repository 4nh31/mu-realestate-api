"""Casos de uso del slice de propiedades. Orquestan dominio, repositorio y auditoría."""
from app.core.exceptions import NoEncontrado, ReglaDeNegocio
from app.features.auditoria.application import Auditor
from app.features.propiedades import domain
from app.features.propiedades.domain import EstadoPublicacion
from app.features.propiedades.infrastructure import DatosInternos, Propiedad, PropiedadRepository
from app.features.propiedades.schemas import (CambioPublicacion, DatosInternosIn, PropiedadActualizar,
                                              PropiedadCrear)

ENTIDAD = "propiedades"
CAMPOS_INTERNOS = ("precio_real", "valor_minimo", "comision_pct", "direccion_exacta", "notas", "propietario_id")


def _obtener(repo: PropiedadRepository, propiedad_id: int) -> Propiedad:
    propiedad = repo.obtener(propiedad_id)
    if propiedad is None:
        raise NoEncontrado("Propiedad no encontrada")
    return propiedad


def _validar_zona(repo: PropiedadRepository, zona_id: int | None) -> None:
    if zona_id is not None and not repo.zona_existe(zona_id):
        raise ReglaDeNegocio("La zona indicada no existe")


def crear_propiedad(repo: PropiedadRepository, auditor: Auditor, datos: PropiedadCrear) -> Propiedad:
    _validar_zona(repo, datos.zona_id)
    valores = datos.model_dump(exclude={"amenidad_ids"})
    propiedad = Propiedad(**valores, amenidades=repo.amenidades(datos.amenidad_ids))
    repo.agregar(propiedad)
    auditor.registrar(ENTIDAD, propiedad.id, "crear", "estado_publicacion", None, propiedad.estado_publicacion)
    return propiedad


def actualizar_propiedad(repo: PropiedadRepository, auditor: Auditor, propiedad_id: int,
                         datos: PropiedadActualizar) -> Propiedad:
    propiedad = _obtener(repo, propiedad_id)
    cambios = datos.model_dump(exclude_unset=True, exclude={"amenidad_ids"})
    _validar_zona(repo, cambios.get("zona_id"))
    antes = {campo: getattr(propiedad, campo) for campo in cambios}
    for campo, valor in cambios.items():
        setattr(propiedad, campo, valor)
    if datos.amenidad_ids is not None:
        propiedad.amenidades = repo.amenidades(datos.amenidad_ids)
    auditor.registrar_diferencias(ENTIDAD, propiedad.id, antes, cambios)
    return propiedad


def cambiar_publicacion(repo: PropiedadRepository, auditor: Auditor, propiedad_id: int,
                        cambio: CambioPublicacion) -> Propiedad:
    propiedad = _obtener(repo, propiedad_id)
    domain.validar_transicion(propiedad.estado_publicacion, cambio.estado)
    if cambio.estado == EstadoPublicacion.PUBLICADA:
        domain.validar_publicable(propiedad.zona_id is not None, propiedad.precio_publico, propiedad.activo)
    if cambio.estado == EstadoPublicacion.RECHAZADA and not cambio.motivo:
        raise ReglaDeNegocio("Indique el motivo del rechazo")
    auditor.registrar(ENTIDAD, propiedad.id, "publicar", "estado_publicacion",
                      propiedad.estado_publicacion, cambio.estado)
    propiedad.estado_publicacion = cambio.estado
    return propiedad


def desactivar_propiedad(repo: PropiedadRepository, auditor: Auditor, propiedad_id: int) -> None:
    """RN-07: baja lógica; si estaba publicada se oculta para que deje de verse en el sitio."""
    propiedad = _obtener(repo, propiedad_id)
    if not propiedad.activo:
        return
    if propiedad.estado_publicacion == EstadoPublicacion.PUBLICADA:
        auditor.registrar(ENTIDAD, propiedad.id, "publicar", "estado_publicacion",
                          propiedad.estado_publicacion, EstadoPublicacion.OCULTA)
        propiedad.estado_publicacion = EstadoPublicacion.OCULTA
    auditor.registrar(ENTIDAD, propiedad.id, "desactivar", "activo", True, False)
    propiedad.activo = False


def guardar_datos_internos(repo: PropiedadRepository, auditor: Auditor, propiedad_id: int,
                           datos: DatosInternosIn) -> DatosInternos:
    propiedad = _obtener(repo, propiedad_id)
    internos = repo.obtener_internos(propiedad_id)
    if internos is None:
        internos = DatosInternos(propiedad_id=propiedad.id)
        repo.db.add(internos)
    antes = {c: getattr(internos, c) for c in CAMPOS_INTERNOS}

    cambios = datos.model_dump(exclude_unset=True, exclude={"propietario"})
    domain.validar_valor_minimo(cambios.get("precio_real", internos.precio_real),
                                cambios.get("valor_minimo", internos.valor_minimo))
    for campo, valor in cambios.items():
        setattr(internos, campo, valor)
    if datos.propietario is not None:
        p = datos.propietario
        internos.propietario = repo.obtener_o_crear_propietario(p.nombre, p.telefono, p.email)
        internos.propietario_id = internos.propietario.id

    repo.db.flush()
    despues = {c: getattr(internos, c) for c in CAMPOS_INTERNOS}
    auditor.registrar_diferencias("datos_internos", propiedad_id, antes, despues)
    return internos
