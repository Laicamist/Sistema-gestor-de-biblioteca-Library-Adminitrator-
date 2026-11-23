# Préstamos
DIAS_PRESTAMO = 7            # el mismo valor por defecto que usa SP_REGISTRAR_PRESTAMO
MAX_PRESTAMOS_ACTIVOS = 3    # lo hace cumplir el trigger; aquí solo es para mostrarlo en la UI

# Interfaz
TITULO_APP = "LIBRARY ADMINISTRATOR"

# Conexión: perfil con el que la app entra antes del login (usa BIB_LOGIN,
# que SOLO puede ejecutar SP_LOGIN). Después del login se reconecta con el
# perfil que se llama igual que el rol (ADMINISTRADOR, BIBLIOTECARIO, CONSULTA).
PERFIL_LOGIN = "LOGIN"

# Permisos de la aplicación
CONSULTAR = "CONSULTAR"            # lector: consultar ejemplar, disponibilidad, historial
PRESTAMOS = "PRESTAMOS"            # registrar préstamos y devoluciones
CATALOGO = "CATALOGO"              # alta de libros y ejemplares, ubicación y estado
ALUMNOS = "ALUMNOS"                # alta, cambios y baja de alumnos
REPORTES = "REPORTES"              # ver los reportes
ADMINISTRACION = "ADMINISTRACION"  # usuarios, auditoría, categorías, carreras, eliminar libros

PERMISOS = {
    "ADMINISTRADOR": {CONSULTAR, PRESTAMOS, CATALOGO, ALUMNOS, REPORTES, ADMINISTRACION},
    "BIBLIOTECARIO": {CONSULTAR, PRESTAMOS, CATALOGO, ALUMNOS, REPORTES},
    "CONSULTA": {CONSULTAR, REPORTES},
}

# Para los mensajes de "no tienes permiso para ..."
DESCRIPCION_PERMISOS = {
    CONSULTAR: "consultar el catálogo",
    PRESTAMOS: "registrar préstamos y devoluciones",
    CATALOGO: "administrar libros y ejemplares",
    ALUMNOS: "administrar alumnos",
    REPORTES: "ver reportes",
    ADMINISTRACION: "tareas de administración",
}
