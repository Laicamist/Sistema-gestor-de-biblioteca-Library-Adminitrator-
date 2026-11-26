"""Piezas reutilizables de la interfaz (estilo Aero moderno).

Todas reaccionan al cambio de tema: se conectan a `tema.gestor.cambiado` con un
método propio, así Qt desconecta la señal solo cuando el widget se destruye.
"""
import csv

from PySide6.QtCore import QEasingCurve, QObject, QPointF, QPropertyAnimation, QSettings, QSize, QTimer, QUrl, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from UI import iconos, tema

try:  # QtMultimedia viene con PySide6; si faltara, la app sigue sin sonido.
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover
    QSoundEffect = None


def repulir(*widgets):
    """Vuelve a aplicar la hoja de estilos después de cambiar una propiedad (por ejemplo `tipo`)."""
    for widget in widgets:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


def etiqueta(texto: str = "", nombre: str = None, tenue: bool = False, ajustar: bool = False) -> QLabel:
    """QLabel con nombre de objeto (para el QSS) y opción de texto tenue o con saltos de línea."""
    lbl = QLabel(texto)
    if nombre:
        lbl.setObjectName(nombre)
    if tenue:
        lbl.setProperty("tenue", True)
    if ajustar:
        lbl.setWordWrap(True)
    return lbl


class FondoAero(QWidget):
    """Fondo de la ventana: degradado de cielo (u océano) con dos brillos suaves."""

    def __init__(self, parent=None):
        super().__init__(parent)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    def _al_cambiar_tema(self, _nombre):
        self.update()

    def paintEvent(self, _evento):
        c = tema.colores()
        r = self.rect()
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QLinearGradient(QPointF(r.topLeft()), QPointF(r.bottomRight()))
        base.setColorAt(0.0, QColor(c["fondo1"]))
        base.setColorAt(0.46, QColor(c["fondo2"]))
        base.setColorAt(1.0, QColor(c["fondo3"]))
        pintor.fillRect(r, QBrush(base))
        lado = max(r.width(), r.height())
        for (x, y, radio, rgba) in ((0.88, -0.12, 0.62, c["brillo"]), (-0.10, 1.12, 0.55, c["brillo2"])):
            brillo = QRadialGradient(QPointF(r.width() * x, r.height() * y), lado * radio)
            brillo.setColorAt(0.0, QColor(*rgba))
            brillo.setColorAt(1.0, QColor(rgba[0], rgba[1], rgba[2], 0))
            pintor.fillRect(r, QBrush(brillo))
        pintor.end()


class Sombra(QGraphicsDropShadowEffect):
    """Sombra suave de los paneles de vidrio; su color sigue al tema."""

    def __init__(self, parent=None, desenfoque: int = 32, desplazamiento: int = 8):
        super().__init__(parent)
        self.setBlurRadius(desenfoque)
        self.setOffset(0, desplazamiento)
        self._al_cambiar_tema(tema.gestor.actual)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    def _al_cambiar_tema(self, _nombre):
        self.setColor(tema.color("sombra"))


class PanelVidrio(QFrame):
    """Tarjeta semitransparente con borde claro. `sombra=True` solo en paneles sin tablas
    grandes (el efecto de sombra hace más lento el desplazamiento)."""

    def __init__(self, parent=None, sombra: bool = False):
        super().__init__(parent)
        self.setObjectName("vidrio")
        if sombra:
            self.setGraphicsEffect(Sombra(self))


class BotonIcono(QPushButton):
    """Botón con ícono de línea que se redibuja con el color del tema.
    `nombre_objeto` elige el estilo del QSS: 'gel', 'nav', 'pastilla', 'segmento', 'enlace'."""

    def __init__(self, texto: str = "", icono: str = None, nombre_objeto: str = None,
                 token: str = "texto", token_activo: str = None, tam: int = 20, parent=None):
        super().__init__(texto, parent)
        self._icono, self._token, self._token_activo, self._tam = icono, token, token_activo, tam
        if nombre_objeto:
            self.setObjectName(nombre_objeto)
        if nombre_objeto == "gel":  # el texto del gel siempre es blanco
            self._token = self._token_activo = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._al_cambiar_tema(tema.gestor.actual)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    def cambiar_icono(self, icono: str, token: str = None):
        """Cambia el ícono y, si se indica, el color del tema con que se dibuja."""
        self._icono = icono
        if token is not None and self.objectName() != "gel":
            self._token = token
        self._al_cambiar_tema(tema.gestor.actual)

    def _al_cambiar_tema(self, _nombre):
        if not self._icono:
            return
        normal = "#ffffff" if self._token is None else tema.color(self._token)
        activo = "#ffffff" if self._token_activo is None else tema.color(self._token_activo)
        self.setIcon(iconos.icono(self._icono, normal, activo, self._tam))
        self.setIconSize(QSize(self._tam, self._tam))


def boton_gel(texto: str, icono: str = None) -> BotonIcono:
    """Botón principal con brillo tipo gel."""
    boton = BotonIcono(texto, icono, "gel", tam=18)
    boton.setMinimumHeight(46)
    return boton


class EtiquetaIcono(QLabel):
    """Solo un ícono (sin texto), en el color de un token del tema."""

    def __init__(self, icono: str, token: str = "acento", tam: int = 20, parent=None):
        super().__init__(parent)
        self._icono, self._token, self._tam = icono, token, tam
        self.setFixedSize(tam, tam)
        self._al_cambiar_tema(tema.gestor.actual)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    def cambiar(self, icono: str = None, token: str = None):
        self._icono = icono or self._icono
        self._token = token or self._token
        self._al_cambiar_tema(tema.gestor.actual)

    def _al_cambiar_tema(self, _nombre):
        color = "#ffffff" if self._token == "blanco" else tema.color(self._token)
        self.setPixmap(iconos.pixmap(self._icono, color, self._tam))


class LogoGel(QLabel):
    """Cuadro con brillo gel y el ícono del libro: la marca de la aplicación."""

    def __init__(self, lado: int = 42, parent=None):
        super().__init__(parent)
        self.setFixedSize(lado, lado)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        radio = round(lado * 0.32)
        self.setStyleSheet(f"background: {tema.GEL}; border: 1px solid #095f79; border-radius: {radio}px;")
        self.setPixmap(iconos.pixmap("libro", "#ffffff", round(lado * 0.52)))


class Insignia(QLabel):
    """Etiqueta pequeña de estado (DISPONIBLE, PRESTADO, VENCIDO...)."""

    def __init__(self, texto: str = "", tipo: str = "info", parent=None):
        super().__init__(texto, parent)
        self.setObjectName("insignia")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.poner(texto, tipo)

    def poner(self, texto: str, tipo: str = "info"):
        self.setText(texto)
        self.setProperty("tipo", tipo)
        repulir(self)


_ICONO_AVISO = {"ok": ("ok", "ok"), "error": ("error", "error"),
                "advertencia": ("advertencia", "aviso"), "info": ("info", "acento")}


def celda_insignia(texto: str, tipo: str) -> QWidget:
    """Insignia de color para ponerla dentro de una celda de `Tabla` (setCellWidget)."""
    celda = QWidget()
    fila = QHBoxLayout(celda)
    fila.setContentsMargins(6, 0, 6, 0)
    fila.addWidget(Insignia(texto, tipo))
    fila.addStretch(1)
    return celda


def exportar_csv(padre: QWidget, nombre_sugerido: str, columnas: list, filas: list):
    """Pide dónde guardar y escribe un CSV que Excel abre con acentos (UTF-8 con BOM).
    Regresa la ruta guardada, o None si el usuario canceló."""
    ruta, _ = QFileDialog.getSaveFileName(padre, "Exportar a CSV", nombre_sugerido, "Archivo CSV (*.csv)")
    if not ruta:
        return None
    if not ruta.lower().endswith(".csv"):
        ruta += ".csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(columnas)
        escritor.writerows([["" if v is None else v for v in fila] for fila in filas])
    return ruta


def fecha_texto(valor) -> str:
    """Fecha como dd/mm/aaaa, o un guion si no hay."""
    return f"{valor:%d/%m/%Y}" if valor else "—"


class Dato(QFrame):
    """Recuadro pequeño con un título tenue y un valor (ISBN, ubicación, correo...)."""

    def __init__(self, titulo: str, parent=None):
        super().__init__(parent)
        self.setObjectName("suave")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(14, 10, 14, 10)
        caja.setSpacing(2)
        rotulo = etiqueta(titulo, tenue=True)
        rotulo.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.valor = etiqueta("—", ajustar=True)
        self.valor.setStyleSheet("font-size: 15px; font-weight: 600;")
        caja.addWidget(rotulo)
        caja.addWidget(self.valor)

    def poner(self, texto):
        self.valor.setText("—" if texto in (None, "") else str(texto))


class Aviso(QFrame):
    """Aviso dentro de la pantalla (verde, rojo, ámbar o informativo).
    Aparece con un fundido y se oculta solo después de `duracion_ms` (0 = se queda)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aviso")
        self.setProperty("tipo", "info")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 12, 12, 12)
        fila.setSpacing(12)
        self._icono = EtiquetaIcono("info", "acento", 20)
        self._texto = etiqueta("", "avisoTexto", ajustar=True)
        self._texto.setProperty("tipo", "info")
        self._texto.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._cerrar = BotonIcono("", "error", "enlace", token="tenue", tam=16)
        self._cerrar.setToolTip("Cerrar aviso")
        self._cerrar.clicked.connect(self.ocultar)
        fila.addWidget(self._icono, 0, Qt.AlignmentFlag.AlignTop)
        fila.addWidget(self._texto, 1)
        fila.addWidget(self._cerrar, 0, Qt.AlignmentFlag.AlignTop)
        self._opacidad = QGraphicsOpacityEffect(self)
        self._opacidad.setOpacity(1.0)
        self.setGraphicsEffect(self._opacidad)
        self._animacion = QPropertyAnimation(self._opacidad, b"opacity", self)
        self._animacion.setDuration(220)
        self._animacion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.timeout.connect(self.ocultar)
        self.hide()

    def mostrar(self, texto: str, tipo: str = "info", duracion_ms: int = 6000):
        tipo = tipo if tipo in _ICONO_AVISO else "info"
        icono, token = _ICONO_AVISO[tipo]
        self._texto.setText(texto)
        self.setProperty("tipo", tipo)
        self._texto.setProperty("tipo", tipo)
        self._icono.cambiar(icono, token)
        repulir(self, self._texto)
        self._animacion.stop()
        self._opacidad.setOpacity(0.0)
        self.show()
        self._animacion.setStartValue(0.0)
        self._animacion.setEndValue(1.0)
        self._animacion.start()
        self._temporizador.stop()
        if duracion_ms > 0:
            self._temporizador.start(duracion_ms)

    def ocultar(self):
        self._temporizador.stop()
        self.hide()


def fundido(widget: QWidget, duracion_ms: int = 220):
    """Animación de entrada (de transparente a visible) al cambiar de pantalla.
    Al terminar quita el efecto para que la pantalla no se dibuje más lento."""
    efecto = QGraphicsOpacityEffect(widget)
    efecto.setOpacity(0.0)
    widget.setGraphicsEffect(efecto)
    animacion = QPropertyAnimation(efecto, b"opacity", widget)
    animacion.setDuration(duracion_ms)
    animacion.setStartValue(0.0)
    animacion.setEndValue(1.0)
    animacion.setEasingCurve(QEasingCurve.Type.OutCubic)
    animacion.finished.connect(lambda: widget.setGraphicsEffect(None))
    animacion.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def confirmar(padre: QWidget, titulo: str, texto: str, boton_si: str = "Sí, continuar") -> bool:
    """Ventana de confirmación, solo para acciones peligrosas (eliminar, dar de baja)."""
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Warning)
    caja.setWindowTitle(titulo)
    caja.setText(texto)
    si = caja.addButton(boton_si, QMessageBox.ButtonRole.AcceptRole)
    no = caja.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    caja.setDefaultButton(no)
    caja.exec()
    return caja.clickedButton() is si


class Tabla(QTableWidget):
    """Tabla de solo lectura con el estilo del tema: filas completas, sin rejilla, sin edición."""

    def __init__(self, columnas: list, parent=None):
        super().__init__(0, len(columnas), parent)
        self.setHorizontalHeaderLabels(columnas)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWordWrap(False)
        cabecera = self.horizontalHeader()
        cabecera.setHighlightSections(False)
        cabecera.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        cabecera.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setDefaultSectionSize(44)

    def cargar(self, filas: list, datos: list = None):
        """`filas`: lista de tuplas con el texto de cada celda.
        `datos`: objeto asociado a cada fila (se recupera con `dato_seleccionado`)."""
        self.setRowCount(0)
        self.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            for j, valor in enumerate(fila):
                celda = QTableWidgetItem("" if valor is None else str(valor))
                if j == 0 and datos is not None:
                    celda.setData(Qt.ItemDataRole.UserRole, datos[i])
                self.setItem(i, j, celda)

    def dato_seleccionado(self):
        fila = self.currentRow()
        if fila < 0 or self.item(fila, 0) is None:
            return None
        return self.item(fila, 0).data(Qt.ItemDataRole.UserRole)


class Sonidos(QObject):
    """Tonos del lector: uno de éxito y otro de error. Se pueden silenciar y la
    preferencia se guarda entre sesiones."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ajustes = QSettings("ITSUR", "LibraryAdministrator")
        self.activo = str(self._ajustes.value("sonido", "true")).lower() == "true"
        self._efectos = {}
        if QSoundEffect is not None:
            for nombre in ("exito", "error"):
                efecto = QSoundEffect(self)
                efecto.setSource(QUrl.fromLocalFile(str(tema.RECURSOS / "sonidos" / f"{nombre}.wav")))
                efecto.setVolume(0.6)
                self._efectos[nombre] = efecto

    def reproducir(self, nombre: str):
        if self.activo and nombre in self._efectos:
            self._efectos[nombre].play()

    def alternar(self) -> bool:
        self.activo = not self.activo
        self._ajustes.setValue("sonido", "true" if self.activo else "false")
        return self.activo
