# MU Real Estate — API (backend)

API REST del **panel administrativo y CRM** de MU Real Estate, unidad inmobiliaria de Cano & Asociados.

| Tecnología | Uso |
|---|---|
| Python 3.12+ y FastAPI | API REST |
| PostgreSQL 16 | Base de datos |
| SQLAlchemy 2 | ORM (modelos y consultas) |
| **Alembic** | **Migraciones**: crea y actualiza las tablas |
| PyJWT + bcrypt | Inicio de sesión con token y contraseñas cifradas |
| Pytest | Pruebas automáticas |
| Docker / Docker Compose | Levantar todo con un solo comando |

La documentación interactiva (**Swagger UI**) queda en `http://localhost:8000/docs` cuando la API está corriendo.

---

## 1. Qué necesitas tener instalado

Elige **una** de las dos formas de ejecutarlo.

### Opción A — Con Docker (la más fácil, recomendada)

| Programa | Para qué | Descarga |
|---|---|---|
| Git | Clonar el repositorio | https://git-scm.com/downloads |
| Docker Desktop | Correr PostgreSQL y la API sin instalarlos | https://www.docker.com/products/docker-desktop/ |

En Windows, Docker Desktop te pedirá activar **WSL 2**; acepta y reinicia.
No necesitas instalar Python ni PostgreSQL.

### Opción B — Sin Docker (desarrollo local)

| Programa | Versión | Descarga |
|---|---|---|
| Git | cualquiera | https://git-scm.com/downloads |
| Python | 3.12 o superior (marca **"Add python.exe to PATH"** al instalar) | https://www.python.org/downloads/ |
| PostgreSQL | 16 | https://www.postgresql.org/download/ |

Opcional: **VS Code** con la extensión *Python*, y **pgAdmin** o **DBeaver** para ver la base de datos.

---

## 2. Descargar el proyecto

```bash
git clone https://github.com/4nh31/mu-realestate-api.git
cd mu-realestate-api
```

Copia el archivo de configuración de ejemplo:

```bash
# Windows (PowerShell)
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Abre `.env` y cambia `JWT_SECRET_KEY` por una clave larga. Puedes generarla con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> `.env` **nunca** se sube a GitHub (ya está en `.gitignore`).

---

## 3A. Ejecutar con Docker

```bash
docker compose up --build
```

Esto:
1. Levanta PostgreSQL 16 en el puerto 5432.
2. Construye la imagen de la API.
3. **Ejecuta automáticamente `alembic upgrade head`** (crea las 18 tablas y carga roles, permisos y catálogos).
4. Levanta la API en http://localhost:8000.

Crear el primer usuario administrador (en otra terminal, con los contenedores corriendo):

```bash
docker compose exec api python -m app.scripts.crear_admin --email admin@murealestate.mx --nombre "Administrador"
```

Te pedirá la contraseña (mínimo 8 caracteres).

Detener: `Ctrl + C` y luego `docker compose down` (los datos se conservan en el volumen `pgdata`).

---

## 3B. Ejecutar sin Docker

**1. Crear la base de datos** (con pgAdmin o desde la terminal de PostgreSQL):

```sql
CREATE DATABASE mu_realestate;
```

Revisa que `DATABASE_URL` en `.env` tenga tu usuario y contraseña de PostgreSQL:

```
DATABASE_URL=postgresql+psycopg://postgres:TU_CONTRASEÑA@localhost:5432/mu_realestate
```

**2. Crear el entorno virtual e instalar dependencias:**

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-dev.txt
```

> Si PowerShell bloquea la activación: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**3. Crear las tablas con Alembic:**

```bash
alembic upgrade head
```

**4. Crear el administrador y levantar la API:**

```bash
python -m app.scripts.crear_admin --email admin@murealestate.mx --nombre "Administrador"
uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs (la raíz http://localhost:8000 también te redirige ahí).

---

## 4. Probar la API en Swagger

1. Entra a http://localhost:8000/docs.
2. Clic en **Authorize** (candado).
3. En `username` escribe el correo del administrador y en `password` su contraseña. Deja vacíos `client_id` y `client_secret`.
4. Clic en **Authorize** → **Close**. Los endpoints con candado ya se pueden ejecutar con **Try it out** → **Execute**.

Los endpoints bajo `/api/v1/publico/...` no requieren sesión.

---

## 5. Alembic 

| Revisión | Qué hace |
|---|---|
| `1538dc5c2bbf` esquema inicial | Crea 18 tablas, tipos ENUM, llaves, índices y restricciones |
| `76e17c599c2f` datos iniciales | Roles (administrador, asesor), 12 permisos, ciudades, zonas y amenidades de Q. Roo |

```bash
alembic upgrade head                                  # aplicar todo lo pendiente
alembic current                                       # ver en qué versión está la BD
alembic history                                       # listar migraciones
alembic downgrade -1                                  # deshacer la última
alembic revision --autogenerate -m "agrega campo X"   # después de cambiar un modelo
```

Regla: **nunca** modifiques tablas a mano; cambia el modelo en `infrastructure.py` y genera una migración.

---

## 6. Pruebas

```bash
pytest -v
```

No necesitas configurar nada extra: las pruebas toman el usuario y la contraseña de PostgreSQL de tu `.env`
y usan una base aparte llamada `mu_realestate_test`, que **se crea sola** si no existe.
Tu base real (`mu_realestate`) nunca se modifica.

Si quieres usar otra base para pruebas, define `TEST_DATABASE_URL` antes de ejecutar `pytest`.

Resultado esperado: `26 passed`.

## 7. Estructura (Clean Architecture + vertical slices)

```
app/
├── core/                 # Núcleo compartido
│   ├── config.py         # Variables de entorno (.env)
│   ├── database.py       # Conexión y Base de SQLAlchemy
│   ├── security.py       # bcrypt + JWT
│   ├── deps.py           # Usuario autenticado y require_permission()
│   ├── exceptions.py     # Errores de dominio → respuestas HTTP
│   └── models.py         # Registro de modelos para Alembic
├── features/             # Un "slice" por módulo
│   ├── propiedades/
│   │   ├── domain.py         # Reglas de negocio puras (sin FastAPI ni SQLAlchemy)
│   │   ├── application.py    # Casos de uso
│   │   ├── infrastructure.py # Modelos ORM y repositorio
│   │   ├── schemas.py        # Entrada/salida (Pydantic)
│   │   └── api.py            # Endpoints
│   ├── auth/  usuarios/  auditoria/  catalogos/
│   └── solicitudes/  prospectos/  agenda/   # modelos listos; endpoints en próximos sprints
└── scripts/crear_admin.py
migrations/               # Alembic
tests/                    # Pytest
```

Para agregar un módulo nuevo, copia la estructura de `features/propiedades/`, registra sus modelos en `app/core/models.py` y su router en `app/main.py`.

---

## 8. Roles iniciales

| Rol | Puede |
|---|---|
| administrador | Todo: usuarios, datos internos de propiedades, publicación y auditoría |
| asesor | Ver/editar propiedades (sin datos internos), solicitudes, prospectos, citas y dashboard |

---

## 9. Problemas comunes

| Error | Solución |
|---|---|
| `connection refused` al puerto 5432 | PostgreSQL no está corriendo, o `DATABASE_URL` tiene otro puerto/contraseña |
| `database "mu_realestate" does not exist` | Crea la base de datos (paso 3B.1) |
| `port is already allocated` (Docker) | Ya tienes un PostgreSQL local en el 5432; detenlo o cambia el puerto en `docker-compose.yml` |
| `relation "usuarios" does not exist` | Falta `alembic upgrade head` |
| `Ejecute primero: alembic upgrade head` al crear admin | Igual: aplica las migraciones primero |
| 401 en Swagger | No has hecho **Authorize**, o el token expiró (60 min) |
| 403 en Swagger | Tu rol no tiene el permiso de ese endpoint |
| `la autentificación password falló para el usuario postgres` | La contraseña de `DATABASE_URL` en `.env` no es la de tu PostgreSQL |
