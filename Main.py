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
        self.setFixedSize(350, 480) # Aumenté un poco el alto para que respire mejor
        
        # --- SOLUCIÓN VISUAL COMPLETA ---
        # Definimos una hoja de estilos global para este diálogo.
        # Esto fuerza a TODOS los elementos a usar fondo blanco y letras oscuras.
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: white;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #007BFF;
            }
            QComboBox {
                background-color: white;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
            }
            QComboBox:on { /* Cuando se despliega */
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            /* ESTO ARREGLA LA LISTA DESPLEGABLE */
            QComboBox QAbstractItemView {
                background-color: white;
                color: #333333;
                selection-background-color: #007BFF;
                selection-color: white;
                outline: 0px;
            }
            QPushButton { 
                background-color: #007BFF; 
                color: white; 
                padding: 12px; 
                font-weight: bold; 
                border-radius: 4px; 
                border: none; 
            }
            QPushButton:hover { 
                background-color: #0056b3; 
            }
            QPushButton:pressed {
                background-color: #004494;
            }
        """)
        
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
        
        # Título (sobrescribimos el tamaño de fuente del estilo global solo para este)
        lbl_titulo = QLabel("Bienvenido")
        lbl_titulo.setStyleSheet("font-size: 24px; color: #333333;") 
        layout.addWidget(lbl_titulo)
        
        layout.addWidget(QLabel("Empresa:"))
        self.cmb = QComboBox()
        # El estilo ya está definido en el setStyleSheet del __init__
        layout.addWidget(self.cmb)
        
        layout.addWidget(QLabel("Usuario:"))
        self.user = QLineEdit()
        self.user.setPlaceholderText("Ej: admin")
        layout.addWidget(self.user)
        
        layout.addWidget(QLabel("Contraseña:"))
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.user.returnPressed.connect(self.pwd.setFocus) 
        self.pwd.returnPressed.connect(self.validar) 
        layout.addWidget(self.pwd)
        
        btn = QPushButton("INICIAR SESIÓN")
        btn.setAutoDefault(False) 
        btn.setDefault(False)     
        btn.setCursor(Qt.CursorShape.PointingHandCursor) 
        # El estilo del botón también está arriba, limpiando el código aquí
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
            
            # Query corregida para incluir nombre_completo
            query = "SELECT id_usuario, password_hash, rol, estatus, nombre_completo FROM seg_usuarios WHERE usuario_login = %s"
            cur.execute(query, (usuario,))
            data = cur.fetchone()
            
            if data:
                db_id, db_hash, db_rol, db_activo, db_nombre = data
                
                # Verificación de estatus (Asumiendo booleano True/False)
                if not db_activo: 
                    conn.close()
                    QMessageBox.warning(self, "Bloqueado", "Usuario inactivo.")
                    return
                
                # Verificación de contraseña
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if input_hash == db_hash:
                    # Verificación de acceso a empresa
                    if db_rol != "Administrador":
                        cur.execute("""
                            SELECT 1 FROM sys_acceso_empresas 
                            WHERE id_usuario = %s AND cod_compania = %s
                        """, (db_id, cod_empresa))
                        
                        if not cur.fetchone():
                            conn.close()
                            QMessageBox.warning(self, "Acceso Denegado", "No tiene permiso para esta empresa.")
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

