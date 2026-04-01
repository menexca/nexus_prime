# -*- coding: utf-8 -*-
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QTableWidget, QHeaderView, QGroupBox, 
    QFormLayout, QPushButton, QMessageBox, QDoubleSpinBox,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt
from db_config import DB_PARAMS

class ImpuestosForm(QWidget):
    def __init__(self, cod_compania, nombre_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.nombre_empresa = nombre_empresa
        
        self.setWindowTitle(f"Gestión de Impuestos - {self.nombre_empresa}")
        self.resize(750, 450)
        self.set_style_local()
        self.init_ui()
        self.cargar_datos()

    def set_style_local(self):
        self.setStyleSheet("""
            QWidget { background-color: #F4F6F9; color: #333; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { font-weight: bold; border: 1px solid #BDC3C7; border-radius: 6px; margin-top: 15px; padding-top: 15px; background-color: #FFFFFF; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; top: -5px; padding: 0 5px; color: #2C3E50; }
            QLineEdit, QDoubleSpinBox { background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; padding: 5px; min-height: 22px; }
            QLineEdit:focus, QDoubleSpinBox:focus { border: 1px solid #3498DB; }
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
        
        # --- PANEL IZQUIERDO ---
        left_panel = QVBoxLayout()
        grp_form = QGroupBox("Datos del Impuesto")
        form_layout = QFormLayout()
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: IVA General, Exento...")
        
        self.spin_porcentaje = QDoubleSpinBox()
        self.spin_porcentaje.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_porcentaje.setRange(0, 100)
        self.spin_porcentaje.setSuffix(" %")
        
        self.chk_activo = QCheckBox("Impuesto Activo")
        self.chk_activo.setChecked(True)
        
        form_layout.addRow("Nombre Impuesto:", self.txt_nombre)
        form_layout.addRow("Porcentaje (%):", self.spin_porcentaje)
        form_layout.addRow("", self.chk_activo)
        
        grp_form.setLayout(form_layout)
        left_panel.addWidget(grp_form)
        
        btn_layout = QHBoxLayout()
        self.btn_limpiar = QPushButton("Limpiar", objectName="btn_limpiar")
        self.btn_eliminar = QPushButton("Eliminar", objectName="btn_eliminar")
        self.btn_guardar = QPushButton("Guardar", objectName="btn_guardar")
        
        self.btn_limpiar.clicked.connect(self.limpiar_form)
        self.btn_eliminar.clicked.connect(self.eliminar_registro)
        self.btn_guardar.clicked.connect(self.guardar_registro)
        self.btn_eliminar.setEnabled(False)
        
        btn_layout.addWidget(self.btn_limpiar)
        btn_layout.addWidget(self.btn_eliminar)
        btn_layout.addWidget(self.btn_guardar)
        
        left_panel.addLayout(btn_layout)
        left_panel.addStretch()
        
        # --- PANEL DERECHO ---
        right_panel = QVBoxLayout()
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre Impuesto", "Porcentaje (%)", "Activo"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.cellDoubleClicked.connect(self.cargar_seleccion)
        right_panel.addWidget(self.tabla)
        
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        self.id_edicion = None

    def cargar_datos(self):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT id_impuesto, nombre_impuesto, porcentaje, activo FROM cfg_impuestos WHERE cod_compania = %s ORDER BY id_impuesto", (self.cod_compania,))
            rows = cur.fetchall()
            conn.close()
            
            self.tabla.setRowCount(0)
            for r in rows:
                i = self.tabla.rowCount()
                self.tabla.insertRow(i)
                self.tabla.setItem(i, 0, QTableWidgetItem(str(r[0])))
                self.tabla.setItem(i, 1, QTableWidgetItem(r[1]))
                self.tabla.setItem(i, 2, QTableWidgetItem(str(r[2])))
                self.tabla.setItem(i, 3, QTableWidgetItem("SI" if r[3] else "NO"))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def cargar_seleccion(self, row, col):
        self.id_edicion = int(self.tabla.item(row, 0).text())
        self.txt_nombre.setText(self.tabla.item(row, 1).text())
        self.spin_porcentaje.setValue(float(self.tabla.item(row, 2).text() or 0))
        self.chk_activo.setChecked(self.tabla.item(row, 3).text() == "SI")
        self.btn_eliminar.setEnabled(True)

    def limpiar_form(self):
        self.id_edicion = None
        self.txt_nombre.clear()
        self.spin_porcentaje.setValue(0)
        self.chk_activo.setChecked(True)
        self.btn_eliminar.setEnabled(False)

    def guardar_registro(self):
        nombre = self.txt_nombre.text().strip()
        porcentaje = self.spin_porcentaje.value()
        activo = self.chk_activo.isChecked()
        
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            if self.id_edicion:
                sql = "UPDATE cfg_impuestos SET nombre_impuesto=%s, porcentaje=%s, activo=%s WHERE id_impuesto=%s AND cod_compania=%s"
                cur.execute(sql, (nombre, porcentaje, activo, self.id_edicion, self.cod_compania))
            else:
                sql = "INSERT INTO cfg_impuestos (cod_compania, nombre_impuesto, porcentaje, activo) VALUES (%s, %s, %s, %s)"
                cur.execute(sql, (self.cod_compania, nombre, porcentaje, activo))
            
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Impuesto guardado.")
            self.limpiar_form()
            self.cargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def eliminar_registro(self):
        if not self.id_edicion: return
        resp = QMessageBox.question(self, "Confirmar", "¿Eliminar este impuesto?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("DELETE FROM cfg_impuestos WHERE id_impuesto=%s AND cod_compania=%s", (self.id_edicion, self.cod_compania))
                conn.commit()
                conn.close()
                self.limpiar_form()
                self.cargar_datos()
            except Exception as e:
                QMessageBox.warning(self, "Bloqueo", "No se puede eliminar porque está en uso.")