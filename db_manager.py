import psycopg2
from psycopg2 import pool, Error

# --- 1. PRIMERO: DEFINIMOS LA CLASE ---
class ConexionDB:
    _pool = None

    def __init__(self, host, database, user, password, min_conn=1, max_conn=20):
        if ConexionDB._pool is None:
            try:
                ConexionDB._pool = psycopg2.pool.ThreadedConnectionPool(
                    min_conn, max_conn,
                    host=host,
                    database=database,
                    user=user,
                    password=password
                )
                print("✅ Pool de conexiones iniciado correctamente.")
            except (Exception, Error) as error:
                print(f"❌ Error al crear el pool: {error}")

    def obtener_conexion(self):
        if ConexionDB._pool:
            return ConexionDB._pool.getconn()
        return None

    def liberar_conexion(self, conexion):
        if ConexionDB._pool and conexion:
            ConexionDB._pool.putconn(conexion)

# --- 2. SEGUNDO: CREAMOS LA INSTANCIA (VARIABLE GLOBAL) ---
# Esto DEBE ir después de la clase, nunca antes.
try:
    db_pool = ConexionDB("localhost", "nexusdb", "postgres", "123Mm456*", 2, 15)
except Exception as e:
    print(f"Error al iniciar la instancia de base de datos: {e}")