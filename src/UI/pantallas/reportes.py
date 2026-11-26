from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Optional

from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QHeaderView, QLineEdit, QProgressBar, QVBoxLayout, QWidget

from config import ALUMNOS
from UI import iconos, tema
from UI.componentes import (
    BotonIcono, EtiquetaIcono, PanelVidrio, Tabla, celda_insignia, etiqueta, exportar_csv, fecha_texto,
)
from UI.pantallas.base import Pantalla


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _dias(n) -> str:
    return _plural(int(n or 0), "día", "días")


@dataclass
class Reporte:
    """Cómo se muestra un reporte: de qué método del servicio sale, sus columnas y qué
    técnica SQL lo resuelve (se muestra para explicarlo en la defensa)."""
    clave: str
    boton: str
    icono: str
    titulo: str
    descripcion: str
    tecnica: str
    metodo: str                                   # método de ReporteServicio
    columnas: list
    filas: Callable                               # objeto -> tupla con el valor de cada columna
    resumen: Callable                             # lista completa -> texto
    insignia: Optional[Callable] = None           # objeto -> (columna, tipo de insignia)
    barra: Optional[Callable] = None              # (objeto, lista) -> (columna, valor, máximo, texto)
    abre_alumno: bool = False                     # doble clic abre al alumno (columna "Matrícula")
    ajustar: list = field(default_factory=list)   # columnas que se ajustan a su contenido


def _resumen_vencidos(filas) -> str:
    if not filas:
        return "No hay préstamos vencidos: todos los libros están dentro de su fecha."
    alumnos = len({f.matricula for f in filas})
    return (f"{_plural(len(filas), 'préstamo vencido', 'préstamos vencidos')} de "
            f"{_plural(alumnos, 'alumno', 'alumnos')} · el mayor retraso es de {_dias(max(f.dias_retraso for f in filas))}.")


def _resumen_retraso(filas) -> str:
    if not filas:
        return "Ningún alumno tiene libros vencidos."
    primero = filas[0]
    return (f"{_plural(len(filas), 'alumno', 'alumnos')} con retraso · el primero del ranking es "
            f"{primero.alumno} con {_dias(primero.total_dias_retraso)} acumulados.")


def _resumen_solicitados(filas) -> str:
    if not filas:
        return "Todavía no hay libros con 2 préstamos o más."
    primero = filas[0]
    return f"{_plural(len(filas), 'libro', 'libros')} en el ranking · el más pedido es {primero.titulo}."


def _resumen_disponibilidad(filas) -> str:
    total = sum(f.total_ejemplares for f in filas)
    libres = sum(f.disponibles for f in filas)
    agotados = sum(1 for f in filas if f.total_ejemplares and not f.disponibles)
    return (f"{libres} de {total} ejemplares disponibles en {_plural(len(filas), 'libro', 'libros')} · "
            f"{_plural(agotados, 'libro sin copias libres', 'libros sin copias libres')}.")


def _resumen_sin_prestamos(filas) -> str:
    if not filas:
        return "Todos los libros se han prestado al menos una vez."
    return f"{_plural(len(filas), 'libro nunca se ha prestado', 'libros nunca se han prestado')}."


REPORTES = (
    Reporte("vencidos", "Préstamos vencidos", "reloj", "Préstamos vencidos",
            "Cada libro que no se ha devuelto a tiempo, con el alumno que lo tiene y los días de retraso.",
            "V_PRESTAMOS_VENCIDOS · JOIN de 5 tablas · FN_DIAS_RETRASO",
            "prestamos_vencidos",
            ["Alumno", "Matrícula", "Carrera", "Libro", "Ejemplar", "Prestado", "Límite", "Retraso"],
            lambda f: (f.alumno, f.matricula, f.carrera, f.titulo, f.codigo_barras,
                       fecha_texto(f.fecha_prestamo), fecha_texto(f.fecha_limite), _dias(f.dias_retraso)),
            _resumen_vencidos,
            insignia=lambda f: (7, "error"), abre_alumno=True, ajustar=[1, 4, 5, 6, 7]),
    Reporte("retraso", "Alumnos con retraso", "alumnos", "Alumnos con retraso",
            "Ranking de alumnos por días de retraso acumulados: quién debe más libros y desde hace cuánto.",
            "V_ALUMNOS_CON_VENCIDOS · CTE (WITH) · GROUP BY · COUNT/SUM/MAX · RANK()",
            "alumnos_con_vencidos",
            ["#", "Alumno", "Matrícula", "Carrera", "Libros vencidos", "Días acumulados", "Mayor retraso", "Correo"],
            lambda f: (f.posicion, f.alumno, f.matricula, f.carrera, f.libros_vencidos,
                       _dias(f.total_dias_retraso), _dias(f.max_dias_retraso), f.correo or "—"),
            _resumen_retraso,
            insignia=lambda f: (5, "error"), abre_alumno=True, ajustar=[0, 2, 4, 5, 6]),
    Reporte("solicitados", "Más solicitados", "libro", "Libros más solicitados",
            "Los libros que más se piden (2 préstamos o más), para decidir qué títulos conviene comprar.",
            "V_LIBROS_MAS_SOLICITADOS · JOIN de 4 tablas · GROUP BY · HAVING · RANK()",
            "libros_mas_solicitados",
            ["#", "Título", "Autor", "Categoría", "Préstamos"],
            lambda f: (f.posicion, f.titulo, f.autor, f.categoria, f.total_prestamos),
            _resumen_solicitados,
            barra=lambda f, todas: (4, f.total_prestamos, max(x.total_prestamos for x in todas),
                                    _plural(f.total_prestamos, "préstamo", "préstamos")),
            ajustar=[0]),
    Reporte("disponibilidad", "Disponibilidad", "ok", "Disponibilidad por libro",
            "Cuántas copias tiene cada libro y cuántas se pueden prestar ahora (sin contar las de baja).",
            "V_DISPONIBILIDAD · subconsulta · FN_DISPONIBLES_LIBRO",
            "disponibilidad_general",
            ["Título", "Autor", "Ejemplares", "Disponibles"],
            lambda f: (f.titulo, f.autor, f.total_ejemplares, f.disponibles),
            _resumen_disponibilidad,
            barra=lambda f, _todas: (3, f.disponibles, max(f.total_ejemplares, 1),
                                     f"{f.disponibles} de {f.total_ejemplares}"),
            ajustar=[2]),
    Reporte("sin_prestamos", "Sin préstamos", "info", "Libros sin préstamos",
            "Títulos que nunca se han prestado: candidatos a moverse de lugar o a revisarse.",
            "V_LIBROS_SIN_PRESTAMOS · NOT EXISTS",
            "libros_sin_prestamos",
            ["Título", "Autor"],
            lambda f: (f.titulo, f.autor),
            _resumen_sin_prestamos),
)
POR_CLAVE = {r.clave: r for r in REPORTES}


def _celda_barra(valor: int, maximo: int, texto: str) -> QWidget:
    celda = QWidget()
    fila = QHBoxLayout(celda)
    fila.setContentsMargins(6, 0, 10, 0)
    fila.setSpacing(10)
    barra = QProgressBar()
    barra.setTextVisible(False)
    barra.setRange(0, max(int(maximo or 0), 1))
    barra.setValue(int(valor or 0))
    barra.setMinimumWidth(90)
    fila.addWidget(barra, 1)
    fila.addWidget(etiqueta(texto, tenue=True))
    return celda


class PantallaReportes(Pantalla):
    """Los reportes avanzados del proyecto, leídos de las vistas de MySQL.
    Se pueden filtrar, exportar a CSV y, en los de alumnos, abrir al alumno con doble clic."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        self.reporte = REPORTES[0]
        self._datos = []
        self._visibles = []
        self._abre_alumno = self.sesiones.puede(ALUMNOS)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 10, 10)
        raiz.setSpacing(16)

        selector = PanelVidrio()
        fila = QHBoxLayout(selector)
        fila.setContentsMargins(6, 6, 6, 6)
        fila.setSpacing(6)
        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botones = {}
        for reporte in REPORTES:
            boton = BotonIcono(reporte.boton, reporte.icono, "segmento", tam=18)
            boton.setCheckable(True)
            boton.setMinimumHeight(44)
            boton.clicked.connect(lambda _marcado=False, c=reporte.clave: self.elegir(c))
            self.grupo.addButton(boton)
            self.botones[reporte.clave] = boton
            fila.addWidget(boton, 1)
        raiz.addWidget(selector)

        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(24, 20, 24, 20)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.setSpacing(10)
        self.icono = EtiquetaIcono(self.reporte.icono, "acento", 24)
        cabecera.addWidget(self.icono)
        self.titulo = etiqueta("", "seccion")
        cabecera.addWidget(self.titulo)
        cabecera.addStretch(1)
        self.tecnica = etiqueta("", "chip")
        self.tecnica.setToolTip("Técnica SQL con la que la vista resuelve este reporte")
        cabecera.addWidget(self.tecnica)
        caja.addLayout(cabecera)
        self.descripcion = etiqueta("", tenue=True, ajustar=True)
        caja.addWidget(self.descripcion)

        herramientas = QHBoxLayout()
        herramientas.setSpacing(10)
        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText("Filtrar este reporte (nombre, matrícula, título...)")
        self.filtro.setClearButtonEnabled(True)
        self._accion_filtro = self.filtro.addAction(
            iconos.icono("buscar", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self.filtro.textChanged.connect(self._filtrar)
        herramientas.addWidget(self.filtro, 1)
        actualizar = BotonIcono("Actualizar", "actualizar", "pastilla", token="acento", tam=18)
        actualizar.clicked.connect(lambda: self._cargar())
        herramientas.addWidget(actualizar)
        exportar = BotonIcono("Exportar CSV", "exportar", "pastilla", token="acento", tam=18)
        exportar.clicked.connect(self._exportar)
        herramientas.addWidget(exportar)
        caja.addLayout(herramientas)

        self.resumen = etiqueta("", ajustar=True)
        self.resumen.setStyleSheet("font-weight: 600;")
        caja.addWidget(self.resumen)
        self.tabla = Tabla(["—"])
        self.tabla.cellDoubleClicked.connect(self._abrir_alumno)
        caja.addWidget(self.tabla, 1)
        pie = QHBoxLayout()
        self.ayuda = etiqueta("", tenue=True)
        pie.addWidget(self.ayuda)
        pie.addStretch(1)
        self.actualizado = etiqueta("", tenue=True)
        pie.addWidget(self.actualizado)
        caja.addLayout(pie)
        raiz.addWidget(panel, 1)

        tema.gestor.cambiado.connect(self._al_cambiar_tema)
        self.elegir(self.reporte.clave, cargar=False)

    def al_mostrar(self, **opciones):
        """`reporte` (opcional) abre directamente uno de los reportes, por ejemplo desde el inicio."""
        clave = opciones.get("reporte")
        if clave in POR_CLAVE:
            self.elegir(clave)
        else:
            self._cargar()

    def elegir(self, clave: str, cargar: bool = True):
        self.reporte = POR_CLAVE[clave]
        r = self.reporte
        self.botones[clave].setChecked(True)
        self.icono.cambiar(r.icono, "acento")
        self.titulo.setText(r.titulo)
        self.tecnica.setText(r.tecnica)
        self.descripcion.setText(r.descripcion)
        self.tabla.setColumnCount(len(r.columnas))
        self.tabla.setHorizontalHeaderLabels(r.columnas)
        cabecera = self.tabla.horizontalHeader()
        for columna in range(len(r.columnas)):
            modo = (QHeaderView.ResizeMode.ResizeToContents if columna in r.ajustar
                    else QHeaderView.ResizeMode.Stretch)
            cabecera.setSectionResizeMode(columna, modo)
        self.ayuda.setText("Doble clic en un renglón para abrir al alumno y ver su historial."
                           if r.abre_alumno and self._abre_alumno else "")
        self.filtro.blockSignals(True)
        self.filtro.clear()
        self.filtro.blockSignals(False)
        self._datos = []
        if cargar:
            self._cargar()

    def _cargar(self):
        r = self.reporte
        ok, datos = self.ejecutar(getattr(self.servicios["reportes"], r.metodo))
        self._datos = datos if ok else []
        self.resumen.setText(r.resumen(self._datos) if ok else "No se pudo cargar el reporte.")
        self.actualizado.setText(f"Actualizado a las {datetime.now():%H:%M}")
        self._filtrar()

    def _filtrar(self, *_):
        r = self.reporte
        texto = self.filtro.text().strip().lower()
        self._visibles = [d for d in self._datos
                          if not texto or any(texto in str(v).lower() for v in r.filas(d))]
        filas = []
        for d in self._visibles:
            valores = list(r.filas(d))
            if r.insignia:
                valores[r.insignia(d)[0]] = ""
            if r.barra:
                valores[r.barra(d, self._datos)[0]] = ""
            filas.append(valores)
        self.tabla.cargar(filas, datos=self._visibles)
        for fila, d in enumerate(self._visibles):
            if r.insignia:
                columna, tipo = r.insignia(d)
                self.tabla.setCellWidget(fila, columna, celda_insignia(str(r.filas(d)[columna]), tipo))
            if r.barra:
                columna, valor, maximo, texto_barra = r.barra(d, self._datos)
                self.tabla.setCellWidget(fila, columna, _celda_barra(valor, maximo, texto_barra))
        if texto:
            self.ayuda.setText(f"Mostrando {len(self._visibles)} de {len(self._datos)} renglones.")
        elif r.abre_alumno and self._abre_alumno:
            self.ayuda.setText("Doble clic en un renglón para abrir al alumno y ver su historial.")
        else:
            self.ayuda.setText("")

    def _exportar(self):
        r = self.reporte
        if not self._visibles:
            self.avisar("El reporte no tiene renglones para exportar.", "info")
            return
        nombre = f"reporte_{r.clave}_{date.today():%Y%m%d}.csv"
        try:
            ruta = exportar_csv(self, nombre, r.columnas, [r.filas(d) for d in self._visibles])
        except OSError as error:
            self.avisar(f"No se pudo guardar el archivo: {error}", "error", 0)
            return
        if ruta:
            self.avisar(f"Reporte exportado: {ruta}", "ok")

    def _abrir_alumno(self, fila: int, _columna: int = 0):
        if not (self.reporte.abre_alumno and self._abre_alumno) or not 0 <= fila < len(self._visibles):
            return
        self.ventana.mostrar("alumnos", matricula=self._visibles[fila].matricula)

    def _al_cambiar_tema(self, _nombre):
        self._accion_filtro.setIcon(iconos.icono("buscar", tema.color("tenue")))
