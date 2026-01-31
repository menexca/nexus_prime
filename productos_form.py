import sys
import psycopg2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QTextEdit, QTabWidget, QFormLayout, 
    QMessageBox, QDoubleSpinBox, QDateEdit, QFrame, QApplication
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt, QDate
from db_config import DB_PARAMS

class ProductosForm(QWidget):
    def __init__(self, cod_compania, id_usuario, nombre_empresa):
        super().__init__()
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        self.nombre_empresa = nombre_empresa
        self.rol_usuario = "Operador" # Se debe validar contra BD
        
        self.setWindowTitle(f"Gestión de Productos - {self.nombre_empresa}")
        self.resize(1100, 750)
        
        self.id_producto_seleccionado = None
        
        self.verificar_permisos()
        self.apply_styles()
        self.init_ui()
        self.cargar_proveedores() # Cargar lista para el combo

    def verificar_permisos(self):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT rol FROM usuarios_sistema WHERE id_usuario = %s", (self.id_usuario,))
            res = cur.fetchone()
            conn.close()
            if res: self.rol_usuario = res[0]
        except: pass

    def apply_styles(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F0F2F5")) 
        self.setPalette(palette)
        self.setFont(QFont("Segoe UI", 10))

        self.setStyleSheet("""
            QPushButton {
                background-color: #007BFF; color: white; border-radius: 5px;
                padding: 8px 15px; border: none; font-weight: bold;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {
                border: 1px solid #cccccc; border-radius: 4px; padding: 5px; background-color: white;
            }
            QLineEdit:focus, QDoubleSpinBox:focus { border: 1px solid #007BFF; }
            QTabWidget::pane { border: 1px solid #cccccc; background-color: white; }
            QTabBar::tab { background: #E0E6ED; padding: 8px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; }
        """)

    def init_ui(self):
        main = QVBoxLayout()

        # --- HEADER ---
        header = QHBoxLayout()
        header.addWidget(QLabel("🔍 Buscar:"))
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Código o Nombre...")
        self.txt_buscar.returnPressed.connect(self.buscar_producto)
        header.addWidget(self.txt_buscar)
        
        btn_buscar = QPushButton("Buscar")
        btn_buscar.clicked.connect(self.buscar_producto)
        header.addWidget(btn_buscar)
        
        self.btn_limpiar = QPushButton("Nuevo")
        self.btn_limpiar.setStyleSheet("background-color: #28a745; color: white;")
        self.btn_limpiar.clicked.connect(self.limpiar_formulario)
        header.addWidget(self.btn_limpiar)
        main.addLayout(header)

        # --- TABS ---
        self.tabs = QTabWidget()

        # TAB 1: Identificación y Ubicación
        tab1 = QWidget()
        l1 = QHBoxLayout(tab1)
        
        f1 = QFormLayout()
        self.txt_codigo = QLineEdit()
        f1.addRow("Código Producto *:", self.txt_codigo)
        self.txt_nombre = QLineEdit()
        f1.addRow("Nombre *:", self.txt_nombre)
        self.txt_desc = QTextEdit(); self.txt_desc.setMaximumHeight(50)
        f1.addRow("Descripción:", self.txt_desc)
        self.cmb_origen = QComboBox(); self.cmb_origen.addItems(["NACIONAL", "IMPORTADO"])
        f1.addRow("Origen:", self.cmb_origen)
        self.cmb_unidad = QComboBox(); self.cmb_unidad.addItems(["UNIDAD", "KILOS", "BULTO", "CAJA", "LITRO"])
        f1.addRow("Unidad:", self.cmb_unidad)
        
        f2 = QFormLayout()
        f2.addRow(QLabel("<b>Ubicación Física</b>"))
        self.txt_almacen = QLineEdit()
        f2.addRow("Almacén:", self.txt_almacen)
        self.txt_pasillo = QLineEdit()
        f2.addRow("Pasillo:", self.txt_pasillo)
        self.txt_estante = QLineEdit()
        f2.addRow("Estante:", self.txt_estante)
        self.txt_peldano = QLineEdit()
        f2.addRow("Peldaño:", self.txt_peldano)
        self.chk_activo = QCheckBox("Activo"); self.chk_activo.setChecked(True)
        f2.addRow("Estado:", self.chk_activo)

        l1.addLayout(f1); l1.addLayout(f2)
        self.tabs.addTab(tab1, "📦 Datos Generales")

        # TAB 2: Costos y Contabilidad (Cálculos automáticos)
        tab2 = QWidget()
        l2 = QHBoxLayout(tab2)
        
        f3 = QFormLayout()
        f3.addRow(QLabel("<b>Estructura de Costos</b>"))
        
        self.spin_costo = QDoubleSpinBox(); self.spin_costo.setRange(0, 1e9); self.spin_costo.setPrefix("$ ")
        self.spin_costo.valueChanged.connect(self.calcular_montos)
        f3.addRow("Costo Unitario:", self.spin_costo)
        
        self.spin_porc_desc = QDoubleSpinBox(); self.spin_porc_desc.setRange(0, 100); self.spin_porc_desc.setSuffix(" %")
        self.spin_porc_desc.valueChanged.connect(self.calcular_montos)
        f3.addRow("% Descuento:", self.spin_porc_desc)
        
        self.spin_monto_desc = QDoubleSpinBox(); self.spin_monto_desc.setRange(0, 1e9); self.spin_monto_desc.setReadOnly(True)
        self.spin_monto_desc.setStyleSheet("background: #f0f0f0;")
        f3.addRow("Monto Descuento:", self.spin_monto_desc)
        
        self.spin_neto = QDoubleSpinBox(); self.spin_neto.setRange(0, 1e9); self.spin_neto.setReadOnly(True)
        self.spin_neto.setStyleSheet("background: #e6f3ff; font-weight: bold;")
        f3.addRow("Neto (Sin IVA):", self.spin_neto)
        
        self.spin_iva_porc = QDoubleSpinBox(); self.spin_iva_porc.setValue(16.00); self.spin_iva_porc.setSuffix(" %")
        self.spin_iva_porc.valueChanged.connect(self.calcular_montos)
        f3.addRow("% IVA:", self.spin_iva_porc)
        
        self.spin_monto_iva = QDoubleSpinBox(); self.spin_monto_iva.setRange(0, 1e9); self.spin_monto_iva.setReadOnly(True)
        f3.addRow("Monto IVA:", self.spin_monto_iva)
        
        f4 = QFormLayout()
        f4.addRow(QLabel("<b>Datos Contables</b>"))
        self.cmb_proveedor = QComboBox() # Se llena desde BD
        f4.addRow("Proveedor:", self.cmb_proveedor)
        self.txt_cuenta_cxp = QLineEdit()
        f4.addRow("Cta. Por Pagar:", self.txt_cuenta_cxp)
        self.txt_tipo_costo = QLineEdit()
        self.txt_tipo_costo.setPlaceholderText("Ej: Reposición")
        f4.addRow("Tipo Costo:", self.txt_tipo_costo)
        
        l2.addLayout(f3); l2.addLayout(f4)
        self.tabs.addTab(tab2, "💰 Costos y Contable")

        # TAB 3: Inventario y Fechas
        tab3 = QWidget()
        l3 = QHBoxLayout(tab3)
        
        f5 = QFormLayout()
        self.spin_cantidad = QDoubleSpinBox(); self.spin_cantidad.setRange(0, 1e6)
        f5.addRow("Cantidad Actual:", self.spin_cantidad)
        
        self.spin_pendiente = QDoubleSpinBox(); self.spin_pendiente.setRange(0, 1e6)
        f5.addRow("Pendiente (Recibir):", self.spin_pendiente)
        
        self.spin_devuelto = QDoubleSpinBox(); self.spin_devuelto.setRange(0, 1e6)
        f5.addRow("Devuelto (Proveedor):", self.spin_devuelto)
        
        self.txt_doc_dev = QLineEdit()
        f5.addRow("Doc. Devolución:", self.txt_doc_dev)
        
        f6 = QFormLayout()
        self.date_elab = QDateEdit(); self.date_elab.setCalendarPopup(True); self.date_elab.setDate(QDate.currentDate())
        f6.addRow("Fecha Elaboración:", self.date_elab)
        self.date_venc = QDateEdit(); self.date_venc.setCalendarPopup(True); self.date_venc.setDate(QDate.currentDate().addDays(30))
        f6.addRow("Fecha Vencimiento:", self.date_venc)
        self.txt_comentario = QTextEdit()
        f6.addRow("Comentario:", self.txt_comentario)

        l3.addLayout(f5); l3.addLayout(f6)
        self.tabs.addTab(tab3, "📅 Fechas y Stocks")

        main.addWidget(self.tabs)

        # --- FOOTER AUDITORÍA ---
        audit_frame = QFrame()
        audit_frame.setStyleSheet("background: #ddd; border-radius: 4px;")
        al = QHBoxLayout(audit_frame)
        self.lbl_audit_crea = QLabel("Creado: -"); al.addWidget(self.lbl_audit_crea)
        al.addStretch()
        self.lbl_audit_mod = QLabel("Modif: -"); al.addWidget(self.lbl_audit_mod)
        main.addWidget(audit_frame)

        # --- BOTONES ---
        btns = QHBoxLayout()
        self.btn_guardar = QPushButton("GUARDAR PRODUCTO")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.clicked.connect(self.guardar_producto)
        
        self.btn_eliminar = QPushButton("ELIMINAR")
        self.btn_eliminar.setStyleSheet("background-color: #d9534f; color: white;")
        self.btn_eliminar.clicked.connect(self.eliminar_producto)
        
        # Permisos
        if self.rol_usuario != "Administrador":
            self.btn_eliminar.setEnabled(False)
            self.btn_eliminar.setToolTip("Solo Administrador")

        btns.addStretch()
        btns.addWidget(self.btn_eliminar)
        btns.addWidget(self.btn_guardar)
        main.addLayout(btns)

        self.setLayout(main)

    # --- LÓGICA ---

    def calcular_montos(self):
        """Calcula Neto, Monto Descuento e IVA en tiempo real"""
        costo = self.spin_costo.value()
        porc_desc = self.spin_porc_desc.value()
        porc_iva = self.spin_iva_porc.value()
        
        monto_desc = costo * (porc_desc / 100)
        neto = costo - monto_desc
        monto_iva = neto * (porc_iva / 100)
        
        self.spin_monto_desc.setValue(monto_desc)
        self.spin_neto.setValue(neto)
        self.spin_monto_iva.setValue(monto_iva)

    def cargar_proveedores(self):
        self.cmb_proveedor.clear()
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT cod_proveedor, nombre_provider FROM maestro_proveedores WHERE cod_compania=%s", (self.cod_compania,))
            rows = cur.fetchall()
            conn.close()
            self.cmb_proveedor.addItem("Sin Proveedor", None)
            for r in rows:
                self.cmb_proveedor.addItem(f"{r[1]} ({r[0]})", r[0])
        except: pass

    def buscar_producto(self):
        term = self.txt_buscar.text().strip()
        if not term: return
        
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = """
                SELECT p.cod_producto, p.nombre_producto, p.descripcion, p.origen, p.unidad,
                       p.almacen, p.pasillo, p.estante, p.peldano,
                       p.cantidad, p.pendiente, p.devuelto, p.documento_dev, p.fecha_elaboracion, p.fecha_vencimiento,
                       p.costo_unitario, p.porc_descuento, p.iva_porc,
                       p.id_proveedor, p.cuenta_por_pagar, p.tipo_costo, p.estatus, p.comentario,
                       u1.usuario_login, p.fecha_registro, u2.usuario_login, p.fecha_modifica
                FROM maestro_productos p
                LEFT JOIN usuarios_sistema u1 ON p.id_user_crea = u1.id_usuario
                LEFT JOIN usuarios_sistema u2 ON p.id_user_mod = u2.id_usuario
                WHERE p.cod_compania = %s AND (p.cod_producto = %s OR p.nombre_producto ILIKE %s)
            """
            cur.execute(query, (self.cod_compania, term, f"%{term}%"))
            data = cur.fetchone()
            conn.close()
            
            if data:
                self.id_producto_seleccionado = data[0]
                self.txt_codigo.setText(data[0])
                self.txt_codigo.setReadOnly(True)
                self.txt_nombre.setText(data[1])
                self.txt_desc.setText(data[2])
                self.cmb_origen.setCurrentText(data[3])
                self.cmb_unidad.setCurrentText(data[4])
                self.txt_almacen.setText(data[5])
                self.txt_pasillo.setText(data[6])
                self.txt_estante.setText(data[7])
                self.txt_peldano.setText(data[8])
                self.spin_cantidad.setValue(float(data[9] or 0))
                self.spin_pendiente.setValue(float(data[10] or 0))
                self.spin_devuelto.setValue(float(data[11] or 0))
                self.txt_doc_dev.setText(data[12])
                if data[13]: self.date_elab.setDate(data[13])
                if data[14]: self.date_venc.setDate(data[14])
                self.spin_costo.setValue(float(data[15] or 0))
                self.spin_porc_desc.setValue(float(data[16] or 0))
                self.spin_iva_porc.setValue(float(data[17] or 16))
                
                # Proveedor
                idx = self.cmb_proveedor.findData(data[18])
                if idx >= 0: self.cmb_proveedor.setCurrentIndex(idx)
                
                self.txt_cuenta_cxp.setText(data[19])
                self.txt_tipo_costo.setText(data[20])
                self.chk_activo.setChecked(data[21])
                self.txt_comentario.setText(data[22])
                
                # Audit
                self.lbl_audit_crea.setText(f"Crea: {data[23]} ({str(data[24])[:10]})")
                self.lbl_audit_mod.setText(f"Mod: {data[25] or '-'} ({str(data[26])[:10]})")
                
                self.calcular_montos()
            else:
                QMessageBox.information(self, "Info", "Producto no encontrado.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def limpiar_formulario(self):
        self.id_producto_seleccionado = None
        self.txt_codigo.setReadOnly(False)
        self.txt_codigo.clear()
        self.txt_nombre.clear()
        self.txt_desc.clear()
        self.spin_costo.setValue(0)
        self.lbl_audit_crea.setText("Crea: -")
        self.lbl_audit_mod.setText("Mod: -")
        self.txt_buscar.clear()

    def guardar_producto(self):
        cod = self.txt_codigo.text().strip().upper()
        nom = self.txt_nombre.text().strip().upper()
        
        if not cod or not nom:
            QMessageBox.warning(self, "Datos", "Código y Nombre son obligatorios.")
            return

        # Calcular valores derivados antes de guardar
        costo = self.spin_costo.value()
        monto_desc = self.spin_monto_desc.value()
        neto = self.spin_neto.value()
        monto_iva = self.spin_monto_iva.value()
        prov_id = self.cmb_proveedor.currentData()

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            
            if self.id_producto_seleccionado is None:
                # INSERT
                query = """
                    INSERT INTO maestro_productos (
                        cod_compania, cod_producto, nombre_producto, descripcion, origen, unidad,
                        almacen, pasillo, estante, peldano,
                        cantidad, pendiente, devuelto, documento_dev, fecha_elaboracion, fecha_vencimiento,
                        costo_unitario, porc_descuento, monto_descuento, iva_porc, monto_iva, neto,
                        tipo_costo, id_proveedor, cuenta_por_pagar,
                        comentario, estatus, id_user_crea
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
                params = (
                    self.cod_compania, cod, nom, self.txt_desc.toPlainText(), self.cmb_origen.currentText(), self.cmb_unidad.currentText(),
                    self.txt_almacen.text(), self.txt_pasillo.text(), self.txt_estante.text(), self.txt_peldano.text(),
                    self.spin_cantidad.value(), self.spin_pendiente.value(), self.spin_devuelto.value(), self.txt_doc_dev.text(), 
                    self.date_elab.date().toString(Qt.DateFormat.ISODate), self.date_venc.date().toString(Qt.DateFormat.ISODate),
                    costo, self.spin_porc_desc.value(), monto_desc, self.spin_iva_porc.value(), monto_iva, neto,
                    self.txt_tipo_costo.text(), prov_id, self.txt_cuenta_cxp.text(),
                    self.txt_comentario.toPlainText(), self.chk_activo.isChecked(), self.id_usuario
                )
            else:
                # UPDATE
                query = """
                    UPDATE maestro_productos SET
                        nombre_producto=%s, descripcion=%s, origen=%s, unidad=%s,
                        almacen=%s, pasillo=%s, estante=%s, peldano=%s,
                        cantidad=%s, pendiente=%s, devuelto=%s, documento_dev=%s, fecha_elaboracion=%s, fecha_vencimiento=%s,
                        costo_unitario=%s, porc_descuento=%s, monto_descuento=%s, iva_porc=%s, monto_iva=%s, neto=%s,
                        tipo_costo=%s, id_proveedor=%s, cuenta_por_pagar=%s,
                        comentario=%s, estatus=%s, id_user_mod=%s
                    WHERE cod_compania=%s AND cod_producto=%s
                """
                params = (
                    nom, self.txt_desc.toPlainText(), self.cmb_origen.currentText(), self.cmb_unidad.currentText(),
                    self.txt_almacen.text(), self.txt_pasillo.text(), self.txt_estante.text(), self.txt_peldano.text(),
                    self.spin_cantidad.value(), self.spin_pendiente.value(), self.spin_devuelto.value(), self.txt_doc_dev.text(),
                    self.date_elab.date().toString(Qt.DateFormat.ISODate), self.date_venc.date().toString(Qt.DateFormat.ISODate),
                    costo, self.spin_porc_desc.value(), monto_desc, self.spin_iva_porc.value(), monto_iva, neto,
                    self.txt_tipo_costo.text(), prov_id, self.txt_cuenta_cxp.text(),
                    self.txt_comentario.toPlainText(), self.chk_activo.isChecked(), self.id_usuario,
                    self.cod_compania, self.id_producto_seleccionado
                )

            cur.execute(query, params)
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Producto guardado correctamente.")
            self.limpiar_formulario()
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error SQL", f"{e.pgerror}")

    def eliminar_producto(self):
        if self.rol_usuario != "Administrador": return
        if not self.id_producto_seleccionado: return
        
        if QMessageBox.question(self, "Confirmar", "¿Eliminar producto?") == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cur = conn.cursor()
                cur.execute("DELETE FROM maestro_productos WHERE cod_compania=%s AND cod_producto=%s", (self.cod_compania, self.id_producto_seleccionado))
                conn.commit()
                conn.close()
                self.limpiar_formulario()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ProductosForm(1, 1, "EMPRESA TEST")
    win.show()
    sys.exit(app.exec())