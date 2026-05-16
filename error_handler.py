import sys
import logging
import traceback
import inspect  
import os # <-- Añadimos os para limpiar las rutas largas
from functools import wraps
from PyQt6.QtWidgets import QMessageBox

# Configuración del archivo log
logging.basicConfig(
    filename='nexus_erp_errores.log',
    level=logging.ERROR,
    format='%(asctime)s - %(module)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def registrar_y_notificar_error(exctype, value, tb, ventana_padre=None):
    """Extrae el detalle del error, lo guarda en el log y avisa al usuario con detalles precisos."""
    # 1. Guardamos el traceback completo en el log (como siempre)
    traceback_details = ''.join(traceback.format_exception(exctype, value, tb))
    logging.error("Excepción capturada:\n%s", traceback_details)
    
    # 2. Extraemos la información del último paso que causó el error
    tb_info = traceback.extract_tb(tb)
    ultimo_paso = tb_info[-1] # Tomamos el último elemento de la pila de errores
    
    archivo_completo = ultimo_paso.filename
    archivo_corto = os.path.basename(archivo_completo) # Solo el nombre del archivo, no la ruta larga
    linea = ultimo_paso.lineno
    funcion = ultimo_paso.name
    
    # 3. Armamos un mensaje mucho más útil para el desarrollador
    mensaje_usuario = (
        f"Ha ocurrido un error inesperado en el sistema.\n\n"
        f"🔴 Motivo: {str(value)}\n\n"
        f"📍 Ubicación del fallo:\n"
        f"   • Archivo: {archivo_corto}\n"
        f"   • Función: {funcion}()\n"
        f"   • Línea: {linea}\n\n"
        f"El detalle técnico completo ha sido guardado en el archivo log."
    )
    
    if ventana_padre:
        QMessageBox.critical(ventana_padre, "Error en el Sistema", mensaje_usuario)
    else:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error Crítico")
        msg.setText(mensaje_usuario)
        msg.exec()

def manejar_error(func):
    """Decorador optimizado para capturar errores y manejar señales de PyQt6."""
    
    # 1. EVALUACIÓN ÚNICA (Tiempo de inicialización)
    # Esto ocurre solo una vez cuando Python lee el @manejar_error
    sig = inspect.signature(func)
    solo_espera_self = len(sig.parameters) == 1
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 2. EJECUCIÓN CONTINUA (Tiempo de ejecución)
        # Esto ocurre en cada clic o evento, pero ahora es una evaluación ultrarrápida (booleana)
        try:
            if solo_espera_self:
                return func(self)
            else:
                return func(self, *args, **kwargs)
                
        except Exception as e:
            registrar_y_notificar_error(type(e), e, e.__traceback__, ventana_padre=self)
            
    return wrapper