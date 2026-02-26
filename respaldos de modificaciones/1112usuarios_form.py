import sys
import psycopg2
import hashlib
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QMessageBox, QListWidget, 
    QFrame, QApplication, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QTreeWidgetItemIterator
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

class UsuariosForm(QWidget):
    def __init__(self, id_usuario_actual):
        super().__init__()
        self.id_usuario_actual = id_usuario_actual
        self.rol_usuario_sesion = "Operador"
        
        self.setWindowTitle("Gestión de Usuarios y Perfiles de Acceso")
        self.resize(1200, 750)
        
        self.id_usuario_seleccionado = None
        
        self.verificar_permisos()
        self.apply_styles()
        self.init_ui()
        self.cargar_lista_usuarios()

    def verificar_permisos(self):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            # Validamos contra seg_usuarios (plural)
            cur.execute("SELECT rol FROM seg_usuarios WHERE id_usuario = %s", (self.id_usuario_actual,))
            res = cur.fetchone()
            conn.close()
            if res: self.rol_usuario_sesion = res[0]
        except Exception as e:
            print(f"Error permisos: {e}")

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
            
            QListWidget, QTreeWidget {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; font-size: 10pt; background-color: white;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #E6F3FF; color: #0056b3; border-left: 4px solid #007BFF; }
            
            QTreeWidget::item { padding: 4px; }
            QHeaderView::section { background-color: #E0E6ED; padding: 6px; border: none; font-weight: bold; }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout()

        # --- PANEL IZQUIERDO ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("👥 Lista de Usuarios"))
        
        self.lista_usuarios = QListWidget()
        self.lista_usuarios.itemClicked.connect(self.cargar_usuario)
        self.lista_usuarios.setMaximumHeight(200)
        left_panel.addWidget(self.lista_usuarios)
        
        self.btn_nuevo = QPushButton("+ Crear Nuevo Usuario")
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)
        left_panel.addWidget(self.btn_nuevo)
        
        left_panel.addSpacing(15)
        left_panel.addWidget(QLabel("📝 Datos de Identificación"))
        
        form_layout = QFormLayout()
        
        self.txt_login = QLineEdit()
        self.txt_login.setPlaceholderText("Ej: jperez")
        form_layout.addRow("Usuario (Login) *:", self.txt_login)
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre y Apellido")
        form_layout.addRow("Nombre Completo *:", self.txt_nombre)
        
        # CAMPO NUEVO: EMAIL
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("ejemplo@correo.com")
        form_layout.addRow("Correo Electrónico:", self.txt_email)
        
        self.cmb_rol = QComboBox()
        self.cmb_rol.addItems(["Operador", "Supervisor", "Administrador"])
        form_layout.addRow("Rol General:", self.cmb_rol)
        
        self.chk_activo = QCheckBox("Usuario Activo")
        self.chk_activo.setChecked(True)
        form_layout.addRow("Estado:", self.chk_activo)
        
        left_panel.addLayout(form_layout)
        
        # --- SECCIÓN CONTRASEÑA ---
        gb_pass = QFrame()
        gb_pass.setStyleSheet("border: 1px solid #ddd; border-radius: 4px; margin-top: 10px; padding: 5px;")
        layout_pass = QFormLayout(gb_pass)
        layout_pass.addRow(QLabel("<b>Seguridad</b>"))
        
        self.txt_pass1 = QLineEdit()
        self.txt_pass1.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass1.setPlaceholderText("Nueva contraseña")
        layout_pass.addRow("Contraseña:", self.txt_pass1)
        
        self.txt_pass2 = QLineEdit()
        self.txt_pass2.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass2.setPlaceholderText("Repetir contraseña")
        layout_pass.addRow("Repetir:", self.txt_pass2)
        
        left_panel.addWidget(gb_pass)
        
        self.lbl_audit = QLabel("Creado: - | Modif: -")
        self.lbl_audit.setStyleSheet("color: gray; font-size: 10px; margin-top: 5px;")
        left_panel.addWidget(self.lbl_audit)
        
        left_panel.addStretch()
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(380)
        main_layout.addWidget(left_widget)

        # --- PANEL DERECHO ---
        right_panel = QVBoxLayout()
        
        header_perm = QHBoxLayout()
        header_perm.addWidget(QLabel("🛡️ Permisología del Sistema"))
        header_perm.addStretch()
        
        btn_all = QPushButton("Marcar Todo")
        btn_all.setFixedSize(90, 25)
        btn_all.setStyleSheet("font-size: 10px; background-color: #6c757d;")
        btn_all.clicked.connect(lambda: self.marcar_arbol(True))
        
        btn_none = QPushButton("Desmarcar")
        btn_none.setFixedSize(80, 25)
        btn_none.setStyleSheet("font-size: 10px; background-color: #6c757d;")
        btn_none.clicked.connect(lambda: self.marcar_arbol(False))

        header_perm.addWidget(btn_all)
        header_perm.addWidget(btn_none)
        right_panel.addLayout(header_perm)

        self.tree_permisos = QTreeWidget()
        self.tree_permisos.setHeaderLabels(["Módulo / Sección", "Ver", "Crear", "Editar", "Eliminar"])
        self.tree_permisos.setColumnWidth(0, 220)
        for i in range(1, 5): self.tree_permisos.setColumnWidth(i, 70)
            
        right_panel.addWidget(self.tree_permisos)

        btns_layout = QHBoxLayout()
        self.btn_eliminar = QPushButton("Eliminar Usuario")
        self.btn_eliminar.setStyleSheet("background-color: #d9534f; color: white;")
        self.btn_eliminar.clicked.connect(self.eliminar_usuario)
        
        self.btn_guardar = QPushButton("GUARDAR CAMBIOS")
        self.btn_guardar.setFixedHeight(45)
        self.btn_guardar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_guardar.clicked.connect(self.guardar_usuario)

        if self.rol_usuario_sesion != "Administrador":
            self.btn_guardar.setEnabled(False)
            self.btn_eliminar.setEnabled(False)
            self.btn_nuevo.setEnabled(False)

        btns_layout.addWidget(self.btn_eliminar)
        btns_layout.addStretch()
        btns_layout.addWidget(self.btn_guardar)
        
        right_panel.addLayout(btns_layout)
        main_layout.addLayout(right_panel)
        self.setLayout(main_layout)

    # --- LÓGICA DE NEGOCIO ---

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validar_email(self, email):
        # Regex simple para validar email
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None

    def cargar_lista_usuarios(self):
        self.lista_usuarios.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            # Consulta a seg_usuarios
            cur.execute("SELECT id_usuario, usuario_login, nombre_completo FROM seg_usuarios ORDER BY id_usuario")
            for u in cur.fetchall():
                self.lista_usuarios.addItem(f"{u[1]} - {u[2]}")
                self.lista_usuarios.item(self.lista_usuarios.count()-1).setData(Qt.ItemDataRole.UserRole, u[0])
            conn.close()
            self.cargar_estructura_arbol()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando lista: {str(e)}")

    def create_checkbox_widget(self):
        widget = QWidget()
        chk = QCheckBox()
        layout = QHBoxLayout(widget)
        layout.addWidget(chk)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget, chk

    def cargar_estructura_arbol(self):
        self.tree_permisos.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT id_modulo, nombre_modulo, categoria FROM sys_moduser ORDER BY categoria, nombre_modulo")
            modulos = cur.fetchall()
            conn.close()

            categorias = {}
            for m in modulos:
                cat = m[2]
                if cat not in categorias:
                    parent = QTreeWidgetItem(self.tree_permisos)
                    parent.setText(0, cat.upper())
                    parent.setExpanded(True)
                    for c in range(5): parent.setBackground(c, QColor("#F2F2F2"))
                    categorias[cat] = parent
                
                child = QTreeWidgetItem(categorias[cat])
                child.setText(0, m[1])
                child.setData(0, Qt.ItemDataRole.UserRole, m[0]) 
                
                for col in range(1, 5):
                    container, chk = self.create_checkbox_widget()
                    self.tree_permisos.setItemWidget(child, col, container)
                    
        except Exception as e:
            print(f"Error cargando árbol: {e}")

    def cargar_usuario(self, item):
        uid = item.data(Qt.ItemDataRole.UserRole)
        self.id_usuario_seleccionado = uid
        self.cargar_estructura_arbol() 

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            # Consultamos seg_usuarios incluyendo email
            query = """
                SELECT u.usuario_login, u.nombre_completo, u.email, u.rol, u.estatus, 
                       u1.usuario_login, u.fecha_creacion, 
                       u2.usuario_login, u.fecha_modifica
                FROM seg_usuarios u
                LEFT JOIN seg_usuarios u1 ON u.id_user_crea = u1.id_usuario
                LEFT JOIN seg_usuarios u2 ON u.id_user_mod = u2.id_usuario
                WHERE u.id_usuario = %s
            """
            cur.execute(query, (uid,))
            data = cur.fetchone()
            
            if data:
                self.txt_login.setText(data[0]); self.txt_login.setReadOnly(True)
                self.txt_nombre.setText(data[1])
                self.txt_email.setText(data[2] if data[2] else "") # Cargar Email
                self.cmb_rol.setCurrentText(data[3] or "Operador")
                self.chk_activo.setChecked(data[4])
                
                f_crea = str(data[6])[:16] if data[6] else "-"
                f_mod = str(data[8])[:16] if data[8] else "-"
                self.lbl_audit.setText(f"Crea: {data[5] or '-'} ({f_crea}) | Mod: {data[7] or '-'} ({f_mod})")
                self.txt_pass1.clear(); self.txt_pass2.clear()

            cur.execute("SELECT id_modulo, p_ver, p_crear, p_editar, p_eliminar FROM sys_permisouser WHERE id_usuario = %s", (uid,))
            permisos_db = cur.fetchall()
            
            mapa_permisos = { row[0]: row[1:] for row in permisos_db }

            iterator = QTreeWidgetItemIterator(self.tree_permisos)
            while iterator.value():
                item_tree = iterator.value()
                id_mod = item_tree.data(0, Qt.ItemDataRole.UserRole)
                
                if id_mod and id_mod in mapa_permisos:
                    vals = mapa_permisos[id_mod]
                    for i in range(4):
                        col_idx = i + 1
                        container = self.tree_permisos.itemWidget(item_tree, col_idx)
                        if container:
                            chk = container.findChild(QCheckBox)
                            if chk: chk.setChecked(vals[i])
                iterator += 1
            conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando usuario: {str(e)}")

    def marcar_arbol(self, estado):
        iterator = QTreeWidgetItemIterator(self.tree_permisos)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole):
                for col in range(1, 5):
                    container = self.tree_permisos.itemWidget(item, col)
                    if container:
                        chk = container.findChild(QCheckBox)
                        if chk: chk.setChecked(estado)
            iterator += 1

    def limpiar_formulario(self):
        self.id_usuario_seleccionado = None
        self.txt_login.clear(); self.txt_login.setReadOnly(False)
        self.txt_nombre.clear()
        self.txt_email.clear()
        self.txt_pass1.clear(); self.txt_pass2.clear()
        self.lbl_audit.setText("Nuevo Usuario")
        self.cargar_estructura_arbol()

    def guardar_usuario(self):
        if self.rol_usuario_sesion != "Administrador": return
        
        login = self.txt_login.text().strip()
        nombre = self.txt_nombre.text().strip()
        email = self.txt_email.text().strip()
        p1 = self.txt_pass1.text()
        p2 = self.txt_pass2.text()
        
        # VALIDACIÓN 1: Campos requeridos
        if not login or not nombre: 
            QMessageBox.warning(self, "Datos incompletos", "El Usuario y Nombre Completo son obligatorios.")
            return

        # VALIDACIÓN 2: Email (si escribieron algo)
        if email and not self.validar_email(email):
            QMessageBox.warning(self, "Email inválido", "El formato del correo no es correcto.")
            return

        pass_hash = None
        
        # MODO CREAR
        if self.id_usuario_seleccionado is None:
            # VALIDACIÓN 3: Contraseña obligatoria al crear
            if not p1: 
                QMessageBox.warning(self, "Seguridad", "Debe asignar una contraseña al nuevo usuario.")
                return
            if p1 != p2:
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
                return
            
            pass_hash = self.hash_password(p1)
        
        # MODO EDITAR
        else:
            if p1: # Si escribió algo en el campo contraseña, quiere cambiarla
                if p1 != p2:
                    QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
                    return
                pass_hash = self.hash_password(p1)

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            new_id = self.id_usuario_seleccionado
            
            # Guardar Usuario
            if new_id is None:
                # VALIDACIÓN 4: Duplicados
                cur.execute("SELECT 1 FROM seg_usuarios WHERE usuario_login=%s", (login,))
                if cur.fetchone(): 
                    QMessageBox.warning(self, "Duplicado", f"El usuario '{login}' ya existe.")
                    conn.close()
                    return
                
                cur.execute("""
                    INSERT INTO seg_usuarios (usuario_login, nombre_completo, email, password_hash, rol, estatus, id_user_crea)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_usuario
                """, (login, nombre, email, pass_hash, self.cmb_rol.currentText(), self.chk_activo.isChecked(), self.id_usuario_actual))
                new_id = cur.fetchone()[0]
            else:
                if pass_hash:
                    cur.execute("""
                        UPDATE seg_usuarios SET nombre_completo=%s, email=%s, password_hash=%s, rol=%s, estatus=%s, id_user_mod=%s
                        WHERE id_usuario=%s
                    """, (nombre, email, pass_hash, self.cmb_rol.currentText(), self.chk_activo.isChecked(), self.id_usuario_actual, new_id))
                else:
                    cur.execute("""
                        UPDATE seg_usuarios SET nombre_completo=%s, email=%s, rol=%s, estatus=%s, id_user_mod=%s
                        WHERE id_usuario=%s
                    """, (nombre, email, self.cmb_rol.currentText(), self.chk_activo.isChecked(), self.id_usuario_actual, new_id))
            
            # Guardar Permisos
            cur.execute("DELETE FROM sys_permisouser WHERE id_usuario = %s", (new_id,))
            
            iterator = QTreeWidgetItemIterator(self.tree_permisos)
            while iterator.value():
                item = iterator.value()
                id_mod = item.data(0, Qt.ItemDataRole.UserRole)
                
                if id_mod: 
                    vals = []
                    for col in range(1, 5):
                        container = self.tree_permisos.itemWidget(item, col)
                        checked = False
                        if container:
                            chk = container.findChild(QCheckBox)
                            if chk: checked = chk.isChecked()
                        vals.append(checked)
                    
                    if any(vals):
                        cur.execute("""
                            INSERT INTO sys_permisouser (id_usuario, id_modulo, p_ver, p_crear, p_editar, p_eliminar)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (new_id, id_mod, vals[0], vals[1], vals[2], vals[3]))
                
                iterator += 1

            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Usuario guardado correctamente.")
            self.limpiar_formulario()
            self.cargar_lista_usuarios()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al guardar: {e}")

    def eliminar_usuario(self):
        if self.rol_usuario_sesion != "Administrador": return
        if not self.id_usuario_seleccionado: return
        if self.id_usuario_seleccionado == self.id_usuario_actual:
            QMessageBox.warning(self, "Error", "No puedes auto-eliminarte.")
            return

        if QMessageBox.question(self, "Confirmar", "¿Eliminar usuario definitivamente?") == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("DELETE FROM seg_usuarios WHERE id_usuario=%s", (self.id_usuario_seleccionado,))
                conn.commit()
                conn.close()
                self.limpiar_formulario()
                self.cargar_lista_usuarios()
            except Exception as e:
                QMessageBox.critical(self, "Error", "No se puede eliminar (posiblemente tenga registros asociados).")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UsuariosForm(1)
    window.show()
    sys.exit(app.exec())