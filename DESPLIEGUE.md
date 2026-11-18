# Despliegue en el VPS de NEUBOX

Guía paso a paso para publicar MU Real Estate (front + API + base de datos) en un VPS Linux con Docker.
Al terminar, el sitio queda en `https://TU-DOMINIO` con certificado HTTPS gratuito que se renueva solo.

```
Internet ──► Caddy (contenedor "web", puertos 80/443)
               ├─ /            → aplicación de Vue (archivos estáticos)
               ├─ /api/...     → API de FastAPI (contenedor "api", red interna)
               └─ /archivos/.. → fotos de las propiedades (volumen "archivos")
             PostgreSQL (contenedor "db", sin acceso desde internet, volumen "pgdata")
```

## 0. Lo que se necesita antes

| Qué | Para qué |
|---|---|
| VPS con Ubuntu 22.04 o 24.04, acceso **root** por SSH | Correr los contenedores |
| Un dominio (p. ej. `murealestate.mx`) | Dirección del sitio y certificado HTTPS |
| Acceso a los dos repositorios de GitHub | Descargar el código en el servidor |
| (Opcional) Cuenta de correo SMTP | Enviar códigos de verificación y recuperación de contraseña |

Con 2 GB de RAM es suficiente. Todos los comandos de esta guía se ejecutan **en el servidor**, por SSH.

## 1. Apuntar el dominio al VPS

En el panel donde se administra el dominio (DNS), crear:

| Tipo | Nombre | Valor |
|---|---|---|
| A | `@` | IP pública del VPS |
| CNAME | `www` | `murealestate.mx` |

El cambio puede tardar de minutos a unas horas. Se comprueba con `ping murealestate.mx`: debe responder la IP del VPS.

## 2. Preparar el servidor

```bash
ssh root@IP_DEL_VPS

apt update && apt upgrade -y
# Firewall: solo SSH, HTTP y HTTPS
apt install -y ufw git
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

# Docker (instalador oficial)
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

## 3. Descargar el código

Los dos repositorios van **uno al lado del otro**; el nombre de la carpeta del front importa.

```bash
mkdir -p /opt/mu && cd /opt/mu
git clone https://github.com/4nh31/mu-realestate-api.git
git clone https://github.com/YairDev17/Front_MuRealEstate.git Front_MuRealEstate
```

Si un repositorio es privado, GitHub pedirá usuario y un *token* personal (Settings → Developer settings →
Personal access tokens) en lugar de la contraseña.

## 4. Configurar las variables

```bash
cd /opt/mu/mu-realestate-api
cp .env.production.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # ejecutar dos veces: una clave para cada variable
nano .env
```

Llenar como mínimo `DOMINIO`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `FRONTEND_URL` y
`API_PUBLIC_URL` con el dominio real. Si `JWT_SECRET_KEY` se deja con el valor de ejemplo, la API **no arranca**
(es intencional). Guardar con `Ctrl+O`, salir con `Ctrl+X`.

## 5. Levantar todo

```bash
cd /opt/mu/mu-realestate-api
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps        # los tres servicios deben decir "running"/"healthy"
docker compose -f docker-compose.prod.yml logs -f web   # Ctrl+C para salir
```

La primera vez tarda unos minutos (descarga imágenes y compila el front). La API aplica sola las migraciones
de la base de datos al arrancar. En el log de `web` debe aparecer `certificate obtained successfully`.

## 6. Crear el primer administrador

```bash
docker compose -f docker-compose.prod.yml exec api python -m app.scripts.crear_admin --email admin@murealestate.mx --nombre "Administrador"
```

Pide la contraseña (mínimo 8 caracteres). Con esa cuenta se entra en `https://TU-DOMINIO/admin`
y desde **Usuarios** se dan de alta los asesores.

> No ejecutar `app.scripts.datos_demo` en el servidor: es solo para pruebas locales y además se niega a
> correr fuera de `ENVIRONMENT=development`.

## 7. Comprobar

- `https://TU-DOMINIO` abre el sitio público con candado HTTPS.
- `https://TU-DOMINIO/health` responde `{"status":"ok"}`.
- En el panel: crear una propiedad, subir una foto y verla publicada en el sitio.

## 8. Actualizar a una nueva versión

```bash
cd /opt/mu/Front_MuRealEstate && git pull
cd /opt/mu/mu-realestate-api && git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Los datos y las fotos no se pierden: viven en los volúmenes `pgdata` y `archivos`.

## 9. Respaldos

```bash
mkdir -p /opt/mu/respaldos && cd /opt/mu/mu-realestate-api
# Base de datos
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres mu_realestate | gzip > /opt/mu/respaldos/bd_$(date +%F).sql.gz
# Fotos
docker compose -f docker-compose.prod.yml cp api:/app/storage /opt/mu/respaldos/archivos_$(date +%F)
```

Para hacerlo cada noche a las 3:00, agregar con `crontab -e`:

```
0 3 * * * cd /opt/mu/mu-realestate-api && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres mu_realestate | gzip > /opt/mu/respaldos/bd_$(date +\%F).sql.gz
```

Conviene descargar de vez en cuando la carpeta `respaldos` a otra computadora.

Restaurar un respaldo de la base:

```bash
gunzip -c /opt/mu/respaldos/bd_2026-11-20.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U postgres mu_realestate
```

## 10. Problemas comunes

| Síntoma | Causa probable |
|---|---|
| El navegador no abre el dominio | El DNS aún no apunta al VPS, o el firewall de NEUBOX bloquea 80/443 |
| `web` no obtiene certificado | Igual que arriba: Let's Encrypt necesita llegar al puerto 80 con el dominio |
| `api` se reinicia una y otra vez | Ver `docker compose -f docker-compose.prod.yml logs api`; casi siempre falta una variable en `.env` |
| No llegan los códigos de verificación | `SMTP_HOST` vacío o datos SMTP incorrectos |
| Error 413 al subir fotos | La foto pasa de `MAX_UPLOAD_MB` |
