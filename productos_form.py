# -*- coding: utf-8 -*-
import sys
import os
import shutil
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QTabWidget, QCheckBox, QTableWidget, QHeaderView, 
    QGroupBox, QFormLayout, QPushButton, QFrame, QDoubleSpinBox,
    QTableWidgetItem, QFileDialog, QRadioButton, QButtonGroup, 
    QDialog, QMessageBox, QCompleter, QApplication, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QCursor, QFont
from datetime import datetime

# --- IMPORTAMOS LAS UTILIDADES GLOBALES Y LA BD ---
try:
    from db_config import DB_PARAMS
except ImportError:
    DB_PARAMS = {}

try:
    from utils_ui import MaestroAuxiliarDialog, ClickableLabel
except ImportError:
    QMessageBox.critical(None, "Error de Arquitectura", "Falta el archivo utils_ui.py en el proyecto.")
    sys.exit(1)


# ==============================================================================
# CATÁLOGO DE PRODUCTOS (BÚSQUEDA AVANZADA CON MÚLTIPLES FILTROS)
# ==============================================================================
class CatalogoProductosDialog(QDialog):
    producto_seleccionado = pyqtSignal(str) 

    def __init__(self, conn, cod_compania):
        super().__init__()
        self.conn = conn
        self.cod_compania = cod_compania
        self.setWindowTitle("Búsqueda Avanzada de Productos")
        self.resize(1050, 600)
        
        self.filtros_activos = {} # Diccionario: { 'columna_bd': (id, 'Nombre para el Tag', combobox_reference) }
        self.init_ui()
        self.buscar()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Barra Superior de Búsqueda y Filtros ---
        search_box = QGroupBox("Criterios de Búsqueda")
        search_layout = QVBoxLayout(search_box)
        
        # Fila 1: Buscador de texto
        row1 = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Escriba Código, Nombre o Referencia...")
        self.txt_buscar.textChanged.connect(self.buscar)
        row1.addWidget(QLabel("🔍"))
        row1.addWidget(self.txt_buscar)
        search_layout.addLayout(row1)
        
        # Fila 2: Combos de Filtros
        row2 = QHBoxLayout()
        self.cmb_filtro_grupo = QComboBox()
        self.cmb_filtro_subgrupo = QComboBox()
        self.cmb_filtro_categoria = QComboBox()
        self.cmb_filtro_marca = QComboBox()
        
        row2.addWidget(self.cmb_filtro_grupo)
        row2.addWidget(self.cmb_filtro_subgrupo)
        row2.addWidget(self.cmb_filtro_categoria)
        row2.addWidget(self.cmb_filtro_marca)
        search_layout.addLayout(row2)
        
        layout.addWidget(search_box)

        self.cargar_filtros_combos()
        
        # Conectar señales después de cargar para evitar disparos en falso
        self.cmb_filtro_grupo.currentIndexChanged.connect(lambda: self.agregar_filtro('id_grupo', self.cmb_filtro_grupo))
        self.cmb_filtro_subgrupo.currentIndexChanged.connect(lambda: self.agregar_filtro('id_subgrupo', self.cmb_filtro_subgrupo))
        self.cmb_filtro_categoria.currentIndexChanged.connect(lambda: self.agregar_filtro('id_categoria', self.cmb_filtro_categoria))
        self.cmb_filtro_marca.currentIndexChanged.connect(lambda: self.agregar_filtro('id_marca', self.cmb_filtro_marca))

        # --- Área de Filtros Activos (Tags con X) ---
        self.frame_tags = QFrame()
        self.layout_tags = QHBoxLayout(self.frame_tags)
        self.layout_tags.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.frame_tags)

        # --- Tabla de Resultados ---
        self.tabla = QTableWidget()
        cols = ["SKU", "Nombre", "Marca", "Grupo", "Costo $", "Existencia"]
        self.tabla.setColumnCount(len(cols))
        self.tabla.setHorizontalHeaderLabels(cols)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.cellDoubleClicked.connect(self.seleccionar)
        layout.addWidget(self.tabla)

    def cargar_filtros_combos(self):
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            def llenar(combo, tabla, pk, txt, placeholder):
                cur.execute(f"SELECT {pk}, {txt} FROM {tabla} WHERE cod_compania = %s AND activo = true", (self.cod_compania,))
                combo.addItem(placeholder, None)
                for r in cur.fetchall(): combo.addItem(r[1], r[0])

            llenar(self.cmb_filtro_grupo, "inv_grupos", "id_grupo", "nombre_grupo", "Filtrar por Grupo...")
            llenar(self.cmb_filtro_subgrupo, "inv_subgrupos", "id_subgrupo", "nombre_subgrupo", "Filtrar por Subgrupo...")
            llenar(self.cmb_filtro_categoria, "inv_categorias", "id_categoria", "nombre_categoria", "Filtrar por Categoría...")
            llenar(self.cmb_filtro_marca, "inv_marcas", "id_marca", "nombre_marca", "Filtrar por Marca...")
        except Exception as e: print("Error cargando filtros:", e)

    def agregar_filtro(self, campo_bd, combo_widget):
        id_filtro = combo_widget.currentData()
        nombre = combo_widget.currentText()
        
        if id_filtro:
            self.filtros_activos[campo_bd] = (id_filtro, nombre, combo_widget)
            self.dibujar_tags()
            self.buscar()

    def dibujar_tags(self):
        # Limpiar tags actuales de la pantalla
        for i in reversed(range(self.layout_tags.count())): 
            widget = self.layout_tags.itemAt(i).widget()
            if widget: widget.setParent(None)
        
        # Dibujar los activos
        for campo, info in self.filtros_activos.items():
            tag = QFrame()
            tag.setStyleSheet("background-color: #3498DB; color: white; border-radius: 10px; padding: 2px 10px;")
            l = QHBoxLayout(tag)
            l.setContentsMargins(5,2,5,2)
            lbl = QLabel(f"{info[1]}")
            btn_x = QPushButton("✕")
            btn_x.setFixedSize(16,16)
            btn_x.setStyleSheet("background: transparent; color: white; font-weight: bold; border: none;")
            btn_x.setCursor(Qt.CursorShape.PointingHandCursor)
            # Pasamos el 'campo' a la función de eliminar
            btn_x.clicked.connect(lambda ch, c=campo: self.quitar_filtro(c))
            
            l.addWidget(lbl)
            l.addWidget(btn_x)
            self.layout_tags.addWidget(tag)

    def quitar_filtro(self, campo):
        if campo in self.filtros_activos:
            info = self.filtros_activos[campo]
            combo = info[2] # Recuperamos qué combo originó este filtro
            
            # Lo quitamos del diccionario
            del self.filtros_activos[campo]
            
            # Reseteamos el combo visualmente sin disparar la búsqueda 2 veces
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            
            self.dibujar_tags()
            self.buscar()

    def buscar(self):
        if not self.conn: return
        texto = self.txt_buscar.text().strip()
        try:
            cur = self.conn.cursor()
            sql = """
                SELECT p.cod_producto, p.nombre, m.nombre_marca, g.nombre_grupo, p.costo_final_usd, 
                       COALESCE((SELECT SUM(cantidad_real) FROM inv_existencias WHERE cod_producto = p.cod_producto AND cod_compania = p.cod_compania), 0)
                FROM inv_productos p
                LEFT JOIN inv_marcas m ON p.id_marca = m.id_marca
                LEFT JOIN inv_grupos g ON p.id_grupo = g.id_grupo
                WHERE p.cod_compania = %s
            """
            params = [self.cod_compania]
            
            if texto:
                sql += " AND (p.cod_producto ILIKE %s OR p.nombre ILIKE %s OR p.cod_barra ILIKE %s OR p.cod_alterno ILIKE %s)"
                params.extend([f"%{texto}%", f"%{texto}%", f"%{texto}%", f"%{texto}%"])
            
            # Aplicar TODOS los filtros activos dinámicamente
            for campo, info in self.filtros_activos.items():
                sql += f" AND p.{campo} = %s"
                params.append(info[0])

            sql += " ORDER BY p.nombre LIMIT 100"
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
                
                it_costo = QTableWidgetItem(f"{r[4]:.2f}")
                it_costo.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(i, 4, it_costo)
                
                it_ext = QTableWidgetItem(f"{r[5]:.2f}")
                it_ext.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(i, 5, it_ext)
        except Exception as e:
            print(f"Error Búsqueda Avanzada: {e}")

    def seleccionar(self, row, col):
        sku = self.tabla.item(row, 0).text()
        self.producto_seleccionado.emit(sku)
        self.accept()


# ==============================================================================
# CLASE PRINCIPAL: FORMULARIO DE PRODUCTOS
# ==============================================================================
class ProductosForm(QWidget):
    def __init__(self, cod_compania, id_usuario, db_connection_or_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        self.nombre_usuario_actual = "Usuario"
        
        # Ruta corporativa para imágenes (Carpeta compartida en Red)
        # Puedes cambiar 'SERVIDOR' por la IP de tu servidor real
        self.PATH_IMAGENES = r"G:\Mi unidad\Sistema - nexus prime\sesion\Imagenes_Productos" 
        if not os.path.exists(self.PATH_IMAGENES):
            try: os.makedirs(self.PATH_IMAGENES, exist_ok=True)
            except: self.PATH_IMAGENES = "img_productos/" # Fallback local
        
        self.conn_propia = False
        if hasattr(db_connection_or_empresa, 'cursor'):
            self.conn = db_connection_or_empresa
        else:
            try:
                if DB_PARAMS:
                    self.conn = psycopg2.connect(**DB_PARAMS)
                    self.conn_propia = True
                else: self.conn = None
            except: self.conn = None

        if self.conn:
            try:
                cur = self.conn.cursor()
                cur.execute("SELECT nombre_completo FROM seg_usuarios WHERE id_usuario = %s", (self.id_usuario,))
                row = cur.fetchone()
                if row: self.nombre_usuario_actual = row[0]
            except: pass

        self.tasa_cambio_actual = 60.50 
        self.ruta_imagen_local = ""
        
        self.setWindowTitle("Ficha Maestra de Productos - NEXUS PRIME")
        self.resize(1150, 800)
        self.init_ui()
        
        if self.conn:
            self.cargar_estructuras_dinamicas() 
            self.configurar_autocompletado_hibrido() 
            self.configurar_autocompletado_insumos()
        else:
            QMessageBox.critical(self, "Error", "No hay conexión a la base de datos.")
            
        self.recalcular_costos_importacion()
        self.limpiar_ficha() # Inicia la ficha completamente limpia

    def closeEvent(self, event):
        if self.conn_propia and self.conn:
            self.conn.close()
        event.accept()

    def crear_input_numerico(self, decimals=2, suffix=""):
        spin = QDoubleSpinBox()
        spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        spin.setDecimals(decimals)
        spin.setRange(0, 9999999.99)
        if suffix: spin.setSuffix(suffix)
        return spin

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10) 

        # --- HEADER ---
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setStyleSheet("#HeaderFrame { background-color: #FFFFFF; border: 1px solid #D5DBDB; border-radius: 8px; }")
        header_frame.setFixedHeight(170) 
        header_layout = QHBoxLayout(header_frame)
        
        # Imagen con lógica corporativa
        self.lbl_imagen = ClickableLabel("FOTO\n(Clic para cambiar)")
        self.lbl_imagen.setFixedSize(140, 140)
        self.lbl_imagen.setStyleSheet("border: 2px dashed #BDC3C7; background-color: #F8F9F9; font-weight:bold; color: #95A5A6;")
        self.lbl_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_imagen.setScaledContents(True)
        self.lbl_imagen.clicked.connect(self.seleccionar_imagen)
        header_layout.addWidget(self.lbl_imagen)
        
        ident_layout = QFormLayout()
        sku_layout = QHBoxLayout()
        self.btn_buscar_sku = QPushButton("🔍")
        self.btn_buscar_sku.setToolTip("Abrir Catálogo Avanzado")
        self.btn_buscar_sku.setFixedSize(35, 30)
        self.btn_buscar_sku.setProperty("cssClass", "btn_search")
        self.btn_buscar_sku.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buscar_sku.clicked.connect(self.abrir_catalogo) 
        self.btn_buscar_sku.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.txt_sku = QLineEdit()
        self.txt_sku.setPlaceholderText("CÓDIGO SKU (Requerido) *")
        self.txt_sku.setStyleSheet("font-weight: bold; font-size: 15px; border: 1px solid #E74C3C;") # Borde rojo indica obligatorio
        self.txt_sku.returnPressed.connect(self.procesar_enter_sku)
        
        sku_layout.addWidget(self.txt_sku)
        sku_layout.addWidget(self.btn_buscar_sku)
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre Completo del Producto (Requerido) *")
        self.txt_nombre.setStyleSheet("font-weight: bold; font-size: 18px; border: 1px solid #E74C3C;")
        self.txt_barra = QLineEdit()
        self.txt_barra.setPlaceholderText("Código de Barras EAN/UPC")
        
        ident_layout.addRow("SKU:", sku_layout) 
        ident_layout.addRow("Descripción:", self.txt_nombre)
        ident_layout.addRow("Cod. Barras:", self.txt_barra)
        header_layout.addLayout(ident_layout, stretch=2)
        
        kpi_layout = QVBoxLayout()
        self.chk_activo = QCheckBox("PRODUCTO ACTIVO"); self.chk_activo.setChecked(True)
        self.chk_activo.setStyleSheet("color: #27AE60; font-weight:bold; font-size: 13px;")
        self.lbl_stock_val = QLabel("0.00")
        self.lbl_stock_val.setStyleSheet("font-size: 32px; font-weight: bold; color: #2980B9;")
        kpi_layout.addWidget(self.chk_activo)
        kpi_layout.addWidget(QLabel("STOCK TOTAL ACTUAL"))
        kpi_layout.addWidget(self.lbl_stock_val)
        header_layout.addLayout(kpi_layout)
        main_layout.addWidget(header_frame)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.tab_general = QWidget(); self.setup_tab_general(); self.tabs.addTab(self.tab_general, "📋 Datos Generales")
        self.tab_stock = QWidget(); self.setup_tab_stock(); self.tabs.addTab(self.tab_stock, "🏭 Existencias")
        self.tab_lotes = QWidget(); self.setup_tab_lotes(); self.tabs.addTab(self.tab_lotes, "📅 Lotes")
        self.tab_composicion = QWidget(); self.setup_tab_composicion(); self.tabs.addTab(self.tab_composicion, "🧩 Composición / Receta")
        self.tab_precios = QWidget(); self.setup_tab_precios(); self.tabs.addTab(self.tab_precios, "💰 Costos y Precios")
        self.tab_kardex = QWidget(); self.setup_tab_kardex(); self.tabs.addTab(self.tab_kardex, "📊 Kardex")
        main_layout.addWidget(self.tabs)
        
        # --- FOOTER BOTONES Y AUDITORÍA ---
        footer_layout = QHBoxLayout()
        
        btn_nuevo = QPushButton("✨ NUEVO PRODUCTO")
        btn_nuevo.setStyleSheet("background-color: #3498DB; color: white; padding: 10px; font-weight: bold; border-radius:4px;")
        btn_nuevo.clicked.connect(self.limpiar_ficha)

        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.setProperty("cssClass", "btn_delete")
        self.btn_eliminar.clicked.connect(self.eliminar_producto)
        
        btn_save = QPushButton("💾 GUARDAR / ACTUALIZAR")
        btn_save.setObjectName("btn_guardar")
        btn_save.clicked.connect(self.guardar_producto)
        
        footer_layout.addWidget(btn_nuevo)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_eliminar)
        footer_layout.addWidget(btn_save)
        main_layout.addLayout(footer_layout)
        
        self.lbl_auditoria = QLabel("-")
        self.lbl_auditoria.setStyleSheet("color: #7F8C8D; font-size: 11px; font-style: italic; margin-top: 5px;")
        main_layout.addWidget(self.lbl_auditoria, alignment=Qt.AlignmentFlag.AlignCenter)

    def crear_selector_con_boton(self, funcion_plus):
        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(4) 
        
        combo = QComboBox()
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(30, 26) 
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plus.setProperty("cssClass", "btn_plus") # Hereda estilo del .qss
        btn_plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_plus.clicked.connect(funcion_plus)
        
        h_layout.addWidget(combo)
        h_layout.addWidget(btn_plus)
        return widget, combo

    # --------------------------------------------------------------------------
    # GESTIÓN DE IMÁGENES EN RED CORPORATIVA
    # --------------------------------------------------------------------------
    def seleccionar_imagen(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Imágenes (*.png *.jpg *.jpeg)")
        if file_path:
            pixmap = QPixmap(file_path)
            self.lbl_imagen.setPixmap(pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio))
            self.ruta_imagen_local = file_path 

    def procesar_imagen_servidor(self, sku):
        if not self.ruta_imagen_local:
            return None
        try:
            os.makedirs(self.PATH_IMAGENES, exist_ok=True)
            extension = os.path.splitext(self.ruta_imagen_local)[1]
            nombre_archivo = f"PROD_{sku}{extension}"
            ruta_destino = os.path.join(self.PATH_IMAGENES, nombre_archivo)
            
            # Copiar imagen al servidor
            shutil.copy2(self.ruta_imagen_local, ruta_destino)
            return nombre_archivo
        except Exception as e:
            print(f"Error guardando imagen en red: {e}")
            return None

    # --------------------------------------------------------------------------
    # PESTAÑA GENERAL 
    # --------------------------------------------------------------------------
    def setup_tab_general(self):
        main_layout = QVBoxLayout(self.tab_general)
        
        grp_clasif = QGroupBox("1. Clasificación Principal")
        grid_clasif = QGridLayout()
        
        self.wid_grupo, self.cmb_grupo = self.crear_selector_con_boton(lambda: self.abrir_maestro("Grupos", "inv_grupos", "id_grupo", "nombre_grupo"))
        self.wid_subgrupo, self.cmb_subgrupo = self.crear_selector_con_boton(lambda: self.abrir_subgrupo())
        self.wid_categ, self.cmb_categoria = self.crear_selector_con_boton(lambda: self.abrir_maestro("Categorías", "inv_categorias", "id_categoria", "nombre_categoria"))
        self.wid_marca, self.cmb_marca = self.crear_selector_con_boton(lambda: self.abrir_maestro("Marcas", "inv_marcas", "id_marca", "nombre_marca"))
        self.wid_unidad, self.cmb_unidad = self.crear_selector_con_boton(lambda: self.abrir_maestro("Unidades", "inv_unidades", "id_unidad", "cod_unidad"))
        self.cmb_impuesto = QComboBox()
        self.cmb_grupo.currentIndexChanged.connect(self.filtrar_subgrupos)

        grid_clasif.addWidget(QLabel("Grupo:"), 0, 0); grid_clasif.addWidget(self.wid_grupo, 0, 1)
        grid_clasif.addWidget(QLabel("Sub-Grupo:"), 0, 2); grid_clasif.addWidget(self.wid_subgrupo, 0, 3)
        grid_clasif.addWidget(QLabel("Categoría:"), 0, 4); grid_clasif.addWidget(self.wid_categ, 0, 5)
        grid_clasif.addWidget(QLabel("Marca:"), 1, 0); grid_clasif.addWidget(self.wid_marca, 1, 1)
        grid_clasif.addWidget(QLabel("Unidad Medida:"), 1, 2); grid_clasif.addWidget(self.wid_unidad, 1, 3)
        grid_clasif.addWidget(QLabel("Impuesto (IVA):"), 1, 4); grid_clasif.addWidget(self.cmb_impuesto, 1, 5)
        grp_clasif.setLayout(grid_clasif)
        main_layout.addWidget(grp_clasif)
        
        row2 = QHBoxLayout()
        grp_ctrl = QGroupBox("2. Control Operativo")
        l_ctrl = QVBoxLayout()
        self.chk_fraccionario = QCheckBox("Es Fraccionario (Permite decimales)")
        self.chk_compuesto = QCheckBox("Es un Producto Compuesto (Receta/Kit)")
        self.chk_lotes = QCheckBox("Controla Lotes y Vencimientos")
        self.chk_servicio = QCheckBox("Es un Servicio (No maneja stock)")
        self.chk_medicamento = QCheckBox("Es Medicamento regulado")
        
        self.chk_lotes.toggled.connect(self.toggle_tab_lotes)
        self.chk_compuesto.toggled.connect(self.toggle_tab_composicion)
        
        l_ctrl.addWidget(self.chk_fraccionario); l_ctrl.addWidget(self.chk_compuesto); l_ctrl.addWidget(self.chk_lotes); l_ctrl.addWidget(self.chk_servicio); l_ctrl.addWidget(self.chk_medicamento); l_ctrl.addStretch()
        grp_ctrl.setLayout(l_ctrl)
        row2.addWidget(grp_ctrl, 4) 
        
        grp_adm = QGroupBox("3. Datos Administrativos")
        f_adm = QFormLayout()
        self.cmb_tipo_prod = QComboBox()
        self.cmb_tipo_prod.addItems(["Producto Terminado", "Materia Prima", "Material de Empaque", "Consumible"])
        self.txt_cod_alt = QLineEdit()
        self.txt_arancel = QLineEdit(); self.txt_arancel.setPlaceholderText("Partida Arancelaria")
        self.cmb_costeo = QComboBox(); self.cmb_costeo.addItems(["PROMEDIO", "ULTIMO", "PEPS"])
        self.cmb_cta = QComboBox() 
        f_adm.addRow("Tipo de Producto:", self.cmb_tipo_prod)
        f_adm.addRow("Ref. Proveedor:", self.txt_cod_alt)
        f_adm.addRow("P. Arancelaria:", self.txt_arancel)
        f_adm.addRow("Método Costeo:", self.cmb_costeo)
        f_adm.addRow("Cta. Contable:", self.cmb_cta)
        grp_adm.setLayout(f_adm)
        row2.addWidget(grp_adm, 6) 
        main_layout.addLayout(row2)
        
        grp_log = QGroupBox("4. Logística y Dimensiones")
        g_log = QHBoxLayout()
        f_dim = QFormLayout()
        self.spin_alto = self.crear_input_numerico(2, " cm"); self.spin_ancho = self.crear_input_numerico(2, " cm"); self.spin_largo = self.crear_input_numerico(2, " cm")
        for sp in [self.spin_alto, self.spin_ancho, self.spin_largo]: sp.valueChanged.connect(self.calcular_volumen)
        f_dim.addRow("Alto:", self.spin_alto); f_dim.addRow("Ancho:", self.spin_ancho); f_dim.addRow("Largo:", self.spin_largo)
        g_log.addLayout(f_dim)
        
        f_pes = QFormLayout()
        self.spin_peso = self.crear_input_numerico(3, " Kg"); self.lbl_vol = QLabel("0.0000 m³"); self.lbl_vol.setStyleSheet("font-weight: bold;")
        self.spin_bulto = self.crear_input_numerico(0, " Unds")
        f_pes.addRow("Peso Bruto:", self.spin_peso); f_pes.addRow("Volumen:", self.lbl_vol); f_pes.addRow("Unds x Bulto:", self.spin_bulto)
        g_log.addLayout(f_pes)
        
        f_stk = QFormLayout()
        self.spin_stock_min = self.crear_input_numerico(2); self.spin_stock_max = self.crear_input_numerico(2)
        f_stk.addRow("Stock Mínimo:", self.spin_stock_min); f_stk.addRow("Stock Máximo:", self.spin_stock_max)
        g_log.addLayout(f_stk)
        
        grp_log.setLayout(g_log)
        main_layout.addWidget(grp_log)
        
        self.txt_desc_larga = QLineEdit()
        self.txt_desc_larga.setPlaceholderText("Descripción Larga para web/cotizaciones...")
        main_layout.addWidget(self.txt_desc_larga)
        main_layout.addStretch()

    # --------------------------------------------------------------------------
    # PESTAÑA STOCK, LOTES, COMPOSICION, PRECIOS, KARDEX
    # --------------------------------------------------------------------------
    def setup_tab_stock(self):
        l = QVBoxLayout(self.tab_stock)
        self.grid_stock = QTableWidget(0, 9) 
        self.grid_stock.setHorizontalHeaderLabels([
            "ID Almacén", "Nombre Almacén", "Pasillo", "Estante", "Peldaño", 
            "Existencia Real", "Pedidos", "Ord. Compra", "Disponible"
        ])
        h = self.grid_stock.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        l.addWidget(self.grid_stock)

    def setup_tab_composicion(self):
        layout = QVBoxLayout(self.tab_composicion)
        info = QLabel("<b>Receta o Composición del Producto:</b> Agregue los insumos o productos hijos necesarios para armar este producto.")
        layout.addWidget(info)
        
        toolbar = QHBoxLayout()
        self.txt_buscar_insumo = QLineEdit()
        self.txt_buscar_insumo.setPlaceholderText("Escriba SKU o Nombre del insumo y seleccione...")
        
        btn_add_insumo = QPushButton("➕ Añadir Insumo")
        btn_add_insumo.setStyleSheet("background-color: #2980B9; color: white; font-weight:bold;")
        btn_add_insumo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_insumo.clicked.connect(self.agregar_insumo_receta) # Conectamos el botón
        
        toolbar.addWidget(self.txt_buscar_insumo)
        toolbar.addWidget(btn_add_insumo)
        layout.addLayout(toolbar)
        
        self.grid_receta = QTableWidget(0, 6) # Ahora son 6 columnas
        self.grid_receta.setHorizontalHeaderLabels(["Código", "Descripción", "Unidad", "Cantidad Requerida", "Costo Aprox ($)", "Acción"])
        self.grid_receta.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.grid_receta)

    def toggle_tab_composicion(self, checked):
        idx = 3 
        self.tabs.setTabEnabled(idx, checked)

    def setup_tab_lotes(self):
        layout = QVBoxLayout(self.tab_lotes)
        top_panel = QFrame()
        top_panel.setStyleSheet("background-color: #E8F6F3; border: 1px solid #A2D9CE; border-radius: 4px;")
        top_layout = QHBoxLayout(top_panel)
        top_layout.addWidget(QLabel("<b>Estrategia de Precios:</b>"))
        self.radio_precio_general = QRadioButton("Usar Precio General"); self.radio_precio_lote = QRadioButton("Usar Precio por Lote")
        self.radio_precio_general.setChecked(True)
        self.bg_estrategia = QButtonGroup(); self.bg_estrategia.addButton(self.radio_precio_general); self.bg_estrategia.addButton(self.radio_precio_lote)
        self.bg_estrategia.buttonClicked.connect(self.toggle_estrategia_precios_lote)
        top_layout.addWidget(self.radio_precio_general); top_layout.addWidget(self.radio_precio_lote); top_layout.addStretch()
        layout.addWidget(top_panel)
        self.grid_lotes = QTableWidget(0, 8)
        self.grid_lotes.setHorizontalHeaderLabels(["Lote","Elab","Venc","Inicial","Vend","Rest","Costo","Precio Venta"])
        self.grid_lotes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.grid_lotes)

    def toggle_tab_lotes(self, checked):
        self.tabs.setTabEnabled(2, checked)

    def toggle_estrategia_precios_lote(self):
        es_por_lote = self.radio_precio_lote.isChecked()
        for i in range(self.grid_lotes.rowCount()):
            item = self.grid_lotes.item(i, 7)
            if not item: continue
            if es_por_lote: item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable); item.setBackground(QColor("white"))
            else: item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable); item.setBackground(QColor("#F2F2F2")); item.setText("")

    def setup_tab_precios(self):
        layout = QVBoxLayout(self.tab_precios)
        grp_costos = QGroupBox("Estructura de Costos")
        costo_layout = QHBoxLayout()
        col_conf_cost = QVBoxLayout()
        self.chk_importado = QCheckBox("Es Importado"); self.chk_importado.toggled.connect(self.toggle_importacion)
        col_conf_cost.addWidget(self.chk_importado); costo_layout.addLayout(col_conf_cost)
        
        self.frm_import = QFormLayout()
        self.spin_fob = self.crear_input_numerico(2, " $"); self.spin_flete = self.crear_input_numerico(2, " $")
        self.spin_seguro = self.crear_input_numerico(2, " $"); self.spin_arancel = self.crear_input_numerico(2, " $"); self.spin_otros = self.crear_input_numerico(2, " $")
        for spin in [self.spin_fob, self.spin_flete, self.spin_seguro, self.spin_arancel, self.spin_otros]: spin.valueChanged.connect(self.recalcular_costos_importacion)
        self.frm_import.addRow("FOB:", self.spin_fob); self.frm_import.addRow("Flete:", self.spin_flete)
        self.frm_import.addRow("Seguro:", self.spin_seguro); self.frm_import.addRow("Arancel:", self.spin_arancel)
        self.frm_import.addRow("Otros:", self.spin_otros)
        costo_layout.addLayout(self.frm_import)
        
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("COSTO BASE FINAL ($)"))
        self.spin_costo_final = self.crear_input_numerico(2, " $")
        self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #E8F8F5;")
        self.spin_costo_final.valueChanged.connect(self.recalcular_tabla_precios)
        res_layout.addWidget(self.spin_costo_final)
        res_layout.addWidget(QLabel("Costo Referencial Bs:")); self.lbl_costo_bs = QLabel("0.00 Bs")
        res_layout.addWidget(self.lbl_costo_bs); costo_layout.addLayout(res_layout)
        grp_costos.setLayout(costo_layout)
        layout.addWidget(grp_costos)
        
        self.grid_precios = QTableWidget(0, 7)
        self.grid_precios.setHorizontalHeaderLabels(["ID Tarifa", "Nombre Tarifa","Margen %","Neto $","IVA $","Final $","Final Bs"])
        self.grid_precios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_precios.hideColumn(0) 
        self.grid_precios.cellChanged.connect(self.on_grid_precios_changed)
        layout.addWidget(self.grid_precios)
        self.toggle_importacion(False)

    def toggle_importacion(self, checked):
        for s in [self.spin_fob, self.spin_flete, self.spin_seguro, self.spin_arancel, self.spin_otros]: s.setEnabled(checked)
        self.spin_costo_final.setReadOnly(checked)
        self.spin_costo_final.setStyleSheet("font-size: 16px; font-weight: bold; background-color: " + ("#E8F8F5;" if checked else "#FFFFFF;"))
        if checked: self.recalcular_costos_importacion()

    def recalcular_costos_importacion(self):
        if self.chk_importado.isChecked():
            t = self.spin_fob.value() + self.spin_flete.value() + self.spin_seguro.value() + self.spin_arancel.value() + self.spin_otros.value()
            self.spin_costo_final.blockSignals(True); self.spin_costo_final.setValue(t); self.spin_costo_final.blockSignals(False)
            self.recalcular_tabla_precios()

    def on_grid_precios_changed(self, row, col):
        if col == 2: self.recalcular_fila_precio(row) 

    def recalcular_tabla_precios(self):
        self.lbl_costo_bs.setText(f"{self.spin_costo_final.value() * self.tasa_cambio_actual:,.2f} Bs")
        self.grid_precios.blockSignals(True)
        for i in range(self.grid_precios.rowCount()): self.recalcular_fila_precio(i, False)
        self.grid_precios.blockSignals(False)

    def recalcular_fila_precio(self, row, block=True):
        try:
            item_margen = self.grid_precios.item(row, 2)
            if not item_margen: return
            margen = float(item_margen.text())
            neto = self.spin_costo_final.value() * (1 + margen/100)
            
            iva = neto * 0.16 
            f_usd = neto + iva; f_bs = f_usd * self.tasa_cambio_actual
            self.grid_precios.setItem(row, 3, QTableWidgetItem(f"{neto:.2f}"))
            self.grid_precios.setItem(row, 4, QTableWidgetItem(f"{iva:.2f}"))
            self.grid_precios.setItem(row, 5, QTableWidgetItem(f"{f_usd:.2f}"))
            self.grid_precios.setItem(row, 6, QTableWidgetItem(f"{f_bs:,.2f}"))
            
            for col in [3,4,5,6]: self.grid_precios.item(row, col).setFlags(Qt.ItemFlag.ItemIsEnabled)
        except: pass

    def setup_tab_kardex(self):
        l = QVBoxLayout(self.tab_kardex)
        self.grid_kardex = QTableWidget(0, 8)
        self.grid_kardex.setHorizontalHeaderLabels(["Fecha","Tipo","Doc","Tercero","Costo","Ent","Sal","Saldo"])
        self.grid_kardex.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.grid_kardex)

    # --------------------------------------------------------------------------
    # CARGA DINÁMICA
    # --------------------------------------------------------------------------
    def cargar_estructuras_dinamicas(self):
        if not self.conn: return
        self.cargar_combos_bd()
        
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT cod_almacen, nombre_almacen FROM inv_almacenes WHERE cod_compania = %s AND activo = true ORDER BY cod_almacen", (self.cod_compania,))
            almacenes = cur.fetchall()
            self.grid_stock.setRowCount(len(almacenes))
            for i, alm in enumerate(almacenes):
                it_cod = QTableWidgetItem(alm[0]); it_cod.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it_nom = QTableWidgetItem(alm[1]); it_nom.setFlags(Qt.ItemFlag.ItemIsEnabled)
                
                self.grid_stock.setItem(i, 0, it_cod)
                self.grid_stock.setItem(i, 1, it_nom)
                self.grid_stock.setItem(i, 2, QTableWidgetItem("")) 
                self.grid_stock.setItem(i, 3, QTableWidgetItem("")) 
                self.grid_stock.setItem(i, 4, QTableWidgetItem("")) 
                
                for col in range(5, 9):
                    it_qty = QTableWidgetItem("0.000")
                    it_qty.setFlags(Qt.ItemFlag.ItemIsEnabled) 
                    it_qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if col == 8: 
                        it_qty.setForeground(QColor("#27AE60"))
                        it_qty.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                    self.grid_stock.setItem(i, col, it_qty)
                
            cur.execute("SELECT id_tarifa, nombre_tarifa, margen_sugerido FROM inv_tarifas WHERE cod_compania = %s AND activo = true ORDER BY id_tarifa", (self.cod_compania,))
            tarifas = cur.fetchall()
            self.grid_precios.setRowCount(len(tarifas))
            for i, tar in enumerate(tarifas):
                self.grid_precios.setItem(i, 0, QTableWidgetItem(str(tar[0])))
                it_nom = QTableWidgetItem(tar[1]); it_nom.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.grid_precios.setItem(i, 1, it_nom)
                self.grid_precios.setItem(i, 2, QTableWidgetItem(str(tar[2] or 0))) 
                
            self.recalcular_tabla_precios()
            cur.close()
        except Exception as e:
            print(f"Error cargando grillas: {e}")

    def cargar_combos_bd(self):
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
            self.cmb_impuesto.clear(); self.cmb_impuesto.addItem("Exento / Sin Impuesto", None)
            for row in cur.fetchall(): self.cmb_impuesto.addItem(f"{row[1]} ({row[2]}%)", row[0])

            self.cmb_cta.clear(); self.cmb_cta.addItem("Sin asignar", None)
            cur.execute("SELECT id_cuenta, codigo_contable, nombre_cuenta FROM cfg_plan_cuentas WHERE cod_compania = %s AND activo = true", (self.cod_compania,))
            for row in cur.fetchall(): self.cmb_cta.addItem(f"{row[1]} - {row[2]}", row[0])
            cur.close()
        except Exception as e: print(f"Error combos BD: {e}")

    def filtrar_subgrupos(self):
        id_g = self.cmb_grupo.currentData()
        self.cmb_subgrupo.clear()
        if not id_g or not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id_subgrupo, nombre_subgrupo FROM inv_subgrupos WHERE id_grupo = %s AND activo = true", (id_g,))
            self.cmb_subgrupo.addItem("Seleccione...", None)
            for r in cur.fetchall(): self.cmb_subgrupo.addItem(r[1], r[0])
        except: pass

    # --------------------------------------------------------------------------
    # AUTOCOMPLETADO Y BÚSQUEDA
    # --------------------------------------------------------------------------
    def configurar_autocompletado_hibrido(self):
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT cod_producto, nombre FROM inv_productos WHERE cod_compania = %s", (self.cod_compania,))
            data = cur.fetchall()
            
            lista_sugerencias = [f"{r[0]} | {r[1]}" for r in data]
            completer = QCompleter(lista_sugerencias, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.activated.connect(self.on_sugerencia_seleccionada)
            
            self.txt_sku.setCompleter(completer)
        except: pass

    def on_sugerencia_seleccionada(self, texto):
        sku = texto.split(" | ")[0].strip()
        self.cargar_datos_producto(sku)

    def procesar_enter_sku(self):
        """
        Si el usuario da Enter y el campo está vacío, abre el buscador.
        Si escribió algo, intenta cargar el producto y salta al siguiente campo.
        """
        sku = self.txt_sku.text().strip()
        if not sku:
            self.abrir_catalogo()
        else:
            self.cargar_datos_producto(sku)
            # Salto automático al siguiente campo
            self.txt_nombre.setFocus()

    def abrir_catalogo(self):
        if not self.conn: return
        dlg = CatalogoProductosDialog(self.conn, self.cod_compania)
        dlg.producto_seleccionado.connect(self.cargar_datos_producto)
        dlg.exec()

    def limpiar_ficha(self):
        # Header
        self.txt_sku.clear()
        self.txt_sku.setReadOnly(False)
        self.txt_sku.setStyleSheet("font-weight: bold; font-size: 15px; border: 1px solid #E74C3C; background-color: #FFFFFF;")
        self.txt_nombre.clear()
        self.txt_barra.clear()
        self.lbl_imagen.setPixmap(QPixmap())
        self.lbl_imagen.setText("FOTO\n(Clic para cambiar)")
        self.lbl_stock_val.setText("0.00")
        self.btn_eliminar.setVisible(False)
        self.ruta_imagen_local = ""
        
        # Combos y checks
        self.cmb_grupo.setCurrentIndex(0)
        self.cmb_subgrupo.clear()
        self.cmb_marca.setCurrentIndex(0)
        self.cmb_unidad.setCurrentIndex(0)
        self.cmb_impuesto.setCurrentIndex(0)
        
        for spin in self.findChildren(QDoubleSpinBox): spin.setValue(0.00)
        for chk in self.findChildren(QCheckBox): 
            if chk != self.chk_activo: chk.setChecked(False)
        
        self.grid_stock.setRowCount(0)
        self.grid_precios.setRowCount(0)
        self.grid_receta.setRowCount(0)
        self.cargar_estructuras_dinamicas() 
        
        self.lbl_auditoria.setText("📝 Modo: Creación de Nuevo Producto")
        self.txt_sku.setFocus()
        
        # Bloquear pestañas que dependen de checks
        self.toggle_tab_lotes(False)
        self.toggle_tab_composicion(False)

    def cargar_datos_producto(self, sku):
        if not self.conn or not sku: return
        self.limpiar_ficha()
        
        try:
            cur = self.conn.cursor()
            sql = """SELECT nombre, cod_barra, id_grupo, id_subgrupo, id_categoria, id_marca, id_unidad, 
                            tipo_producto, partida_arancelaria, id_impuesto, id_cuenta_contable, tipo_costeo,
                            es_activo, es_servicio, es_fraccionario, es_compuesto, es_medicamento, usa_lotes, es_importado,
                            peso_kg, alto_cm, ancho_cm, largo_cm, unds_bulto, stock_minimo, stock_maximo,
                            costo_fob, costo_flete, costo_seguro, costo_arancel, costo_otros, costo_final_usd, cod_alterno, 
                            descripcion_larga, estrategia_precio_lote, fecha_registro, fecha_modifica, ruta_imagen
                     FROM inv_productos WHERE cod_producto = %s AND cod_compania = %s"""
            cur.execute(sql, (sku, self.cod_compania))
            row = cur.fetchone()
            
            if row:
                self.txt_sku.setText(sku)
                self.txt_sku.setReadOnly(True)
                self.txt_sku.setStyleSheet("font-weight: bold; font-size: 15px; border: 1px solid #BDC3C7; background-color: #E8ECEF;")
                self.txt_nombre.setText(row[0])
                self.txt_barra.setText(row[1] or "")
                
                if row[2]: self.cmb_grupo.setCurrentIndex(self.cmb_grupo.findData(row[2]))
                self.filtrar_subgrupos()
                if row[3]: self.cmb_subgrupo.setCurrentIndex(self.cmb_subgrupo.findData(row[3]))
                if row[4]: self.cmb_categoria.setCurrentIndex(self.cmb_categoria.findData(row[4]))
                if row[5]: self.cmb_marca.setCurrentIndex(self.cmb_marca.findData(row[5]))
                if row[6]: self.cmb_unidad.setCurrentIndex(self.cmb_unidad.findData(row[6]))
                
                self.cmb_tipo_prod.setCurrentText(row[7])
                self.txt_arancel.setText(row[8] or "")
                if row[9]: self.cmb_impuesto.setCurrentIndex(self.cmb_impuesto.findData(row[9]))
                if row[10]: self.cmb_cta.setCurrentIndex(self.cmb_cta.findData(row[10]))
                self.cmb_costeo.setCurrentText(row[11])

                self.chk_activo.setChecked(row[12])
                self.chk_servicio.setChecked(row[13])
                self.chk_fraccionario.setChecked(row[14])
                self.chk_compuesto.setChecked(row[15])
                self.chk_medicamento.setChecked(row[16])
                self.chk_lotes.setChecked(row[17])
                self.chk_importado.setChecked(row[18])
                
                self.spin_peso.setValue(float(row[19] or 0))
                self.spin_alto.setValue(float(row[20] or 0))
                self.spin_ancho.setValue(float(row[21] or 0))
                self.spin_largo.setValue(float(row[22] or 0))
                self.spin_bulto.setValue(float(row[23] or 1))
                self.spin_stock_min.setValue(float(row[24] or 0))
                self.spin_stock_max.setValue(float(row[25] or 0))

                self.spin_fob.setValue(float(row[26] or 0))
                self.spin_flete.setValue(float(row[27] or 0))
                self.spin_seguro.setValue(float(row[28] or 0))
                self.spin_arancel.setValue(float(row[29] or 0))
                self.spin_otros.setValue(float(row[30] or 0))
                self.spin_costo_final.setValue(float(row[31] or 0))
                
                self.txt_cod_alt.setText(row[32] or "")
                self.txt_desc_larga.setText(row[33] or "")
                
                if row[34] == 'POR_LOTE': self.radio_precio_lote.setChecked(True)
                else: self.radio_precio_general.setChecked(True)
                
                f_crea = row[35].strftime("%d/%m/%Y") if row[35] else "-"
                f_mod = row[36].strftime("%d/%m/%Y %H:%M") if row[36] else "-"
                self.lbl_auditoria.setText(f"📝 Registrado por: Sistema | Fecha: {f_crea}  ---  ✏️ Última Modificación: {f_mod}")
                self.btn_eliminar.setVisible(True)
                
                # Cargar imagen desde el servidor
                nombre_img = row[37]
                if nombre_img:
                    full_path = os.path.join(self.PATH_IMAGENES, nombre_img)
                    if os.path.exists(full_path):
                        self.lbl_imagen.setPixmap(QPixmap(full_path).scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio))
                    else:
                        self.lbl_imagen.setText("IMAGEN\nNO ENCONTRADA")

                # Cargar Existencias
                cur.execute("SELECT cod_almacen, pasillo, estante, peldano, cantidad_real FROM inv_existencias WHERE cod_producto = %s AND cod_compania = %s", (sku, self.cod_compania))
                existencias = cur.fetchall()
                stock_total_kpi = 0.0
                
                for e in existencias:
                    for i in range(self.grid_stock.rowCount()):
                        if self.grid_stock.item(i, 0).text() == e[0]:
                            self.grid_stock.setItem(i, 2, QTableWidgetItem(e[1] or ""))
                            self.grid_stock.setItem(i, 3, QTableWidgetItem(e[2] or ""))
                            self.grid_stock.setItem(i, 4, QTableWidgetItem(e[3] or ""))
                            
                            real_qty = float(e[4] or 0)
                            stock_total_kpi += real_qty
                            
                            cantidades = [real_qty, 0.0, 0.0, real_qty] # Disponible = Real (por ahora)
                            for col_offset, val in enumerate(cantidades):
                                it_qty = QTableWidgetItem(f"{val:.3f}")
                                it_qty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                                it_qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                                if col_offset == 3: 
                                    it_qty.setForeground(QColor("#27AE60"))
                                    it_qty.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                                self.grid_stock.setItem(i, 5 + col_offset, it_qty)
                            break
                            
                self.lbl_stock_val.setText(f"{stock_total_kpi:,.2f}")

                # --- CARGAR RECETA (COMPOSICIÓN) ---
                cur.execute("""
                    SELECT r.cod_producto_hijo, p.nombre, u.cod_unidad, r.cantidad_requerida, p.costo_final_usd
                    FROM inv_productos_recetas r
                    JOIN inv_productos p ON r.cod_producto_hijo = p.cod_producto AND r.cod_compania = p.cod_compania
                    LEFT JOIN inv_unidades u ON p.id_unidad = u.id_unidad
                    WHERE r.cod_producto_padre = %s AND r.cod_compania = %s
                """, (sku, self.cod_compania))
                self.grid_receta.setRowCount(0)
                for idx, rec in enumerate(cur.fetchall()):
                    self.grid_receta.insertRow(idx)
                    self.grid_receta.setItem(idx, 0, QTableWidgetItem(str(rec[0])))
                    self.grid_receta.setItem(idx, 1, QTableWidgetItem(str(rec[1])))
                    self.grid_receta.setItem(idx, 2, QTableWidgetItem(str(rec[2] or "UND")))
                    
                    it_cant = QTableWidgetItem(f"{rec[3]:.4f}")
                    self.grid_receta.setItem(idx, 3, it_cant)
                    
                    it_cost = QTableWidgetItem(f"{rec[4] or 0:.2f}")
                    it_cost.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.grid_receta.setItem(idx, 4, it_cost)
                    
                    # Botón de eliminar en la grilla
                    btn_del = QPushButton("❌")
                    btn_del.setStyleSheet("color: #E74C3C; font-weight: bold; border: none; background: transparent;")
                    btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del.clicked.connect(self.eliminar_fila_receta)
                    self.grid_receta.setCellWidget(idx, 5, btn_del)

                # --- CARGAR KARDEX (MOVIMIENTOS) ---
                cur.execute("""
                    SELECT m.fecha_movimiento, m.tipo_movimiento, m.documento_origen, 
                           COALESCE(prov.nombre_proveedor, cli.razon_social, 'Ajuste / S/I') AS tercero, 
                           m.costo_unitario_usd, m.cantidad, m.saldo_cantidad
                    FROM inv_movimientos m
                    LEFT JOIN com_proveedores prov ON m.cod_compania = prov.cod_compania AND m.cod_proveedor = prov.cod_proveedor
                    LEFT JOIN ven_clientes cli ON m.cod_compania = cli.cod_compania AND m.cod_cliente = cli.cod_cliente
                    WHERE m.cod_producto = %s AND m.cod_compania = %s
                    ORDER BY m.fecha_movimiento DESC LIMIT 100
                """, (sku, self.cod_compania))
                
                self.grid_kardex.setRowCount(0)
                for idx, mov in enumerate(cur.fetchall()):
                    self.grid_kardex.insertRow(idx)
                    self.grid_kardex.setItem(idx, 0, QTableWidgetItem(mov[0].strftime("%d/%m/%Y %H:%M")))
                    self.grid_kardex.setItem(idx, 1, QTableWidgetItem(str(mov[1])))
                    self.grid_kardex.setItem(idx, 2, QTableWidgetItem(str(mov[2] or "")))
                    self.grid_kardex.setItem(idx, 3, QTableWidgetItem(str(mov[3]))) # Muestra Proveedor, Cliente o "Ajuste / S/I"
                    self.grid_kardex.setItem(idx, 4, QTableWidgetItem(f"{mov[4]:.2f}"))
                    
                    cant = float(mov[5] or 0)
                    if mov[1] == 'ENTRADA':
                        self.grid_kardex.setItem(idx, 5, QTableWidgetItem(f"{cant:.3f}"))
                        self.grid_kardex.setItem(idx, 6, QTableWidgetItem(""))
                    else:
                        self.grid_kardex.setItem(idx, 5, QTableWidgetItem(""))
                        self.grid_kardex.setItem(idx, 6, QTableWidgetItem(f"{cant:.3f}"))
                    
                    it_saldo = QTableWidgetItem(f"{mov[6]:.3f}")
                    # it_saldo.setFont(QFont("Arial", 9, QFont.Weight.Bold)) # Descomenta si importaste QFont
                    self.grid_kardex.setItem(idx, 7, it_saldo)
                    
                # Cargar Precios
                cur.execute("SELECT id_tarifa, margen_porcentaje FROM inv_precios WHERE cod_producto = %s AND cod_compania = %s", (sku, self.cod_compania))
                precios = cur.fetchall()
                for p in precios:
                    for i in range(self.grid_precios.rowCount()):
                        if self.grid_precios.item(i, 0).text() == str(p[0]):
                            self.grid_precios.setItem(i, 2, QTableWidgetItem(str(p[1] or 0)))
                            break
                self.recalcular_tabla_precios()
                self.calcular_volumen()
            else:
                QMessageBox.information(self, "Nuevo", f"El código {sku} está disponible para ser creado.")
                self.txt_sku.setText(sku)
                self.txt_nombre.setFocus()
        except Exception as e:
            QMessageBox.warning(self, "Error Carga", f"No se pudo cargar: {e}")

    # --------------------------------------------------------------------------
    # GUARDAR Y ELIMINAR 
    # --------------------------------------------------------------------------
    def guardar_producto(self):
        sku = self.txt_sku.text().strip().upper()
        nombre = self.txt_nombre.text().strip()
        
        if not sku or not nombre:
            QMessageBox.warning(self, "Validación", "El SKU y el Nombre son obligatorios (están marcados en rojo).")
            return

        try:
            cur = self.conn.cursor()
            nombre_imagen = self.procesar_imagen_servidor(sku)
            
            sql_prod = """
                INSERT INTO inv_productos (
                    cod_compania, cod_producto, nombre, descripcion_larga, cod_barra, cod_alterno,
                    id_grupo, id_subgrupo, id_categoria, id_marca, id_unidad, tipo_producto, partida_arancelaria,
                    id_impuesto, id_cuenta_contable, tipo_costeo, es_activo, es_servicio, es_fraccionario,
                    es_compuesto, es_medicamento, usa_lotes, es_importado, estrategia_precio_lote,
                    peso_kg, alto_cm, ancho_cm, largo_cm, volumen_m3, unds_bulto, stock_minimo, stock_maximo,
                    costo_fob, costo_flete, costo_seguro, costo_arancel, costo_otros, costo_final_usd, id_usuario_crea,
                    ruta_imagen
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (cod_compania, cod_producto) DO UPDATE SET
                    nombre = EXCLUDED.nombre, descripcion_larga = EXCLUDED.descripcion_larga, 
                    cod_barra = EXCLUDED.cod_barra, cod_alterno = EXCLUDED.cod_alterno,
                    id_grupo = EXCLUDED.id_grupo, id_subgrupo = EXCLUDED.id_subgrupo, id_categoria = EXCLUDED.id_categoria,
                    id_marca = EXCLUDED.id_marca, id_unidad = EXCLUDED.id_unidad, tipo_producto = EXCLUDED.tipo_producto,
                    partida_arancelaria = EXCLUDED.partida_arancelaria, id_impuesto = EXCLUDED.id_impuesto, 
                    id_cuenta_contable = EXCLUDED.id_cuenta_contable, tipo_costeo = EXCLUDED.tipo_costeo,
                    es_activo = EXCLUDED.es_activo, es_servicio = EXCLUDED.es_servicio, es_fraccionario = EXCLUDED.es_fraccionario,
                    es_compuesto = EXCLUDED.es_compuesto, es_medicamento = EXCLUDED.es_medicamento, usa_lotes = EXCLUDED.usa_lotes,
                    es_importado = EXCLUDED.es_importado, estrategia_precio_lote = EXCLUDED.estrategia_precio_lote,
                    peso_kg = EXCLUDED.peso_kg, alto_cm = EXCLUDED.alto_cm, ancho_cm = EXCLUDED.ancho_cm, largo_cm = EXCLUDED.largo_cm,
                    volumen_m3 = EXCLUDED.volumen_m3, unds_bulto = EXCLUDED.unds_bulto, stock_minimo = EXCLUDED.stock_minimo, 
                    stock_maximo = EXCLUDED.stock_maximo, costo_fob = EXCLUDED.costo_fob, costo_flete = EXCLUDED.costo_flete,
                    costo_seguro = EXCLUDED.costo_seguro, costo_arancel = EXCLUDED.costo_arancel, costo_otros = EXCLUDED.costo_otros,
                    costo_final_usd = EXCLUDED.costo_final_usd, fecha_modifica = CURRENT_TIMESTAMP,
                    ruta_imagen = COALESCE(EXCLUDED.ruta_imagen, inv_productos.ruta_imagen)
            """
            
            vol_str = self.lbl_vol.text().replace(" m³", "").replace(",", ".")
            vol = float(vol_str) if vol_str else 0.0
            est_precio = "GENERAL" if self.radio_precio_general.isChecked() else "POR_LOTE"
            
            params_prod = (
                self.cod_compania, sku, nombre, self.txt_desc_larga.text(), self.txt_barra.text(), self.txt_cod_alt.text(),
                self.cmb_grupo.currentData(), self.cmb_subgrupo.currentData(), self.cmb_categoria.currentData(), 
                self.cmb_marca.currentData(), self.cmb_unidad.currentData(), self.cmb_tipo_prod.currentText(),
                self.txt_arancel.text(), self.cmb_impuesto.currentData(), self.cmb_cta.currentData(), self.cmb_costeo.currentText(),
                self.chk_activo.isChecked(), self.chk_servicio.isChecked(), self.chk_fraccionario.isChecked(),
                self.chk_compuesto.isChecked(), self.chk_medicamento.isChecked(), self.chk_lotes.isChecked(),
                self.chk_importado.isChecked(), est_precio,
                self.spin_peso.value(), self.spin_alto.value(), self.spin_ancho.value(), self.spin_largo.value(),
                vol, self.spin_bulto.value(), self.spin_stock_min.value(), self.spin_stock_max.value(),
                self.spin_fob.value(), self.spin_flete.value(), self.spin_seguro.value(), self.spin_arancel.value(),
                self.spin_otros.value(), self.spin_costo_final.value(), self.id_usuario, nombre_imagen
            )
            cur.execute(sql_prod, params_prod)

            for i in range(self.grid_stock.rowCount()):
                cod_alm = self.grid_stock.item(i, 0).text()
                pasillo = self.grid_stock.item(i, 2).text() if self.grid_stock.item(i, 2) else ""
                estante = self.grid_stock.item(i, 3).text() if self.grid_stock.item(i, 3) else ""
                peldano = self.grid_stock.item(i, 4).text() if self.grid_stock.item(i, 4) else ""
                
                sql_ex = """
                    INSERT INTO inv_existencias (cod_compania, cod_almacen, cod_producto, pasillo, estante, peldano)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cod_compania, cod_almacen, cod_producto) DO UPDATE SET
                    pasillo = EXCLUDED.pasillo, estante = EXCLUDED.estante, peldano = EXCLUDED.peldano
                """
                cur.execute(sql_ex, (self.cod_compania, cod_alm, sku, pasillo, estante, peldano))

            for i in range(self.grid_precios.rowCount()):
                id_tar = int(self.grid_precios.item(i, 0).text())
                try: margen = float(self.grid_precios.item(i, 2).text() or 0)
                except: margen = 0.0
                try: neto = float(self.grid_precios.item(i, 3).text() or 0)
                except: neto = 0.0
                try: iva = float(self.grid_precios.item(i, 4).text() or 0)
                except: iva = 0.0
                try: f_usd = float(self.grid_precios.item(i, 5).text() or 0)
                except: f_usd = 0.0
                try: f_bs = float(self.grid_precios.item(i, 6).text().replace(',', '') or 0)
                except: f_bs = 0.0
                
                sql_pr = """
                    INSERT INTO inv_precios (cod_compania, cod_producto, id_tarifa, margen_porcentaje, precio_neto_usd, monto_iva_usd, precio_final_usd, precio_final_bs)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cod_compania, cod_producto, id_tarifa) DO UPDATE SET
                    margen_porcentaje = EXCLUDED.margen_porcentaje, precio_neto_usd = EXCLUDED.precio_neto_usd,
                    monto_iva_usd = EXCLUDED.monto_iva_usd, precio_final_usd = EXCLUDED.precio_final_usd, precio_final_bs = EXCLUDED.precio_final_bs
                """
                cur.execute(sql_pr, (self.cod_compania, sku, id_tar, margen, neto, iva, f_usd, f_bs))

            if self.chk_compuesto.isChecked():
                cur.execute("DELETE FROM inv_productos_recetas WHERE cod_compania = %s AND cod_producto_padre = %s", (self.cod_compania, sku))
                for i in range(self.grid_receta.rowCount()):
                    hijo_sku = self.grid_receta.item(i, 0).text()
                    try: cant_req = float(self.grid_receta.item(i, 3).text() or 0)
                    except: cant_req = 0.0
                    if hijo_sku and cant_req > 0:
                        cur.execute("INSERT INTO inv_productos_recetas (cod_compania, cod_producto_padre, cod_producto_hijo, cantidad_requerida) VALUES (%s, %s, %s, %s)", (self.cod_compania, sku, hijo_sku, cant_req))

            self.conn.commit()
            QMessageBox.information(self, "Guardado", f"El producto {sku} se guardó exitosamente.")
            self.configurar_autocompletado_hibrido() 
            self.cargar_datos_producto(sku) 
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error BD", f"Error al guardar:\n{str(e)}")

    def eliminar_producto(self):
        sku = self.txt_sku.text()
        if not sku: return
        resp = QMessageBox.question(self, "Confirmar", f"¿Eliminar definitivamente el producto {sku}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            try:
                cur = self.conn.cursor()
                cur.execute("DELETE FROM inv_productos_recetas WHERE cod_compania=%s AND cod_producto_padre=%s", (self.cod_compania, sku))
                cur.execute("DELETE FROM inv_existencias WHERE cod_producto=%s AND cod_compania=%s", (sku, self.cod_compania))
                cur.execute("DELETE FROM inv_precios WHERE cod_producto=%s AND cod_compania=%s", (sku, self.cod_compania))
                cur.execute("DELETE FROM inv_productos WHERE cod_producto=%s AND cod_compania=%s", (sku, self.cod_compania))
                self.conn.commit()
                QMessageBox.information(self, "Eliminado", "Producto eliminado.")
                self.limpiar_ficha()
            except Exception as e:
                self.conn.rollback()
                QMessageBox.warning(self, "Bloqueo", "No se puede eliminar el producto porque está en uso.")

    def abrir_maestro(self, titulo, tabla, pk, campo_nombre):
        if not self.conn: return
        dlg = MaestroAuxiliarDialog(self.conn, self.cod_compania, titulo, tabla, pk, campo_nombre)
        dlg.datos_actualizados.connect(self.cargar_combos_bd)
        dlg.exec()
        
    def abrir_subgrupo(self):
        id_g = self.cmb_grupo.currentData()
        if not id_g:
            QMessageBox.warning(self, "Atención", "Seleccione un Grupo primero.")
            return
        if not self.conn: return
        dlg = MaestroAuxiliarDialog(self.conn, self.cod_compania, "Subgrupos", "inv_subgrupos", "id_subgrupo", "nombre_subgrupo", parent_id=id_g, campo_fk="id_grupo")
        dlg.datos_actualizados.connect(self.filtrar_subgrupos)
        dlg.exec()

    # --------------------------------------------------------------------------
    # LÓGICA DE LA RECETA / COMPOSICIÓN
    # --------------------------------------------------------------------------
    def configurar_autocompletado_insumos(self):
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT cod_producto, nombre FROM inv_productos WHERE cod_compania = %s", (self.cod_compania,))
            data = cur.fetchall()
            lista_sugerencias = [f"{r[0]} | {r[1]}" for r in data]
            completer = QCompleter(lista_sugerencias, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.txt_buscar_insumo.setCompleter(completer)
        except: pass

    def agregar_insumo_receta(self):
        texto = self.txt_buscar_insumo.text().strip()
        if not texto: return
        
        # Extraer el SKU de la sugerencia "CÓDIGO | NOMBRE"
        sku_hijo = texto.split(" | ")[0].strip()
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT p.nombre, u.cod_unidad, p.costo_final_usd 
                FROM inv_productos p 
                LEFT JOIN inv_unidades u ON p.id_unidad = u.id_unidad 
                WHERE p.cod_producto = %s AND p.cod_compania = %s
            """, (sku_hijo, self.cod_compania))
            row = cur.fetchone()
            
            if row:
                # 1. Verificar que no agregue el mismo producto que estamos editando
                if sku_hijo == self.txt_sku.text():
                    QMessageBox.warning(self, "Operación Inválida", "Un producto no puede ser insumo de sí mismo.")
                    return

                # 2. Verificar que no exista ya en la grilla
                for i in range(self.grid_receta.rowCount()):
                    if self.grid_receta.item(i, 0).text() == sku_hijo:
                        QMessageBox.warning(self, "Aviso", "Este insumo ya se encuentra en la receta.")
                        return
                        
                # 3. Agregar a la grilla
                idx = self.grid_receta.rowCount()
                self.grid_receta.insertRow(idx)
                
                self.grid_receta.setItem(idx, 0, QTableWidgetItem(sku_hijo))
                self.grid_receta.setItem(idx, 1, QTableWidgetItem(row[0]))
                self.grid_receta.setItem(idx, 2, QTableWidgetItem(row[1] or "UND"))
                
                it_cant = QTableWidgetItem("1.0000") # Cantidad por defecto
                self.grid_receta.setItem(idx, 3, it_cant)
                
                it_costo = QTableWidgetItem(f"{row[2] or 0:.2f}")
                it_costo.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.grid_receta.setItem(idx, 4, it_costo)
                
                btn_del = QPushButton("❌")
                btn_del.setStyleSheet("color: #E74C3C; font-weight: bold; border: none; background: transparent;")
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.clicked.connect(self.eliminar_fila_receta)
                self.grid_receta.setCellWidget(idx, 5, btn_del)
                
                self.txt_buscar_insumo.clear()
            else:
                QMessageBox.warning(self, "Error", "El código de insumo seleccionado no existe.")
        except Exception as e:
            print(f"Error agregando insumo: {e}")

    def eliminar_fila_receta(self):
        # Esta es la forma 100% segura de eliminar filas dinámicas en PyQt
        boton = self.sender()
        if boton:
            index = self.grid_receta.indexAt(boton.pos())
            if index.isValid():
                self.grid_receta.removeRow(index.row())

    def calcular_volumen(self):
        v = (self.spin_alto.value() * self.spin_ancho.value() * self.spin_largo.value()) / 1000000
        self.lbl_vol.setText(f"{v:.4f} m³")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ProductosForm(1, 1, "Sin BD")
    win.show()
    sys.exit(app.exec())