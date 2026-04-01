import sys
import psycopg2
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QListWidget, QFrame, QApplication, QDateEdit, QDoubleSpinBox,
    QTableWidget, QHeaderView, QTableWidgetItem, QCompleter, QSizePolicy, QDialog, QAbstractItemView
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt, QDate, QTimer
from db_config import DB_PARAMS

# 1. Importamos el manejador de errores
from error_handler import manejar_error

class BuscadorComprasModal(QDialog):
    def __init__(self, cod_compania, parent=None):
        super().__init__(parent)
        self.cod_compania = cod_compania
        self.doc_seleccionado = None
        self.setWindowTitle("Buscar Documento de Compra")
        self.resize(750, 450)
        self.init_ui()
        self.cargar_compras()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Buscador
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por N° Documento, Factura o Proveedor...")
        
        self.timer_busqueda = QTimer()
        self.timer_busqueda.setSingleShot(True)
        self.timer_busqueda.timeout.connect(self.cargar_compras)
        self.txt_buscar.textChanged.connect(lambda: self.timer_busqueda.start(400))
        
        layout.addWidget(self.txt_buscar)

        # Tabla de resultados
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["N° Interno", "N° Factura", "Proveedor", "Fecha", "Estatus"])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.cellDoubleClicked.connect(self.seleccionar_documento)
        
        layout.addWidget(self.tabla)

    @manejar_error
    def cargar_compras(self):
        self.tabla.setRowCount(0)
        filtro = self.txt_buscar.text().strip()
        
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                if filtro:
                    query = """
                        SELECT c.num_doc_interno, c.num_factura, p.nombre_proveedor, c.fecha_compra, c.estatus 
                        FROM trx_compras c
                        JOIN com_proveedores p ON c.cod_proveedor = p.cod_proveedor AND c.cod_compania = p.cod_compania
                        WHERE c.cod_compania = %s AND 
                              (c.num_doc_interno ILIKE %s OR c.num_factura ILIKE %s OR p.nombre_proveedor ILIKE %s)
                        ORDER BY c.fecha_registro DESC LIMIT 100
                    """
                    patron = f"%{filtro}%"
                    cur.execute(query, (self.cod_compania, patron, patron, patron))
                else:
                    query = """
                        SELECT c.num_doc_interno, c.num_factura, p.nombre_proveedor, c.fecha_compra, c.estatus 
                        FROM trx_compras c
                        JOIN com_proveedores p ON c.cod_proveedor = p.cod_proveedor AND c.cod_compania = p.cod_compania
                        WHERE c.cod_compania = %s ORDER BY c.fecha_registro DESC LIMIT 100
                    """
                    cur.execute(query, (self.cod_compania,))
                    
                for r, doc in enumerate(cur.fetchall()):
                    self.tabla.insertRow(r)
                    self.tabla.setItem(r, 0, QTableWidgetItem(str(doc[0])))
                    self.tabla.setItem(r, 1, QTableWidgetItem(str(doc[1])))
                    self.tabla.setItem(r, 2, QTableWidgetItem(str(doc[2])))
                    self.tabla.setItem(r, 3, QTableWidgetItem(doc[3].strftime("%d/%m/%Y")))
                    
                    item_estatus = QTableWidgetItem(str(doc[4]))
                    if doc[4] == 'ANULADA':
                        item_estatus.setForeground(QColor("#DC3545"))
                    self.tabla.setItem(r, 4, item_estatus)

    def seleccionar_documento(self, row, col):
        self.doc_seleccionado = self.tabla.item(row, 0).text()
        self.accept() # Cierra el modal indicando éxito

class BuscadorProductosModal(QDialog):
    def __init__(self, cod_compania, filtro_inicial="", parent=None):
        super().__init__(parent)
        self.cod_compania = cod_compania
        self.producto_seleccionado = None
        self.setWindowTitle("Búsqueda Inteligente de Productos")
        self.resize(700, 400)
        self.init_ui()
        
        if filtro_inicial:
            self.txt_buscar.setText(filtro_inicial)
        self.cargar_productos()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por Código, Nombre o Referencia...")
        self.txt_buscar.setStyleSheet("font-size: 14px; padding: 5px;")
        
        self.timer_busqueda = QTimer()
        self.timer_busqueda.setSingleShot(True)
        self.timer_busqueda.timeout.connect(self.cargar_productos)
        self.txt_buscar.textChanged.connect(lambda: self.timer_busqueda.start(300))
        
        layout.addWidget(self.txt_buscar)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Código", "Descripción", "Costo U.", "Marca"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.cellDoubleClicked.connect(self.seleccionar_producto)
        layout.addWidget(self.tabla)

    @manejar_error
    def cargar_productos(self):
        self.tabla.setRowCount(0)
        filtro = self.txt_buscar.text().strip()
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                if filtro:
                    query = """
                        SELECT p.cod_producto, p.nombre, p.costo_final_usd, m.nombre_marca
                        FROM inv_productos p
                        LEFT JOIN inv_marcas m ON p.id_marca = m.id_marca AND p.cod_compania = m.cod_compania
                        WHERE p.cod_compania = %s AND p.es_activo = TRUE AND 
                              (p.cod_producto ILIKE %s OR p.nombre ILIKE %s)
                        ORDER BY p.nombre LIMIT 100
                    """
                    patron = f"%{filtro}%"
                    cur.execute(query, (self.cod_compania, patron, patron))
                else:
                    query = """
                        SELECT p.cod_producto, p.nombre, p.costo_final_usd, m.nombre_marca
                        FROM inv_productos p
                        LEFT JOIN inv_marcas m ON p.id_marca = m.id_marca AND p.cod_compania = m.cod_compania
                        WHERE p.cod_compania = %s AND p.es_activo = TRUE
                        ORDER BY p.nombre LIMIT 100
                    """
                    cur.execute(query, (self.cod_compania,))
                    
                for r, prod in enumerate(cur.fetchall()):
                    self.tabla.insertRow(r)
                    self.tabla.setItem(r, 0, QTableWidgetItem(str(prod[0])))
                    self.tabla.setItem(r, 1, QTableWidgetItem(str(prod[1])))
                    self.tabla.setItem(r, 2, QTableWidgetItem(f"{prod[2]:.4f}"))
                    self.tabla.setItem(r, 3, QTableWidgetItem(str(prod[3] or "")))

    def seleccionar_producto(self, row, col):
        cod = self.tabla.item(row, 0).text()
        desc = self.tabla.item(row, 1).text()
        costo = self.tabla.item(row, 2).text()
        self.producto_seleccionado = (cod, desc, costo)
        self.accept()

class ComprasForm(QWidget):
    def __init__(self, cod_compania, id_usuario_actual, nombre_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.id_usuario_actual = id_usuario_actual
        self.nombre_empresa = nombre_empresa
        self.rol_usuario = "Operador"
        self.estatus_actual = None
        
        self.setWindowTitle(f"Registro de Compras - {self.nombre_empresa}")
        self.resize(1200, 750)
        
        self.doc_seleccionado = None
        
        self.verificar_permisos_usuario()
        self.apply_styles()
        self.init_ui()
        
        self.cargar_combo_proveedores()
        self.cargar_combo_almacenes()
        
        self.cancelar_accion()

    @manejar_error
    def verificar_permisos_usuario(self):
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT rol FROM seg_usuarios WHERE id_usuario = %s", (self.id_usuario_actual,))
                res = cur.fetchone()
                if res: 
                    self.rol_usuario = str(res[0]).strip()

    def apply_styles(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F0F2F5")) 
        self.setPalette(palette)
        self.setFont(QFont("Segoe UI", 10))

        self.setStyleSheet("""
            QPushButton { background-color: #007BFF; color: white; border-radius: 5px; padding: 8px 15px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
            QPushButton.btn-eliminar-fila { background-color: #e74c3c; padding: 4px 8px; border-radius: 3px; }
            QPushButton.btn-eliminar-fila:hover { background-color: #c0392b; }
            QPushButton.btn-buscar-mini { background-color: #6c757d; color: white; padding: 5px 10px; border-radius: 3px; font-size: 12px; }
            QPushButton.btn-buscar-mini:hover { background-color: #5a6268; }
            
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; background-color: #FFFFFF;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 1px solid #007BFF; }
            QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QDoubleSpinBox:disabled { 
                background-color: #E9ECEF; color: #6C757D; 
            }
            QLineEdit:read-only { background-color: #E0E0E0; color: #555; }
            
            QListWidget, QTableWidget { border: 1px solid #cccccc; background-color: white; border-radius: 4px; font-size: 10pt; }
            QListWidget::item { padding: 5px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background-color: #E6F3FF; color: #0056b3; border-left: 4px solid #007BFF; }
            QHeaderView::section { background-color: #E0E6ED; padding: 5px; border: none; font-weight: bold; }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout() 

        # --- CABECERA PRINCIPAL (Botones y Título) ---
        header_layout = QHBoxLayout()
        
        self.btn_nuevo = QPushButton("+ Registrar Nueva Compra")
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)
        header_layout.addWidget(self.btn_nuevo)
        
        self.btn_buscar_compra = QPushButton("🔍 Buscar Compra")
        self.btn_buscar_compra.setStyleSheet("background-color: #6c757d; color: white;")
        self.btn_buscar_compra.clicked.connect(self.abrir_buscador_compras)
        header_layout.addWidget(self.btn_buscar_compra)
        
        header_layout.addSpacing(20)
        
        self.lbl_titulo_form = QLabel("Detalles del Documento")
        self.lbl_titulo_form.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header_layout.addWidget(self.lbl_titulo_form)
        
        self.lbl_estado_doc = QLabel("[DOCUMENTO ANULADO]")
        self.lbl_estado_doc.setStyleSheet("font-size: 16px; font-weight: bold; color: #DC3545; background-color: #F8D7DA; padding: 4px 8px; border-radius: 4px;")
        self.lbl_estado_doc.hide()
        header_layout.addWidget(self.lbl_estado_doc)
        
        lbl_permisos = QLabel(f"Rol: {self.rol_usuario}")
        color_p = "green" if self.rol_usuario == "Administrador" else "orange"
        lbl_permisos.setStyleSheet(f"color: {color_p}; font-weight: bold; border: 1px solid {color_p}; padding: 2px 5px; border-radius: 4px;")
        header_layout.addStretch()
        header_layout.addWidget(lbl_permisos)
        
        main_layout.addLayout(header_layout)

        # --- PESTAÑAS ---
        self.tabs = QTabWidget()

        # TAB 1: DATOS DE FACTURA + PRODUCTOS
        tab_general = QWidget()
        layout_general_main = QVBoxLayout(tab_general)
        
        form_gen = QFormLayout()
        
        self.txt_doc_interno = QLineEdit()
        self.txt_doc_interno.setReadOnly(True)
        self.txt_doc_interno.setStyleSheet("background-color: #E8F0FE; color: #2C3E50; font-weight: bold;")
        form_gen.addRow("N° Documento Interno *:", self.txt_doc_interno)
        
        self.cmb_proveedor = QComboBox()
        self.cmb_proveedor.setEditable(True)
        self.cmb_proveedor.lineEdit().setPlaceholderText("--- Escriba o seleccione un Proveedor ---")
        self.cmb_proveedor.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.completer_prov = QCompleter(self)
        self.completer_prov.setFilterMode(Qt.MatchFlag.MatchContains) 
        self.completer_prov.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cmb_proveedor.setCompleter(self.completer_prov)
        form_gen.addRow("Proveedor *:", self.cmb_proveedor)
        
        self.txt_factura = QLineEdit()
        form_gen.addRow("N° Factura *:", self.txt_factura)
        
        self.txt_control = QLineEdit()
        form_gen.addRow("N° Control:", self.txt_control)
        
        self.cmb_tipo_compra = QComboBox()
        self.cmb_tipo_compra.addItems(["Mercancía para la Venta", "Insumos Internos", "Servicios", "Activos Fijos", "Otros"])
        form_gen.addRow("Tipo de Compra:", self.cmb_tipo_compra)
        
        self.cmb_moneda = QComboBox()
        self.cmb_moneda.addItems(["Bs", "USD", "EUR", "COP"])
        form_gen.addRow("Moneda de Compra:", self.cmb_moneda)
        
        layout_general_main.addLayout(form_gen)
        
        linea_divisoria = QFrame()
        linea_divisoria.setFrameShape(QFrame.Shape.HLine)
        linea_divisoria.setStyleSheet("color: #cccccc; margin-top: 10px; margin-bottom: 5px;")
        layout_general_main.addWidget(linea_divisoria)
        
        lbl_titulo_prod = QLabel("🛒 Detalles de Productos (Escriba el código y presione Enter)")
        lbl_titulo_prod.setStyleSheet("font-weight: bold; color: #2C3E50;")
        layout_general_main.addWidget(lbl_titulo_prod)

        # TABLA DE PRODUCTOS (Edición en línea)
        self.tabla_productos = QTableWidget(0, 6)
        self.tabla_productos.setHorizontalHeaderLabels(["Código", "Descripción", "Cantidad", "Costo U.", "Total", "Acción"])
        self.tabla_productos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Conectamos la señal de edición
        self.tabla_productos.cellChanged.connect(self.procesar_edicion_celda)
        layout_general_main.addWidget(self.tabla_productos)

        self.lbl_totales = QLabel("TOTAL: 0.00")
        self.lbl_totales.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        self.lbl_totales.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout_general_main.addWidget(self.lbl_totales)
        
        self.tabs.addTab(tab_general, "🧾 Factura y Productos")

        # TAB 2: FECHAS Y PLAZOS
        tab_fechas = QWidget()
        form_fechas = QFormLayout(tab_fechas)
        self.dt_compra = QDateEdit(); self.dt_compra.setCalendarPopup(True)
        form_fechas.addRow("Fecha de Compra *:", self.dt_compra)
        self.dt_recepcion = QDateEdit(); self.dt_recepcion.setCalendarPopup(True)
        form_fechas.addRow("Fecha de Recepción:", self.dt_recepcion)
        self.dt_vencimiento = QDateEdit(); self.dt_vencimiento.setCalendarPopup(True)
        form_fechas.addRow("Fecha de Vencimiento:", self.dt_vencimiento)
        self.tabs.addTab(tab_fechas, "📅 Fechas")

        # TAB 3: ALMACÉN Y CONTABILIDAD 
        tab_conta = QWidget()
        form_conta = QFormLayout(tab_conta)
        self.cmb_almacen = QComboBox()
        form_conta.addRow("Almacén de Entrada *:", self.cmb_almacen)
        self.spin_costo_add = QDoubleSpinBox(); self.spin_costo_add.setRange(0, 999999999.99); self.spin_costo_add.setDecimals(2)
        form_conta.addRow("Costo Adicional a Distribuir:", self.spin_costo_add)
        self.chk_genera_cxp = QCheckBox("Generar Cuenta por Pagar (CxP)"); self.chk_genera_cxp.setChecked(True)
        form_conta.addRow("", self.chk_genera_cxp)
        self.txt_comentario = QTextEdit(); self.txt_comentario.setMaximumHeight(60)
        form_conta.addRow("Observaciones:", self.txt_comentario)
        self.tabs.addTab(tab_conta, "⚙️ Ajustes")

        main_layout.addWidget(self.tabs)

        # Auditoría y Botones Inferiores 
        frm_audit = QFrame()
        frm_audit.setStyleSheet("background-color: #E8E8E8; border-radius: 4px; margin-top: 5px;")
        layout_audit = QHBoxLayout(frm_audit)
        estilo_audit = "font-size: 10px; color: #555;"
        self.lbl_creado_por = QLabel("Creado por: -"); self.lbl_creado_por.setStyleSheet(estilo_audit)
        self.lbl_fecha_crea = QLabel("Registro: -"); self.lbl_fecha_crea.setStyleSheet(estilo_audit)
        self.lbl_modif_por = QLabel("Modif. por: -"); self.lbl_modif_por.setStyleSheet(estilo_audit)
        self.lbl_fecha_mod = QLabel("Modificación: -"); self.lbl_fecha_mod.setStyleSheet(estilo_audit)
        layout_audit.addWidget(self.lbl_creado_por); layout_audit.addWidget(self.lbl_fecha_crea)
        layout_audit.addStretch()
        layout_audit.addWidget(self.lbl_modif_por); layout_audit.addWidget(self.lbl_fecha_mod)
        main_layout.addWidget(frm_audit)

        btn_layout = QHBoxLayout()
        self.btn_anular = QPushButton("Anular Compra")
        self.btn_anular.setStyleSheet("background-color: #d9534f; color: white;")
        self.btn_anular.setFixedHeight(40)
        self.btn_anular.clicked.connect(self.anular_compra)
        
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setStyleSheet("background-color: #6c757d; color: white;")
        self.btn_cancelar.setFixedHeight(40)
        self.btn_cancelar.clicked.connect(self.cancelar_accion)
        
        self.btn_guardar = QPushButton("Procesar y Guardar")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_guardar.clicked.connect(self.guardar_compra)
        
        self.btn_salir = QPushButton("Salir")
        self.btn_salir.setFixedHeight(40)
        self.btn_salir.setStyleSheet("background-color: #343a40; color: white; font-weight: bold;")
        self.btn_salir.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_anular)
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_salir)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
    def obtener_data_combo(self, combo):
        texto = combo.currentText()
        if not texto: return None
        idx = combo.findText(texto)
        if idx >= 0: return combo.itemData(idx)
        return None

    def set_estado_formulario(self, activo):
        if self.rol_usuario != "Administrador":
            activo = False
            self.btn_guardar.setText("Solo Lectura")
            self.btn_anular.setToolTip("Sin Permisos")
            
        # Bloqueo ERP: Si hay un documento cargado, forzamos Solo Lectura
        if self.doc_seleccionado is not None:
            activo = False
            self.btn_guardar.setEnabled(False)
            self.btn_guardar.setText("Documento Procesado")
        else:
            if self.rol_usuario == "Administrador":
                self.btn_guardar.setEnabled(True)
                self.btn_guardar.setText("Procesar y Guardar")
            
        widgets_a_cambiar = [
            self.txt_factura, self.txt_control, self.txt_comentario,
            self.cmb_proveedor, self.cmb_tipo_compra, self.cmb_moneda, 
            self.cmb_almacen, self.spin_costo_add,
            self.dt_compra, self.dt_recepcion, self.dt_vencimiento,
            self.chk_genera_cxp, self.tabla_productos
        ]
        
        for w in widgets_a_cambiar: w.setEnabled(activo)
        
        
        # El botón de anular se activa si hay doc, el usuario es ADMIN, y el estatus NO es ANULADA
        if self.doc_seleccionado is not None and self.estatus_actual != 'ANULADA' and self.rol_usuario == "Administrador":
            self.btn_anular.setEnabled(True)
        else:
            self.btn_anular.setEnabled(False)
            
        self.btn_cancelar.setEnabled(True)

    def cancelar_accion(self):
        self.doc_seleccionado = None
        self.estatus_actual = None
        self.lbl_titulo_form.setText("Seleccione una compra o registre una nueva")
        self.lbl_estado_doc.hide() 
        
        self.txt_doc_interno.setText("AUTOGENERADO AL GUARDAR")
        self.txt_factura.clear(); self.txt_control.clear(); self.txt_comentario.clear()
        
        hoy = QDate.currentDate()
        self.dt_compra.setDate(hoy); self.dt_recepcion.setDate(hoy); self.dt_vencimiento.setDate(hoy.addDays(30))
        
        self.tabla_productos.setRowCount(0)
        self.lbl_totales.setText("TOTAL: 0.00")
        
        self.chk_genera_cxp.setChecked(True)
        self.spin_costo_add.setValue(0.0)
        
        self.cmb_proveedor.setCurrentIndex(-1)
        
        if self.cmb_moneda.count() > 0: self.cmb_moneda.setCurrentIndex(0)
        if self.cmb_tipo_compra.count() > 0: self.cmb_tipo_compra.setCurrentIndex(0)
        if self.cmb_almacen.count() > 0: self.cmb_almacen.setCurrentIndex(0)
        
        self.tabs.setCurrentIndex(0)
        self.lbl_creado_por.setText("Creado por: -"); self.lbl_fecha_crea.setText("Fecha: -")
        self.lbl_modif_por.setText("Modif. por: -"); self.lbl_fecha_mod.setText("Fecha: -")
        
        self.set_estado_formulario(False)

    @manejar_error
    def limpiar_formulario(self):
        self.cancelar_accion()
                
        self.lbl_titulo_form.setText("Registrando Nueva Compra")
        self.set_estado_formulario(True)

        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT public.fn_obtener_proximo_correlativo(%s, 'COMPRAS');", (self.cod_compania,))
                proximo_numero = cur.fetchone()[0]
                if proximo_numero and proximo_numero != 'NO CONFIGURADO':
                    self.txt_doc_interno.setText(proximo_numero)
                    
        # NUEVO: Aseguramos que la tabla inicie con 1 fila vacía para poder tipear
        self.tabla_productos.setRowCount(0)
        self.asegurar_fila_vacia()

    def abrir_buscador_compras(self):
        modal = BuscadorComprasModal(self.cod_compania, self)
        if modal.exec() == QDialog.DialogCode.Accepted and modal.doc_seleccionado:
            self.cargar_datos_formulario(modal.doc_seleccionado)

    def asegurar_fila_vacia(self):
        """Añade una fila en blanco al final de la tabla para escribir un nuevo producto."""
        self.tabla_productos.blockSignals(True) # Apagamos señales para no crear un bucle
        
        row = self.tabla_productos.rowCount()
        self.tabla_productos.insertRow(row)
        
        self.tabla_productos.setItem(row, 0, QTableWidgetItem("")) # Código
        
        item_desc = QTableWidgetItem("")
        item_desc.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled) # Solo lectura
        self.tabla_productos.setItem(row, 1, item_desc)
        
        self.tabla_productos.setItem(row, 2, QTableWidgetItem("1.00")) # Cantidad
        self.tabla_productos.setItem(row, 3, QTableWidgetItem("0.0000")) # Costo U.
        
        item_total = QTableWidgetItem("0.0000")
        item_total.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled) # Solo lectura
        self.tabla_productos.setItem(row, 4, item_total)
        
        btn_eliminar = QPushButton("❌")
        btn_eliminar.setProperty("class", "btn-eliminar-fila")
        btn_eliminar.clicked.connect(self.eliminar_fila_tabla)
        self.tabla_productos.setCellWidget(row, 5, btn_eliminar)
        
        self.tabla_productos.blockSignals(False)

    @manejar_error
    def procesar_edicion_celda(self, row, col):
        """Se dispara cada vez que el usuario modifica una celda."""
        self.tabla_productos.blockSignals(True) # Prevenir recursividad infinita
        
        try:
            if col == 0: # El usuario escribió/cambió un Código
                item_cod = self.tabla_productos.item(row, 0)
                cod_prod = item_cod.text().strip().upper() if item_cod else ""
                
                if not cod_prod:
                    # Si borran el código, limpiamos la fila
                    self.tabla_productos.item(row, 1).setText("")
                    self.tabla_productos.item(row, 2).setText("1.00")
                    self.tabla_productos.item(row, 3).setText("0.0000")
                    self.tabla_productos.item(row, 4).setText("0.0000")
                else:
                    item_cod.setText(cod_prod) # Forzar mayúsculas
                    # Buscar en BD
                    with psycopg2.connect(**DB_PARAMS) as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT nombre, costo_final_usd FROM inv_productos WHERE cod_compania=%s AND cod_producto=%s", (self.cod_compania, cod_prod))
                            prod = cur.fetchone()
                            
                            if prod:
                                self.tabla_productos.item(row, 1).setText(prod[0]) # Descripción
                                self.tabla_productos.item(row, 3).setText(f"{prod[1]:.4f}") # Último costo
                                
                                # Si es la última fila, agregamos una nueva vacía debajo
                                if row == self.tabla_productos.rowCount() - 1:
                                    self.asegurar_fila_vacia()
                            else:
                                QMessageBox.warning(self, "No Encontrado", f"El código '{cod_prod}' no existe.")
                                item_cod.setText("")
                                
            # Si editaron Código(0), Cantidad(2) o Costo(3), recalculamos el Total
            if col in (0, 2, 3):
                try:
                    cant = float(self.tabla_productos.item(row, 2).text())
                    costo = float(self.tabla_productos.item(row, 3).text())
                    self.tabla_productos.item(row, 4).setText(f"{(cant * costo):.4f}")
                except ValueError:
                    pass # Evitar crash si escriben letras temporalmente
                
        finally:
            self.calcular_totales()
            self.tabla_productos.blockSignals(False)

    def eliminar_fila_tabla(self):
        btn_pulsado = self.sender()
        if btn_pulsado:
            for row in range(self.tabla_productos.rowCount()):
                if self.tabla_productos.cellWidget(row, 5) == btn_pulsado:
                    # Prevenir borrar la última fila si es la única vacía
                    if self.tabla_productos.rowCount() == 1:
                        self.tabla_productos.item(0, 0).setText("")
                    else:
                        self.tabla_productos.removeRow(row)
                        
                    self.calcular_totales()
                    break

    def calcular_totales(self):
        total_general = 0.0
        for row in range(self.tabla_productos.rowCount()):
            try:
                cant = float(self.tabla_productos.item(row, 2).text())
                costo = float(self.tabla_productos.item(row, 3).text())
                total_linea = cant * costo
                self.tabla_productos.item(row, 4).setText(f"{total_linea:.4f}")
                total_general += total_linea
            except ValueError: pass
        self.lbl_totales.setText(f"TOTAL: {total_general:,.2f}")

    @manejar_error
    def cargar_combo_proveedores(self):
        self.cmb_proveedor.clear()
        
        # 1. OPTIMIZACIÓN: Apagar repintado y señales visuales
        self.cmb_proveedor.setUpdatesEnabled(False)
        self.cmb_proveedor.blockSignals(True)
        
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cod_proveedor, nombre_proveedor, rif FROM com_proveedores WHERE cod_compania = %s AND estatus = TRUE ORDER BY nombre_proveedor", (self.cod_compania,))
                for p in cur.fetchall():
                    self.cmb_proveedor.addItem(f"{p[1]} | RIF: {p[2]}", p[0])
                    
        self.cmb_proveedor.setCurrentIndex(-1)
        self.completer_prov.setModel(self.cmb_proveedor.model())
        
        # 2. OPTIMIZACIÓN: Volver a encender la UI de un solo golpe
        self.cmb_proveedor.blockSignals(False)
        self.cmb_proveedor.setUpdatesEnabled(True)

    @manejar_error
    def cargar_combo_almacenes(self):
        self.cmb_almacen.clear()
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cod_almacen, nombre_almacen FROM inv_almacenes WHERE cod_compania = %s AND activo = TRUE", (self.cod_compania,))
                for a in cur.fetchall():
                    self.cmb_almacen.addItem(f"{a[0]} - {a[1]}", a[0])

    @manejar_error
    def cargar_datos_formulario(self, doc_interno): 
        self.doc_seleccionado = doc_interno
        self.lbl_titulo_form.setText("Cargando datos...") 
        self.lbl_estado_doc.hide()
        
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT c.cod_proveedor, c.num_factura, c.num_control, c.fecha_compra, c.fecha_recepcion, 
                           c.fecha_vencimiento, c.moneda, c.genera_cxp, c.tipo_compra, c.almacen, 
                           c.costo_adicional, c.comentario, 
                           u1.usuario_login, c.fecha_registro, u2.usuario_login, c.fecha_modifica,
                           c.estatus
                    FROM trx_compras c
                    LEFT JOIN seg_usuarios u1 ON c.id_user_crea = u1.id_usuario
                    LEFT JOIN seg_usuarios u2 ON c.id_user_mod = u2.id_usuario
                    WHERE c.cod_compania = %s AND c.num_doc_interno = %s
                """
                cur.execute(query, (self.cod_compania, doc_interno))
                d = cur.fetchone()
                
                if d:
                    self.lbl_titulo_form.setText(f"Viendo Compra Doc: {doc_interno} - Fact: {d[1]}")
                    self.txt_doc_interno.setText(doc_interno)
                    
                    idx_p = self.cmb_proveedor.findData(d[0])
                    if idx_p >= 0: self.cmb_proveedor.setCurrentIndex(idx_p)
                    
                    self.txt_factura.setText(d[1] or "")
                    self.txt_control.setText(d[2] or "")
                    
                    if d[3]: self.dt_compra.setDate(d[3])
                    if d[4]: self.dt_recepcion.setDate(d[4])
                    if d[5]: self.dt_vencimiento.setDate(d[5])
                    
                    self.cmb_moneda.setCurrentText(d[6] or "Bs")
                    self.chk_genera_cxp.setChecked(bool(d[7]))
                    self.cmb_tipo_compra.setCurrentText(d[8] or "")
                    
                    idx_a = self.cmb_almacen.findData(d[9])
                    if idx_a >= 0: self.cmb_almacen.setCurrentIndex(idx_a)
                    
                    self.spin_costo_add.setValue(float(d[10] or 0.0))
                    self.txt_comentario.setText(d[11] or "")
                    
                    f_crea = d[13].strftime("%d/%m/%Y %I:%M %p") if d[13] else "-"
                    f_mod = d[15].strftime("%d/%m/%Y %I:%M %p") if d[15] else "-"
                    self.lbl_creado_por.setText(f"Creado por: {d[12] or '-'}"); self.lbl_fecha_crea.setText(f"Fecha: {f_crea}")
                    self.lbl_modif_por.setText(f"Modif. por: {d[14] or '-'}"); self.lbl_fecha_mod.setText(f"Fecha: {f_mod}")

                    # Si viene Nulo o con espacios, lo forzamos a un texto limpio
                    self.estatus_actual = str(d[16]).strip().upper() if d[16] else 'PROCESADA'

                self.tabla_productos.setRowCount(0)
                cur.execute("""
                    SELECT d.cod_producto, p.nombre, d.cantidad, d.costo_unitario, d.total_linea 
                    FROM trx_compras_detalle d
                    JOIN inv_productos p ON d.cod_producto = p.cod_producto AND d.cod_compania = p.cod_compania
                    WHERE d.cod_compania = %s AND d.num_doc_interno = %s
                """, (self.cod_compania, doc_interno))
                
                detalles = cur.fetchall()
                # Para evitar que se disparen eventos de edición accidentalmente al cargar
                self.tabla_productos.blockSignals(True) 
                
                for r, det in enumerate(detalles):
                    self.tabla_productos.insertRow(r)
                    self.tabla_productos.setItem(r, 0, QTableWidgetItem(str(det[0])))
                    self.tabla_productos.setItem(r, 1, QTableWidgetItem(str(det[1])))
                    self.tabla_productos.setItem(r, 2, QTableWidgetItem(str(det[2])))
                    self.tabla_productos.setItem(r, 3, QTableWidgetItem(str(det[3])))
                    self.tabla_productos.setItem(r, 4, QTableWidgetItem(str(det[4])))
                    
                    btn_elim = QPushButton("❌")
                    btn_elim.setProperty("class", "btn-eliminar-fila")
                    btn_elim.setEnabled(False) # Bloqueado porque solo estamos viendo
                    self.tabla_productos.setCellWidget(r, 5, btn_elim)
                
                self.tabla_productos.blockSignals(False)
                self.calcular_totales()
                
                if self.estatus_actual == 'ANULADA':
                    self.lbl_estado_doc.show()
                else:
                    self.lbl_estado_doc.hide()
                    
                # Siempre forzamos a False porque NUNCA se edita un documento cargado
                self.set_estado_formulario(False)

    @manejar_error
    def guardar_compra(self):
        if self.rol_usuario != "Administrador": return
        
        # Bloqueo ERP estricto
        if self.doc_seleccionado is not None:
            QMessageBox.warning(self, "Bloqueo ERP", "Los documentos procesados no pueden ser modificados.\n\nSi detecta un error, por favor anule el documento y registre uno nuevo.")
            return

        factura = self.txt_factura.text().strip()
        cod_prov = self.obtener_data_combo(self.cmb_proveedor)
        cod_almacen = self.cmb_almacen.currentData()
        
        if not factura or not cod_prov or not cod_almacen:
            QMessageBox.warning(self, "Datos incompletos", "Factura, Proveedor válido y Almacén de Entrada son obligatorios.")
            return

        self.calcular_totales()
        
        detalles_a_guardar = []
        for row in range(self.tabla_productos.rowCount()):
            try:
                item_cod = self.tabla_productos.item(row, 0)
                if not item_cod or not item_cod.text().strip(): continue

                cod_p = item_cod.text().strip()
                cant = float(self.tabla_productos.item(row, 2).text())
                costo = float(self.tabla_productos.item(row, 3).text())
                total_l = float(self.tabla_productos.item(row, 4).text())
                detalles_a_guardar.append((cod_p, cant, costo, total_l))
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Error en tabla", f"Verifique que las cantidades y costos en la fila {row + 1} sean números válidos.")
                return
                
        if not detalles_a_guardar:
            QMessageBox.warning(self, "Tabla vacía", "Debe agregar al menos un producto a la compra antes de guardar.")
            return

        try:
            with psycopg2.connect(**DB_PARAMS) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TIME ZONE 'America/Caracas'")
                    
                    # ---------------- FLUJO: NUEVO INGRESO (Único permitido) ----------------
                    cur.execute("SELECT public.fn_consumir_correlativo(%s, 'COMPRAS');", (self.cod_compania,))
                    doc = cur.fetchone()[0]

                    params_ins = (
                        cod_prov, factura, self.txt_control.text(), 
                        self.dt_compra.date().toString("yyyy-MM-dd"), self.dt_recepcion.date().toString("yyyy-MM-dd"), 
                        self.dt_vencimiento.date().toString("yyyy-MM-dd"), self.cmb_moneda.currentText(), 
                        self.chk_genera_cxp.isChecked(), self.cmb_tipo_compra.currentText(), 
                        cod_almacen, self.spin_costo_add.value(), self.txt_comentario.toPlainText(), 
                        'PROCESADA', self.cod_compania, doc, self.id_usuario_actual
                    )
                    query_ins = """
                        INSERT INTO trx_compras (
                            cod_proveedor, num_factura, num_control, fecha_compra, fecha_recepcion, fecha_vencimiento,
                            moneda, genera_cxp, tipo_compra, almacen, costo_adicional, comentario, estatus,
                            cod_compania, num_doc_interno, id_user_crea
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    cur.execute(query_ins, params_ins)

                    # --- INSERCIÓN EN TABLAS DE INVENTARIO ---
                    for cod_p, cant, costo, total_l in detalles_a_guardar:
                        cur.execute("""
                            INSERT INTO trx_compras_detalle (cod_compania, num_doc_interno, cod_producto, cantidad, costo_unitario, total_linea) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (self.cod_compania, doc, cod_p, cant, costo, total_l))
                        
                        # Obtener saldo previo para reflejarlo correctamente en el historial
                        cur.execute("SELECT cantidad_real FROM inv_existencias WHERE cod_compania=%s AND cod_almacen=%s AND cod_producto=%s", (self.cod_compania, cod_almacen, cod_p))
                        row_saldo = cur.fetchone()
                        saldo_previo = row_saldo[0] if row_saldo else 0
                        saldo_post_movimiento = saldo_previo + cant

                        # Ya NO tocamos inv_existencias. Insertamos el movimiento y el Trigger hace el resto.
                        params_mov = (
                            self.cod_compania, cod_p, cod_almacen, 'ENTRADA', 'COMPRA', 
                            doc, cod_prov, cant, saldo_post_movimiento, costo, self.id_usuario_actual
                        )
                        cur.execute("""
                            INSERT INTO inv_movimientos (
                                cod_compania, cod_producto, cod_almacen, tipo_movimiento, concepto, 
                                documento_origen, cod_proveedor, cantidad, saldo_cantidad, costo_unitario_usd, id_usuario
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, params_mov)
                        
        except psycopg2.IntegrityError:
            QMessageBox.warning(self, "Error de Duplicidad", "El código interno de documento ya existe o hay un registro duplicado.")
            return

        QMessageBox.information(self, "Éxito", f"Operación completada exitosamente.\nDocumento: {doc}")
        self.cancelar_accion()

    @manejar_error
    def anular_compra(self):
        if self.rol_usuario != "Administrador": return
        if not self.doc_seleccionado: return
        
        resp = QMessageBox.question(self, "Confirmar Anulación", 
            "Al ANULAR la compra, la mercancía se RESTARÁ del almacén y el documento quedará invalidado de forma permanente.\n\n¿Desea continuar?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if resp == QMessageBox.StandardButton.Yes:
            with psycopg2.connect(**DB_PARAMS) as conn:
                with conn.cursor() as cur:
                    # 1. Verificar estatus y obtener datos
                    cur.execute("SELECT estatus, almacen, cod_proveedor FROM trx_compras WHERE cod_compania=%s AND num_doc_interno=%s", (self.cod_compania, self.doc_seleccionado))
                    row = cur.fetchone()
                    
                    if not row or row[0] == 'ANULADA':
                        QMessageBox.warning(self, "Aviso", "Este documento ya se encuentra anulado.")
                        return
                        
                    almacen = row[1]
                    cod_prov = row[2]

                    # 2. NUEVO: Validación Preventiva de Inventario (Alcabala)
                    # Obtenemos todo lo que intentamos devolver
                    cur.execute("SELECT cod_producto, cantidad, costo_unitario FROM trx_compras_detalle WHERE cod_compania=%s AND num_doc_interno=%s", (self.cod_compania, self.doc_seleccionado))
                    detalles_compra = cur.fetchall()

                    for cod_p, cant_a_restar, costo in detalles_compra:
                        # Preguntamos cuánto hay realmente HOY en el almacén
                        cur.execute("SELECT cantidad_real FROM inv_existencias WHERE cod_compania=%s AND cod_almacen=%s AND cod_producto=%s", (self.cod_compania, almacen, cod_p))
                        row_stock = cur.fetchone()
                        stock_actual = row_stock[0] if row_stock else 0

                        # Si intentamos devolver más de lo que hay, abortamos amigablemente
                        if stock_actual < cant_a_restar:
                            QMessageBox.warning(self, "Stock Insuficiente", 
                                f"No se puede anular esta compra.\n\n"
                                f"El producto '{cod_p}' actualmente tiene solo {stock_actual} unidades en el almacén, "
                                f"pero la compra intentaría devolver {cant_a_restar} unidades.\n\n"
                                f"(Es posible que la mercancía ya se haya vendido, movido, o el inventario esté desincronizado en las pruebas).")
                            return # Cancelamos el proceso sin tocar la base de datos
                    
                    # 3. Si pasó la alcabala, Actualizamos el estatus a ANULADA
                    cur.execute("UPDATE trx_compras SET estatus = 'ANULADA', id_user_mod = %s WHERE cod_compania=%s AND num_doc_interno=%s", 
                                (self.id_usuario_actual, self.cod_compania, self.doc_seleccionado))
                    
                    # 4. Registrar movimiento de salida. El trigger de la base de datos hará la resta real.
                    for cod_p, cant_a_restar, costo in detalles_compra:
                        cur.execute("SELECT cantidad_real FROM inv_existencias WHERE cod_compania=%s AND cod_almacen=%s AND cod_producto=%s", (self.cod_compania, almacen, cod_p))
                        saldo_previo = cur.fetchone()[0]
                        saldo_post_movimiento = saldo_previo - cant_a_restar # Calculamos el saldo final para el historial
                        
                        params_mov = (
                            self.cod_compania, cod_p, almacen, 'SALIDA', 'ANULACION DE COMPRA', 
                            self.doc_seleccionado, cod_prov, cant_a_restar, saldo_post_movimiento, costo, self.id_usuario_actual
                        )
                        cur.execute("""
                            INSERT INTO inv_movimientos (
                                cod_compania, cod_producto, cod_almacen, tipo_movimiento, concepto, 
                                documento_origen, cod_proveedor, cantidad, saldo_cantidad, costo_unitario_usd, id_usuario
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, params_mov)
                    
            QMessageBox.information(self, "Documento Anulado", "La compra ha sido anulada exitosamente. El inventario ha sido revertido automáticamente.")
            self.cancelar_accion()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComprasForm(1, 1, "EMPRESA PRUEBA CA")
    window.showMaximized()
    sys.exit(app.exec())