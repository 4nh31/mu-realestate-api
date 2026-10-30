"""Envío de correos por SMTP. Sin SMTP_HOST (desarrollo y pruebas) el correo solo se registra en el log."""
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("mu.email")


@dataclass
class Correo:
    para: str
    asunto: str
    cuerpo: str


# Correos "enviados" cuando no hay SMTP configurado; las pruebas leen aquí los códigos de verificación.
BANDEJA_DESARROLLO: list[Correo] = []


def enviar_correo(para: str, asunto: str, cuerpo: str) -> None:
    """Pensado para ejecutarse en BackgroundTasks: un fallo de SMTP se registra y no rompe la petición."""
    s = get_settings()
    if not s.smtp_host:
        BANDEJA_DESARROLLO.append(Correo(para, asunto, cuerpo))
        log.info("Correo (sin SMTP) para %s: %s\n%s", para, asunto, cuerpo)
        return
    mensaje = EmailMessage()
    mensaje["From"], mensaje["To"], mensaje["Subject"] = s.smtp_from, para, asunto
    mensaje.set_content(cuerpo)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(mensaje)
    except (smtplib.SMTPException, OSError):
        log.exception("No se pudo enviar el correo a %s", para)
