import sys
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QListWidget, QDoubleSpinBox, QGroupBox, QApplication, QFrame,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator # <--- CAMBIO CLAVE
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

class EmpresasForm(QWidget):
    def __init__(self, id_usuario_actual):
        super().__init__()
        self.id_usuario_actual = id_usuario_actual
        self.rol_usuario = "Operador" 
        
        self.setWindowTitle("Configuración de Empresas (Multi-Tenant)")
        self.resize(1150, 720)
        
        self.id_empresa_seleccionada = None 
        
        self.verificar_permisos_usuario()
        self.apply_styles()
        self.init_ui()
        self.cargar_lista_empresas()
        self.cargar_catalogo_usuarios() 

    def verificar_permisos_usuario(self):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = "SELECT rol FROM seg_usuarios WHERE id_usuario = %s"
            cur.execute(query, (self.id_usuario_actual,))
            res = cur.fetchone()
            conn.close()
            
            if res:
                self.rol_usuario = res[0]
            else:
                self.rol_usuario = "Operador"
        except Exception as e:
            print(f"Error verificando permisos: {e}")
            self.rol_usuario = "Operador"

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
            
            QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; background-color: #FFFFFF;
            }
            QLineEdit:focus { border: 1px solid #007BFF; }
            QLineEdit:read-only { background-color: #E0E0E0; color: #555; }
            
            QListWidget, QTreeWidget {
                border: 1px solid #cccccc; background-color: white; border-radius: 4px;
                font-size: 11pt;
            }
            QListWidget::item, QTreeWidget::item { padding: 5px; }
            QListWidget::item:selected, QTreeWidget::item:selected { 
                background-color: #E6F3FF; color: #0056b3; border-left: 4px solid #007BFF; 
            }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout()

        # --- PANEL IZQUIERDO ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("🏢 Mis Empresas"))
        
        self.lista_empresas = QListWidget()
        self.lista_empresas.itemClicked.connect(self.cargar_datos_formulario)
        left_panel.addWidget(self.lista_empresas)
        
        self.btn_nueva = QPushButton("+ Nueva Empresa")
        self.btn_nueva.clicked.connect(self.limpiar_formulario)
        left_panel.addWidget(self.btn_nueva)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(280)
        main_layout.addWidget(left_widget)

        # --- PANEL DERECHO ---
        right_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.lbl_titulo_form = QLabel("Detalles de la Empresa")
        self.lbl_titulo_form.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header_layout.addWidget(self.lbl_titulo_form)
        
        lbl_permisos = QLabel(f"Rol Detectado: {self.rol_usuario}")
        color_p = "green" if self.rol_usuario == "Administrador" else "orange"
        lbl_permisos.setStyleSheet(f"color: {color_p}; font-weight: bold; border: 1px solid {color_p}; padding: 2px 5px; border-radius: 4px;")
        header_layout.addStretch()
        header_layout.addWidget(lbl_permisos)
        right_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()

        # TAB 1: DATOS GENERALES
        tab_general = QWidget()
        layout_gen = QHBoxLayout(tab_general)
        
        form_ident = QFormLayout()
        self.txt_razon_social = QLineEdit()
        form_ident.addRow("Razón Social *:", self.txt_razon_social)
        self.txt_rif = QLineEdit()
        self.txt_rif.setPlaceholderText("J-12345678-0")
        form_ident.addRow("RIF *:", self.txt_rif)
        self.txt_nit = QLineEdit()
        form_ident.addRow("NIT:", self.txt_nit)
        self.txt_telefono1 = QLineEdit()
        form_ident.addRow("Teléfono 1:", self.txt_telefono1)
        self.txt_telefono2 = QLineEdit()
        form_ident.addRow("Teléfono 2:", self.txt_telefono2)
        self.chk_estatus = QCheckBox("Empresa Activa")
        self.chk_estatus.setChecked(True)
        form_ident.addRow("Estado:", self.chk_estatus)

        form_ubic = QFormLayout()
        self.txt_pais = QLineEdit("Venezuela")
        form_ubic.addRow("País:", self.txt_pais)
        self.txt_estado = QLineEdit()
        form_ubic.addRow("Estado:", self.txt_estado)
        self.txt_ciudad = QLineEdit()
        form_ubic.addRow("Ciudad:", self.txt_ciudad)
        self.txt_municipio = QLineEdit()
        form_ubic.addRow("Municipio:", self.txt_municipio)
        self.txt_zona_postal = QLineEdit()
        form_ubic.addRow("Zona Postal:", self.txt_zona_postal)
        self.txt_direccion = QTextEdit()
        self.txt_direccion.setMaximumHeight(80)
        form_ubic.addRow("Dirección Fiscal:", self.txt_direccion)

        layout_gen.addLayout(form_ident)
        layout_gen.addLayout(form_ubic)
        self.tabs.addTab(tab_general, "Datos Generales")

        # TAB 2: DATOS FISCALES
        tab_fiscal = QWidget()
        form_fiscal = QFormLayout(tab_fiscal)
        self.cmb_tipo_contrib = QComboBox()
        self.cmb_tipo_contrib.addItems(["Jurídica", "Gubernamental", "Consejo Comunal", "Firma Personal"])
        form_fiscal.addRow("Tipo Contribuyente:", self.cmb_tipo_contrib)
        self.cmb_contrib_iva = QComboBox()
        self.cmb_contrib_iva.addItems(["Ordinario", "Especial", "Formal", "Exento"])
        form_fiscal.addRow("Condición IVA:", self.cmb_contrib_iva)
        self.txt_persona_fiscal = QLineEdit()
        self.txt_persona_fiscal.setPlaceholderText("Nombre del Representante Legal")
        form_fiscal.addRow("Persona Fiscal:", self.txt_persona_fiscal)
        self.txt_cod_contribuyente = QLineEdit()
        self.txt_cod_contribuyente.setPlaceholderText("Licencia de Actividad Económica")
        form_fiscal.addRow("Cód. Contribuyente (Alcaldía):", self.txt_cod_contribuyente)
        self.spin_patente = QDoubleSpinBox()
        self.spin_patente.setSuffix(" %")
        self.spin_patente.setRange(0, 100)
        form_fiscal.addRow("% Patente Municipal:", self.spin_patente)
        self.txt_ciiu = QLineEdit()
        self.txt_ciiu.setPlaceholderText("Ej: 4711 - Venta al por menor")
        form_fiscal.addRow("Código CIIU Principal:", self.txt_ciiu)

        self.tabs.addTab(tab_fiscal, "Datos Fiscales")
        
        # --- TAB 3: SEGURIDAD (SOLUCIÓN TREEWIDGET ROBUSTO) ---
        tab_seguridad = QWidget()
        layout_seg = QVBoxLayout(tab_seguridad)
        layout_seg.addWidget(QLabel("Seleccione los usuarios que tendrán acceso a esta empresa:"))
        
        # Usamos QTreeWidget en lugar de ListWidget para usar la misma técnica que en Usuarios
        self.arbol_usuarios = QTreeWidget()
        self.arbol_usuarios.setHeaderHidden(True) # Ocultamos cabecera para que parezca lista
        self.arbol_usuarios.setColumnCount(1)
        layout_seg.addWidget(self.arbol_usuarios)
        
        btn_todos = QPushButton("Marcar Todos")
        btn_todos.setFixedSize(100, 25)
        btn_todos.clicked.connect(lambda: self.marcar_usuarios(True))
        
        btn_ninguno = QPushButton("Desmarcar")
        btn_ninguno.setFixedSize(100, 25)
        btn_ninguno.clicked.connect(lambda: self.marcar_usuarios(False))
        
        layout_btns_seg = QHBoxLayout()
        layout_btns_seg.addWidget(btn_todos)
        layout_btns_seg.addWidget(btn_ninguno)
        layout_btns_seg.addStretch()
        layout_seg.addLayout(layout_btns_seg)
        
        self.tabs.addTab(tab_seguridad, "Seguridad / Acceso")
        
        right_layout.addWidget(self.tabs)

        # Auditoría
        frm_audit = QFrame()
        frm_audit.setStyleSheet("background-color: #E8E8E8; border-radius: 4px; margin-top: 5px;")
        layout_audit = QHBoxLayout(frm_audit)
        
        estilo_audit = "font-size: 10px; color: #555;"
        self.lbl_creado_por = QLabel("Creado por: -"); self.lbl_creado_por.setStyleSheet(estilo_audit)
        self.lbl_fecha_crea = QLabel("Fecha: -"); self.lbl_fecha_crea.setStyleSheet(estilo_audit)
        self.lbl_modif_por = QLabel("Modif. por: -"); self.lbl_modif_por.setStyleSheet(estilo_audit)
        self.lbl_fecha_mod = QLabel("Fecha: -"); self.lbl_fecha_mod.setStyleSheet(estilo_audit)
        
        layout_audit.addWidget(self.lbl_creado_por)
        layout_audit.addWidget(self.lbl_fecha_crea)
        layout_audit.addStretch()
        layout_audit.addWidget(self.lbl_modif_por)
        layout_audit.addWidget(self.lbl_fecha_mod)
        right_layout.addWidget(frm_audit)

        # Botones Principales
        btn_layout = QHBoxLayout()
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_eliminar.setStyleSheet("background-color: #d9534f; color: white;")
        self.btn_eliminar.clicked.connect(self.eliminar_empresa)
        
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.clicked.connect(self.guardar_empresa)
        
        if self.rol_usuario != "Administrador":
            self.btn_guardar.setEnabled(False)
            self.btn_eliminar.setEnabled(False)
            self.btn_nueva.setEnabled(False)
            self.btn_guardar.setText("Solo Lectura")
            self.btn_guardar.setToolTip("No tiene permisos de Administrador")
            self.btn_eliminar.setToolTip("No tiene permisos de Administrador")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addWidget(self.btn_guardar)
        right_layout.addLayout(btn_layout)
        
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    # --- LÓGICA ---

    def create_checkbox_widget(self, text):
        """Crea un widget contenedor con QCheckBox (Mismo método que UsuariosForm)"""
        widget = QWidget()
        chk = QCheckBox(text)
        layout = QHBoxLayout(widget)
        layout.addWidget(chk)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return widget, chk

    def cargar_catalogo_usuarios(self):
        """Carga usuarios usando QTreeWidget + setItemWidget para estabilidad total"""
        self.arbol_usuarios.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT id_usuario, usuario_login, nombre_completo FROM seg_usuarios WHERE estatus = TRUE ORDER BY usuario_login")
            usuarios = cur.fetchall()
            conn.close()
            
            for u in usuarios:
                # 1. Crear Item de Árbol
                item = QTreeWidgetItem()
                item.setData(0, Qt.ItemDataRole.UserRole, u[0]) # ID en columna 0
                self.arbol_usuarios.addTopLevelItem(item)
                
                # 2. Crear Widget Real con Checkbox
                container, chk = self.create_checkbox_widget(f"{u[1]} - {u[2]}")
                
                # 3. Incrustar en la celda
                self.arbol_usuarios.setItemWidget(item, 0, container)
                
        except Exception as e:
            print(f"Error cargando usuarios: {e}")

    def cargar_lista_empresas(self):
        self.lista_empresas.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT cod_compania, razon_social, rif FROM cfg_empresas ORDER BY cod_compania")
            empresas = cur.fetchall()
            conn.close()
            for emp in empresas:
                self.lista_empresas.addItem(f"{emp[1]} ({emp[2]})")
                self.lista_empresas.item(self.lista_empresas.count()-1).setData(Qt.ItemDataRole.UserRole, emp[0])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def cargar_datos_formulario(self, item):
        id_empresa = item.data(Qt.ItemDataRole.UserRole)
        self.id_empresa_seleccionada = id_empresa
        self.lbl_titulo_form.setText(f"Editando Empresa ID: {id_empresa}")
        
        # 1. Cargar Datos Generales
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = """
                SELECT e.razon_social, e.rif, e.nit, e.telefono1, e.telefono2, e.estatus,
                       e.pais, e.estado, e.ciudad, e.municipio, e.zona_postal, e.direccion,
                       e.tipo_contribuyente, e.tipo_contrib_iva, e.persona_fiscal, 
                       e.cod_contribuyente, e.porcentaje_patente,
                       u1.usuario_login as user_crea, e.fecha_registro,
                       u2.usuario_login as user_mod, e.fecha_modifica
                FROM cfg_empresas e
                LEFT JOIN seg_usuarios u1 ON e.id_user_crea = u1.id_usuario
                LEFT JOIN seg_usuarios u2 ON e.id_user_mod = u2.id_usuario
                WHERE e.cod_compania = %s
            """
            cur.execute(query, (id_empresa,))
            data = cur.fetchone()
            
            if data:
                self.txt_razon_social.setText(data[0])
                self.txt_rif.setText(data[1])
                self.txt_nit.setText(data[2] or "")
                self.txt_telefono1.setText(data[3] or "")
                self.txt_telefono2.setText(data[4] or "")
                self.chk_estatus.setChecked(data[5])
                self.txt_pais.setText(data[6] or "Venezuela")
                self.txt_estado.setText(data[7] or "")
                self.txt_ciudad.setText(data[8] or "")
                self.txt_municipio.setText(data[9] or "")
                self.txt_zona_postal.setText(data[10] or "")
                self.txt_direccion.setText(data[11] or "")
                self.cmb_tipo_contrib.setCurrentText(data[12] or "")
                self.cmb_contrib_iva.setCurrentText(data[13] or "")
                self.txt_persona_fiscal.setText(data[14] or "")
                self.txt_cod_contribuyente.setText(data[15] or "")
                self.spin_patente.setValue(float(data[16] or 0.0))
                
                self.lbl_creado_por.setText(f"Creado por: {data[17] or 'Sistema'}")
                self.lbl_fecha_crea.setText(f"Fecha: {str(data[18])[:16]}")
                self.lbl_modif_por.setText(f"Modif. por: {data[19] or '-'}")
                self.lbl_fecha_mod.setText(f"Fecha: {str(data[20])[:16]}")

            # 2. Cargar Acceso de Usuarios (Seguridad)
            self.marcar_usuarios(False) # Limpiar

            cur.execute("SELECT id_usuario FROM sys_acceso_empresas WHERE cod_compania = %s", (id_empresa,))
            usuarios_acceso = [row[0] for row in cur.fetchall()]
            
            # Recorrer árbol para marcar
            iterator = QTreeWidgetItemIterator(self.arbol_usuarios)
            while iterator.value():
                item_tree = iterator.value()
                uid = item_tree.data(0, Qt.ItemDataRole.UserRole)
                
                # Obtener el widget incrustado
                container = self.arbol_usuarios.itemWidget(item_tree, 0)
                if container and uid in usuarios_acceso:
                    chk = container.findChild(QCheckBox)
                    if chk: chk.setChecked(True)
                
                iterator += 1

            conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def marcar_usuarios(self, marcar):
        """Marca o desmarca los QCheckBox reales"""
        iterator = QTreeWidgetItemIterator(self.arbol_usuarios)
        while iterator.value():
            item = iterator.value()
            container = self.arbol_usuarios.itemWidget(item, 0)
            if container:
                chk = container.findChild(QCheckBox)
                if chk: chk.setChecked(marcar)
            iterator += 1

    def limpiar_formulario(self):
        self.id_empresa_seleccionada = None
        self.lbl_titulo_form.setText("Nueva Empresa")
        self.lista_empresas.clearSelection()
        for widget in self.findChildren(QLineEdit): widget.clear()
        self.txt_direccion.clear()
        self.chk_estatus.setChecked(True)
        self.spin_patente.setValue(0.0)
        self.txt_pais.setText("Venezuela")
        self.lbl_creado_por.setText("-"); self.lbl_fecha_crea.setText("-")
        self.lbl_modif_por.setText("-"); self.lbl_fecha_mod.setText("-")
        self.marcar_usuarios(False)

    def guardar_empresa(self):
        if self.rol_usuario != "Administrador":
            QMessageBox.warning(self, "Acceso Denegado", "Permisos insuficientes.")
            return

        razon = self.txt_razon_social.text().strip()
        rif = self.txt_rif.text().strip().upper()
        if not razon or not rif:
            QMessageBox.warning(self, "Datos", "Razón Social y RIF requeridos.")
            return

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            # 1. Guardar/Actualizar Empresa
            if self.id_empresa_seleccionada is None:
                query = """
                    INSERT INTO cfg_empresas (
                        razon_social, rif, nit, telefono1, telefono2, estatus,
                        pais, estado, ciudad, municipio, zona_postal, direccion,
                        tipo_contribuyente, tipo_contrib_iva, persona_fiscal, 
                        cod_contribuyente, porcentaje_patente, id_user_crea
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING cod_compania
                """
                params = (
                    razon, rif, self.txt_nit.text(), self.txt_telefono1.text(), self.txt_telefono2.text(), self.chk_estatus.isChecked(),
                    self.txt_pais.text(), self.txt_estado.text(), self.txt_ciudad.text(), self.txt_municipio.text(), self.txt_zona_postal.text(), self.txt_direccion.toPlainText(),
                    self.cmb_tipo_contrib.currentText(), self.cmb_contrib_iva.currentText(), self.txt_persona_fiscal.text(),
                    self.txt_cod_contribuyente.text(), self.spin_patente.value(), self.id_usuario_actual
                )
                cur.execute(query, params)
                self.id_empresa_seleccionada = cur.fetchone()[0]
            else:
                query = """
                    UPDATE cfg_empresas SET
                        razon_social=%s, rif=%s, nit=%s, telefono1=%s, telefono2=%s, estatus=%s,
                        pais=%s, estado=%s, ciudad=%s, municipio=%s, zona_postal=%s, direccion=%s,
                        tipo_contribuyente=%s, tipo_contrib_iva=%s, persona_fiscal=%s, 
                        cod_contribuyente=%s, porcentaje_patente=%s, id_user_mod=%s
                    WHERE cod_compania = %s
                """
                params = (
                    razon, rif, self.txt_nit.text(), self.txt_telefono1.text(), self.txt_telefono2.text(), self.chk_estatus.isChecked(),
                    self.txt_pais.text(), self.txt_estado.text(), self.txt_ciudad.text(), self.txt_municipio.text(), self.txt_zona_postal.text(), self.txt_direccion.toPlainText(),
                    self.cmb_tipo_contrib.currentText(), self.cmb_contrib_iva.currentText(), self.txt_persona_fiscal.text(),
                    self.txt_cod_contribuyente.text(), self.spin_patente.value(), self.id_usuario_actual, self.id_empresa_seleccionada
                )
                cur.execute(query, params)

            # 2. Guardar Acceso de Usuarios
            cur.execute("DELETE FROM sys_acceso_empresas WHERE cod_compania = %s", (self.id_empresa_seleccionada,))
            
            # Recorrer el ÁRBOL para guardar
            iterator = QTreeWidgetItemIterator(self.arbol_usuarios)
            while iterator.value():
                item = iterator.value()
                container = self.arbol_usuarios.itemWidget(item, 0)
                
                if container:
                    chk = container.findChild(QCheckBox)
                    if chk and chk.isChecked():
                        uid = item.data(0, Qt.ItemDataRole.UserRole)
                        cur.execute("INSERT INTO sys_acceso_empresas (id_usuario, cod_compania) VALUES (%s, %s)", (uid, self.id_empresa_seleccionada))
                iterator += 1

            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Guardado correctamente.")
            self.limpiar_formulario()
            self.cargar_lista_empresas()
            
        except psycopg2.Error as e:
            if "unique" in str(e).lower():
                QMessageBox.warning(self, "Duplicado", "Ya existe una empresa con ese RIF.")
            else:
                QMessageBox.critical(self, "Error SQL", f"{e.pgerror}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def eliminar_empresa(self):
        if self.rol_usuario != "Administrador": return
        if not self.id_empresa_seleccionada: return
        
        if QMessageBox.question(self, "Confirmar", "¿Eliminar empresa?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("DELETE FROM cfg_empresas WHERE cod_compania = %s", (self.id_empresa_seleccionada,))
                conn.commit()
                conn.close()
                self.limpiar_formulario()
                self.cargar_lista_empresas()
            except Exception as e:
                QMessageBox.critical(self, "Error", "No se puede eliminar (Tiene datos asociados).")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmpresasForm(1)
    window.show()
    sys.exit(app.exec())