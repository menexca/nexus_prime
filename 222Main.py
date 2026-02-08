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
            # Tabla correcta: cfg_empresas
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
            

            

            # 1. Obtener credenciales del usuario
            query = "SELECT id_usuario, password_hash, rol, estatus FROM seg_usuarios WHERE usuario_login = %s"
            cur.execute(query, (usuario,))
            data = cur.fetchone()
            
            if data:
                db_id, db_hash, db_rol, db_activo = data
                
                # A. Verificar Estatus Global
                if not db_activo:
                    conn.close()
                    QMessageBox.warning(self, "Bloqueado", "Usuario inactivo en el sistema.")
                    return
                
                # B. Verificar Contraseña
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if input_hash == db_hash:
                    # C. VERIFICAR ACCESO A LA EMPRESA (NUEVO)
                    # Si NO es Administrador, debe estar explícitamente en la tabla sys_acceso_empresas
                    if db_rol != "Administrador":
                        cur.execute("""
                            SELECT 1 FROM sys_acceso_empresas 
                            WHERE id_usuario = %s AND cod_compania = %s
                        """, (db_id, cod_empresa))
                        
                        acceso = cur.fetchone()
                        if not acceso:
                            conn.close()
                            QMessageBox.warning(self, "Acceso Denegado", 
                                f"El usuario '{usuario}' no tiene permiso para acceder a\n{nombre_empresa}")
                            return

                    # --- LOGIN EXITOSO ---
                    conn.close()
                    self.usuario_id = db_id
                    self.rol_usuario = db_rol
                    self.empresa_id = cod_empresa
                    self.nombre_empresa = nombre_empresa
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
            rol_usuario=login.rol_usuario
        )
        menu.showMaximized() 
        sys.exit(app.exec())
    else:
        sys.exit()