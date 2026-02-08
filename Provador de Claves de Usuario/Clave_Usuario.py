import sys
import hashlib
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QFormLayout, QTextEdit
)
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCore import Qt

class HashTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Herramienta SHA-256: Generador y Verificador")
        self.resize(500, 450)
        self.apply_styles()
        self.init_ui()

    def apply_styles(self):
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; margin-top: 10px; padding: 10px; border-radius: 5px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit, QTextEdit { padding: 5px; border: 1px solid #aaa; border-radius: 4px; }
            QPushButton { background-color: #007BFF; color: white; padding: 8px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #0056b3; }
            .success { color: green; font-weight: bold; }
            .fail { color: red; font-weight: bold; }
        """)

    def init_ui(self):
        layout = QVBoxLayout()

        # --- SECCIÓN 1: GENERAR (Clave -> Hash) ---
        gb_gen = QGroupBox("1. Generar Hash (Para guardar en DB)")
        form_gen = QFormLayout()
        
        self.txt_input_pass = QLineEdit()
        self.txt_input_pass.setPlaceholderText("Escribe la contraseña aquí...")
        self.txt_input_pass.textChanged.connect(self.generar_hash)
        
        self.txt_output_hash = QTextEdit()
        self.txt_output_hash.setReadOnly(True)
        self.txt_output_hash.setMaximumHeight(60)
        self.txt_output_hash.setStyleSheet("background-color: #f0f0f0; color: #333;")
        
        btn_copy = QPushButton("Copiar Hash")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(self.txt_output_hash.toPlainText()))

        form_gen.addRow("Contraseña:", self.txt_input_pass)
        form_gen.addRow("Hash SHA-256:", self.txt_output_hash)
        form_gen.addRow("", btn_copy)
        
        gb_gen.setLayout(form_gen)
        layout.addWidget(gb_gen)

        # --- SECCIÓN 2: VERIFICAR (Hash + Clave -> ¿Coinciden?) ---
        gb_ver = QGroupBox("2. Verificar (Validar Hash de la DB)")
        form_ver = QFormLayout()

        self.txt_db_hash = QLineEdit()
        self.txt_db_hash.setPlaceholderText("Pega aquí el código largo (a665a...)")
        
        self.txt_try_pass = QLineEdit()
        self.txt_try_pass.setPlaceholderText("Escribe la posible contraseña...")
        
        btn_check = QPushButton("¿Coinciden?")
        btn_check.setStyleSheet("background-color: #28a745; color: white;")
        btn_check.clicked.connect(self.verificar_match)
        
        self.lbl_result = QLabel("Esperando comprobación...")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_ver.addRow("Hash de DB:", self.txt_db_hash)
        form_ver.addRow("Posible Clave:", self.txt_try_pass)
        form_ver.addRow("", btn_check)
        form_ver.addRow(self.lbl_result)

        gb_ver.setLayout(form_ver)
        layout.addWidget(gb_ver)

        layout.addStretch()
        self.setLayout(layout)

    # --- LÓGICA ---

    def generar_hash(self):
        text = self.txt_input_pass.text()
        if text:
            # Aquí ocurre la magia: SHA-256
            hash_result = hashlib.sha256(text.encode()).hexdigest()
            self.txt_output_hash.setText(hash_result)
        else:
            self.txt_output_hash.clear()

    def verificar_match(self):
        db_hash = self.txt_db_hash.text().strip()
        candidate = self.txt_try_pass.text()
        
        if not db_hash or not candidate:
            QMessageBox.warning(self, "Error", "Llena ambos campos en la sección 2")
            return

        # Generamos el hash de la clave candidata
        candidate_hash = hashlib.sha256(candidate.encode()).hexdigest()

        # Comparamos
        if candidate_hash == db_hash:
            self.lbl_result.setText("✅ ¡COINCIDEN! La contraseña es correcta.")
            self.lbl_result.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_result.setText("❌ NO COINCIDEN. Esa no es la contraseña.")
            self.lbl_result.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HashTool()
    window.show()
    sys.exit(app.exec())