# MU Real Estate — API (backend)

API REST del **panel administrativo y CRM** de MU Real Estate, unidad inmobiliaria de Cano & Asociados.

- **Python 3.13 + FastAPI** · **PostgreSQL 16** · **SQLAlchemy 2** · **Alembic**
- Autenticación **JWT** + contraseñas con **bcrypt** + control de acceso **por roles (RBAC)**
- Documentación interactiva **Swagger UI** en `/docs` y ReDoc en `/redoc`
- Arquitectura **Clean Architecture + vertical slices**

## Estructura

```
app/
├── core/                 # Núcleo compartido (transversal)
│   ├── config.py         # Variables de entorno
│   ├── database.py       # Engine, sesión y Base de SQLAlchemy
│   ├── security.py       # bcrypt + JWT
│   ├── deps.py           # Usuario autenticado y require_permission()
│   ├── exceptions.py     # Errores de dominio → HTTP
│   └── models.py         # Registro de modelos para Alembic
├── features/             # Un vertical slice por módulo
│   ├── auth/
│   ├── usuarios/
│   ├── propiedades/
│   │   ├── domain.py         # Enumeraciones y reglas de negocio puras
│   │   ├── application.py    # Casos de uso
│   │   ├── infrastructure.py # Modelos ORM y repositorio
│   │   ├── schemas.py        # Contratos de entrada/salida (Pydantic)
│   │   └── api.py            # Endpoints FastAPI
│   ├── catalogos/  auditoria/
│   └── solicitudes/  prospectos/  agenda/   # modelos listos; endpoints en sprints siguientes
└── scripts/crear_admin.py
migrations/               # Alembic (esquema inicial + datos iniciales)
tests/                    # Pytest (unitarias e integración sobre PostgreSQL)
```

Regla de dependencia: `api → application → domain`; `infrastructure` implementa el acceso a datos.
`domain.py` no importa FastAPI ni SQLAlchemy.

## Puesta en marcha con Docker

```bash
cp .env.example .env            # y cambiar JWT_SECRET_KEY
docker compose up --build       # levanta PostgreSQL y la API (aplica migraciones)
docker compose exec api python -m app.scripts.crear_admin --email admin@murealestate.mx
```

Abrir http://localhost:8000/docs

## Desarrollo local (sin Docker para la API)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d db
alembic upgrade head
python -m app.scripts.crear_admin --email admin@murealestate.mx
uvicorn app.main:app --reload
```

## Migraciones

```bash
alembic revision --autogenerate -m "descripcion del cambio"   # tras modificar modelos
alembic upgrade head
alembic downgrade -1
```

## Pruebas

Requieren una base `mu_realestate_test` (se migra automáticamente):

```bash
docker compose exec db createdb -U postgres mu_realestate_test
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mu_realestate_test pytest
```

## Roles iniciales

| Rol | Permisos |
|---|---|
| administrador | Todos (incluye datos internos, publicación, usuarios y auditoría) |
| asesor | Ver/editar propiedades (sin datos internos), solicitudes, prospectos, citas y dashboard |
