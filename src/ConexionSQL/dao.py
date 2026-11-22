from mysql.connector import Error, IntegrityError
from ConexionSQL.conexion import Database



class DAO:
    def __init__(self, conexion=None):
        self._db = None
        if conexion is None:
            self._db = Database()
            conexion = self._db.get_connection()
        self.conn = conexion
        # Las consultas sueltas no dejan transacciones abiertas;
        # guardar_venta() abre la suya de forma explícita.
        self.conn.autocommit = True

    def cerrar(self):
        if self._db is not None:
            self._db.close()
