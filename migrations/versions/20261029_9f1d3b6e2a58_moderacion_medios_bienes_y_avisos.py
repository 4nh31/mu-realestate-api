"""moderacion persistente, bienes incluidos y avisos para clientes

Revision ID: 9f1d3b6e2a58
Revises: 4c2e9a17d0b3
Create Date: 2026-10-29 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9f1d3b6e2a58'
down_revision: Union[str, Sequence[str], None] = '4c2e9a17d0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tipo_aviso = postgresql.ENUM('solicitud', 'publicacion', 'cita', 'favorito', 'busqueda', 'resena', 'documento',
                             'interno', 'sistema', name='tipo_aviso', create_type=False)

BIENES = {
    "Electrodomésticos": ["Refrigerador", "Estufa", "Horno empotrado", "Microondas", "Lavavajillas", "Lavadora",
                          "Secadora", "Campana extractora", "Calentador solar"],
    "Climatización": ["Aire acondicionado", "Calefacción central", "Minisplit"],
    "Muebles": ["Cocina integral", "Clósets empotrados", "Armarios", "Muebles de sala", "Comedor"],
    "Instalaciones": ["Paneles solares", "Cisterna", "Generador eléctrico", "Sistema de filtrado de agua"],
    "Seguridad y tecnología": ["Cámaras de seguridad", "Sistema de alarma", "Intercomunicador",
                               "Automatización de puertas"],
}


def upgrade() -> None:
    """Upgrade schema."""
    # ---- Moderación de propiedades ----
    op.add_column('propiedades', sa.Column('antiguedad_anios', sa.SmallInteger(), nullable=True))
    op.add_column('propiedades', sa.Column('destacada', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('propiedades', sa.Column('motivo_rechazo', sa.Text(), nullable=True))
    op.add_column('propiedades', sa.Column('revisado_por', sa.Integer(), nullable=True))
    op.add_column('propiedades', sa.Column('revisado_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('propiedades', sa.Column('publicada_en', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(op.f('fk_propiedades_revisado_por_usuarios'), 'propiedades', 'usuarios',
                          ['revisado_por'], ['id'], ondelete='SET NULL')
    # Antes el motivo no se guardaba: las ya rechazadas quedan marcadas para cumplir la restricción.
    op.execute("UPDATE propiedades SET motivo_rechazo = 'Motivo no registrado' WHERE estado_publicacion = 'rechazada'")
    op.execute("UPDATE propiedades SET publicada_en = actualizado_en "
               "WHERE estado_publicacion IN ('publicada', 'oculta')")
    op.create_check_constraint(op.f('ck_propiedades_antiguedad_no_negativa'), 'propiedades',
                               'antiguedad_anios IS NULL OR antiguedad_anios >= 0')
    op.create_check_constraint(op.f('ck_propiedades_rechazo_con_motivo'), 'propiedades',
                               "estado_publicacion <> 'rechazada' OR motivo_rechazo IS NOT NULL")
    op.create_index('ix_propiedades_origen_estado', 'propiedades', ['origen', 'estado_publicacion'], unique=False)

    # ---- Bienes incluidos ----
    bienes = op.create_table('bienes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('categoria', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bienes')),
    sa.UniqueConstraint('nombre', name=op.f('uq_bienes_nombre'))
    )
    op.create_table('propiedad_bienes',
    sa.Column('propiedad_id', sa.Integer(), nullable=False),
    sa.Column('bien_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['bien_id'], ['bienes.id'], name=op.f('fk_propiedad_bienes_bien_id_bienes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['propiedad_id'], ['propiedades.id'], name=op.f('fk_propiedad_bienes_propiedad_id_propiedades'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('propiedad_id', 'bien_id', name=op.f('pk_propiedad_bienes'))
    )
    op.bulk_insert(bienes, [{"nombre": n, "categoria": c} for c, nombres in BIENES.items() for n in nombres])

    # ---- Avisos para personal y clientes ----
    tipo_aviso.create(op.get_bind())
    op.add_column('avisos', sa.Column('tipo', tipo_aviso, server_default='solicitud', nullable=False))
    op.add_column('avisos', sa.Column('mensaje', sa.Text(), nullable=True))
    op.add_column('avisos', sa.Column('enlace', sa.String(length=255), nullable=True))
    op.add_column('avisos', sa.Column('autor_id', sa.Integer(), nullable=True))
    op.add_column('avisos', sa.Column('por_correo', sa.Boolean(), server_default='false', nullable=False))
    op.create_foreign_key(op.f('fk_avisos_autor_id_usuarios'), 'avisos', 'usuarios', ['autor_id'], ['id'],
                          ondelete='SET NULL')
    op.create_index('ix_avisos_usuario_leido', 'avisos', ['usuario_id', 'leido'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_avisos_usuario_leido', table_name='avisos')
    op.drop_constraint(op.f('fk_avisos_autor_id_usuarios'), 'avisos', type_='foreignkey')
    for columna in ('por_correo', 'autor_id', 'enlace', 'mensaje', 'tipo'):
        op.drop_column('avisos', columna)
    tipo_aviso.drop(op.get_bind())

    op.drop_table('propiedad_bienes')
    op.drop_table('bienes')

    op.drop_index('ix_propiedades_origen_estado', table_name='propiedades')
    op.drop_constraint(op.f('ck_propiedades_rechazo_con_motivo'), 'propiedades', type_='check')
    op.drop_constraint(op.f('ck_propiedades_antiguedad_no_negativa'), 'propiedades', type_='check')
    op.drop_constraint(op.f('fk_propiedades_revisado_por_usuarios'), 'propiedades', type_='foreignkey')
    for columna in ('publicada_en', 'revisado_en', 'revisado_por', 'motivo_rechazo', 'destacada', 'antiguedad_anios'):
        op.drop_column('propiedades', columna)
