# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, 
    QLineEdit, QPushButton, QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal

class ClickableLabel(QLabel):
    """Etiqueta que funciona como un botón (Ideal para fotos)."""
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class MaestroAuxiliarDialog(QDialog):
    """Ventana reutilizable para gestionar mantenimientos pequeños (Grupos, Marcas, Unidades, etc.)"""
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
        self.btn_nuevo = QPushButton("Limpiar / Nuevo", objectName="btn_limpiar")
        self.btn_guardar = QPushButton("Guardar", objectName="btn_guardar")
        
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
        
        self.tabla_lista = QTableWidget(0, 3)
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
            
            self.tabla_lista.setRowCount(0)
            for row in cur.fetchall():
                idx = self.tabla_lista.rowCount()
                self.tabla_lista.insertRow(idx)
                self.tabla_lista.setItem(idx, 0, QTableWidgetItem(str(row[0])))
                self.tabla_lista.setItem(idx, 1, QTableWidgetItem(row[1]))
                self.tabla_lista.setItem(idx, 2, QTableWidgetItem("SI" if row[2] else "NO"))
                self.tabla_lista.item(idx, 0).setData(Qt.ItemDataRole.UserRole, row[0])
        except Exception as e:
            QMessageBox.critical(self, "Error BD", str(e))

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
                    cols += f", {self.campo_fk}"; vals += ", %s"; params.append(self.parent_id)
                cur.execute(f"INSERT INTO {self.tabla} ({cols}) VALUES ({vals})", tuple(params))
            else:
                cur.execute(f"UPDATE {self.tabla} SET {self.campo_nombre} = %s WHERE {self.pk} = %s", (nombre, self.id_edicion))
            
            self.conn.commit()
            self.limpiar_form()
            self.cargar_datos()
            self.datos_actualizados.emit()
            QMessageBox.information(self, "Éxito", "Registro guardado.")
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error Guardar", str(e))

    def cargar_registro_seleccionado(self, row, col):
        self.id_edicion = self.tabla_lista.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.txt_descripcion.setText(self.tabla_lista.item(row, 1).text())
    
    def limpiar_form(self):
        self.id_edicion = None
        self.txt_codigo.clear()
        self.txt_descripcion.clear()