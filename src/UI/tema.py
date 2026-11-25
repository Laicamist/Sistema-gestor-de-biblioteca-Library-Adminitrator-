"""Tema visual de la aplicación: moderno con toques de Frutiger Aero.

- Los colores de cada tema (claro y oscuro) viven en un diccionario de tokens.
- La hoja de estilos de Qt (QSS) se genera a partir de esos tokens, así los dos
  temas comparten las mismas reglas y solo cambian los colores.
- GestorTema aplica el tema a toda la app, recuerda la elección del usuario
  (QSettings) y avisa con una señal para que los widgets redibujen sus íconos.
"""
from pathlib import Path
from string import Template

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase

RECURSOS = Path(__file__).resolve().parent / "recursos"

# Degradado de los botones "gel" (igual en los dos temas): parte superior clara,
# corte a la mitad y parte inferior más oscura, como los botones de Windows 7.
GEL = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4fc6dc, stop:0.48 #1592b1, "
       "stop:0.52 #0b7896, stop:1 #095f79)")
GEL_HOVER = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66d2e6, stop:0.48 #1ba2c2, "
             "stop:0.52 #0d86a6, stop:1 #0a6a87)")
GEL_PRESIONADO = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1592b1, stop:0.48 #0b7896, "
                  "stop:0.52 #09657f, stop:1 #074f63)")
GEL_APAGADO = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b9cdd2, stop:0.48 #93aab1, "
               "stop:0.52 #879fa6, stop:1 #7a939a)")

# Tokens de color. Las transparencias van en el formato rgba(r, g, b, a) de Qt (a de 0 a 255).
TEMAS = {
    "claro": {
        "fondo1": "#ecfbfe", "fondo2": "#c9eef6", "fondo3": "#9edbe9",
        "brillo": (255, 255, 255, 235), "brillo2": (45, 212, 191, 82),
        "vidrio": "rgba(255, 255, 255, 158)", "vidrio_borde": "rgba(255, 255, 255, 235)",
        "solido": "#f4fcfe",
        "texto": "#0b3440", "tenue": "#41656f",
        "acento": "#0e7490", "acento_suave": "rgba(8, 145, 178, 41)",
        "linea": "rgba(14, 116, 144, 46)", "campo": "rgba(255, 255, 255, 219)",
        "ok": "#15803d", "ok_fondo": "#dcfce7",
        "error": "#b91c1c", "error_fondo": "#fee2e2",
        "aviso": "#92400e", "aviso_fondo": "#fef3c7",
        "sombra": (14, 116, 144, 45),
    },
    "oscuro": {
        "fondo1": "#031419", "fondo2": "#062833", "fondo3": "#08394a",
        "brillo": (34, 211, 238, 56), "brillo2": (20, 184, 166, 51),
        "vidrio": "rgba(8, 40, 50, 148)", "vidrio_borde": "rgba(103, 232, 249, 51)",
        "solido": "#0a2a33",
        "texto": "#e7fbff", "tenue": "#9cc7d1",
        "acento": "#67e8f9", "acento_suave": "rgba(103, 232, 249, 41)",
        "linea": "rgba(103, 232, 249, 41)", "campo": "rgba(3, 20, 26, 158)",
        "ok": "#4ade80", "ok_fondo": "rgba(74, 222, 128, 33)",
        "error": "#fca5a5", "error_fondo": "rgba(248, 113, 113, 38)",
        "aviso": "#fcd34d", "aviso_fondo": "rgba(252, 211, 77, 33)",
        "sombra": (0, 0, 0, 110),
    },
}

# Hoja de estilos. Se usa string.Template ($token) porque QSS ya usa llaves { }.
QSS = Template("""
* { font-family: "Inter", "Segoe UI", sans-serif; font-size: 14px; color: $texto; }
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QLabel { background: transparent; }
QLabel[tenue="true"] { color: $tenue; }
QLabel#marca { font-size: 15px; font-weight: 800; }
QLabel#tituloLogin { font-size: 46px; font-weight: 800; }
QLabel#tituloPantalla { font-size: 28px; font-weight: 800; }
QLabel#subtituloPantalla { font-size: 15px; color: $tenue; }
QLabel#seccion { font-size: 17px; font-weight: 700; }
QLabel#dato { font-size: 36px; font-weight: 800; }
QLabel#chip { background: $vidrio; border: 1px solid $vidrio_borde; border-radius: 15px;
    padding: 6px 14px; color: $acento; font-size: 13px; font-weight: 600; }
QLabel#avatar { background: $campo; color: $acento; border-radius: 20px; font-weight: 700; }

QFrame#vidrio { background: $vidrio; border: 1px solid $vidrio_borde; border-radius: 22px; }
QFrame#suave { background: $acento_suave; border: none; border-radius: 14px; }
QFrame#linea { background: $linea; border: none; max-height: 1px; min-height: 1px; }

QLineEdit, QComboBox, QSpinBox, QDateEdit, QPlainTextEdit {
    background: $campo; border: 1px solid $linea; border-radius: 12px; padding: 9px 12px;
    selection-background-color: $acento; selection-color: #ffffff; min-height: 24px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QPlainTextEdit:focus {
    border: 2px solid $acento; padding: 8px 11px; }
QLineEdit#lector { font-size: 22px; font-weight: 600; padding: 14px 18px; border: 2px solid $acento;
    border-radius: 16px; min-height: 32px; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView { background: $solido; border: 1px solid $linea; border-radius: 8px;
    selection-background-color: $acento; selection-color: #ffffff; padding: 4px; }

QPushButton { background: transparent; border: 1px solid $linea; border-radius: 12px;
    padding: 9px 18px; font-weight: 600; }
QPushButton:hover { background: $acento_suave; }
QPushButton:disabled { color: $tenue; }
QPushButton#gel { background: $gel; border: 1px solid #095f79; border-radius: 14px; color: #ffffff;
    padding: 11px 24px; font-size: 15px; font-weight: 700; }
QPushButton#gel:hover { background: $gel_hover; }
QPushButton#gel:pressed { background: $gel_presionado; }
QPushButton#gel:disabled { background: $gel_apagado; border-color: #7a939a; color: rgba(255, 255, 255, 200); }
QPushButton#pastilla { background: $vidrio; border: 1px solid $vidrio_borde; border-radius: 20px;
    padding: 9px 16px; font-weight: 500; }
QPushButton#pastilla:hover { background: $acento_suave; }
QPushButton#enlace { border: none; background: transparent; color: $acento; padding: 6px 8px; }
QPushButton#enlace:hover { color: $texto; }
QPushButton#nav { text-align: left; border: 1px solid transparent; border-radius: 12px;
    padding: 10px 14px; font-size: 15px; font-weight: 500; }
QPushButton#nav:hover { background: $acento_suave; }
QPushButton#nav:checked { background: $gel; border: 1px solid #095f79; color: #ffffff; font-weight: 600; }
QPushButton#segmento { border: 1px solid transparent; border-radius: 12px; padding: 10px 16px; }
QPushButton#segmento:hover { background: $acento_suave; }
QPushButton#segmento:checked { background: $gel; border: 1px solid #095f79; color: #ffffff; }

QFrame#aviso[tipo="ok"] { background: $ok_fondo; border-radius: 14px; }
QFrame#aviso[tipo="error"] { background: $error_fondo; border-radius: 14px; }
QFrame#aviso[tipo="advertencia"] { background: $aviso_fondo; border-radius: 14px; }
QFrame#aviso[tipo="info"] { background: $acento_suave; border-radius: 14px; }
QLabel#avisoTexto[tipo="ok"] { color: $ok; font-weight: 600; }
QLabel#avisoTexto[tipo="error"] { color: $error; font-weight: 600; }
QLabel#avisoTexto[tipo="advertencia"] { color: $aviso; font-weight: 600; }
QLabel#avisoTexto[tipo="info"] { color: $texto; font-weight: 500; }
QLabel#insignia { border-radius: 10px; padding: 3px 10px; font-size: 12px; font-weight: 700; }
QLabel#insignia[tipo="ok"] { background: $ok_fondo; color: $ok; }
QLabel#insignia[tipo="error"] { background: $error_fondo; color: $error; }
QLabel#insignia[tipo="advertencia"] { background: $aviso_fondo; color: $aviso; }
QLabel#insignia[tipo="info"] { background: $acento_suave; color: $acento; }

QTableWidget, QTableView { background: transparent; border: none; gridline-color: transparent;
    selection-background-color: $acento_suave; selection-color: $texto; outline: none; }
QTableView::item { padding: 6px 10px; border-bottom: 1px solid $linea; }
QHeaderView::section { background: transparent; color: $tenue; border: none; border-bottom: 1px solid $linea;
    padding: 8px 10px; font-size: 12px; font-weight: 600; }
QTableCornerButton::section { background: transparent; border: none; }

QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; border: 1px solid transparent; border-radius: 12px;
    padding: 9px 16px; margin-right: 6px; font-weight: 600; }
QTabBar::tab:hover { background: $acento_suave; }
QTabBar::tab:selected { background: $gel; border: 1px solid #095f79; color: #ffffff; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $linea; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:horizontal { background: $linea; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QDialog, QMessageBox { background: $solido; }
QToolTip { background: $solido; color: $texto; border: 1px solid $linea; padding: 6px 8px; }
QCheckBox { spacing: 8px; }
""")


def colores(nombre: str = None) -> dict:
    """Tokens del tema indicado (o del tema actual)."""
    return TEMAS[nombre or gestor.actual]


def color(token: str, nombre: str = None) -> QColor:
    """Un token como QColor, para pintar con QPainter o colorear íconos."""
    valor = colores(nombre)[token]
    if isinstance(valor, tuple):
        return QColor(*valor)
    if valor.startswith("rgba"):
        r, g, b, a = (int(x) for x in valor[valor.index("(") + 1:-1].split(","))
        return QColor(r, g, b, a)
    return QColor(valor)


def hoja_de_estilos(nombre: str) -> str:
    tokens = {k: v for k, v in TEMAS[nombre].items() if isinstance(v, str)}
    return QSS.substitute(tokens, gel=GEL, gel_hover=GEL_HOVER,
                          gel_presionado=GEL_PRESIONADO, gel_apagado=GEL_APAGADO)


def cargar_fuentes() -> bool:
    """Registra Inter (recursos/fuentes). Si no está, Qt usa Segoe UI."""
    cargadas = 0
    for archivo in sorted((RECURSOS / "fuentes").glob("*.otf")):
        if QFontDatabase.addApplicationFont(str(archivo)) != -1:
            cargadas += 1
    return cargadas > 0


class GestorTema(QObject):
    """Tema actual de la app. Emite `cambiado` para que los widgets redibujen íconos y fondo."""

    cambiado = Signal(str)

    def __init__(self):
        super().__init__()
        self.actual = "claro"
        self._app = None
        self._ajustes = None

    def iniciar(self, app):
        """Aplica el tema que el usuario eligió la última vez (o el claro)."""
        self._app = app
        self._ajustes = QSettings("ITSUR", "LibraryAdministrator")
        guardado = self._ajustes.value("tema", "claro")
        app.setFont(QFont("Inter", 10))
        self.aplicar(guardado if guardado in TEMAS else "claro")

    def aplicar(self, nombre: str):
        self.actual = nombre
        if self._app is not None:
            self._app.setStyleSheet(hoja_de_estilos(nombre))
        if self._ajustes is not None:
            self._ajustes.setValue("tema", nombre)
        self.cambiado.emit(nombre)

    def alternar(self):
        self.aplicar("oscuro" if self.actual == "claro" else "claro")

    def etiqueta_boton(self) -> str:
        """Texto del botón que cambia de tema."""
        return "Tema oscuro" if self.actual == "claro" else "Tema claro"


gestor = GestorTema()
