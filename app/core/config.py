"""Configuración central de la aplicación, leída desde variables de entorno (.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MU Real Estate API"
    app_version: str = "0.8.0"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mu_realestate"

    jwt_secret_key: str = "CAMBIAR_EN_PRODUCCION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:5173"]
    frontend_url: str = "http://localhost:5173"
    api_public_url: str = "http://localhost:8000"

    # Archivos: "local" guarda en STORAGE_DIR; "s3" usa un bucket compatible (DigitalOcean Spaces).
    storage_backend: str = "local"
    storage_dir: str = "./storage"
    s3_endpoint_url: str | None = None
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_public_base_url: str = ""
    max_upload_mb: int = 10

    # Correo: con SMTP_HOST vacío los mensajes solo se escriben en el log (desarrollo y pruebas).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "MU Real Estate <no-responder@murealestate.mx>"
    codigo_verificacion_minutos: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
