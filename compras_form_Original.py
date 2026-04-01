import sys
import psycopg2
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QListWidget, QFrame, QApplication, QDateEdit, QDoubleSpinBox,
    QTableWidget, QHeaderView, QTableWidgetItem, QCompleter, QSizePolicy
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt, QDate, QTimer
from db_config import DB_PARAMS

# 1. Importamos el manejador de errores
from error_handler import manejar_error

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
        self.cargar_combo_productos()
        self.cargar_combo_almacenes()
        
        self.cargar_lista_compras()
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
        main_layout = QHBoxLayout()

        # --- PANEL IZQUIERDO ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("📦 Historial de Compras"))
        
        layout_buscar_hist = QHBoxLayout()
        self.txt_buscar_historial = QLineEdit()
        self.txt_buscar_historial.setPlaceholderText("Buscar N° Factura, Doc o Proveedor...")
        
        # --- BÚSQUEDA INTELIGENTE (Patrón Debounce) ---
        self.timer_busqueda = QTimer()
        self.timer_busqueda.setSingleShot(True) # Se ejecuta una sola vez al terminar el tiempo
        self.timer_busqueda.timeout.connect(self.cargar_lista_compras)
        
        # Cada vez que el usuario teclea, se reinicia el cronómetro
        self.txt_buscar_historial.textChanged.connect(self.reiniciar_timer_busqueda)
        
        # Mantenemos la tecla 'Enter' activa por si el usuario teclea y da enter muy rápido
        self.txt_buscar_historial.returnPressed.connect(self.cargar_lista_compras)
        
        self.btn_buscar_historial = QPushButton("Buscar")
        self.btn_buscar_historial.setProperty("class", "btn-buscar-mini")
        self.btn_buscar_historial.clicked.connect(self.cargar_lista_compras)
        
        layout_buscar_hist.addWidget(self.txt_buscar_historial)
        layout_buscar_hist.addWidget(self.btn_buscar_historial)
        left_panel.addLayout(layout_buscar_hist)
        
        self.lista_compras = QListWidget()
        self.lista_compras.itemClicked.connect(self.cargar_datos_formulario)
        left_panel.addWidget(self.lista_compras)
        
        self.btn_nuevo = QPushButton("+ Registrar Nueva Compra")
        self.btn_nuevo.clicked.connect(self.limpiar_formulario)
        left_panel.addWidget(self.btn_nuevo)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(300)
        main_layout.addWidget(left_widget)

        # --- PANEL DERECHO ---
        right_layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
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
        right_layout.addLayout(header_layout)

        # PESTAÑAS
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
        
        lbl_titulo_prod = QLabel("🛒 Detalles de Productos")
        lbl_titulo_prod.setStyleSheet("font-weight: bold; color: #2C3E50;")
        layout_general_main.addWidget(lbl_titulo_prod)

        layout_add = QHBoxLayout()
        
        self.cmb_producto = QComboBox()
        self.cmb_producto.setMinimumWidth(300)
        self.cmb_producto.setEditable(True)
        self.cmb_producto.lineEdit().setPlaceholderText("--- Escriba o seleccione un Producto ---")
        self.cmb_producto.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.completer_prod = QCompleter(self)
        self.completer_prod.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer_prod.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cmb_producto.setCompleter(self.completer_prod)
        
        self.spin_cantidad = QDoubleSpinBox()
        self.spin_cantidad.setRange(0.01, 999999.99)
        self.spin_cantidad.setValue(1.0)
        
        self.spin_costo = QDoubleSpinBox()
        self.spin_costo.setRange(0.00, 99999999.99)
        self.spin_costo.setDecimals(4)
        
        self.btn_add_prod = QPushButton("➕ Agregar")
        self.btn_add_prod.setStyleSheet("background-color: #17A2B8; color: white;")
        self.btn_add_prod.clicked.connect(self.agregar_producto_a_tabla)

        layout_add.addWidget(QLabel("Producto:"))
        layout_add.addWidget(self.cmb_producto, 1)
        layout_add.addWidget(QLabel("Cant:"))
        layout_add.addWidget(self.spin_cantidad)
        layout_add.addWidget(QLabel("Costo U:"))
        layout_add.addWidget(self.spin_costo)
        layout_add.addWidget(self.btn_add_prod)
        layout_general_main.addLayout(layout_add)

        self.tabla_productos = QTableWidget(0, 6)
        self.tabla_productos.setHorizontalHeaderLabels(["Código", "Descripción", "Cantidad", "Costo U.", "Total", "Acción"])
        self.tabla_productos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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

        right_layout.addWidget(self.tabs)

        # Auditoría
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
        right_layout.addWidget(frm_audit)

        # Botones Principales Inferiores
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
        
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout)
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
            self.cmb_producto, self.cmb_almacen, self.spin_cantidad, 
            self.spin_costo, self.spin_costo_add,
            self.dt_compra, self.dt_recepcion, self.dt_vencimiento,
            self.chk_genera_cxp, self.btn_add_prod, self.tabla_productos
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
        self.lista_compras.clearSelection()
        
        self.txt_doc_interno.setText("AUTOGENERADO AL GUARDAR")
        self.txt_factura.clear(); self.txt_control.clear(); self.txt_comentario.clear()
        
        hoy = QDate.currentDate()
        self.dt_compra.setDate(hoy); self.dt_recepcion.setDate(hoy); self.dt_vencimiento.setDate(hoy.addDays(30))
        
        self.tabla_productos.setRowCount(0)
        self.lbl_totales.setText("TOTAL: 0.00")
        
        self.chk_genera_cxp.setChecked(True)
        self.spin_costo_add.setValue(0.0)
        self.spin_cantidad.setValue(1.0)
        self.spin_costo.setValue(0.0)
        
        self.cmb_proveedor.setCurrentIndex(-1)
        self.cmb_producto.setCurrentIndex(-1)
        
        if self.cmb_moneda.count() > 0: self.cmb_moneda.setCurrentIndex(0)
        if self.cmb_tipo_compra.count() > 0: self.cmb_tipo_compra.setCurrentIndex(0)
        if self.cmb_almacen.count() > 0: self.cmb_almacen.setCurrentIndex(0)
        
        self.tabs.setCurrentIndex(0)
        self.lbl_creado_por.setText("Creado por: -"); self.lbl_fecha_crea.setText("Fecha: -")
        self.lbl_modif_por.setText("Modif. por: -"); self.lbl_fecha_mod.setText("Fecha: -")
        
        self.set_estado_formulario(False)
    
    def reiniciar_timer_busqueda(self):
        """
        Reinicia el cronómetro de búsqueda inteligente. 
        Espera 400 milisegundos después de la última pulsación de tecla antes de consultar a la BD.
        """
        self.timer_busqueda.start(400)

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

    def agregar_producto_a_tabla(self):
        cod_prod = self.obtener_data_combo(self.cmb_producto)
        if not cod_prod:
            QMessageBox.warning(self, "Advertencia", "Por favor, busque y seleccione un producto.")
            return
            
        desc_prod = self.cmb_producto.currentText()
        cant = self.spin_cantidad.value()
        costo = self.spin_costo.value()
        total_linea = cant * costo
        
        row_position = self.tabla_productos.rowCount()
        self.tabla_productos.insertRow(row_position)
        
        item_cod = QTableWidgetItem(str(cod_prod))
        item_cod.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        item_desc = QTableWidgetItem(str(desc_prod))
        item_desc.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        item_cant = QTableWidgetItem(f"{cant:.2f}")
        item_costo = QTableWidgetItem(f"{costo:.4f}")
        item_total = QTableWidgetItem(f"{total_linea:.4f}")
        item_total.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        
        btn_eliminar = QPushButton("❌")
        btn_eliminar.setProperty("class", "btn-eliminar-fila")
        btn_eliminar.clicked.connect(self.eliminar_fila_tabla)
        
        self.tabla_productos.setItem(row_position, 0, item_cod)
        self.tabla_productos.setItem(row_position, 1, item_desc)
        self.tabla_productos.setItem(row_position, 2, item_cant)
        self.tabla_productos.setItem(row_position, 3, item_costo)
        self.tabla_productos.setItem(row_position, 4, item_total)
        self.tabla_productos.setCellWidget(row_position, 5, btn_eliminar)
        
        self.spin_cantidad.setValue(1.0)
        self.spin_costo.setValue(0.0)
        self.cmb_producto.setCurrentIndex(-1)
        self.calcular_totales()

    def eliminar_fila_tabla(self):
        btn_pulsado = self.sender()
        if btn_pulsado:
            for row in range(self.tabla_productos.rowCount()):
                if self.tabla_productos.cellWidget(row, 5) == btn_pulsado:
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
    def cargar_combo_productos(self):
        self.cmb_producto.clear()
        
        # 1. OPTIMIZACIÓN: Apagar repintado y señales visuales
        self.cmb_producto.setUpdatesEnabled(False)
        self.cmb_producto.blockSignals(True)
        
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cod_producto, nombre FROM inv_productos WHERE cod_compania = %s AND es_activo = TRUE ORDER BY nombre", (self.cod_compania,))
                for p in cur.fetchall():
                    self.cmb_producto.addItem(f"{p[0]} | {p[1]}", p[0])
                    
        self.cmb_producto.setCurrentIndex(-1)
        self.completer_prod.setModel(self.cmb_producto.model())
        
        # 2. OPTIMIZACIÓN: Volver a encender la UI de un solo golpe
        self.cmb_producto.blockSignals(False)
        self.cmb_producto.setUpdatesEnabled(True)

    @manejar_error
    def cargar_combo_almacenes(self):
        self.cmb_almacen.clear()
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cod_almacen, nombre_almacen FROM inv_almacenes WHERE cod_compania = %s AND activo = TRUE", (self.cod_compania,))
                for a in cur.fetchall():
                    self.cmb_almacen.addItem(f"{a[0]} - {a[1]}", a[0])

    @manejar_error
    def cargar_lista_compras(self):
        self.lista_compras.clear()
        
        # 1. OPTIMIZACIÓN: Apagar repintado del historial
        self.lista_compras.setUpdatesEnabled(False)
        
        filtro = self.txt_buscar_historial.text().strip()
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                if filtro:
                    # 2. OPTIMIZACIÓN: Añadir LIMIT 100 para no sobrecargar la RAM
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
                    
                for doc in cur.fetchall():
                    f_compra = doc[3].strftime("%d/%m/%Y")
                    estado_etiqueta = "[ANULADA] " if doc[4] == 'ANULADA' else ""
                    self.lista_compras.addItem(f"{estado_etiqueta}Doc: {doc[0]} | Fact: {doc[1]}\nProv: {doc[2]} | {f_compra}")
                    self.lista_compras.item(self.lista_compras.count()-1).setData(Qt.ItemDataRole.UserRole, doc[0])
                    
        # Volver a encender la UI de la lista
        self.lista_compras.setUpdatesEnabled(True)
        
    @manejar_error
    def cargar_datos_formulario(self, item):
        doc_interno = item.data(Qt.ItemDataRole.UserRole)
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
                
                self.calcular_totales()
                self.cmb_producto.setCurrentIndex(-1)
                
                if self.estatus_actual == 'ANULADA':
                    self.lbl_estado_doc.show()
                else:
                    self.lbl_estado_doc.hide()
                    
                # Siempre forzamos a False porque en Opción C NUNCA se edita un documento cargado
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
        self.cargar_lista_compras()

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
            self.cargar_lista_compras()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComprasForm(1, 1, "EMPRESA PRUEBA CA")
    window.showMaximized()
    sys.exit(app.exec())