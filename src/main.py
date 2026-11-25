import sys

from ConexionSQL.dao import DAO
from Logic.sesion_servicio import SesionServicio
from Logic.prestamo_servicio import PrestamoServicio
from Logic.catalogo_servicio import CatalogoServicio
from Logic.alumno_servicio import AlumnoServicio
from Logic.reporte_servicio import ReporteServicio
from Logic.usuario_servicio import UsuarioServicio


def crear_dao():
    """Conecta con el usuario de MySQL de login. Regresa (dao, None) o (None, mensaje de error)."""
    try:
        return DAO(), None
    except Exception as e:
        return None, ("No se pudo conectar a MySQL.\n"
                      "Revisa tu archivo .env o que el servidor esté encendido.\n\n"
                      f"{e}")


def main():
    dao, error = crear_dao()
    sesiones = SesionServicio(dao)
    servicios = {
        "prestamos": PrestamoServicio(dao, sesiones),
        "catalogo": CatalogoServicio(dao, sesiones),
        "alumnos": AlumnoServicio(dao, sesiones),
        "reportes": ReporteServicio(dao, sesiones),
        "usuarios": UsuarioServicio(dao, sesiones),
    }
    estado = {"dao": dao}

    def reconectar():
        """Botón 'Reintentar conexión' del login: crea otro DAO y se lo da a todos los servicios."""
        nuevo, mensaje = crear_dao()
        if nuevo is None:
            return mensaje
        estado["dao"] = nuevo
        sesiones.dao = nuevo
        for servicio in servicios.values():
            servicio.dao = nuevo
        return None

    try:
        from UI.app import iniciar
    except ImportError as e:
        print("No se pudo cargar la interfaz. Instala las dependencias con:\n"
              "    pip install -r Requisitos.txt\n\n"
              f"Detalle: {e}")
        if dao is not None:
            dao.cerrar()
        return 1

    try:
        return iniciar(sesiones, servicios, error, reconectar)
    finally:
        if estado["dao"] is not None:
            estado["dao"].cerrar()


if __name__ == "__main__":
    sys.exit(main())
