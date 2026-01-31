from db_manager import db_pool  # Importamos tu pool de conexiones

class Proveedor:
    def __init__(self, cod_compania, cod_proveedor, rif, nombre, direccion=None, telefono=None, email=None, usuario_id=1):
        # Inicializamos los datos básicos del proveedor
        self.cod_compania = cod_compania
        self.cod_proveedor = cod_proveedor
        self.rif = rif
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.email = email
        self.usuario_id = usuario_id  # El ID del usuario que está registrando (Auditoría)

    def guardar(self):
        """Intenta guardar este proveedor en la base de datos PostgreSQL"""
        conn = db_pool.obtener_conexion()
        
        if conn:
            try:
                cursor = conn.cursor()
                # La consulta SQL exacta para tu tabla creada en el Paso 1
                sql = """
                    INSERT INTO maestro_proveedores 
                    (cod_compania, cod_proveedor, rif, nombre_provider, direccion, telefono1, email1, id_user_crea)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                # Los valores que vamos a insertar
                valores = (
                    self.cod_compania, 
                    self.cod_proveedor, 
                    self.rif, 
                    self.nombre, 
                    self.direccion, 
                    self.telefono, 
                    self.email, 
                    self.usuario_id
                )
                
                cursor.execute(sql, valores)
                conn.commit() # Confirmamos el cambio
                return True, f"Proveedor {self.nombre} registrado con éxito."
                
            except Exception as e:
                conn.rollback() # Si falla, deshacemos cualquier cambio parcial
                return False, f"Error de Base de Datos: {e}"
                
            finally:
                cursor.close()
                db_pool.liberar_conexion(conn) # ¡Devolvemos la conexión al pool!
        else:
            return False, "Error crítico: No hay conexión con el servidor."

    @staticmethod
    def obtener_todos(cod_compania):
        """Método para listar proveedores en una grilla (ejemplo futuro)"""
        conn = db_pool.obtener_conexion()
        lista = []
        if conn:
            try:
                cursor = conn.cursor()
                sql = "SELECT cod_proveedor, rif, nombre_provider FROM maestro_proveedores WHERE cod_compania = %s"
                cursor.execute(sql, (cod_compania,))
                lista = cursor.fetchall()
            except Exception as e:
                print(f"Error al listar: {e}")
            finally:
                cursor.close()
                db_pool.liberar_conexion(conn)
        return lista