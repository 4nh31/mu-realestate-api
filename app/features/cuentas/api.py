"""Endpoints de las cuentas del sitio público: registro y verificación, favoritos y propiedades del dueño."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.archivos import IMAGENES, validar_archivo
from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.core.storage import get_almacenamiento
from app.features.cuentas import application as casos
from app.features.cuentas.infrastructure import CuentaRepository
from app.features.cuentas.schemas import (CorreoIn, MensajeOut, OfertaCuentaIn, PropiedadCuentaOut, RegistroIn,
                                          RestablecimientoIn, SincronizarFavoritosIn, VerificacionIn)
from app.features.propiedades.schemas import PropiedadPublica
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario

auth = APIRouter(prefix="/auth", tags=["Autenticación"])
cuenta = APIRouter(prefix="/cuenta", tags=["Mi cuenta"], responses=RESPUESTAS_PROTEGIDAS)
Cuenta = Annotated[Usuario, Depends(require_permission(Permisos.CUENTA_USAR))]

ENVIADO = "Si el correo está registrado, te enviamos un código."


def _verificada(usuario: Cuenta) -> Usuario:
    """RN-15: con el correo sin verificar se puede entrar, pero no ofrecer propiedades ni reseñar."""
    if usuario.email_verificado_en is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Verifica tu correo para continuar")
    return usuario


CuentaVerificada = Annotated[Usuario, Depends(_verificada)]


# ---------- Registro y verificación ----------
@auth.post("/registro", response_model=MensajeOut, status_code=status.HTTP_201_CREATED,
           summary="Crear una cuenta de cliente o propietario y enviar el código de verificación")
def registro(datos: RegistroIn, db: DbSession, tareas: BackgroundTasks):
    casos.registrar(db, datos, tareas)
    db.commit()
    return MensajeOut(mensaje="Te enviamos un código de 6 dígitos para verificar tu correo.")


def _con_intento(db, accion) -> None:
    """Guarda el intento fallido aunque la petición responda con error."""
    try:
        accion()
    except casos.CodigoIncorrecto:
        db.commit()
        raise
    db.commit()


@auth.post("/verificar-correo", response_model=MensajeOut, summary="Verificar el correo con el código recibido")
def verificar_correo(datos: VerificacionIn, db: DbSession):
    _con_intento(db, lambda: casos.verificar_correo(db, datos.email, datos.codigo))
    return MensajeOut(mensaje="Correo verificado. Ya puedes iniciar sesión.")


@auth.post("/reenviar-codigo", response_model=MensajeOut, status_code=status.HTTP_202_ACCEPTED,
           summary="Reenviar el código de verificación (uno por minuto)")
def reenviar_codigo(datos: CorreoIn, db: DbSession, tareas: BackgroundTasks):
    casos.reenviar_codigo(db, datos.email, tareas)
    db.commit()
    return MensajeOut(mensaje=ENVIADO)


@auth.post("/restablecer-password", response_model=MensajeOut, status_code=status.HTTP_202_ACCEPTED,
           summary="Pedir un código para restablecer la contraseña")
def restablecer_password(datos: CorreoIn, db: DbSession, tareas: BackgroundTasks):
    casos.solicitar_restablecimiento(db, datos.email, tareas)
    db.commit()
    return MensajeOut(mensaje=ENVIADO)


@auth.post("/restablecer-password/confirmar", response_model=MensajeOut,
           summary="Cambiar la contraseña con el código recibido")
def confirmar_restablecimiento(datos: RestablecimientoIn, db: DbSession):
    _con_intento(db, lambda: casos.restablecer_password(db, datos.email, datos.codigo, datos.password))
    return MensajeOut(mensaje="Contraseña actualizada. Ya puedes iniciar sesión.")


# ---------- Favoritos ----------
@cuenta.get("/favoritos", response_model=list[PropiedadPublica], summary="Mis propiedades favoritas")
def favoritos(db: DbSession, usuario: Cuenta):
    return [PropiedadPublica.desde(p) for p in CuentaRepository(db).favoritos(usuario.id)]


@cuenta.put("/favoritos/{propiedad_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Guardar en favoritos")
def guardar_favorito(propiedad_id: int, db: DbSession, usuario: Cuenta):
    casos.guardar_favorito(db, usuario.id, propiedad_id)
    db.commit()


@cuenta.delete("/favoritos/{propiedad_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Quitar de favoritos")
def quitar_favorito(propiedad_id: int, db: DbSession, usuario: Cuenta):
    CuentaRepository(db).quitar_favorito(usuario.id, propiedad_id)
    db.commit()


@cuenta.post("/favoritos/sincronizar", response_model=list[PropiedadPublica],
             summary="Unir los favoritos guardados en el navegador antes de iniciar sesión")
def sincronizar_favoritos(datos: SincronizarFavoritosIn, db: DbSession, usuario: Cuenta):
    casos.sincronizar_favoritos(db, usuario.id, datos.propiedad_ids)
    db.commit()
    return [PropiedadPublica.desde(p) for p in CuentaRepository(db).favoritos(usuario.id)]


# ---------- Propiedades del dueño ----------
@cuenta.get("/propiedades", response_model=list[PropiedadCuentaOut],
            summary="Propiedades que ofrecí: estado de revisión y motivo si se rechazó")
def mis_propiedades(db: DbSession, usuario: Cuenta):
    return [PropiedadCuentaOut.desde(p) for p in CuentaRepository(db).propiedades_de(usuario.id)]


@cuenta.post("/propiedades", response_model=PropiedadCuentaOut, status_code=status.HTTP_201_CREATED,
             summary="Ofrecer una propiedad con fotos (multipart: «datos» en JSON e «imagenes»)")
def ofrecer_propiedad(
    db: DbSession,
    usuario: CuentaVerificada,
    datos: Annotated[str, Form(description="JSON con los campos de OfertaCuentaIn")],
    imagenes: Annotated[list[UploadFile], File(description="Hasta 10 fotos JPG, PNG o WEBP")] = [],
):
    try:
        oferta = OfertaCuentaIn.model_validate_json(datos)
    except ValidationError as e:
        raise RequestValidationError(e.errors(include_url=False)) from None
    validadas = [validar_archivo(i, IMAGENES) for i in imagenes]
    p = casos.ofrecer_propiedad(db, usuario, oferta, validadas, get_almacenamiento())
    db.commit()
    db.refresh(p)
    return PropiedadCuentaOut.desde(p)
