"""Casos de uso de las cuentas del sitio: registro, verificación, contraseña y propiedades del dueño."""
from datetime import UTC, datetime, timedelta

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.archivos import ArchivoValidado
from app.core.config import get_settings
from app.core.email import enviar_correo
from app.core.exceptions import NoEncontrado, ReglaDeNegocio
from app.core.security import hash_password, verify_password
from app.core.storage import Almacenamiento
from app.features.auditoria.application import Auditor
from app.features.cuentas import domain
from app.features.cuentas.domain import PropositoCodigo
from app.features.cuentas.infrastructure import CodigoVerificacion, CuentaRepository
from app.features.cuentas.schemas import OfertaCuentaIn, RegistroIn
from app.features.propiedades import application as propiedades
from app.features.propiedades.infrastructure import Propiedad, PropiedadRepository
from app.features.solicitudes.application import recibir_oferta
from app.features.solicitudes.infrastructure import SolicitudRepository
from app.features.solicitudes.schemas import OfertaPropiedadIn
from app.features.usuarios.domain import ROL_CLIENTE, ROL_PROPIETARIO
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository

ASUNTOS = {
    PropositoCodigo.VERIFICAR_CORREO: ("Verifica tu correo", "Tu código para verificar tu cuenta de MU Real Estate es"),
    PropositoCodigo.RESTABLECER_PASSWORD: ("Restablece tu contraseña", "Tu código para restablecer tu contraseña es"),
}


class CodigoIncorrecto(ReglaDeNegocio):
    """Se distingue para que el endpoint guarde el intento fallido antes de responder."""


def _ahora() -> datetime:
    return datetime.now(UTC)


def _emitir_codigo(repo: CuentaRepository, usuario: Usuario, proposito: PropositoCodigo,
                   tareas: BackgroundTasks) -> None:
    """Invalida los códigos anteriores, guarda el nuevo solo como hash y lo manda por correo."""
    ahora = _ahora()
    vigente = repo.codigo_vigente(usuario.id, proposito)
    if not domain.puede_reenviar(vigente.creado_en if vigente else None, ahora):
        return
    repo.invalidar_codigos(usuario.id, proposito, ahora)
    codigo = domain.generar_codigo()
    minutos = get_settings().codigo_verificacion_minutos
    repo.db.add(CodigoVerificacion(usuario_id=usuario.id, proposito=proposito, codigo_hash=hash_password(codigo),
                                   expira_en=ahora + timedelta(minutes=minutos)))
    asunto, frase = ASUNTOS[proposito]
    cuerpo = (f"Hola, {usuario.nombre}:\n\n{frase} {codigo}\n\nVence en {minutos} minutos. "
              "Si no lo solicitaste, ignora este correo.")
    tareas.add_task(enviar_correo, usuario.email, f"MU Real Estate · {asunto}", cuerpo)


def _consumir_codigo(repo: CuentaRepository, usuario: Usuario, proposito: PropositoCodigo, codigo: str) -> None:
    ahora = _ahora()
    vigente = repo.codigo_vigente(usuario.id, proposito)
    if vigente is None:
        raise ReglaDeNegocio("No hay un código vigente; solicita uno nuevo")
    domain.validar_vigencia(vigente.expira_en, vigente.intentos, ahora)
    if not verify_password(codigo, vigente.codigo_hash):
        vigente.intentos += 1
        restantes = domain.MAX_INTENTOS - vigente.intentos
        raise CodigoIncorrecto(f"Código incorrecto; te quedan {restantes} intentos" if restantes
                               else "Código incorrecto; solicita un código nuevo")
    vigente.usado_en = ahora


def registrar(db: Session, datos: RegistroIn, tareas: BackgroundTasks) -> None:
    """Si el correo ya existe no se revela: solo se reenvía el código cuando la cuenta sigue sin verificar."""
    usuarios, repo = UsuarioRepository(db), CuentaRepository(db)
    existente = usuarios.obtener_por_email(datos.email)
    if existente is not None:
        if existente.email_verificado_en is None:
            _emitir_codigo(repo, existente, PropositoCodigo.VERIFICAR_CORREO, tareas)
        return
    rol = usuarios.obtener_rol(ROL_PROPIETARIO if datos.quiere_publicar else ROL_CLIENTE)
    usuario = usuarios.agregar(Usuario(nombre=datos.nombre.strip(), email=datos.email.lower(), telefono=datos.telefono,
                                       rol=rol, password_hash=hash_password(datos.password)))
    Auditor(db, usuario.id).registrar("usuarios", usuario.id, "crear", "rol", None, rol.nombre)
    _emitir_codigo(repo, usuario, PropositoCodigo.VERIFICAR_CORREO, tareas)


def verificar_correo(db: Session, email: str, codigo: str) -> None:
    usuario = UsuarioRepository(db).obtener_por_email(email)
    if usuario is None:
        raise ReglaDeNegocio("No hay un código vigente; solicita uno nuevo")
    if usuario.email_verificado_en is not None:
        return
    _consumir_codigo(CuentaRepository(db), usuario, PropositoCodigo.VERIFICAR_CORREO, codigo)
    usuario.email_verificado_en = _ahora()


def reenviar_codigo(db: Session, email: str, tareas: BackgroundTasks) -> None:
    usuario = UsuarioRepository(db).obtener_por_email(email)
    if usuario is not None and usuario.activo and usuario.email_verificado_en is None:
        _emitir_codigo(CuentaRepository(db), usuario, PropositoCodigo.VERIFICAR_CORREO, tareas)


def solicitar_restablecimiento(db: Session, email: str, tareas: BackgroundTasks) -> None:
    usuario = UsuarioRepository(db).obtener_por_email(email)
    if usuario is not None and usuario.activo:
        _emitir_codigo(CuentaRepository(db), usuario, PropositoCodigo.RESTABLECER_PASSWORD, tareas)


def restablecer_password(db: Session, email: str, codigo: str, password: str) -> None:
    usuario = UsuarioRepository(db).obtener_por_email(email)
    if usuario is None or not usuario.activo:
        raise ReglaDeNegocio("No hay un código vigente; solicita uno nuevo")
    _consumir_codigo(CuentaRepository(db), usuario, PropositoCodigo.RESTABLECER_PASSWORD, codigo)
    usuario.password_hash = hash_password(password)
    # El código llegó a su buzón, así que el correo también queda verificado.
    usuario.email_verificado_en = usuario.email_verificado_en or _ahora()
    Auditor(db, usuario.id).registrar("usuarios", usuario.id, "actualizar", "password", None, None)


# ---------- Favoritos ----------
def guardar_favorito(db: Session, usuario_id: int, propiedad_id: int) -> None:
    repo = CuentaRepository(db)
    if not repo.ids_publicadas([propiedad_id]):
        raise NoEncontrado("Propiedad no encontrada")
    repo.guardar_favoritos(usuario_id, [propiedad_id])


def sincronizar_favoritos(db: Session, usuario_id: int, propiedad_ids: list[int]) -> None:
    """Une los favoritos que el visitante marcó sin sesión; ignora los que ya no están publicados."""
    repo = CuentaRepository(db)
    repo.guardar_favoritos(usuario_id, repo.ids_publicadas(propiedad_ids))


# ---------- Propiedades del dueño ----------
def ofrecer_propiedad(db: Session, usuario: Usuario, datos: OfertaCuentaIn, imagenes: list[ArchivoValidado],
                      almacen: Almacenamiento) -> Propiedad:
    """Igual que «Vende o renta con nosotros», pero ligada a la cuenta del dueño y con fotos (RN-03)."""
    if len(imagenes) > domain.MAX_IMAGENES_OFERTA:
        raise ReglaDeNegocio(f"Adjunte como máximo {domain.MAX_IMAGENES_OFERTA} imágenes")
    prepo, repo = PropiedadRepository(db), CuentaRepository(db)
    propietario = repo.propietario_de(usuario.id)
    if propietario is None:
        propietario = prepo.obtener_o_crear_propietario(usuario.nombre, usuario.telefono, usuario.email)
        if propietario.usuario_id is None:
            propietario.usuario_id = usuario.id
        elif propietario.usuario_id != usuario.id:
            propietario = prepo.obtener_o_crear_propietario(usuario.nombre, None, None)
            propietario.usuario_id = usuario.id
    oferta = OfertaPropiedadIn(nombre=usuario.nombre, telefono=usuario.telefono, email=usuario.email,
                               **datos.model_dump(include=set(OfertaPropiedadIn.model_fields)))
    _, propiedad = recibir_oferta(SolicitudRepository(db), oferta)
    db.flush()
    prepo.obtener_internos(propiedad.id).propietario_id = propietario.id
    propiedad.estacionamientos = datos.estacionamientos
    propiedad.antiguedad_anios = datos.antiguedad_anios
    propiedad.amenidades = prepo.amenidades(datos.amenidad_ids)
    propiedad.bienes = prepo.bienes(datos.bien_ids)
    auditor = Auditor(db, usuario.id)
    auditor.registrar("propiedades", propiedad.id, "crear", "estado_publicacion", None, propiedad.estado_publicacion)
    if imagenes:
        propiedades.agregar_medios(prepo, auditor, almacen, propiedad.id, imagenes)
    return propiedad
