import sys
import psycopg2
import hashlib # Para verificar contraseñas reales
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QMessageBox
)
# CORRECCIÓN AQUÍ: Se agregó 'Qt' a la importación
from PyQt6.QtCore import QTimer, Qt 
from db_config import DB_PARAMS

# Importamos el nuevo Menú Principal
from menu_principal import MenuPrincipal

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acceso Nexus ERP")
        self.setFixedSize(350, 450)
        self.setStyleSheet("background-color: white;")
        
        # Variables de retorno
        self.usuario_id = None
        self.empresa_id = None
        self.nombre_empresa = None
        self.rol_usuario = None 
        
        self.init_ui()
        QTimer.singleShot(100, self.cargar_empresas)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Título
        lbl = QLabel("Bienvenido")
        lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(lbl)
        
        layout.addWidget(QLabel("Empresa:"))
        self.cmb = QComboBox()
        self.cmb.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.cmb)
        
        layout.addWidget(QLabel("Usuario:"))
        self.user = QLineEdit()
        self.user.setPlaceholderText("Ej: admin")
        self.user.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.user)
        
        layout.addWidget(QLabel("Contraseña:"))
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        self.pwd.returnPressed.connect(self.validar) # Enter para entrar
        layout.addWidget(self.pwd)
        
        btn = QPushButton("INICIAR SESIÓN")
        # AQUI OCURRIA EL ERROR: Ahora Qt ya está definido arriba
        btn.setCursor(Qt.CursorShape.PointingHandCursor) 
        btn.setStyleSheet("""
            QPushButton { background-color: #007BFF; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #0056b3; }
        """)
        btn.clicked.connect(self.validar)
        layout.addWidget(btn)
        
        self.setLayout(layout)

    def cargar_empresas(self):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT cod_compania, razon_social FROM maestro_empresas WHERE estatus=True")
            rows = cur.fetchall()
            conn.close()
            
            if rows:
                for r in rows:
                    self.cmb.addItem(r[1], r[0])
            else:
                self.cmb.addItem("No hay empresas (Ejecute Config)", -1)
                
        except Exception as e:
            QMessageBox.critical(self, "Error Conexión", f"Error DB: {e}")

    def validar(self):
        usuario = self.user.text().strip()
        password = self.pwd.text()
        idx = self.cmb.currentIndex()
        
        if idx == -1 or not usuario or not password:
            QMessageBox.warning(self, "Datos incompletos", "Por favor ingrese usuario, contraseña y seleccione una empresa.")
            return
            
        cod_empresa = self.cmb.itemData(idx)
        nombre_empresa = self.cmb.currentText()
        
        # Validar credenciales contra BD
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            # Buscamos el hash y el rol del usuario
            query = "SELECT id_usuario, password_hash, rol, estatus FROM usuarios_sistema WHERE usuario_login = %s"
            cur.execute(query, (usuario,))
            data = cur.fetchone()
            conn.close()
            
            if data:
                db_id, db_hash, db_rol, db_activo = data
                
                if not db_activo:
                    QMessageBox.warning(self, "Bloqueado", "Este usuario está inactivo.")
                    return
                
                # Verificar Hash
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if input_hash == db_hash:
                    # LOGIN EXITOSO
                    self.usuario_id = db_id
                    self.rol_usuario = db_rol
                    self.empresa_id = cod_empresa
                    self.nombre_empresa = nombre_empresa
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", "Contraseña incorrecta.")
            else:
                QMessageBox.warning(self, "Error", "Usuario no encontrado.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error SQL", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Ejecutar Login
    login = LoginDialog()
    
    if login.exec() == QDialog.DialogCode.Accepted:
        # 2. Si es correcto, lanzar MENÚ PRINCIPAL
        # Pasamos TODOS los datos de contexto
        menu = MenuPrincipal(
            cod_compania=login.empresa_id,
            id_usuario=login.usuario_id,
            nombre_empresa=login.nombre_empresa,
            rol_usuario=login.rol_usuario
        )
        menu.show()
        
        sys.exit(app.exec())
    else:
        sys.exit()