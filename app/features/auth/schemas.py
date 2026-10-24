from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Perfil(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str
    permisos: list[str]
