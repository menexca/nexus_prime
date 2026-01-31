import sys
import psycopg2
import hashlib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QMessageBox, QListWidget, 
    QFrame, QApplication, QFormLayout
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

class UsuariosForm(QWidget):
    def __init__(self, id_usuario_actual):
        super().__init__()
        self.id_usuario_actual = id_usuario_actual
        self.rol_usuario_sesion = "Operador" # Default seguro
        
        self.setWindowTitle("Gestión de Usuarios y Seguridad")
        self.resize(1000, 650)
        
        self.id_usuario_seleccionado = None
        
        self.verificar_permisos() # <--- Paso Crítico
        self.apply_styles()
        self.init_ui()
        self.cargar_lista_usuarios()

    def verificar_permisos(self):
        """Consulta el rol real en la base de datos"""
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = "SELECT rol FROM usuarios_sistema WHERE id_usuario = %s"
            cur.execute(query, (self.id_usuario_actual,))
            res = cur.fetchone()
            conn.close()
            
            if res:
                self.rol_usuario_sesion = res[0]
                print(f"DEBUG: Rol detectado para usuario {self.id_usuario_actual}: {self.rol_usuario_sesion}")
            else:
                print("DEBUG: No se encontró el usuario actual en BD.")
                
        except Exception as e:
            print(f"Error crítico verificando permisos: {e}")
            QMessageBox.critical(self, "Error DB", "No se pudieron verificar los permisos.")

    def apply_styles(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F0F2F5"))
        self.setPalette(palette)
        self.setFont(QFont("Segoe UI", 10))
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #007BFF; color: white; border-radius: 5px;
                padding: 8px 15px; border: none; font-weight: bold;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
            
            QLineEdit, QComboBox {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; background-color: white;
            }
            QLineEdit:focus { border: 1px solid #007BFF; }
            QLineEdit:read-only { background-color: #E0E0E0; color: #555; }
            
            QListWidget {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; font-size: 11pt;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #E6F3FF; color: #0056b3; border-left: 4px solid #007BFF; }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout()

        # --- PANEL IZQUIERDO ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("👥 Usuarios"))
        
        self.lista_usuarios = QListWidget()
        self.lista_usuarios.itemClicked.connect(self.cargar_usuario)
        left_layout.addWidget(self.lista_usuarios)
        
        self.btn_nuevo = QPushButton("+ Nuevo Usuario")
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)
        left_layout.addWidget(self.btn_nuevo)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(280)
        main_layout.addWidget(left_widget)

        # --- PANEL DERECHO ---
        right_layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        lbl_titulo = QLabel("Ficha de Seguridad")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header.addWidget(lbl_titulo)
        
        # Indicador Visual de Permisos
        lbl_rol = QLabel(f"Tu Rol: {self.rol_usuario_sesion}")
        es_admin = self.rol_usuario_sesion == "Administrador"
        color = "green" if es_admin else "orange"
        lbl_rol.setStyleSheet(f"color: {color}; font-weight: bold; border: 1px solid {color}; padding: 4px; border-radius: 4px;")
        header.addStretch()
        header.addWidget(lbl_rol)
        right_layout.addLayout(header)
        
        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.txt_login = QLineEdit()
        self.txt_login.setPlaceholderText("Ej: jperez")
        form_layout.addRow("Usuario (Login) *:", self.txt_login)
        
        self.txt_nombre = QLineEdit()
        form_layout.addRow("Nombre Completo *:", self.txt_nombre)
        
        self.cmb_rol = QComboBox()
        self.cmb_rol.addItems(["Operador", "Supervisor", "Administrador"])
        form_layout.addRow("Nivel de Acceso:", self.cmb_rol)
        
        self.chk_activo = QCheckBox("Usuario Activo")
        self.chk_activo.setChecked(True)
        form_layout.addRow("Estado:", self.chk_activo)
        
        # Passwords
        lbl_pass = QLabel("Seguridad")
        lbl_pass.setStyleSheet("font-weight: bold; color: #0056b3; margin-top: 10px;")
        form_layout.addRow(lbl_pass)
        
        self.txt_pass1 = QLineEdit()
        self.txt_pass1.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass1.setPlaceholderText("Nueva contraseña")
        form_layout.addRow("Contraseña:", self.txt_pass1)
        
        self.txt_pass2 = QLineEdit()
        self.txt_pass2.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass2.setPlaceholderText("Confirmar")
        form_layout.addRow("Repetir:", self.txt_pass2)
        
        right_layout.addLayout(form_layout)
        right_layout.addStretch()

        # Auditoría
        frm_audit = QFrame()
        frm_audit.setStyleSheet("background-color: #E8E8E8; border-radius: 4px;")
        audit_layout = QHBoxLayout(frm_audit)
        
        estilo = "font-size: 10px; color: #555;"
        self.lbl_creado = QLabel("Creado por: -"); self.lbl_creado.setStyleSheet(estilo)
        self.lbl_fcrea = QLabel("Fecha: -"); self.lbl_fcrea.setStyleSheet(estilo)
        self.lbl_modif = QLabel("Modif: -"); self.lbl_modif.setStyleSheet(estilo)
        self.lbl_fmod = QLabel("Fecha: -"); self.lbl_fmod.setStyleSheet(estilo)
        
        audit_layout.addWidget(self.lbl_creado); audit_layout.addWidget(self.lbl_fcrea)
        audit_layout.addStretch()
        audit_layout.addWidget(self.lbl_modif); audit_layout.addWidget(self.lbl_fmod)
        right_layout.addWidget(frm_audit)

        # Botonera
        btns = QHBoxLayout()
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_eliminar.setStyleSheet("background-color: #d9534f; color: white;")
        self.btn_eliminar.clicked.connect(self.eliminar_usuario)
        
        self.btn_guardar = QPushButton("Guardar Usuario")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.clicked.connect(self.guardar_usuario)
        
        # LOGICA DE BLOQUEO DE SEGURIDAD
        if not es_admin:
            self.btn_guardar.setEnabled(False)
            self.btn_eliminar.setEnabled(False)
            self.btn_nuevo.setEnabled(False)
            self.btn_guardar.setText("Solo Lectura")
            self.btn_guardar.setToolTip("Su usuario actual no tiene permiso de Administrador")

        btns.addStretch()
        btns.addWidget(self.btn_eliminar)
        btns.addWidget(self.btn_guardar)
        right_layout.addLayout(btns)
        
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    # --- LÓGICA ---
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def cargar_lista_usuarios(self):
        self.lista_usuarios.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT id_usuario, usuario_login, nombre_completo FROM usuarios_sistema ORDER BY id_usuario")
            users = cur.fetchall()
            conn.close()
            for u in users:
                self.lista_usuarios.addItem(f"{u[1]} - {u[2]}")
                self.lista_usuarios.item(self.lista_usuarios.count()-1).setData(Qt.ItemDataRole.UserRole, u[0])
        except Exception as e:
            QMessageBox.critical(self, "Error Carga", str(e))

    def cargar_usuario(self, item):
        uid = item.data(Qt.ItemDataRole.UserRole)
        self.id_usuario_seleccionado = uid
        
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = """
                SELECT u.usuario_login, u.nombre_completo, u.rol, u.estatus,
                       ua.usuario_login, u.fecha_creacion,
                       ub.usuario_login, u.fecha_modifica
                FROM usuarios_sistema u
                LEFT JOIN usuarios_sistema ua ON u.id_user_crea = ua.id_usuario
                LEFT JOIN usuarios_sistema ub ON u.id_user_mod = ub.id_usuario
                WHERE u.id_usuario = %s
            """
            cur.execute(query, (uid,))
            data = cur.fetchone()
            conn.close()
            
            if data:
                self.txt_login.setText(data[0])
                self.txt_login.setReadOnly(True)
                self.txt_nombre.setText(data[1] or "")
                
                # Seleccionar rol en combo (Manejo de errores si el rol no está en la lista)
                index = self.cmb_rol.findText(data[2] or "Operador", Qt.MatchFlag.MatchFixedString)
                if index >= 0:
                    self.cmb_rol.setCurrentIndex(index)
                    
                self.chk_activo.setChecked(data[3])
                
                # Auditoría
                self.lbl_creado.setText(f"Creado por: {data[4] or 'Sistema'}")
                self.lbl_fcrea.setText(f"Fecha: {str(data[5])[:16]}")
                self.lbl_modif.setText(f"Modif: {data[6] or '-'}")
                self.lbl_fmod.setText(f"Fecha: {str(data[7])[:16]}")
                
                self.txt_pass1.clear()
                self.txt_pass2.clear()

        except Exception as e:
            QMessageBox.critical(self, "Error Carga Detalle", str(e))

    def limpiar_formulario(self):
        self.id_usuario_seleccionado = None
        self.txt_login.clear()
        self.txt_login.setReadOnly(False)
        self.txt_nombre.clear()
        self.txt_pass1.clear()
        self.txt_pass2.clear()
        self.chk_activo.setChecked(True)
        self.cmb_rol.setCurrentIndex(0)
        self.lbl_creado.setText("Creado por: -"); self.lbl_fcrea.setText("Fecha: -")
        self.lbl_modif.setText("Modif: -"); self.lbl_fmod.setText("Fecha: -")

    def guardar_usuario(self):
        # Doble chequeo de seguridad
        if self.rol_usuario_sesion != "Administrador":
            QMessageBox.warning(self, "Acceso Denegado", "No tiene permiso de Administrador.")
            return

        login = self.txt_login.text().strip()
        nombre = self.txt_nombre.text().strip()
        p1 = self.txt_pass1.text()
        p2 = self.txt_pass2.text()
        
        if not login or not nombre:
            QMessageBox.warning(self, "Validación", "Login y Nombre son obligatorios.")
            return

        nueva_pass_hash = None
        if self.id_usuario_seleccionado is None:
            # Creando
            if not p1:
                QMessageBox.warning(self, "Validación", "Contraseña obligatoria para nuevo usuario.")
                return
            if p1 != p2:
                QMessageBox.warning(self, "Validación", "Las contraseñas no coinciden.")
                return
            nueva_pass_hash = self.hash_password(p1)
        else:
            # Editando
            if p1:
                if p1 != p2:
                    QMessageBox.warning(self, "Validación", "Las contraseñas no coinciden.")
                    return
                nueva_pass_hash = self.hash_password(p1)

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            if self.id_usuario_seleccionado is None:
                # Verificar duplicado
                cur.execute("SELECT 1 FROM usuarios_sistema WHERE usuario_login = %s", (login,))
                if cur.fetchone():
                    QMessageBox.warning(self, "Duplicado", f"El usuario '{login}' ya existe.")
                    conn.close(); return

                query = """
                    INSERT INTO usuarios_sistema (usuario_login, nombre_completo, password_hash, rol, estatus, id_user_crea)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cur.execute(query, (login, nombre, nueva_pass_hash, self.cmb_rol.currentText(), self.chk_activo.isChecked(), self.id_usuario_actual))
            
            else:
                if nueva_pass_hash:
                    query = """
                        UPDATE usuarios_sistema SET 
                        nombre_completo=%s, password_hash=%s, rol=%s, estatus=%s, id_user_mod=%s
                        WHERE id_usuario=%s
                    """
                    params = (nombre, nueva_pass_hash, self.cmb_rol.currentText(), self.chk_activo.isChecked(), self.id_usuario_actual, self.id_usuario_seleccionado)
                else:
                    query = """
                        UPDATE usuarios_sistema SET 
                        nombre_completo=%s, rol=%s, estatus=%s, id_user_mod=%s
                        WHERE id_usuario=%s
                    """
                    params = (nombre, self.cmb_rol.currentText(), self.chk_activo.isChecked(), self.id_usuario_actual, self.id_usuario_seleccionado)
                
                cur.execute(query, params)

            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Éxito", "Usuario guardado correctamente.")
            self.limpiar_formulario()
            self.cargar_lista_usuarios()
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error SQL", f"No se pudo guardar:\n{e.pgerror}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def eliminar_usuario(self):
        if self.rol_usuario_sesion != "Administrador": return
        if not self.id_usuario_seleccionado: return
        
        if self.id_usuario_seleccionado == self.id_usuario_actual:
            QMessageBox.warning(self, "Seguridad", "No puedes eliminar tu propio usuario.")
            return

        res = QMessageBox.question(self, "Confirmar", "¿Eliminar usuario definitivamente?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("DELETE FROM usuarios_sistema WHERE id_usuario=%s", (self.id_usuario_seleccionado,))
                conn.commit()
                conn.close()
                self.limpiar_formulario()
                self.cargar_lista_usuarios()
            except Exception as e:
                QMessageBox.critical(self, "Error Integridad", "Este usuario ha realizado operaciones (crear empresas/proveedores).\nNo se puede eliminar para preservar la auditoría.\n\nSugerencia: Cambie su estado a Inactivo.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UsuariosForm(id_usuario_actual=1)
    window.show()
    sys.exit(app.exec())