"""Excepciones de dominio y su traducción a respuestas HTTP."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Error de regla de negocio. status_code permite mapearlo a HTTP."""

    status_code = 400

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(DomainError):
    status_code = 404


class Conflicto(DomainError):
    status_code = 409


class ReglaDeNegocio(DomainError):
    status_code = 422


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})
