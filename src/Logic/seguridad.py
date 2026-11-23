import hashlib

from Modelos import DatosInvalidosError

MIN_CONTRASENA = 8


def hashear(contrasena: str) -> str:
    """SHA-256 en hexadecimal (64 caracteres), igual que CONTRASENA_HASH.

    No cambia mayúsculas: los usuarios de prueba usan ADMIN123, BIBLIO123 y CONS123.
    """
    return hashlib.sha256(contrasena.encode("utf-8")).hexdigest()


def validar_contrasena(contrasena: str) -> None:
    """Regla para contraseñas nuevas (las de prueba ya existen y no pasan por aquí)."""
    if not contrasena or len(contrasena) < MIN_CONTRASENA:
        raise DatosInvalidosError(f"La contraseña debe tener al menos {MIN_CONTRASENA} caracteres.")
    if contrasena.isdigit() or contrasena.isalpha():
        raise DatosInvalidosError("La contraseña debe combinar letras y números.")
