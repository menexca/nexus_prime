import psycopg2
from psycopg2 import pool
from psycopg2 import Error

class ConexionDB:
    _pool = None  # Aquí guardaremos el pool para que sea compartido

    def __init__(self, host, database, user, password, min_conn=1, max_conn=20):
        # Si el pool no ha sido creado, lo creamos una sola vez
        if ConexionDB._pool is None:
            try:
                ConexionDB._pool = psycopg2.pool.ThreadedConnectionPool(
                    min_conn,    # Conexiones que siempre estarán abiertas
                    max_conn,    # Máximo de conexiones si hay mucha carga
                    host=host,
                    database=database,
                    user=user,
                    password=password
                )
                print(f"Pool de conexiones creado exitosamente (Máx: {max_conn})")
            except (Exception, Error) as error:
                print(f"Error al crear el pool: {error}")

    def obtener_conexion(self):
        """Pide una conexión prestada al pool."""
        if ConexionDB._pool:
            return ConexionDB._pool.getconn()
        return None

    def liberar_conexion(self, conexion):
        """Devuelve la conexión al pool para que otro la use."""
        if ConexionDB._pool and conexion:
            ConexionDB._pool.putconn(conexion)

    def cerrar_todo(self):
        """Cierra todas las conexiones del pool (al apagar el sistema)."""
        if ConexionDB._pool:
            ConexionDB._pool.closeall()
            print("Pool de conexiones cerrado.")