import sys
import os  # <-- Añadimos esto para manejar las rutas
from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

def iniciar_sistema():
    app = QApplication(sys.argv)

    # --- LA SOLUCIÓN AL ERROR ---
    # 1. Obtenemos la ruta exacta de la carpeta donde está este script (main2.py)
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Unimos esa ruta con el nombre de tu diseño (Asegúrate de que se llame así)
    # Si le pusiste otro nombre a tu archivo en Qt Designer, cámbialo aquí abajo:
    ruta_ui = os.path.join(directorio_actual, "pantalla_principal.ui") 

    # 3. Abrimos el archivo con la ruta completa y a prueba de fallos
    ruta_archivo = QFile(ruta_ui)
    
    # Verificamos si el archivo realmente existe antes de abrirlo para evitar caídas
    if not os.path.exists(ruta_ui):
        print(f"ERROR FATAL: No se encontró el archivo en la ruta: {ruta_ui}")
        return

    ruta_archivo.open(QFile.ReadOnly)

    # 4. Cargar la ventana
    cargador = QUiLoader()
    ventana = cargador.load(ruta_archivo)
    ruta_archivo.close()

    # 5. Mostrar la ventana
    ventana.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    iniciar_sistema()