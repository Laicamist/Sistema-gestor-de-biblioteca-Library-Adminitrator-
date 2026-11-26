from datetime import date
from typing import List, Optional

from config import CONSULTAR, CATALOGO, ADMINISTRACION
from Modelos import (
    Categoria,
    Disponibilidad,
    Ejemplar,
    Libro,
    DatosInvalidosError,
    EjemplarNoEncontradoError,
)
from Logic.servicio_base import ServicioBase

# Tamaños de las columnas en la base de datos
MAX_ISBN = 20
MAX_TITULO = 150
MAX_AUTOR = 100
MAX_EDITORIAL = 80
MAX_CATEGORIA = 50
MAX_CODIGO = 30
MAX_UBICACION = 50

# Estados que se pueden poner a mano; PRESTADO solo lo ponen los procedimientos
ESTADOS_MANUALES = ("DISPONIBLE", "MANTENIMIENTO", "BAJA")


class CatalogoServicio(ServicioBase):

    #Categorías

    def listar_categorias(self) -> List[Categoria]:
        self._exigir(CATALOGO)
        return self._dao().listar_categorias()

    def agregar_categoria(self, nombre: str) -> Categoria:
        self._exigir(ADMINISTRACION)
        categoria = Categoria(nombre=self._requerido(nombre, "el nombre de la categoría",
                                                     MAX_CATEGORIA).upper())
        self._dao().agregar_categoria(categoria)
        return categoria

    #Libros

    def listar_libros(self) -> List[Libro]:
        self._exigir(CATALOGO)
        return self._dao().listar_libros()

    def buscar_libro(self, isbn: str) -> Optional[Libro]:
        """Se puede llamar con el ISBN escaneado de la contraportada."""
        self._exigir(CATALOGO)
        return self._dao().buscar_libro(self._requerido(isbn, "el ISBN", MAX_ISBN))

    def registrar_libro(self, isbn: str, titulo: str, autor: str, id_categoria: int,
                        editorial: Optional[str] = None, anio=None) -> Libro:
        self._exigir(CATALOGO)
        libro = self._armar_libro(isbn, titulo, autor, id_categoria, editorial, anio)
        if self._dao().buscar_libro(libro.isbn) is not None:
            raise DatosInvalidosError(f"Ya existe un libro con el ISBN {libro.isbn}.")
        self._dao().agregar_libro(libro)
        return libro

    def actualizar_libro(self, id_libro: int, isbn: str, titulo: str, autor: str, id_categoria: int,
                         editorial: Optional[str] = None, anio=None) -> Libro:
        """Corrige los datos de un libro. El ISBN puede cambiar si no lo usa otro libro."""
        self._exigir(CATALOGO)
        libro = self._armar_libro(isbn, titulo, autor, id_categoria, editorial, anio)
        libro.id_libro = self._entero(id_libro, "el libro", 1)
        otro = self._dao().buscar_libro(libro.isbn)
        if otro is not None and otro.id_libro != libro.id_libro:
            raise DatosInvalidosError(f"Ya existe otro libro con el ISBN {libro.isbn}.")
        # Sin revisar filas afectadas: MySQL reporta 0 si se guarda sin cambios.
        self._dao().actualizar_libro(libro)
        return libro

    def _armar_libro(self, isbn, titulo, autor, id_categoria, editorial, anio) -> Libro:
        """Valida y normaliza los datos de un libro (mayúsculas, tamaños, año)."""
        if anio not in (None, ""):
            anio = self._entero(anio, "el año", 1, date.today().year)
        else:
            anio = None
        editorial = self._opcional(editorial, "la editorial", MAX_EDITORIAL)
        return Libro(
            isbn=self._requerido(isbn, "el ISBN", MAX_ISBN),
            titulo=self._requerido(titulo, "el título", MAX_TITULO).upper(),
            autor=self._requerido(autor, "el autor", MAX_AUTOR).upper(),
            id_categoria=self._entero(id_categoria, "la categoría", 1),
            editorial=editorial.upper() if editorial else None,
            anio=anio,
        )

    def eliminar_libro(self, id_libro: int) -> int:
        """Solo administrador. Se puede eliminar un libro sin ejemplares o con todas sus
        copias dadas de BAJA; esas copias se borran junto con él. No se elimina si una copia
        sigue en uso o si sus copias tienen préstamos: el historial alimenta los reportes
        y el historial de los alumnos. Regresa cuántas copias en BAJA se borraron."""
        self._exigir(ADMINISTRACION)
        id_libro = self._entero(id_libro, "el libro", 1)
        ejemplares = self._dao().listar_ejemplares(id_libro)
        en_uso = [e for e in ejemplares if e.estado != "BAJA"]
        if en_uso:
            codigos = ", ".join(f"{e.codigo_barras} ({e.estado})" for e in en_uso[:3])
            if len(en_uso) > 3:
                codigos += f" y {len(en_uso) - 3} más"
            raise DatosInvalidosError(
                f"El libro aún tiene {len(en_uso)} copia(s) sin dar de BAJA: {codigos}. "
                "Dalas de BAJA para poder eliminarlo (una prestada primero se devuelve).")
        prestamos = self._dao().contar_prestamos_libro(id_libro)
        if prestamos:
            raise DatosInvalidosError(
                f"No se puede eliminar: sus copias tienen {prestamos} préstamo(s) en el historial, "
                "que se perderían de los reportes y del historial de los alumnos. "
                "Con todas sus copias en BAJA ya no se puede prestar.")
        if self._dao().eliminar_libro(id_libro) == 0:
            raise DatosInvalidosError("Ese libro no existe.")
        return len(ejemplares)

    #Ejemplares

    def listar_ejemplares(self, id_libro: int) -> List[Ejemplar]:
        self._exigir(CATALOGO)
        return self._dao().listar_ejemplares(id_libro)

    def registrar_ejemplar(self, codigo_barras: str, id_libro: int, ubicacion: str) -> Ejemplar:
        """El código se captura con el lector al pegar la etiqueta en la copia."""
        self._exigir(CATALOGO)
        ejemplar = Ejemplar(
            codigo_barras=self._requerido(codigo_barras, "el código de barras", MAX_CODIGO),
            id_libro=self._entero(id_libro, "el libro", 1),
            ubicacion=self._requerido(ubicacion, "la ubicación", MAX_UBICACION).upper(),
        )
        self._dao().agregar_ejemplar(ejemplar)
        return ejemplar

    def _ejemplar_existente(self, codigo_barras: str):
        codigo = self._requerido(codigo_barras, "el código de barras", MAX_CODIGO)
        actual = self._dao().consultar_ejemplar(codigo)
        if actual is None:
            raise EjemplarNoEncontradoError(f"No existe un ejemplar con el código {codigo}.")
        return codigo, actual

    def cambiar_ubicacion(self, codigo_barras: str, nueva_ubicacion: str) -> None:
        """Usa SP_CAMBIAR_UBICACION; la auditoría guarda la ubicación anterior y la nueva."""
        self._exigir(CATALOGO)
        codigo, actual = self._ejemplar_existente(codigo_barras)
        nueva = self._requerido(nueva_ubicacion, "la nueva ubicación", MAX_UBICACION).upper()
        if nueva == actual.ubicacion:
            raise DatosInvalidosError("El ejemplar ya está en esa ubicación.")
        self._dao().cambiar_ubicacion(codigo, nueva)

    def cambiar_estado_ejemplar(self, codigo_barras: str, estado: str) -> None:
        """DISPONIBLE, MANTENIMIENTO o BAJA. Un ejemplar prestado primero se devuelve."""
        self._exigir(CATALOGO)
        estado = (estado or "").strip().upper()
        if estado not in ESTADOS_MANUALES:
            raise DatosInvalidosError(f"Estado inválido. Usa: {', '.join(ESTADOS_MANUALES)}.")
        codigo, actual = self._ejemplar_existente(codigo_barras)
        if actual.estado == "PRESTADO":
            raise DatosInvalidosError("El ejemplar está prestado; registra primero la devolución.")
        if actual.estado == estado:
            raise DatosInvalidosError(f"El ejemplar ya está en {estado}.")
        self._dao().cambiar_estado_ejemplar(codigo, estado)

    #Disponibilidad (cualquier rol)

    def disponibilidad(self, id_libro: int) -> Disponibilidad:
        """Usa SP_DISPONIBILIDAD_LIBRO (parámetros OUT)."""
        self._exigir(CONSULTAR)
        return self._dao().disponibilidad_libro(self._entero(id_libro, "el libro", 1))
