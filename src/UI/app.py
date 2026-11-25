import sys

from PySide6.QtWidgets import QApplication

from config import TITULO_APP
from UI import iconos, tema
from UI.ventana_principal import VentanaPrincipal


def iniciar(sesiones, servicios, error_inicial: str = None, reconectar=None) -> int:
    """Crea la aplicación Qt, aplica el tema guardado y abre la ventana maximizada.
    Regresa el código de salida de Qt."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(TITULO_APP.title())
    app.setOrganizationName("ITSUR")
    tema.cargar_fuentes()
    tema.gestor.iniciar(app)
    app.setWindowIcon(iconos.icono("libro", "#0e7490", tam=64))

    ventana = VentanaPrincipal(sesiones, servicios, error_inicial, reconectar)
    ventana.showMaximized()
    return app.exec()
