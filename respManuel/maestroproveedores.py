import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QStatusBar
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt

# Importar las clases de conexión y proveedor que ya diseñamos
from poolconexion import ConexionDB 
from proveedor_model import Proveedor

class ProveedorForm(QWidget):
    def __init__(self, cod_compania_actual, id_user_actual):
        super().__init__()
        self.cod_compania_actual = cod_compania_actual
        self.id_user_actual = id_user_actual
        self.db_conn = ConexionDB("localssshost", "nexusdb", "postgres", "123Mm456*") # Configura tu DB
        self.setWindowTitle("Gestión de Maestros de Proveedores")
        self.setGeometry(100, 100, 1000, 700) # Tamaño de ventana
        self.apply_styles()
        self.init_ui()

    def apply_styles(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F0F2F5")) # Fondo suave
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#333333")) # Texto oscuro
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF")) # Fondo de campos
        palette.setColor(QPalette.ColorRole.Text, QColor("#333333"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#5A9BD3")) # Selección (azul suave)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(palette)

        self.setFont(QFont("Segoe UI", 10)) # Fuente legible

        # Estilos CSS para QPushButton (ejemplo)
        self.setStyleSheet("""
            QPushButton {
                background-color: #007BFF; /* Azul institucional */
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: #FFFFFF;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background: #E0E6ED;
                border: 1px solid #cccccc;
                border-bottom-color: #cccccc; /* Separator color */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-bottom-color: #FFFFFF; /* Makes it look connected to the pane */
            }
            QStatusBar {
                background-color: #E0E6ED;
                color: #333333;
                border-top: 1px solid #cccccc;
            }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout()

        # --- Sección de Botones de Acción ---
        top_buttons_layout = QHBoxLayout()
        self.btn_nuevo = QPushButton("Nuevo")
        self.btn_buscar = QPushButton("Buscar")
        self.btn_guardar = QPushButton("Guardar")
        self.btn_editar = QPushButton("Editar")
        self.btn_eliminar = QPushButton("Eliminar")

        top_buttons_layout.addWidget(self.btn_nuevo)
        top_buttons_layout.addWidget(self.btn_buscar)
        top_buttons_layout.addStretch() # Empuja los botones a la izquierda
        top_buttons_layout.addWidget(self.btn_guardar)
        top_buttons_layout.addWidget(self.btn_editar)
        top_buttons_layout.addWidget(self.btn_eliminar)
        main_layout.addLayout(top_buttons_layout)

        # --- Campo de Búsqueda ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar Proveedor:"))
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Ingrese RIF, Código o Nombre")
        search_layout.addWidget(self.search_line)
        main_layout.addLayout(search_layout)

        # --- Pestañas de Datos del Proveedor ---
        self.tab_widget = QTabWidget()
        
        # Pestaña 1: Datos Generales
        tab_general = QWidget()
        form_general = QFormLayout(tab_general)
        self.lbl_cod_compania = QLabel(f"Compañía Actual: {self.cod_compania_actual}") # Solo lectura
        form_general.addRow(self.lbl_cod_compania)
        self.txt_cod_proveedor = QLineEdit()
        form_general.addRow("Código Proveedor:", self.txt_cod_proveedor)
        self.txt_rif = QLineEdit()
        self.txt_rif.textChanged.connect(self.validar_rif_ui) # Conectar validación en UI
        form_general.addRow("RIF:", self.txt_rif)
        self.txt_nit = QLineEdit()
        form_general.addRow("NIT:", self.txt_nit)
        self.txt_nombre_provider = QLineEdit()
        form_general.addRow("Razón Social:", self.txt_nombre_provider)
        self.chk_activo_inactivo = QCheckBox("Activo")
        self.chk_activo_inactivo.setChecked(True)
        form_general.addRow("Estado:", self.chk_activo_inactivo)
        self.txt_comentario = QTextEdit()
        form_general.addRow("Comentario:", self.txt_comentario)
        self.tab_widget.addTab(tab_general, "Datos Generales")

        # Pestaña 2: Contactos y Ubicación
        tab_contactos = QWidget()
        form_contactos = QFormLayout(tab_contactos)
        self.txt_direccion = QTextEdit()
        form_contactos.addRow("Dirección:", self.txt_direccion)
        self.txt_direccion_alt = QTextEdit()
        form_contactos.addRow("Dirección Alterna:", self.txt_direccion_alt)
        self.txt_zona = QLineEdit()
        form_contactos.addRow("Zona:", self.txt_zona)
        self.txt_contacto1 = QLineEdit()
        form_contactos.addRow("Contacto 1:", self.txt_contacto1)
        self.txt_telefono1 = QLineEdit()
        form_contactos.addRow("Teléfono 1:", self.txt_telefono1)
        self.txt_email1 = QLineEdit()
        form_contactos.addRow("Email 1:", self.txt_email1)
        # ... añadir más campos de contacto ...
        self.tab_widget.addTab(tab_contactos, "Contactos y Ubicación")

        # Pestaña 3: Información Tributaria
        tab_tributaria = QWidget()
        form_tributaria = QFormLayout(tab_tributaria)
        self.cmb_tipo_persona = QComboBox()
        self.cmb_tipo_persona.addItems(["Natural", "Jurídica", "Domiciliado", "No Domiciliado"])
        form_tributaria.addRow("Tipo Persona:", self.cmb_tipo_persona)
        self.txt_cod_retencion = QLineEdit()
        form_tributaria.addRow("Cod. Retención:", self.txt_cod_retencion)
        self.chk_sujeto_ret_iva = QCheckBox("Sujeto a Retención IVA")
        form_tributaria.addRow("Retención IVA:", self.chk_sujeto_ret_iva)
        self.cmb_tipo_contrib = QComboBox()
        self.cmb_tipo_contrib.addItems(["Especial", "Ordinario", "Formal", "Exento"])
        form_tributaria.addRow("Tipo Contribuyente:", self.cmb_tipo_contrib)
        self.chk_contribuyente_iva = QCheckBox("Es Contribuyente IVA")
        form_tributaria.addRow("Contrib. IVA:", self.chk_contribuyente_iva)
        self.txt_figura_tributaria = QLineEdit()
        form_tributaria.addRow("Figura Tributaria:", self.txt_figura_tributaria)
        self.txt_registro_unico = QLineEdit()
        form_tributaria.addRow("Registro Único:", self.txt_registro_unico)
        self.tab_widget.addTab(tab_tributaria, "Info. Tributaria")

        # Pestaña 4: Datos Contables y Bancarios
        tab_contable = QWidget()
        form_contable = QFormLayout(tab_contable)
        self.cmb_forma_pago = QComboBox()
        self.cmb_forma_pago.addItems(["Crédito", "Contado", "Transferencia", "Cheque"])
        form_contable.addRow("Forma de Pago:", self.cmb_forma_pago)
        self.txt_gastos = QLineEdit()
        form_contable.addRow("Cta. Gastos:", self.txt_gastos)
        self.txt_anticipos = QLineEdit()
        form_contable.addRow("Cta. Anticipos:", self.txt_anticipos)
        self.txt_cxp_proveedor = QLineEdit()
        form_contable.addRow("Cta. CXP:", self.txt_cxp_proveedor)
        self.txt_lineas = QTextEdit()
        form_contable.addRow("Líneas de Producto:", self.txt_lineas)
        self.txt_num_cuenta_ban = QLineEdit()
        form_contable.addRow("N° Cuenta Bancaria:", self.txt_num_cuenta_ban)
        self.txt_beneficiario = QLineEdit()
        form_contable.addRow("Beneficiario:", self.txt_beneficiario)
        self.txt_nombre_banco = QLineEdit()
        form_contable.addRow("Banco:", self.txt_nombre_banco)
        self.tab_widget.addTab(tab_contable, "Info. Contable/Bancaria")
        
        main_layout.addWidget(self.tab_widget)

        # --- Sección de Auditoría ---
        audit_layout = QHBoxLayout()
        audit_layout.addWidget(QLabel("Creado por:"))
        self.lbl_user_crea = QLineEdit()
        self.lbl_user_crea.setReadOnly(True)
        audit_layout.addWidget(self.lbl_user_crea)
        audit_layout.addWidget(QLabel("Fecha Registro:"))
        self.lbl_fecha_reg = QLineEdit()
        self.lbl_fecha_reg.setReadOnly(True)
        audit_layout.addWidget(self.lbl_fecha_reg)
        audit_layout.addWidget(QLabel("Modificado por:"))
        self.lbl_user_mod = QLineEdit()
        self.lbl_user_mod.setReadOnly(True)
        audit_layout.addWidget(self.lbl_user_mod)
        audit_layout.addWidget(QLabel("Última Modif.:"))
        self.lbl_fecha_mod = QLineEdit()
        self.lbl_fecha_mod.setReadOnly(True)
        audit_layout.addWidget(self.lbl_fecha_mod)
        main_layout.addLayout(audit_layout)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)


        self.setLayout(main_layout)

        # Conectar botones a sus funciones
        self.btn_guardar.clicked.connect(self.guardar_proveedor)
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)
        self.btn_buscar.clicked.connect(self.buscar_proveedor) # Implementar búsqueda
        # ... conectar otros botones ...

    def validar_rif_ui(self):
        rif_text = self.txt_rif.text()
        if not Proveedor.validar_rif(rif_text) and rif_text: # Solo si hay texto
            self.txt_rif.setStyleSheet("border: 1px solid red; background-color: #FFEEEE;")
            self.status_bar.showMessage("Formato de RIF inválido (ej. J-12345678-0)", 3000)
            self.btn_guardar.setEnabled(False)
        else:
            self.txt_rif.setStyleSheet("border: 1px solid #cccccc; background-color: #FFFFFF;")
            self.status_bar.clearMessage()
            self.btn_guardar.setEnabled(True) # Re-habilitar si es válido (podría tener otras validaciones)


    def guardar_proveedor(self):
        # 1. Recopilar datos del formulario
        if not Proveedor.validar_rif(self.txt_rif.text()):
            QMessageBox.warning(self, "Error de Validación", "El formato del RIF es incorrecto.")
            return

        # Simula un ID de usuario logueado
        # id_user_actual = self.id_user_actual # Este viene del login

        # Crea un objeto Proveedor con los datos del formulario
        nuevo_proveedor = Proveedor(
            cod_compania=self.cod_compania_actual,
            cod_proveedor=self.txt_cod_proveedor.text(),
            rif=self.txt_rif.text(),
            nombre_provider=self.txt_nombre_provider.text(),
            id_user=self.id_user_actual # Usar el ID del usuario logueado
        )
        # Rellenar los otros campos
        nuevo_proveedor.nit = self.txt_nit.text()
        nuevo_proveedor.direccion = self.txt_direccion.toPlainText()
        nuevo_proveedor.activo_inactivo = self.chk_activo_inactivo.isChecked()
        # ... y así con todos los campos ...

        # 2. Conectar a la base de datos y guardar
        connection = self.db_conn.conectar()
        if connection:
            success, message = nuevo_proveedor.guardar(connection)
            if success:
                QMessageBox.information(self, "Éxito", message)
                self.limpiar_formulario()
                self.status_bar.showMessage(message, 3000)
            else:
                QMessageBox.critical(self, "Error", message)
                self.status_bar.showMessage(message, 5000)
            # self.db_conn.cerrar() # Considerar cerrar la conexión o mantenerla viva
        else:
            QMessageBox.critical(self, "Error de Conexión", "No se pudo conectar a la base de datos.")
            self.status_bar.showMessage("Error de conexión a la base de datos.", 5000)
            
    def limpiar_formulario(self):
        # Limpiar todos los campos de entrada
        self.txt_cod_proveedor.clear()
        self.txt_rif.clear()
        self.txt_nit.clear()
        self.txt_nombre_provider.clear()
        self.chk_activo_inactivo.setChecked(True)
        self.txt_comentario.clear()
        self.txt_direccion.clear()
        self.txt_direccion_alt.clear()
        self.txt_zona.clear()
        self.txt_contacto1.clear()
        self.txt_telefono1.clear()
        self.txt_email1.clear()
        # Limpiar otros campos de las pestañas
        self.cmb_tipo_persona.setCurrentIndex(0)
        self.txt_cod_retencion.clear()
        self.chk_sujeto_ret_iva.setChecked(False)
        self.cmb_tipo_contrib.setCurrentIndex(0)
        self.chk_contribuyente_iva.setChecked(True)
        self.txt_figura_tributaria.clear()
        self.txt_registro_unico.clear()
        self.cmb_forma_pago.setCurrentIndex(0)
        self.txt_gastos.clear()
        self.txt_anticipos.clear()
        self.txt_cxp_proveedor.clear()
        self.txt_lineas.clear()
        self.txt_num_cuenta_ban.clear()
        self.txt_beneficiario.clear()
        self.txt_nombre_banco.clear()

        # Limpiar campos de auditoría
        self.lbl_user_crea.clear()
        self.lbl_fecha_reg.clear()
        self.lbl_user_mod.clear()
        self.lbl_fecha_mod.clear()

        self.txt_rif.setStyleSheet("border: 1px solid #cccccc; background-color: #FFFFFF;") # Limpiar estilo de error
        self.btn_guardar.setEnabled(True)
        self.status_bar.clearMessage()

    def buscar_proveedor(self):
        search_term = self.search_line.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Búsqueda", "Por favor, ingrese un término de búsqueda.")
            return

        query = """
        SELECT cod_proveedor, rif, nit, nombre_provider, direccion, direccion_alt, zona,
               contacto1, contacto2, email1, email2, telefono1, telefono2, fax,
               tipo_persona, cod_retencion, sujeto_ret_iva, tipo_contrib, contribuyente_iva,
               figura_tributaria, registro_unico, forma_pago, gastos, anticipos, cxp_proveedor,
               lineas, num_cuenta_ban, beneficiario, nombre_banco, activo_inactivo, comentario,
               id_user_crea, fecha_registro, id_user_mod, fecha_modifica
        FROM maestro_proveedores
        WHERE cod_compania = %s AND (
            rif ILIKE %s OR cod_proveedor ILIKE %s OR nombre_provider ILIKE %s
        );
        """
        connection = self.db_conn.conectar()
        if connection:
            try:
                with connection.cursor() as cursor:
                    # Usamos %s para el patrón ILIKE
                    cursor.execute(query, (
                        self.cod_compania_actual, 
                        f"%{search_term}%", 
                        f"%{search_term}%", 
                        f"%{search_term}%"
                    ))
                    result = cursor.fetchone() # Asumimos un solo resultado por simplicidad
                    if result:
                        self.cargar_datos_en_formulario(result)
                        self.status_bar.showMessage("Proveedor encontrado.", 3000)
                    else:
                        QMessageBox.information(self, "Búsqueda", "Proveedor no encontrado.")
                        self.status_bar.showMessage("Proveedor no encontrado.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error de Búsqueda", f"Error en la base de datos: {e}")
                self.status_bar.showMessage(f"Error en búsqueda: {e}", 5000)
        else:
            QMessageBox.critical(self, "Error de Conexión", "No se pudo conectar a la base de datos.")
            self.status_bar.showMessage("Error de conexión a la base de datos.", 5000)

    def cargar_datos_en_formulario(self, data):
        # Asumiendo el orden de los campos en el SELECT
        self.txt_cod_proveedor.setText(data[0] if data[0] is not None else "")
        self.txt_rif.setText(data[1] if data[1] is not None else "")
        self.txt_nit.setText(data[2] if data[2] is not None else "")
        self.txt_nombre_provider.setText(data[3] if data[3] is not None else "")
        self.txt_direccion.setText(data[4] if data[4] is not None else "")
        self.txt_direccion_alt.setText(data[5] if data[5] is not None else "")
        self.txt_zona.setText(data[6] if data[6] is not None else "")
        self.txt_contacto1.setText(data[7] if data[7] is not None else "")
        self.txt_contacto2.setText(data[8] if data[8] is not None else "")
        self.txt_email1.setText(data[9] if data[9] is not None else "")
        self.txt_email2.setText(data[10] if data[10] is not None else "")
        self.txt_telefono1.setText(data[11] if data[11] is not None else "")
        self.txt_telefono2.setText(data[12] if data[12] is not None else "")
        self.txt_fax.setText(data[13] if data[13] is not None else "")

        # ComboBoxes y CheckBoxes
        self.cmb_tipo_persona.setCurrentText(data[14] if data[14] is not None else "")
        self.txt_cod_retencion.setText(data[15] if data[15] is not None else "")
        self.chk_sujeto_ret_iva.setChecked(data[16] if data[16] is not None else False)
        self.cmb_tipo_contrib.setCurrentText(data[17] if data[17] is not None else "")
        self.chk_contribuyente_iva.setChecked(data[18] if data[18] is not None else False)
        self.txt_figura_tributaria.setText(data[19] if data[19] is not None else "")
        self.txt_registro_unico.setText(data[20] if data[20] is not None else "")
        
        self.cmb_forma_pago.setCurrentText(data[21] if data[21] is not None else "")
        self.txt_gastos.setText(data[22] if data[22] is not None else "")
        self.txt_anticipos.setText(data[23] if data[23] is not None else "")
        self.txt_cxp_proveedor.setText(data[24] if data[24] is not None else "")
        self.txt_lineas.setText(data[25] if data[25] is not None else "")
        self.txt_num_cuenta_ban.setText(data[26] if data[26] is not None else "")
        self.txt_beneficiario.setText(data[27] if data[27] is not None else "")
        self.txt_nombre_banco.setText(data[28] if data[28] is not None else "")

        self.chk_activo_inactivo.setChecked(data[29] if data[29] is not None else False)
        self.txt_comentario.setText(data[30] if data[30] is not None else "")

        # Campos de Auditoría
        self.lbl_user_crea.setText(str(data[31]) if data[31] is not None else "") # Necesitará un lookup de nombre de usuario
        self.lbl_fecha_reg.setText(str(data[32]) if data[32] is not None else "")
        self.lbl_user_mod.setText(str(data[33]) if data[33] is not None else "") # Necesitará un lookup de nombre de usuario
        self.lbl_fecha_mod.setText(str(data[34]) if data[34] is not None else "")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Simula el COD_COMPANIA y ID_USUARIO obtenidos del login
    # Aquí iría la lógica del LOGIN para obtener estos valores reales
    COD_COMPANIA_SESSION = 1 
    ID_USER_SESSION = 1 

    window = ProveedorForm(COD_COMPANIA_SESSION, ID_USER_SESSION)
    window.show()
    sys.exit(app.exec())