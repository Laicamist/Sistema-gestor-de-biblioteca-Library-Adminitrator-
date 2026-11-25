"""Íconos de línea (estilo Lucide) dibujados como SVG en el color que se pida.

Se generan en tiempo de ejecución, así no hay que guardar imágenes y el mismo
ícono sirve para el tema claro y el oscuro: solo cambia el color.
"""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Solo el contenido del <svg>: trazos de 24 x 24.
TRAZOS = {
    "libro": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "inicio": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "lector": ('<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2'
               'M7 21H5a2 2 0 0 1-2-2v-2M8 7v10M12 7v10M17 7v10"/>'),
    "alumnos": ('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
                '<path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>'),
    "reportes": '<path d="M3 3v18h18M18 17V9M13 17V5M8 17v-3"/>',
    "auditoria": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/>',
    "usuarios": ('<circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4"/>'
                 '<circle cx="18" cy="17" r="3"/><path d="M18 12v2M18 20v2M13 17h2M21 17h2"/>'),
    "salir": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    "sol": ('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41'
            'M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'),
    "luna": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "usuario": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    "candado": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "ojo": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    "ojo_cerrado": ('<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24M10.73 5.08A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7'
                    'a13.2 13.2 0 0 1-1.67 2.68M6.61 6.61A13.5 13.5 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.39-1.61'
                    'M2 2l20 20"/>'),
    "ok": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "error": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
    "advertencia": ('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86'
                    'a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>'),
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "reloj": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "prestar": '<path d="M8 3 4 7l4 4M4 7h16M16 21l4-4-4-4M20 17H4"/>',
    "devolver": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "buscar": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "agregar": '<path d="M12 5v14M5 12h14"/>',
    "editar": '<path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "eliminar": ('<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4'
                 'a2 2 0 0 1 2 2v2M10 11v6M14 11v6"/>'),
    "ubicacion": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "credencial": ('<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="12" r="2"/>'
                   '<path d="M13 10h5M13 14h3"/>'),
    "sonido": '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>',
    "silencio": '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="m23 9-6 6M17 9l6 6"/>',
    "actualizar": '<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>',
    "construccion": ('<rect x="2" y="6" width="20" height="8" rx="1"/><path d="M17 14v7M7 14v7M17 3v3M7 3v3'
                     'M10 14 2.3 6.3M14 6l7.7 7.7M8 6l8 8"/>'),
}

_PLANTILLA = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
              'fill="none" stroke="{color}" stroke-width="{grosor}" stroke-linecap="round" '
              'stroke-linejoin="round">{trazos}</svg>')


def _nombre_color(color) -> str:
    """Acepta QColor o texto ('#0e7490') y regresa '#rrggbb' para el SVG."""
    return QColor(color).name() if not isinstance(color, QColor) else color.name()


def pixmap(nombre: str, color, tam: int = 20, grosor: float = 2) -> QPixmap:
    """Dibuja el ícono en un QPixmap transparente, nítido en pantallas de alta densidad."""
    svg = _PLANTILLA.format(color=_nombre_color(color), grosor=grosor, trazos=TRAZOS[nombre])
    escala = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
    lado = max(1, round(tam * escala))
    imagen = QPixmap(lado, lado)
    imagen.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(pintor, QRectF(0, 0, lado, lado))
    pintor.end()
    imagen.setDevicePixelRatio(escala)
    return imagen


def icono(nombre: str, color, color_activo=None, tam: int = 20) -> QIcon:
    """QIcon con dos versiones: normal y 'activo' (botones marcados, por ejemplo la
    opción seleccionada de la barra lateral, que va en blanco sobre el gel)."""
    resultado = QIcon()
    resultado.addPixmap(pixmap(nombre, color, tam), QIcon.Mode.Normal, QIcon.State.Off)
    resultado.addPixmap(pixmap(nombre, color_activo or color, tam), QIcon.Mode.Normal, QIcon.State.On)
    return resultado
