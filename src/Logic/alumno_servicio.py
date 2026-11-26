from typing import List, Optional

from config import ALUMNOS, ADMINISTRACION
from Modelos import Alumno, AlumnoListado, Carrera, AlumnoNoEncontradoError, DatosInvalidosError
from Logic.servicio_base import ServicioBase

# Tamaños de las columnas en la base de datos
MAX_MATRICULA = 20
MAX_NOMBRE = 100
MAX_CORREO = 100
MAX_TELEFONO = 15
MAX_CARRERA = 80


class AlumnoServicio(ServicioBase):

    #Carreras

    def listar_carreras(self) -> List[Carrera]:
        self._exigir(ALUMNOS)
        return self._dao().listar_carreras()

    def agregar_carrera(self, nombre: str) -> Carrera:
        self._exigir(ADMINISTRACION)
        carrera = Carrera(nombre=self._requerido(nombre, "el nombre de la carrera",
                                                 MAX_CARRERA).upper())
        self._dao().agregar_carrera(carrera)
        return carrera

    #Alumnos

    def listar(self) -> List[AlumnoListado]:
        self._exigir(ALUMNOS)
        return self._dao().listar_alumnos()

    def buscar(self, matricula: str) -> Alumno:
        self._exigir(ALUMNOS)
        matricula = self._requerido(matricula, "la matrícula", MAX_MATRICULA)
        alumno = self._dao().buscar_alumno(matricula)
        if alumno is None:
            raise AlumnoNoEncontradoError(f"No existe un alumno con la matrícula {matricula}.")
        return alumno

    def _correo(self, correo) -> Optional[str]:
        correo = self._opcional(correo, "el correo", MAX_CORREO)
        if correo and ("@" not in correo or correo.startswith("@") or correo.endswith("@")):
            raise DatosInvalidosError("El correo no tiene un formato válido.")
        return correo.upper() if correo else None

    def _telefono(self, telefono) -> Optional[str]:
        telefono = self._opcional(telefono, "el teléfono", MAX_TELEFONO)
        if telefono and not telefono.isdigit():
            raise DatosInvalidosError("El teléfono solo debe tener números.")
        return telefono

    def registrar(self, matricula: str, nombre_completo: str, id_carrera: int, semestre,
                  correo: Optional[str] = None, telefono: Optional[str] = None) -> Alumno:
        self._exigir(ALUMNOS)
        matricula = self._requerido(matricula, "la matrícula", MAX_MATRICULA)
        if self._dao().buscar_alumno(matricula) is not None:
            raise DatosInvalidosError(f"Ya existe un alumno con la matrícula {matricula}.")
        alumno = Alumno(
            matricula=matricula,
            nombre_completo=self._requerido(nombre_completo, "el nombre", MAX_NOMBRE).upper(),
            id_carrera=self._entero(id_carrera, "la carrera", 1),
            semestre=self._entero(semestre, "el semestre", 1, 12),
            correo=self._correo(correo),
            telefono=self._telefono(telefono),
        )
        self._dao().agregar_alumno(alumno)
        return alumno

    def actualizar(self, matricula: str, nombre_completo: str, id_carrera: int, semestre,
                   correo: Optional[str] = None, telefono: Optional[str] = None) -> Alumno:
        """La matrícula no cambia; la auditoría registra carrera y semestre anteriores y nuevos."""
        alumno = self.buscar(matricula)
        alumno.nombre_completo = self._requerido(nombre_completo, "el nombre", MAX_NOMBRE).upper()
        alumno.id_carrera = self._entero(id_carrera, "la carrera", 1)
        alumno.semestre = self._entero(semestre, "el semestre", 1, 12)
        alumno.correo = self._correo(correo)
        alumno.telefono = self._telefono(telefono)
        self._dao().actualizar_alumno(alumno)
        return alumno

    def dar_de_baja(self, matricula: str) -> None:
        """No se da de baja a quien todavía tiene libros prestados."""
        alumno = self.buscar(matricula)
        if alumno.estado == "INACTIVO":
            raise DatosInvalidosError("El alumno ya está dado de baja.")
        activos = self._dao().contar_prestamos_activos(alumno.id_alumno)
        if activos:
            raise DatosInvalidosError(
                f"El alumno tiene {activos} préstamo(s) activo(s); registra las devoluciones primero.")
        self._dao().cambiar_estado_alumno(alumno.id_alumno, "INACTIVO")

    def reactivar(self, matricula: str) -> None:
        alumno = self.buscar(matricula)
        if alumno.estado == "ACTIVO":
            raise DatosInvalidosError("El alumno ya está activo.")
        self._dao().cambiar_estado_alumno(alumno.id_alumno, "ACTIVO")
