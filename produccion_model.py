# -*- coding: utf-8 -*-
# produccion_model.py

class ProduccionModel:
    def __init__(self, conexion, cod_compania):
        self.conn = conexion
        self.cod_compania = cod_compania

    def obtener_receta_teorica(self, sku_producto):
        """
        Busca la receta maestra del producto (Cantidades para 1 unidad base).
        """
        if not self.conn:
            return False, "No hay conexión a la base de datos.", []
            
        try:
            cur = self.conn.cursor()
            # FÍJATE QUE AHORA SOLO TRAE r.cantidad_requerida SIN MULTIPLICAR
            sql = """
                SELECT r.cod_producto_hijo, p.nombre, u.cod_unidad, 
                       r.cantidad_requerida, 
                       p.costo_final_usd
                FROM inv_productos_recetas r
                JOIN inv_productos p ON r.cod_producto_hijo = p.cod_producto AND r.cod_compania = p.cod_compania
                LEFT JOIN inv_unidades u ON p.id_unidad = u.id_unidad
                WHERE r.cod_producto_padre = %s AND r.cod_compania = %s
            """
            cur.execute(sql, (sku_producto, self.cod_compania))
            filas = cur.fetchall()
            
            if not filas:
                return False, "Este producto no tiene una receta configurada.", []
                
            return True, "Receta cargada con éxito.", filas
            
        except Exception as e:
            return False, f"Error al consultar la receta: {str(e)}", []
            
    def generar_numero_orden(self):
        """Genera un correlativo automático para la Orden de Producción"""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM prd_ordenes_produccion WHERE cod_compania = %s", (self.cod_compania,))
            total = cur.fetchone()[0]
            return f"ORD-{total + 1:05d}" # Ejemplo: ORD-00001
        except:
            return "ORD-ERROR"