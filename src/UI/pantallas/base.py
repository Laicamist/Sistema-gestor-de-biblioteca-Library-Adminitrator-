from PySide6.QtWidgets import QWidget

from Modelos import BibliotecaError, SinConexionError


class Pantalla(QWidget):
    """Base de las pantallas que viven dentro de la ventana principal.

    Cada pantalla recibe la ventana, y con ella la sesión (`sesiones`), los
    servicios (`servicios`), los avisos (`avisar`) y los sonidos del lector.
    """

    def __init__(self, ventana, parent=None):
        super().__init__(parent)
        self.ventana = ventana
        self.sesiones = ventana.sesiones
        self.servicios = ventana.servicios

    def al_mostrar(self):
        """Se llama cada vez que el usuario abre la pantalla (para recargar datos)."""

    def avisar(self, texto: str, tipo: str = "info", duracion_ms: int = 6000):
        self.ventana.avisar(texto, tipo, duracion_ms)

    def ejecutar(self, funcion, *args, exito: str = None, **kwargs):
        """Llama a un servicio y convierte cualquier error en un aviso rojo.

        Regresa (True, resultado) o (False, None). Los mensajes de los triggers
        (SIGNAL SQLSTATE '45000') llegan aquí ya traducidos por el DAO.
        """
        try:
            resultado = funcion(*args, **kwargs)
        except (BibliotecaError, SinConexionError) as error:
            self.avisar(str(error), "error", 8000)
            return False, None
        except Exception as error:  # noqa: BLE001 - nunca cerrar la app por un error inesperado
            self.avisar(f"Ocurrió un error inesperado: {error}", "error", 0)
            return False, None
        if exito:
            self.avisar(exito, "ok")
        return True, resultado
