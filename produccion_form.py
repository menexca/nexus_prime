# -*- coding: utf-8 -*-
# produccion_form.py
import psycopg2
try:
    from db_config import DB_PARAMS
except ImportError:
    DB_PARAMS = {}

import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTabWidget, QTableWidget, QHeaderView, QGroupBox, QFormLayout, 
    QPushButton, QDoubleSpinBox, QTableWidgetItem, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

# Importamos nuestro Modelo y el Buscador
from produccion_model import ProduccionModel
from productos_form import CatalogoProductosDialog

class ProduccionForm(QWidget):
    def __init__(self, conn, cod_compania, id_usuario):
        super().__init__()
        if conn:
            self.conn = conn
        else:
            try:
                self.conn = psycopg2.connect(**DB_PARAMS)
            except Exception as e:
                self.conn = None
                print(f"Error de conexión en Producción: {e}")
                
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        
        # Tasa de cambio por defecto (Idealmente la consultarías de una tabla de configuración)
        self.tasa_cambio_actual = 36.50 
        
        self.modelo = ProduccionModel(self.conn, self.cod_compania)
        
        self.setWindowTitle("Órdenes de Producción - NEXUS PRIME")
        self.resize(1150, 750)
        self.init_ui()
        
        self.txt_nro_orden.setText(self.modelo.generar_numero_orden())

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # =========================================================
        # 1. ENCABEZADO
        # =========================================================
        grp_header = QGroupBox("Datos de la Orden de Producción")
        grp_header.setStyleSheet("QGroupBox { font-weight: bold; }")
        header_layout = QHBoxLayout(grp_header)
        
        form_izq = QFormLayout()
        self.txt_nro_orden = QLineEdit()
        self.txt_nro_orden.setReadOnly(True)
        self.txt_nro_orden.setStyleSheet("background-color: #E8ECEF; font-weight: bold;")
        
        self.txt_sku_padre = QLineEdit()
        self.txt_sku_padre.setPlaceholderText("Presione Enter para buscar producto...")
        self.txt_sku_padre.setStyleSheet("border: 1px solid #E74C3C; font-weight:bold;")
        self.txt_sku_padre.returnPressed.connect(self.procesar_busqueda_producto)
        
        self.txt_nombre_padre = QLineEdit()
        self.txt_nombre_padre.setReadOnly(True)
        
        form_izq.addRow("Nro. Orden:", self.txt_nro_orden)
        form_izq.addRow("Producto a Fabricar:", self.txt_sku_padre)
        form_izq.addRow("Descripción:", self.txt_nombre_padre)
        header_layout.addLayout(form_izq, 2)
        
        form_der = QFormLayout()
        self.spin_cantidad = QDoubleSpinBox()
        self.spin_cantidad.setRange(0.01, 999999.00)
        self.spin_cantidad.setDecimals(2)
        self.spin_cantidad.setValue(1.00)
        self.spin_cantidad.setStyleSheet("font-size: 18px; font-weight: bold; color: #2980B9;")
        # --- REACTIVIDAD: Al cambiar la cantidad, recalculamos la grilla ---
        self.spin_cantidad.valueChanged.connect(self.recalcular_grilla_completa)
        
        self.spin_tasa = QDoubleSpinBox()
        self.spin_tasa.setRange(0.01, 9999.99)
        self.spin_tasa.setDecimals(2)
        self.spin_tasa.setValue(self.tasa_cambio_actual)
        self.spin_tasa.setSuffix(" Bs/$")
        self.spin_tasa.valueChanged.connect(self.actualizar_totales_footer) # Reactivo a la tasa
        
        self.btn_restaurar_receta = QPushButton("🔄 Restaurar Receta Orig.")
        self.btn_restaurar_receta.setToolTip("Restaura la receta a sus valores originales por si borró algo.")
        self.btn_restaurar_receta.clicked.connect(self.cargar_receta_a_grilla)
        
        form_der.addRow("Cantidad a Producir:", self.spin_cantidad)
        form_der.addRow("Tasa de Cambio:", self.spin_tasa)
        form_der.addRow("", self.btn_restaurar_receta)
        header_layout.addLayout(form_der, 1)
        
        main_layout.addWidget(grp_header)

        # =========================================================
        # 2. PESTAÑAS DE PRODUCCIÓN
        # =========================================================
        self.tabs = QTabWidget()
        self.tab_mp = QWidget(); self.setup_tab_materia_prima(); self.tabs.addTab(self.tab_mp, "🧪 1. Materia Prima a Consumir")
        self.tab_costos = QWidget(); self.setup_tab_costos_operativos(); self.tabs.addTab(self.tab_costos, "🏭 2. Costos Operativos (MOD / CIF)")
        main_layout.addWidget(self.tabs)

        # =========================================================
        # 3. FOOTER
        # =========================================================
        footer_layout = QHBoxLayout()
        self.lbl_totales = QLabel("TOTAL MATERIA PRIMA: $0.00 | 0.00 Bs")
        self.lbl_totales.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        
        self.btn_procesar = QPushButton("✅ PROCESAR PRODUCCIÓN")
        self.btn_procesar.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        
        footer_layout.addWidget(self.lbl_totales)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_procesar)
        main_layout.addLayout(footer_layout)

    def setup_tab_materia_prima(self):
        layout = QVBoxLayout(self.tab_mp)
        
        info = QLabel("Modifique la <b>Cantidad Real</b> si hubo desviaciones. Si cambia la cantidad a producir arriba, los totales se recalcularán solos.")
        layout.addWidget(info)
        
        self.grid_mp = QTableWidget(0, 9) # Aumentamos columnas
        self.grid_mp.setHorizontalHeaderLabels([
            "Código", "Insumo", "Und", 
            "Cant Base (x1)", "Total Teórico", "Cant REAL", 
            "Costo U ($)", "Subtotal ($)", "Subtotal (Bs)", "Acción"
        ])
        h = self.grid_mp.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Ajustamos algunas columnas para que se vea ordenado
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Conectamos la edición manual de la grilla
        self.grid_mp.cellChanged.connect(self.on_grid_cell_changed)
        layout.addWidget(self.grid_mp)

    def setup_tab_costos_operativos(self):
        layout = QVBoxLayout(self.tab_costos)
        layout.addWidget(QLabel("Área en construcción para carga de Mano de Obra y Carga Fabril..."))

    # =========================================================
    # LÓGICA Y REACTIVIDAD
    # =========================================================
    def procesar_busqueda_producto(self):
        if not self.conn: return
        dlg = CatalogoProductosDialog(self.conn, self.cod_compania)
        dlg.producto_seleccionado.connect(self.setear_producto_padre)
        dlg.exec()

    def setear_producto_padre(self, sku):
        self.txt_sku_padre.setText(sku)
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT nombre FROM inv_productos WHERE cod_producto = %s AND cod_compania = %s", (sku, self.cod_compania))
            row = cur.fetchone()
            if row:
                self.txt_nombre_padre.setText(row[0])
                # Carga Automática al seleccionar el producto
                self.cargar_receta_a_grilla()
                self.spin_cantidad.setFocus()
        except Exception as e:
            print(f"Error cargando nombre del producto: {e}")

    def cargar_receta_a_grilla(self):
        sku = self.txt_sku_padre.text().strip()
        if not sku: return
            
        exito, mensaje, filas_receta = self.modelo.obtener_receta_teorica(sku)
        
        if not exito:
            self.grid_mp.setRowCount(0)
            self.actualizar_totales_footer()
            QMessageBox.critical(self, "Error", mensaje)
            return
            
        # Bloqueamos la señal cellChanged mientras armamos la grilla para evitar falsos cálculos
        self.grid_mp.blockSignals(True)
        self.grid_mp.setRowCount(0)
        
        for idx, rec in enumerate(filas_receta):
            self.grid_mp.insertRow(idx)
            
            # Datos fijos (Solo lectura)
            it_cod = QTableWidgetItem(str(rec[0])); it_cod.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it_nom = QTableWidgetItem(str(rec[1])); it_nom.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it_und = QTableWidgetItem(str(rec[2] or "")); it_und.setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # Cantidad Base Unitaria (Lo que manda la receta original)
            cant_base = float(rec[3])
            it_base = QTableWidgetItem(f"{cant_base:.4f}"); it_base.setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # Dejamos las columnas de Totales y Subtotales vacías momentáneamente
            it_teo = QTableWidgetItem("0.0000"); it_teo.setFlags(Qt.ItemFlag.ItemIsEnabled); it_teo.setBackground(QColor("#F8F9F9"))
            it_real = QTableWidgetItem("0.0000"); it_real.setBackground(QColor("#E8F8F5")); it_real.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            
            costo_u = float(rec[4] or 0)
            it_costou = QTableWidgetItem(f"{costo_u:.4f}"); it_costou.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it_subusd = QTableWidgetItem("0.00"); it_subusd.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it_subbs = QTableWidgetItem("0.00"); it_subbs.setFlags(Qt.ItemFlag.ItemIsEnabled)

            self.grid_mp.setItem(idx, 0, it_cod); self.grid_mp.setItem(idx, 1, it_nom)
            self.grid_mp.setItem(idx, 2, it_und); self.grid_mp.setItem(idx, 3, it_base)
            self.grid_mp.setItem(idx, 4, it_teo); self.grid_mp.setItem(idx, 5, it_real)
            self.grid_mp.setItem(idx, 6, it_costou); self.grid_mp.setItem(idx, 7, it_subusd)
            self.grid_mp.setItem(idx, 8, it_subbs)
            
            # Botón Eliminar
            btn_del = QPushButton("❌")
            btn_del.setStyleSheet("color: #E74C3C; font-weight: bold; border: none; background: transparent;")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(self.eliminar_fila_receta)
            self.grid_mp.setCellWidget(idx, 9, btn_del)

        self.grid_mp.blockSignals(False)
        
        # Invocamos la reactividad por primera vez para llenar los cálculos
        self.recalcular_grilla_completa()

    def recalcular_grilla_completa(self):
        """Multiplica la Cantidad Base x Cantidad a Producir en toda la grilla."""
        multiplicador = self.spin_cantidad.value()
        
        self.grid_mp.blockSignals(True)
        for row in range(self.grid_mp.rowCount()):
            # Leemos la cantidad base (Columna 3)
            item_base = self.grid_mp.item(row, 3)
            if not item_base: continue
            
            cant_base = float(item_base.text())
            nuevo_total = cant_base * multiplicador
            
            # Actualizamos Teórico y Real (Sobrescribe si el usuario había puesto algo a mano)
            self.grid_mp.item(row, 4).setText(f"{nuevo_total:.4f}")
            self.grid_mp.item(row, 5).setText(f"{nuevo_total:.4f}")
            
            # Recalculamos los subtotales de esta fila
            self.calcular_subtotales_fila(row)
            
        self.grid_mp.blockSignals(False)
        self.actualizar_totales_footer()

    def on_grid_cell_changed(self, row, col):
        """Se dispara si el usuario escribe a mano en la Cantidad REAL."""
        if col == 5: # 5 es el índice de 'Cant REAL'
            self.grid_mp.blockSignals(True)
            self.calcular_subtotales_fila(row)
            self.grid_mp.blockSignals(False)
            self.actualizar_totales_footer()

    def calcular_subtotales_fila(self, row):
        try:
            cant_real = float(self.grid_mp.item(row, 5).text())
            costo_unit = float(self.grid_mp.item(row, 6).text())
            tasa = self.spin_tasa.value()
            
            sub_usd = cant_real * costo_unit
            sub_bs = sub_usd * tasa
            
            self.grid_mp.item(row, 7).setText(f"{sub_usd:.2f}")
            self.grid_mp.item(row, 8).setText(f"{sub_bs:.2f}")
        except ValueError:
            pass

    def actualizar_totales_footer(self):
        """Suma toda la columna de Subtotal USD y muestra el Bimoneda."""
        total_usd = 0.0
        for row in range(self.grid_mp.rowCount()):
            try:
                total_usd += float(self.grid_mp.item(row, 7).text())
            except ValueError:
                pass
                
        total_bs = total_usd * self.spin_tasa.value()
        self.lbl_totales.setText(f"TOTAL MATERIA PRIMA: ${total_usd:,.2f} | {total_bs:,.2f} Bs")

    def eliminar_fila_receta(self):
        boton = self.sender()
        if boton:
            index = self.grid_mp.indexAt(boton.pos())
            if index.isValid():
                self.grid_mp.removeRow(index.row())
                self.actualizar_totales_footer() # Actualizamos el dinero tras borrar

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ProduccionForm(None, 1, 1)
    win.show()
    sys.exit(app.exec())