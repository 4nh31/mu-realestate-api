from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Perfil(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str
    telefono: str | None = None
    email_verificado: bool = False
    permisos: list[str]
