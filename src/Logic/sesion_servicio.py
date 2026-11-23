from typing import Optional

from config import PERFIL_LOGIN
from Modelos import Sesion, LoginError, SinConexionError
from Logic.seguridad import hashear
from Logic.servicio_base import tiene_permiso

MAX_USUARIO = 30  # VARCHAR(30) en la base de datos


class SesionServicio:
    """Guarda quién inició sesión. Los demás servicios lo reciben para revisar permisos."""

    def __init__(self, dao=None):
        self.dao = dao
        self.sesion: Optional[Sesion] = None

    def _dao(self):
        if self.dao is None:
            raise SinConexionError("Sin conexión a la base de datos.")
        return self.dao

    def iniciar_sesion(self, nombre_usuario: str, contrasena: str) -> Sesion:
        """1. Valida y hashea la contraseña.
        2. SP_LOGIN con el usuario de MySQL de login (BIB_LOGIN, solo puede ejecutar SP_LOGIN).
        3. Se reconecta con el usuario de MySQL del rol (BIB_ADMIN, BIB_BIBLIOTECARIO...).
        4. Asigna @USUARIO_APP en la nueva conexión para la auditoría."""
        nombre_usuario = (nombre_usuario or "").strip()
        if not nombre_usuario or not contrasena:
            raise LoginError("Captura usuario y contraseña.")
        if len(nombre_usuario) > MAX_USUARIO:
            raise LoginError("USUARIO O CONTRASENA INCORRECTOS")

        dao = self._dao()
        sesion = dao.login(nombre_usuario, hashear(contrasena))
        try:
            dao.reconectar(sesion.rol)
        except Exception as e:
            raise SinConexionError(
                f"No se pudo conectar con el usuario de base de datos del rol {sesion.rol}. "
                f"Revisa DB_USER_{sesion.rol} en el .env.\n\n{e}") from e
        dao.establecer_usuario_app(sesion.nombre_usuario)
        self.sesion = sesion
        return sesion

    def cerrar_sesion(self):
        """Regresa a la conexión de login para que nadie use los permisos del rol anterior."""
        self.sesion = None
        if self.dao is not None:
            self.dao.reconectar(PERFIL_LOGIN)

    def puede(self, permiso: str) -> bool:
        """Para la UI: mostrar u ocultar botones del menú según el rol."""
        return self.sesion is not None and tiene_permiso(self.sesion.rol, permiso)
