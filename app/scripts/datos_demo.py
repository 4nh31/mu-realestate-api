"""Carga datos de demostración para probar el front en local: personal y propiedades publicadas.

Uso:  python -m app.scripts.datos_demo
Solo funciona con ENVIRONMENT=development. Es idempotente: no duplica lo que ya existe.
Contraseñas de demostración (solo para la base local):
    admin@demo.mu    Demo1234   (administrador)
    asesor@demo.mu   Demo1234   (asesor)
"""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.features.catalogos.infrastructure import Amenidad, Bien, Zona
from app.features.propiedades.domain import EstadoPublicacion, Operacion, TipoMedio, TipoPropiedad
from app.features.propiedades.infrastructure import Medio, Propiedad, PropiedadRepository
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository

PASSWORD = "Demo1234"
PERSONAL = [("admin@demo.mu", "Administrador Demo", "administrador"),
            ("asesor@demo.mu", "Asesora Demo", "asesor")]
PROPIEDADES = [
    ("Casa con alberca en Residencial Cumbres", Operacion.VENTA, TipoPropiedad.CASA, "Residencial Cumbres",
     4, "3.5", 2, "320", 6, "6850000", True, ["Alberca", "Seguridad 24/7"], ["Refrigerador", "Minisplit"]),
    ("Departamento frente al mar en Zona Hotelera", Operacion.VENTA, TipoPropiedad.DEPARTAMENTO, "Zona Hotelera",
     2, "2", 1, "110", 3, "5200000", True, ["Acceso a playa", "Gimnasio", "Elevador"], ["Cocina integral"]),
    ("Departamento amueblado en Puerto Cancún", Operacion.RENTA, TipoPropiedad.DEPARTAMENTO, "Puerto Cancún",
     2, "2", 1, "95", 2, "32000", False, ["Amueblado", "Alberca", "Pet friendly"], ["Lavadora", "Secadora"]),
    ("Terreno residencial en Polígono Sur", Operacion.VENTA, TipoPropiedad.TERRENO, "Polígono Sur",
     None, None, None, "250", None, "1450000", False, [], []),
]

# Fotos del diseño (Unsplash). Son URLs externas, así que no se guardan en el almacenamiento.
FOTOS = [f"https://images.unsplash.com/photo-{f}?w=1200&h=700&fit=crop&auto=format" for f in (
    "1613490493576-7fde63acd811", "1724582586529-62622e50c0b3", "1600210491369-e753d80a41f3",
    "1665249934445-1de680641f50", "1628592102751-ba83b0314276", "1670589953882-b94c9cb380f5",
    "1706855203772-c249b75fe016", "1564078516393-cf04bd966897", "1628012209120-d9db7abf7eab",
    "1679364297777-1db77b6199be", "1600596542815-ffad4c1539a9", "1600607687939-ce8a6c25118c",
)]
FOTOS_POR_PROPIEDAD = 3


def main() -> None:
    if get_settings().environment != "development":
        raise SystemExit("Solo se cargan datos de demostración con ENVIRONMENT=development")
    with SessionLocal() as db:
        usuarios = UsuarioRepository(db)
        ids = {}
        for email, nombre, rol in PERSONAL:
            u = usuarios.obtener_por_email(email)
            if u is None:
                u = usuarios.agregar(Usuario(nombre=nombre, email=email, rol=usuarios.obtener_rol(rol),
                                             password_hash=hash_password(PASSWORD),
                                             email_verificado_en=datetime.now(UTC)))
            ids[rol] = u.id
        repo = PropiedadRepository(db)
        for (titulo, op, tipo, zona, rec, banos, est, m2, antig, precio, dest, amen, bienes) in PROPIEDADES:
            if db.scalar(select(Propiedad).where(Propiedad.titulo == titulo)):
                continue
            ahora = datetime.now(UTC)
            repo.agregar(Propiedad(
                titulo=titulo, operacion=op, tipo=tipo, recamaras=rec, estacionamientos=est,
                zona_id=db.scalar(select(Zona.id).where(Zona.nombre == zona)),
                banos=Decimal(banos) if banos else None, superficie_m2=Decimal(m2), antiguedad_anios=antig,
                precio_publico=Decimal(precio), destacada=dest, asesor_id=ids["asesor"],
                estado_publicacion=EstadoPublicacion.PUBLICADA, publicada_en=ahora, revisado_en=ahora,
                revisado_por=ids["administrador"],
                descripcion=f"{titulo}. Propiedad de demostración cargada para probar el sitio.",
                amenidades=list(db.scalars(select(Amenidad).where(Amenidad.nombre.in_(amen)))),
                bienes=list(db.scalars(select(Bien).where(Bien.nombre.in_(bienes)))),
            ))
        db.flush()
        # Tres fotos por propiedad de demostración que todavía no tenga ninguna.
        demo = db.scalars(select(Propiedad).where(Propiedad.titulo.in_([p[0] for p in PROPIEDADES]))
                          .order_by(Propiedad.id))
        for n, propiedad in enumerate(demo):
            if propiedad.medios:
                continue
            for i in range(FOTOS_POR_PROPIEDAD):
                url = FOTOS[(n * FOTOS_POR_PROPIEDAD + i) % len(FOTOS)]
                propiedad.medios.append(Medio(tipo=TipoMedio.FOTO, url=url, orden=i, es_portada=i == 0))
        db.commit()
    print("Datos de demostración listos. Personal: " + ", ".join(e for e, _, _ in PERSONAL)
          + f" (contraseña {PASSWORD}).")


if __name__ == "__main__":
    main()
