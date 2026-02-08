import sys
import psycopg2
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QMessageBox, QStatusBar
)
from PyQt6.QtGui import QFont, QPalette, QColor, QAction
from PyQt6.QtCore import Qt
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
        
        # Referencias a ventanas
        self.ventana_proveedores = None
        self.ventana_productos = None
        self.ventana_empresas = None
        self.ventana_usuarios = None
        
        # Cache de permisos (se llena al iniciar)
        self.permisos_activos = []

        self.setWindowTitle(f"NEXUS ERP - {self.nombre_empresa}")
        self.resize(1280, 800)
        #self.showMaximized()
        
        self.cargar_permisos_usuario() # <--- NUEVO: Cargar ACL
        self.init_ui()

    def cargar_permisos_usuario(self):
        """Consulta qué módulos tiene permitido VER este usuario"""
        # Si es Administrador, tiene acceso a todo automáticamente
        if self.rol_usuario == "Administrador":
            self.permisos_activos = ["TODO"]
            return

        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            # Unimos la tabla de permisos con la de nombres de módulos
            query = """
                SELECT m.nombre_modulo 
                FROM sys_permisouser p
                JOIN sys_moduser m ON p.id_modulo = m.id_modulo
                WHERE p.id_usuario = %s AND p.p_ver = TRUE
            """
            cur.execute(query, (self.id_usuario,))
            rows = cur.fetchall()
            conn.close()
            
            # Guardamos los nombres de los módulos permitidos en una lista
            self.permisos_activos = [row[0] for row in rows]
            print(f"Permisos cargados: {self.permisos_activos}")
            
        except Exception as e:
            print(f"Error cargando permisos: {e}")
            self.permisos_activos = []

    def tiene_permiso(self, nombre_modulo):
        """Helper para verificar si activamos el botón"""
        if "TODO" in self.permisos_activos: return True
        return nombre_modulo in self.permisos_activos

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F0F2F5; }
            QWidget#Sidebar { background-color: #2C3E50; border-right: 1px solid #1a252f; }
            QLabel#Logo { color: white; font-size: 22px; font-weight: bold; padding: 20px; }
            QLabel#InfoSession { color: #555; font-size: 14px; font-weight: bold; }
            
            QPushButton.menu_btn {
                background-color: transparent;
                color: #ecf0f1;
                text-align: left;
                padding: 15px;
                font-size: 14px;
                border: none;
                border-left: 5px solid transparent;
            }
            QPushButton.menu_btn:hover {
                background-color: #34495E;
                border-left: 5px solid #3498DB;
            }
            QPushButton.menu_btn:pressed { background-color: #2980B9; }
            QPushButton.menu_btn:disabled { color: #7f8c8d; background-color: transparent; }
            
            QPushButton#btn_salir {
                background-color: #c0392b; color: white; border-radius: 4px; padding: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_logo = QLabel("NEXUS ERP", objectName="Logo")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(lbl_logo)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #7f8c8d;")
        sidebar_layout.addWidget(line)

        # --- BOTONES DINÁMICOS ---
        
        # 1. Productos
        self.btn_productos = QPushButton("📦  Inventario / Productos")
        self.btn_productos.setProperty("class", "menu_btn")
        self.btn_productos.clicked.connect(self.abrir_productos)
        # Aplicar Permiso: Nombre exacto como en la BD
        self.btn_productos.setEnabled(self.tiene_permiso("Productos / Inventario"))
        sidebar_layout.addWidget(self.btn_productos)
        
        # 2. Proveedores
        self.btn_proveedores = QPushButton("🚛  Proveedores")
        self.btn_proveedores.setProperty("class", "menu_btn")
        self.btn_proveedores.clicked.connect(self.abrir_proveedores)
        self.btn_proveedores.setEnabled(self.tiene_permiso("Proveedores"))
        sidebar_layout.addWidget(self.btn_proveedores)
        
        sidebar_layout.addSpacing(20)
        lbl_admin = QLabel("  ADMINISTRACIÓN")
        lbl_admin.setStyleSheet("color: #95a5a6; font-size: 12px; font-weight: bold;")
        sidebar_layout.addWidget(lbl_admin)

        # 3. Empresas
        self.btn_empresas = QPushButton("🏢  Config. Empresas")
        self.btn_empresas.setProperty("class", "menu_btn")
        self.btn_empresas.clicked.connect(self.abrir_empresas)
        self.btn_empresas.setEnabled(self.tiene_permiso("Empresas"))
        sidebar_layout.addWidget(self.btn_empresas)

        # 4. Usuarios
        self.btn_usuarios = QPushButton("👥  Seguridad / Usuarios")
        self.btn_usuarios.setProperty("class", "menu_btn")
        self.btn_usuarios.clicked.connect(self.abrir_usuarios)
        self.btn_usuarios.setEnabled(self.tiene_permiso("Usuarios"))
        sidebar_layout.addWidget(self.btn_usuarios)

        sidebar_layout.addStretch()

        btn_salir = QPushButton("Cerrar Sesión", objectName="btn_salir")
        btn_salir.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_salir)
        sidebar_layout.setContentsMargins(10, 10, 10, 20)

        main_layout.addWidget(sidebar)

        # --- ÁREA CENTRAL ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        
        top_bar = QHBoxLayout()
        lbl_welcome = QLabel(f"Usuario: {self.id_usuario} | Rol: {self.rol_usuario}")
        lbl_welcome.setObjectName("InfoSession")
        lbl_empresa = QLabel(f"{self.nombre_empresa.upper()}")
        lbl_empresa.setStyleSheet("color: #2980B9; font-size: 16px; font-weight: bold;")
        
        top_bar.addWidget(lbl_welcome)
        top_bar.addStretch()
        top_bar.addWidget(lbl_empresa)
        
        content_layout.addLayout(top_bar)
        
        workspace = QFrame()
        workspace.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        workspace_layout = QVBoxLayout(workspace)
        
        msg = QLabel("Seleccione una opción del menú.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: #ccc; font-size: 20px;")
        workspace_layout.addWidget(msg)
        
        content_layout.addWidget(workspace)
        main_layout.addWidget(content_area)

    # --- ACCIONES ---
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