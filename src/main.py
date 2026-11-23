from config import PERFIL_LOGIN
from ConexionSQL.dao import DAO
from Logic.sesion_servicio import SesionServicio
from Logic.prestamo_servicio import PrestamoServicio
from Logic.catalogo_servicio import CatalogoServicio
from Logic.alumno_servicio import AlumnoServicio
from Logic.reporte_servicio import ReporteServicio
from Logic.usuario_servicio import UsuarioServicio


def main():
    dao = None
    error = None
    try:
        dao = DAO()
    except Exception as e:
        error = ("No se pudo conectar a MySQL.\n"
                 "Revisa tu archivo .env o que el servidor esté encendido o exista.\n\n"
                 f"{e}")
    sesiones = SesionServicio(dao)
    servicios = {
        "prestamos": PrestamoServicio(dao, sesiones),
        "catalogo": CatalogoServicio(dao, sesiones),
        "alumnos": AlumnoServicio(dao, sesiones),
        "reportes": ReporteServicio(dao, sesiones),
        "usuarios": UsuarioServicio(dao, sesiones),
    }

    # Cuando exista la interfaz:
    # app = PantallaLogin(sesiones, servicios, error_inicial=error)
    # app.mainloop()
    if error:
        print(error)

    if dao is not None:
        dao.cerrar()


if __name__ == "__main__":
    main()
