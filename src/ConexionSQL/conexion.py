import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Cargar variables de entorno (.env en la raíz del proyecto)
load_dotenv(override=True)  # el .env manda sobre variables viejas de la terminal


class Database:
    """Abre UNA conexión a MySQL con el usuario de BD del perfil indicado.

    Cada perfil es un usuario distinto de MySQL con sus propios GRANT
    (ver 04_seguridad.sql). En el .env se configuran así:

        DB_USER_LOGIN / DB_PASSWORD_LOGIN                  -> BIB_LOGIN o BIB_CONSULTA (ejecutan SP_LOGIN)
        DB_USER_ADMINISTRADOR / DB_PASSWORD_ADMINISTRADOR  -> BIB_ADMIN
        DB_USER_BIBLIOTECARIO / DB_PASSWORD_BIBLIOTECARIO  -> BIB_BIBLIOTECARIO
        DB_USER_CONSULTA / DB_PASSWORD_CONSULTA            -> BIB_CONSULTA

    El nombre del perfil es el mismo que el del rol que regresa SP_LOGIN,
    así la sesión se reconecta con los permisos exactos de su rol.

    Si falta DB_USER_<PERFIL>, se usa DB_USER / DB_PASSWORD (útil mientras se
    desarrolla), pero se avisa en la consola: con ese usuario MySQL ya no
    restringe por rol, así que en la evaluación deben existir los 4 perfiles.
    """

    def __init__(self, perfil: str = "LOGIN"):
        perfil = (perfil or "LOGIN").upper()
        usuario = os.getenv(f"DB_USER_{perfil}")
        contrasena = os.getenv(f"DB_PASSWORD_{perfil}")
        if not usuario:
            usuario = os.getenv("DB_USER")
            contrasena = os.getenv("DB_PASSWORD")
            if not usuario:
                raise Error(msg=f"Falta DB_USER_{perfil} (o DB_USER) en el archivo .env.")
            print(f"AVISO: no existe DB_USER_{perfil} en el .env; se usa DB_USER ({usuario}). "
                  "MySQL no aplicará los permisos del rol.")
        self.perfil = perfil
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "3306")),
                database=os.getenv("DB_NAME", "BIBLIOTECA"),
                user=usuario,
                password=contrasena or "",
            )
        except Error as e:
            print(f"Error al conectar con el perfil {perfil} ({usuario}): {e}")
            raise

    def get_connection(self):
        return self.connection

    def close(self):
        if hasattr(self, "connection") and self.connection.is_connected():
            self.connection.close()
