from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QProgressBar, QScrollArea, QVBoxLayout, QWidget,
)

from config import PRESTAMOS
from UI.componentes import BotonIcono, EtiquetaIcono, Insignia, PanelVidrio, Tabla, etiqueta, repulir
from UI.pantallas.base import Pantalla

MAX_VENCIDOS = 6      # filas de la tabla de vencidos en el inicio (el reporte completo está en Reportes)
MAX_SOLICITADOS = 5   # libros en la lista de más solicitados


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _vaciar(layout):
    """Quita y destruye los widgets de un layout (para volver a llenarlo)."""
    while layout.count():
        elemento = layout.takeAt(0)
        if elemento.widget() is not None:
            elemento.widget().deleteLater()


class TarjetaDato(PanelVidrio):
    """Tarjeta del resumen: título, ícono, cifra grande y una línea de detalle."""

    def __init__(self, titulo: str, icono: str, token_icono: str = "acento", parent=None):
        super().__init__(parent, sombra=True)
        self.setMinimumHeight(132)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(20, 18, 20, 18)
        caja.setSpacing(8)
        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta(titulo, tenue=True, ajustar=True), 1)
        cabecera.addWidget(EtiquetaIcono(icono, token_icono, 20), 0, Qt.AlignmentFlag.AlignTop)
        caja.addLayout(cabecera)
        cifra = QHBoxLayout()
        cifra.setSpacing(8)
        self.valor = etiqueta("—", "dato")
        self.total = etiqueta("", "datoSecundario")
        cifra.addWidget(self.valor, 0, Qt.AlignmentFlag.AlignBottom)
        cifra.addWidget(self.total, 0, Qt.AlignmentFlag.AlignBottom)
        cifra.addStretch(1)
        caja.addLayout(cifra)
        self.detalle = etiqueta("", tenue=True, ajustar=True)
        caja.addWidget(self.detalle)
        caja.addStretch(1)

    def poner(self, valor: int, detalle: str = "", total: str = "", alerta: bool = False):
        self.valor.setText(str(valor))
        self.total.setText(total)
        self.total.setVisible(bool(total))
        self.detalle.setText(detalle)
        self.valor.setObjectName("datoError" if alerta else "dato")
        repulir(self.valor)


class PantallaInicio(Pantalla):
    """Resumen de la biblioteca: contadores (vista V_RESUMEN), préstamos vencidos
    (V_PRESTAMOS_VENCIDOS), libros más solicitados (V_LIBROS_MAS_SOLICITADOS) y
    accesos rápidos al lector. Se recarga cada vez que se abre."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QFrame.Shape.NoFrame)
        desplazable.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        desplazable.setWidget(contenido)
        raiz.addWidget(desplazable)

        caja = QVBoxLayout(contenido)
        caja.setContentsMargins(0, 0, 10, 10)
        caja.setSpacing(18)

        # Hora de la última carga y botón para recargar
        barra = QHBoxLayout()
        self.actualizado = etiqueta("", tenue=True)
        barra.addWidget(self.actualizado)
        barra.addStretch(1)
        recargar = BotonIcono("Actualizar", "actualizar", "pastilla", token="acento", tam=18)
        recargar.clicked.connect(lambda: self.al_mostrar())
        barra.addWidget(recargar)
        caja.addLayout(barra)

        # Tarjetas del resumen
        tarjetas = QHBoxLayout()
        tarjetas.setSpacing(16)
        self.t_activos = TarjetaDato("Préstamos activos", "prestar")
        self.t_vencidos = TarjetaDato("Préstamos vencidos", "reloj", "error")
        self.t_disponibles = TarjetaDato("Ejemplares disponibles", "libro")
        self.t_alumnos = TarjetaDato("Alumnos activos", "alumnos")
        for tarjeta in (self.t_activos, self.t_vencidos, self.t_disponibles, self.t_alumnos):
            tarjetas.addWidget(tarjeta, 1)
        caja.addLayout(tarjetas)

        # Vencidos + más solicitados
        medio = QHBoxLayout()
        medio.setSpacing(16)
        medio.addWidget(self._crear_vencidos(), 3)
        medio.addWidget(self._crear_solicitados(), 2)
        caja.addLayout(medio)

        # Accesos rápidos al lector (prestar y devolver solo si el rol puede)
        acciones = QHBoxLayout()
        acciones.setSpacing(16)
        opciones = [("Consultar un ejemplar", "buscar", "consultar")]
        if self.sesiones.puede(PRESTAMOS):
            opciones = [("Prestar un libro", "prestar", "prestar"),
                        ("Registrar una devolución", "devolver", "devolver")] + opciones
        for texto, icono, modo in opciones:
            boton = BotonIcono(texto, icono, "accion", token="acento", tam=24)
            boton.setMinimumHeight(68)
            boton.clicked.connect(lambda _marcado=False, m=modo: self.ventana.mostrar("lector", modo=m))
            acciones.addWidget(boton, 1)
        caja.addLayout(acciones)
        caja.addStretch(1)

    # Construcción de los paneles

    def _crear_vencidos(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("Préstamos vencidos", "seccion"))
        cabecera.addStretch(1)
        ver = BotonIcono("Ver reporte", None, "enlace")
        ver.clicked.connect(lambda: self.ventana.mostrar("reportes", reporte="vencidos"))
        cabecera.addWidget(ver)
        caja.addLayout(cabecera)
        self.tabla_vencidos = Tabla(["Alumno", "Libro", "Código", "Retraso"])
        self.tabla_vencidos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        caja.addWidget(self.tabla_vencidos)
        self.sin_vencidos = etiqueta("No hay préstamos vencidos: todos los libros están dentro de su fecha.",
                                     tenue=True, ajustar=True)
        self.sin_vencidos.hide()
        caja.addWidget(self.sin_vencidos)
        caja.addStretch(1)
        return panel

    def _crear_solicitados(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(12)
        caja.addWidget(etiqueta("Libros más solicitados", "seccion"))
        self.lista_solicitados = QVBoxLayout()
        self.lista_solicitados.setSpacing(12)
        caja.addLayout(self.lista_solicitados)
        caja.addStretch(1)
        return panel

    # Datos

    def al_mostrar(self, **opciones):
        sesion = self.sesiones.sesion
        if sesion is not None and self.ventana.escritorio is not None:
            self.ventana.escritorio.subtitulo.setText(
                f"Hola, {sesion.nombre_usuario}. Así está la biblioteca hoy.")
        reportes = self.servicios["reportes"]
        ok, resumen = self.ejecutar(reportes.resumen)
        if ok:
            self._poner_resumen(resumen)
        ok, vencidos = self.ejecutar(reportes.prestamos_vencidos)
        if ok:
            self._poner_vencidos(vencidos)
        ok, solicitados = self.ejecutar(reportes.libros_mas_solicitados)
        if ok:
            self._poner_solicitados(solicitados)
        self.actualizado.setText(f"Actualizado a las {datetime.now():%H:%M}")

    def _poner_resumen(self, r):
        vigentes = r.prestamos_activos - r.prestamos_vencidos
        self.t_activos.poner(r.prestamos_activos,
                             f"{_plural(vigentes, 'vigente', 'vigentes')} · "
                             f"{_plural(r.prestamos_vencidos, 'vencido', 'vencidos')}")
        self.t_vencidos.poner(r.prestamos_vencidos,
                              _plural(r.alumnos_con_retraso, "alumno con retraso", "alumnos con retraso")
                              if r.alumnos_con_retraso else "Nadie tiene retraso",
                              alerta=r.prestamos_vencidos > 0)
        self.t_disponibles.poner(r.ejemplares_disponibles,
                                 f"{r.en_mantenimiento} en mantenimiento · {r.de_baja} de baja",
                                 total=f"de {r.total_ejemplares}")
        inactivos = r.total_alumnos - r.alumnos_activos
        self.t_alumnos.poner(r.alumnos_activos,
                             _plural(inactivos, "dado de baja", "dados de baja"),
                             total=f"de {r.total_alumnos}")

    def _poner_vencidos(self, vencidos):
        vencidos = sorted(vencidos, key=lambda v: v.dias_retraso, reverse=True)[:MAX_VENCIDOS]
        tabla = self.tabla_vencidos
        tabla.setVisible(bool(vencidos))
        self.sin_vencidos.setVisible(not vencidos)
        tabla.cargar([(f"{v.alumno} ({v.matricula})", v.titulo, v.codigo_barras, "") for v in vencidos],
                     datos=vencidos)
        for fila, v in enumerate(vencidos):
            celda = QWidget()
            linea = QHBoxLayout(celda)
            linea.setContentsMargins(6, 0, 6, 0)
            linea.addStretch(1)
            linea.addWidget(Insignia(_plural(v.dias_retraso, "día", "días"),
                                     "error" if v.dias_retraso >= 7 else "advertencia"))
            tabla.setCellWidget(fila, 3, celda)
        alto_cabecera = 42
        tabla.setFixedHeight(alto_cabecera + 44 * max(len(vencidos), 1))

    def _poner_solicitados(self, solicitados):
        _vaciar(self.lista_solicitados)
        solicitados = solicitados[:MAX_SOLICITADOS]
        if not solicitados:
            self.lista_solicitados.addWidget(
                etiqueta("Todavía no hay libros con 2 o más préstamos.", tenue=True, ajustar=True))
            return
        maximo = max(libro.total_prestamos for libro in solicitados)
        for libro in solicitados:
            renglon = QWidget()
            caja = QVBoxLayout(renglon)
            caja.setContentsMargins(0, 0, 0, 0)
            caja.setSpacing(6)
            textos = QHBoxLayout()
            textos.addWidget(etiqueta(libro.titulo, ajustar=True), 1)
            textos.addWidget(etiqueta(_plural(libro.total_prestamos, "préstamo", "préstamos"), tenue=True))
            caja.addLayout(textos)
            barra = QProgressBar()
            barra.setTextVisible(False)
            barra.setRange(0, maximo)
            barra.setValue(libro.total_prestamos)
            caja.addWidget(barra)
            self.lista_solicitados.addWidget(renglon)
