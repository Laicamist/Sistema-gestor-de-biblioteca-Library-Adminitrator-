"""Piezas reutilizables de la interfaz (estilo Aero moderno).

Todas reaccionan al cambio de tema: se conectan a `tema.gestor.cambiado` con un
método propio, así Qt desconecta la señal solo cuando el widget se destruye.
"""
import csv
import time

from PySide6.QtCore import (
    QEasingCurve, QEvent, QObject, QPointF, QPropertyAnimation, QSettings, QSize, QTimer, QUrl, Qt, Signal,
)
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
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


_TECLAS_EDICION = {
    Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up,
    Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_Escape,
}


class CampoLector(QLineEdit):
    """Campo donde escribe el lector de código de barras. Emite `leido` cuando termina una lectura.

    El lector es un teclado (HID): escribe el código muy rápido y al final manda un sufijo.
    Casi todos mandan Enter, pero hay modelos configurados para mandar Tab, un salto de
    línea (Ctrl+J) o nada. Con un QLineEdit normal solo el Enter dispara `returnPressed`,
    y con los demás el código aparecía en el campo sin que pasara nada. Aquí `leido` se
    emite en todos los casos:
      - con Enter (también el del teclado numérico), Ctrl+J o Ctrl+M;
      - con Tab, si el campo tiene texto (vacío, Tab sigue cambiando de campo);
      - si no llega ningún sufijo, al terminar una ráfaga de teclas tan rápida que solo
        puede venir del lector. Al escribir a mano hay que presionar Enter, como siempre.
    """

    leido = Signal()

    RAFAGA_MS = 60     # el lector deja menos de esto entre carácter y carácter
    MIN_RAFAGA = 6     # caracteres seguidos a esa velocidad para tomarlo como lectura
    SILENCIO_MS = 150  # tiempo sin teclas que marca el fin de una lectura sin sufijo
    ECO_MS = 600       # un Enter que llega justo después de una lectura automática se ignora

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ultima_tecla = None   # momento (ms) del último carácter escrito
        self._rafaga = 0            # caracteres seguidos escritos a velocidad de lector
        self._automatica = None     # (momento, texto) de la última lectura detectada sin sufijo
        self._silencio = QTimer(self)
        self._silencio.setSingleShot(True)
        self._silencio.setInterval(self.SILENCIO_MS)
        self._silencio.timeout.connect(self._fin_de_rafaga)

    def event(self, evento):
        # Tab se atiende antes de keyPressEvent (mueve el foco), por eso se atrapa aquí.
        if (evento.type() == QEvent.Type.KeyPress and evento.key() == Qt.Key.Key_Tab
                and evento.modifiers() == Qt.KeyboardModifier.NoModifier and self.text().strip()):
            self._terminar()
            return True
        return super().event(evento)

    def keyPressEvent(self, evento):
        tecla, mods = evento.key(), evento.modifiers()
        # Ctrl sin Alt (AltGr llega como Ctrl+Alt y escribe caracteres como @)
        control = (bool(mods & Qt.KeyboardModifier.ControlModifier)
                   and not bool(mods & Qt.KeyboardModifier.AltModifier))
        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter) or (control and tecla in (Qt.Key.Key_J, Qt.Key.Key_M)):
            self._terminar()
            evento.accept()
            return
        texto = evento.text()
        super().keyPressEvent(evento)
        if texto and texto.isprintable() and not control:
            self._contar_caracter(evento.timestamp() or int(time.monotonic() * 1000))
        elif control or tecla in _TECLAS_EDICION:  # borrar, flechas, pegar...: ya no es una lectura
            self._rafaga = 0
            self._silencio.stop()
        # Shift, Alt, Bloq Mayús... no cuentan ni cortan la ráfaga (el lector usa Shift en las mayúsculas)

    def _contar_caracter(self, ahora_ms: int):
        rapido = self._ultima_tecla is not None and 0 <= ahora_ms - self._ultima_tecla <= self.RAFAGA_MS
        self._rafaga = self._rafaga + 1 if rapido else 1
        self._ultima_tecla = ahora_ms
        self._automatica = None
        if self._rafaga >= self.MIN_RAFAGA:
            self._silencio.start()  # se reinicia con cada carácter; vence cuando el lector termina
        else:
            self._silencio.stop()

    def _fin_de_rafaga(self):
        """El lector dejó de escribir y no mandó sufijo: la lectura terminó."""
        if self._rafaga >= self.MIN_RAFAGA and self.text().strip():
            self._rafaga = 0
            self._automatica = (time.monotonic(), self.text())
            self.leido.emit()

    def _terminar(self):
        """Llegó el sufijo (Enter, Tab, Ctrl+J o Ctrl+M) o el usuario presionó Enter."""
        self._silencio.stop()
        self._rafaga = 0
        if self._automatica is not None:
            momento, texto = self._automatica
            self._automatica = None
            if texto == self.text() and (time.monotonic() - momento) * 1000 < self.ECO_MS:
                return  # sufijo atrasado de una lectura que ya se procesó: no repetirla
        self.leido.emit()


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
