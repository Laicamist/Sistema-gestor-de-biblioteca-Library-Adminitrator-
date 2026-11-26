from typing import List

from config import DIAS_PRESTAMO, CONSULTAR, PRESTAMOS
from Modelos import (
    BibliotecaError,
    EjemplarConsulta,
    HistorialPrestamo,
    AlumnoNoEncontradoError,
    EjemplarNoEncontradoError,
)
from Logic.servicio_base import ServicioBase

MAX_CODIGO = 30      # VARCHAR(30) en la base de datos
MAX_MATRICULA = 20   # VARCHAR(20) en la base de datos
MAX_DIAS = 60        # tope razonable para no capturar un préstamo de años por error


class PrestamoServicio(ServicioBase):

    #Consultas (cualquier rol)

    def consultar_ejemplar(self, codigo_barras: str) -> EjemplarConsulta:
        """Lo que se muestra al escanear un código con el lector."""
        self._exigir(CONSULTAR)
        codigo = self._requerido(codigo_barras, "el código de barras", MAX_CODIGO)
        ejemplar = self._dao().consultar_ejemplar(codigo)
        if ejemplar is None:
            raise EjemplarNoEncontradoError(self._mensaje_sin_ejemplar(codigo))
        return ejemplar

    def _mensaje_sin_ejemplar(self, codigo: str) -> str:
        """Si lo que se escaneó es el ISBN de un libro (la obra) y no la etiqueta de una
        copia, lo dice; así no parece que el lector falló."""
        try:
            libro = self._dao().buscar_libro(codigo)
        except BibliotecaError:  # el rol CONSULTA no puede leer LIBROS en MySQL
            libro = None
        if libro is None:
            return f"No existe un ejemplar con el código {codigo}."
        return (f"{codigo} es el ISBN de «{libro.titulo}», no la etiqueta de un ejemplar. "
                "Escanea el código de la copia (cada ejemplar tiene el suyo; se ven en Catálogo).")

    def historial(self, matricula: str) -> List[HistorialPrestamo]:
        self._exigir(CONSULTAR)
        return self._dao().historial_alumno(
            self._requerido(matricula, "la matrícula", MAX_MATRICULA))

    #Préstamo y devolución (administrador y bibliotecario)

    def prestar(self, codigo_barras: str, matricula: str, dias: int = DIAS_PRESTAMO) -> str:
        """Busca al alumno por matrícula y registra el préstamo con SP_REGISTRAR_PRESTAMO.
        Disponibilidad, alumno activo y máximo 3 préstamos los revisa el trigger."""
        sesion = self._exigir(PRESTAMOS)
        codigo = self._requerido(codigo_barras, "el código de barras", MAX_CODIGO)
        matricula = self._requerido(matricula, "la matrícula", MAX_MATRICULA)
        dias = self._entero(dias, "los días de préstamo", 1, MAX_DIAS)

        alumno = self._dao().buscar_alumno(matricula)
        if alumno is None:
            raise AlumnoNoEncontradoError(f"No existe un alumno con la matrícula {matricula}.")

        return self._dao().registrar_prestamo(codigo, alumno.id_alumno, sesion.id_usuario, dias)

    def devolver(self, codigo_barras: str) -> int:
        """Registra la devolución con SP_REGISTRAR_DEVOLUCION.
        Regresa los días de retraso para mostrarlos en pantalla."""
        self._exigir(PRESTAMOS)
        return self._dao().registrar_devolucion(
            self._requerido(codigo_barras, "el código de barras", MAX_CODIGO))
