import psycopg2
from psycopg2 import OperationalError

def probar_conexion():
    # ⚠️ IMPORTANTE: Reemplaza estos valores con los datos reales de tu servidor
    credenciales = {
        "dbname": "nexusdb",
        "user": "postgres",           # Tu usuario (suele ser postgres por defecto)
        "password": "123mm456*",  # La contraseña de ese usuario
        "host": "localhost",          # 'localhost' si está en tu misma PC, o la IP del servidor
        "port": "5432"                # 5432 es el puerto por defecto de PostgreSQL
    }

    try:
        print("Iniciando conexión para el sistema NEXUS PRIME...")
        
        # Intentamos establecer la conexión
        conexion = psycopg2.connect(**credenciales)
        
        # El cursor es nuestra "herramienta" para ejecutar comandos SQL
        cursor = conexion.cursor()
        
        # Ejecutamos una consulta básica y segura para verificar la comunicación
        cursor.execute("SELECT version();")
        version_db = cursor.fetchone()
        
        print("\n¡Conexión exitosa! ✅")
        print(f"Estás conectado a: {version_db[0]}")
        print("La base de datos está lista para empezar a gestionar el inventario y las ventas.")

    except OperationalError as e:
        print("\n❌ Ocurrió un error al intentar conectar a la base de datos:")
        print("Revisa que el servicio de PostgreSQL esté activo y que las credenciales sean correctas.")
        print(f"Detalle técnico: {e}")
        
    finally:
        # Esta sección siempre se ejecuta, haya error o no, para asegurar que no queden conexiones abiertas
        if 'conexion' in locals() and conexion is not None:
            cursor.close()
            conexion.close()
            print("\nConexión cerrada de forma segura.")

if __name__ == "__main__":
    probar_conexion()