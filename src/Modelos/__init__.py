"""Esta carpeta contiene las dataclasses que representan las tablas y resultados de la
base de datos, y los errores de negocio.
Ademas de marcar la carpeta como un paquete de Python, para que pueda ser importada donde se necesite.
"""
from .entidades import (
    ESTADOS_REGISTRO,
    ESTADOS_EJEMPLAR,
    ESTADOS_PRESTAMO,
    Rol,
    Usuario,
    Carrera,
    Alumno,
    Categoria,
    Libro,
    Ejemplar,
    Prestamo,
    RegistroAuditoria,
    Sesion,
    Disponibilidad,
    EjemplarConsulta,
    HistorialPrestamo,
    PrestamoVencido,
    LibroSolicitado,
    LibroSinPrestamos,
    DisponibilidadLibro,
    AlumnoConVencidos,
    ResumenBiblioteca,
)
from .excepciones import (
    BibliotecaError,
    DatosInvalidosError,
    AccesoDenegadoError,
    LoginError,
    AlumnoNoEncontradoError,
    EjemplarNoEncontradoError,
    PrestamoError,
    SinConexionError,
)
