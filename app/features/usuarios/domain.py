"""Dominio de usuarios: roles y catálogo de permisos (RBAC). Sin dependencias de frameworks."""


class Permisos:
    USUARIOS_GESTIONAR = "usuarios:gestionar"
    PROPIEDADES_VER = "propiedades:ver"
    PROPIEDADES_EDITAR = "propiedades:editar"
    PROPIEDADES_VER_INTERNO = "propiedades:ver_interno"
    PROPIEDADES_EDITAR_INTERNO = "propiedades:editar_interno"
    PROPIEDADES_PUBLICAR = "propiedades:publicar"
    SOLICITUDES_GESTIONAR = "solicitudes:gestionar"
    PROSPECTOS_GESTIONAR = "prospectos:gestionar"
    CITAS_GESTIONAR = "citas:gestionar"
    AUDITORIA_VER = "auditoria:ver"
    DASHBOARD_VER = "dashboard:ver"
    CATALOGOS_GESTIONAR = "catalogos:gestionar"


DESCRIPCION_PERMISOS: dict[str, str] = {
    Permisos.USUARIOS_GESTIONAR: "Crear, modificar y desactivar usuarios y asignar roles",
    Permisos.PROPIEDADES_VER: "Consultar propiedades en el panel",
    Permisos.PROPIEDADES_EDITAR: "Registrar y modificar datos públicos de propiedades",
    Permisos.PROPIEDADES_VER_INTERNO: "Consultar precio real, valor mínimo, propietario, comisión, dirección y notas",
    Permisos.PROPIEDADES_EDITAR_INTERNO: "Modificar los datos internos de una propiedad",
    Permisos.PROPIEDADES_PUBLICAR: "Publicar, ocultar, aprobar o rechazar propiedades",
    Permisos.SOLICITUDES_GESTIONAR: "Atender y asignar solicitudes de contacto y visita",
    Permisos.PROSPECTOS_GESTIONAR: "Gestionar prospectos y su seguimiento",
    Permisos.CITAS_GESTIONAR: "Agendar, confirmar, reprogramar y cancelar visitas",
    Permisos.AUDITORIA_VER: "Consultar la bitácora de auditoría",
    Permisos.DASHBOARD_VER: "Consultar indicadores y reportes",
    Permisos.CATALOGOS_GESTIONAR: "Administrar ciudades, zonas y amenidades",
}

ROL_ADMINISTRADOR = "administrador"
ROL_ASESOR = "asesor"

PERMISOS_POR_ROL: dict[str, list[str]] = {
    ROL_ADMINISTRADOR: list(DESCRIPCION_PERMISOS),
    ROL_ASESOR: [
        Permisos.PROPIEDADES_VER,
        Permisos.PROPIEDADES_EDITAR,
        Permisos.SOLICITUDES_GESTIONAR,
        Permisos.PROSPECTOS_GESTIONAR,
        Permisos.CITAS_GESTIONAR,
        Permisos.DASHBOARD_VER,
    ],
}
