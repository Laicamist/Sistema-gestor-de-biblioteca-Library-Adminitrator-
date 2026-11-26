import traceback
from datetime import date, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QStackedWidget,
    QVBoxLayout, QWidget,
)

from config import ALUMNOS, CATALOGO, CONSULTAR, DIAS_PRESTAMO, PRESTAMOS
from Modelos import BibliotecaError, SinConexionError
from UI import iconos, tema
from UI.componentes import (
    Aviso, BotonIcono, CampoLector, Dato, EtiquetaIcono, Insignia, PanelVidrio, boton_gel, etiqueta,
    fecha_texto, repulir,
)
from UI.pantallas.base import Pantalla

# modo: (texto del botón, ícono, permiso, etiqueta del campo)
MODOS = {
    "consultar": ("Consultar", "buscar", CONSULTAR, "Código del ejemplar a consultar"),
    "prestar": ("Prestar", "prestar", PRESTAMOS, "1 · Ejemplar a prestar"),
    "devolver": ("Devolver", "devolver", PRESTAMOS, "Ejemplar que se devuelve"),
    "alta": ("Alta de ejemplar", "agregar", CATALOGO, "Etiqueta nueva del ejemplar"),
}
TIPO_ESTADO = {"DISPONIBLE": "ok", "PRESTADO": "advertencia", "MANTENIMIENTO": "info", "BAJA": "error"}
MAX_LECTURAS = 8


def _sin_prefijo(mensaje: str) -> str:
    """Los procedimientos regresan 'ERROR: ...'; en pantalla basta con el mensaje."""
    texto = str(mensaje)
    return texto[6:].strip() if texto.upper().startswith("ERROR:") else texto


class FichaEjemplar(QWidget):
    """Lo que se sabe de un ejemplar escaneado (resultado de SP_CONSULTAR_EJEMPLAR)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(12)
        cabecera = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.titulo = etiqueta("", "seccion", ajustar=True)
        self.titulo.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.autor = etiqueta("", tenue=True, ajustar=True)
        textos.addWidget(self.titulo)
        textos.addWidget(self.autor)
        cabecera.addLayout(textos, 1)
        self.estado = Insignia("", "info")
        cabecera.addWidget(self.estado, 0, Qt.AlignmentFlag.AlignTop)
        caja.addLayout(cabecera)
        rejilla = QGridLayout()
        rejilla.setSpacing(10)
        self.isbn, self.categoria = Dato("ISBN"), Dato("Categoría")
        self.ubicacion, self.copias = Dato("Ubicación"), Dato("Copias disponibles del libro")
        for i, dato in enumerate((self.isbn, self.categoria, self.ubicacion, self.copias)):
            rejilla.addWidget(dato, i // 2, i % 2)
        caja.addLayout(rejilla)

    def poner(self, e):
        self.titulo.setText(e.titulo)
        self.autor.setText(f"{e.autor} · código {e.codigo_barras}")
        self.estado.poner(e.estado, TIPO_ESTADO.get(e.estado, "info"))
        self.isbn.poner(e.isbn)
        self.categoria.poner(e.categoria)
        self.ubicacion.poner(e.ubicacion)
        self.copias.poner(e.copias_disponibles)


class Lectura(QFrame):
    """Renglón del historial de lecturas de la sesión (verde, rojo, ámbar o informativo)."""

    def __init__(self, tipo: str, titulo: str, detalle: str, parent=None):
        super().__init__(parent)
        self.setObjectName("aviso")
        self.setProperty("tipo", tipo)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(12, 10, 12, 10)
        fila.setSpacing(10)
        icono, token = {"ok": ("ok", "ok"), "error": ("error", "error"),
                        "advertencia": ("advertencia", "aviso")}.get(tipo, ("info", "acento"))
        fila.addWidget(EtiquetaIcono(icono, token, 18), 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        cabeza = etiqueta(titulo, "avisoTexto")
        cabeza.setProperty("tipo", tipo)
        cuerpo = etiqueta(detalle, tenue=True, ajustar=True)
        cuerpo.setStyleSheet("font-size: 13px;")
        textos.addWidget(cabeza)
        textos.addWidget(cuerpo)
        fila.addLayout(textos, 1)
        repulir(self, cabeza)


class PantallaLector(Pantalla):
    """Lector de código de barras. El escáner funciona como teclado: escribe el código
    y manda un sufijo (Enter, Tab o nada, según cómo esté configurado). CampoLector
    detecta el fin de la lectura en cualquiera de esos casos y emite `leido`, que dispara
    la operación en MySQL: consultar (SP_CONSULTAR_EJEMPLAR), prestar (SP_REGISTRAR_PRESTAMO),
    devolver (SP_REGISTRAR_DEVOLUCION) o dar de alta un ejemplar (INSERT con triggers)."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        self.modo = None
        self._ejemplar = None       # ejemplar escaneado en el paso 1 del préstamo
        self._alumno = None         # alumno encontrado en el paso 2 del préstamo
        self._alta_pendiente = None  # código escaneado en alta, esperando confirmación
        self._carreras = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 10, 10)
        raiz.setSpacing(16)

        # Selector de modo (solo los que el rol puede usar)
        selector = PanelVidrio()
        fila = QHBoxLayout(selector)
        fila.setContentsMargins(6, 6, 6, 6)
        fila.setSpacing(6)
        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botones_modo = {}
        for clave, (texto, icono, permiso, _) in MODOS.items():
            if not self.sesiones.puede(permiso):
                continue
            boton = BotonIcono(texto, icono, "segmento", tam=18)
            boton.setCheckable(True)
            boton.setMinimumHeight(44)
            boton.clicked.connect(lambda _marcado=False, m=clave: self.cambiar_modo(m))
            self.grupo.addButton(boton)
            self.botones_modo[clave] = boton
            fila.addWidget(boton, 1)
        raiz.addWidget(selector)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._crear_panel_lectura(), 3)
        cuerpo.addWidget(self._crear_panel_historial(), 2)
        raiz.addLayout(cuerpo, 1)

        self._al_cambiar_tema(tema.gestor.actual)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)
        self.cambiar_modo("consultar")

    # Construcción

    def _crear_panel_lectura(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(24, 22, 24, 22)
        caja.setSpacing(12)
        self.rotulo = etiqueta("", "seccion")
        self.rotulo.setStyleSheet("font-size: 14px; font-weight: 600;")
        caja.addWidget(self.rotulo)
        self.campo = CampoLector()
        self.campo.setObjectName("lector")
        self.campo.setMaxLength(30)
        self.campo.setPlaceholderText("Escanea o escribe el código y presiona Enter")
        self.campo.setClearButtonEnabled(True)
        self._accion_lector = self.campo.addAction(
            iconos.icono("lector", tema.color("acento"), tam=26), QLineEdit.ActionPosition.LeadingPosition)
        self.campo.leido.connect(lambda: self._proteger(self._leer, codigo=self.campo.text().strip()))
        caja.addWidget(self.campo)
        self.ayuda = etiqueta("El campo conserva el foco: después de cada lectura queda listo para la siguiente.",
                              tenue=True, ajustar=True)
        self.ayuda.setStyleSheet("font-size: 13px;")
        caja.addWidget(self.ayuda)

        self.paginas = QStackedWidget()
        self.paginas.addWidget(self._crear_consulta())
        self.paginas.addWidget(self._crear_prestamo())
        self.paginas.addWidget(self._crear_devolucion())
        self.paginas.addWidget(self._crear_alta())
        caja.addWidget(self.paginas)

        self.resultado = Aviso()
        caja.addWidget(self.resultado)
        caja.addStretch(1)
        return panel

    def _crear_consulta(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 6, 0, 0)
        caja.setSpacing(12)
        self.ficha_consulta = FichaEjemplar()
        self.ficha_consulta.hide()
        self.prestado_a = Aviso()
        self.prestado_a._cerrar.hide()
        caja.addWidget(self.ficha_consulta)
        caja.addWidget(self.prestado_a)
        return pagina

    def _crear_prestamo(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 6, 0, 0)
        caja.setSpacing(12)
        self.ficha_prestamo = FichaEjemplar()
        self.ficha_prestamo.hide()
        caja.addWidget(self.ficha_prestamo)

        self.paso_alumno = QWidget()
        paso = QVBoxLayout(self.paso_alumno)
        paso.setContentsMargins(0, 0, 0, 0)
        paso.setSpacing(8)
        rotulo = etiqueta("2 · Alumno: escanea la credencial o escribe la matrícula")
        rotulo.setStyleSheet("font-size: 14px; font-weight: 600;")
        paso.addWidget(rotulo)
        self.matricula = CampoLector()
        self.matricula.setMaxLength(15)
        self.matricula.setPlaceholderText("Matrícula y Enter")
        self._accion_credencial = self.matricula.addAction(
            iconos.icono("credencial", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self.matricula.leido.connect(
            lambda: self._proteger(self._leer_matricula, codigo=self.matricula.text().strip()))
        paso.addWidget(self.matricula)

        self.tarjeta_alumno = QFrame()
        self.tarjeta_alumno.setObjectName("suave")
        fila = QHBoxLayout(self.tarjeta_alumno)
        fila.setContentsMargins(14, 12, 14, 12)
        fila.setSpacing(12)
        self.iniciales = etiqueta("", "avatar")
        self.iniciales.setFixedSize(40, 40)
        self.iniciales.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fila.addWidget(self.iniciales)
        datos = QVBoxLayout()
        datos.setSpacing(2)
        self.nombre_alumno = etiqueta("")
        self.nombre_alumno.setStyleSheet("font-weight: 700;")
        self.detalle_alumno = etiqueta("", tenue=True, ajustar=True)
        datos.addWidget(self.nombre_alumno)
        datos.addWidget(self.detalle_alumno)
        fila.addLayout(datos, 1)
        self.estado_alumno = Insignia("", "ok")
        fila.addWidget(self.estado_alumno, 0, Qt.AlignmentFlag.AlignTop)
        self.tarjeta_alumno.hide()
        paso.addWidget(self.tarjeta_alumno)

        botones = QHBoxLayout()
        self.boton_prestar = boton_gel(f"Registrar préstamo · {DIAS_PRESTAMO} días", "prestar")
        self.boton_prestar.clicked.connect(lambda *_: self._proteger(self._registrar_prestamo))
        cancelar = BotonIcono("Cancelar")
        cancelar.clicked.connect(self._reiniciar_prestamo)
        botones.addWidget(self.boton_prestar)
        botones.addWidget(cancelar)
        botones.addStretch(1)
        paso.addLayout(botones)
        self.paso_alumno.hide()
        caja.addWidget(self.paso_alumno)
        return pagina

    def _crear_devolucion(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 6, 0, 0)
        caja.setSpacing(12)
        self.ficha_devolucion = FichaEjemplar()
        self.ficha_devolucion.hide()
        caja.addWidget(self.ficha_devolucion)
        return pagina

    def _crear_alta(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 6, 0, 0)
        caja.setSpacing(10)
        formulario = QGridLayout()
        formulario.setHorizontalSpacing(14)
        formulario.setVerticalSpacing(6)
        formulario.addWidget(etiqueta("Libro"), 0, 0)
        formulario.addWidget(etiqueta("Ubicación"), 0, 1)
        self.libros = QComboBox()
        self.libros.setMinimumWidth(260)
        self.ubicacion = QLineEdit()
        self.ubicacion.setMaxLength(60)
        self.ubicacion.setPlaceholderText("Por ejemplo, PASILLO A - ESTANTE 1")
        formulario.addWidget(self.libros, 1, 0)
        formulario.addWidget(self.ubicacion, 1, 1)
        formulario.setColumnStretch(0, 3)
        formulario.setColumnStretch(1, 2)
        caja.addLayout(formulario)
        self.confirmacion_alta = Aviso()
        self.confirmacion_alta._cerrar.hide()
        caja.addWidget(self.confirmacion_alta)
        botones = QHBoxLayout()
        self.boton_alta = boton_gel("Registrar ejemplar", "agregar")
        self.boton_alta.clicked.connect(lambda *_: self._proteger(self._registrar_alta))
        cancelar = BotonIcono("Cancelar")
        cancelar.clicked.connect(self._reiniciar_alta)
        botones.addWidget(self.boton_alta)
        botones.addWidget(cancelar)
        botones.addStretch(1)
        caja.addLayout(botones)
        nota = etiqueta("Elige el libro y la ubicación, escanea la etiqueta nueva y confirma con Enter, "
                        "escaneándola otra vez o con el botón.", tenue=True, ajustar=True)
        nota.setStyleSheet("font-size: 13px;")
        caja.addWidget(nota)
        return pagina

    def _crear_panel_historial(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(20, 20, 20, 20)
        caja.setSpacing(10)
        caja.addWidget(etiqueta("Últimas lecturas", "seccion"))
        self.vacio = etiqueta("Aquí aparece cada código que leas en esta sesión.", tenue=True, ajustar=True)
        caja.addWidget(self.vacio)
        self.lecturas = QVBoxLayout()
        self.lecturas.setSpacing(8)
        caja.addLayout(self.lecturas)
        caja.addStretch(1)
        return panel

    # Modo y foco

    def al_mostrar(self, **opciones):
        modo = opciones.get("modo")
        if modo in self.botones_modo:
            self.cambiar_modo(modo)
        elif self.modo == "alta":
            self._cargar_libros()
        id_libro = opciones.get("id_libro")
        if id_libro is not None and self.modo == "alta":
            indice = self.libros.findData(id_libro)  # viene del catálogo: libro ya elegido
            if indice >= 0:
                self.libros.setCurrentIndex(indice)
        self._enfocar()

    def cambiar_modo(self, modo: str):
        if modo not in self.botones_modo:
            return
        self.modo = modo
        self.botones_modo[modo].setChecked(True)
        self.rotulo.setText(MODOS[modo][3])
        self.paginas.setCurrentIndex(list(MODOS).index(modo))
        self.resultado.ocultar()
        self._reiniciar_prestamo(enfocar=False)
        self._reiniciar_alta(enfocar=False)
        self.ficha_consulta.hide()
        self.prestado_a.ocultar()
        self.ficha_devolucion.hide()
        if modo == "alta":
            self._cargar_libros()
        self._enfocar()

    def _enfocar(self):
        """Devuelve el foco al campo que espera la siguiente lectura del escáner."""
        destino = self.matricula if (self.modo == "prestar" and self._ejemplar is not None) else self.campo
        QTimer.singleShot(0, destino.setFocus)
        QTimer.singleShot(0, destino.selectAll)

    # Lectura del código

    def _leer(self):
        codigo = self.campo.text().strip()
        if not codigo:
            return
        acciones = {"consultar": self._consultar, "prestar": self._escanear_para_prestamo,
                    "devolver": self._devolver, "alta": self._escanear_para_alta}
        acciones[self.modo](codigo)
        self._enfocar()

    def _consultar(self, codigo: str):
        ok, e = self._llamar(self.servicios["prestamos"].consultar_ejemplar, codigo,
                             titulo_error="Código no encontrado", codigo=codigo)
        if not ok:
            self.ficha_consulta.hide()
            self.prestado_a.ocultar()
            return
        self.ficha_consulta.poner(e)
        self.ficha_consulta.show()
        if e.prestado_a:
            atraso = (date.today() - e.fecha_limite).days if e.fecha_limite else 0
            if atraso > 0:
                texto, tipo = f"Prestado a {e.prestado_a} ({e.matricula_alumno}) · venció hace {atraso} días", "error"
            else:
                texto, tipo = (f"Prestado a {e.prestado_a} ({e.matricula_alumno}) · "
                               f"se devuelve a más tardar el {fecha_texto(e.fecha_limite)}"), "advertencia"
            self.prestado_a.mostrar(texto, tipo, 0)
        else:
            self.prestado_a.ocultar()
        self.resultado.ocultar()
        self.ventana.sonidos.reproducir("exito")
        self._agregar_lectura("info", "Consulta", f"{codigo} · {e.titulo} · {e.estado}")

    # Préstamo (dos pasos: ejemplar y alumno)

    def _escanear_para_prestamo(self, codigo: str):
        ok, e = self._llamar(self.servicios["prestamos"].consultar_ejemplar, codigo,
                             titulo_error="Código no encontrado", codigo=codigo)
        if not ok:
            self._reiniciar_prestamo(enfocar=False)
            return
        self._ejemplar = e
        self._alumno = None
        self.ficha_prestamo.poner(e)
        self.ficha_prestamo.show()
        self.paso_alumno.show()
        self.tarjeta_alumno.hide()
        self.matricula.clear()
        self.boton_prestar.setEnabled(False)
        if e.disponible:
            self.resultado.ocultar()
        else:
            self.resultado.mostrar(f"Este ejemplar está {e.estado}: MySQL rechazará el préstamo si continúas.",
                                   "advertencia", 0)
        self.ventana.sonidos.reproducir("exito" if e.disponible else "error")

    def _leer_matricula(self):
        matricula = self.matricula.text().strip().upper()
        if not matricula or self._ejemplar is None:
            return
        if self._alumno is not None and self._alumno.matricula.upper() == matricula:
            self._registrar_prestamo()  # segundo Enter con la misma matrícula: confirma
            return
        if self.sesiones.puede(ALUMNOS):
            ok, alumno = self._llamar(self.servicios["alumnos"].buscar, matricula,
                                      titulo_error="Alumno no encontrado", codigo=matricula)
            if not ok:
                self.tarjeta_alumno.hide()
                self._alumno = None
                self.boton_prestar.setEnabled(False)
                self._enfocar()
                return
        else:  # sin permiso para ver alumnos: se presta solo con la matrícula
            alumno = None
        self._alumno = alumno
        self._mostrar_alumno(alumno, matricula)
        self.boton_prestar.setEnabled(True)
        self.ventana.sonidos.reproducir("exito")
        self._enfocar()

    def _mostrar_alumno(self, alumno, matricula: str):
        if alumno is None:
            self.nombre_alumno.setText(f"Matrícula {matricula}")
            self.detalle_alumno.setText("Presiona Enter otra vez o el botón para registrar el préstamo.")
            self.iniciales.setText(matricula[:2])
            self.estado_alumno.hide()
            self.tarjeta_alumno.show()
            return
        activos = 0
        ok, historial = self._llamar_silencioso(self.servicios["prestamos"].historial, alumno.matricula)
        if ok:
            activos = sum(1 for h in historial if h.estado == "ACTIVO")
        carrera = self._nombre_carrera(alumno.id_carrera)
        partes = [p for p in (carrera, f"{alumno.semestre}° semestre",
                              f"{activos} de 3 préstamos activos") if p]
        self.nombre_alumno.setText(f"{alumno.nombre_completo} ({alumno.matricula})")
        self.detalle_alumno.setText(" · ".join(partes) + "\nPresiona Enter otra vez o el botón para registrar.")
        self.iniciales.setText("".join(p[0] for p in alumno.nombre_completo.split()[:2]).upper())
        self.estado_alumno.poner(alumno.estado, "ok" if alumno.estado == "ACTIVO" else "error")
        self.estado_alumno.show()
        self.tarjeta_alumno.show()

    def _nombre_carrera(self, id_carrera) -> str:
        if self._carreras is None:
            ok, carreras = self._llamar_silencioso(self.servicios["alumnos"].listar_carreras)
            self._carreras = {c.id_carrera: c.nombre for c in carreras} if ok else {}
        return self._carreras.get(id_carrera, "")

    def _registrar_prestamo(self):
        if self._ejemplar is None:
            return
        matricula = self.matricula.text().strip().upper()
        codigo = self._ejemplar.codigo_barras
        ok, mensaje = self._llamar(self.servicios["prestamos"].prestar, codigo, matricula,
                                   titulo_error="Préstamo rechazado", codigo=f"{codigo} · {matricula}")
        if ok:
            limite = date.today() + timedelta(days=DIAS_PRESTAMO)
            nombre = self._alumno.nombre_completo if self._alumno else matricula
            self.resultado.mostrar(f"{_sin_prefijo(mensaje)} · se devuelve a más tardar el {fecha_texto(limite)}",
                                   "ok", 0)
            self.ventana.sonidos.reproducir("exito")
            self._agregar_lectura("ok", "Préstamo", f"{codigo} · {self._ejemplar.titulo} · {nombre}")
        self._reiniciar_prestamo(limpiar_resultado=False)

    def _reiniciar_prestamo(self, *_, enfocar: bool = True, limpiar_resultado: bool = True):
        self._ejemplar = None
        self._alumno = None
        self.ficha_prestamo.hide()
        self.paso_alumno.hide()
        self.tarjeta_alumno.hide()
        self.matricula.clear()
        if limpiar_resultado:
            self.resultado.ocultar()
        if enfocar:
            self.campo.clear()
            self._enfocar()

    # Devolución

    def _devolver(self, codigo: str):
        servicio = self.servicios["prestamos"]
        ok, e = self._llamar(servicio.consultar_ejemplar, codigo, titulo_error="Código no encontrado",
                             codigo=codigo)
        if not ok:
            self.ficha_devolucion.hide()
            return
        ok, dias = self._llamar(servicio.devolver, codigo, titulo_error="Devolución rechazada", codigo=codigo)
        if not ok:
            self.ficha_devolucion.hide()
            return
        ok, actualizado = self._llamar_silencioso(servicio.consultar_ejemplar, codigo)
        self.ficha_devolucion.poner(actualizado if ok else e)
        self.ficha_devolucion.show()
        quien = f" por {e.prestado_a}" if e.prestado_a else ""
        if dias > 0:
            self.resultado.mostrar(f"DEVOLUCION REGISTRADA{quien} · {dias} días de retraso", "advertencia", 0)
            self._agregar_lectura("advertencia", "Devolución con retraso", f"{codigo} · {e.titulo} · {dias} días")
        else:
            self.resultado.mostrar(f"DEVOLUCION REGISTRADA{quien} · a tiempo", "ok", 0)
            self._agregar_lectura("ok", "Devolución", f"{codigo} · {e.titulo}")
        self.ventana.sonidos.reproducir("exito")

    # Alta de ejemplar

    def _cargar_libros(self):
        ok, libros = self._llamar_silencioso(self.servicios["catalogo"].listar_libros)
        if not ok:
            return
        seleccionado = self.libros.currentData()
        self.libros.clear()
        for libro in libros:
            self.libros.addItem(f"{libro.titulo} · {libro.isbn}", libro.id_libro)
        indice = self.libros.findData(seleccionado)
        if indice >= 0:
            self.libros.setCurrentIndex(indice)

    def _escanear_para_alta(self, codigo: str):
        if self._alta_pendiente == codigo:
            self._registrar_alta()  # segundo Enter con la misma etiqueta: confirma
            return
        self._alta_pendiente = codigo
        libro = self.libros.currentText().split(" · ")[0] or "el libro elegido"
        ubicacion = self.ubicacion.text().strip().upper() or "(captura la ubicación)"
        self.confirmacion_alta.mostrar(f"La etiqueta {codigo} se registrará como copia nueva de {libro} "
                                       f"en {ubicacion}. Presiona Enter otra vez o el botón para confirmar.",
                                       "info", 0)
        self.boton_alta.setEnabled(True)
        self.resultado.ocultar()

    def _registrar_alta(self):
        codigo = self._alta_pendiente or self.campo.text().strip()
        ok, ejemplar = self._llamar(self.servicios["catalogo"].registrar_ejemplar, codigo,
                                    self.libros.currentData(), self.ubicacion.text(),
                                    titulo_error="Alta rechazada", codigo=codigo)
        if ok:
            libro = self.libros.currentText().split(" · ")[0]
            self.resultado.mostrar(f"Ejemplar {codigo} registrado como copia de {libro}.", "ok", 0)
            self.ventana.sonidos.reproducir("exito")
            self._agregar_lectura("ok", "Alta de ejemplar", f"{codigo} · {libro} · {ejemplar.ubicacion}")
        self._reiniciar_alta(limpiar_resultado=False)

    def _reiniciar_alta(self, *_, enfocar: bool = True, limpiar_resultado: bool = True):
        self._alta_pendiente = None
        self.confirmacion_alta.ocultar()
        self.boton_alta.setEnabled(False)
        if limpiar_resultado:
            self.resultado.ocultar()
        if enfocar:
            self.campo.clear()
            self._enfocar()

    # Llamadas a los servicios

    def _proteger(self, accion, codigo: str = ""):
        """Ejecuta una lectura o un botón sin que un error se pierda en la consola: si algo
        falla fuera de los servicios (al llenar la ficha, por ejemplo), se avisa en rojo,
        suena el tono de error y la traza completa queda en la terminal."""
        try:
            accion()
        except Exception as error:  # noqa: BLE001 - la pantalla nunca debe quedarse sin respuesta
            traceback.print_exc()
            mensaje = f"No se pudo procesar la lectura: {error}"
            self.resultado.mostrar(mensaje, "error", 0)
            self.ventana.sonidos.reproducir("error")
            self._agregar_lectura("error", "Lectura no procesada", f"{mensaje}\n{codigo}" if codigo else mensaje)
            self._enfocar()

    def _llamar(self, funcion, *args, titulo_error: str = "Error", codigo: str = ""):
        """Ejecuta un servicio; si falla muestra el mensaje (del trigger o del servicio)
        en rojo, suena el tono de error y lo anota en el historial."""
        try:
            return True, funcion(*args)
        except (BibliotecaError, SinConexionError) as error:
            mensaje = _sin_prefijo(error)
        except Exception as error:  # noqa: BLE001
            mensaje = f"Error inesperado: {error}"
        self.resultado.mostrar(mensaje, "error", 0)
        self.ventana.sonidos.reproducir("error")
        self._agregar_lectura("error", titulo_error, f"{mensaje}\n{codigo}" if codigo else mensaje)
        return False, None

    @staticmethod
    def _llamar_silencioso(funcion, *args):
        """Para datos de apoyo (carreras, historial): si fallan, la pantalla sigue sin ellos."""
        try:
            return True, funcion(*args)
        except Exception:  # noqa: BLE001
            return False, None

    def _agregar_lectura(self, tipo: str, titulo: str, detalle: str):
        self.vacio.hide()
        self.lecturas.insertWidget(0, Lectura(tipo, titulo, detalle))
        while self.lecturas.count() > MAX_LECTURAS:
            elemento = self.lecturas.takeAt(self.lecturas.count() - 1)
            if elemento.widget() is not None:
                elemento.widget().deleteLater()

    def _al_cambiar_tema(self, _nombre):
        self._accion_lector.setIcon(iconos.icono("lector", tema.color("acento"), tam=26))
        self._accion_credencial.setIcon(iconos.icono("credencial", tema.color("tenue")))
