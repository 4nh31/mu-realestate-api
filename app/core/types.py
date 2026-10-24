"""Tipos de columna reutilizables."""
import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Enum nativo de PostgreSQL que guarda el *valor* (en minúsculas) y no el nombre del miembro."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e], validate_strings=True)
