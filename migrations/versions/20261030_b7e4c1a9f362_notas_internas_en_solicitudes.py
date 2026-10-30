"""notas internas en solicitudes

Revision ID: b7e4c1a9f362
Revises: 9f1d3b6e2a58
Create Date: 2026-10-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4c1a9f362'
down_revision: Union[str, Sequence[str], None] = '9f1d3b6e2a58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('solicitudes', sa.Column('notas', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('solicitudes', 'notas')
