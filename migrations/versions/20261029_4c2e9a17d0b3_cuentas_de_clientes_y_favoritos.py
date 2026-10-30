"""cuentas de clientes y propietarios, verificacion de correo y favoritos

Revision ID: 4c2e9a17d0b3
Revises: bb1196688f84
Create Date: 2026-10-29 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4c2e9a17d0b3'
down_revision: Union[str, Sequence[str], None] = 'bb1196688f84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Datos congelados en la migración (no se importan del dominio para que no cambien con el código).
PERMISOS = {
    "expedientes:ver": "Consultar expedientes legales, subir y descargar documentos",
    "expedientes:validar": "Validar o rechazar documentos legales",
    "resenas:moderar": "Aprobar o rechazar reseñas",
    "contratos:gestionar": "Administrar plantillas y generar borradores de contratos",
    "entregas:gestionar": "Registrar actas de entrega y recepción de inmuebles",
    "avisos:enviar": "Enviar avisos internos manuales",
    "cuenta:usar": "Usar la cuenta de cliente: favoritos, búsquedas, reseñas y ofrecer propiedades",
}
ROLES = {
    "cliente": "Cliente registrado en el sitio: favoritos, búsquedas y reseñas",
    "propietario": "Dueño que ofrece sus propiedades desde el sitio",
}
ASIGNACION = {
    "administrador": [p for p in PERMISOS if p != "cuenta:usar"],
    "asesor": ["expedientes:ver", "contratos:gestionar", "entregas:gestionar"],
    "cliente": ["cuenta:usar"],
    "propietario": ["cuenta:usar"],
}

proposito_codigo = postgresql.ENUM('verificar_correo', 'restablecer_password', name='proposito_codigo',
                                   create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuarios', sa.Column('telefono', sa.String(length=20), nullable=True))
    op.add_column('usuarios', sa.Column('email_verificado_en', sa.DateTime(timezone=True), nullable=True))
    # El personal existente lo dio de alta el administrador: se considera verificado.
    op.execute("UPDATE usuarios SET email_verificado_en = creado_en")

    op.add_column('propietarios', sa.Column('usuario_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(op.f('uq_propietarios_usuario_id'), 'propietarios', ['usuario_id'])
    op.create_foreign_key(op.f('fk_propietarios_usuario_id_usuarios'), 'propietarios', 'usuarios',
                          ['usuario_id'], ['id'], ondelete='SET NULL')

    proposito_codigo.create(op.get_bind())
    op.create_table('codigos_verificacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('proposito', proposito_codigo, nullable=False),
    sa.Column('codigo_hash', sa.String(length=100), nullable=False),
    sa.Column('expira_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('intentos', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('usado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('intentos >= 0 AND intentos <= 5', name=op.f('ck_codigos_verificacion_intentos_rango')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_codigos_verificacion_usuario_id_usuarios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_codigos_verificacion'))
    )
    op.create_index(op.f('ix_codigos_verificacion_usuario_id'), 'codigos_verificacion', ['usuario_id'], unique=False)

    op.create_table('favoritos',
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('propiedad_id', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['propiedad_id'], ['propiedades.id'], name=op.f('fk_favoritos_propiedad_id_propiedades'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_favoritos_usuario_id_usuarios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('usuario_id', 'propiedad_id', name=op.f('pk_favoritos'))
    )
    op.create_index(op.f('ix_favoritos_propiedad_id'), 'favoritos', ['propiedad_id'], unique=False)

    # Permisos y roles nuevos. Idempotente: en una base nueva la migración de datos iniciales ya pudo
    # insertar estos permisos porque lee el catálogo actual del dominio.
    conn = op.get_bind()
    for clave, descripcion in PERMISOS.items():
        conn.execute(sa.text("INSERT INTO permisos (clave, descripcion) VALUES (:c, :d) ON CONFLICT (clave) DO NOTHING"),
                     {"c": clave, "d": descripcion})
    for nombre, descripcion in ROLES.items():
        conn.execute(sa.text("INSERT INTO roles (nombre, descripcion) VALUES (:n, :d) ON CONFLICT (nombre) DO NOTHING"),
                     {"n": nombre, "d": descripcion})
    for rol, claves in ASIGNACION.items():
        for clave in claves:
            conn.execute(sa.text("INSERT INTO rol_permisos (rol_id, permiso_id) "
                                 "SELECT r.id, p.id FROM roles r, permisos p WHERE r.nombre = :r AND p.clave = :c "
                                 "ON CONFLICT DO NOTHING"), {"r": rol, "c": clave})


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM usuarios WHERE rol_id IN (SELECT id FROM roles WHERE nombre IN :r)")
                 .bindparams(sa.bindparam("r", expanding=True)), {"r": list(ROLES)})
    conn.execute(sa.text("DELETE FROM roles WHERE nombre IN :r").bindparams(sa.bindparam("r", expanding=True)),
                 {"r": list(ROLES)})
    conn.execute(sa.text("DELETE FROM permisos WHERE clave IN :c").bindparams(sa.bindparam("c", expanding=True)),
                 {"c": list(PERMISOS)})

    op.drop_index(op.f('ix_favoritos_propiedad_id'), table_name='favoritos')
    op.drop_table('favoritos')
    op.drop_index(op.f('ix_codigos_verificacion_usuario_id'), table_name='codigos_verificacion')
    op.drop_table('codigos_verificacion')
    proposito_codigo.drop(op.get_bind())
    op.drop_constraint(op.f('fk_propietarios_usuario_id_usuarios'), 'propietarios', type_='foreignkey')
    op.drop_constraint(op.f('uq_propietarios_usuario_id'), 'propietarios', type_='unique')
    op.drop_column('propietarios', 'usuario_id')
    op.drop_column('usuarios', 'email_verificado_en')
    op.drop_column('usuarios', 'telefono')
