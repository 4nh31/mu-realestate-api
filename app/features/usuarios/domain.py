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
    EXPEDIENTES_VER = "expedientes:ver"
    EXPEDIENTES_VALIDAR = "expedientes:validar"
    RESENAS_MODERAR = "resenas:moderar"
    CONTRATOS_GESTIONAR = "contratos:gestionar"
    ENTREGAS_GESTIONAR = "entregas:gestionar"
    AVISOS_ENVIAR = "avisos:enviar"
    CUENTA_USAR = "cuenta:usar"


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
    Permisos.EXPEDIENTES_VER: "Consultar expedientes legales, subir y descargar documentos",
    Permisos.EXPEDIENTES_VALIDAR: "Validar o rechazar documentos legales",
    Permisos.RESENAS_MODERAR: "Aprobar o rechazar reseñas",
    Permisos.CONTRATOS_GESTIONAR: "Administrar plantillas y generar borradores de contratos",
    Permisos.ENTREGAS_GESTIONAR: "Registrar actas de entrega y recepción de inmuebles",
    Permisos.AVISOS_ENVIAR: "Enviar avisos internos manuales",
    Permisos.CUENTA_USAR: "Usar la cuenta de cliente: favoritos, búsquedas, reseñas y ofrecer propiedades",
}

ROL_ADMINISTRADOR = "administrador"
ROL_ASESOR = "asesor"
ROL_CLIENTE = "cliente"
ROL_PROPIETARIO = "propietario"

# Roles del personal (panel). El administrador tiene todo salvo el permiso de cuenta de cliente.
PERMISOS_POR_ROL: dict[str, list[str]] = {
    ROL_ADMINISTRADOR: [p for p in DESCRIPCION_PERMISOS if p != Permisos.CUENTA_USAR],
    ROL_ASESOR: [
        Permisos.PROPIEDADES_VER,
        Permisos.PROPIEDADES_EDITAR,
        Permisos.SOLICITUDES_GESTIONAR,
        Permisos.PROSPECTOS_GESTIONAR,
        Permisos.CITAS_GESTIONAR,
        Permisos.DASHBOARD_VER,
        Permisos.EXPEDIENTES_VER,
        Permisos.CONTRATOS_GESTIONAR,
        Permisos.ENTREGAS_GESTIONAR,
    ],
}

# Roles de quienes se registran en el sitio público. Solo tienen el permiso de cuenta, así que ningún
# endpoint del panel les queda abierto.
PERMISOS_POR_ROL_CUENTA: dict[str, list[str]] = {
    ROL_CLIENTE: [Permisos.CUENTA_USAR],
    ROL_PROPIETARIO: [Permisos.CUENTA_USAR],
}
