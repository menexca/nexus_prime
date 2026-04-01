import sys
import logging
import traceback
import inspect  # <-- Añadimos inspect
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
    """Extrae el detalle del error, lo guarda en el log y avisa al usuario."""
    traceback_details = ''.join(traceback.format_exception(exctype, value, tb))
    logging.error("Excepción capturada:\n%s", traceback_details)
    
    mensaje_usuario = f"Ha ocurrido un error inesperado.\n\nMotivo: {str(value)}\n\nEl detalle técnico ha sido guardado en el registro."
    
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