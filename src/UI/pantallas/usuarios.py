from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QLineEdit, QVBoxLayout

from config import DESCRIPCION_PERMISOS, PERMISOS
from Logic.seguridad import MIN_CONTRASENA
from Modelos import BibliotecaError, SinConexionError
from UI import iconos, tema
from UI.componentes import (
    Aviso, BotonIcono, Dato, Insignia, PanelVidrio, Tabla, boton_gel, celda_insignia, confirmar, etiqueta,
)
from UI.pantallas.base import Pantalla

FILTROS_ESTADO = (("Todos los estados", None), ("Activos", "ACTIVO"), ("Inactivos", "INACTIVO"))
TIPO_ROL = {"ADMINISTRADOR": "error", "BIBLIOTECARIO": "info", "CONSULTA": "ok"}
REGLA = f"Al menos {MIN_CONTRASENA} caracteres, combinando letras y números."


class CampoContrasena(QLineEdit):
    """Campo de contraseña con el botón del ojo para mostrarla u ocultarla."""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setMaxLength(64)
        self.setPlaceholderText(placeholder)
        self._visible = False
        self._accion = self.addAction(iconos.icono("ojo", tema.color("tenue")),
                                      QLineEdit.ActionPosition.TrailingPosition)
        self._accion.setToolTip("Mostrar u ocultar la contraseña")
        self._accion.triggered.connect(self._alternar)
        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    def _alternar(self):
        self._visible = not self._visible
        self.setEchoMode(QLineEdit.EchoMode.Normal if self._visible else QLineEdit.EchoMode.Password)
        self._al_cambiar_tema(tema.gestor.actual)

    def _al_cambiar_tema(self, _nombre):
        self._accion.setIcon(iconos.icono("ojo_cerrado" if self._visible else "ojo", tema.color("tenue")))


class DialogoUsuario(QDialog):
    """Alta de una cuenta del personal. La contraseña se convierte a SHA-256 en la app
    (Logic/seguridad.py) y solo el hash llega a MySQL."""

    def __init__(self, ventana, roles, parent=None):
        super().__init__(parent or ventana)
        self.servicio = ventana.servicios["usuarios"]
        self.usuario = None
        self.setWindowTitle("Nuevo usuario")
        self.setModal(True)
        self.setMinimumWidth(540)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(28, 24, 28, 24)
        caja.setSpacing(12)
        caja.addWidget(etiqueta("Nuevo usuario", "seccion"))

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(14)
        rejilla.setVerticalSpacing(6)
        self.nombre = QLineEdit()
        self.nombre.setMaxLength(100)
        self.nombre.setPlaceholderText("Nombre y apellidos")
        self.nombre_usuario = QLineEdit()
        self.nombre_usuario.setMaxLength(30)
        self.nombre_usuario.setPlaceholderText("Sin espacios, por ejemplo JPEREZ")
        self.rol = QComboBox()
        for rol in roles:
            self.rol.addItem(rol.nombre_rol, rol.id_rol)
        self.contrasena = CampoContrasena("Contraseña")
        self.confirmacion = CampoContrasena("Repite la contraseña")

        rejilla.addWidget(etiqueta("Nombre completo"), 0, 0, 1, 2)
        rejilla.addWidget(self.nombre, 1, 0, 1, 2)
        rejilla.addWidget(etiqueta("Nombre de usuario"), 2, 0)
        rejilla.addWidget(etiqueta("Rol"), 2, 1)
        rejilla.addWidget(self.nombre_usuario, 3, 0)
        rejilla.addWidget(self.rol, 3, 1)
        rejilla.addWidget(etiqueta("Contraseña"), 4, 0)
        rejilla.addWidget(etiqueta("Confirmar contraseña"), 4, 1)
        rejilla.addWidget(self.contrasena, 5, 0)
        rejilla.addWidget(self.confirmacion, 5, 1)
        caja.addLayout(rejilla)
        regla = etiqueta(REGLA, tenue=True, ajustar=True)
        regla.setStyleSheet("font-size: 12px;")
        caja.addWidget(regla)

        self.aviso = Aviso()
        caja.addWidget(self.aviso)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = BotonIcono("Cancelar")
        cancelar.setAutoDefault(False)
        cancelar.clicked.connect(self.reject)
        crear = boton_gel("Crear usuario", "agregar")
        crear.setAutoDefault(False)
        crear.clicked.connect(self._guardar)
        botones.addWidget(cancelar)
        botones.addWidget(crear)
        caja.addLayout(botones)

        self.nombre.returnPressed.connect(self.nombre_usuario.setFocus)
        self.nombre_usuario.returnPressed.connect(self.contrasena.setFocus)
        self.contrasena.returnPressed.connect(self.confirmacion.setFocus)
        self.confirmacion.returnPressed.connect(self._guardar)
        self.nombre.setFocus()

    def _guardar(self):
        if self.contrasena.text() != self.confirmacion.text():
            self.aviso.mostrar("Las contraseñas no coinciden.", "error", 0)
            self.confirmacion.selectAll()
            self.confirmacion.setFocus()
            return
        try:
            self.usuario = self.servicio.crear(self.nombre.text(), self.nombre_usuario.text(),
                                               self.contrasena.text(), self.rol.currentData())
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            return
        except Exception as error:  # noqa: BLE001
            self.aviso.mostrar(f"No se pudo crear el usuario: {error}", "error", 0)
            return
        self.accept()


class DialogoContrasena(QDialog):
    """El administrador asigna una contraseña nueva (no puede ver la anterior: solo existe el hash)."""

    def __init__(self, ventana, usuario, parent=None):
        super().__init__(parent or ventana)
        self.servicio = ventana.servicios["usuarios"]
        self.usuario = usuario
        self.cambiada = False
        self.setWindowTitle("Restablecer contraseña")
        self.setModal(True)
        self.setMinimumWidth(460)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(28, 24, 28, 24)
        caja.setSpacing(10)
        caja.addWidget(etiqueta("Restablecer contraseña", "seccion"))
        caja.addWidget(etiqueta(f"Cuenta: {usuario.nombre_usuario} · {usuario.nombre_completo}", tenue=True,
                                ajustar=True))
        self.nueva = CampoContrasena("Contraseña nueva")
        self.confirmacion = CampoContrasena("Repite la contraseña nueva")
        caja.addWidget(self.nueva)
        caja.addWidget(self.confirmacion)
        regla = etiqueta(REGLA, tenue=True, ajustar=True)
        regla.setStyleSheet("font-size: 12px;")
        caja.addWidget(regla)
        self.aviso = Aviso()
        caja.addWidget(self.aviso)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = BotonIcono("Cancelar")
        cancelar.setAutoDefault(False)
        cancelar.clicked.connect(self.reject)
        guardar = boton_gel("Guardar contraseña", "candado")
        guardar.setAutoDefault(False)
        guardar.clicked.connect(self._guardar)
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        caja.addLayout(botones)
        self.nueva.returnPressed.connect(self.confirmacion.setFocus)
        self.confirmacion.returnPressed.connect(self._guardar)
        self.nueva.setFocus()

    def _guardar(self):
        if self.nueva.text() != self.confirmacion.text():
            self.aviso.mostrar("Las contraseñas no coinciden.", "error", 0)
            return
        try:
            self.servicio.restablecer_contrasena(self.usuario.id_usuario, self.nueva.text())
        except (BibliotecaError, SinConexionError) as error:
            self.aviso.mostrar(str(error), "error", 0)
            return
        self.cambiada = True
        self.accept()


class PantallaUsuarios(Pantalla):
    """Cuentas del personal (solo administrador): alta, rol, activar o desactivar y contraseña.
    Los cambios los registra TRG_AUD_USUARIOS_AI / TRG_AUD_USUARIOS_AU sin guardar el hash."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        self._usuarios = []
        self._roles = []
        self._id_elegido = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 10, 10)
        raiz.setSpacing(16)

        barra = QHBoxLayout()
        barra.setSpacing(10)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar por nombre o usuario")
        self.buscar.setClearButtonEnabled(True)
        self._accion_buscar = self.buscar.addAction(
            iconos.icono("buscar", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self.buscar.textChanged.connect(self._filtrar)
        barra.addWidget(self.buscar, 3)
        self.filtro_rol = QComboBox()
        self.filtro_rol.setMinimumWidth(200)
        self.filtro_rol.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_rol, 1)
        self.filtro_estado = QComboBox()
        for texto, valor in FILTROS_ESTADO:
            self.filtro_estado.addItem(texto, valor)
        self.filtro_estado.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_estado)
        nuevo = boton_gel("Nuevo usuario", "agregar")
        nuevo.clicked.connect(self._nuevo)
        barra.addWidget(nuevo)
        raiz.addLayout(barra)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._crear_panel_lista(), 3)
        cuerpo.addWidget(self._crear_panel_ficha(), 2)
        raiz.addLayout(cuerpo, 1)

        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    # Construcción

    def _crear_panel_lista(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("Usuarios del sistema", "seccion"))
        self.total = etiqueta("", tenue=True)
        cabecera.addWidget(self.total)
        cabecera.addStretch(1)
        caja.addLayout(cabecera)
        self.tabla = Tabla(["Usuario", "Nombre completo", "Rol", "Estado"])
        cabecera_tabla = self.tabla.horizontalHeader()
        for columna in (0, 2, 3):
            cabecera_tabla.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.itemSelectionChanged.connect(self._al_seleccionar)
        caja.addWidget(self.tabla, 1)
        nota = etiqueta("Las contraseñas se guardan como hash SHA-256: nadie puede verlas, ni el administrador.",
                        tenue=True, ajustar=True)
        nota.setStyleSheet("font-size: 12px;")
        caja.addWidget(nota)
        return panel

    def _crear_panel_ficha(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        self.nombre = etiqueta("Selecciona un usuario", "seccion", ajustar=True)
        cabecera.addWidget(self.nombre, 1)
        self.insignia_estado = Insignia("", "ok")
        self.insignia_estado.hide()
        cabecera.addWidget(self.insignia_estado, 0, Qt.AlignmentFlag.AlignTop)
        caja.addLayout(cabecera)
        self.detalle = etiqueta("Verás su rol, lo que puede hacer y las acciones sobre su cuenta.",
                                tenue=True, ajustar=True)
        caja.addWidget(self.detalle)

        self.d_permisos = Dato("Lo que puede hacer en la app")
        caja.addWidget(self.d_permisos)

        caja.addWidget(etiqueta("Rol", "seccion"))
        fila_rol = QHBoxLayout()
        self.rol_nuevo = QComboBox()
        self.rol_nuevo.currentIndexChanged.connect(self._revisar_rol)
        fila_rol.addWidget(self.rol_nuevo, 1)
        self.boton_rol = BotonIcono("Cambiar rol", "usuarios", tam=18)
        self.boton_rol.clicked.connect(self._cambiar_rol)
        fila_rol.addWidget(self.boton_rol)
        caja.addLayout(fila_rol)

        caja.addWidget(etiqueta("Cuenta", "seccion"))
        acciones = QHBoxLayout()
        self.boton_estado = BotonIcono("Desactivar", "candado", token="error", tam=18)
        self.boton_estado.clicked.connect(self._cambiar_estado)
        self.boton_contrasena = BotonIcono("Restablecer contraseña", "candado", tam=18)
        self.boton_contrasena.clicked.connect(self._restablecer)
        acciones.addWidget(self.boton_estado)
        acciones.addWidget(self.boton_contrasena)
        acciones.addStretch(1)
        caja.addLayout(acciones)
        self.nota_propia = etiqueta("Es tu cuenta: no puedes cambiar tu propio rol ni desactivarte "
                                    "(así nunca se queda el sistema sin administrador).", tenue=True, ajustar=True)
        self.nota_propia.setStyleSheet("font-size: 12px;")
        self.nota_propia.hide()
        caja.addWidget(self.nota_propia)
        caja.addStretch(1)
        self._limpiar_ficha()
        return panel

    # Datos

    def al_mostrar(self, **opciones):
        self._cargar()

    def _cargar(self):
        servicio = self.servicios["usuarios"]
        ok, roles = self.ejecutar(servicio.listar_roles)
        if ok:
            self._roles = roles
            elegido = self.filtro_rol.currentData()
            self.filtro_rol.blockSignals(True)
            self.filtro_rol.clear()
            self.filtro_rol.addItem("Todos los roles", None)
            for rol in roles:
                self.filtro_rol.addItem(rol.nombre_rol, rol.id_rol)
            self.filtro_rol.setCurrentIndex(max(self.filtro_rol.findData(elegido), 0))
            self.filtro_rol.blockSignals(False)
            self.rol_nuevo.blockSignals(True)
            self.rol_nuevo.clear()
            for rol in roles:
                self.rol_nuevo.addItem(rol.nombre_rol, rol.id_rol)
            self.rol_nuevo.blockSignals(False)
        ok, usuarios = self.ejecutar(servicio.listar_usuarios)
        if ok:
            self._usuarios = usuarios
        self._filtrar()

    def _nombre_rol(self, id_rol) -> str:
        return next((r.nombre_rol for r in self._roles if r.id_rol == id_rol), "")

    def _es_yo(self, usuario) -> bool:
        sesion = self.sesiones.sesion
        return sesion is not None and sesion.id_usuario == usuario.id_usuario

    def _filtrar(self, *_):
        texto = self.buscar.text().strip().lower()
        rol = self.filtro_rol.currentData()
        estado = self.filtro_estado.currentData()
        visibles = [u for u in self._usuarios
                    if (rol is None or u.id_rol == rol) and (estado is None or u.estado_cuenta == estado)
                    and (not texto or texto in u.nombre_usuario.lower() or texto in u.nombre_completo.lower())]
        self.tabla.blockSignals(True)
        self.tabla.cargar([(u.nombre_usuario + ("  (tú)" if self._es_yo(u) else ""), u.nombre_completo, "", "")
                           for u in visibles], datos=visibles)
        for fila, u in enumerate(visibles):
            nombre_rol = self._nombre_rol(u.id_rol)
            self.tabla.setCellWidget(fila, 2, celda_insignia(nombre_rol, TIPO_ROL.get(nombre_rol, "info")))
            self.tabla.setCellWidget(fila, 3, celda_insignia(u.estado_cuenta,
                                                             "ok" if u.estado_cuenta == "ACTIVO" else "error"))
        self.tabla.blockSignals(False)
        self.total.setText(f"{len(visibles)} de {len(self._usuarios)}")
        fila = next((i for i, u in enumerate(visibles) if u.id_usuario == self._id_elegido), -1)
        if fila >= 0:
            self.tabla.selectRow(fila)  # dispara _al_seleccionar
        else:
            self._limpiar_ficha()

    def _actual(self):
        return self.tabla.dato_seleccionado()

    def _al_seleccionar(self):
        usuario = self._actual()
        if usuario is None:
            self._limpiar_ficha()
            return
        self._id_elegido = usuario.id_usuario
        self._mostrar_ficha(usuario)

    def _mostrar_ficha(self, u):
        activo = u.estado_cuenta == "ACTIVO"
        yo = self._es_yo(u)
        nombre_rol = self._nombre_rol(u.id_rol)
        self.nombre.setText(u.nombre_completo)
        self.insignia_estado.poner(u.estado_cuenta, "ok" if activo else "error")
        self.insignia_estado.show()
        self.detalle.setText(f"Usuario {u.nombre_usuario} · rol {nombre_rol}" + (" · es tu cuenta" if yo else ""))
        permisos = PERMISOS.get(nombre_rol, set())
        texto = ", ".join(DESCRIPCION_PERMISOS[p] for p in DESCRIPCION_PERMISOS if p in permisos)
        self.d_permisos.poner(texto[:1].upper() + texto[1:] if texto else "Ninguna operación")
        self.rol_nuevo.blockSignals(True)
        self.rol_nuevo.setCurrentIndex(max(self.rol_nuevo.findData(u.id_rol), 0))
        self.rol_nuevo.blockSignals(False)
        self.rol_nuevo.setEnabled(not yo)
        self.boton_rol.setEnabled(False)  # se activa al elegir un rol distinto
        self.boton_estado.setEnabled(not yo)
        self.boton_estado.setText("Desactivar" if activo else "Activar")
        self.boton_estado.cambiar_icono("candado" if activo else "ok", "error" if activo else "ok")
        self.boton_contrasena.setEnabled(True)
        self.nota_propia.setVisible(yo)

    def _limpiar_ficha(self):
        self._id_elegido = None
        self.nombre.setText("Selecciona un usuario")
        self.insignia_estado.hide()
        self.detalle.setText("Verás su rol, lo que puede hacer y las acciones sobre su cuenta.")
        self.d_permisos.poner(None)
        self.rol_nuevo.setEnabled(False)
        for boton in (self.boton_rol, self.boton_estado, self.boton_contrasena):
            boton.setEnabled(False)
        self.nota_propia.hide()

    def _revisar_rol(self, *_):
        usuario = self._actual()
        self.boton_rol.setEnabled(usuario is not None and not self._es_yo(usuario)
                                  and self.rol_nuevo.currentData() != usuario.id_rol)

    # Acciones

    def _nuevo(self):
        dialogo = DialogoUsuario(self.ventana, self._roles)
        if dialogo.exec() and dialogo.usuario is not None:  # 1 = aceptado
            self._id_elegido = dialogo.usuario.id_usuario
            self.buscar.blockSignals(True)
            self.buscar.clear()
            self.buscar.blockSignals(False)
            self.avisar(f"Usuario {dialogo.usuario.nombre_usuario} creado. Ya puede iniciar sesión.", "ok")
            self._cargar()

    def _cambiar_rol(self):
        usuario = self._actual()
        if usuario is None:
            return
        if self.rol_nuevo.currentData() == usuario.id_rol:
            self.avisar(f"{usuario.nombre_usuario} ya tiene ese rol.", "info")
            return
        nuevo = self.rol_nuevo.currentText()
        if not confirmar(self, "Cambiar rol", f"¿Cambiar el rol de {usuario.nombre_usuario} a {nuevo}?\n\n"
                                              "Sus permisos cambian desde su próximo inicio de sesión.",
                         "Sí, cambiar rol"):
            return
        ok, _ = self.ejecutar(self.servicios["usuarios"].cambiar_rol, usuario.id_usuario,
                              self.rol_nuevo.currentData(), exito=f"{usuario.nombre_usuario} ahora es {nuevo}.")
        if ok:
            self._cargar()

    def _cambiar_estado(self):
        usuario = self._actual()
        if usuario is None:
            return
        activo = usuario.estado_cuenta == "ACTIVO"
        if activo and not confirmar(self, "Desactivar cuenta",
                                    f"¿Desactivar la cuenta {usuario.nombre_usuario}?\n\n"
                                    "Ya no podrá iniciar sesión hasta que se active de nuevo.", "Sí, desactivar"):
            return
        estado = "INACTIVO" if activo else "ACTIVO"
        ok, _ = self.ejecutar(self.servicios["usuarios"].cambiar_estado, usuario.id_usuario, estado,
                              exito=f"Cuenta {usuario.nombre_usuario}: {'desactivada' if activo else 'activada'}.")
        if ok:
            self._cargar()

    def _restablecer(self):
        usuario = self._actual()
        if usuario is None:
            return
        dialogo = DialogoContrasena(self.ventana, usuario)
        if dialogo.exec() and dialogo.cambiada:
            self.avisar(f"Contraseña de {usuario.nombre_usuario} actualizada.", "ok")

    def _al_cambiar_tema(self, _nombre):
        self._accion_buscar.setIcon(iconos.icono("buscar", tema.color("tenue")))
