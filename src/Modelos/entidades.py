from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

# Valores válidos de las columnas ENUM
ESTADOS_REGISTRO = ("ACTIVO", "INACTIVO")                                # USUARIOS, ALUMNOS
ESTADOS_EJEMPLAR = ("DISPONIBLE", "PRESTADO", "MANTENIMIENTO", "BAJA")   # EJEMPLARES
ESTADOS_PRESTAMO = ("ACTIVO", "DEVUELTO")                                # PRESTAMOS

def _limpiar(texto):
    """Quita espacios que sobran dejando un None"""
    return texto.strip() if isinstance(texto, str) else texto
#Tablas
@dataclass
class Usuario:
    """Tabla usuarios (inician sesión)"""
    nombre_completo: str
    nombre_usuario: str
    id_rol: int
    estado_cuenta: str = "ACTIVO"
    id_usuario: Optional[int] = None
    contrasena_hash: str = field(default="", repr=False) # repr=False: el hash nunca aparece al imprimir el objeto
    def __post_init__(self):
        self.nombre_completo = _limpiar(self.nombre_completo)
        self.nombre_usuario = _limpiar(self.nombre_usuario)

@dataclass
class Rol:
    """Tabla roles."""
    nombre_rol: str
    descripcion: Optional[str] = None
    id_rol: Optional[int] = None


@dataclass
class Prestamo:
    """Tabla prestamos."""
    id_ejemplar: int
    id_alumno: int
    id_usuario: int
    fecha_prestamo: date
    fecha_limite: date
    fecha_devolucion: Optional[date] = None
    estado: str = "ACTIVO"
    id_prestamo: Optional[int] = None
    @property
    def vencido(self) -> bool:
        return self.estado == "ACTIVO" and self.fecha_limite < date.today()

    def dias_retraso(self, hoy: Optional[date] = None) -> int:
        """Mismo cálculo que FN_DIAS_RETRASO."""
        fin = self.fecha_devolucion or hoy or date.today()
        return max((fin - self.fecha_limite).days, 0)

@dataclass
class Alumno:
    """Tabla alumnos (piden libros, no inician sesión)."""
    matricula: str
    nombre_completo: str
    id_carrera: int
    semestre: int
    correo: Optional[str] = None
    telefono: Optional[str] = None
    estado: str = "ACTIVO"
    id_alumno: Optional[int] = None

    def __post_init__(self):
        self.matricula = _limpiar(self.matricula)
        self.nombre_completo = _limpiar(self.nombre_completo)
        self.correo = _limpiar(self.correo) or None
        self.telefono = _limpiar(self.telefono) or None


@dataclass
class Carrera:
    """Tabla carreras."""
    nombre: str
    id_carrera: Optional[int] = None

@dataclass
class Ejemplar:
    """Tabla ejemplares (Copia fisica de un libro)"""
    codigo_barras: str
    id_libro: int
    ubicacion: str
    estado: str = "DISPONIBLE"
    id_ejemplar: Optional[int] = None

    def __post_init__(self):
        self.codigo_barras = _limpiar(self.codigo_barras)
        self.ubicacion = _limpiar(self.ubicacion)

@dataclass
class Libro:
    """Tabla libros (Como obra y no como una copia física)."""
    isbn: str
    titulo: str
    autor: str
    id_categoria: int
    editorial: Optional[str] = None
    anio: Optional[int] = None
    id_libro: Optional[int] = None

    def __post_init__(self):
        self.isbn = _limpiar(self.isbn)
        self.titulo = _limpiar(self.titulo)
        self.autor = _limpiar(self.autor)
        self.editorial = _limpiar(self.editorial) or None


@dataclass
class Categoria:
    """Tabla categorias."""
    nombre: str
    id_categoria: Optional[int] = None

@dataclass
class RegistroAuditoria:
    """Tabla auditoria (la llenan los triggers; la app solo la lee)."""
    tabla_afectada: str
    tipo_operacion: str
    fecha_hora: datetime
    usuario_responsable: Optional[str] = None
    datos_anteriores: Optional[str] = None   # JSON como texto
    datos_nuevos: Optional[str] = None       # JSON como texto
    id_movimiento: Optional[int] = None

# Resultados de los procedimientos
@dataclass
class Sesion:
    """Lo que devuelve un login correcto (OUT de SP_LOGIN)."""
    id_usuario: int
    nombre_usuario: str
    rol: str

@dataclass
class Disponibilidad:
    """OUT de SP_DISPONIBILIDAD_LIBRO."""
    total: int
    disponibles: int


@dataclass
class EjemplarConsulta:
    """Result set de SP_CONSULTAR_EJEMPLAR (lo que muestra el lector de codigos de barras)."""
    id_ejemplar: int
    codigo_barras: str
    titulo: str
    autor: str
    isbn: str
    categoria: str
    ubicacion: str
    estado: str
    disponible: int                      # 1/0 que regresa FN_EJEMPLAR_DISPONIBLE
    copias_disponibles: int
    matricula_alumno: Optional[str] = None
    prestado_a: Optional[str] = None
    fecha_limite: Optional[date] = None

@dataclass
class HistorialPrestamo:
    """Result set de SP_HISTORIAL_ALUMNO."""
    id_prestamo: int
    titulo: str
    codigo_barras: str
    fecha_prestamo: date
    fecha_limite: date
    fecha_devolucion: Optional[date]
    estado: str
    dias_retraso: int

# Vistas (Reportes)
@dataclass
class PrestamoVencido:
    """Vista v_prestamos_vencidos."""
    id_prestamo: int
    matricula: str
    alumno: str
    carrera: str
    correo: Optional[str]
    titulo: str
    codigo_barras: str
    fecha_prestamo: date
    fecha_limite: date
    dias_retraso: int


@dataclass
class LibroSolicitado:
    """Vista v_libros_mas_solicitados."""
    posicion: int
    id_libro: int
    titulo: str
    autor: str
    categoria: str
    total_prestamos: int


@dataclass
class LibroSinPrestamos:
    """Vista v_libros_sin_prestamos."""
    id_libro: int
    titulo: str
    autor: str


@dataclass
class DisponibilidadLibro:
    """Vista v_disponibilidad."""
    id_libro: int
    titulo: str
    autor: str
    total_ejemplares: int
    disponibles: int


@dataclass
class AlumnoConVencidos:
    """Vista v_alumnos_con_vencidos (reporte con CTE, GROUP BY y RANK)."""
    posicion: int
    matricula: str
    alumno: str
    carrera: str
    correo: Optional[str]
    libros_vencidos: int
    total_dias_retraso: int
    max_dias_retraso: int


@dataclass
class ResumenBiblioteca:
    """Vista v_resumen: contadores de la pantalla de inicio."""
    prestamos_activos: int
    prestamos_vencidos: int
    alumnos_con_retraso: int
    ejemplares_disponibles: int
    total_ejemplares: int
    en_mantenimiento: int
    de_baja: int
    alumnos_activos: int
    total_alumnos: int
