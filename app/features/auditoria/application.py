"""Servicio de auditoría reutilizado por los demás slices (núcleo compartido de la regla RN-06)."""
from sqlalchemy.orm import Session

from app.features.auditoria.infrastructure import AuditoriaRepository, RegistroAuditoria


def _texto(valor: object) -> str | None:
    return None if valor is None else str(valor.value if hasattr(valor, "value") else valor)


class Auditor:
    def __init__(self, db: Session, usuario_id: int | None):
        self.repo = AuditoriaRepository(db)
        self.usuario_id = usuario_id

    def registrar(self, entidad: str, entidad_id: int, accion: str, campo: str | None,
                  anterior: object, nuevo: object) -> None:
        self.repo.agregar(RegistroAuditoria(
            usuario_id=self.usuario_id, entidad=entidad, entidad_id=entidad_id, accion=accion,
            campo=campo, valor_anterior=_texto(anterior), valor_nuevo=_texto(nuevo),
        ))

    def registrar_diferencias(self, entidad: str, entidad_id: int, antes: dict, despues: dict) -> int:
        """Registra un renglón por cada campo cuyo valor cambió. Devuelve cuántos cambios hubo."""
        cambios = 0
        for campo, nuevo in despues.items():
            anterior = antes.get(campo)
            if _texto(anterior) != _texto(nuevo):
                self.registrar(entidad, entidad_id, "actualizar", campo, anterior, nuevo)
                cambios += 1
        return cambios
