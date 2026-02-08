# -*- coding: utf-8 -*-
import sys
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QTabWidget, QCheckBox, QTableWidget, QHeaderView, 
    QGroupBox, QFormLayout, QPushButton, QFrame, QDoubleSpinBox,
    QTableWidgetItem, QFileDialog, QRadioButton, QButtonGroup, 
    QScrollArea, QDateEdit, QGridLayout, QDialog, QMessageBox,
    QCompleter, QApplication
)
from PyQt6.QtCore import Qt, QSize, QDate, pyqtSignal, QStringListModel
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QPalette, QCursor

# ==============================================================================
# CLASE 1: DIÁLOGO GENÉRICO PARA MAESTROS AUXILIARES (Grupos, Marcas, etc.)
# ==============================================================================
class MaestroAuxiliarDialog(QDialog):
    datos_actualizados = pyqtSignal()

    def __init__(self, conn, cod_compania, titulo, tabla_bd, campo_pk, campo_nombre, parent_id=None, campo_fk=None):
        super().__init__()
        self.conn = conn
        self.cod_compania = cod_compania
        self.tabla = tabla_bd
        self.pk = campo_pk
        self.campo_nombre = campo_nombre
        self.parent_id = parent_id 
        self.campo_fk = campo_fk 

        self.setWindowTitle(f"Gestión de {titulo}")
        self.resize(600, 450)
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Formulario
        grp = QGroupBox("Datos del Registro")
        frm = QFormLayout()
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ingrese descripción...")
        frm.addRow("Descripción:", self.txt_nombre)
        
        btn_box = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setStyleSheet("background-color: #27ae60; color: white;")
        self.btn_guardar.clicked.connect(self.guardar)
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.clicked.connect(self.limpiar)
        
        btn_box.addWidget(self.btn_limpiar)
        btn_box.addWidget(self.btn_guardar)
        frm.addRow(btn_box)
        grp.setLayout(frm)
        layout.addWidget(grp)
        
        # Tabla
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar...")
        self.txt_buscar.textChanged.connect(self.cargar_datos)
        layout.addWidget(self.txt_buscar)
        
        self.tabla_lista = QTableWidget()
        self.tabla_lista.setColumnCount(2)
        self.tabla_lista.setHorizontalHeaderLabels(["ID", "Descripción"])
        self.tabla_lista.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_lista.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_lista.cellDoubleClicked.connect(self.cargar_seleccion)
        layout.addWidget(self.tabla_lista)
        
        self.setLayout(layout)
        self.id_actual = None

    def cargar_datos(self):
        if not self.conn: return
        filtro = self.txt_buscar.text()
        try:
            cur = self.conn.cursor()
            sql = f"SELECT {self.pk}, {self.campo_nombre} FROM {self.tabla} WHERE cod_compania = %s"
            params = [self.cod_compania]
            
            if self.parent_id and self.campo_fk:
                sql += f" AND {self.campo_fk} = %s"
                params.append(self.parent_id)
            
            if filtro:
                sql += f" AND {self.campo_nombre} ILIKE %s"
                params.append(f"%{filtro}%")
            
            sql += f" ORDER BY {self.campo_nombre}"
            cur.execute(sql, tuple(params))
            
            rows = cur.fetchall()
            self.tabla_lista.setRowCount(0)
            for r in rows:
                idx = self.tabla_lista.rowCount()
                self.tabla_lista.insertRow(idx)
                self.tabla_lista.setItem(idx, 0, QTableWidgetItem(str(r[0])))
                self.tabla_lista.setItem(idx, 1, QTableWidgetItem(r[1]))
        except Exception as e:
            QMessageBox.critical(self, "Error BD", str(e))

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre: return
        
        try:
            cur = self.conn.cursor()
            if self.id_actual:
                sql = f"UPDATE {self.tabla} SET {self.campo_nombre} = %s WHERE {self.pk} = %s"
                cur.execute(sql, (nombre, self.id_actual))
            else:
                cols = f"cod_compania, {self.campo_nombre}"
                vals = "%s, %s"
                params = [self.cod_compania, nombre]
                
                if self.parent_id and self.campo_fk:
                    cols += f", {self.campo_fk}"
                    vals += ", %s"
                    params.append(self.parent_id)
                
                sql = f"INSERT INTO {self.tabla} ({cols}) VALUES ({vals})"
                cur.execute(sql, tuple(params))
            
            self.conn.commit()
            self.datos_actualizados.emit()
            self.limpiar()
            self.cargar_datos()
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error Guardar", str(e))

    def cargar_seleccion(self, row, col):
        self.id_actual = self.tabla_lista.item(row, 0).text()
        self.txt_nombre.setText(self.tabla_lista.item(row, 1).text())

    def limpiar(self):
        self.id_actual = None
        self.txt_nombre.clear()

# ==============================================================================
# CLASE 2: CATÁLOGO DE PRODUCTOS (BUSCADOR AVANZADO)
# ==============================================================================
class CatalogoProductosDialog(QDialog):
    producto_seleccionado = pyqtSignal(str) # Emite el SKU

    def __init__(self, conn, cod_compania):
        super().__init__()
        self.conn = conn
        self.cod_compania = cod_compania
        self.setWindowTitle("Catálogo de Productos")
        self.resize(800, 500)
        self.init_ui()
        self.buscar()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Filtros
        h_layout = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por Código, Nombre o Referencia...")
        self.txt_buscar.textChanged.connect(self.buscar)
        h_layout.addWidget(self.txt_buscar)
        layout.addLayout(h_layout)
        
        # Tabla
        self.tabla = QTableWidget()
        cols = ["SKU", "Nombre", "Marca", "Ref.", "Precio ($)", "Stock"]
        self.tabla.setColumnCount(len(cols))
        self.tabla.setHorizontalHeaderLabels(cols)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.cellDoubleClicked.connect(self.seleccionar)
        layout.addWidget(self.tabla)
        
        self.setLayout(layout)

    def buscar(self):
        if not self.conn: return
        txt = self.txt_buscar.text()
        try:
            cur = self.conn.cursor()
            sql = """
                SELECT p.cod_producto, p.nombre, m.nombre_marca, p.cod_alterno, 
                       pr.precio_final_usd, e.cantidad_real
                FROM inv_productos p
                LEFT JOIN inv_marcas m ON p.id_marca = m.id_marca
                LEFT JOIN inv_precios pr ON p.cod_producto = pr.cod_producto 
                     AND pr.id_lista = 1 -- Asumiendo lista 1 como base
                LEFT JOIN inv_existencias e ON p.cod_producto = e.cod_producto 
                     AND e.cod_almacen = 'MAIN' -- Asumiendo almacén principal
                WHERE p.cod_compania = %s
            """
            params = [self.cod_compania]
            if txt:
                sql += " AND (p.cod_producto ILIKE %s OR p.nombre ILIKE %s OR p.cod_alterno ILIKE %s)"
                params.extend([f"%{txt}%", f"%{txt}%", f"%{txt}%"])
            
            sql += " LIMIT 50"
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            
            self.tabla.setRowCount(0)
            for r in rows:
                i = self.tabla.rowCount()
                self.tabla.insertRow(i)
                self.tabla.setItem(i, 0, QTableWidgetItem(str(r[0])))
                self.tabla.setItem(i, 1, QTableWidgetItem(str(r[1])))
                self.tabla.setItem(i, 2, QTableWidgetItem(str(r[2] or "")))
                self.tabla.setItem(i, 3, QTableWidgetItem(str(r[3] or "")))
                self.tabla.setItem(i, 4, QTableWidgetItem(f"{r[4]:.2f}" if r[4] else "0.00"))
                self.tabla.setItem(i, 5, QTableWidgetItem(f"{r[5]:.2f}" if r[5] else "0.00"))
        except Exception as e:
            print(f"Error buscar catálogo: {e}")

    def seleccionar(self, row, col):
        sku = self.tabla.item(row, 0).text()
        self.producto_seleccionado.emit(sku)
        self.accept()

# ==============================================================================
# CLASE PRINCIPAL: FORMULARIO DE PRODUCTOS
# ==============================================================================

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ProductosForm(QWidget):
    def __init__(self, cod_compania, id_usuario, db_connection_or_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        
        # Manejo robusto de conexión
        if hasattr(db_connection_or_empresa, 'cursor'):
            self.conn = db_connection_or_empresa
        else:
            self.conn = None 
            print("ERROR CRÍTICO: No hay conexión a BD en ProductosForm")

        self.tasa_cambio_actual = 60.50 
        self.ruta_imagen_actual = ""
        
        self.setWindowTitle("Ficha Maestra de Productos - NEXUS PRIME")
        self.resize(1150, 800)
        self.set_style_local()
        self.init_ui()
        
        # Inicializar lógica
        if self.conn:
            self.cargar_combos_bd()
            self.configurar_autocompletado() # NUEVO: Hybrid Search
        else:
            QMessageBox.critical(self, "Error de Conexión", "No se recibió una conexión válida a la base de datos.")
            
        self.recalcular_costos_importacion()
        self.simular_datos_kardex()
        self.toggle_tab_lotes(False)
        self.toggle_estrategia_precios_lote()

    def set_style_local(self):
        self.setStyleSheet("""
            QWidget { background-color: #f4f6f9; color: #333; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px; margin-top: 10px; background-color: white; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { background-color: white; border: 1px solid #bdc3c7; border-radius: 4px; padding: 4px; min-height: 20px; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3498db; }
            QTableWidget { background-color: white; alternate-background-color: #f9f9f9; gridline-color: #eee; border: 1px solid #ddd; }
            QHeaderView::section { background-color: #2c3e50; color: white; padding: 6px; font-weight: bold; border: none; font-size: 11px; }
            QPushButton[cssClass="btn_plus"] { background-color: #3498db; color: white; font-weight: bold; border-radius: 4px; max-width: 30px; }
            QPushButton[cssClass="btn_search"] { background-color: #e67e22; color: white; font-weight: bold; border: none; border-radius: 4px; padding: 5px; text-align: left; }
            QPushButton[cssClass="btn_search"]:hover { background-color: #d35400; }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5) 

        # --- HEADER ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 8px;")
        header_frame.setFixedHeight(160) 
        header_layout = QHBoxLayout(header_frame)
        
        # Imagen
        self.lbl_imagen = ClickableLabel("FOTO")
        self.lbl_imagen.setFixedSize(135, 135)
        self.lbl_imagen.setStyleSheet("border: 2px dashed #adb5bd; background-color: #eee;")
        self.lbl_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_imagen.setScaledContents(True)
        self.lbl_imagen.clicked.connect(self.seleccionar_imagen)
        header_layout.addWidget(self.lbl_imagen)
        
        # Identificación (BÚSQUEDA HÍBRIDA)
        ident_layout = QFormLayout()
        
        # Campo SKU con Botón de Búsqueda Integrado (Solicitud del Usuario)
        sku_layout = QHBoxLayout()
        self.btn_buscar_sku = QPushButton("🔍 Código SKU:")
        self.btn_buscar_sku.setProperty("cssClass", "btn_search")
        self.btn_buscar_sku.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buscar_sku.setFixedWidth(110)
        self.btn_buscar_sku.clicked.connect(self.abrir_catalogo) # Acción botón Buscar
        
        self.txt_sku = QLineEdit()
        self.txt_sku.setPlaceholderText("Escriba código o presione el botón...")
        self.txt_sku.setStyleSheet("font-weight: bold; font-size: 14px;")
        # Conectar Enter para cargar
        self.txt_sku.returnPressed.connect(lambda: self.cargar_datos_producto(self.txt_sku.text()))
        
        sku_layout.addWidget(self.btn_buscar_sku)
        sku_layout.addWidget(self.txt_sku)
        
        # Nombre
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Escriba nombre para buscar...")
        self.txt_nombre.setStyleSheet("font-weight: bold; font-size: 18px;")
        
        self.txt_barra = QLineEdit()
        
        ident_layout.addRow(sku_layout) # Fila 1 personalizada
        ident_layout.addRow("Nombre:", self.txt_nombre)
        ident_layout.addRow("Cod. Barras:", self.txt_barra)
        header_layout.addLayout(ident_layout, stretch=2)
        
        # KPIs
        kpi_layout = QVBoxLayout()
        self.chk_activo = QCheckBox("PRODUCTO ACTIVO"); self.chk_activo.setChecked(True)
        self.lbl_stock_val = QLabel("0.00")
        self.lbl_stock_val.setStyleSheet("font-size: 26px; font-weight: bold; color: #2980b9;")
        kpi_layout.addWidget(self.chk_activo)
        kpi_layout.addWidget(QLabel("Existencia Total"))
        kpi_layout.addWidget(self.lbl_stock_val)
        header_layout.addLayout(kpi_layout)
        main_layout.addWidget(header_frame)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.tab_general = QWidget(); self.setup_tab_general(); self.tabs.addTab(self.tab_general, "📋 Datos Generales")
        self.tab_stock = QWidget(); self.setup_tab_stock(); self.tabs.addTab(self.tab_stock, "🏭 Existencias")
        self.tab_lotes = QWidget(); self.setup_tab_lotes(); self.tabs.addTab(self.tab_lotes, "📅 Lotes")
        self.tab_precios = QWidget(); self.setup_tab_precios(); self.tabs.addTab(self.tab_precios, "💰 Costos y Precios")
        self.tab_kardex = QWidget(); self.setup_tab_kardex(); self.tabs.addTab(self.tab_kardex, "📊 Kardex")
        
        main_layout.addWidget(self.tabs)
        
        # --- FOOTER ---
        btn_layout = QHBoxLayout()
        btn_limpiar = QPushButton("🧹 Limpiar Ficha")
        btn_limpiar.clicked.connect(self.limpiar_ficha)
        btn_save = QPushButton("💾 GUARDAR PRODUCTO")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        btn_save.clicked.connect(self.guardar_producto)
        
        btn_layout.addWidget(btn_limpiar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)

    def crear_selector_con_boton(self, funcion_plus):
        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(2)
        combo = QComboBox()
        btn_plus = QPushButton("+")
        btn_plus.setProperty("cssClass", "btn_plus") 
        btn_plus.setFixedSize(30, 25)
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plus.clicked.connect(funcion_plus)
        h_layout.addWidget(combo)
        h_layout.addWidget(btn_plus)
        return widget, combo

    # --------------------------------------------------------------------------
    # BÚSQUEDA HÍBRIDA Y AUTOCOMPLETADO
    # --------------------------------------------------------------------------
    def configurar_autocompletado(self):
        """Carga listas de SKU y Nombres para el autocompletado"""
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            # 1. Autocompletar SKU
            cur.execute("SELECT cod_producto FROM inv_productos WHERE cod_compania = %s", (self.cod_compania,))
            skus = [r[0] for r in cur.fetchall()]
            completer_sku = QCompleter(skus, self)
            completer_sku.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer_sku.setFilterMode(Qt.MatchFlag.MatchContains)
            self.txt_sku.setCompleter(completer_sku)
            # Al seleccionar del autocompletado, cargar
            completer_sku.activated.connect(self.cargar_datos_producto)

            # 2. Autocompletar Nombre
            cur.execute("SELECT nombre FROM inv_productos WHERE cod_compania = %s", (self.cod_compania,))
            nombres = [r[0] for r in cur.fetchall()]
            completer_nom = QCompleter(nombres, self)
            completer_nom.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer_nom.setFilterMode(Qt.MatchFlag.MatchContains)
            self.txt_nombre.setCompleter(completer_nom)
            # Al seleccionar nombre, buscar su SKU y cargar
            completer_nom.activated.connect(self.cargar_por_nombre)

        except Exception as e:
            print(f"Error autocompletado: {e}")

    def abrir_catalogo(self):
        """Abre la ventana de catálogo avanzado"""
        if not self.conn: return
        dlg = CatalogoProductosDialog(self.conn, self.cod_compania)
        dlg.producto_seleccionado.connect(self.cargar_datos_producto)
        dlg.exec()

    def cargar_por_nombre(self, nombre):
        """Busca el SKU asociado al nombre y carga"""
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT cod_producto FROM inv_productos WHERE nombre = %s AND cod_compania = %s", (nombre, self.cod_compania))
            row = cur.fetchone()
            if row:
                self.cargar_datos_producto(row[0])
        except: pass

    def cargar_datos_producto(self, sku):
        """Carga toda la info de la BD a la ficha"""
        if not self.conn or not sku: return
        
        try:
            cur = self.conn.cursor()
            # Datos Generales
            sql = """SELECT cod_producto, nombre, cod_barra, id_grupo, id_subgrupo, 
                            id_categoria, id_marca, id_unidad, es_servicio, usa_lotes, 
                            es_medicamento, peso, volumen, costo_final_usd
                     FROM inv_productos WHERE cod_producto = %s AND cod_compania = %s"""
            cur.execute(sql, (sku, self.cod_compania))
            row = cur.fetchone()
            
            if row:
                self.txt_sku.setText(row[0])
                self.txt_nombre.setText(row[1])
                self.txt_barra.setText(row[2] or "")
                
                # Seleccionar Combos (helper function needed or manual set)
                index = self.cmb_grupo.findData(row[3])
                if index >= 0: self.cmb_grupo.setCurrentIndex(index)
                
                self.filtrar_subgrupos() # Refrescar subgrupos
                index = self.cmb_subgrupo.findData(row[4])
                if index >= 0: self.cmb_subgrupo.setCurrentIndex(index)

                # Setear checks
                self.chk_servicio.setChecked(row[8])
                self.chk_lotes.setChecked(row[9])
                self.chk_medicamento.setChecked(row[10])
                
                # Costo
                self.spin_costo_final.setValue(float(row[13] or 0))
                
                print(f"Producto {sku} cargado.")
            else:
                # Si escribió un SKU nuevo, es para crear, no hacemos nada (o limpiamos)
                pass

        except Exception as e:
            QMessageBox.warning(self, "Error Carga", f"No se pudo cargar el producto: {e}")

    def limpiar_ficha(self):
        self.txt_sku.clear()
        self.txt_nombre.clear()
        self.txt_barra.clear()
        self.spin_costo_final.setValue(0)
        self.chk_activo.setChecked(True)
        # Reset combos
        self.cmb_grupo.setCurrentIndex(0)

    # --------------------------------------------------------------------------
    # PESTAÑA GENERAL (70/30)
    # --------------------------------------------------------------------------
    def setup_tab_general(self):
        main_layout = QVBoxLayout(self.tab_general)
        row1 = QHBoxLayout()
        
        # 1.1 Jerarquía (70%)
        grp_clasif = QGroupBox("Jerarquía y Clasificación")
        grid = QGridLayout()
        
        self.wid_grupo, self.cmb_grupo = self.crear_selector_con_boton(lambda: self.abrir_maestro("Grupos", "inv_grupos", "id_grupo", "nombre_grupo"))
        self.wid_subgrupo, self.cmb_subgrupo = self.crear_selector_con_boton(lambda: self.abrir_subgrupo())
        self.wid_categ, self.cmb_categoria = self.crear_selector_con_boton(lambda: self.abrir_maestro("Categorías", "inv_categorias", "id_categoria", "nombre_categoria"))
        self.wid_marca, self.cmb_marca = self.crear_selector_con_boton(lambda: self.abrir_maestro("Marcas", "inv_marcas", "id_marca", "nombre_marca"))
        self.wid_unidad, self.cmb_unidad = self.crear_selector_con_boton(lambda: self.abrir_maestro("Unidades", "inv_unidades", "id_unidad", "cod_unidad"))
        self.cmb_impuesto = QComboBox()
        
        self.cmb_grupo.currentIndexChanged.connect(self.filtrar_subgrupos)

        grid.addWidget(QLabel("1. Grupo:"), 0, 0); grid.addWidget(self.wid_grupo, 0, 1)
        grid.addWidget(QLabel("2. Sub-Grupo:"), 1, 0); grid.addWidget(self.wid_subgrupo, 1, 1)
        grid.addWidget(QLabel("3. Categoría:"), 2, 0); grid.addWidget(self.wid_categ, 2, 1)
        grid.addWidget(QLabel("4. Marca:"), 0, 2); grid.addWidget(self.wid_marca, 0, 3)
        grid.addWidget(QLabel("Unidad:"), 1, 2); grid.addWidget(self.wid_unidad, 1, 3)
        grid.addWidget(QLabel("Impuesto:"), 2, 2); grid.addWidget(self.cmb_impuesto, 2, 3)
        grp_clasif.setLayout(grid)
        row1.addWidget(grp_clasif, 7)
        
        # 1.2 Control (30%)
        grp_ctrl = QGroupBox("Control")
        l_ctrl = QVBoxLayout()
        self.chk_servicio = QCheckBox("Es Servicio")
        self.chk_lotes = QCheckBox("Usa Lotes/Venc.")
        self.chk_medicamento = QCheckBox("Es Medicamento")
        self.chk_lotes.toggled.connect(self.toggle_tab_lotes)
        l_ctrl.addWidget(self.chk_servicio)
        l_ctrl.addWidget(self.chk_lotes)
        l_ctrl.addWidget(self.chk_medicamento)
        l_ctrl.addStretch()
        grp_ctrl.setLayout(l_ctrl)
        row1.addWidget(grp_ctrl, 3)
        
        main_layout.addLayout(row1)
        
        # FILA 2
        row2 = QHBoxLayout()
        grp_log = QGroupBox("Logística")
        g_log = QGridLayout()
        self.spin_peso = QDoubleSpinBox(); self.spin_peso.setSuffix(" Kg")
        self.spin_alto = QDoubleSpinBox(); self.spin_ancho = QDoubleSpinBox(); self.spin_prof = QDoubleSpinBox()
        self.spin_bulto = QDoubleSpinBox(); self.spin_bulto.setValue(1)
        self.lbl_vol = QLabel("0.00")
        
        for sp in [self.spin_alto, self.spin_ancho, self.spin_prof]:
            sp.setSuffix(" cm"); sp.setRange(0,9999); sp.valueChanged.connect(self.calcular_volumen)

        g_log.addWidget(QLabel("Peso:"),0,0); g_log.addWidget(self.spin_peso,0,1)
        g_log.addWidget(QLabel("Alto:"),0,2); g_log.addWidget(self.spin_alto,0,3)
        g_log.addWidget(QLabel("Bulto:"),1,0); g_log.addWidget(self.spin_bulto,1,1)
        g_log.addWidget(QLabel("Ancho:"),1,2); g_log.addWidget(self.spin_ancho,1,3)
        g_log.addWidget(QLabel("Volumen:"),2,0); g_log.addWidget(self.lbl_vol,2,1)
        g_log.addWidget(QLabel("Prof.:"),2,2); g_log.addWidget(self.spin_prof,2,3)
        grp_log.setLayout(g_log)
        row2.addWidget(grp_log, 7)
        
        grp_adm = QGroupBox("Admin")
        f_adm = QFormLayout()
        self.txt_cod_alt = QLineEdit()
        self.cmb_costeo = QComboBox(); self.cmb_costeo.addItems(["PROMEDIO", "ULTIMO", "PEPS"])
        self.cmb_cta = QComboBox() 
        f_adm.addRow("Ref:", self.txt_cod_alt)
        f_adm.addRow("Costeo:", self.cmb_costeo)
        f_adm.addRow("Cta:", self.cmb_cta)
        grp_adm.setLayout(f_adm)
        row2.addWidget(grp_adm, 3)
        main_layout.addLayout(row2)
        
        self.txt_desc_larga = QLineEdit(); self.txt_desc_larga.setPlaceholderText("Descripción Larga...")
        main_layout.addWidget(self.txt_desc_larga)
        main_layout.addStretch()

    # --------------------------------------------------------------------------
    # PESTAÑA STOCK (Detallada)
    # --------------------------------------------------------------------------
    def setup_tab_stock(self):
        l = QVBoxLayout(self.tab_stock)
        self.grid_stock = QTableWidget(0, 8); 
        self.grid_stock.setHorizontalHeaderLabels(["Almacén","Pasillo","Estante","Peldaño","Real","Pedidos","OC","Disp"])
        self.grid_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.grid_stock)

    # --------------------------------------------------------------------------
    # PESTAÑA LOTES (Con lógica faltante restaurada)
    # --------------------------------------------------------------------------
    def setup_tab_lotes(self):
        layout = QVBoxLayout(self.tab_lotes)
        
        top_panel = QFrame()
        top_panel.setStyleSheet("background-color: #e8f6f3; border: 1px solid #a2d9ce; border-radius: 4px;")
        top_layout = QHBoxLayout(top_panel)
        top_layout.addWidget(QLabel("<b>Estrategia de Precios:</b>"))
        
        self.radio_precio_general = QRadioButton("Usar Precio General (Distribuidora)")
        self.radio_precio_lote = QRadioButton("Usar Precio por Lote (Farmacia)")
        self.radio_precio_general.setChecked(True)
        
        self.bg_estrategia = QButtonGroup()
        self.bg_estrategia.addButton(self.radio_precio_general)
        self.bg_estrategia.addButton(self.radio_precio_lote)
        self.bg_estrategia.buttonClicked.connect(self.toggle_estrategia_precios_lote)
        
        top_layout.addWidget(self.radio_precio_general)
        top_layout.addWidget(self.radio_precio_lote)
        top_layout.addStretch()
        layout.addWidget(top_panel)
        
        self.grid_lotes = QTableWidget(0, 8)
        self.grid_lotes.setHorizontalHeaderLabels(["Lote","Elab","Venc","Inicial","Vend","Rest","Costo","Precio Venta"])
        self.grid_lotes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.grid_lotes)

    def toggle_tab_lotes(self, checked):
        self.tabs.setTabEnabled(2, checked)

    def toggle_estrategia_precios_lote(self):
        """Bloquea o desbloquea la columna de Precio Venta en el Grid de lotes"""
        es_por_lote = self.radio_precio_lote.isChecked()
        col_precio_venta = 7
        rows = self.grid_lotes.rowCount()
        for i in range(rows):
            item = self.grid_lotes.item(i, col_precio_venta)
            if not item: continue
            if es_por_lote:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QColor("white"))
            else:
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable) 
                item.setBackground(QColor("#f2f2f2")) 
                item.setText("")

    # --------------------------------------------------------------------------
    # PESTAÑA PRECIOS
    # --------------------------------------------------------------------------
    def setup_tab_precios(self):
        layout = QVBoxLayout(self.tab_precios)
        
        # Costos Importación
        grp_costos = QGroupBox("Estructura de Costos")
        costo_layout = QHBoxLayout()
        col_conf_cost = QVBoxLayout()
        self.chk_importado = QCheckBox("Es Importado")
        self.chk_importado.toggled.connect(self.toggle_importacion)
        col_conf_cost.addWidget(self.chk_importado)
        costo_layout.addLayout(col_conf_cost)
        
        self.frm_import = QFormLayout()
        self.spin_fob = self.crear_spin_moneda()
        self.spin_flete = self.crear_spin_moneda()
        self.spin_seguro = self.crear_spin_moneda()
        self.spin_arancel = self.crear_spin_moneda()
        self.spin_otros = self.crear_spin_moneda()
        
        for spin in [self.spin_fob, self.spin_flete, self.spin_seguro, self.spin_arancel, self.spin_otros]:
            spin.valueChanged.connect(self.recalcular_costos_importacion)

        self.frm_import.addRow("FOB:", self.spin_fob); self.frm_import.addRow("Flete:", self.spin_flete)
        self.frm_import.addRow("Seguro:", self.spin_seguro); self.frm_import.addRow("Arancel:", self.spin_arancel)
        costo_layout.addLayout(self.frm_import)
        
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("COSTO BASE ($)"))
        self.spin_costo_final = self.crear_spin_moneda()
        self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #e8f8f5;")
        self.spin_costo_final.valueChanged.connect(self.recalcular_tabla_precios)
        res_layout.addWidget(self.spin_costo_final)
        
        res_layout.addWidget(QLabel("Costo Bs:"))
        self.lbl_costo_bs = QLabel("0.00 Bs")
        res_layout.addWidget(self.lbl_costo_bs)
        costo_layout.addLayout(res_layout)
        grp_costos.setLayout(costo_layout)
        layout.addWidget(grp_costos)
        
        # Grid Precios
        self.grid_precios = QTableWidget(3, 6)
        self.grid_precios.setHorizontalHeaderLabels(["Tarifa","Margen %","Neto $","IVA $","Final $","Final Bs"])
        self.grid_precios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.init_tabla_precios()
        self.grid_precios.cellChanged.connect(self.on_grid_precios_changed)
        layout.addWidget(self.grid_precios)
        self.toggle_importacion(False)

    def crear_spin_moneda(self):
        s = QDoubleSpinBox(); s.setRange(0, 9999999); s.setDecimals(2); s.setPrefix("$ ")
        return s

    def toggle_importacion(self, checked):
        self.spin_fob.setEnabled(checked); self.spin_flete.setEnabled(checked)
        self.spin_seguro.setEnabled(checked); self.spin_arancel.setEnabled(checked)
        if not checked:
            self.spin_costo_final.setReadOnly(False)
            self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: white;")
        else:
            self.spin_costo_final.setReadOnly(True)
            self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #e8f8f5;")
            self.recalcular_costos_importacion()

    def recalcular_costos_importacion(self):
        if self.chk_importado.isChecked():
            total = self.spin_fob.value() + self.spin_flete.value() + self.spin_seguro.value() + self.spin_arancel.value() + self.spin_otros.value()
            self.spin_costo_final.blockSignals(True)
            self.spin_costo_final.setValue(total)
            self.spin_costo_final.blockSignals(False)
            self.recalcular_tabla_precios()

    def init_tabla_precios(self):
        tarifas = ["Detal", "Mayorista", "Gran Mayorista"]
        margenes = [30, 20, 15]
        for i, t in enumerate(tarifas):
            self.grid_precios.setItem(i,0,QTableWidgetItem(t))
            self.grid_precios.setItem(i,1,QTableWidgetItem(str(margenes[i])))
            for j in range(2,6): self.grid_precios.setItem(i,j,QTableWidgetItem("0.00"))

    def on_grid_precios_changed(self, row, col):
        if col == 1: self.recalcular_fila_precio(row)

    def recalcular_tabla_precios(self):
        costo = self.spin_costo_final.value()
        self.lbl_costo_bs.setText(f"{costo * self.tasa_cambio_actual:,.2f} Bs")
        self.grid_precios.blockSignals(True)
        for i in range(self.grid_precios.rowCount()): self.recalcular_fila_precio(i, False)
        self.grid_precios.blockSignals(False)

    def recalcular_fila_precio(self, row, block=True):
        try:
            costo = self.spin_costo_final.value()
            margen = float(self.grid_precios.item(row, 1).text())
            neto = costo * (1 + margen/100)
            iva = neto * 0.16
            final_usd = neto + iva
            final_bs = final_usd * self.tasa_cambio_actual
            
            self.grid_precios.setItem(row, 2, QTableWidgetItem(f"{neto:.2f}"))
            self.grid_precios.setItem(row, 3, QTableWidgetItem(f"{iva:.2f}"))
            self.grid_precios.setItem(row, 4, QTableWidgetItem(f"{final_usd:.2f}"))
            self.grid_precios.setItem(row, 5, QTableWidgetItem(f"{final_bs:,.2f}"))
        except: pass

    # --------------------------------------------------------------------------
    # PESTAÑA KARDEX
    # --------------------------------------------------------------------------
    def setup_tab_kardex(self):
        l = QVBoxLayout(self.tab_kardex)
        self.grid_kardex = QTableWidget(0, 8)
        self.grid_kardex.setHorizontalHeaderLabels(["Fecha","Tipo","Doc","Tercero","Costo","Ent","Sal","Saldo"])
        self.grid_kardex.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.grid_kardex)
        
    def simular_datos_kardex(self):
        pass 

    # --------------------------------------------------------------------------
    # CARGA DE DATOS BD
    # --------------------------------------------------------------------------
    def cargar_combos_bd(self):
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            def llenar(combo, tabla, pk, txt):
                cur.execute(f"SELECT {pk}, {txt} FROM {tabla} WHERE cod_compania = %s AND activo = true ORDER BY {txt}", (self.cod_compania,))
                combo.clear(); combo.addItem("Seleccione...", None)
                for row in cur.fetchall(): combo.addItem(str(row[1]), row[0])

            llenar(self.cmb_grupo, "inv_grupos", "id_grupo", "nombre_grupo")
            llenar(self.cmb_categoria, "inv_categorias", "id_categoria", "nombre_categoria")
            llenar(self.cmb_marca, "inv_marcas", "id_marca", "nombre_marca")
            llenar(self.cmb_unidad, "inv_unidades", "id_unidad", "cod_unidad")
            
            cur.execute("SELECT id_impuesto, nombre_impuesto, porcentaje FROM cfg_impuestos WHERE cod_compania = %s AND activo = true", (self.cod_compania,))
            self.cmb_impuesto.clear()
            for row in cur.fetchall(): self.cmb_impuesto.addItem(f"{row[1]} ({row[2]}%)", row[0])

            self.cmb_cta.clear(); self.cmb_cta.addItem("Sin asignar", None)
            cur.execute("SELECT id_cuenta, codigo_contable, nombre_cuenta FROM cfg_plan_cuentas WHERE cod_compania = %s AND activo = true", (self.cod_compania,))
            for row in cur.fetchall(): self.cmb_cta.addItem(f"{row[1]} - {row[2]}", row[0])

            cur.close()
        except Exception as e:
            print(f"Error BD: {e}")

    def filtrar_subgrupos(self):
        id_grupo = self.cmb_grupo.currentData()
        self.cmb_subgrupo.clear()
        if not id_grupo or not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id_subgrupo, nombre_subgrupo FROM inv_subgrupos WHERE id_grupo = %s AND activo = true", (id_grupo,))
            self.cmb_subgrupo.addItem("Seleccione...", None)
            for row in cur.fetchall(): self.cmb_subgrupo.addItem(row[1], row[0])
            cur.close()
        except: pass

    # --------------------------------------------------------------------------
    # APERTURA DE DIÁLOGOS
    # --------------------------------------------------------------------------
    def abrir_maestro(self, titulo, tabla, pk, campo_nombre):
        if not self.conn: 
            QMessageBox.critical(self, "Error", "No hay conexión a la base de datos.")
            return
        dialog = MaestroAuxiliarDialog(self.conn, self.cod_compania, titulo, tabla, pk, campo_nombre)
        dialog.datos_actualizados.connect(self.cargar_combos_bd)
        dialog.exec()
        
    def abrir_subgrupo(self):
        id_grupo = self.cmb_grupo.currentData()
        if not id_grupo:
            QMessageBox.warning(self, "Atención", "Seleccione un Grupo primero.")
            return
        if not self.conn: return
        dialog = MaestroAuxiliarDialog(self.conn, self.cod_compania, "Subgrupos", "inv_subgrupos", 
            "id_subgrupo", "nombre_subgrupo", parent_id=id_grupo, campo_fk="id_grupo")
        dialog.datos_actualizados.connect(self.filtrar_subgrupos)
        dialog.exec()

    # --------------------------------------------------------------------------
    # OTROS
    # --------------------------------------------------------------------------
    def seleccionar_imagen(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Imagen", "", "Img (*.png *.jpg)")
        if archivo: self.lbl_imagen.setPixmap(QPixmap(archivo))

    def calcular_volumen(self):
        v = (self.spin_alto.value() * self.spin_ancho.value() * self.spin_prof.value()) / 1000000
        self.lbl_vol.setText(f"{v:.4f} m³")

    def cargar_combos_simulados(self):
        self.cmb_marca.addItems(["Generico"])

    def guardar_producto(self):
        sku = self.txt_sku.text()
        nombre = self.txt_nombre.text()
        
        if not sku or not nombre:
            QMessageBox.warning(self, "Validación", "El SKU y el Nombre son obligatorios.")
            return

        try:
            cur = self.conn.cursor()
            
            # Verificar si existe para UPDATE o INSERT
            cur.execute("SELECT cod_producto FROM inv_productos WHERE cod_producto = %s AND cod_compania = %s", (sku, self.cod_compania))
            existe = cur.fetchone()
            
            campos_comunes = {
                'id_grupo': self.cmb_grupo.currentData(),
                'id_subgrupo': self.cmb_subgrupo.currentData(),
                'id_marca': self.cmb_marca.currentData(),
                'nombre': nombre,
                # ... agregar resto de campos
            }
            
            # Nota: Esto es un ejemplo simplificado. Deberías mapear TODOS los campos
            if existe:
                # UPDATE
                print("Actualizando...")
            else:
                # INSERT
                print("Insertando...")
            
            # self.conn.commit()
            QMessageBox.information(self, "Guardar", "Producto guardado correctamente (Simulado).")
            self.limpiar_ficha()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

if __name__ == "__main__":
    try:
        # PRUEBA LOCAL (Ajusta contraseña)
        conn = psycopg2.connect("dbname=nexusdb user=postgres password=postgres host=localhost")
        app = sys.modules['__main__'].QApplication(sys.argv)
        app.setStyle("Fusion")
        win = ProductosForm(1, 1, conn)
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error Conexión: {e}")
        app = sys.modules['__main__'].QApplication(sys.argv)
        win = ProductosForm(1, 1, "SIN_CONEXION")
        win.show()
        sys.exit(app.exec())