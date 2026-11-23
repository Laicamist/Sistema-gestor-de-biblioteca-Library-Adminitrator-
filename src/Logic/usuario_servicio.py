from typing import List

from config import ADMINISTRACION
from Modelos import Rol, Usuario, DatosInvalidosError, ESTADOS_REGISTRO
from Logic.seguridad import hashear, validar_contrasena
from Logic.servicio_base import ServicioBase

# Tamaños de las columnas en la base de datos
MAX_NOMBRE = 100
MAX_USUARIO = 30


class UsuarioServicio(ServicioBase):
    """Administración de cuentas del personal. Todo es solo para el administrador."""

    def listar_roles(self) -> List[Rol]:
        self._exigir(ADMINISTRACION)
        return self._dao().listar_roles()

    def listar_usuarios(self) -> List[Usuario]:
        self._exigir(ADMINISTRACION)
        return self._dao().listar_usuarios()

    def crear(self, nombre_completo: str, nombre_usuario: str, contrasena: str,
              id_rol: int) -> Usuario:
        self._exigir(ADMINISTRACION)
        nombre_usuario = self._requerido(nombre_usuario, "el nombre de usuario", MAX_USUARIO).upper()
        if " " in nombre_usuario:
            raise DatosInvalidosError("El nombre de usuario no debe tener espacios.")
        validar_contrasena(contrasena)
        usuario = Usuario(
            nombre_completo=self._requerido(nombre_completo, "el nombre completo", MAX_NOMBRE).upper(),
            nombre_usuario=nombre_usuario,
            id_rol=self._entero(id_rol, "el rol", 1),
            contrasena_hash=hashear(contrasena),
        )
        self._dao().agregar_usuario(usuario)   # UNIQUE evita usuarios repetidos
        return usuario

    def _no_es_uno_mismo(self, id_usuario: int, accion: str):
        sesion = self._exigir(ADMINISTRACION)
        if sesion.id_usuario == id_usuario:
            raise DatosInvalidosError(f"No puedes {accion} tu propia cuenta.")

    def cambiar_estado(self, id_usuario: int, estado: str) -> None:
        """Lo registra TRG_AUD_USUARIOS_AU."""
        self._no_es_uno_mismo(id_usuario, "cambiar el estado de")
        estado = (estado or "").strip().upper()
        if estado not in ESTADOS_REGISTRO:
            raise DatosInvalidosError(f"Estado inválido. Usa: {', '.join(ESTADOS_REGISTRO)}.")
        if self._dao().cambiar_estado_usuario(id_usuario, estado) == 0:
            raise DatosInvalidosError("Ese usuario no existe o ya tenía ese estado.")

    def cambiar_rol(self, id_usuario: int, id_rol: int) -> None:
        """Lo registra TRG_AUD_USUARIOS_AU."""
        self._no_es_uno_mismo(id_usuario, "cambiar el rol de")
        if self._dao().cambiar_rol_usuario(id_usuario, self._entero(id_rol, "el rol", 1)) == 0:
            raise DatosInvalidosError("Ese usuario no existe o ya tenía ese rol.")

    def restablecer_contrasena(self, id_usuario: int, nueva: str) -> None:
        self._exigir(ADMINISTRACION)
        validar_contrasena(nueva)
        if self._dao().cambiar_contrasena(id_usuario, hashear(nueva)) == 0:
            raise DatosInvalidosError("Ese usuario no existe o la contraseña es la misma.")
