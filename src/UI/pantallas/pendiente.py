from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from UI.componentes import EtiquetaIcono, PanelVidrio, etiqueta
from UI.pantallas.base import Pantalla


class PantallaPendiente(Pantalla):
    """Lugar temporal para los módulos que todavía no se construyen."""

    def __init__(self, ventana, modulo, parent=None):
        super().__init__(ventana, parent)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addStretch(1)
        panel = PanelVidrio(sombra=True)
        panel.setMaximumWidth(560)
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(40, 36, 40, 36)
        caja.setSpacing(12)
        caja.addWidget(EtiquetaIcono("construccion", "acento", 44), 0, Qt.AlignmentFlag.AlignHCenter)
        titulo = etiqueta(f"{modulo.texto}: en construcción", "seccion")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detalle = etiqueta(f"Esta pantalla se agrega en la parte {modulo.parte} de la interfaz. "
                           "El backend que la alimenta ya funciona.", tenue=True, ajustar=True)
        detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja.addWidget(titulo)
        caja.addWidget(detalle)
        raiz.addWidget(panel, 0, Qt.AlignmentFlag.AlignHCenter)
        raiz.addStretch(2)
