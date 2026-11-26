from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from Modelos import BibliotecaError, SinConexionError
from UI import iconos, tema
from UI.componentes import Aviso, BotonIcono, LogoGel, PanelVidrio, boton_gel, etiqueta


class PantallaLogin(QWidget):
    """Inicio de sesión: valida con SP_LOGIN (la contraseña viaja como hash SHA-256)
    y, si todo sale bien, la ventana se reconecta con el usuario de MySQL del rol."""

    def __init__(self, ventana, error_inicial: str = None, parent=None):
        super().__init__(parent)
        self.ventana = ventana
        self._mostrar_contrasena = False

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(40, 28, 40, 24)

        barra = QHBoxLayout()
        barra.addStretch(1)
        self.boton_tema = BotonIcono(tema.gestor.etiqueta_boton(), "luna", "pastilla")
        self.boton_tema.clicked.connect(tema.gestor.alternar)
        barra.addWidget(self.boton_tema)
        raiz.addLayout(barra)

        centro = QHBoxLayout()
        centro.setSpacing(72)
        centro.addStretch(1)
        centro.addLayout(self._crear_marca())
        centro.addWidget(self._crear_tarjeta(), 0, Qt.AlignmentFlag.AlignVCenter)
        centro.addStretch(1)
        raiz.addStretch(1)
        raiz.addLayout(centro)
        raiz.addStretch(1)

        pie = etiqueta("Taller de Bases de Datos", tenue=True)
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        raiz.addWidget(pie)

        self._al_cambiar_tema(tema.gestor.actual)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)
        if error_inicial:
            self._mostrar_sin_conexion(error_inicial)

    # Construcción

    def _crear_marca(self) -> QVBoxLayout:
        marca = QVBoxLayout()
        marca.setSpacing(20)
        marca.addStretch(1)
        marca.addWidget(LogoGel(76))
        marca.addWidget(etiqueta("Library\nAdministrator", "tituloLogin"))
        descripcion = etiqueta("Sistema de administración de la biblioteca, encuentra el libro que buscas facilmente, "
                               "contamos con sistema de prestamos para continuar la magia de la lectura en casa", 
                               tenue=True, ajustar=True)
        descripcion.setMaximumWidth(460)
        descripcion.setStyleSheet("font-size: 17px;")
        marca.addWidget(descripcion)
        chips = QHBoxLayout()
        chips.setSpacing(10)
        for texto in ("Funciones integrales:","Lector de código de barras", "Préstamos en tiempo real", "Auditoría de cambios"):
            chips.addWidget(etiqueta(texto, "chip"))
        chips.addStretch(1)
        marca.addLayout(chips)
        marca.addStretch(1)
        return marca

    def _crear_tarjeta(self) -> PanelVidrio:
        tarjeta = PanelVidrio(sombra=True)
        tarjeta.setFixedWidth(420)
        caja = QVBoxLayout(tarjeta)
        caja.setContentsMargins(40, 36, 40, 32)
        caja.setSpacing(10)

        caja.addWidget(etiqueta("Iniciar sesión", "tituloPantalla"))
        caja.addWidget(etiqueta("Usa tu usuario de la biblioteca.", tenue=True))
        caja.addSpacing(10)

        caja.addWidget(etiqueta("Usuario"))
        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Tu usuario")
        self.usuario.setMaxLength(30)
        self._accion_usuario = self.usuario.addAction(
            iconos.icono("usuario", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        caja.addWidget(self.usuario)
        caja.addSpacing(6)

        caja.addWidget(etiqueta("Contraseña"))
        self.contrasena = QLineEdit()
        self.contrasena.setEchoMode(QLineEdit.EchoMode.Password)
        self.contrasena.setPlaceholderText("Tu contraseña")
        self._accion_candado = self.contrasena.addAction(
            iconos.icono("candado", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self._accion_ver = self.contrasena.addAction(
            iconos.icono("ojo", tema.color("tenue")), QLineEdit.ActionPosition.TrailingPosition)
        self._accion_ver.setToolTip("Mostrar u ocultar la contraseña")
        self._accion_ver.triggered.connect(self._alternar_contrasena)
        caja.addWidget(self.contrasena)
        caja.addSpacing(8)

        self.aviso = Aviso()
        caja.addWidget(self.aviso)

        self.boton_entrar = boton_gel("Entrar")
        self.boton_entrar.setDefault(True)
        self.boton_entrar.clicked.connect(self._entrar)
        caja.addWidget(self.boton_entrar)

        self.boton_reintentar = BotonIcono("Reintentar conexión", "actualizar", "enlace", token="acento", tam=16)
        self.boton_reintentar.clicked.connect(self._reintentar)
        self.boton_reintentar.hide()
        caja.addWidget(self.boton_reintentar, 0, Qt.AlignmentFlag.AlignHCenter)

        self.usuario.returnPressed.connect(self.contrasena.setFocus)
        self.contrasena.returnPressed.connect(self._entrar)
        return tarjeta

    # Acciones

    def _entrar(self):
        if self.ventana.sesiones.dao is None:
            self._mostrar_sin_conexion("Sin conexión a la base de datos.")
            return
        self.boton_entrar.setEnabled(False)
        self.boton_entrar.setText("Verificando…")
        QApplication.processEvents()
        try:
            sesion = self.ventana.sesiones.iniciar_sesion(self.usuario.text(), self.contrasena.text())
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            self.contrasena.selectAll()
            self.contrasena.setFocus()
        except Exception as error:  # noqa: BLE001
            self.aviso.mostrar(f"No se pudo iniciar sesión: {error}", "error", 0)
        else:
            self.contrasena.clear()
            self.aviso.ocultar()
            self.ventana.entrar(sesion)
        finally:
            self.boton_entrar.setEnabled(True)
            self.boton_entrar.setText("Entrar")

    def _reintentar(self):
        error = self.ventana.reconectar_bd()
        if error:
            self._mostrar_sin_conexion(error)
        else:
            self.boton_reintentar.hide()
            self.aviso.mostrar("Conexión con la base de datos establecida.", "ok")

    def _mostrar_sin_conexion(self, texto: str):
        self.aviso.mostrar(texto, "error", 0)
        self.boton_reintentar.setVisible(self.ventana.puede_reconectar)

    def _alternar_contrasena(self):
        self._mostrar_contrasena = not self._mostrar_contrasena
        self.contrasena.setEchoMode(QLineEdit.EchoMode.Normal if self._mostrar_contrasena
                                    else QLineEdit.EchoMode.Password)
        self._al_cambiar_tema(tema.gestor.actual)

    def limpiar(self):
        """Al cerrar sesión: deja el formulario listo para el siguiente usuario."""
        self.contrasena.clear()
        self.aviso.ocultar()
        self.usuario.setFocus()
        self.usuario.selectAll()

    def _al_cambiar_tema(self, _nombre):
        tenue = tema.color("tenue")
        self.boton_tema.setText(tema.gestor.etiqueta_boton())
        self.boton_tema.cambiar_icono("luna" if tema.gestor.actual == "claro" else "sol")
        self._accion_usuario.setIcon(iconos.icono("usuario", tenue))
        self._accion_candado.setIcon(iconos.icono("candado", tenue))
        self._accion_ver.setIcon(iconos.icono("ojo_cerrado" if self._mostrar_contrasena else "ojo", tenue))

    def showEvent(self, evento):
        super().showEvent(evento)
        self.usuario.setFocus()
