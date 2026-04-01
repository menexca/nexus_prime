import sys
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QFormLayout, QMessageBox, QApplication, QSpinBox
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

from error_handler import manejar_error

class CorrelativosForm(QWidget):
    def __init__(self, cod_compania, nombre_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.nombre_empresa = nombre_empresa
        
        self.setWindowTitle(f"Control de Números y Correlativos - {self.nombre_empresa}")
        self.resize(700, 450)
        self.tipo_seleccionado = None
        
        self.apply_styles()
        self.init_ui()
        
        # 1. Ejecutamos la auto-reparación antes de cargar la lista
        self.verificar_y_crear_default()
        self.cargar_lista()

    def apply_styles(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F0F2F5")) 
        self.setPalette(palette)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QPushButton { background-color: #007BFF; color: white; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #0056b3; }
            QLineEdit, QSpinBox { border: 1px solid #ccc; border-radius: 4px; padding: 5px; background-color: white; }
            QLineEdit:focus, QSpinBox:focus { border: 1px solid #007BFF; }
            QListWidget { border: 1px solid #ccc; background-color: white; border-radius: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background-color: #E6F3FF; color: #0056b3; font-weight: bold; border-left: 4px solid #007BFF; }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Panel Izquierdo
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Documentos Disponibles:"))
        self.lista_docs = QListWidget()
        self.lista_docs.itemClicked.connect(self.cargar_datos)
        left_layout.addWidget(self.lista_docs)
        
        self.btn_nuevo = QPushButton("+ Nuevo Correlativo")
        self.btn_nuevo.clicked.connect(self.limpiar)
        left_layout.addWidget(self.btn_nuevo)
        main_layout.addLayout(left_layout, 1)

        # Panel Derecho
        right_layout = QVBoxLayout()
        self.lbl_titulo = QLabel("Configuración de Secuencia")
        self.lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px;")
        right_layout.addWidget(self.lbl_titulo)

        form = QFormLayout()
        self.txt_tipo = QLineEdit()
        self.txt_tipo.setPlaceholderText("Ej: COMPRAS, VENTAS, PAGOS")
        form.addRow("Tipo Documento *:", self.txt_tipo)

        self.txt_prefijo = QLineEdit()
        self.txt_prefijo.setPlaceholderText("Ej: COMP-")
        form.addRow("Prefijo:", self.txt_prefijo)

        self.spin_siguiente = QSpinBox()
        self.spin_siguiente.setRange(1, 999999999)
        form.addRow("Siguiente Número:", self.spin_siguiente)

        self.spin_ceros = QSpinBox()
        self.spin_ceros.setRange(0, 10)
        self.spin_ceros.setValue(5)
        form.addRow("Longitud (Ceros a la izq):", self.spin_ceros)

        right_layout.addLayout(form)
        right_layout.addStretch()

        btn_layout = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar Configuración")
        self.btn_guardar.setStyleSheet("background-color: #28a745;")
        self.btn_guardar.clicked.connect(self.guardar)
        
        self.btn_salir = QPushButton("Salir")
        self.btn_salir.setStyleSheet("background-color: #343a40;")
        self.btn_salir.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_salir)
        
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout, 2)

    def limpiar(self):
        self.tipo_seleccionado = None
        self.txt_tipo.clear()
        self.txt_tipo.setReadOnly(False)
        self.txt_prefijo.clear()
        self.spin_siguiente.setValue(1)
        self.spin_ceros.setValue(5)
        self.lista_docs.clearSelection()

    # --- NUEVA FUNCIÓN: Auto-reparación e Inicialización ---
    @manejar_error
    def verificar_y_crear_default(self):
        # Lista de documentos que todo ERP necesita por defecto
        documentos_base = ["COMPRAS", "VENTAS", "PAGOS", "COBROS", "AJUSTES_INV", "NOTAS_ENTREGA"]
        
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                for doc in documentos_base:
                    # Verificamos si ya existe
                    cur.execute("SELECT 1 FROM cfg_correlativos WHERE cod_compania = %s AND tipo_documento = %s", (self.cod_compania, doc))
                    if not cur.fetchone():
                        # Si no existe, lo creamos con un prefijo sugerido (las 3 primeras letras)
                        prefijo_sugerido = f"{doc[:3]}-"
                        cur.execute("""
                            INSERT INTO cfg_correlativos (cod_compania, tipo_documento, prefijo, siguiente_numero, longitud_ceros) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (self.cod_compania, doc, prefijo_sugerido, 1, 5))

    @manejar_error
    def cargar_lista(self):
        self.lista_docs.clear()
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tipo_documento FROM cfg_correlativos WHERE cod_compania = %s ORDER BY tipo_documento", (self.cod_compania,))
                for r in cur.fetchall():
                    self.lista_docs.addItem(r[0])

    @manejar_error
    def cargar_datos(self, item):
        tipo = item.text()
        self.tipo_seleccionado = tipo
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT prefijo, siguiente_numero, longitud_ceros FROM cfg_correlativos WHERE cod_compania = %s AND tipo_documento = %s", (self.cod_compania, tipo))
                d = cur.fetchone()
                
        if d:
            self.txt_tipo.setText(tipo)
            self.txt_tipo.setReadOnly(True)
            self.txt_prefijo.setText(d[0])
            self.spin_siguiente.setValue(d[1])
            self.spin_ceros.setValue(d[2])

    @manejar_error
    def guardar(self):
        tipo = self.txt_tipo.text().strip().upper()
        if not tipo:
            QMessageBox.warning(self, "Error", "El tipo de documento es obligatorio.")
            return
            
        try:
            with psycopg2.connect(**DB_PARAMS) as conn:
                with conn.cursor() as cur:
                    if self.tipo_seleccionado:
                        cur.execute("UPDATE cfg_correlativos SET prefijo=%s, siguiente_numero=%s, longitud_ceros=%s WHERE cod_compania=%s AND tipo_documento=%s", 
                                    (self.txt_prefijo.text(), self.spin_siguiente.value(), self.spin_ceros.value(), self.cod_compania, self.tipo_seleccionado))
                    else:
                        cur.execute("INSERT INTO cfg_correlativos (cod_compania, tipo_documento, prefijo, siguiente_numero, longitud_ceros) VALUES (%s, %s, %s, %s, %s)",
                                    (self.cod_compania, tipo, self.txt_prefijo.text(), self.spin_siguiente.value(), self.spin_ceros.value()))
            
            QMessageBox.information(self, "Éxito", "Configuración guardada.")
            self.cargar_lista()
            self.limpiar()
            
        except psycopg2.IntegrityError:
            QMessageBox.warning(self, "Error", f"El tipo de documento '{tipo}' ya existe en esta empresa.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CorrelativosForm(1, "EMPRESA PRUEBA")
    w.show()
    sys.exit(app.exec())