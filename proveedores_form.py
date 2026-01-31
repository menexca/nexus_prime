# proveedores_form.py
import sys
import psycopg2
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QStatusBar
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS # Importamos configuración compartida

class ProveedorForm(QWidget):
    def __init__(self, cod_compania, id_usuario, nombre_empresa):
        super().__init__()
        # --- RECEPCIÓN DE SESIÓN (LOGIN) ---
        self.cod_compania_actual = cod_compania
        self.id_user_actual = id_usuario
        self.nombre_empresa_actual = nombre_empresa
        
        # Configuración de Ventana
        self.setWindowTitle(f"Gestión de Proveedores - {self.nombre_empresa_actual}")
        self.setGeometry(100, 100, 1000, 700)
        
        self.apply_styles()
        self.init_ui()

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
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #007BFF; }
            QTabWidget::pane { border: 1px solid #cccccc; background-color: #FFFFFF; }
            QTabBar::tab {
                background: #E0E6ED; border: 1px solid #cccccc;
                padding: 8px 15px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: #FFFFFF; border-bottom-color: #FFFFFF; font-weight: bold; }
            QStatusBar { background-color: #E0E6ED; color: #333333; }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout()

        # --- BARRA SUPERIOR (Info de Sesión + Botones) ---
        top_bar = QHBoxLayout()
        lbl_session = QLabel(f"🏢 Empresa: {self.nombre_empresa_actual} | 👤 Usuario ID: {self.id_user_actual}")
        lbl_session.setStyleSheet("color: #0056b3; font-weight: bold;")
        top_bar.addWidget(lbl_session)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        buttons_layout = QHBoxLayout()
        self.btn_nuevo = QPushButton("Nuevo")
        self.btn_buscar = QPushButton("Buscar")
        self.btn_guardar = QPushButton("Guardar")
        self.btn_editar = QPushButton("Editar")
        self.btn_eliminar = QPushButton("Eliminar")
        
        buttons_layout.addWidget(self.btn_nuevo)
        buttons_layout.addWidget(self.btn_buscar)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_guardar)
        buttons_layout.addWidget(self.btn_editar)
        buttons_layout.addWidget(self.btn_eliminar)
        main_layout.addLayout(buttons_layout)

        # --- BÚSQUEDA ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar:"))
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Ingrese RIF, Código o Nombre...")
        search_layout.addWidget(self.search_line)
        main_layout.addLayout(search_layout)

        # --- PESTAÑAS (EL FORMULARIO COMPLETO) ---
        self.tab_widget = QTabWidget()
        
        # TAB 1: Datos Generales
        tab_general = QWidget()
        form_general = QFormLayout(tab_general)
        
        self.txt_cod_proveedor = QLineEdit()
        form_general.addRow("Código Interno:", self.txt_cod_proveedor)
        
        self.txt_rif = QLineEdit()
        self.txt_rif.textChanged.connect(self.validar_rif_ui)
        form_general.addRow("RIF (J-12345678-9):", self.txt_rif)
        
        self.txt_nit = QLineEdit()
        form_general.addRow("NIT:", self.txt_nit)
        
        self.txt_nombre_provider = QLineEdit()
        form_general.addRow("Razón Social:", self.txt_nombre_provider)
        
        self.chk_activo_inactivo = QCheckBox("Proveedor Activo")
        self.chk_activo_inactivo.setChecked(True)
        form_general.addRow("Estatus:", self.chk_activo_inactivo)
        
        self.txt_comentario = QTextEdit()
        self.txt_comentario.setMaximumHeight(60)
        form_general.addRow("Comentario:", self.txt_comentario)
        self.tab_widget.addTab(tab_general, "Datos Generales")

        # TAB 2: Contactos y Ubicación
        tab_contactos = QWidget()
        form_contactos = QFormLayout(tab_contactos)
        self.txt_direccion = QTextEdit()
        self.txt_direccion.setMaximumHeight(50)
        form_contactos.addRow("Dirección Fiscal:", self.txt_direccion)
        self.txt_direccion_alt = QTextEdit()
        self.txt_direccion_alt.setMaximumHeight(50)
        form_contactos.addRow("Dirección Alterna:", self.txt_direccion_alt)
        self.txt_zona = QLineEdit()
        form_contactos.addRow("Zona / Ruta:", self.txt_zona)
        
        h_contact = QHBoxLayout()
        self.txt_contacto1 = QLineEdit(); self.txt_contacto1.setPlaceholderText("Nombre Contacto 1")
        self.txt_telefono1 = QLineEdit(); self.txt_telefono1.setPlaceholderText("Tlf 1")
        h_contact.addWidget(self.txt_contacto1); h_contact.addWidget(self.txt_telefono1)
        form_contactos.addRow("Contacto Principal:", h_contact)
        
        self.txt_email1 = QLineEdit()
        form_contactos.addRow("Email Pedidos:", self.txt_email1)
        self.tab_widget.addTab(tab_contactos, "Ubicación y Contacto")

        # TAB 3: Tributaria
        tab_tributaria = QWidget()
        form_tributaria = QFormLayout(tab_tributaria)
        self.cmb_tipo_persona = QComboBox()
        self.cmb_tipo_persona.addItems(["Jurídica", "Natural", "Jurídica Domiciliada"])
        form_tributaria.addRow("Tipo Persona:", self.cmb_tipo_persona)
        
        self.txt_cod_retencion = QLineEdit()
        form_tributaria.addRow("Cód. Concepto ISLR:", self.txt_cod_retencion)
        
        self.chk_sujeto_ret_iva = QCheckBox("Es Agente de Retención")
        form_tributaria.addRow("Retención IVA:", self.chk_sujeto_ret_iva)
        
        self.cmb_tipo_contrib = QComboBox()
        self.cmb_tipo_contrib.addItems(["Ordinario", "Especial", "Formal"])
        form_tributaria.addRow("Tipo Contribuyente:", self.cmb_tipo_contrib)
        
        self.chk_contribuyente_iva = QCheckBox("Contribuyente IVA")
        self.chk_contribuyente_iva.setChecked(True)
        form_tributaria.addRow("Paga IVA:", self.chk_contribuyente_iva)
        self.tab_widget.addTab(tab_tributaria, "Info. Fiscal")

        # TAB 4: Contable
        tab_contable = QWidget()
        form_contable = QFormLayout(tab_contable)
        self.cmb_forma_pago = QComboBox()
        self.cmb_forma_pago.addItems(["Crédito 7 Días", "Crédito 15 Días", "Crédito 30 Días", "Contado"])
        form_contable.addRow("Condición Pago:", self.cmb_forma_pago)
        
        self.txt_cxp_proveedor = QLineEdit()
        self.txt_cxp_proveedor.setPlaceholderText("Ej: 2.1.01.001")
        form_contable.addRow("Cta. Contable CXP:", self.txt_cxp_proveedor)
        
        self.txt_gastos = QLineEdit()
        form_contable.addRow("Cta. Gastos:", self.txt_gastos)
        
        self.txt_num_cuenta_ban = QLineEdit()
        form_contable.addRow("Cuenta Bancaria:", self.txt_num_cuenta_ban)
        self.txt_beneficiario = QLineEdit()
        form_contable.addRow("Beneficiario:", self.txt_beneficiario)
        self.txt_nombre_banco = QLineEdit()
        form_contable.addRow("Banco:", self.txt_nombre_banco)
        self.tab_widget.addTab(tab_contable, "Datos Bancarios")
        
        main_layout.addWidget(self.tab_widget)

        # --- FOOTER (AUDITORÍA) ---
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)
        
        self.setLayout(main_layout)

        # Conexiones
        self.btn_guardar.clicked.connect(self.guardar_proveedor)
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)

    # --- LÓGICA DE NEGOCIO ---
    def validar_rif_ui(self):
        rif = self.txt_rif.text().upper().strip()
        patron = r'^[JVGEC]-\d{8}-\d$'
        if rif and not re.match(patron, rif):
            self.txt_rif.setStyleSheet("border: 2px solid red; background-color: #FFF0F0;")
            self.status_bar.showMessage("⚠️ Formato RIF Inválido (Ej: J-12345678-0)")
            self.btn_guardar.setEnabled(False)
        else:
            self.txt_rif.setStyleSheet("")
            self.status_bar.showMessage("✅ Formato RIF Correcto")
            self.btn_guardar.setEnabled(True)

    def guardar_proveedor(self):
        # 1. Validaciones básicas
        if not self.txt_rif.text() or not self.txt_nombre_provider.text():
            QMessageBox.warning(self, "Faltan Datos", "El RIF y la Razón Social son obligatorios.")
            return

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cursor = conn.cursor()
            
            # 2. Query de Inserción (Usando el COD_COMPANIA de la sesión)
            query = """
                INSERT INTO maestro_proveedores (
                    cod_compania, cod_proveedor, rif, nit, nombre_provider, 
                    direccion, zona, contacto1, telefono1, email1,
                    tipo_persona, cod_retencion, sujeto_ret_iva, tipo_contrib, contribuyente_iva,
                    forma_pago, cxp_proveedor, gastos, num_cuenta_ban, beneficiario, nombre_banco,
                    activo_inactivo, comentario, id_user_crea
                ) VALUES (
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
            """
            
            # Recolección de datos
            datos = (
                self.cod_compania_actual, self.txt_cod_proveedor.text(), self.txt_rif.text().upper(), self.txt_nit.text(), self.txt_nombre_provider.text(),
                self.txt_direccion.toPlainText(), self.txt_zona.text(), self.txt_contacto1.text(), self.txt_telefono1.text(), self.txt_email1.text(),
                self.cmb_tipo_persona.currentText(), self.txt_cod_retencion.text(), self.chk_sujeto_ret_iva.isChecked(), self.cmb_tipo_contrib.currentText(), self.chk_contribuyente_iva.isChecked(),
                self.cmb_forma_pago.currentText(), self.txt_cxp_proveedor.text(), self.txt_gastos.text(), self.txt_num_cuenta_ban.text(), self.txt_beneficiario.text(), self.txt_nombre_banco.text(),
                self.chk_activo_inactivo.isChecked(), self.txt_comentario.toPlainText(), self.id_user_actual
            )
            
            cursor.execute(query, datos)
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Éxito", "Proveedor registrado correctamente.")
            self.limpiar_formulario()
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Detalle: {e.pgerror}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error inesperado: {e}")

    def limpiar_formulario(self):
        self.txt_cod_proveedor.clear()
        self.txt_rif.clear()
        self.txt_nit.clear()
        self.txt_nombre_provider.clear()
        self.txt_direccion.clear()
        self.txt_direccion_alt.clear()
        self.txt_zona.clear()
        self.txt_contacto1.clear()
        self.txt_telefono1.clear()
        self.txt_email1.clear()
        self.txt_comentario.clear()
        self.txt_cxp_proveedor.clear()
        self.txt_gastos.clear()
        self.txt_num_cuenta_ban.clear()
        self.txt_beneficiario.clear()
        self.txt_nombre_banco.clear()
        self.chk_activo_inactivo.setChecked(True)
        self.status_bar.clearMessage()