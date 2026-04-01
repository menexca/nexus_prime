# -*- coding: utf-8 -*-
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QTableWidget, QHeaderView, QGroupBox, 
    QFormLayout, QPushButton, QMessageBox, QTextEdit,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

# 1. Importamos el nuevo manejador de errores
from error_handler import manejar_error

class AlmacenesForm(QWidget):
    def __init__(self, cod_compania, nombre_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.nombre_empresa = nombre_empresa
        
        self.setWindowTitle(f"Gestión de Almacenes - {self.nombre_empresa}")
        self.resize(800, 500)
        self.set_style_local()
        self.init_ui()
        self.cargar_almacenes()

    def set_style_local(self):
        self.setStyleSheet("""
            QWidget { background-color: #F4F6F9; color: #333; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { font-weight: bold; border: 1px solid #BDC3C7; border-radius: 6px; margin-top: 15px; padding-top: 15px; background-color: #FFFFFF; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; top: -5px; padding: 0 5px; color: #2C3E50; }
            QLineEdit, QTextEdit { background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; padding: 5px; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #3498DB; }
            QTableWidget { background-color: #FFFFFF; gridline-color: #EEEEEE; border: 1px solid #DDDDDD; }
            QHeaderView::section { background-color: #34495E; color: white; padding: 6px; font-weight: bold; border: none; }
            QPushButton { font-weight: bold; padding: 8px 15px; border-radius: 4px; }
            QPushButton#btn_guardar { background-color: #27AE60; color: white; }
            QPushButton#btn_guardar:hover { background-color: #2ECC71; }
            QPushButton#btn_limpiar { background-color: #95A5A6; color: white; }
            QPushButton#btn_eliminar { background-color: #E74C3C; color: white; }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- PANEL IZQUIERDO: FORMULARIO ---
        left_panel = QVBoxLayout()
        grp_form = QGroupBox("Datos del Almacén")
        form_layout = QFormLayout()
        
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Ej: MAIN, SUR, BODEGA1")
        self.txt_codigo.setMaxLength(10)
        self.txt_codigo.setStyleSheet("text-transform: uppercase;")
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre descriptivo del almacén")
        
        self.txt_ubicacion = QTextEdit()
        self.txt_ubicacion.setPlaceholderText("Dirección o detalles físicos del almacén...")
        self.txt_ubicacion.setFixedHeight(60)
        
        self.chk_principal = QCheckBox("Es el Almacén Principal")
        self.chk_activo = QCheckBox("Almacén Activo")
        self.chk_activo.setChecked(True)
        
        form_layout.addRow("Código:", self.txt_codigo)
        form_layout.addRow("Nombre:", self.txt_nombre)
        form_layout.addRow("Ubicación:", self.txt_ubicacion)
        form_layout.addRow("", self.chk_principal)
        form_layout.addRow("", self.chk_activo)
        
        grp_form.setLayout(form_layout)
        left_panel.addWidget(grp_form)
        
        # Botones
        btn_layout = QHBoxLayout()
        self.btn_limpiar = QPushButton("Limpiar", objectName="btn_limpiar")
        self.btn_eliminar = QPushButton("Eliminar", objectName="btn_eliminar")
        self.btn_guardar = QPushButton("Guardar", objectName="btn_guardar")
        
        self.btn_limpiar.clicked.connect(self.limpiar_form)
        self.btn_eliminar.clicked.connect(self.eliminar_almacen)
        self.btn_guardar.clicked.connect(self.guardar_almacen)
        
        self.btn_eliminar.setEnabled(False) 
        
        btn_layout.addWidget(self.btn_limpiar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addWidget(self.btn_guardar)
        
        left_panel.addLayout(btn_layout)
        left_panel.addStretch()
        
        # --- PANEL DERECHO: GRILLA ---
        right_panel = QVBoxLayout()
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["Código", "Nombre", "Principal", "Activo"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.cellDoubleClicked.connect(self.cargar_seleccion)
        right_panel.addWidget(self.tabla)
        
        main_layout.addLayout(left_panel, 1) 
        main_layout.addLayout(right_panel, 2) 

        self.modo_edicion = False

    # 2. Decorador aplicado. Retirado el bloque try...except general
    @manejar_error
    def cargar_almacenes(self):
        # Usamos 'with' para la conexión y el cursor
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cod_almacen, nombre_almacen, es_principal, activo, ubicacion_fisica FROM inv_almacenes WHERE cod_compania = %s ORDER BY cod_almacen", (self.cod_compania,))
                rows = cur.fetchall()
        
        # Interfaz gráfica fuera de la conexión
        self.tabla.setRowCount(0)
        for r in rows:
            i = self.tabla.rowCount()
            self.tabla.insertRow(i)
            self.tabla.setItem(i, 0, QTableWidgetItem(r[0]))
            self.tabla.setItem(i, 1, QTableWidgetItem(r[1]))
            self.tabla.setItem(i, 2, QTableWidgetItem("SI" if r[2] else "NO"))
            self.tabla.setItem(i, 3, QTableWidgetItem("SI" if r[3] else "NO"))
            self.tabla.item(i, 0).setData(Qt.ItemDataRole.UserRole, r[4])

    # No necesita decorador porque solo afecta la UI (no toca BD)
    def cargar_seleccion(self, row, col):
        codigo = self.tabla.item(row, 0).text()
        nombre = self.tabla.item(row, 1).text()
        principal = self.tabla.item(row, 2).text() == "SI"
        activo = self.tabla.item(row, 3).text() == "SI"
        ubicacion = self.tabla.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        self.txt_codigo.setText(codigo)
        self.txt_codigo.setReadOnly(True) 
        self.txt_codigo.setStyleSheet("background-color: #E8ECEF;")
        
        self.txt_nombre.setText(nombre)
        self.txt_ubicacion.setText(ubicacion or "")
        self.chk_principal.setChecked(principal)
        self.chk_activo.setChecked(activo)
        
        self.modo_edicion = True
        self.btn_eliminar.setEnabled(True)

    def limpiar_form(self):
        self.txt_codigo.clear()
        self.txt_codigo.setReadOnly(False)
        self.txt_codigo.setStyleSheet("background-color: #FFFFFF; text-transform: uppercase;")
        self.txt_nombre.clear()
        self.txt_ubicacion.clear()
        self.chk_principal.setChecked(False)
        self.chk_activo.setChecked(True)
        self.modo_edicion = False
        self.btn_eliminar.setEnabled(False)

    @manejar_error
    def guardar_almacen(self):
        codigo = self.txt_codigo.text().strip().upper()
        nombre = self.txt_nombre.text().strip()
        ubicacion = self.txt_ubicacion.toPlainText().strip()
        principal = self.chk_principal.isChecked()
        activo = self.chk_activo.isChecked()
        
        if not codigo or not nombre:
            QMessageBox.warning(self, "Validación", "Código y Nombre son obligatorios.")
            return

        try:
            with psycopg2.connect(**DB_PARAMS) as conn:
                with conn.cursor() as cur:
                    if principal:
                        cur.execute("UPDATE inv_almacenes SET es_principal = false WHERE cod_compania = %s", (self.cod_compania,))

                    if self.modo_edicion:
                        sql = """UPDATE inv_almacenes 
                                 SET nombre_almacen=%s, ubicacion_fisica=%s, es_principal=%s, activo=%s
                                 WHERE cod_compania=%s AND cod_almacen=%s"""
                        cur.execute(sql, (nombre, ubicacion, principal, activo, self.cod_compania, codigo))
                    else:
                        sql = """INSERT INTO inv_almacenes (cod_compania, cod_almacen, nombre_almacen, ubicacion_fisica, es_principal, activo)
                                 VALUES (%s, %s, %s, %s, %s, %s)"""
                        cur.execute(sql, (self.cod_compania, codigo, nombre, ubicacion, principal, activo))
        # Mantenemos el aviso amigable para duplicados. Otros errores los atrapa el decorador.
        except psycopg2.IntegrityError:
            QMessageBox.warning(self, "Error", "El código de almacén ya existe.")
            return
            
        QMessageBox.information(self, "Éxito", "Almacén guardado correctamente.")
        self.limpiar_form()
        self.cargar_almacenes()

    @manejar_error
    def eliminar_almacen(self):
        codigo = self.txt_codigo.text().strip()
        resp = QMessageBox.question(self, "Confirmar", f"¿Eliminar el almacén {codigo}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if resp == QMessageBox.StandardButton.Yes:
            try:
                with psycopg2.connect(**DB_PARAMS) as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM inv_almacenes WHERE cod_compania=%s AND cod_almacen=%s", (self.cod_compania, codigo))
            # Mantenemos el aviso amigable de llaves foráneas.
            except psycopg2.IntegrityError:
                QMessageBox.warning(self, "Bloqueo", "No se puede eliminar porque hay productos con existencias en este almacén.")
                return
                
            QMessageBox.information(self, "Eliminado", "Almacén eliminado.")
            self.limpiar_form()
            self.cargar_almacenes()