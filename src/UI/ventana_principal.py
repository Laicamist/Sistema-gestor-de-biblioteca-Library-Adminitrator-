from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget,
)

from config import ADMINISTRACION, ALUMNOS, CATALOGO, CONSULTAR, REPORTES, TITULO_APP
from UI import tema
from UI.componentes import (
    Aviso, BotonIcono, FondoAero, LogoGel, PanelVidrio, Sonidos, etiqueta, fundido,
)
from UI.pantallas.alumnos import PantallaAlumnos
from UI.pantallas.catalogo import PantallaCatalogo
from UI.pantallas.inicio import PantallaInicio
from UI.pantallas.lector import PantallaLector
from UI.pantallas.login import PantallaLogin
from UI.pantallas.pendiente import PantallaPendiente


@dataclass(frozen=True)
class Modulo:
    clave: str
    texto: str
    icono: str
    permiso: str        # permiso de config.PERMISOS que necesita el rol para verlo
    subtitulo: str
    parte: int          # parte de la interfaz en la que se construye la pantalla


# Orden de la barra lateral. Solo aparecen los módulos que el rol tiene permitidos.
MODULOS = (
    Modulo("inicio", "Inicio", "inicio", CONSULTAR, "Así está la biblioteca hoy.", 3),
    Modulo("lector", "Lector", "lector", CONSULTAR,
           "Escanea una etiqueta: el lector manda el código y un Enter.", 4),
    Modulo("catalogo", "Catálogo", "libro", CATALOGO, "Libros, ejemplares y categorías.", 5),
    Modulo("alumnos", "Alumnos", "alumnos", ALUMNOS, "Alta, cambios e historial de préstamos.", 6),
    Modulo("reportes", "Reportes", "reportes", REPORTES, "Consultas para la toma de decisiones.", 7),
    Modulo("auditoria", "Auditoría", "auditoria", ADMINISTRACION,
           "Bitácora de cambios que registran los triggers.", 7),
    Modulo("usuarios", "Usuarios", "usuarios", ADMINISTRACION, "Cuentas del sistema y sus roles.", 8),
)

# Clase de cada pantalla ya construida (clave -> clase). Cada parte de la interfaz
# agrega aquí su pantalla; las que falten se muestran como "en construcción".
PANTALLAS = {
    "inicio": PantallaInicio,
    "lector": PantallaLector,
    "catalogo": PantallaCatalogo,
    "alumnos": PantallaAlumnos,
}


class BarraLateral(PanelVidrio):
    """Panel de vidrio a la izquierda: marca, módulos del rol, usuario y cierre de sesión."""

    def __init__(self, ventana, modulos, sesion, parent=None):
        super().__init__(parent, sombra=True)
        self.setFixedWidth(252)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(14, 20, 14, 16)
        caja.setSpacing(4)

        marca = QHBoxLayout()
        marca.setContentsMargins(6, 0, 0, 0)
        marca.setSpacing(12)
        marca.addWidget(LogoGel(42))
        marca.addWidget(etiqueta("Library\nAdministrator", "marca"))
        marca.addStretch(1)
        caja.addLayout(marca)
        caja.addSpacing(18)

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botones = {}
        for modulo in modulos:
            boton = BotonIcono(modulo.texto, modulo.icono, "nav")
            boton.setCheckable(True)
            boton.setMinimumHeight(44)
            boton.clicked.connect(lambda _marcado=False, clave=modulo.clave: ventana.mostrar(clave))
            self.grupo.addButton(boton)
            self.botones[modulo.clave] = boton
            caja.addWidget(boton)
        caja.addStretch(1)

        tarjeta = QFrame()
        tarjeta.setObjectName("suave")
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(12, 12, 12, 12)
        fila.setSpacing(12)
        avatar = etiqueta(sesion.nombre_usuario[:2].upper(), "avatar")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fila.addWidget(avatar)
        datos = QVBoxLayout()
        datos.setSpacing(0)
        datos.addWidget(etiqueta(sesion.nombre_usuario))
        rol = etiqueta(sesion.rol.capitalize(), tenue=True)
        rol.setStyleSheet("font-size: 12px;")
        datos.addWidget(rol)
        fila.addLayout(datos, 1)
        caja.addWidget(tarjeta)

        salir = BotonIcono("Cerrar sesión", "salir", "nav", token="tenue")
        salir.setMinimumHeight(44)
        salir.clicked.connect(ventana.salir)
        caja.addWidget(salir)

    def marcar(self, clave: str):
        if clave in self.botones:
            self.botones[clave].setChecked(True)


class Escritorio(QWidget):
    """Lo que se ve después del login: barra lateral + encabezado + aviso + pantallas."""

    def __init__(self, ventana, modulos, sesion, parent=None):
        super().__init__(parent)
        self.ventana = ventana
        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 16, 16, 16)
        fila.setSpacing(20)
        self.barra = BarraLateral(ventana, modulos, sesion)
        fila.addWidget(self.barra)

        contenido = QVBoxLayout()
        contenido.setContentsMargins(4, 8, 8, 4)
        contenido.setSpacing(16)
        encabezado = QHBoxLayout()
        encabezado.setSpacing(10)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.titulo = etiqueta("", "tituloPantalla")
        self.subtitulo = etiqueta("", "subtituloPantalla")
        textos.addWidget(self.titulo)
        textos.addWidget(self.subtitulo)
        encabezado.addLayout(textos, 1)
        self.boton_sonido = BotonIcono("", "sonido", "pastilla", token="acento")
        self.boton_sonido.clicked.connect(self._alternar_sonido)
        encabezado.addWidget(self.boton_sonido, 0, Qt.AlignmentFlag.AlignTop)
        self.boton_tema = BotonIcono(tema.gestor.etiqueta_boton(), "luna", "pastilla")
        self.boton_tema.clicked.connect(tema.gestor.alternar)
        encabezado.addWidget(self.boton_tema, 0, Qt.AlignmentFlag.AlignTop)
        contenido.addLayout(encabezado)

        self.aviso = Aviso()
        contenido.addWidget(self.aviso)
        self.paginas = QStackedWidget()
        contenido.addWidget(self.paginas, 1)
        fila.addLayout(contenido, 1)

        self._actualizar_sonido()
        self._al_cambiar_tema(tema.gestor.actual)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    def _alternar_sonido(self):
        self.ventana.sonidos.alternar()
        self._actualizar_sonido()

    def _actualizar_sonido(self):
        activo = self.ventana.sonidos.activo
        self.boton_sonido.setText("Sonido activado" if activo else "Sonido apagado")
        self.boton_sonido.cambiar_icono("sonido" if activo else "silencio")

    def _al_cambiar_tema(self, _nombre):
        self.boton_tema.setText(tema.gestor.etiqueta_boton())
        self.boton_tema.cambiar_icono("luna" if tema.gestor.actual == "claro" else "sol")


class VentanaPrincipal(QMainWindow):
    """Única ventana de la aplicación. Alterna entre el login y el escritorio del rol."""

    def __init__(self, sesiones, servicios, error_inicial: str = None, reconectar=None):
        super().__init__()
        self.sesiones = sesiones
        self.servicios = servicios
        self._reconectar = reconectar
        self.sonidos = Sonidos(self)
        self.escritorio = None
        self._modulos = {}
        self._paginas = {}

        self.setWindowTitle(TITULO_APP.title())
        self.setMinimumSize(1100, 700)
        fondo = FondoAero()
        self.setCentralWidget(fondo)
        capa = QVBoxLayout(fondo)
        capa.setContentsMargins(0, 0, 0, 0)
        self.raiz = QStackedWidget()
        capa.addWidget(self.raiz)

        self.login = PantallaLogin(self, error_inicial)
        self.raiz.addWidget(self.login)

    # Conexión

    @property
    def puede_reconectar(self) -> bool:
        return self._reconectar is not None

    def reconectar_bd(self):
        """Intenta otra vez la conexión con MySQL. Regresa None si funcionó o el texto del error."""
        if self._reconectar is None:
            return "No hay forma de reintentar la conexión desde aquí; reinicia la aplicación."
        return self._reconectar()

    # Sesión

    def entrar(self, sesion):
        """Arma el escritorio con los módulos del rol y abre el primero."""
        self._quitar_escritorio()
        permitidos = [m for m in MODULOS if self.sesiones.puede(m.permiso)]
        self._modulos = {m.clave: m for m in permitidos}
        self.escritorio = Escritorio(self, permitidos, sesion)
        self.raiz.addWidget(self.escritorio)
        self.raiz.setCurrentWidget(self.escritorio)
        fundido(self.escritorio, 280)
        if permitidos:
            self.mostrar(permitidos[0].clave)

    def salir(self):
        """Cierra la sesión: la conexión vuelve al usuario de MySQL de login."""
        try:
            self.sesiones.cerrar_sesion()
        except Exception as error:  # noqa: BLE001 - aunque falle la reconexión, se sale
            self.login.aviso.mostrar(f"Sesión cerrada, pero no se pudo reconectar: {error}", "advertencia", 0)
        self._quitar_escritorio()
        self.raiz.setCurrentWidget(self.login)
        self.login.limpiar()
        fundido(self.login, 280)

    def _quitar_escritorio(self):
        if self.escritorio is not None:
            self.raiz.removeWidget(self.escritorio)
            self.escritorio.deleteLater()
            self.escritorio = None
        self._paginas = {}
        self._modulos = {}

    # Navegación

    def mostrar(self, clave: str, **opciones):
        """Abre un módulo. Cada pantalla se crea la primera vez que se abre y luego se reutiliza.
        Las `opciones` se pasan a `al_mostrar` (por ejemplo, el modo inicial del lector)."""
        if self.escritorio is None or clave not in self._modulos:
            return
        modulo = self._modulos[clave]
        pagina = self._paginas.get(clave)
        if pagina is None:
            clase = PANTALLAS.get(clave)
            pagina = clase(self) if clase is not None else PantallaPendiente(self, modulo)
            self.escritorio.paginas.addWidget(pagina)
            self._paginas[clave] = pagina
        self.escritorio.titulo.setText(modulo.texto)
        self.escritorio.subtitulo.setText(modulo.subtitulo)
        self.escritorio.barra.marcar(clave)
        self.escritorio.aviso.ocultar()
        self.escritorio.paginas.setCurrentWidget(pagina)
        fundido(pagina)
        try:
            pagina.al_mostrar(**opciones)
        except Exception as error:  # noqa: BLE001
            self.avisar(f"No se pudo cargar {modulo.texto}: {error}", "error", 0)

    def avisar(self, texto: str, tipo: str = "info", duracion_ms: int = 6000):
        """Aviso general debajo del encabezado (verde, rojo, ámbar o informativo)."""
        if self.escritorio is not None:
            self.escritorio.aviso.mostrar(texto, tipo, duracion_ms)
