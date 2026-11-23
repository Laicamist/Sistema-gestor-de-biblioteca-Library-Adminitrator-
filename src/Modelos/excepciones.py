"""Errores de negocio. La UI atrapa BibliotecaError y muestra el mensaje tal cual."""

class BibliotecaError(Exception):
    """Base de todos los errores que el usuario debe ver."""


class DatosInvalidosError(BibliotecaError):
    """Falta un dato, tiene mal formato, o la base lo rechazó (trigger, UNIQUE, FK)."""


class AccesoDenegadoError(BibliotecaError):
    """El rol no tiene permiso (lo detecta la app o MySQL con sus GRANT)."""


class LoginError(BibliotecaError):
    """Usuario o contraseña incorrectos, o cuenta inactiva."""


class AlumnoNoEncontradoError(BibliotecaError):
    pass


class EjemplarNoEncontradoError(BibliotecaError):
    pass


class PrestamoError(BibliotecaError):
    """El préstamo o la devolución no se guardó (el procedimiento hizo ROLLBACK)."""


class SinConexionError(Exception):
    """No se puede conectar con la base de datos."""
