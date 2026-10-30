"""Casos de uso del slice de propiedades. Orquestan dominio, repositorio y auditoría."""
from datetime import UTC, datetime

from app.core.archivos import ArchivoValidado
from app.core.exceptions import NoEncontrado, ReglaDeNegocio
from app.core.storage import PUBLICO, Almacenamiento
from app.features.auditoria.application import Auditor
from app.features.cuentas.infrastructure import CuentaRepository
from app.features.notificaciones.application import Notificador
from app.features.notificaciones.domain import TipoAviso
from app.features.propiedades import domain
from app.features.propiedades.domain import EstadoPublicacion, TipoMedio
from app.features.propiedades.infrastructure import DatosInternos, Medio, Propiedad, PropiedadRepository
from app.features.propiedades.schemas import (CambioPublicacion, DatosInternosIn, MedioActualizar,
                                              PropiedadActualizar, PropiedadCrear)

ENTIDAD = "propiedades"
MAX_MEDIOS = 10
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
    valores = datos.model_dump(exclude={"amenidad_ids", "bien_ids"})
    propiedad = Propiedad(**valores, amenidades=repo.amenidades(datos.amenidad_ids), bienes=repo.bienes(datos.bien_ids))
    repo.agregar(propiedad)
    auditor.registrar(ENTIDAD, propiedad.id, "crear", "estado_publicacion", None, propiedad.estado_publicacion)
    return propiedad


def actualizar_propiedad(repo: PropiedadRepository, auditor: Auditor, propiedad_id: int,
                         datos: PropiedadActualizar, notificador: Notificador | None = None) -> Propiedad:
    propiedad = _obtener(repo, propiedad_id)
    cambios = datos.model_dump(exclude_unset=True, exclude={"amenidad_ids", "bien_ids"})
    _validar_zona(repo, cambios.get("zona_id"))
    antes = {campo: getattr(propiedad, campo) for campo in cambios}
    for campo, valor in cambios.items():
        setattr(propiedad, campo, valor)
    if datos.amenidad_ids is not None:
        propiedad.amenidades = repo.amenidades(datos.amenidad_ids)
    if datos.bien_ids is not None:
        propiedad.bienes = repo.bienes(datos.bien_ids)
    auditor.registrar_diferencias(ENTIDAD, propiedad.id, antes, cambios)
    _avisar_bajada_de_precio(repo, notificador, propiedad, antes.get("precio_publico"))
    return propiedad


def _avisar_bajada_de_precio(repo: PropiedadRepository, notificador: Notificador | None, propiedad: Propiedad,
                             precio_anterior) -> None:
    """Quien guardó la propiedad en favoritos recibe un aviso cuando baja su precio público."""
    nuevo = propiedad.precio_publico
    if (notificador is None or precio_anterior is None or nuevo is None or nuevo >= precio_anterior
            or propiedad.estado_publicacion != EstadoPublicacion.PUBLICADA or not propiedad.activo):
        return
    interesados = CuentaRepository(repo.db).usuarios_con_favorito(propiedad.id)
    notificador.notificar(interesados, TipoAviso.FAVORITO, f"Bajó de precio: {propiedad.titulo}",
                          f"Ahora cuesta ${nuevo:,.2f} {propiedad.moneda} (antes ${precio_anterior:,.2f}).",
                          f"/propiedad/{propiedad.id}", por_correo=True)


def cambiar_publicacion(repo: PropiedadRepository, auditor: Auditor, propiedad_id: int,
                        cambio: CambioPublicacion, notificador: Notificador | None = None) -> Propiedad:
    propiedad = _obtener(repo, propiedad_id)
    domain.validar_transicion(propiedad.estado_publicacion, cambio.estado)
    if cambio.estado == EstadoPublicacion.PUBLICADA:
        domain.validar_publicable(propiedad.zona_id is not None, propiedad.precio_publico, propiedad.activo)
    motivo = (cambio.motivo or "").strip() or None
    if cambio.estado == EstadoPublicacion.RECHAZADA and not motivo:
        raise ReglaDeNegocio("Indique el motivo del rechazo")
    ahora = datetime.now(UTC)
    revision = propiedad.estado_publicacion == EstadoPublicacion.EN_REVISION
    auditor.registrar(ENTIDAD, propiedad.id, "publicar", "estado_publicacion",
                      propiedad.estado_publicacion, cambio.estado)
    propiedad.estado_publicacion = cambio.estado
    if cambio.estado == EstadoPublicacion.RECHAZADA:
        auditor.registrar(ENTIDAD, propiedad.id, "rechazar", "motivo_rechazo", propiedad.motivo_rechazo, motivo)
        propiedad.motivo_rechazo = motivo
    if cambio.estado == EstadoPublicacion.PUBLICADA and propiedad.publicada_en is None:
        propiedad.publicada_en = ahora
    if revision:
        propiedad.revisado_por, propiedad.revisado_en = auditor.usuario_id, ahora
        _avisar_moderacion(repo, notificador, propiedad)
    return propiedad


def _avisar_moderacion(repo: PropiedadRepository, notificador: Notificador | None, propiedad: Propiedad) -> None:
    """RN-09: el dueño que ofreció la propiedad desde su cuenta se entera de la decisión y del motivo."""
    usuario_id = repo.propietario_usuario_id(propiedad.id) if notificador else None
    if usuario_id is None:
        return
    if propiedad.estado_publicacion == EstadoPublicacion.PUBLICADA:
        titulo, mensaje = f"Tu propiedad «{propiedad.titulo}» ya está publicada", None
    else:
        titulo, mensaje = f"Tu propiedad «{propiedad.titulo}» no fue aprobada", f"Motivo: {propiedad.motivo_rechazo}"
    notificador.notificar([usuario_id], TipoAviso.PUBLICACION, titulo, mensaje, "/mis-propiedades", por_correo=True)


# ---------- Medios (fotos) ----------
def agregar_medios(repo: PropiedadRepository, auditor: Auditor, almacen: Almacenamiento, propiedad_id: int,
                   archivos: list[ArchivoValidado]) -> list[Medio]:
    propiedad = _obtener(repo, propiedad_id)
    if not archivos:
        raise ReglaDeNegocio("Adjunte al menos una imagen")
    if len(propiedad.medios) + len(archivos) > MAX_MEDIOS:
        raise ReglaDeNegocio(f"Una propiedad admite como máximo {MAX_MEDIOS} imágenes")
    orden = max((m.orden for m in propiedad.medios), default=-1) + 1
    hay_portada = any(m.es_portada for m in propiedad.medios)
    nuevos = []
    for i, archivo in enumerate(archivos):
        clave = almacen.guardar_nuevo(archivo.contenido, PUBLICO, f"propiedades/{propiedad.id}", archivo.mime)
        medio = Medio(tipo=TipoMedio.FOTO, url=almacen.url_publica(clave), public_id=clave, orden=orden + i,
                      es_portada=not hay_portada and i == 0)
        propiedad.medios.append(medio)
        nuevos.append(medio)
    repo.db.flush()
    auditor.registrar(ENTIDAD, propiedad.id, "actualizar", "medios", len(propiedad.medios) - len(nuevos),
                      len(propiedad.medios))
    return nuevos


def _obtener_medio(repo: PropiedadRepository, medio_id: int) -> Medio:
    medio = repo.obtener_medio(medio_id)
    if medio is None:
        raise NoEncontrado("Imagen no encontrada")
    return medio


def actualizar_medio(repo: PropiedadRepository, medio_id: int, datos: MedioActualizar) -> Medio:
    medio = _obtener_medio(repo, medio_id)
    if datos.orden is not None:
        medio.orden = datos.orden
    if datos.es_portada:
        for otro in medio.propiedad.medios:
            otro.es_portada = otro.id == medio.id
    return medio


def eliminar_medio(repo: PropiedadRepository, auditor: Auditor, almacen: Almacenamiento, medio_id: int) -> None:
    medio = _obtener_medio(repo, medio_id)
    propiedad = medio.propiedad
    restantes = [m for m in propiedad.medios if m.id != medio.id]
    if medio.es_portada and restantes:
        restantes[0].es_portada = True
    propiedad.medios.remove(medio)
    if medio.public_id:
        almacen.eliminar(medio.public_id)
    auditor.registrar(ENTIDAD, propiedad.id, "actualizar", "medios", len(restantes) + 1, len(restantes))


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
