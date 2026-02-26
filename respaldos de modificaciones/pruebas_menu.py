import sys
import psycopg2
import subprocess # Para llamar a la calculadora
from datetime import datetime # Para la fecha y hora
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QMessageBox, QGridLayout, QStackedWidget, 
    QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QFont, QPalette, QColor, QCursor
from PyQt6.QtCore import Qt, QTimer, QTime, QDate
from db_config import DB_PARAMS

# --- IMPORTACIÓN DE TUS MÓDULOS ---
from proveedores_form import ProveedorForm
from productos_form import ProductosForm
from empresas_form import EmpresasForm
from usuarios_form import UsuariosForm

class MenuPrincipal(QMainWindow):
    def __init__(self, cod_compania, id_usuario, nombre_empresa, rol_usuario):
        super().__init__()
        
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        self.nombre_empresa = nombre_empresa
        self.rol_usuario = rol_usuario
        
        # Referencias a ventanas (Singleton pattern)
        self.ventana_proveedores = None
        self.ventana_productos = None
        self.ventana_empresas = None
        self.ventana_usuarios = None
        
        self.permisos_activos = []

        self.setWindowTitle(f"NEXUS ERP - {self.nombre_empresa}")
        self.resize(1280, 800)
        
        self.cargar_permisos_usuario() 
        self.init_ui()
        
        # Iniciar el reloj
        self.timer_reloj = QTimer(self)
        self.timer_reloj.timeout.connect(self.actualizar_reloj)
        self.timer_reloj.start(1000) # Actualizar cada segundo
        self.actualizar_reloj()

    def cargar_permisos_usuario(self):
        if self.rol_usuario == "Administrador":
            self.permisos_activos = ["TODO"]
            return

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            query = """
                SELECT m.nombre_modulo 
                FROM sys_permisouser p
                JOIN sys_moduser m ON p.id_modulo = m.id_modulo
                WHERE p.id_usuario = %s AND p.p_ver = TRUE
            """
            cur.execute(query, (self.id_usuario,))
            rows = cur.fetchall()
            conn.close()
            self.permisos_activos = [row[0] for row in rows]
            
        except Exception as e:
            print(f"Error cargando permisos: {e}")
            self.permisos_activos = []

    def tiene_permiso(self, nombre_modulo):
        if "TODO" in self.permisos_activos: return True
        return nombre_modulo in self.permisos_activos

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F0F2F5; }
            
            /* SIDEBAR IZQUIERDO */
            QWidget#Sidebar { background-color: #2C3E50; border-right: 1px solid #1a252f; }
            QLabel#Logo { color: white; font-size: 22px; font-weight: bold; padding: 20px; }
            
            QPushButton.menu_cat_btn {
                background-color: transparent;
                color: #ecf0f1;
                text-align: left;
                padding: 15px;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-left: 5px solid transparent;
            }
            QPushButton.menu_cat_btn:hover { background-color: #34495E; }
            QPushButton.menu_cat_btn:checked { 
                background-color: #34495E; 
                border-left: 5px solid #3498DB;
                color: #3498DB;
            }
            
            QPushButton#btn_salir {
                background-color: #c0392b; color: white; border-radius: 4px; padding: 10px; font-weight: bold;
            }

            /* DASHBOARD DERECHO */
            QPushButton.dashboard_card {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 15px;
                text-align: center;
                color: #333;
                font-size: 14px;
                padding: 20px;
            }
            QPushButton.dashboard_card:hover {
                background-color: #F4F6F7;
                border: 1px solid #3498DB;
                color: #2980B9;
                margin-top: -3px; /* Efecto de elevación */
            }
            
            QLabel.page_title {
                color: #2C3E50; font-size: 24px; font-weight: bold; margin-bottom: 20px;
            }
            
            /* FOOTER */
            QFrame#Footer { background-color: #FFFFFF; border-top: 1px solid #DDD; }
            QLabel#ClockLabel { font-size: 16px; font-weight: bold; color: #555; }
            QLabel#DateLabel { font-size: 14px; color: #777; }
            QPushButton#CalcBtn {
                background-color: #27AE60; 
                color: white; 
                border-radius: 20px; /* La mitad del tamaño (45) para que sea redondo */
                font-size: 40px; /* Tamaño ideal para que se vea grande pero centrado */
                border: 2px solid #2ECC71;
                padding-bottom: 4px; /* Ajuste fino para elevar visualmente el emoji */
            }
            QPushButton#CalcBtn:hover { background-color: #D68910; }
            
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =======================================================
        # 1. SIDEBAR (IZQUIERDA) - CATEGORÍAS
        # =======================================================
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_logo = QLabel("NEXUS ERP", objectName="Logo")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(lbl_logo)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #7f8c8d;")
        sidebar_layout.addWidget(line)

        # -- Botones de Categoría (Checkable para efecto de selección) --
        self.btn_cat_ops = QPushButton("📊  Operaciones y Logística")
        self.btn_cat_ops.setProperty("class", "menu_cat_btn")
        self.btn_cat_ops.setCheckable(True)
        self.btn_cat_ops.setChecked(True) # Por defecto activo
        self.btn_cat_ops.clicked.connect(lambda: self.cambiar_pagina(0))
        sidebar_layout.addWidget(self.btn_cat_ops)
        
        self.btn_cat_adm = QPushButton("⚙️  Administración del Sistema")
        self.btn_cat_adm.setProperty("class", "menu_cat_btn")
        self.btn_cat_adm.setCheckable(True)
        self.btn_cat_adm.clicked.connect(lambda: self.cambiar_pagina(1))
        sidebar_layout.addWidget(self.btn_cat_adm)

        # Grupo exclusivo para los botones (solo uno activo a la vez visualmente)
        self.btn_group = [self.btn_cat_ops, self.btn_cat_adm]

        sidebar_layout.addStretch()

        btn_salir = QPushButton("Cerrar Sesión", objectName="btn_salir")
        btn_salir.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_salir.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_salir)
        sidebar_layout.setContentsMargins(10, 10, 10, 20)

        main_layout.addWidget(sidebar)

        # =======================================================
        # 2. ÁREA CENTRAL (DERECHA) - STACKED WIDGET
        # =======================================================
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.setSpacing(0)
        
        # Barra Superior
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #DDD;")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 10, 20, 10)
        
        lbl_welcome = QLabel(f"Usuario: <b>{self.id_usuario}</b> | Rol: <span style='color:#2980B9'>{self.rol_usuario}</span>")
        lbl_welcome.setStyleSheet("font-size: 14px; color: #555;")
        lbl_empresa = QLabel(f"{self.nombre_empresa.upper()}")
        lbl_empresa.setStyleSheet("color: #2C3E50; font-size: 16px; font-weight: bold;")
        
        top_bar_layout.addWidget(lbl_welcome)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(lbl_empresa)
        content_layout.addWidget(top_bar)
        
        # --- STACKED WIDGET (El contenedor que cambia) ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #F0F2F5;")
        
        # PÁGINA 0: OPERACIONES Y LOGÍSTICA
        page_ops = QWidget()
        layout_ops = QVBoxLayout(page_ops)
        layout_ops.setContentsMargins(40, 40, 40, 40)
        
        lbl_ops_title = QLabel("Operaciones y Logística")
        lbl_ops_title.setProperty("class", "page_title")
        layout_ops.addWidget(lbl_ops_title)
        
        grid_ops = QGridLayout()
        grid_ops.setSpacing(25)
        
        if self.tiene_permiso("Productos / Inventario"):
            btn_prod = self.crear_boton_dashboard("📦", "Inventario", "Productos y Stock", self.abrir_productos)
            grid_ops.addWidget(btn_prod, 0, 0)
            
        if self.tiene_permiso("Proveedores"):
            btn_prov = self.crear_boton_dashboard("🚛", "Proveedores", "Gestión de Compras", self.abrir_proveedores)
            grid_ops.addWidget(btn_prov, 0, 1)
            
        # Espaciadores para mantener el grid a la izquierda
        grid_ops.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), 0, 2)
        grid_ops.setRowStretch(1, 1) # Empujar hacia arriba
        
        layout_ops.addLayout(grid_ops)
        self.stacked_widget.addWidget(page_ops)
        
        # PÁGINA 1: ADMINISTRACIÓN DEL SISTEMA
        page_adm = QWidget()
        layout_adm = QVBoxLayout(page_adm)
        layout_adm.setContentsMargins(40, 40, 40, 40)
        
        lbl_adm_title = QLabel("Administración del Sistema")
        lbl_adm_title.setProperty("class", "page_title")
        layout_adm.addWidget(lbl_adm_title)
        
        grid_adm = QGridLayout()
        grid_adm.setSpacing(25)
        
        col_idx = 0
        if self.tiene_permiso("Empresas"):
            btn_emp = self.crear_boton_dashboard("🏢", "Config. Empresas", "Datos Fiscales", self.abrir_empresas)
            grid_adm.addWidget(btn_emp, 0, col_idx)
            col_idx += 1
            
        if self.tiene_permiso("Usuarios"):
            btn_user = self.crear_boton_dashboard("👥", "Seguridad", "Usuarios y Accesos", self.abrir_usuarios)
            grid_adm.addWidget(btn_user, 0, col_idx)
            col_idx += 1
            
        grid_adm.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), 0, col_idx)
        grid_adm.setRowStretch(1, 1)
        
        layout_adm.addLayout(grid_adm)
        self.stacked_widget.addWidget(page_adm)
        
        content_layout.addWidget(self.stacked_widget)

        # =======================================================
        # 3. FOOTER (ABAJO) - FECHA, RELOJ, CALCULADORA
        # =======================================================
        footer = QFrame()
        footer.setObjectName("Footer")
        footer.setFixedHeight(50)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        
        # Fecha
        self.lbl_fecha = QLabel("Fecha: -")
        self.lbl_fecha.setObjectName("DateLabel")
        
        # Reloj
        self.lbl_reloj = QLabel("00:00:00")
        self.lbl_reloj.setObjectName("ClockLabel")
        
        # Botón Calculadora
        btn_calc = QPushButton("🖩") # Icono más claro (Pocket Calculator)
        btn_calc.setObjectName("CalcBtn")
        btn_calc.setFixedSize(40, 40) # Un poco más grande para facilitar el clic
        btn_calc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_calc.setToolTip("Abrir Calculadora")
        btn_calc.clicked.connect(self.abrir_calculadora)



        #btn_calc = QPushButton("🧮")
        #btn_calc.setObjectName("CalcBtn")
        #btn_calc.setFixedSize(35, 35)
        #btn_calc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        #btn_calc.setToolTip("Abrir Calculadora de Windows")
        #btn_calc.clicked.connect(self.abrir_calculadora)
        
        footer_layout.addWidget(self.lbl_fecha)
        footer_layout.addSpacing(20)
        footer_layout.addWidget(self.lbl_reloj)
        footer_layout.addStretch()
        footer_layout.addWidget(btn_calc)
        
        content_layout.addWidget(footer)
        
        main_layout.addWidget(content_area)

    # --- LÓGICA UI ---
    
    def cambiar_pagina(self, indice):
        """Cambia la página del StackedWidget y actualiza el estilo de los botones laterales"""
        self.stacked_widget.setCurrentIndex(indice)
        
        # Actualizar estado visual de los botones
        for i, btn in enumerate(self.btn_group):
            btn.setChecked(i == indice)

    def crear_boton_dashboard(self, icono, titulo, subtitulo, funcion):
        btn = QPushButton()
        btn.setProperty("class", "dashboard_card")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setFixedSize(200, 160)
        
        texto_html = f"""
            <div style='font-size: 45px; margin-bottom: 15px;'>{icono}</div>
            <div style='font-size: 16px; font-weight: bold;'>{titulo}</div>
            <div style='font-size: 12px; color: #7f8c8d; margin-top: 5px;'>{subtitulo}</div>
        """
        btn.setText(f"{icono}\n\n{titulo}\n{subtitulo}") 
        btn.clicked.connect(funcion)
        return btn

    def actualizar_reloj(self):
        ahora = datetime.now()
       # self.lbl_reloj.setText(ahora.strftime("%H:%M:%S"))  ##24 Horas
        self.lbl_reloj.setText(ahora.strftime("%I:%M:%S %p"))  ##12 horas
        # Fecha en formato: Lunes, 02 de Enero 2026
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        fecha_str = f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} {ahora.year}"
        self.lbl_fecha.setText(fecha_str)

    def abrir_calculadora(self):
        try:
            # Comando universal para calculadora de Windows
            subprocess.Popen('calc.exe')
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la calculadora: {e}")

    # --- ACCIONES DE MÓDULOS ---
    def abrir_proveedores(self):
        if self.ventana_proveedores is None or not self.ventana_proveedores.isVisible():
            self.ventana_proveedores = ProveedorForm(self.cod_compania, self.id_usuario, self.nombre_empresa)
            self.ventana_proveedores.show()
        else: self.ventana_proveedores.activateWindow()

    def abrir_productos(self):
        if self.ventana_productos is None or not self.ventana_productos.isVisible():
            self.ventana_productos = ProductosForm(self.cod_compania, self.id_usuario, self.nombre_empresa)
            self.ventana_productos.show()
        else: self.ventana_productos.activateWindow()

    def abrir_empresas(self):
        if self.ventana_empresas is None or not self.ventana_empresas.isVisible():
            self.ventana_empresas = EmpresasForm(self.id_usuario)
            self.ventana_empresas.show()
        else: self.ventana_empresas.activateWindow()

    def abrir_usuarios(self):
        if self.ventana_usuarios is None or not self.ventana_usuarios.isVisible():
            self.ventana_usuarios = UsuariosForm(self.id_usuario)
            self.ventana_usuarios.show()
        else: self.ventana_usuarios.activateWindow()

####################################### Menu Original de aqui para arriba #######################

        # ... (todo tu código anterior de la clase MenuPrincipal) ...

# --- BLOQUE DE EJECUCIÓN ---
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    # 1. Crear la aplicación
    app = QApplication(sys.argv)

    # 2. Definir datos de prueba (Dummy data) para que la clase no de error
    # Estos datos normalmente vendrían del Login, pero aquí los ponemos manuales para probar.
    cod_compania_test = "001"
    id_usuario_test = "admin_test"
    nombre_empresa_test = "EMPRESA PRUEBA S.A."
    rol_usuario_test = "Administrador" # Ponemos admin para ver todos los botones habilitados

    # 3. Instanciar la ventana principal
    ventana = MenuPrincipal(
        cod_compania=cod_compania_test, 
        id_usuario=id_usuario_test, 
        nombre_empresa=nombre_empresa_test, 
        rol_usuario=rol_usuario_test
    )

    # 4. Mostrar la ventana
    #ventana.show() # O ventana.showMaximized()
    ventana.showMaximized()
    # 5. Ejecutar el loop de la aplicación
    sys.exit(app.exec())