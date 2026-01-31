import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QTabWidget, QCheckBox, QTableWidget, QHeaderView, 
    QGroupBox, QFormLayout, QPushButton, QFrame, QDoubleSpinBox,
    QTableWidgetItem, QFileDialog, QRadioButton, QButtonGroup, QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor

class ProductosForm(QWidget):
    def __init__(self, cod_compania, id_usuario, nombre_empresa):
        super().__init__()
        # Contexto de Base de Datos
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        
        # Variables Globales de la Ventana
        self.tasa_cambio_actual = 60.50 # ESTO DEBE VENIR DE BD (cfg_tasas)
        self.ruta_imagen_actual = ""
        
        self.setWindowTitle("Ficha Maestra de Productos")
        self.resize(1100, 750)
        self.init_ui()
        
        # Inicializar lógica (Simulado)
        self.cargar_combos_simulados()
        self.recalcular_costos_importacion() # Para inicializar ceros

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # ======================================================================
        # SECCIÓN 1: ENCABEZADO PERSISTENTE (KPIs y Datos Clave)
        # ======================================================================
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 8px;")
        header_layout = QHBoxLayout(header_frame)

        # 1.1 Imagen del Producto
        self.lbl_imagen = QLabel("SIN IMAGEN")
        self.lbl_imagen.setFixedSize(110, 110)
        self.lbl_imagen.setStyleSheet("background-color: #e9ecef; border: 2px dashed #adb5bd; color: #6c757d;")
        self.lbl_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_imagen.setScaledContents(True)
        # Evento Clic para cargar imagen (se conecta luego)
        
        btn_img_layout = QVBoxLayout()
        btn_img_layout.addWidget(self.lbl_imagen)
        self.btn_cargar_img = QPushButton("Cambiar")
        self.btn_cargar_img.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cargar_img.clicked.connect(self.seleccionar_imagen)
        btn_img_layout.addWidget(self.btn_cargar_img)
        
        header_layout.addLayout(btn_img_layout)

        # 1.2 Datos de Identificación Principal
        ident_layout = QFormLayout()
        
        self.txt_sku = QLineEdit()
        self.txt_sku.setPlaceholderText("Ej: PROD-10025")
        self.txt_sku.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Descripción Comercial del Producto...")
        self.txt_nombre.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50;")
        
        self.txt_barra = QLineEdit()
        self.txt_barra.setPlaceholderText("Escanee código EAN/UPC...")
        self.txt_barra.setClearButtonEnabled(True)

        ident_layout.addRow("Código SKU:", self.txt_sku)
        ident_layout.addRow("Nombre:", self.txt_nombre)
        ident_layout.addRow("Cod. Barras:", self.txt_barra)
        
        header_layout.addLayout(ident_layout, stretch=2)

        # 1.3 Estado y KPIs (Display Digital)
        kpi_layout = QVBoxLayout()
        
        # Switch Activo/Inactivo
        self.chk_activo = QCheckBox("PRODUCTO ACTIVO")
        self.chk_activo.setChecked(True)
        self.chk_activo.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 13px;")
        
        # Display de Stock Total
        lbl_stock_titulo = QLabel("Existencia Total")
        lbl_stock_titulo.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.lbl_stock_val = QLabel("0.00")
        self.lbl_stock_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_stock_val.setStyleSheet("font-size: 24px; font-weight: bold; color: #2980b9; border-bottom: 2px solid #3498db;")

        # Tasa de Cambio (Informativo)
        self.lbl_tasa = QLabel(f"Tasa Ref: {self.tasa_cambio_actual} Bs/$")
        self.lbl_tasa.setStyleSheet("color: #e67e22; font-weight: bold;")

        kpi_layout.addWidget(self.chk_activo)
        kpi_layout.addStretch()
        kpi_layout.addWidget(lbl_stock_titulo)
        kpi_layout.addWidget(self.lbl_stock_val)
        kpi_layout.addWidget(self.lbl_tasa)
        
        header_layout.addLayout(kpi_layout, stretch=1)
        main_layout.addWidget(header_frame)

        # ======================================================================
        # SECCIÓN 2: PESTAÑAS DETALLADAS
        # ======================================================================
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #ccc; }")

        # >> Pestaña 1: General
        self.tab_general = QWidget()
        self.setup_tab_general()
        self.tabs.addTab(self.tab_general, "📋 Datos Generales y Logística")
        
        # >> Pestaña 2: Existencias
        self.tab_stock = QWidget()
        self.setup_tab_stock()
        self.tabs.addTab(self.tab_stock, "🏭 Existencias y Ubicaciones")
        
        # >> Pestaña 3: Costos y Precios
        self.tab_precios = QWidget()
        self.setup_tab_precios()
        self.tabs.addTab(self.tab_precios, "💰 Costos, Importación y Precios")

        main_layout.addWidget(self.tabs)

        # ======================================================================
        # SECCIÓN 3: BOTONERA DE ACCIÓN
        # ======================================================================
        btn_layout = QHBoxLayout()
        
        btn_cancelar = QPushButton("Cancelar / Salir")
        btn_cancelar.setFixedSize(120, 40)
        btn_cancelar.clicked.connect(self.close)
        
        btn_guardar = QPushButton("💾 GUARDAR PRODUCTO")
        btn_guardar.setFixedSize(180, 40)
        btn_guardar.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_guardar.clicked.connect(self.guardar_producto)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    # --------------------------------------------------------------------------
    # SETUP: PESTAÑA GENERAL
    # --------------------------------------------------------------------------
    def setup_tab_general(self):
        layout = QHBoxLayout(self.tab_general)
        
        # COLUMNA IZQUIERDA: Clasificación
        col_left = QVBoxLayout()
        grp_clasif = QGroupBox("Clasificación")
        form_clasif = QFormLayout()
        
        self.cmb_marca = QComboBox()
        self.cmb_grupo = QComboBox()
        self.cmb_unidad = QComboBox()
        self.cmb_impuesto = QComboBox()
        
        self.chk_servicio = QCheckBox("Es un Servicio (No maneja stock)")
        self.chk_lotes = QCheckBox("Controlar por Lotes y Vencimiento")
        
        form_clasif.addRow("Marca:", self.cmb_marca)
        form_clasif.addRow("Grupo / Categoría:", self.cmb_grupo)
        form_clasif.addRow("Unidad Medida:", self.cmb_unidad)
        form_clasif.addRow("Impuesto (IVA):", self.cmb_impuesto)
        form_clasif.addRow("", self.chk_servicio)
        form_clasif.addRow("", self.chk_lotes)
        
        grp_clasif.setLayout(form_clasif)
        col_left.addWidget(grp_clasif)
        
        # Datos Extras
        grp_extra = QGroupBox("Datos Administrativos")
        form_extra = QFormLayout()
        
        self.txt_cod_alterno = QLineEdit()
        self.txt_cod_alterno.setPlaceholderText("Ref. Prov. o Fabricante")
        
        self.cmb_costeo = QComboBox()
        self.cmb_costeo.addItems(["PROMEDIO PONDERADO", "ULTIMO COSTO", "PEPS (FIFO)"])
        
        self.cmb_cta_contable = QComboBox() # Cargar desde Plan de Cuentas
        
        form_extra.addRow("Cód. Alterno:", self.txt_cod_alterno)
        form_extra.addRow("Método Costeo:", self.cmb_costeo)
        form_extra.addRow("Cuenta Contable:", self.cmb_cta_contable)
        
        grp_extra.setLayout(form_extra)
        col_left.addWidget(grp_extra)
        layout.addLayout(col_left)
        
        # COLUMNA DERECHA: Logística y Volumetría
        col_right = QVBoxLayout()
        grp_logistica = QGroupBox("Dimensiones y Logística (Para Despacho)")
        form_log = QFormLayout()
        
        # Usamos SpinBox para números
        self.spin_peso = QDoubleSpinBox()
        self.spin_peso.setSuffix(" Kg")
        self.spin_peso.setRange(0, 99999.99)
        
        self.spin_alto = QDoubleSpinBox()
        self.spin_alto.setSuffix(" cm")
        self.spin_alto.setRange(0, 9999.99)
        self.spin_alto.valueChanged.connect(self.calcular_volumen)

        self.spin_ancho = QDoubleSpinBox()
        self.spin_ancho.setSuffix(" cm")
        self.spin_ancho.setRange(0, 9999.99)
        self.spin_ancho.valueChanged.connect(self.calcular_volumen)

        self.spin_prof = QDoubleSpinBox()
        self.spin_prof.setSuffix(" cm")
        self.spin_prof.setRange(0, 9999.99)
        self.spin_prof.valueChanged.connect(self.calcular_volumen)
        
        self.lbl_volumen_m3 = QLabel("0.000 m³")
        self.lbl_volumen_m3.setStyleSheet("font-weight: bold; color: #555;")
        
        self.spin_bulto = QDoubleSpinBox()
        self.spin_bulto.setDecimals(0)
        self.spin_bulto.setSuffix(" Unds")
        self.spin_bulto.setValue(1)

        form_log.addRow("Peso Bruto:", self.spin_peso)
        form_log.addRow("Alto:", self.spin_alto)
        form_log.addRow("Ancho:", self.spin_ancho)
        form_log.addRow("Profundidad:", self.spin_prof)
        form_log.addRow("Volumen Calc.:", self.lbl_volumen_m3)
        form_log.addRow("Unds x Bulto:", self.spin_bulto)
        
        grp_logistica.setLayout(form_log)
        col_right.addWidget(grp_logistica)
        
        # Descripción Larga
        grp_desc = QGroupBox("Descripción Detallada (Web / Presupuestos)")
        layout_desc = QVBoxLayout()
        self.txt_desc_larga = QLineEdit() # O QTextEdit si prefieres multilínea
        layout_desc.addWidget(self.txt_desc_larga)
        grp_desc.setLayout(layout_desc)
        col_right.addWidget(grp_desc)
        
        layout.addLayout(col_right)

    # --------------------------------------------------------------------------
    # SETUP: PESTAÑA STOCK (Multi-Almacén)
    # --------------------------------------------------------------------------
    def setup_tab_stock(self):
        layout = QVBoxLayout(self.tab_stock)
        
        info_lbl = QLabel("ℹ️ La existencia física se gestiona mediante Movimientos (Entradas/Salidas). "
                          "Aquí puede asignar ubicaciones físicas por almacén.")
        info_lbl.setStyleSheet("color: #666; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(info_lbl)
        
        # Tabla de Existencias
        self.grid_stock = QTableWidget()
        self.grid_stock.setColumnCount(6)
        headers = ["Almacén", "Ubicación (Pasillo/Estante)", "Existencia Real", "Comprometido", "Por Llegar", "Disponible"]
        self.grid_stock.setHorizontalHeaderLabels(headers)
        self.grid_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_stock.verticalHeader().setVisible(False)
        self.grid_stock.setAlternatingRowColors(True)
        
        # Ejemplo Visual (Esto se llenará con DB)
        self.grid_stock.setRowCount(2)
        # Fila 1
        self.grid_stock.setItem(0, 0, QTableWidgetItem("ALM-01: PRINCIPAL"))
        self.grid_stock.setItem(0, 1, QTableWidgetItem("P-05-E-02")) # Editable
        self.grid_stock.setItem(0, 2, QTableWidgetItem("100")) # Solo lectura
        self.grid_stock.setItem(0, 3, QTableWidgetItem("10"))  # Solo lectura
        self.grid_stock.setItem(0, 4, QTableWidgetItem("50"))  # Solo lectura
        item_disp = QTableWidgetItem("90")
        item_disp.setForeground(QColor("green"))
        item_disp.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.grid_stock.setItem(0, 5, item_disp)
        
        layout.addWidget(self.grid_stock)

    # --------------------------------------------------------------------------
    # SETUP: PESTAÑA COSTOS Y PRECIOS
    # --------------------------------------------------------------------------
    def setup_tab_precios(self):
        layout = QVBoxLayout(self.tab_precios)
        
        # 3.1 ZONA DE COSTOS (Arriba)
        grp_costos = QGroupBox("Estructura de Costos")
        costo_layout = QHBoxLayout()
        
        # Columna Config
        col_conf_cost = QVBoxLayout()
        self.chk_importado = QCheckBox("Es Producto Importado")
        self.chk_importado.toggled.connect(self.toggle_importacion)
        
        self.radio_mantener_margen = QRadioButton("Mantener Margen %")
        self.radio_mantener_precio = QRadioButton("Mantener Precio Final")
        self.radio_mantener_margen.setChecked(True)
        
        bg = QButtonGroup(self)
        bg.addButton(self.radio_mantener_margen)
        bg.addButton(self.radio_mantener_precio)
        
        col_conf_cost.addWidget(self.chk_importado)
        col_conf_cost.addWidget(QLabel("Al cambiar costo:"))
        col_conf_cost.addWidget(self.radio_mantener_margen)
        col_conf_cost.addWidget(self.radio_mantener_precio)
        col_conf_cost.addStretch()
        costo_layout.addLayout(col_conf_cost)
        
        # Columna Inputs Costos (Se habilitan si es importado)
        self.frm_import = QFormLayout()
        
        self.spin_fob = self.crear_spin_moneda()
        self.spin_flete = self.crear_spin_moneda()
        self.spin_seguro = self.crear_spin_moneda()
        self.spin_arancel = self.crear_spin_moneda()
        self.spin_otros = self.crear_spin_moneda()
        
        # Conectar todos al recalculo
        self.spin_fob.valueChanged.connect(self.recalcular_costos_importacion)
        self.spin_flete.valueChanged.connect(self.recalcular_costos_importacion)
        self.spin_seguro.valueChanged.connect(self.recalcular_costos_importacion)
        self.spin_arancel.valueChanged.connect(self.recalcular_costos_importacion)
        self.spin_otros.valueChanged.connect(self.recalcular_costos_importacion)

        self.frm_import.addRow("Costo FOB ($):", self.spin_fob)
        self.frm_import.addRow("Fletes + Gastos ($):", self.spin_flete)
        self.frm_import.addRow("Seguros ($):", self.spin_seguro)
        self.frm_import.addRow("Aranceles/Aduana ($):", self.spin_arancel)
        
        costo_layout.addLayout(self.frm_import)
        
        # Columna Resultado Costo
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("COSTO BASE FINAL ($)"))
        self.spin_costo_final = self.crear_spin_moneda()
        self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #e8f8f5;")
        self.spin_costo_final.valueChanged.connect(self.recalcular_tabla_precios) # Gatilla actualización de grid
        
        res_layout.addWidget(self.spin_costo_final)
        
        res_layout.addWidget(QLabel("Costo en Bs (Ref):"))
        self.lbl_costo_bs = QLabel("0.00 Bs")
        self.lbl_costo_bs.setStyleSheet("font-weight: bold; color: #7f8c8d;")
        res_layout.addWidget(self.lbl_costo_bs)
        
        res_layout.addStretch()
        costo_layout.addLayout(res_layout)
        
        grp_costos.setLayout(costo_layout)
        layout.addWidget(grp_costos)
        
        # 3.2 ZONA DE PRECIOS (Abajo)
        grp_precios = QGroupBox("Tarifas de Venta")
        grid_layout = QVBoxLayout()
        
        self.grid_precios = QTableWidget()
        self.grid_precios.setColumnCount(6)
        cols_precios = ["Tarifa / Lista", "Margen Utilidad %", "Precio Neto ($)", "IVA ($)", "Precio Final ($)", "Precio Final (Bs)"]
        self.grid_precios.setHorizontalHeaderLabels(cols_precios)
        self.grid_precios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Inicializar con 3 tarifas base
        self.init_tabla_precios()
        
        # Conectar cambio en la celda de Margen (Columna 1)
        self.grid_precios.cellChanged.connect(self.on_grid_precios_changed)
        
        grid_layout.addWidget(self.grid_precios)
        grp_precios.setLayout(grid_layout)
        layout.addWidget(grp_precios)

        # Inicializar estado visual
        self.toggle_importacion(False)

    # ==========================================================================
    # LÓGICA DE NEGOCIO Y CÁLCULOS (FRONTEND)
    # ==========================================================================
    
    def crear_spin_moneda(self):
        spin = QDoubleSpinBox()
        spin.setRange(0, 9999999.99)
        spin.setDecimals(2)
        spin.setPrefix("$ ")
        return spin

    def seleccionar_imagen(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Imágenes (*.png *.jpg *.jpeg)")
        if archivo:
            self.ruta_imagen_actual = archivo
            pixmap = QPixmap(archivo)
            self.lbl_imagen.setPixmap(pixmap)

    def calcular_volumen(self):
        alto = self.spin_alto.value()
        ancho = self.spin_ancho.value()
        prof = self.spin_prof.value()
        
        # Formula: cm3 / 1.000.000 = m3
        volumen = (alto * ancho * prof) / 1000000
        self.lbl_volumen_m3.setText(f"{volumen:.4f} m³")

    def toggle_importacion(self, checked):
        # Habilitar o deshabilitar campos de importación
        self.spin_fob.setEnabled(checked)
        self.spin_flete.setEnabled(checked)
        self.spin_seguro.setEnabled(checked)
        self.spin_arancel.setEnabled(checked)
        
        if not checked:
            # Si no es importado, el Costo Final es editable directamente
            self.spin_costo_final.setReadOnly(False)
            self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: white;")
        else:
            # Si es importado, el Costo Final es calculado (Read Only)
            self.spin_costo_final.setReadOnly(True)
            self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #e8f8f5;")
            self.recalcular_costos_importacion()

    def recalcular_costos_importacion(self):
        if self.chk_importado.isChecked():
            total = (self.spin_fob.value() + 
                     self.spin_flete.value() + 
                     self.spin_seguro.value() + 
                     self.spin_arancel.value())
            self.spin_costo_final.blockSignals(True) # Evitar bucle infinito
            self.spin_costo_final.setValue(total)
            self.spin_costo_final.blockSignals(False)
            self.recalcular_tabla_precios()

    def init_tabla_precios(self):
        tarifas = ["Precio A (Detal)", "Precio B (Mayorista)", "Precio C (Gran Mayorista)"]
        márgenes_default = [30.00, 20.00, 15.00] # %
        
        self.grid_precios.setRowCount(len(tarifas))
        
        for i, nombre in enumerate(tarifas):
            # Col 0: Nombre Tarifa (No editable)
            item_nom = QTableWidgetItem(nombre)
            item_nom.setFlags(item_nom.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.grid_precios.setItem(i, 0, item_nom)
            
            # Col 1: Margen (Editable)
            self.grid_precios.setItem(i, 1, QTableWidgetItem(f"{márgenes_default[i]:.2f}"))
            
            # Resto de columnas se calculan solas...
            for j in range(2, 6):
                item = QTableWidgetItem("0.00")
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable) # ReadOnly
                self.grid_precios.setItem(i, j, item)

    def on_grid_precios_changed(self, row, col):
        # Solo reaccionamos si cambia la columna de Margen (Col 1)
        if col == 1:
            self.recalcular_fila_precio(row)

    def recalcular_tabla_precios(self):
        # Actualizar ref en Bs
        costo_usd = self.spin_costo_final.value()
        self.lbl_costo_bs.setText(f"{costo_usd * self.tasa_cambio_actual:,.2f} Bs")
        
        # Recorrer toda la tabla
        self.grid_precios.blockSignals(True) # Pausar señales para performance
        for i in range(self.grid_precios.rowCount()):
            self.recalcular_fila_precio(i, signal_block=False)
        self.grid_precios.blockSignals(False)

    def recalcular_fila_precio(self, row, signal_block=True):
        try:
            costo = self.spin_costo_final.value()
            
            # Leer Margen
            margen_txt = self.grid_precios.item(row, 1).text()
            margen = float(margen_txt) if margen_txt else 0.0
            
            # Lógica de Precio: Costo + (Costo * %)
            # OJO: Si la empresa usa "Margen sobre Venta", la fórmula es: Costo / (1 - %/100)
            # Usaremos la simple (Sobre Costo) por defecto:
            precio_neto = costo * (1 + margen / 100)
            
            # Impuesto (Simulado 16%)
            # TO-DO: Leer del combo de impuesto seleccionado
            iva_porc = 16.0 
            monto_iva = precio_neto * (iva_porc / 100)
            precio_final_usd = precio_neto + monto_iva
            precio_final_bs = precio_final_usd * self.tasa_cambio_actual
            
            # Escribir en columnas (Neto, IVA, Final USD, Final BS)
            self.grid_precios.setItem(row, 2, QTableWidgetItem(f"{precio_neto:.2f}"))
            self.grid_precios.setItem(row, 3, QTableWidgetItem(f"{monto_iva:.2f}"))
            self.grid_precios.setItem(row, 4, QTableWidgetItem(f"{precio_final_usd:.2f}"))
            self.grid_precios.setItem(row, 5, QTableWidgetItem(f"{precio_final_bs:,.2f}"))
            
        except ValueError:
            pass # Si escriben letras en el margen

    def cargar_combos_simulados(self):
        # Aquí llamarías a tu DBManager
        self.cmb_marca.addItems(["Seleccione...", "Samsung", "Nestlé", "Polar", "Generico"])
        self.cmb_grupo.addItems(["Seleccione...", "Alimentos", "Limpieza", "Tecnología"])
        self.cmb_unidad.addItems(["UND - Unidad", "CJA - Caja", "BTO - Bulto"])
        self.cmb_impuesto.addItems(["IVA General 16%", "Reducido 8%", "Exento 0%"])

    def guardar_producto(self):
        # Aquí recolectas todos los datos
        data = {
            "sku": self.txt_sku.text(),
            "nombre": self.txt_nombre.text(),
            "costo_usd": self.spin_costo_final.value(),
            "es_importado": self.chk_importado.isChecked(),
            # ... obtener el resto de campos ...
        }
        print("Guardando producto...", data)
        # 1. INSERT/UPDATE en inv_productos
        # 2. Loop para INSERT/UPDATE en inv_precios (recorriendo la tabla)
        # 3. INSERT/UPDATE en inv_existencias (ubicaciones)
        
        self.close()

# Para pruebas independientes
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # Estilo Fusion para que se vea moderno
    app.setStyle("Fusion")
    ventana = ProductosForm(1, 1, "EMPRESA DEMO")
    ventana.show()
    sys.exit(app.exec())