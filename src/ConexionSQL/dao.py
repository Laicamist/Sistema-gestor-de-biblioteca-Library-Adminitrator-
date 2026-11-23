"""
Solo lee y escribe en la base de datos y convierte las filas en objetos de Modelos/.
Préstamos y devoluciones usan los procedimientos SP_REGISTRAR_*, que ya hacen su
propia transacción (START TRANSACTION / COMMIT / ROLLBACK) dentro de MySQL.
"""
from mysql.connector import Error, IntegrityError
from ConexionSQL.conexion import Database
from typing import List, Optional
from Modelos import (
    Alumno,
    AlumnoConVencidos,
    Carrera,
    Categoria,
    Disponibilidad,
    DisponibilidadLibro,
    Ejemplar,
    EjemplarConsulta,
    HistorialPrestamo,
    Libro,
    LibroSinPrestamos,
    LibroSolicitado,
    PrestamoVencido,
    RegistroAuditoria,
    Rol,
    Sesion,
    Usuario,
    AccesoDenegadoError,
    DatosInvalidosError,
    LoginError,
    PrestamoError,
)
# Códigos de error de MySQL que se traducen a errores de negocio
ERRNO_SIGNAL = 1644                        # SIGNAL SQLSTATE '45000' de un trigger
ERRNO_SIN_PERMISO = (1044, 1142, 1143, 1370)  # GRANT insuficiente (base, tabla, columna, procedimiento)
ERRNO_DUPLICADO = 1062                     # UNIQUE (ISBN, código de barras, matrícula, usuario)
ERRNO_TIENE_HIJOS = 1451                   # borrar un registro que otros usan (FK)
ERRNO_SIN_PADRE = 1452                     # FK apunta a un registro que no existe
ERRNO_CHECK = 3819                         # restricción CHECK


class DAO:
    def __init__(self, conexion=None, perfil: str = "LOGIN"):
        self._db = None
        if conexion is None:
            self._db = Database(perfil)
            conexion = self._db.get_connection()
        self.conn = conexion
        # Cada sentencia se confirma sola; los procedimientos de préstamo y
        # devolución abren su propia transacción.
        self.conn.autocommit = True

    def reconectar(self, perfil: str):
        """Cambia el usuario de MySQL (por ejemplo, del de login al del rol).
        Los servicios comparten este mismo objeto, así que todos quedan con la nueva conexión."""
        nueva = Database(perfil)   # si falla, se queda la conexión anterior
        self.cerrar()
        self._db = nueva
        self.conn = nueva.get_connection()
        self.conn.autocommit = True

    def cerrar(self):
        if self._db is not None:
            self._db.close()

    # Utilidades internas

    @staticmethod
    def _fila(fila: dict) -> dict:
        """Las vistas y procedimientos regresan columnas en MAYÚSCULAS;
        los campos de las dataclasses están en minúsculas."""
        return {k.lower(): v for k, v in fila.items()}

    @staticmethod
    def _texto(valor):
        """Algunos parámetros OUT llegan como bytes según la versión del conector."""
        return valor.decode() if isinstance(valor, (bytes, bytearray)) else valor

    @staticmethod
    def _traducir(e: Error) -> Optional[Exception]:
        """Convierte un error de MySQL en un error que la UI pueda mostrar.
        Regresa None si es un error técnico que debe subir tal cual."""
        errno = getattr(e, "errno", None)
        msg = getattr(e, "msg", None) or str(e)
        if errno == ERRNO_SIGNAL:
            return DatosInvalidosError(msg)
        if errno in ERRNO_SIN_PERMISO:
            return AccesoDenegadoError("Tu usuario de base de datos no tiene permiso para esta operación.")
        if errno == ERRNO_DUPLICADO:
            return DatosInvalidosError(f"Ya existe un registro con ese valor ({msg}).")
        if errno == ERRNO_TIENE_HIJOS:
            return DatosInvalidosError("No se puede eliminar: tiene registros relacionados.")
        if errno == ERRNO_SIN_PADRE:
            return DatosInvalidosError("El registro relacionado (categoría, carrera, libro, rol...) no existe.")
        if errno == ERRNO_CHECK or isinstance(e, IntegrityError):
            return DatosInvalidosError(f"La BD rechazó el registro: {msg}")
        return None

    def _consultar(self, sql: str, params=()) -> List[dict]:
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return [self._fila(f) for f in cur.fetchall()]
        except Error as e:
            traducido = self._traducir(e)
            if traducido:
                raise traducido from e
            raise
        finally:
            cur.close()

    def _consultar_uno(self, sql: str, params=()) -> Optional[dict]:
        filas = self._consultar(sql, params)
        return filas[0] if filas else None

    def _ejecutar(self, sql: str, params=()) -> int:
        """INSERT/UPDATE/DELETE. Regresa el id generado o las filas afectadas."""
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.lastrowid or cur.rowcount
        except Error as e:
            traducido = self._traducir(e)
            if traducido:
                raise traducido from e
            raise
        finally:
            cur.close()

    def _llamar_sp(self, nombre: str, args=()):
        """Regresa (argumentos con los OUT llenos, filas del SELECT del procedimiento).
        En args se pone None en el lugar de cada parámetro OUT."""
        cur = self.conn.cursor()
        try:
            salida = cur.callproc(nombre, list(args))
            filas = []
            for rs in cur.stored_results():
                filas.extend(self._fila(dict(zip(rs.column_names, f))) for f in rs.fetchall())
            return tuple(self._texto(v) for v in salida), filas
        except Error as e:
            traducido = self._traducir(e)
            if traducido:
                raise traducido from e
            raise
        finally:
            cur.close()

    #Sesión

    def login(self, nombre_usuario: str, contrasena_hash: str) -> Sesion:
        salida, _ = self._llamar_sp(
            "SP_LOGIN", (nombre_usuario, contrasena_hash, None, None, None))
        id_usuario, rol, mensaje = salida[2], salida[3], salida[4]
        if id_usuario is None:
            raise LoginError(mensaje)
        return Sesion(id_usuario=id_usuario, nombre_usuario=nombre_usuario, rol=rol)

    def establecer_usuario_app(self, nombre_usuario: str):
        """Los triggers de AUDITORIA leen @USUARIO_APP. Solo existe en ESTA conexión."""
        self._ejecutar("SET @USUARIO_APP = %s", (nombre_usuario,))

    #Usuarios del sistema (solo administrador)

    def listar_roles(self) -> List[Rol]:
        filas = self._consultar("SELECT id_rol, nombre_rol, descripcion FROM ROLES ORDER BY id_rol")
        return [Rol(**f) for f in filas]

    def listar_usuarios(self) -> List[Usuario]:
        """Sin el hash: nunca sale de la base para mostrarse."""
        filas = self._consultar(
            "SELECT id_usuario, nombre_completo, nombre_usuario, id_rol, estado_cuenta "
            "FROM USUARIOS ORDER BY nombre_completo")
        return [Usuario(**f) for f in filas]

    def agregar_usuario(self, usuario: Usuario) -> int:
        usuario.id_usuario = self._ejecutar(
            "INSERT INTO USUARIOS (nombre_completo, nombre_usuario, contrasena_hash, id_rol, estado_cuenta) "
            "VALUES (%s, %s, %s, %s, %s)",
            (usuario.nombre_completo, usuario.nombre_usuario, usuario.contrasena_hash,
             usuario.id_rol, usuario.estado_cuenta))
        return usuario.id_usuario

    def cambiar_estado_usuario(self, id_usuario: int, estado: str) -> int:
        return self._ejecutar("UPDATE USUARIOS SET estado_cuenta = %s WHERE id_usuario = %s",
                              (estado, id_usuario))

    def cambiar_rol_usuario(self, id_usuario: int, id_rol: int) -> int:
        return self._ejecutar("UPDATE USUARIOS SET id_rol = %s WHERE id_usuario = %s",
                              (id_rol, id_usuario))

    def cambiar_contrasena(self, id_usuario: int, contrasena_hash: str) -> int:
        return self._ejecutar("UPDATE USUARIOS SET contrasena_hash = %s WHERE id_usuario = %s",
                              (contrasena_hash, id_usuario))

    #Catálogo

    def listar_categorias(self) -> List[Categoria]:
        filas = self._consultar(
            "SELECT id_categoria, nombre FROM CATEGORIAS ORDER BY nombre")
        return [Categoria(**f) for f in filas]

    def agregar_categoria(self, categoria: Categoria) -> int:
        categoria.id_categoria = self._ejecutar(
            "INSERT INTO CATEGORIAS (nombre) VALUES (%s)", (categoria.nombre,))
        return categoria.id_categoria

    def listar_libros(self) -> List[Libro]:
        filas = self._consultar(
            "SELECT id_libro, isbn, titulo, autor, editorial, anio, id_categoria "
            "FROM LIBROS ORDER BY titulo")
        return [Libro(**f) for f in filas]

    def buscar_libro(self, isbn: str) -> Optional[Libro]:
        f = self._consultar_uno(
            "SELECT id_libro, isbn, titulo, autor, editorial, anio, id_categoria "
            "FROM LIBROS WHERE isbn = %s", (isbn,))
        return Libro(**f) if f else None

    def agregar_libro(self, libro: Libro) -> int:
        libro.id_libro = self._ejecutar(
            "INSERT INTO LIBROS (isbn, titulo, autor, editorial, anio, id_categoria) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (libro.isbn, libro.titulo, libro.autor, libro.editorial, libro.anio,
             libro.id_categoria))
        return libro.id_libro

    def eliminar_libro(self, id_libro: int) -> int:
        """Lo registra TRG_AUD_LIBROS_AD. Falla si el libro tiene ejemplares (FK)."""
        return self._ejecutar("DELETE FROM LIBROS WHERE id_libro = %s", (id_libro,))

    def listar_ejemplares(self, id_libro: int) -> List[Ejemplar]:
        filas = self._consultar(
            "SELECT id_ejemplar, codigo_barras, id_libro, ubicacion, estado "
            "FROM EJEMPLARES WHERE id_libro = %s ORDER BY codigo_barras", (id_libro,))
        return [Ejemplar(**f) for f in filas]

    def agregar_ejemplar(self, ejemplar: Ejemplar) -> int:
        ejemplar.id_ejemplar = self._ejecutar(
            "INSERT INTO EJEMPLARES (codigo_barras, id_libro, ubicacion, estado) "
            "VALUES (%s, %s, %s, %s)",
            (ejemplar.codigo_barras, ejemplar.id_libro, ejemplar.ubicacion, ejemplar.estado))
        return ejemplar.id_ejemplar

    def cambiar_estado_ejemplar(self, codigo_barras: str, estado: str) -> int:
        """Lo registra TRG_AUD_EJEMPLARES_AU."""
        return self._ejecutar("UPDATE EJEMPLARES SET estado = %s WHERE codigo_barras = %s",
                              (estado, codigo_barras))

    def cambiar_ubicacion(self, codigo_barras: str, nueva_ubicacion: str):
        """Lo registra TRG_AUD_EJEMPLARES_AU (ubicación anterior y nueva)."""
        self._llamar_sp("SP_CAMBIAR_UBICACION", (codigo_barras, nueva_ubicacion))

    def consultar_ejemplar(self, codigo_barras: str) -> Optional[EjemplarConsulta]:
        _, filas = self._llamar_sp("SP_CONSULTAR_EJEMPLAR", (codigo_barras,))
        return EjemplarConsulta(**filas[0]) if filas else None

    def disponibilidad_libro(self, id_libro: int) -> Disponibilidad:
        salida, _ = self._llamar_sp("SP_DISPONIBILIDAD_LIBRO", (id_libro, None, None))
        return Disponibilidad(total=salida[1] or 0, disponibles=salida[2] or 0)

    #Alumnos

    def listar_carreras(self) -> List[Carrera]:
        filas = self._consultar("SELECT id_carrera, nombre FROM CARRERAS ORDER BY nombre")
        return [Carrera(**f) for f in filas]

    def agregar_carrera(self, carrera: Carrera) -> int:
        carrera.id_carrera = self._ejecutar(
            "INSERT INTO CARRERAS (nombre) VALUES (%s)", (carrera.nombre,))
        return carrera.id_carrera

    def buscar_alumno(self, matricula: str) -> Optional[Alumno]:
        f = self._consultar_uno(
            "SELECT id_alumno, matricula, nombre_completo, id_carrera, semestre, "
            "correo, telefono, estado FROM ALUMNOS WHERE matricula = %s", (matricula,))
        return Alumno(**f) if f else None

    def agregar_alumno(self, alumno: Alumno) -> int:
        alumno.id_alumno = self._ejecutar(
            "INSERT INTO ALUMNOS (matricula, nombre_completo, id_carrera, semestre, "
            "correo, telefono, estado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (alumno.matricula, alumno.nombre_completo, alumno.id_carrera, alumno.semestre,
             alumno.correo, alumno.telefono, alumno.estado))
        return alumno.id_alumno

    def actualizar_alumno(self, alumno: Alumno) -> int:
        """Lo registra TRG_AUD_ALUMNOS_AU."""
        return self._ejecutar(
            "UPDATE ALUMNOS SET nombre_completo = %s, id_carrera = %s, semestre = %s, "
            "correo = %s, telefono = %s WHERE id_alumno = %s",
            (alumno.nombre_completo, alumno.id_carrera, alumno.semestre,
             alumno.correo, alumno.telefono, alumno.id_alumno))

    def cambiar_estado_alumno(self, id_alumno: int, estado: str) -> int:
        """Lo registra TRG_AUD_ALUMNOS_AU."""
        return self._ejecutar("UPDATE ALUMNOS SET estado = %s WHERE id_alumno = %s",
                              (estado, id_alumno))

    def contar_prestamos_activos(self, id_alumno: int) -> int:
        f = self._consultar_uno(
            "SELECT COUNT(*) AS total FROM PRESTAMOS WHERE id_alumno = %s AND estado = 'ACTIVO'",
            (id_alumno,))
        return f["total"] if f else 0

    #Préstamos

    def registrar_prestamo(self, codigo_barras: str, id_alumno: int,
                           id_usuario: int, dias: int) -> str:
        """El procedimiento atrapa sus propios errores y hace ROLLBACK: no lanza
        excepción, regresa 'ERROR: ...' en el mensaje. Aquí se convierte en PrestamoError."""
        salida, _ = self._llamar_sp(
            "SP_REGISTRAR_PRESTAMO", (codigo_barras, id_alumno, id_usuario, dias, None))
        mensaje = salida[4] or ""
        if mensaje.upper().startswith("ERROR"):
            raise PrestamoError(mensaje)
        return mensaje

    def registrar_devolucion(self, codigo_barras: str) -> int:
        """Regresa los días de retraso (0 si se devolvió a tiempo)."""
        salida, _ = self._llamar_sp("SP_REGISTRAR_DEVOLUCION", (codigo_barras, None, None))
        dias_retraso, mensaje = salida[1], salida[2] or ""
        if mensaje.upper().startswith("ERROR"):
            raise PrestamoError(mensaje)
        return dias_retraso or 0

    def historial_alumno(self, matricula: str) -> List[HistorialPrestamo]:
        _, filas = self._llamar_sp("SP_HISTORIAL_ALUMNO", (matricula,))
        return [HistorialPrestamo(**f) for f in filas]

    #Reportes

    def prestamos_vencidos(self) -> List[PrestamoVencido]:
        filas = self._consultar(
            "SELECT * FROM V_PRESTAMOS_VENCIDOS ORDER BY dias_retraso DESC")
        return [PrestamoVencido(**f) for f in filas]

    def libros_mas_solicitados(self) -> List[LibroSolicitado]:
        filas = self._consultar("SELECT * FROM V_LIBROS_MAS_SOLICITADOS ORDER BY posicion")
        return [LibroSolicitado(**f) for f in filas]

    def alumnos_con_vencidos(self) -> List[AlumnoConVencidos]:
        filas = self._consultar("SELECT * FROM V_ALUMNOS_CON_VENCIDOS ORDER BY posicion, alumno")
        return [AlumnoConVencidos(**f) for f in filas]

    def libros_sin_prestamos(self) -> List[LibroSinPrestamos]:
        filas = self._consultar("SELECT * FROM V_LIBROS_SIN_PRESTAMOS ORDER BY titulo")
        return [LibroSinPrestamos(**f) for f in filas]

    def disponibilidad_general(self) -> List[DisponibilidadLibro]:
        filas = self._consultar("SELECT * FROM V_DISPONIBILIDAD ORDER BY titulo")
        return [DisponibilidadLibro(**f) for f in filas]

    def listar_auditoria(self, limite: int = 200) -> List[RegistroAuditoria]:
        filas = self._consultar(
            "SELECT id_movimiento, tabla_afectada, tipo_operacion, fecha_hora, "
            "usuario_responsable, datos_anteriores, datos_nuevos FROM AUDITORIA "
            "ORDER BY fecha_hora DESC, id_movimiento DESC LIMIT %s", (limite,))
        return [RegistroAuditoria(**f) for f in filas]
