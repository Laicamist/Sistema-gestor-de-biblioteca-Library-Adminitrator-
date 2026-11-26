import json
import re
from datetime import date, datetime

from PySide6.QtGui import QBrush, QFont
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QVBoxLayout

from UI import iconos, tema
from UI.componentes import (
    BotonIcono, Insignia, PanelVidrio, Tabla, celda_insignia, etiqueta, exportar_csv,
)
from UI.pantallas.base import Pantalla

TABLAS = ("EJEMPLARES", "PRESTAMOS", "LIBROS", "ALUMNOS", "USUARIOS")
OPERACIONES = ("INSERT", "UPDATE", "DELETE")
TIPO_OPERACION = {"INSERT": "ok", "UPDATE": "info", "DELETE": "error"}
TEXTO_OPERACION = {"INSERT": "ALTA", "UPDATE": "CAMBIO", "DELETE": "BORRADO"}
LIMITES = (100, 200, 500, 1000)

# Nombre legible de cada campo que guardan los triggers, en el orden en que se muestran
# (MySQL reordena las llaves de una columna JSON, así que el orden se pone aquí).
CAMPOS = {
    "ID_PRESTAMO": "Préstamo", "ID_EJEMPLAR": "Ejemplar", "CODIGO_BARRAS": "Código de barras",
    "ID_LIBRO": "Libro", "ISBN": "ISBN", "TITULO": "Título", "AUTOR": "Autor",
    "ID_ALUMNO": "Alumno", "MATRICULA": "Matrícula", "ID_CARRERA": "Carrera", "SEMESTRE": "Semestre",
    "ID_USUARIO": "Usuario", "NOMBRE_USUARIO": "Nombre de usuario", "ID_ROL": "Rol",
    "UBICACION": "Ubicación", "FECHA_LIMITE": "Fecha límite", "FECHA_DEVOLUCION": "Fecha de devolución",
    "ESTADO": "Estado", "ESTADO_CUENTA": "Estado de la cuenta", "CAMBIO_CONTRASENA": "Contraseña",
}
ORDEN = list(CAMPOS)
# Campo que identifica el registro en el resumen de un cambio (el primero que exista)
IDENTIFICADORES = ("CODIGO_BARRAS", "MATRICULA", "NOMBRE_USUARIO", "ISBN", "ID_PRESTAMO")
_FECHA_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def _json(valor) -> dict:
    """Las columnas JSON llegan como texto (o bytes, según el conector)."""
    if valor is None:
        return {}
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, (bytes, bytearray)):
        valor = valor.decode("utf-8")
    try:
        datos = json.loads(valor)
    except (TypeError, ValueError):
        return {"VALOR": str(valor)}
    return datos if isinstance(datos, dict) else {"VALOR": datos}


def _campo(llave: str) -> str:
    return CAMPOS.get(llave, llave.replace("_", " ").capitalize())


def _valor(valor) -> str:
    if valor in (None, ""):
        return "—"
    texto = str(valor)
    fecha = _FECHA_ISO.match(texto)
    return f"{fecha.group(3)}/{fecha.group(2)}/{fecha.group(1)}" if fecha else texto


def _llaves(*dicts) -> list:
    todas = set().union(*dicts)
    return sorted(todas, key=lambda k: (ORDEN.index(k) if k in ORDEN else len(ORDEN), k))


def comparar(registro) -> list:
    """Renglones (campo, antes, después, cambió) para el detalle de un movimiento."""
    antes, despues = _json(registro.datos_anteriores), _json(registro.datos_nuevos)
    renglones = []
    for llave in _llaves(antes, despues):
        if llave == "CAMBIO_CONTRASENA":  # el trigger nunca guarda el hash, solo si cambió
            cambio = antes.get(llave) == "SI"
            renglones.append((_campo(llave), "—", "Cambiada" if cambio else "Sin cambio", cambio))
            continue
        a = _valor(antes.get(llave)) if registro.tipo_operacion != "INSERT" else ""
        d = _valor(despues.get(llave)) if registro.tipo_operacion != "DELETE" else ""
        cambio = registro.tipo_operacion == "UPDATE" and llave in antes and llave in despues \
            and antes.get(llave) != despues.get(llave)
        renglones.append((_campo(llave), a, d, cambio))
    return renglones


def _identificador(registro) -> str:
    datos = {**_json(registro.datos_anteriores), **_json(registro.datos_nuevos)}
    for llave in IDENTIFICADORES:
        if datos.get(llave) not in (None, ""):
            return f"Préstamo {datos[llave]}" if llave == "ID_PRESTAMO" else str(datos[llave])
    return ""


def texto_busqueda(registro) -> str:
    """Todo lo guardado en el movimiento, para que la búsqueda encuentre códigos o matrículas
    aunque no hayan cambiado."""
    valores = list(_json(registro.datos_anteriores).values()) + list(_json(registro.datos_nuevos).values())
    return " ".join([str(registro.usuario_responsable), registro.tabla_afectada, resumir(registro)]
                    + [str(v) for v in valores]).lower()


def resumir(registro) -> str:
    """Una línea con lo que pasó: qué campos cambiaron, o qué se dio de alta o se borró."""
    if registro.tipo_operacion == "UPDATE":
        partes = [f"{campo}: {a} → {d}" if campo != "Contraseña" else "Contraseña cambiada"
                  for campo, a, d, cambio in comparar(registro) if cambio]
        cambios = "; ".join(partes) or "Sin cambios en los campos registrados"
        identificador = _identificador(registro)
        return f"{identificador} · {cambios}" if identificador else cambios
    datos = _json(registro.datos_nuevos if registro.tipo_operacion == "INSERT" else registro.datos_anteriores)
    return ", ".join(f"{_campo(k)}: {_valor(datos[k])}" for k in _llaves(datos)) or "—"


def _fecha_hora(valor) -> str:
    return f"{valor:%d/%m/%Y %H:%M:%S}" if isinstance(valor, datetime) else str(valor or "—")


class PantallaAuditoria(Pantalla):
    """Bitácora que llenan los triggers de auditoría. La app solo la lee: el usuario de
    MySQL del administrador no tiene permiso para modificarla ni borrarla."""

    def __init__(self, ventana, parent=None):
        super().__init__(ventana, parent)
        self._registros = []
        self._visibles = []
        self._id_elegido = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 10, 10)
        raiz.setSpacing(16)

        barra = QHBoxLayout()
        barra.setSpacing(10)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar por usuario, código, matrícula, título...")
        self.buscar.setClearButtonEnabled(True)
        self._accion_buscar = self.buscar.addAction(
            iconos.icono("buscar", tema.color("tenue")), QLineEdit.ActionPosition.LeadingPosition)
        self.buscar.textChanged.connect(self._filtrar)
        barra.addWidget(self.buscar, 3)
        self.filtro_tabla = QComboBox()
        self.filtro_tabla.addItem("Todas las tablas", None)
        for tabla in TABLAS:
            self.filtro_tabla.addItem(tabla, tabla)
        self.filtro_tabla.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_tabla, 1)
        self.filtro_operacion = QComboBox()
        self.filtro_operacion.addItem("Todas las operaciones", None)
        for operacion in OPERACIONES:
            self.filtro_operacion.addItem(f"{operacion} ({TEXTO_OPERACION[operacion].lower()})", operacion)
        self.filtro_operacion.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_operacion, 1)
        self.limite = QComboBox()
        for limite in LIMITES:
            self.limite.addItem(f"Últimos {limite}", limite)
        self.limite.setCurrentIndex(1)
        self.limite.currentIndexChanged.connect(lambda *_: self._cargar())
        barra.addWidget(self.limite)
        actualizar = BotonIcono("Actualizar", "actualizar", "pastilla", token="acento", tam=18)
        actualizar.clicked.connect(lambda: self._cargar())
        barra.addWidget(actualizar)
        exportar = BotonIcono("Exportar CSV", "exportar", "pastilla", token="acento", tam=18)
        exportar.clicked.connect(self._exportar)
        barra.addWidget(exportar)
        raiz.addLayout(barra)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._crear_panel_lista(), 3)
        cuerpo.addWidget(self._crear_panel_detalle(), 2)
        raiz.addLayout(cuerpo, 1)

        tema.gestor.cambiado.connect(self._al_cambiar_tema)

    # Construcción

    def _crear_panel_lista(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("Movimientos", "seccion"))
        self.total = etiqueta("", tenue=True)
        cabecera.addWidget(self.total)
        cabecera.addStretch(1)
        cabecera.addWidget(etiqueta("Solo lectura · la escriben los triggers", "chip"))
        caja.addLayout(cabecera)
        self.tabla = Tabla(["Fecha y hora", "Tabla", "Operación", "Usuario", "Qué pasó"])
        cabecera_tabla = self.tabla.horizontalHeader()
        for columna in (0, 1, 2, 3):
            cabecera_tabla.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.itemSelectionChanged.connect(self._al_seleccionar)
        caja.addWidget(self.tabla, 1)
        self.sin_movimientos = etiqueta("No hay movimientos con estos filtros.", tenue=True)
        self.sin_movimientos.hide()
        caja.addWidget(self.sin_movimientos)
        return panel

    def _crear_panel_detalle(self) -> PanelVidrio:
        panel = PanelVidrio()
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(22, 18, 22, 18)
        caja.setSpacing(10)
        cabecera = QHBoxLayout()
        self.titulo_detalle = etiqueta("Detalle del movimiento", "seccion")
        cabecera.addWidget(self.titulo_detalle, 1)
        self.insignia_operacion = Insignia("", "info")
        self.insignia_operacion.hide()
        cabecera.addWidget(self.insignia_operacion)
        caja.addLayout(cabecera)
        self.datos_detalle = etiqueta("Selecciona un movimiento para ver los datos antes y después del cambio.",
                                      tenue=True, ajustar=True)
        caja.addWidget(self.datos_detalle)
        self.detalle = Tabla(["Campo", "Antes", "Después"])
        self.detalle.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        caja.addWidget(self.detalle, 1)
        self.nota = etiqueta("Los campos que cambiaron aparecen resaltados. Las contraseñas nunca se guardan: "
                             "solo se registra si cambiaron.", tenue=True, ajustar=True)
        self.nota.setStyleSheet("font-size: 12px;")
        caja.addWidget(self.nota)
        return panel

    # Datos

    def al_mostrar(self, **opciones):
        self._cargar()

    def _cargar(self):
        limite = self.limite.currentData() or LIMITES[1]
        ok, registros = self.ejecutar(self.servicios["reportes"].auditoria, limite)
        if ok:
            self._registros = registros
        self._filtrar()

    def _filtrar(self, *_):
        texto = self.buscar.text().strip().lower()
        tabla = self.filtro_tabla.currentData()
        operacion = self.filtro_operacion.currentData()
        visibles = []
        for r in self._registros:
            if tabla is not None and r.tabla_afectada != tabla:
                continue
            if operacion is not None and r.tipo_operacion != operacion:
                continue
            resumen = resumir(r)
            if texto and texto not in texto_busqueda(r):
                continue
            visibles.append((r, resumen))
        self._visibles = [r for r, _ in visibles]
        self.tabla.blockSignals(True)
        self.tabla.cargar([(_fecha_hora(r.fecha_hora), r.tabla_afectada, "", r.usuario_responsable or "—", resumen)
                           for r, resumen in visibles], datos=self._visibles)
        for fila, r in enumerate(self._visibles):
            self.tabla.setCellWidget(fila, 2, celda_insignia(TEXTO_OPERACION.get(r.tipo_operacion, r.tipo_operacion),
                                                             TIPO_OPERACION.get(r.tipo_operacion, "info")))
        self.tabla.blockSignals(False)
        self.total.setText(f"{len(self._visibles)} de {len(self._registros)}")
        self.tabla.setVisible(bool(self._visibles))
        self.sin_movimientos.setVisible(not self._visibles)
        fila = next((i for i, r in enumerate(self._visibles) if r.id_movimiento == self._id_elegido), -1)
        if fila >= 0:
            self.tabla.selectRow(fila)  # dispara _al_seleccionar
        else:
            self._limpiar_detalle()

    def _al_seleccionar(self):
        registro = self.tabla.dato_seleccionado()
        if registro is None:
            self._limpiar_detalle()
            return
        self._id_elegido = registro.id_movimiento
        self._mostrar_detalle(registro)

    def _mostrar_detalle(self, r):
        self.titulo_detalle.setText(f"Movimiento #{r.id_movimiento}" if r.id_movimiento else "Movimiento")
        self.insignia_operacion.poner(f"{r.tipo_operacion} · {TEXTO_OPERACION.get(r.tipo_operacion, '')}",
                                      TIPO_OPERACION.get(r.tipo_operacion, "info"))
        self.insignia_operacion.show()
        self.datos_detalle.setText(f"{r.tabla_afectada} · {_fecha_hora(r.fecha_hora)} · "
                                   f"hecho por {r.usuario_responsable or 'desconocido'}")
        renglones = comparar(r)
        self.detalle.cargar([(campo, a, d) for campo, a, d, _ in renglones])
        negrita = QFont()
        negrita.setBold(True)
        acento = QBrush(tema.color("acento"))
        for fila, (_, _, _, cambio) in enumerate(renglones):
            if not cambio:
                continue
            for columna in range(3):
                celda = self.detalle.item(fila, columna)
                if celda is not None:
                    celda.setFont(negrita)
                    celda.setForeground(acento)

    def _limpiar_detalle(self):
        self._id_elegido = None
        self.titulo_detalle.setText("Detalle del movimiento")
        self.insignia_operacion.hide()
        self.datos_detalle.setText("Selecciona un movimiento para ver los datos antes y después del cambio.")
        self.detalle.cargar([])

    def _exportar(self):
        if not self._visibles:
            self.avisar("No hay movimientos para exportar.", "info")
            return
        filas = [(r.id_movimiento, _fecha_hora(r.fecha_hora), r.tabla_afectada, r.tipo_operacion,
                  r.usuario_responsable, resumir(r)) for r in self._visibles]
        try:
            ruta = exportar_csv(self, f"auditoria_{date.today():%Y%m%d}.csv",
                                ["Movimiento", "Fecha y hora", "Tabla", "Operación", "Usuario", "Qué pasó"], filas)
        except OSError as error:
            self.avisar(f"No se pudo guardar el archivo: {error}", "error", 0)
            return
        if ruta:
            self.avisar(f"Auditoría exportada: {ruta}", "ok")

    def _al_cambiar_tema(self, _nombre):
        self._accion_buscar.setIcon(iconos.icono("buscar", tema.color("tenue")))
        registro = self.tabla.dato_seleccionado()
        if registro is not None:
            self._mostrar_detalle(registro)  # el resaltado usa el color del tema
