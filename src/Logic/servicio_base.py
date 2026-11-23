from typing import Optional

from config import PERMISOS, DESCRIPCION_PERMISOS
from Modelos import Sesion, AccesoDenegadoError, DatosInvalidosError, SinConexionError


def tiene_permiso(rol: Optional[str], permiso: str) -> bool:
    """La UI la usa para ocultar o deshabilitar botones; los servicios, para bloquear."""
    return permiso in PERMISOS.get(rol or "", set())


class ServicioBase:
    """Lo que comparten todos los servicios: el DAO, la sesión actual,
    la revisión de permisos y las validaciones de texto."""

    def __init__(self, dao=None, sesiones=None):
        self.dao = dao
        self.sesiones = sesiones   # SesionServicio compartido (sabe quién inició sesión)

    def _dao(self):
        if self.dao is None:
            raise SinConexionError("Sin conexión a la base de datos.")
        return self.dao

    def _exigir(self, permiso: str) -> Sesion:
        """Regresa la sesión si el rol tiene el permiso; si no, lanza AccesoDenegadoError."""
        sesion = self.sesiones.sesion if self.sesiones is not None else None
        if sesion is None:
            raise AccesoDenegadoError("Inicia sesión primero.")
        if not tiene_permiso(sesion.rol, permiso):
            raise AccesoDenegadoError(
                f"Tu rol ({sesion.rol}) no tiene permiso para "
                f"{DESCRIPCION_PERMISOS.get(permiso, permiso)}.")
        return sesion

    # Validaciones de texto (los máximos son los VARCHAR de la base)

    @staticmethod
    def _requerido(valor, campo: str, maximo: int) -> str:
        texto = str(valor).strip() if valor is not None else ""
        if not texto:
            raise DatosInvalidosError(f"Captura {campo}.")
        if len(texto) > maximo:
            raise DatosInvalidosError(f"{campo.capitalize()} excede {maximo} caracteres.")
        return texto

    @staticmethod
    def _opcional(valor, campo: str, maximo: int) -> Optional[str]:
        texto = str(valor).strip() if valor is not None else ""
        if not texto:
            return None
        if len(texto) > maximo:
            raise DatosInvalidosError(f"{campo.capitalize()} excede {maximo} caracteres.")
        return texto

    @staticmethod
    def _entero(valor, campo: str, minimo: int, maximo: Optional[int] = None) -> int:
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            raise DatosInvalidosError(f"{campo.capitalize()} debe ser un número.") from None
        if numero < minimo or (maximo is not None and numero > maximo):
            rango = f"entre {minimo} y {maximo}" if maximo is not None else f"mayor o igual a {minimo}"
            raise DatosInvalidosError(f"{campo.capitalize()} debe ser {rango}.")
        return numero
