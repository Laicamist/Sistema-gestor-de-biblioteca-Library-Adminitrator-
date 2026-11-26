from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit, QVBoxLayout,
    QWidget,
)

from config import ADMINISTRACION, REPORTES
from Logic.catalogo_servicio import ESTADOS_MANUALES
from Modelos import BibliotecaError, SinConexionError
from UI import iconos, tema
from UI.componentes import (
    Aviso, BotonIcono, CampoLector, Insignia, PanelVidrio, Tabla, boton_gel, celda_insignia, confirmar,
    etiqueta,
)
from UI.pantallas.base import Pantalla

TIPO_ESTADO = {"DISPONIBLE": "ok", "PRESTADO": "advertencia", "MANTENIMIENTO": "info", "BAJA": "error"}


class DialogoLibro(QDialog):
    """Formulario para registrar o corregir un libro (la obra, no las copias).
    El ISBN se puede escanear de la contraportada: el Enter del lector solo pasa al
    siguiente campo, no guarda el formulario."""

    def __init__(self, ventana, categorias, libro=None, parent=None):
        super().__init__(parent or ventana)
        self.ventana = ventana
        self.servicio = ventana.servicios["catalogo"]
        self.libro_original = libro
        self.libro = None
        self.setWindowTitle("Editar libro" if libro else "Nuevo libro")
        self.setModal(True)
        self.setMinimumWidth(560)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(28, 24, 28, 24)
        caja.setSpacing(12)
        caja.addWidget(etiqueta("Editar libro" if libro else "Nuevo libro", "seccion"))

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(14)
        rejilla.setVerticalSpacing(6)
        # Se crean en el orden de captura: así Tab y Enter siguen el mismo recorrido
        self.isbn = QLineEdit()
        self.isbn.setMaxLength(20)
        self.isbn.setPlaceholderText("Escanéalo o escríbelo")
        self.categoria = QComboBox()
        for categoria in categorias:
            self.categoria.addItem(categoria.nombre, categoria.id_categoria)
        fila_categoria = QHBoxLayout()
        fila_categoria.addWidget(self.categoria, 1)
        if ventana.sesiones.puede(ADMINISTRACION):
            nueva = BotonIcono("", "agregar", token="acento", tam=18)
            nueva.setToolTip("Nueva categoría")
            nueva.setAutoDefault(False)
            nueva.clicked.connect(self._nueva_categoria)
            fila_categoria.addWidget(nueva)
        self.titulo = QLineEdit()
        self.titulo.setMaxLength(150)
        self.autor = QLineEdit()
        self.autor.setMaxLength(100)
        self.editorial = QLineEdit()
        self.editorial.setMaxLength(80)
        self.editorial.setPlaceholderText("Opcional")
        self.anio = QLineEdit()
        # Solo dígitos; vacío también es válido (el año es opcional y Enter debe funcionar)
        self.anio.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,4}"), self))
        self.anio.setPlaceholderText("Opcional")

        rejilla.addWidget(etiqueta("ISBN"), 0, 0)
        rejilla.addWidget(etiqueta("Categoría"), 0, 1)
        rejilla.addWidget(self.isbn, 1, 0)
        rejilla.addLayout(fila_categoria, 1, 1)
        rejilla.addWidget(etiqueta("Título"), 2, 0, 1, 2)
        rejilla.addWidget(self.titulo, 3, 0, 1, 2)
        rejilla.addWidget(etiqueta("Autor"), 4, 0, 1, 2)
        rejilla.addWidget(self.autor, 5, 0, 1, 2)
        rejilla.addWidget(etiqueta("Editorial"), 6, 0)
        rejilla.addWidget(etiqueta("Año"), 6, 1)
        rejilla.addWidget(self.editorial, 7, 0)
        rejilla.addWidget(self.anio, 7, 1)
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
        guardar = boton_gel("Guardar cambios" if libro else "Registrar libro")
        guardar.setAutoDefault(False)
        guardar.clicked.connect(self._guardar)
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        caja.addLayout(botones)

        # El lector manda Enter: que solo avance de campo
        self.isbn.returnPressed.connect(self.titulo.setFocus)
        self.titulo.returnPressed.connect(self.autor.setFocus)
        self.autor.returnPressed.connect(self.editorial.setFocus)
        self.editorial.returnPressed.connect(self.anio.setFocus)
        self.anio.returnPressed.connect(self._guardar)  # el último campo sí guarda

        if libro is not None:
            self.isbn.setText(libro.isbn)
            self.titulo.setText(libro.titulo)
            self.autor.setText(libro.autor)
            self.editorial.setText(libro.editorial or "")
            self.anio.setText(str(libro.anio) if libro.anio else "")
            indice = self.categoria.findData(libro.id_categoria)
            if indice >= 0:
                self.categoria.setCurrentIndex(indice)
        self.isbn.setFocus()

    def _nueva_categoria(self):
        nombre, aceptado = QInputDialog.getText(self, "Nueva categoría", "Nombre de la categoría:")
        if not aceptado or not nombre.strip():
            return
        try:
            categoria = self.servicio.agregar_categoria(nombre)
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            return
        self.categoria.addItem(categoria.nombre, categoria.id_categoria)
        self.categoria.setCurrentIndex(self.categoria.count() - 1)
        self.aviso.mostrar(f"Categoría {categoria.nombre} creada.", "ok")

    def _guardar(self):
        datos = (self.isbn.text(), self.titulo.text(), self.autor.text(), self.categoria.currentData(),
                 self.editorial.text(), self.anio.text())
        try:
            if self.libro_original is None:
                self.libro = self.servicio.registrar_libro(*datos)
            else:
                self.libro = self.servicio.actualizar_libro(self.libro_original.id_libro, *datos)
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            return
        except Exception as error:  # noqa: BLE001
            self.aviso.mostrar(f"No se pudo guardar: {error}", "error", 0)
            return
        self.accept()


class PantallaCatalogo(Pantalla):
    """Catálogo: libros (alta, edición, eliminación) y las copias de cada uno
    (ubicación con SP_CAMBIAR_UBICACION, estado, disponibilidad con SP_DISPONIBILIDAD_LIBRO)."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        self._libros = []
        self._categorias = {}
        self._categorias_lista = []
        self._disponibilidad = {}
        self._id_seleccionado = None
        self._es_admin = self.sesiones.puede(ADMINISTRACION)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 10, 10)
        raiz.setSpacing(16)

        barra = QHBoxLayout()
        barra.setSpacing(10)
        self.buscar = CampoLector()
        self.buscar.setPlaceholderText("Buscar por título, autor o ISBN (también con el lector)")
        self.buscar.setClearButtonEnabled(True)
        self._accion_buscar = self.buscar.addAction(
            iconos.icono("buscar", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self.buscar.textChanged.connect(self._filtrar)
        self.buscar.leido.connect(self._buscar_exacto)  # Enter o fin de la lectura del lector
        barra.addWidget(self.buscar, 3)
        self.filtro_categoria = QComboBox()
        self.filtro_categoria.setMinimumWidth(220)
        self.filtro_categoria.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_categoria, 1)
        nuevo = boton_gel("Nuevo libro", "agregar")
        nuevo.clicked.connect(self._nuevo)
        barra.addWidget(nuevo)
        raiz.addLayout(barra)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._crear_panel_libros(), 3)
        cuerpo.addWidget(self._crear_panel_ejemplares(), 2)
        raiz.addLayout(cuerpo, 1)

        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    # Construcción

    def _crear_panel_libros(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("Libros", "seccion"))
        self.total_libros = etiqueta("", tenue=True)
        cabecera.addWidget(self.total_libros)
        cabecera.addStretch(1)
        caja.addLayout(cabecera)
        self.tabla_libros = Tabla(["ISBN", "Título", "Autor", "Categoría", "Año", "Disponibles"])
        cabecera_tabla = self.tabla_libros.horizontalHeader()
        for columna in (0, 3, 4, 5):
            cabecera_tabla.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_libros.itemSelectionChanged.connect(self._al_seleccionar_libro)
        self.tabla_libros.cellDoubleClicked.connect(lambda *_: self._editar())
        caja.addWidget(self.tabla_libros, 1)
        acciones = QHBoxLayout()
        self.boton_editar = BotonIcono("Editar", "editar", tam=18)
        self.boton_editar.clicked.connect(self._editar)
        acciones.addWidget(self.boton_editar)
        if self._es_admin:
            self.boton_eliminar = BotonIcono("Eliminar", "eliminar", token="error", tam=18)
            self.boton_eliminar.clicked.connect(self._eliminar)
            acciones.addWidget(self.boton_eliminar)
        acciones.addStretch(1)
        caja.addLayout(acciones)
        return panel

    def _crear_panel_ejemplares(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        caja.addWidget(etiqueta("Ejemplares", "seccion"))
        self.libro_elegido = etiqueta("Selecciona un libro para ver sus copias.", tenue=True, ajustar=True)
        caja.addWidget(self.libro_elegido)
        self.disponibles = Insignia("", "info")
        self.disponibles.hide()
        caja.addWidget(self.disponibles)
        self.tabla_ejemplares = Tabla(["Código", "Ubicación", "Estado"])
        self.tabla_ejemplares.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_ejemplares.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        caja.addWidget(self.tabla_ejemplares, 1)

        self.acciones_ejemplar = QWidget()
        acciones = QGridLayout(self.acciones_ejemplar)
        acciones.setContentsMargins(0, 0, 0, 0)
        acciones.setHorizontalSpacing(8)
        acciones.setVerticalSpacing(8)
        agregar = boton_gel("Agregar con el lector", "lector")
        agregar.clicked.connect(self._agregar_con_lector)
        ubicacion = BotonIcono("Cambiar ubicación", "ubicacion", tam=18)
        ubicacion.clicked.connect(self._cambiar_ubicacion)
        self.estado_nuevo = QComboBox()
        self.estado_nuevo.addItems(ESTADOS_MANUALES)
        aplicar = BotonIcono("Cambiar estado", "actualizar", tam=18)
        aplicar.clicked.connect(self._cambiar_estado)
        acciones.addWidget(agregar, 0, 0, 1, 2)
        acciones.addWidget(ubicacion, 1, 0, 1, 2)
        acciones.addWidget(self.estado_nuevo, 2, 0)
        acciones.addWidget(aplicar, 2, 1)
        self.acciones_ejemplar.setEnabled(False)
        caja.addWidget(self.acciones_ejemplar)
        return panel

    # Carga de datos

    def al_mostrar(self, **opciones):
        self._cargar()

    def _cargar(self):
        catalogo = self.servicios["catalogo"]
        ok, categorias = self.ejecutar(catalogo.listar_categorias)
        if ok:
            self._categorias = {c.id_categoria: c.nombre for c in categorias}
            self._categorias_lista = categorias
            elegido = self.filtro_categoria.currentData()
            self.filtro_categoria.blockSignals(True)
            self.filtro_categoria.clear()
            self.filtro_categoria.addItem("Todas las categorías", None)
            for c in categorias:
                self.filtro_categoria.addItem(c.nombre, c.id_categoria)
            indice = self.filtro_categoria.findData(elegido)
            self.filtro_categoria.setCurrentIndex(max(indice, 0))
            self.filtro_categoria.blockSignals(False)
        ok, libros = self.ejecutar(catalogo.listar_libros)
        if ok:
            self._libros = libros
        self._disponibilidad = {}
        if self.sesiones.puede(REPORTES):
            ok, filas = self.ejecutar(self.servicios["reportes"].disponibilidad_general)
            if ok:
                self._disponibilidad = {d.id_libro: d for d in filas}
        self._filtrar()

    def _filtrar(self, *_):
        texto = self.buscar.text().strip().lower()
        categoria = self.filtro_categoria.currentData()
        visibles = [l for l in self._libros
                    if (categoria is None or l.id_categoria == categoria)
                    and (not texto or texto in l.titulo.lower() or texto in l.autor.lower()
                         or texto in l.isbn.lower())]
        filas = []
        for libro in visibles:
            disp = self._disponibilidad.get(libro.id_libro)
            filas.append((libro.isbn, libro.titulo, libro.autor, self._categorias.get(libro.id_categoria, ""),
                          libro.anio or "—", f"{disp.disponibles} de {disp.total_ejemplares}" if disp else "—"))
        self.tabla_libros.blockSignals(True)
        self.tabla_libros.cargar(filas, datos=visibles)
        self.tabla_libros.blockSignals(False)
        self.total_libros.setText(f"{len(visibles)} de {len(self._libros)}")
        fila = next((i for i, l in enumerate(visibles) if l.id_libro == self._id_seleccionado), -1)
        if fila >= 0:
            self.tabla_libros.selectRow(fila)  # dispara _al_seleccionar_libro
        else:
            self._limpiar_ejemplares()

    def _buscar_exacto(self):
        """Enter (o el lector con un ISBN): selecciona el libro exacto o el único resultado."""
        texto = self.buscar.text().strip().upper()
        filas = self.tabla_libros.rowCount()
        for fila in range(filas):
            libro = self.tabla_libros.item(fila, 0).data(Qt.ItemDataRole.UserRole)
            if libro is not None and libro.isbn.upper() == texto:
                self.tabla_libros.selectRow(fila)
                return
        if filas == 1:
            self.tabla_libros.selectRow(0)

    def _libro_actual(self):
        return self.tabla_libros.dato_seleccionado()

    def _al_seleccionar_libro(self):
        libro = self._libro_actual()
        if libro is None:
            self._limpiar_ejemplares()
            return
        self._id_seleccionado = libro.id_libro
        self._cargar_ejemplares(libro)

    def _cargar_ejemplares(self, libro):
        catalogo = self.servicios["catalogo"]
        self.libro_elegido.setText(f"{libro.titulo} · {libro.autor}")
        ok, disponibilidad = self.ejecutar(catalogo.disponibilidad, libro.id_libro)
        if ok:
            self.disponibles.poner(f"{disponibilidad.disponibles} de {disponibilidad.total} copias disponibles",
                                   "ok" if disponibilidad.disponibles else "advertencia")
            self.disponibles.show()
        ok, ejemplares = self.ejecutar(catalogo.listar_ejemplares, libro.id_libro)
        if not ok:
            return
        self.tabla_ejemplares.cargar([(e.codigo_barras, e.ubicacion, "") for e in ejemplares], datos=ejemplares)
        for fila, e in enumerate(ejemplares):
            self.tabla_ejemplares.setCellWidget(fila, 2, celda_insignia(e.estado, TIPO_ESTADO.get(e.estado, "info")))
        self.acciones_ejemplar.setEnabled(True)

    def _limpiar_ejemplares(self):
        self._id_seleccionado = None
        self.libro_elegido.setText("Selecciona un libro para ver sus copias.")
        self.disponibles.hide()
        self.tabla_ejemplares.cargar([])
        self.acciones_ejemplar.setEnabled(False)

    # Libros

    def _nuevo(self):
        dialogo = DialogoLibro(self.ventana, self._categorias_lista)
        if dialogo.exec() and dialogo.libro is not None:  # 1 = aceptado
            self._id_seleccionado = dialogo.libro.id_libro
            self.avisar(f"Libro registrado: {dialogo.libro.titulo}. Agrega sus copias con el lector.", "ok")
            self._cargar()

    def _editar(self):
        libro = self._libro_actual()
        if libro is None:
            self.avisar("Selecciona el libro que quieres editar.", "info")
            return
        dialogo = DialogoLibro(self.ventana, self._categorias_lista, libro)
        if dialogo.exec() and dialogo.libro is not None:
            self.avisar(f"Libro actualizado: {dialogo.libro.titulo}.", "ok")
            self._cargar()

    def _eliminar(self):
        libro = self._libro_actual()
        if libro is None:
            self.avisar("Selecciona el libro que quieres eliminar.", "info")
            return
        if not confirmar(self, "Eliminar libro",
                         f"¿Eliminar «{libro.titulo}»?\n\nSolo se puede eliminar un libro sin ejemplares. "
                         "El cambio queda registrado en la auditoría.", "Sí, eliminar"):
            return
        ok, _ = self.ejecutar(self.servicios["catalogo"].eliminar_libro, libro.id_libro,
                              exito=f"Libro eliminado: {libro.titulo}.")
        if ok:
            self._id_seleccionado = None
            self._cargar()

    # Ejemplares

    def _ejemplar_actual(self):
        ejemplar = self.tabla_ejemplares.dato_seleccionado()
        if ejemplar is None:
            self.avisar("Selecciona un ejemplar de la lista.", "info")
        return ejemplar

    def _agregar_con_lector(self):
        libro = self._libro_actual()
        if libro is not None:
            self.ventana.mostrar("lector", modo="alta", id_libro=libro.id_libro)

    def _cambiar_ubicacion(self):
        ejemplar = self._ejemplar_actual()
        if ejemplar is None:
            return
        nueva, aceptado = QInputDialog.getText(self, "Cambiar ubicación",
                                               f"Nueva ubicación del ejemplar {ejemplar.codigo_barras}:",
                                               QLineEdit.EchoMode.Normal, ejemplar.ubicacion)
        if not aceptado:
            return
        ok, _ = self.ejecutar(self.servicios["catalogo"].cambiar_ubicacion, ejemplar.codigo_barras, nueva,
                              exito=f"Ejemplar {ejemplar.codigo_barras} movido a {nueva.strip().upper()}.")
        if ok:
            self._recargar_ejemplares()

    def _cambiar_estado(self):
        ejemplar = self._ejemplar_actual()
        if ejemplar is None:
            return
        estado = self.estado_nuevo.currentText()
        if estado == "BAJA" and not confirmar(
                self, "Dar de baja", f"¿Dar de baja el ejemplar {ejemplar.codigo_barras}?\n\n"
                                     "Ya no se podrá prestar.", "Sí, dar de baja"):
            return
        ok, _ = self.ejecutar(self.servicios["catalogo"].cambiar_estado_ejemplar, ejemplar.codigo_barras, estado,
                              exito=f"Ejemplar {ejemplar.codigo_barras}: ahora está en {estado}.")
        if ok:
            self._recargar_ejemplares()

    def _recargar_ejemplares(self):
        """Recarga la lista de libros (columna de disponibles) y las copias del libro elegido."""
        self._cargar()

    def _al_cambiar_tema(self, _nombre):
        self._accion_buscar.setIcon(iconos.icono("buscar", tema.color("tenue")))
