from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit, QVBoxLayout,
)

from config import ADMINISTRACION, MAX_PRESTAMOS_ACTIVOS
from Modelos import BibliotecaError, SinConexionError
from UI import iconos, tema
from UI.componentes import (
    Aviso, BotonIcono, CampoLector, Dato, Insignia, PanelVidrio, Tabla, boton_gel, celda_insignia, confirmar,
    etiqueta, fecha_texto,
)
from UI.pantallas.base import Pantalla

FILTROS_ESTADO = (("Activos", "ACTIVO"), ("Dados de baja", "INACTIVO"), ("Todos", None))


def _estado_prestamo(p) -> tuple:
    """Texto y color de un renglón del historial (SP_HISTORIAL_ALUMNO + FN_DIAS_RETRASO)."""
    if p.estado == "ACTIVO":
        if p.dias_retraso:
            return f"VENCIDO · {p.dias_retraso} d", "error"
        return "ACTIVO", "ok"
    if p.dias_retraso:
        return f"DEVUELTO · {p.dias_retraso} d tarde", "advertencia"
    return "DEVUELTO", "info"


def _situacion(a) -> tuple:
    """Columna "Situación" de la lista: baja, préstamos vencidos, activos o ninguno."""
    if a.estado != "ACTIVO":
        return "DADO DE BAJA", "error"
    if a.prestamos_vencidos:
        return f"{a.prestamos_activos} préstamo(s) · {a.prestamos_vencidos} vencido(s)", "error"
    if a.prestamos_activos:
        tipo = "advertencia" if a.prestamos_activos >= MAX_PRESTAMOS_ACTIVOS else "info"
        return f"{a.prestamos_activos} de {MAX_PRESTAMOS_ACTIVOS} préstamos", tipo
    return "Sin préstamos", "ok"


class DialogoAlumno(QDialog):
    """Formulario para registrar o corregir un alumno. La matrícula se puede leer de la
    credencial con el lector (su Enter solo pasa al siguiente campo) y no cambia al editar."""

    def __init__(self, ventana, carreras, alumno=None, parent=None):
        super().__init__(parent or ventana)
        self.ventana = ventana
        self.servicio = ventana.servicios["alumnos"]
        self.alumno_original = alumno
        self.alumno = None
        titulo = "Editar alumno" if alumno else "Nuevo alumno"
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(560)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(28, 24, 28, 24)
        caja.setSpacing(12)
        caja.addWidget(etiqueta(titulo, "seccion"))

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(14)
        rejilla.setVerticalSpacing(6)
        # Se crean en el orden de captura: así Tab y Enter siguen el mismo recorrido
        self.matricula = QLineEdit()
        self.matricula.setMaxLength(20)
        self.matricula.setPlaceholderText("Escanea la credencial o escríbela")
        self.semestre = QComboBox()
        self.semestre.addItems([str(n) for n in range(1, 13)])
        self.nombre = QLineEdit()
        self.nombre.setMaxLength(100)
        self.carrera = QComboBox()
        for carrera in carreras:
            self.carrera.addItem(carrera.nombre, carrera.id_carrera)
        fila_carrera = QHBoxLayout()
        fila_carrera.addWidget(self.carrera, 1)
        if ventana.sesiones.puede(ADMINISTRACION):
            nueva = BotonIcono("", "agregar", token="acento", tam=18)
            nueva.setToolTip("Nueva carrera")
            nueva.setAutoDefault(False)
            nueva.clicked.connect(self._nueva_carrera)
            fila_carrera.addWidget(nueva)
        self.correo = QLineEdit()
        self.correo.setMaxLength(100)
        self.correo.setPlaceholderText("Opcional")
        self.telefono = QLineEdit()
        self.telefono.setMaxLength(15)
        self.telefono.setPlaceholderText("Opcional, solo números")
        self.telefono.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,15}"), self))

        rejilla.addWidget(etiqueta("Matrícula"), 0, 0)
        rejilla.addWidget(etiqueta("Semestre"), 0, 1)
        rejilla.addWidget(self.matricula, 1, 0)
        rejilla.addWidget(self.semestre, 1, 1)
        rejilla.addWidget(etiqueta("Nombre completo"), 2, 0, 1, 2)
        rejilla.addWidget(self.nombre, 3, 0, 1, 2)
        rejilla.addWidget(etiqueta("Carrera"), 4, 0, 1, 2)
        rejilla.addLayout(fila_carrera, 5, 0, 1, 2)
        rejilla.addWidget(etiqueta("Correo"), 6, 0)
        rejilla.addWidget(etiqueta("Teléfono"), 6, 1)
        rejilla.addWidget(self.correo, 7, 0)
        rejilla.addWidget(self.telefono, 7, 1)
        rejilla.setColumnStretch(0, 3)
        rejilla.setColumnStretch(1, 2)
        caja.addLayout(rejilla)

        self.aviso = Aviso()
        caja.addWidget(self.aviso)

        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = BotonIcono("Cancelar")
        cancelar.setAutoDefault(False)
        cancelar.clicked.connect(self.reject)
        guardar = boton_gel("Guardar cambios" if alumno else "Registrar alumno")
        guardar.setAutoDefault(False)
        guardar.clicked.connect(self._guardar)
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        caja.addLayout(botones)

        # El lector manda Enter al leer la credencial: que solo avance de campo
        self.matricula.returnPressed.connect(self.nombre.setFocus)
        self.nombre.returnPressed.connect(self.correo.setFocus)
        self.correo.returnPressed.connect(self.telefono.setFocus)
        self.telefono.returnPressed.connect(self._guardar)  # el último campo sí guarda

        if alumno is not None:
            self.matricula.setText(alumno.matricula)
            self.matricula.setReadOnly(True)
            self.matricula.setToolTip("La matrícula no se cambia")
            self.nombre.setText(alumno.nombre_completo)
            self.semestre.setCurrentIndex(max(0, min(int(alumno.semestre), 12) - 1))
            self.correo.setText(alumno.correo or "")
            self.telefono.setText(alumno.telefono or "")
            indice = self.carrera.findData(alumno.id_carrera)
            if indice >= 0:
                self.carrera.setCurrentIndex(indice)
            self.nombre.setFocus()
        else:
            self.matricula.setFocus()

    def _nueva_carrera(self):
        nombre, aceptado = QInputDialog.getText(self, "Nueva carrera", "Nombre de la carrera:")
        if not aceptado or not nombre.strip():
            return
        try:
            carrera = self.servicio.agregar_carrera(nombre)
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            return
        self.carrera.addItem(carrera.nombre, carrera.id_carrera)
        self.carrera.setCurrentIndex(self.carrera.count() - 1)
        self.aviso.mostrar(f"Carrera {carrera.nombre} creada.", "ok")

    def _guardar(self):
        datos = (self.matricula.text(), self.nombre.text(), self.carrera.currentData(),
                 self.semestre.currentText(), self.correo.text(), self.telefono.text())
        try:
            if self.alumno_original is None:
                self.alumno = self.servicio.registrar(*datos)
            else:
                self.alumno = self.servicio.actualizar(*datos)
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            return
        except Exception as error:  # noqa: BLE001
            self.aviso.mostrar(f"No se pudo guardar: {error}", "error", 0)
            return
        self.accept()


class PantallaAlumnos(Pantalla):
    """Alumnos: lista con préstamos activos y vencidos, alta, edición, baja y reactivación,
    y el historial de cada uno con SP_HISTORIAL_ALUMNO."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        self._alumnos = []
        self._carreras = []
        self._matricula_elegida = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 10, 10)
        raiz.setSpacing(16)

        barra = QHBoxLayout()
        barra.setSpacing(10)
        self.buscar = CampoLector()
        self.buscar.setPlaceholderText("Buscar por matrícula o nombre (también con la credencial)")
        self.buscar.setClearButtonEnabled(True)
        self._accion_buscar = self.buscar.addAction(
            iconos.icono("credencial", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self.buscar.textChanged.connect(self._filtrar)
        self.buscar.leido.connect(self._buscar_exacto)  # Enter o fin de la lectura del lector
        barra.addWidget(self.buscar, 3)
        self.filtro_carrera = QComboBox()
        self.filtro_carrera.setMinimumWidth(220)
        self.filtro_carrera.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_carrera, 1)
        self.filtro_estado = QComboBox()
        for texto, valor in FILTROS_ESTADO:
            self.filtro_estado.addItem(texto, valor)
        self.filtro_estado.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_estado)
        nuevo = boton_gel("Nuevo alumno", "agregar")
        nuevo.clicked.connect(self._nuevo)
        barra.addWidget(nuevo)
        raiz.addLayout(barra)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._crear_panel_lista(), 5)
        cuerpo.addWidget(self._crear_panel_ficha(), 6)
        raiz.addLayout(cuerpo, 1)

        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    # Construcción

    def _crear_panel_lista(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("Alumnos", "seccion"))
        self.total = etiqueta("", tenue=True)
        cabecera.addWidget(self.total)
        cabecera.addStretch(1)
        caja.addLayout(cabecera)
        self.tabla = Tabla(["Matrícula", "Nombre", "Carrera", "Sem.", "Situación"])
        cabecera_tabla = self.tabla.horizontalHeader()
        for columna in (0, 3, 4):
            cabecera_tabla.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.itemSelectionChanged.connect(self._al_seleccionar)
        self.tabla.cellDoubleClicked.connect(lambda *_: self._editar())
        caja.addWidget(self.tabla, 1)
        return panel

    def _crear_panel_ficha(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)

        cabecera = QHBoxLayout()
        self.nombre = etiqueta("Selecciona un alumno", "seccion", ajustar=True)
        cabecera.addWidget(self.nombre, 1)
        self.insignia_estado = Insignia("", "ok")
        self.insignia_estado.hide()
        cabecera.addWidget(self.insignia_estado, 0, Qt.AlignmentFlag.AlignTop)
        caja.addLayout(cabecera)
        self.detalle = etiqueta("Verás sus datos y todos los libros que ha pedido.", tenue=True, ajustar=True)
        caja.addWidget(self.detalle)

        datos = QGridLayout()
        datos.setHorizontalSpacing(10)
        datos.setVerticalSpacing(10)
        self.d_correo, self.d_telefono = Dato("Correo"), Dato("Teléfono")
        self.d_activos, self.d_vencidos = Dato("Préstamos activos"), Dato("Préstamos vencidos")
        datos.addWidget(self.d_correo, 0, 0)
        datos.addWidget(self.d_telefono, 0, 1)
        datos.addWidget(self.d_activos, 1, 0)
        datos.addWidget(self.d_vencidos, 1, 1)
        caja.addLayout(datos)

        acciones = QHBoxLayout()
        self.boton_editar = BotonIcono("Editar", "editar", tam=18)
        self.boton_editar.clicked.connect(self._editar)
        self.boton_estado = BotonIcono("Dar de baja", "eliminar", token="error", tam=18)
        self.boton_estado.clicked.connect(self._cambiar_estado)
        acciones.addWidget(self.boton_editar)
        acciones.addWidget(self.boton_estado)
        acciones.addStretch(1)
        caja.addLayout(acciones)

        caja.addWidget(etiqueta("Historial de préstamos", "seccion"))
        self.historial = Tabla(["Título", "Ejemplar", "Prestado", "Límite", "Devuelto", "Estado"])
        cabecera_historial = self.historial.horizontalHeader()
        for columna in (1, 2, 3, 4, 5):
            cabecera_historial.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        caja.addWidget(self.historial, 1)
        self.sin_historial = etiqueta("Todavía no ha pedido ningún libro.", tenue=True)
        self.sin_historial.hide()
        caja.addWidget(self.sin_historial)
        self._limpiar_ficha()
        return panel

    # Carga de datos

    def al_mostrar(self, **opciones):
        """`matricula` (opcional) abre la pantalla con ese alumno elegido, por ejemplo desde un reporte."""
        matricula = opciones.get("matricula")
        if matricula:
            self._matricula_elegida = str(matricula).upper()
            self.filtro_estado.blockSignals(True)
            self.filtro_estado.setCurrentIndex(len(FILTROS_ESTADO) - 1)  # Todos
            self.filtro_estado.blockSignals(False)
            self.buscar.blockSignals(True)
            self.buscar.setText(str(matricula))
            self.buscar.blockSignals(False)
        self._cargar()

    def _cargar(self):
        servicio = self.servicios["alumnos"]
        ok, carreras = self.ejecutar(servicio.listar_carreras)
        if ok:
            self._carreras = carreras
            elegida = self.filtro_carrera.currentData()
            self.filtro_carrera.blockSignals(True)
            self.filtro_carrera.clear()
            self.filtro_carrera.addItem("Todas las carreras", None)
            for c in carreras:
                self.filtro_carrera.addItem(c.nombre, c.id_carrera)
            indice = self.filtro_carrera.findData(elegida)
            self.filtro_carrera.setCurrentIndex(max(indice, 0))
            self.filtro_carrera.blockSignals(False)
        ok, alumnos = self.ejecutar(servicio.listar)
        if ok:
            self._alumnos = alumnos
        self._filtrar()

    def _filtrar(self, *_):
        texto = self.buscar.text().strip().lower()
        carrera = self.filtro_carrera.currentData()
        estado = self.filtro_estado.currentData()
        visibles = [a for a in self._alumnos
                    if (carrera is None or a.id_carrera == carrera)
                    and (estado is None or a.estado == estado)
                    and (not texto or texto in a.matricula.lower() or texto in a.nombre_completo.lower())]
        filas = [(a.matricula, a.nombre_completo, a.carrera, a.semestre, "") for a in visibles]
        self.tabla.blockSignals(True)
        self.tabla.cargar(filas, datos=visibles)
        for fila, a in enumerate(visibles):
            self.tabla.setCellWidget(fila, 4, celda_insignia(*_situacion(a)))
        self.tabla.blockSignals(False)
        self.total.setText(f"{len(visibles)} de {len(self._alumnos)}")
        fila = next((i for i, a in enumerate(visibles) if a.matricula.upper() == self._matricula_elegida), -1)
        if fila >= 0:
            self.tabla.selectRow(fila)  # dispara _al_seleccionar
        else:
            self._limpiar_ficha()

    def _buscar_exacto(self):
        """Enter (o el lector con la credencial): elige la matrícula exacta o el único resultado."""
        texto = self.buscar.text().strip().upper()
        filas = self.tabla.rowCount()
        for fila in range(filas):
            alumno = self.tabla.item(fila, 0).data(Qt.ItemDataRole.UserRole)
            if alumno is not None and alumno.matricula.upper() == texto:
                self.tabla.selectRow(fila)
                return
        if filas == 1:
            self.tabla.selectRow(0)
        elif texto and filas == 0:
            self.avisar(f"No hay ningún alumno con «{self.buscar.text().strip()}» con estos filtros.", "info")

    def _actual(self):
        return self.tabla.dato_seleccionado()

    def _al_seleccionar(self):
        alumno = self._actual()
        if alumno is None:
            self._limpiar_ficha()
            return
        self._matricula_elegida = alumno.matricula.upper()
        self._mostrar_ficha(alumno)

    def _mostrar_ficha(self, a):
        activo = a.estado == "ACTIVO"
        self.nombre.setText(a.nombre_completo)
        self.insignia_estado.poner("ACTIVO" if activo else "DADO DE BAJA", "ok" if activo else "error")
        self.insignia_estado.show()
        self.detalle.setText(f"{a.matricula} · {a.carrera} · {a.semestre}° semestre")
        self.d_correo.poner(a.correo)
        self.d_telefono.poner(a.telefono)
        self.d_activos.poner(f"{a.prestamos_activos} de {MAX_PRESTAMOS_ACTIVOS}")
        self.d_vencidos.poner(a.prestamos_vencidos)
        self.boton_editar.setEnabled(True)
        self.boton_estado.setEnabled(True)
        if activo:
            self.boton_estado.setText("Dar de baja")
            self.boton_estado.cambiar_icono("eliminar", "error")
        else:
            self.boton_estado.setText("Reactivar")
            self.boton_estado.cambiar_icono("ok", "ok")

        ok, historial = self.ejecutar(self.servicios["prestamos"].historial, a.matricula)
        if not ok:
            historial = []
        self.historial.cargar([(p.titulo, p.codigo_barras, fecha_texto(p.fecha_prestamo), fecha_texto(p.fecha_limite),
                                fecha_texto(p.fecha_devolucion), "") for p in historial], datos=historial)
        for fila, p in enumerate(historial):
            self.historial.setCellWidget(fila, 5, celda_insignia(*_estado_prestamo(p)))
        self.historial.setVisible(bool(historial))
        self.sin_historial.setVisible(not historial)

    def _limpiar_ficha(self):
        self._matricula_elegida = None
        self.nombre.setText("Selecciona un alumno")
        self.insignia_estado.hide()
        self.detalle.setText("Verás sus datos y todos los libros que ha pedido.")
        for dato in (self.d_correo, self.d_telefono, self.d_activos, self.d_vencidos):
            dato.poner(None)
        self.boton_editar.setEnabled(False)
        self.boton_estado.setEnabled(False)
        self.historial.cargar([])
        self.historial.show()
        self.sin_historial.hide()

    # Acciones

    def _nuevo(self):
        dialogo = DialogoAlumno(self.ventana, self._carreras)
        if dialogo.exec() and dialogo.alumno is not None:  # 1 = aceptado
            self._matricula_elegida = dialogo.alumno.matricula.upper()
            self.buscar.blockSignals(True)
            self.buscar.clear()  # que el alumno nuevo quede a la vista
            self.buscar.blockSignals(False)
            self.avisar(f"Alumno registrado: {dialogo.alumno.nombre_completo}.", "ok")
            self._cargar()

    def _editar(self):
        alumno = self._actual()
        if alumno is None:
            self.avisar("Selecciona el alumno que quieres editar.", "info")
            return
        dialogo = DialogoAlumno(self.ventana, self._carreras, alumno)
        if dialogo.exec() and dialogo.alumno is not None:
            self.avisar(f"Datos actualizados: {dialogo.alumno.nombre_completo}.", "ok")
            self._cargar()

    def _cambiar_estado(self):
        alumno = self._actual()
        if alumno is None:
            return
        servicio = self.servicios["alumnos"]
        if alumno.estado == "ACTIVO":
            if alumno.prestamos_activos:  # no tiene caso pedir confirmación: el servicio lo rechazaría
                self.avisar(f"{alumno.nombre_completo} tiene {alumno.prestamos_activos} libro(s) sin devolver; "
                            "registra las devoluciones antes de darlo de baja.", "advertencia")
                return
            if not confirmar(self, "Dar de baja",
                             f"¿Dar de baja a {alumno.nombre_completo}?\n\nYa no podrá pedir libros hasta que "
                             "se reactive. El cambio queda registrado en la auditoría.", "Sí, dar de baja"):
                return
            ok, _ = self.ejecutar(servicio.dar_de_baja, alumno.matricula,
                                  exito=f"{alumno.nombre_completo} quedó dado de baja.")
        else:
            ok, _ = self.ejecutar(servicio.reactivar, alumno.matricula,
                                  exito=f"{alumno.nombre_completo} está activo otra vez.")
        if ok:
            if self.filtro_estado.currentData() is not None:  # que no desaparezca de la lista
                self.filtro_estado.blockSignals(True)
                self.filtro_estado.setCurrentIndex(len(FILTROS_ESTADO) - 1)
                self.filtro_estado.blockSignals(False)
            self._cargar()

    def _al_cambiar_tema(self, _nombre):
        self._accion_buscar.setIcon(iconos.icono("credencial", tema.color("tenue")))
