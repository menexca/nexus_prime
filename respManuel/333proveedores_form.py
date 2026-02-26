import sys
import psycopg2
import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QListWidget, QFrame, QApplication
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

class ProveedorForm(QWidget):
    def __init__(self, cod_compania, id_usuario_actual, nombre_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.id_usuario_actual = id_usuario_actual
        self.nombre_empresa = nombre_empresa
        self.rol_usuario = "Operador"
        
        self.setWindowTitle(f"Maestro de Proveedores - {self.nombre_empresa}")
        self.resize(1150, 720)
        
        self.cod_proveedor_seleccionado = None
        
        self.verificar_permisos_usuario()
        self.apply_styles()
        self.init_ui()
        self.cargar_lista_proveedores()
        
        self.cancelar_accion()

    def verificar_permisos_usuario(self):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT rol FROM seg_usuarios WHERE id_usuario = %s", (self.id_usuario_actual,))
            res = cur.fetchone()
            conn.close()
            if res: self.rol_usuario = res[0]
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
            
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; background-color: #FFFFFF;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #007BFF; }
            QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled { 
                background-color: #E9ECEF; color: #6C757D; 
            }
            QLineEdit:read-only { background-color: #E0E0E0; color: #555; }
            
            QListWidget {
                border: 1px solid #cccccc; background-color: white; border-radius: 4px; font-size: 11pt;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { 
                background-color: #E6F3FF; color: #0056b3; border-left: 4px solid #007BFF; 
            }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout()

        # --- PANEL IZQUIERDO ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("🚛 Mis Proveedores"))
        
        # --- NUEVO: BARRA DE BÚSQUEDA ---
        layout_buscar = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar nombre o RIF...")
        # Permitir buscar al presionar Enter
        self.txt_buscar.returnPressed.connect(self.cargar_lista_proveedores) 
        
        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setStyleSheet("background-color: #6c757d; color: white; padding: 6px; font-size: 11px;")
        self.btn_buscar.clicked.connect(self.cargar_lista_proveedores)
        
        layout_buscar.addWidget(self.txt_buscar)
        layout_buscar.addWidget(self.btn_buscar)
        left_panel.addLayout(layout_buscar)
        # --------------------------------
        
        self.lista_proveedores = QListWidget()
        self.lista_proveedores.itemClicked.connect(self.cargar_datos_formulario)
        left_panel.addWidget(self.lista_proveedores)
        
        self.btn_nuevo = QPushButton("+ Nuevo Proveedor")
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)
        left_panel.addWidget(self.btn_nuevo)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(280)
        main_layout.addWidget(left_widget)

        # --- PANEL DERECHO ---
        right_layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        self.lbl_titulo_form = QLabel("Detalles del Proveedor")
        self.lbl_titulo_form.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header_layout.addWidget(self.lbl_titulo_form)
        
        lbl_permisos = QLabel(f"Rol: {self.rol_usuario}")
        color_p = "green" if self.rol_usuario == "Administrador" else "orange"
        lbl_permisos.setStyleSheet(f"color: {color_p}; font-weight: bold; border: 1px solid {color_p}; padding: 2px 5px; border-radius: 4px;")
        header_layout.addStretch()
        header_layout.addWidget(lbl_permisos)
        right_layout.addLayout(header_layout)

        # PESTAÑAS
        self.tabs = QTabWidget()

        # TAB 1: DATOS GENERALES
        tab_general = QWidget()
        form_gen = QFormLayout(tab_general)
        self.txt_cod_proveedor = QLineEdit()
        self.txt_cod_proveedor.setPlaceholderText("Ej: PROV-001 (Único)")
        form_gen.addRow("Cód. Proveedor *:", self.txt_cod_proveedor)
        self.txt_nombre = QLineEdit()
        form_gen.addRow("Razón Social *:", self.txt_nombre)
        self.cmb_tipo_prov = QComboBox()
        self.cmb_tipo_prov.addItems(["Nacional", "Internacional", "Servicios", "Insumos", "Otros"])
        form_gen.addRow("Tipo Proveedor:", self.cmb_tipo_prov)
        self.txt_rif = QLineEdit()
        self.txt_rif.setPlaceholderText("J-12345678-0")
        form_gen.addRow("RIF *:", self.txt_rif)
        self.txt_nit = QLineEdit()
        form_gen.addRow("NIT:", self.txt_nit)
        self.chk_estatus = QCheckBox("Proveedor Activo")
        self.chk_estatus.setChecked(True)
        form_gen.addRow("Estado:", self.chk_estatus)
        self.tabs.addTab(tab_general, "📋 Datos Generales")

        # TAB 2: CONTACTO Y UBICACIÓN
        tab_contacto = QWidget()
        form_cont = QFormLayout(tab_contacto)
        self.txt_contacto1 = QLineEdit(); form_cont.addRow("Contacto Ppal:", self.txt_contacto1)
        self.txt_contacto2 = QLineEdit(); form_cont.addRow("Contacto Alt:", self.txt_contacto2)
        self.txt_telefono1 = QLineEdit(); form_cont.addRow("Teléfono 1:", self.txt_telefono1)
        self.txt_telefono2 = QLineEdit(); form_cont.addRow("Teléfono 2:", self.txt_telefono2)
        self.txt_email1 = QLineEdit(); form_cont.addRow("Email 1:", self.txt_email1)
        self.txt_email2 = QLineEdit(); form_cont.addRow("Email 2:", self.txt_email2)
        self.txt_fax = QLineEdit(); form_cont.addRow("Fax:", self.txt_fax)
        self.txt_zona = QLineEdit(); form_cont.addRow("Zona / Ruta:", self.txt_zona)
        self.txt_direccion = QTextEdit(); self.txt_direccion.setMaximumHeight(50)
        form_cont.addRow("Dirección Ppal:", self.txt_direccion)
        self.txt_direccion_alt = QTextEdit(); self.txt_direccion_alt.setMaximumHeight(50)
        form_cont.addRow("Dirección Alt:", self.txt_direccion_alt)
        self.tabs.addTab(tab_contacto, "📞 Contacto y Ubicación")

        # TAB 3: FISCAL Y TRIBUTARIO
        tab_fiscal = QWidget()
        form_fisc = QFormLayout(tab_fiscal)
        self.cmb_tipo_persona = QComboBox(); self.cmb_tipo_persona.addItems(["Jurídica", "Natural"])
        form_fisc.addRow("Tipo Persona:", self.cmb_tipo_persona)
        self.cmb_tipo_contrib = QComboBox(); self.cmb_tipo_contrib.addItems(["Ordinario", "Especial", "Formal"])
        form_fisc.addRow("Tipo Contribuyente:", self.cmb_tipo_contrib)
        self.txt_figura_trib = QLineEdit(); form_fisc.addRow("Figura Tributaria:", self.txt_figura_trib)
        self.txt_reg_unico = QLineEdit(); form_fisc.addRow("Registro Único:", self.txt_reg_unico)
        self.txt_cod_retencion = QLineEdit(); form_fisc.addRow("Cód. Retención ISLR:", self.txt_cod_retencion)
        self.chk_retencion_iva = QCheckBox("Sujeto a Retención IVA")
        form_fisc.addRow("", self.chk_retencion_iva)
        self.chk_contrib_iva = QCheckBox("Es Contribuyente IVA"); self.chk_contrib_iva.setChecked(True)
        form_fisc.addRow("", self.chk_contrib_iva)
        self.tabs.addTab(tab_fiscal, "🏛️ Datos Fiscales")

        # TAB 4: BANCARIO Y CONTABLE
        tab_banco = QWidget()
        form_banc = QFormLayout(tab_banco)
        self.cmb_forma_pago = QComboBox(); self.cmb_forma_pago.addItems(["Transferencia", "Efectivo", "Cheque", "Crédito", "Zelle"])
        form_banc.addRow("Forma de Pago Ppal:", self.cmb_forma_pago)
        self.txt_banco = QLineEdit(); form_banc.addRow("Nombre del Banco:", self.txt_banco)
        self.txt_cuenta = QLineEdit(); form_banc.addRow("Número de Cuenta:", self.txt_cuenta)
        self.txt_beneficiario = QLineEdit(); form_banc.addRow("Beneficiario:", self.txt_beneficiario)
        
        lbl_linea = QLabel("<hr>")
        form_banc.addRow(lbl_linea)
        
        self.txt_gastos = QLineEdit(); form_banc.addRow("Cuenta de Gastos:", self.txt_gastos)
        self.txt_anticipos = QLineEdit(); form_banc.addRow("Cuenta Anticipos:", self.txt_anticipos)
        self.txt_cxp = QLineEdit(); form_banc.addRow("Cuenta CxP:", self.txt_cxp)
        self.txt_lineas = QLineEdit(); form_banc.addRow("Líneas de Crédito/Prod:", self.txt_lineas)
        self.tabs.addTab(tab_banco, "💰 Contabilidad y Banco")

        # TAB 5: OBSERVACIONES
        tab_obs = QWidget()
        layout_obs = QVBoxLayout(tab_obs)
        self.txt_comentario = QTextEdit()
        layout_obs.addWidget(QLabel("Comentarios Internos:"))
        layout_obs.addWidget(self.txt_comentario)
        self.tabs.addTab(tab_obs, "📝 Observaciones")

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
        self.btn_eliminar.setFixedHeight(40)
        self.btn_eliminar.clicked.connect(self.eliminar_proveedor)
        
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setStyleSheet("background-color: #6c757d; color: white;")
        self.btn_cancelar.setFixedHeight(40)
        self.btn_cancelar.clicked.connect(self.cancelar_accion)
        
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_guardar.clicked.connect(self.guardar_proveedor)
        
        self.btn_salir = QPushButton("Salir")
        self.btn_salir.setFixedHeight(40)
        self.btn_salir.setStyleSheet("background-color: #343a40; color: white; font-weight: bold;")
        self.btn_salir.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_salir)
        
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    # --- LÓGICA DE ESTADOS Y UI ---
    def set_estado_formulario(self, activo):
        if self.rol_usuario != "Administrador":
            activo = False
            self.btn_guardar.setText("Solo Lectura")
            self.btn_eliminar.setToolTip("Sin Permisos")
            
        for widget in self.findChildren(QLineEdit): 
            # No desactivar la barra de búsqueda nunca
            if widget != self.txt_buscar:
                widget.setEnabled(activo)
                
        for widget in self.findChildren(QComboBox): widget.setEnabled(activo)
        for widget in self.findChildren(QCheckBox): widget.setEnabled(activo)
        for widget in self.findChildren(QTextEdit): widget.setEnabled(activo)
        
        self.btn_guardar.setEnabled(activo)
        self.btn_cancelar.setEnabled(activo)
        
        if activo and self.cod_proveedor_seleccionado is not None:
            self.btn_eliminar.setEnabled(True)
            self.txt_cod_proveedor.setReadOnly(True) # No se cambia la PK
        else:
            self.btn_eliminar.setEnabled(False)
            self.txt_cod_proveedor.setReadOnly(False)

    def cancelar_accion(self):
        self.cod_proveedor_seleccionado = None
        self.lbl_titulo_form.setText("Seleccione un proveedor o cree uno nuevo")
        self.lista_proveedores.clearSelection()
        
        for widget in self.findChildren(QLineEdit): 
            if widget != self.txt_buscar: # No borrar la búsqueda al cancelar
                widget.clear()
                
        for widget in self.findChildren(QTextEdit): widget.clear()
        self.chk_estatus.setChecked(True)
        self.chk_contrib_iva.setChecked(True)
        self.chk_retencion_iva.setChecked(False)
        self.tabs.setCurrentIndex(0)
        
        self.lbl_creado_por.setText("Creado por: -"); self.lbl_fecha_crea.setText("Fecha: -")
        self.lbl_modif_por.setText("Modif. por: -"); self.lbl_fecha_mod.setText("Fecha: -")
        self.set_estado_formulario(False)

    def limpiar_formulario(self):
        self.cancelar_accion()
        self.lbl_titulo_form.setText("Nuevo Proveedor")
        self.set_estado_formulario(True)

    def validar_rif(self, rif):
        pattern = r"^[JVEGPC]-\d{5,9}(-\d)?$"
        return re.match(pattern, rif) is not None

    # --- LÓGICA DE BASE DE DATOS ---
    
    # --- ACTUALIZADO: BÚSQUEDA INTEGRADA ---
    def cargar_lista_proveedores(self):
        self.lista_proveedores.clear()
        filtro = self.txt_buscar.text().strip() if hasattr(self, 'txt_buscar') else ""
        
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            if filtro:
                # Busca por nombre o RIF que contenga el texto (ILIKE no distingue mayúsculas/minúsculas)
                query = """
                    SELECT cod_proveedor, nombre_proveedor, rif 
                    FROM maestro_proveedores 
                    WHERE cod_compania = %s AND 
                          (nombre_proveedor ILIKE %s OR rif ILIKE %s)
                    ORDER BY nombre_proveedor
                """
                patron = f"%{filtro}%"
                cur.execute(query, (self.cod_compania, patron, patron))
            else:
                # Si el buscador está vacío, carga todos
                query = "SELECT cod_proveedor, nombre_proveedor, rif FROM maestro_proveedores WHERE cod_compania = %s ORDER BY nombre_proveedor"
                cur.execute(query, (self.cod_compania,))
                
            for p in cur.fetchall():
                self.lista_proveedores.addItem(f"{p[1]} ({p[2]})")
                self.lista_proveedores.item(self.lista_proveedores.count()-1).setData(Qt.ItemDataRole.UserRole, p[0])
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al cargar proveedores: {e}")

    def cargar_datos_formulario(self, item):
        cod_prov = item.data(Qt.ItemDataRole.UserRole)
        self.cod_proveedor_seleccionado = cod_prov
        self.lbl_titulo_form.setText(f"Editando Proveedor: {cod_prov}")
        
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = """
                SELECT p.tipo_proveedor, p.rif, p.nit, p.nombre_proveedor, p.contacto1, p.contacto2, 
                       p.email1, p.email2, p.telefono1, p.telefono2, p.fax, p.direccion, p.direccion_alterna, 
                       p.zona, p.lineas, p.num_cuenta_bancaria, p.beneficiario, p.nombre_banco, 
                       p.gastos, p.anticipos, p.cxp_proveedor, p.forma_pago, p.tipo_contribuyente, 
                       p.contribuyente_iva, p.figura_tributaria, p.registro_unico, p.tipo_persona, 
                       p.cod_retencion, p.sujeto_retencion_iva, p.comentario, p.estatus,
                       u1.usuario_login, p.fecha_registro, u2.usuario_login, p.fecha_modifica
                FROM maestro_proveedores p
                LEFT JOIN seg_usuarios u1 ON p.id_user_crea = u1.id_usuario
                LEFT JOIN seg_usuarios u2 ON p.id_user_mod = u2.id_usuario
                WHERE p.cod_compania = %s AND p.cod_proveedor = %s
            """
            cur.execute(query, (self.cod_compania, cod_prov))
            d = cur.fetchone()
            conn.close()
            
            if d:
                self.txt_cod_proveedor.setText(cod_prov)
                self.cmb_tipo_prov.setCurrentText(d[0] or "")
                self.txt_rif.setText(d[1] or "")
                self.txt_nit.setText(d[2] or "")
                self.txt_nombre.setText(d[3] or "")
                
                self.txt_contacto1.setText(d[4] or "")
                self.txt_contacto2.setText(d[5] or "")
                self.txt_email1.setText(d[6] or "")
                self.txt_email2.setText(d[7] or "")
                self.txt_telefono1.setText(d[8] or "")
                self.txt_telefono2.setText(d[9] or "")
                self.txt_fax.setText(d[10] or "")
                self.txt_direccion.setText(d[11] or "")
                self.txt_direccion_alt.setText(d[12] or "")
                self.txt_zona.setText(d[13] or "")
                
                self.txt_lineas.setText(d[14] or "")
                self.txt_cuenta.setText(d[15] or "")
                self.txt_beneficiario.setText(d[16] or "")
                self.txt_banco.setText(d[17] or "")
                self.txt_gastos.setText(d[18] or "")
                self.txt_anticipos.setText(d[19] or "")
                self.txt_cxp.setText(d[20] or "")
                self.cmb_forma_pago.setCurrentText(d[21] or "")
                
                self.cmb_tipo_contrib.setCurrentText(d[22] or "")
                self.chk_contrib_iva.setChecked(bool(d[23]))
                self.txt_figura_trib.setText(d[24] or "")
                self.txt_reg_unico.setText(d[25] or "")
                self.cmb_tipo_persona.setCurrentText(d[26] or "")
                self.txt_cod_retencion.setText(d[27] or "")
                self.chk_retencion_iva.setChecked(bool(d[28]))
                
                self.txt_comentario.setText(d[29] or "")
                self.chk_estatus.setChecked(bool(d[30]))
                
                f_crea = d[32].strftime("%d/%m/%Y %I:%M %p") if d[32] else "-"
                f_mod = d[34].strftime("%d/%m/%Y %I:%M %p") if d[34] else "-"
                
                self.lbl_creado_por.setText(f"Creado por: {d[31] or '-'}")
                self.lbl_fecha_crea.setText(f"Fecha: {f_crea}")
                self.lbl_modif_por.setText(f"Modif. por: {d[33] or '-'}")
                self.lbl_fecha_mod.setText(f"Fecha: {f_mod}")

            self.set_estado_formulario(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al cargar datos: {e}")

    def guardar_proveedor(self):
        if self.rol_usuario != "Administrador": return
        
        cod = self.txt_cod_proveedor.text().strip().upper()
        nombre = self.txt_nombre.text().strip()
        rif = self.txt_rif.text().strip().upper()
        
        if not cod or not nombre or not rif:
            QMessageBox.warning(self, "Datos", "Cód. Proveedor, Razón Social y RIF son obligatorios.")
            return
            
        if not self.validar_rif(rif):
            QMessageBox.warning(self, "Formato", "El RIF es inválido. Formato: J-12345678-0")
            return

        params = (
            self.cmb_tipo_prov.currentText(), rif, self.txt_nit.text(), nombre,
            self.txt_contacto1.text(), self.txt_contacto2.text(), self.txt_email1.text(), self.txt_email2.text(),
            self.txt_telefono1.text(), self.txt_telefono2.text(), self.txt_fax.text(), self.txt_direccion.toPlainText(),
            self.txt_direccion_alt.toPlainText(), self.txt_zona.text(), self.txt_comentario.toPlainText(),
            self.txt_lineas.text(), self.txt_cuenta.text(), self.txt_beneficiario.text(), self.txt_banco.text(),
            self.cmb_tipo_contrib.currentText(), self.chk_contrib_iva.isChecked(), self.txt_figura_trib.text(),
            self.cmb_forma_pago.currentText(), self.txt_reg_unico.text(), self.cmb_tipo_persona.currentText(),
            self.txt_cod_retencion.text(), self.chk_retencion_iva.isChecked(), self.txt_gastos.text(),
            self.txt_anticipos.text(), self.txt_cxp.text(), self.chk_estatus.isChecked()
        )

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            cur.execute("SET TIME ZONE 'America/Caracas'")
            
            if self.cod_proveedor_seleccionado is None:
                query = """
                    INSERT INTO maestro_proveedores (
                        tipo_proveedor, rif, nit, nombre_proveedor, contacto1, contacto2, email1, email2, 
                        telefono1, telefono2, fax, direccion, direccion_alterna, zona, comentario, lineas, 
                        num_cuenta_bancaria, beneficiario, nombre_banco, tipo_contribuyente, contribuyente_iva, 
                        figura_tributaria, forma_pago, registro_unico, tipo_persona, cod_retencion, 
                        sujeto_retencion_iva, gastos, anticipos, cxp_proveedor, estatus, cod_compania, cod_proveedor, id_user_crea
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cur.execute(query, (*params, self.cod_compania, cod, self.id_usuario_actual))
            else:
                query = """
                    UPDATE maestro_proveedores SET
                        tipo_proveedor=%s, rif=%s, nit=%s, nombre_proveedor=%s, contacto1=%s, contacto2=%s, 
                        email1=%s, email2=%s, telefono1=%s, telefono2=%s, fax=%s, direccion=%s, direccion_alterna=%s, 
                        zona=%s, comentario=%s, lineas=%s, num_cuenta_bancaria=%s, beneficiario=%s, nombre_banco=%s, 
                        tipo_contribuyente=%s, contribuyente_iva=%s, figura_tributaria=%s, forma_pago=%s, 
                        registro_unico=%s, tipo_persona=%s, cod_retencion=%s, sujeto_retencion_iva=%s, 
                        gastos=%s, anticipos=%s, cxp_proveedor=%s, estatus=%s, id_user_mod=%s
                    WHERE cod_compania = %s AND cod_proveedor = %s
                """
                cur.execute(query, (*params, self.id_usuario_actual, self.cod_compania, self.cod_proveedor_seleccionado))

            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Proveedor guardado exitosamente.")
            self.cancelar_accion()
            self.cargar_lista_proveedores()
            
        except psycopg2.Error as e:
            if "unique" in str(e).lower() and "rif" in str(e).lower():
                QMessageBox.warning(self, "Error", "Ya existe un proveedor con ese RIF en esta empresa.")
            elif "unique" in str(e).lower() and "pkey" in str(e).lower():
                QMessageBox.warning(self, "Error", f"El código '{cod}' ya está en uso.")
            else:
                QMessageBox.critical(self, "Error BD", f"{e.pgerror}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def eliminar_proveedor(self):
        if self.rol_usuario != "Administrador": return
        if not self.cod_proveedor_seleccionado: return
        
        if QMessageBox.question(self, "Confirmar", "¿Eliminar definitivamente el proveedor?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("DELETE FROM maestro_proveedores WHERE cod_compania=%s AND cod_proveedor=%s", (self.cod_compania, self.cod_proveedor_seleccionado))
                conn.commit()
                conn.close()
                self.cancelar_accion()
                self.cargar_lista_proveedores()
            except Exception as e:
                QMessageBox.critical(self, "Error", "No se pudo eliminar. Es posible que tenga documentos (compras) asociados.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProveedorForm(1, 1, "EMPRESA PRUEBA CA")
    window.showMaximized()
    sys.exit(app.exec())