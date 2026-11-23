from typing import List

from config import REPORTES, ADMINISTRACION
from Modelos import (
    AlumnoConVencidos,
    DisponibilidadLibro,
    LibroSinPrestamos,
    LibroSolicitado,
    PrestamoVencido,
    RegistroAuditoria,
)
from Logic.servicio_base import ServicioBase


class ReporteServicio(ServicioBase):
    """Los reportes que pide el proyecto, leídos de las vistas de la base."""

    def prestamos_vencidos(self) -> List[PrestamoVencido]:
        """Reporte 1: alumnos con préstamos vencidos (JOIN de 5 tablas + FN_DIAS_RETRASO)."""
        self._exigir(REPORTES)
        return self._dao().prestamos_vencidos()

    def alumnos_con_vencidos(self) -> List[AlumnoConVencidos]:
        """Reporte 1b: alumnos con préstamos vencidos agrupados (CTE, GROUP BY, SUM, MAX, RANK)."""
        self._exigir(REPORTES)
        return self._dao().alumnos_con_vencidos()

    def libros_mas_solicitados(self) -> List[LibroSolicitado]:
        """Reporte 2: ranking con GROUP BY, HAVING, COUNT y RANK()."""
        self._exigir(REPORTES)
        return self._dao().libros_mas_solicitados()

    def libros_sin_prestamos(self) -> List[LibroSinPrestamos]:
        """Extra: NOT EXISTS."""
        self._exigir(REPORTES)
        return self._dao().libros_sin_prestamos()

    def disponibilidad_general(self) -> List[DisponibilidadLibro]:
        """Extra: subconsulta + FN_DISPONIBLES_LIBRO."""
        self._exigir(REPORTES)
        return self._dao().disponibilidad_general()

    def auditoria(self, limite: int = 200) -> List[RegistroAuditoria]:
        """Solo administrador: los últimos movimientos registrados por los triggers."""
        self._exigir(ADMINISTRACION)
        return self._dao().listar_auditoria(self._entero(limite, "el límite", 1, 5000))
