"""datos iniciales roles permisos y catalogos

Revision ID: 76e17c599c2f
Revises: 1538dc5c2bbf
Create Date: 2026-10-24 12:14:44.818158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.features.usuarios.domain import DESCRIPCION_PERMISOS, PERMISOS_POR_ROL


# revision identifiers, used by Alembic.
revision: str = '76e17c599c2f'
down_revision: Union[str, Sequence[str], None] = '1538dc5c2bbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Carga roles, permisos (RBAC) y catálogos base de Quintana Roo."""
    conn = op.get_bind()
    for clave, descripcion in DESCRIPCION_PERMISOS.items():
        conn.execute(sa.text("INSERT INTO permisos (clave, descripcion) VALUES (:c, :d)"), {"c": clave, "d": descripcion})
    descripciones = {"administrador": "Acceso total, incluida la información interna y la auditoría",
                     "asesor": "Gestión de propiedades, solicitudes, prospectos y visitas"}
    for rol, permisos in PERMISOS_POR_ROL.items():
        rol_id = conn.execute(sa.text("INSERT INTO roles (nombre, descripcion) VALUES (:n, :d) RETURNING id"),
                              {"n": rol, "d": descripciones[rol]}).scalar_one()
        for clave in permisos:
            conn.execute(sa.text("INSERT INTO rol_permisos (rol_id, permiso_id) "
                                 "SELECT :r, id FROM permisos WHERE clave = :c"), {"r": rol_id, "c": clave})
    for ciudad, zonas in CATALOGO.items():
        ciudad_id = conn.execute(sa.text("INSERT INTO ciudades (nombre, estado) VALUES (:n, 'Quintana Roo') RETURNING id"),
                                 {"n": ciudad}).scalar_one()
        for zona in zonas:
            conn.execute(sa.text("INSERT INTO zonas (ciudad_id, nombre) VALUES (:c, :n)"), {"c": ciudad_id, "n": zona})
    for amenidad in AMENIDADES:
        conn.execute(sa.text("INSERT INTO amenidades (nombre) VALUES (:n)"), {"n": amenidad})


def downgrade() -> None:
    for tabla in ("propiedad_amenidades", "amenidades", "zonas", "ciudades", "rol_permisos", "roles", "permisos"):
        op.execute(f"DELETE FROM {tabla}")


CATALOGO = {
    "Cancún": ["Centro", "Zona Hotelera", "Puerto Cancún", "Residencial Cumbres", "Residencial Río",
               "Huayacán", "Polígono Sur", "Alfredo V. Bonfil"],
    "Playa del Carmen": ["Centro", "Playacar", "Colosio", "Selvamar", "Corasol"],
    "Tulum": ["Centro", "Aldea Zamá", "La Veleta", "Región 15"],
    "Puerto Morelos": ["Centro", "Zona Urbana"],
}
AMENIDADES = ["Alberca", "Gimnasio", "Seguridad 24/7", "Roof garden", "Áreas verdes", "Elevador", "Casa club",
              "Acceso a playa", "Amueblado", "Pet friendly"]
