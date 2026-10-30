"""tipo de inmueble bodega

Revision ID: d3a8f0c6b214
Revises: b7e4c1a9f362
Create Date: 2026-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd3a8f0c6b214'
down_revision: Union[str, Sequence[str], None] = 'b7e4c1a9f362'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ANTERIORES = ('casa', 'departamento', 'terreno', 'lote', 'comercial')


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE tipo_propiedad ADD VALUE IF NOT EXISTS 'bodega'")


def downgrade() -> None:
    """Downgrade schema.

    PostgreSQL no permite quitar un valor de un enum: se recrea el tipo. Las bodegas pasan a «comercial».
    """
    op.execute("ALTER TABLE propiedades ALTER COLUMN tipo TYPE text")
    op.execute("UPDATE propiedades SET tipo = 'comercial' WHERE tipo = 'bodega'")
    op.execute("DROP TYPE tipo_propiedad")
    op.execute(f"CREATE TYPE tipo_propiedad AS ENUM {ANTERIORES}")
    op.execute("ALTER TABLE propiedades ALTER COLUMN tipo TYPE tipo_propiedad USING tipo::tipo_propiedad")
