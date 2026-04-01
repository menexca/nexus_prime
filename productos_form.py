# -*- coding: utf-8 -*-
import sys
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

try:
    from db_config import DB_PARAMS
except ImportError:
    DB_PARAMS = {}

# ==============================================================================
# CLASE AUXILIAR: DIÁLOGO GENÉRICO PARA MAESTROS (CRUD)
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
        grp = QGroupBox("Datos del Registro")
        frm = QFormLayout()
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Código (Opcional)")
        self.txt_descripcion = QLineEdit()
        self.txt_descripcion.setPlaceholderText("Nombre / Descripción")
        
        frm.addRow("Código:", self.txt_codigo)
        frm.addRow("Descripción:", self.txt_descripcion)
        
        btn_box = QHBoxLayout()
        self.btn_nuevo = QPushButton("Limpiar / Nuevo")
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_nuevo.clicked.connect(self.limpiar_form)
        self.btn_guardar.clicked.connect(self.guardar_registro)
        
        btn_box.addWidget(self.btn_nuevo)
        btn_box.addWidget(self.btn_guardar)
        frm.addRow(btn_box)
        grp.setLayout(frm)
        layout.addWidget(grp)
        
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar...")
        self.txt_buscar.textChanged.connect(self.cargar_datos)
        layout.addWidget(self.txt_buscar)
        
        self.tabla_lista = QTableWidget()
        self.tabla_lista.setColumnCount(3)
        self.tabla_lista.setHorizontalHeaderLabels(["ID", "Descripción", "Activo"])
        self.tabla_lista.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_lista.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_lista.cellDoubleClicked.connect(self.cargar_registro_seleccionado)
        layout.addWidget(self.tabla_lista)
        
        self.setLayout(layout)
        self.id_edicion = None

    def cargar_datos(self):
        if not self.conn: return
        filtro = self.txt_buscar.text()
        try:
            cur = self.conn.cursor()
            sql = f"SELECT {self.pk}, {self.campo_nombre}, activo FROM {self.tabla} WHERE cod_compania = %s"
            params = [self.cod_compania]
            if self.parent_id and self.campo_fk:
                sql += f" AND {self.campo_fk} = %s"
                params.append(self.parent_id)
            if filtro:
                sql += f" AND {self.campo_nombre} ILIKE %s"
                params.append(f"%{filtro}%")
            sql += f" ORDER BY {self.campo_nombre}"
            cur.execute(sql, tuple(params))
            filas = cur.fetchall()
            
            self.tabla_lista.setRowCount(0)
            for row in filas:
                idx = self.tabla_lista.rowCount()
                self.tabla_lista.insertRow(idx)
                self.tabla_lista.setItem(idx, 0, QTableWidgetItem(str(row[0])))
                self.tabla_lista.setItem(idx, 1, QTableWidgetItem(row[1]))
                self.tabla_lista.setItem(idx, 2, QTableWidgetItem("SI" if row[2] else "NO"))
                self.tabla_lista.item(idx, 0).setData(Qt.ItemDataRole.UserRole, row[0])
        except Exception as e:
            pass

    def guardar_registro(self):
        nombre = self.txt_descripcion.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return
        try:
            cur = self.conn.cursor()
            if self.id_edicion is None:
                cols = f"cod_compania, {self.campo_nombre}"
                vals = "%s, %s"
                params = [self.cod_compania, nombre]
                if self.parent_id and self.campo_fk:
                    cols += f", {self.campo_fk}"
                    vals += ", %s"
                    params.append(self.parent_id)
                sql = f"INSERT INTO {self.tabla} ({cols}) VALUES ({vals})"
                cur.execute(sql, tuple(params))
            else:
                sql = f"UPDATE {self.tabla} SET {self.campo_nombre} = %s WHERE {self.pk} = %s"
                cur.execute(sql, (nombre, self.id_edicion))
            
            self.conn.commit()
            self.limpiar_form()
            self.cargar_datos()
            self.datos_actualizados.emit()
            QMessageBox.information(self, "Éxito", "Registro guardado.")
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error Guardar", str(e))

    def cargar_registro_seleccionado(self, row, col):
        item_id = self.tabla_lista.item(row, 0)
        self.id_edicion = item_id.data(Qt.ItemDataRole.UserRole)
        self.txt_descripcion.setText(self.tabla_lista.item(row, 1).text())
    
    def limpiar_form(self):
        self.id_edicion = None
        self.txt_codigo.clear()
        self.txt_descripcion.clear()

# ==============================================================================
# CATÁLOGO DE PRODUCTOS (BUSCADOR AVANZADO)
# ==============================================================================
class CatalogoProductosDialog(QDialog):
    producto_seleccionado = pyqtSignal(str) 

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
        h_layout = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por Código, Nombre o Referencia...")
        self.txt_buscar.textChanged.connect(self.buscar)
        h_layout.addWidget(self.txt_buscar)
        layout.addLayout(h_layout)
        
        self.tabla = QTableWidget()
        cols = ["SKU", "Nombre", "Marca", "Ref.", "Precio Base ($)"]
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
                SELECT p.cod_producto, p.nombre, m.nombre_marca, p.cod_alterno, p.costo_final_usd
                FROM inv_productos p
                LEFT JOIN inv_marcas m ON p.id_marca = m.id_marca
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
        except Exception as e:
            pass

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
        self.nombre_usuario_actual = "Usuario"
        
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
        self.ruta_imagen_actual = ""
        
        self.setWindowTitle("Ficha Maestra de Productos - NEXUS PRIME")
        self.resize(1150, 800)
        self.set_style_local()
        self.init_ui()
        
        if self.conn:
            self.cargar_estructuras_dinamicas() # Carga combos, almacenes y tarifas
            self.configurar_autocompletado() 
        else:
            QMessageBox.critical(self, "Error", "No hay conexión a la base de datos.")
            
        self.recalcular_costos_importacion()
        self.toggle_tab_lotes(False)
        self.toggle_tab_composicion(False)
        self.toggle_estrategia_precios_lote()

    def closeEvent(self, event):
        if self.conn_propia and self.conn:
            self.conn.close()
        event.accept()

    def set_style_local(self):
        self.setStyleSheet("""
            QWidget { background-color: #E8ECEF; color: #333; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { font-weight: bold; border: 1px solid #BDC3C7; border-radius: 6px; margin-top: 25px; padding-top: 15px; padding-bottom: 10px; background-color: #E8ECEF; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px; padding: 5px 8px; color: #2C3E50; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; padding: 5px; min-height: 22px; selection-background-color: #3498DB; }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 1px solid #3498DB; }
            QTabWidget::pane { border: 1px solid #BDC3C7; background: #FFFFFF; }
            QTabBar::tab { background: #D5DBDB; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px;}
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; border-bottom: none; }
            QTableWidget { background-color: #FFFFFF; alternate-background-color: #F9F9F9; gridline-color: #EEEEEE; border: 1px solid #DDDDDD; }
            QHeaderView::section { background-color: #34495E; color: white; padding: 6px; font-weight: bold; border: none; font-size: 11px; }
            QPushButton[cssClass="btn_plus"] { background-color: #3498DB; color: white; font-weight: bold; border-radius: 4px; max-width: 30px; }
            QPushButton[cssClass="btn_plus"]:hover { background-color: #2980B9; }
            QPushButton[cssClass="btn_search"] { background-color: #E67E22; color: white; font-weight: bold; border: none; border-radius: 4px; padding: 6px; text-align: left; }
            QPushButton[cssClass="btn_search"]:hover { background-color: #D35400; }
            QPushButton[cssClass="btn_delete"] { background-color: #E74C3C; color: white; font-weight: bold; border-radius: 4px; padding: 10px; }
            QPushButton[cssClass="btn_delete"]:hover { background-color: #C0392B; }
        """)

    def crear_input_numerico(self, decimals=2, suffix=""):
        spin = QDoubleSpinBox()
        spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        spin.setDecimals(decimals)
        spin.setRange(0, 9999999.99)
        if suffix: spin.setSuffix(suffix)
        return spin

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10) 

        # --- HEADER ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D5DBDB; border-radius: 8px;")
        header_frame.setFixedHeight(160) 
        header_layout = QHBoxLayout(header_frame)
        
        self.lbl_imagen = ClickableLabel("FOTO\n(Clic para cambiar)")
        self.lbl_imagen.setFixedSize(135, 135)
        self.lbl_imagen.setStyleSheet("border: 2px dashed #BDC3C7; background-color: #F8F9F9; font-weight:bold; color: #95A5A6;")
        self.lbl_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_imagen.setScaledContents(True)
        self.lbl_imagen.clicked.connect(self.seleccionar_imagen)
        header_layout.addWidget(self.lbl_imagen)
        
        ident_layout = QFormLayout()
        sku_layout = QHBoxLayout()
        self.btn_buscar_sku = QPushButton("🔍 Código SKU:")
        self.btn_buscar_sku.setProperty("cssClass", "btn_search")
        self.btn_buscar_sku.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buscar_sku.setFixedWidth(110)
        self.btn_buscar_sku.clicked.connect(self.abrir_catalogo) 
        
        self.txt_sku = QLineEdit()
        self.txt_sku.setPlaceholderText("Escriba código o presione Buscar...")
        self.txt_sku.setStyleSheet("font-weight: bold; font-size: 15px;")
        self.txt_sku.returnPressed.connect(lambda: self.cargar_datos_producto(self.txt_sku.text()))
        
        sku_layout.addWidget(self.btn_buscar_sku)
        sku_layout.addWidget(self.txt_sku)
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Escriba nombre para buscar...")
        self.txt_nombre.setStyleSheet("font-weight: bold; font-size: 18px;")
        self.txt_barra = QLineEdit()
        
        ident_layout.addRow(sku_layout) 
        ident_layout.addRow("Nombre:", self.txt_nombre)
        ident_layout.addRow("Cod. Barras:", self.txt_barra)
        header_layout.addLayout(ident_layout, stretch=2)
        
        kpi_layout = QVBoxLayout()
        self.chk_activo = QCheckBox("PRODUCTO ACTIVO"); self.chk_activo.setChecked(True)
        self.chk_activo.setStyleSheet("color: #27AE60; font-weight:bold; font-size: 13px;")
        self.lbl_stock_val = QLabel("0.00")
        self.lbl_stock_val.setStyleSheet("font-size: 28px; font-weight: bold; color: #2980B9;")
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
        self.tab_composicion = QWidget(); self.setup_tab_composicion(); self.tabs.addTab(self.tab_composicion, "🧩 Composición / Receta")
        self.tab_precios = QWidget(); self.setup_tab_precios(); self.tabs.addTab(self.tab_precios, "💰 Costos y Precios")
        self.tab_kardex = QWidget(); self.setup_tab_kardex(); self.tabs.addTab(self.tab_kardex, "📊 Kardex")
        main_layout.addWidget(self.tabs)
        
        # --- FOOTER BOTONES Y AUDITORÍA ---
        footer_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        
        btn_limpiar = QPushButton("🧹 Limpiar Ficha")
        btn_limpiar.setStyleSheet("background-color: #95A5A6; color: white; padding: 10px; font-weight: bold; border-radius:4px;")
        btn_limpiar.clicked.connect(self.limpiar_ficha)
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.setProperty("cssClass", "btn_delete")
        self.btn_eliminar.clicked.connect(self.eliminar_producto)
        self.btn_eliminar.setVisible(False) # Solo se muestra si el producto existe
        
        btn_save = QPushButton("💾 GUARDAR / ACTUALIZAR")
        btn_save.setStyleSheet("background-color: #27AE60; color: white; padding: 10px 25px; font-weight: bold; font-size: 14px; border-radius:4px;")
        btn_save.clicked.connect(self.guardar_producto)
        
        btn_layout.addWidget(btn_limpiar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        self.lbl_auditoria = QLabel(f"📝 Registrado por: {self.nombre_usuario_actual} | Fecha: {fecha_hoy}  ---  ✏️ Modificado por: Ninguno | Fecha Mod: -")
        self.lbl_auditoria.setStyleSheet("color: #7F8C8D; font-size: 11px; font-style: italic; margin-top: 5px;")
        
        footer_layout.addLayout(btn_layout)
        footer_layout.addWidget(self.lbl_auditoria, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(footer_layout)
        
        self.setLayout(main_layout)

    def crear_selector_con_boton(self, funcion_plus):
        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(4) # Un poquito más de separación
        
        combo = QComboBox()
        
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(30, 26) # Tamaño un poco más cómodo para hacer clic
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # APLICAMOS EL ESTILO DIRECTAMENTE AQUÍ (A prueba de fallos)
        btn_plus.setStyleSheet("""
            QPushButton {
                background-color: #3498DB; 
                color: white; 
                font-weight: bold; 
                font-size: 16px;
                border-radius: 4px; 
            }
            QPushButton:hover { 
                background-color: #2980B9; 
            }
        """)
        
        btn_plus.clicked.connect(funcion_plus)
        
        h_layout.addWidget(combo)
        h_layout.addWidget(btn_plus)
        
        return widget, combo

    # --------------------------------------------------------------------------
    # PESTAÑA GENERAL 
    # --------------------------------------------------------------------------
    def setup_tab_general(self):
        main_layout = QVBoxLayout(self.tab_general)
        self.tab_general.setStyleSheet("background-color: #FFFFFF;") 
        
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
        self.tab_stock.setStyleSheet("background-color: #FFFFFF;")
        l = QVBoxLayout(self.tab_stock)
        
        self.grid_stock = QTableWidget(0, 9) 
        self.grid_stock.setHorizontalHeaderLabels([
            "ID Almacén", "Nombre Almacén", "Pasillo", "Estante", "Peldaño", 
            "Existencia Real", "Pedidos", "Ord. Compra", "Disponible"
        ])
        
        h = self.grid_stock.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID más pequeño
        
        l.addWidget(self.grid_stock)

    def setup_tab_composicion(self):
        layout = QVBoxLayout(self.tab_composicion)
        self.tab_composicion.setStyleSheet("background-color: #FFFFFF;")
        info = QLabel("<b>Receta o Composición del Producto:</b> Agregue los insumos o productos hijos necesarios para armar este producto.")
        layout.addWidget(info)
        toolbar = QHBoxLayout()
        self.txt_buscar_insumo = QLineEdit(); self.txt_buscar_insumo.setPlaceholderText("Buscar insumo por Código o Nombre...")
        btn_add_insumo = QPushButton("➕ Añadir Insumo")
        btn_add_insumo.setStyleSheet("background-color: #2980B9; color: white; font-weight:bold;")
        toolbar.addWidget(self.txt_buscar_insumo); toolbar.addWidget(btn_add_insumo)
        layout.addLayout(toolbar)
        self.grid_receta = QTableWidget(0, 5)
        self.grid_receta.setHorizontalHeaderLabels(["Código", "Descripción", "Unidad", "Cantidad Requerida", "Costo Aprox ($)"])
        self.grid_receta.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.grid_receta)

    def toggle_tab_composicion(self, checked):
        idx = 3 
        self.tabs.setTabEnabled(idx, checked)
        if checked: self.tabs.setCurrentIndex(idx) 

    def setup_tab_lotes(self):
        self.tab_lotes.setStyleSheet("background-color: #FFFFFF;")
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
        self.tab_precios.setStyleSheet("background-color: #FFFFFF;")
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
        
        # Grid Precios (Se llena desde DB)
        self.grid_precios = QTableWidget(0, 7)
        self.grid_precios.setHorizontalHeaderLabels(["ID Tarifa", "Nombre Tarifa","Margen %","Neto $","IVA $","Final $","Final Bs"])
        self.grid_precios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grid_precios.hideColumn(0) # Ocultar ID Tarifa
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
        if col == 2: self.recalcular_fila_precio(row) # Columna Margen

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
            
            # TODO: Leer porcentaje real del combobox de IVA
            iva = neto * 0.16 
            f_usd = neto + iva; f_bs = f_usd * self.tasa_cambio_actual
            self.grid_precios.setItem(row, 3, QTableWidgetItem(f"{neto:.2f}"))
            self.grid_precios.setItem(row, 4, QTableWidgetItem(f"{iva:.2f}"))
            self.grid_precios.setItem(row, 5, QTableWidgetItem(f"{f_usd:.2f}"))
            self.grid_precios.setItem(row, 6, QTableWidgetItem(f"{f_bs:,.2f}"))
            
            # Poner columnas como ReadOnly
            for col in [3,4,5,6]: self.grid_precios.item(row, col).setFlags(Qt.ItemFlag.ItemIsEnabled)
        except: pass

    def setup_tab_kardex(self):
        self.tab_kardex.setStyleSheet("background-color: #FFFFFF;")
        l = QVBoxLayout(self.tab_kardex)
        self.grid_kardex = QTableWidget(0, 8)
        self.grid_kardex.setHorizontalHeaderLabels(["Fecha","Tipo","Doc","Tercero","Costo","Ent","Sal","Saldo"])
        self.grid_kardex.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.grid_kardex)

    # --------------------------------------------------------------------------
    # CARGA DE ESTRUCTURAS DE BASE DE DATOS (COMBOS, GRILLAS DINÁMICAS)
    # --------------------------------------------------------------------------
    def cargar_estructuras_dinamicas(self):
        if not self.conn: return
        self.cargar_combos_bd()
        
        try:
            cur = self.conn.cursor()
            
            # Llenar Grilla de Almacenes Dinámica
            cur.execute("SELECT cod_almacen, nombre_almacen FROM inv_almacenes WHERE cod_compania = %s AND activo = true ORDER BY cod_almacen", (self.cod_compania,))
            almacenes = cur.fetchall()
            self.grid_stock.setRowCount(len(almacenes))
            for i, alm in enumerate(almacenes):
                it_cod = QTableWidgetItem(alm[0]); it_cod.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it_nom = QTableWidgetItem(alm[1]); it_nom.setFlags(Qt.ItemFlag.ItemIsEnabled)
                
                self.grid_stock.setItem(i, 0, it_cod)
                self.grid_stock.setItem(i, 1, it_nom)
                self.grid_stock.setItem(i, 2, QTableWidgetItem("")) # Pasillo
                self.grid_stock.setItem(i, 3, QTableWidgetItem("")) # Estante
                self.grid_stock.setItem(i, 4, QTableWidgetItem("")) # Peldaño
                
                # Inicializar cantidades en 0.000 (Solo lectura y alineadas a la derecha)
                for col in range(5, 9):
                    it_qty = QTableWidgetItem("0.000")
                    it_qty.setFlags(Qt.ItemFlag.ItemIsEnabled) # Bloqueado
                    it_qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if col == 8: # Color al disponible para resaltar
                        it_qty.setForeground(QColor("#27AE60"))
                        it_qty.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                    self.grid_stock.setItem(i, col, it_qty)
                
            # Llenar Grilla de Tarifas de Precio Dinámica
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
            self.cmb_impuesto.clear()
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
    # BÚSQUEDA Y CRUD EN BD (LA MAGIA UPSERT)
    # --------------------------------------------------------------------------
    def configurar_autocompletado(self):
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT cod_producto FROM inv_productos WHERE cod_compania = %s", (self.cod_compania,))
            skus = [r[0] for r in cur.fetchall()]
            comp_sku = QCompleter(skus, self)
            comp_sku.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            comp_sku.setFilterMode(Qt.MatchFlag.MatchContains)
            self.txt_sku.setCompleter(comp_sku)
            comp_sku.activated.connect(self.cargar_datos_producto)

            cur.execute("SELECT nombre FROM inv_productos WHERE cod_compania = %s", (self.cod_compania,))
            nombres = [r[0] for r in cur.fetchall()]
            comp_nom = QCompleter(nombres, self)
            comp_nom.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            comp_nom.setFilterMode(Qt.MatchFlag.MatchContains)
            self.txt_nombre.setCompleter(comp_nom)
            comp_nom.activated.connect(self.cargar_por_nombre)
        except: pass

    def abrir_catalogo(self):
        if not self.conn: return
        dlg = CatalogoProductosDialog(self.conn, self.cod_compania)
        dlg.producto_seleccionado.connect(self.cargar_datos_producto)
        dlg.exec()

    def cargar_por_nombre(self, nombre):
        if not self.conn: return
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT cod_producto FROM inv_productos WHERE nombre = %s AND cod_compania = %s", (nombre, self.cod_compania))
            r = cur.fetchone()
            if r: self.cargar_datos_producto(r[0])
        except: pass

    def cargar_datos_producto(self, sku):
        if not self.conn or not sku: return
        try:
            cur = self.conn.cursor()
            # 1. Cargar Ficha Principal
            sql = """SELECT nombre, cod_barra, id_grupo, id_subgrupo, id_categoria, id_marca, id_unidad, 
                            tipo_producto, partida_arancelaria, id_impuesto, id_cuenta_contable, tipo_costeo,
                            es_activo, es_servicio, es_fraccionario, es_compuesto, es_medicamento, usa_lotes, es_importado,
                            peso_kg, alto_cm, ancho_cm, largo_cm, unds_bulto, stock_minimo, stock_maximo,
                            costo_fob, costo_flete, costo_seguro, costo_arancel, costo_otros, costo_final_usd, cod_alterno, 
                            descripcion_larga, estrategia_precio_lote, fecha_registro, fecha_modifica
                     FROM inv_productos WHERE cod_producto = %s AND cod_compania = %s"""
            cur.execute(sql, (sku, self.cod_compania))
            row = cur.fetchone()
            
            if row:
                self.txt_sku.setText(sku)
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

                # 2. Cargar Existencias (Ubicaciones y Cantidades en grilla)
                cur.execute("""
                    SELECT cod_almacen, pasillo, estante, peldano, cantidad_real 
                    FROM inv_existencias 
                    WHERE cod_producto = %s AND cod_compania = %s
                """, (sku, self.cod_compania))
                
                existencias = cur.fetchall()
                stock_total_kpi = 0.0
                
                for e in existencias:
                    for i in range(self.grid_stock.rowCount()):
                        if self.grid_stock.item(i, 0).text() == e[0]:
                            # Cargar Ubicación Fìsica
                            self.grid_stock.setItem(i, 2, QTableWidgetItem(e[1] or ""))
                            self.grid_stock.setItem(i, 3, QTableWidgetItem(e[2] or ""))
                            self.grid_stock.setItem(i, 4, QTableWidgetItem(e[3] or ""))
                            
                            # Cargar y sumar Existencia Real
                            real_qty = float(e[4] or 0)
                            stock_total_kpi += real_qty
                            
                            # Simulamos 0 en pedidos y OC temporalmente hasta tener esos módulos
                            pedidos = 0.0
                            oc = 0.0
                            disponible = real_qty - pedidos + oc
                            
                            # Actualizar celdas numéricas
                            cantidades = [real_qty, pedidos, oc, disponible]
                            for col_offset, val in enumerate(cantidades):
                                it_qty = QTableWidgetItem(f"{val:.3f}")
                                it_qty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                                it_qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                                if col_offset == 3: # Disponible
                                    it_qty.setForeground(QColor("#27AE60"))
                                    it_qty.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                                self.grid_stock.setItem(i, 5 + col_offset, it_qty)
                            break
                            
                # Actualizar el gran KPI visual del encabezado
                self.lbl_stock_val.setText(f"{stock_total_kpi:,.2f}")

                # 3. Cargar Precios (Grilla)
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
                self.btn_eliminar.setVisible(False)
        except Exception as e:
            QMessageBox.warning(self, "Error Carga", f"No se pudo cargar: {e}")

    def guardar_producto(self):
        sku = self.txt_sku.text().strip()
        nombre = self.txt_nombre.text().strip()
        
        if not sku or not nombre:
            QMessageBox.warning(self, "Validación", "El SKU y el Nombre son obligatorios.")
            return

        try:
            cur = self.conn.cursor()
            
            # UPSERT PRODUCTO
            sql_prod = """
                INSERT INTO inv_productos (
                    cod_compania, cod_producto, nombre, descripcion_larga, cod_barra, cod_alterno,
                    id_grupo, id_subgrupo, id_categoria, id_marca, id_unidad, tipo_producto, partida_arancelaria,
                    id_impuesto, id_cuenta_contable, tipo_costeo, es_activo, es_servicio, es_fraccionario,
                    es_compuesto, es_medicamento, usa_lotes, es_importado, estrategia_precio_lote,
                    peso_kg, alto_cm, ancho_cm, largo_cm, volumen_m3, unds_bulto, stock_minimo, stock_maximo,
                    costo_fob, costo_flete, costo_seguro, costo_arancel, costo_otros, costo_final_usd, id_usuario_crea
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                    costo_final_usd = EXCLUDED.costo_final_usd, fecha_modifica = CURRENT_TIMESTAMP
            """
            
            vol = float(self.lbl_vol.text().replace(" m³", ""))
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
                self.spin_otros.value(), self.spin_costo_final.value(), self.id_usuario
            )
            cur.execute(sql_prod, params_prod)

            # UPSERT EXISTENCIAS (Solo ubicación, la cantidad no se sobreescribe manual)
            for i in range(self.grid_stock.rowCount()):
                cod_alm = self.grid_stock.item(i, 0).text()
                pasillo = self.grid_stock.item(i, 2).text()
                estante = self.grid_stock.item(i, 3).text()
                peldano = self.grid_stock.item(i, 4).text()
                
                sql_ex = """
                    INSERT INTO inv_existencias (cod_compania, cod_almacen, cod_producto, pasillo, estante, peldano)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cod_compania, cod_almacen, cod_producto) DO UPDATE SET
                    pasillo = EXCLUDED.pasillo, estante = EXCLUDED.estante, peldano = EXCLUDED.peldano
                """
                cur.execute(sql_ex, (self.cod_compania, cod_alm, sku, pasillo, estante, peldano))

            # UPSERT PRECIOS
            for i in range(self.grid_precios.rowCount()):
                id_tar = int(self.grid_precios.item(i, 0).text())
                margen = float(self.grid_precios.item(i, 2).text() or 0)
                neto = float(self.grid_precios.item(i, 3).text() or 0)
                iva = float(self.grid_precios.item(i, 4).text() or 0)
                f_usd = float(self.grid_precios.item(i, 5).text() or 0)
                f_bs = float(self.grid_precios.item(i, 6).text().replace(',', '') or 0)
                
                sql_pr = """
                    INSERT INTO inv_precios (cod_compania, cod_producto, id_tarifa, margen_porcentaje, precio_neto_usd, monto_iva_usd, precio_final_usd, precio_final_bs)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cod_compania, cod_producto, id_tarifa) DO UPDATE SET
                    margen_porcentaje = EXCLUDED.margen_porcentaje, precio_neto_usd = EXCLUDED.precio_neto_usd,
                    monto_iva_usd = EXCLUDED.monto_iva_usd, precio_final_usd = EXCLUDED.precio_final_usd, precio_final_bs = EXCLUDED.precio_final_bs
                """
                cur.execute(sql_pr, (self.cod_compania, sku, id_tar, margen, neto, iva, f_usd, f_bs))

            self.conn.commit()
            QMessageBox.information(self, "Guardado", f"El producto {sku} ha sido procesado correctamente.")
            self.limpiar_ficha()
            self.configurar_autocompletado() # Recargar memoria
            
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error SQL", f"Error al guardar: {e}")

    def eliminar_producto(self):
        sku = self.txt_sku.text()
        if not sku: return
        resp = QMessageBox.question(self, "Confirmar", f"¿Está seguro que desea eliminar el producto {sku}?\nSe eliminarán sus precios y ubicaciones (No se puede si tiene movimientos en Kardex).", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            try:
                cur = self.conn.cursor()
                cur.execute("DELETE FROM inv_existencias WHERE cod_producto=%s AND cod_compania=%s", (sku, self.cod_compania))
                cur.execute("DELETE FROM inv_precios WHERE cod_producto=%s AND cod_compania=%s", (sku, self.cod_compania))
                cur.execute("DELETE FROM inv_productos WHERE cod_producto=%s AND cod_compania=%s", (sku, self.cod_compania))
                self.conn.commit()
                QMessageBox.information(self, "Eliminado", "Producto eliminado correctamente.")
                self.limpiar_ficha()
            except Exception as e:
                self.conn.rollback()
                QMessageBox.warning(self, "Bloqueo", "No se puede eliminar el producto porque tiene movimientos o relaciones activas.")

    def limpiar_ficha(self):
        self.txt_sku.clear(); self.txt_nombre.clear(); self.txt_barra.clear()
        self.txt_cod_alt.clear(); self.txt_arancel.clear(); self.txt_desc_larga.clear()
        
        self.spin_costo_final.setValue(0); self.spin_peso.setValue(0); self.spin_bulto.setValue(1)
        self.spin_alto.setValue(0); self.spin_ancho.setValue(0); self.spin_largo.setValue(0)
        self.spin_stock_min.setValue(0); self.spin_stock_max.setValue(0)
        
        self.chk_activo.setChecked(True); self.cmb_grupo.setCurrentIndex(0)
        self.chk_fraccionario.setChecked(False); self.chk_compuesto.setChecked(False)
        self.chk_lotes.setChecked(False); self.chk_medicamento.setChecked(False)
        self.chk_importado.setChecked(False); self.chk_servicio.setChecked(False)
        
        self.btn_eliminar.setVisible(False)
        self.lbl_auditoria.setText(f"📝 Registrado por: {self.nombre_usuario_actual} | Fecha: {datetime.now().strftime('%d/%m/%Y')}  ---  ✏️ Modificado por: Ninguno")
        self.cargar_estructuras_dinamicas() # Resetea las grillas limpias

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

    def seleccionar_imagen(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Imagen", "", "Img (*.png *.jpg)")
        if archivo: self.lbl_imagen.setPixmap(QPixmap(archivo))

    def calcular_volumen(self):
        v = (self.spin_alto.value() * self.spin_ancho.value() * self.spin_largo.value()) / 1000000
        self.lbl_vol.setText(f"{v:.4f} m³")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ProductosForm(1, 1, "Sin BD")
    win.show()
    sys.exit(app.exec())