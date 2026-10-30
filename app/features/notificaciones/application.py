"""Servicio de notificaciones reutilizado por los demás slices: guarda el aviso y, si aplica, manda correo."""
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import enviar_correo
from app.features.notificaciones.domain import TipoAviso
from app.features.solicitudes.infrastructure import Aviso
from app.features.usuarios.infrastructure import UsuarioRepository


class Notificador:
    def __init__(self, db: Session, tareas: BackgroundTasks | None = None, autor_id: int | None = None):
        self.db = db
        self.tareas = tareas
        self.autor_id = autor_id

    def notificar(self, usuario_ids: list[int], tipo: TipoAviso, titulo: str, mensaje: str | None = None,
                  enlace: str | None = None, por_correo: bool = False) -> None:
        usuarios = UsuarioRepository(self.db)
        for uid in dict.fromkeys(usuario_ids):
            self.db.add(Aviso(usuario_id=uid, tipo=tipo, titulo=titulo[:150], mensaje=mensaje, enlace=enlace,
                              autor_id=self.autor_id, por_correo=por_correo))
            usuario = usuarios.obtener(uid) if por_correo and self.tareas else None
            if usuario is not None and usuario.activo:
                cuerpo = "\n\n".join(filter(None, [titulo, mensaje,
                                                   enlace and f"{get_settings().frontend_url}{enlace}"]))
                self.tareas.add_task(enviar_correo, usuario.email, f"MU Real Estate · {titulo[:80]}", cuerpo)

    def notificar_permiso(self, clave: str, tipo: TipoAviso, titulo: str, mensaje: str | None = None,
                          enlace: str | None = None) -> None:
        """Avisa a todo el personal activo que tenga el permiso indicado."""
        ids = [u.id for u in UsuarioRepository(self.db).con_permiso(clave)]
        self.notificar(ids, tipo, titulo, mensaje, enlace)
