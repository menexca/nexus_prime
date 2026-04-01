import sys
import psycopg2
import hashlib
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt 
from db_config import DB_PARAMS

from menu_principal import MenuPrincipal
from error_handler import manejar_error

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acceso Nexus ERP")
        self.setFixedSize(350, 450)
        self.setStyleSheet("background-color: white;")
        
        self.usuario_id = None
        self.empresa_id = None
        self.nombre_empresa = None
        self.rol_usuario = None 
        self.nombre_completo = None 
        
        self.init_ui()
        QTimer.singleShot(100, self.cargar_empresas)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
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
        
        self.user.returnPressed.connect(self.pwd.setFocus) 
        self.pwd.returnPressed.connect(self.validar) 
        layout.addWidget(self.pwd)
        
        btn = QPushButton("INICIAR SESIÓN")
        btn.setAutoDefault(False) 
        btn.setDefault(False)     
        btn.setCursor(Qt.CursorShape.PointingHandCursor) 
        btn.setStyleSheet("""
            QPushButton { background-color: #007BFF; color: white; padding: 12px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #0056b3; }
        """)
        btn.clicked.connect(self.validar)
        layout.addWidget(btn)
        
        self.setLayout(layout)
        self.user.setFocus()

    def cargar_empresas(self):
        self.cmb.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT cod_compania, razon_social FROM cfg_empresas WHERE estatus=True")
            rows = cur.fetchall()
            conn.close()
            
            if rows:
                for r in rows:
                    self.cmb.addItem(r[1], r[0]) 
            else:
                self.cmb.addItem("No hay empresas activas", -1)
                
        except Exception as e:
            QMessageBox.critical(self, "Error Conexión", f"Error DB: {e}")

    def validar(self):
        usuario = self.user.text().strip()
        password = self.pwd.text()
        idx = self.cmb.currentIndex()
        
        if idx == -1 or not usuario or not password:
            QMessageBox.warning(self, "Datos incompletos", "Complete todos los campos.")
            return
            
        cod_empresa = self.cmb.itemData(idx)
        nombre_empresa = self.cmb.currentText()
        
        if cod_empresa == -1:
            QMessageBox.warning(self, "Error", "Debe configurar una empresa primero.")
            return

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            query = "SELECT id_usuario, password_hash, rol, estatus, nombre_completo FROM seg_usuarios WHERE usuario_login = %s"
            cur.execute(query, (usuario,))
            data = cur.fetchone()
            
            if data:
                db_id, db_hash, db_rol, db_activo, db_nombre = data
                
                # A. Verificar Estatus
                if not db_activo: 
                    conn.close()
                    QMessageBox.warning(self, "Bloqueado", "Usuario inactivo.")
                    return
                
                # B. Verificar Contraseña
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if input_hash == db_hash:
                    # C. Verificar Acceso a Empresa
                    if db_rol != "Administrador":
                        # --- CORRECCIÓN AQUÍ: Cambio de sys_acceso_empresas a seg_acceso_empresas ---
                        cur.execute("""
                            SELECT 1 FROM seg_acceso_empresas 
                            WHERE id_usuario = %s AND cod_compania = %s
                        """, (db_id, cod_empresa))
                        
                        if not cur.fetchone():
                            conn.close()
                            QMessageBox.warning(self, "Acceso Denegado", "No tiene permiso para ingresar a esta empresa.")
                            return

                    conn.close()
                    self.usuario_id = db_id
                    self.rol_usuario = db_rol
                    self.empresa_id = cod_empresa
                    self.nombre_empresa = nombre_empresa
                    self.nombre_completo = db_nombre if db_nombre else usuario
                    
                    self.accept()
                else:
                    conn.close()
                    QMessageBox.warning(self, "Error", "Contraseña incorrecta.")
            else:
                conn.close()
                QMessageBox.warning(self, "Error", "Usuario no encontrado.")
                
        except Exception as e:
            if 'conn' in locals() and conn: conn.close()
            QMessageBox.critical(self, "Error SQL", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginDialog()
    if login.exec() == QDialog.DialogCode.Accepted:
        menu = MenuPrincipal(
            cod_compania=login.empresa_id,
            id_usuario=login.usuario_id,
            nombre_empresa=login.nombre_empresa,
            rol_usuario=login.rol_usuario,
            nombre_real_usuario=login.nombre_completo 
        )
        menu.showMaximized() 
        sys.exit(app.exec())
    else:
        sys.exit()