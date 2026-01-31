import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QMessageBox, QStatusBar
)
from PyQt6.QtGui import QFont, QPalette, QColor, QAction
from PyQt6.QtCore import Qt

# --- IMPORTACIÓN DE TUS MÓDULOS ---
# Asegúrate de que todos los archivos _form.py estén en la misma carpeta
from proveedores_form import ProveedorForm
from productos_form import ProductosForm
from empresas_form import EmpresasForm
from usuarios_form import UsuariosForm

class MenuPrincipal(QMainWindow):
    def __init__(self, cod_compania, id_usuario, nombre_empresa, rol_usuario):
        super().__init__()
        
        # Datos de Sesión
        self.cod_compania = cod_compania
        self.id_usuario = id_usuario
        self.nombre_empresa = nombre_empresa
        self.rol_usuario = rol_usuario
        
        # Referencias a ventanas abiertas (para evitar Garbage Collection)
        self.ventana_proveedores = None
        self.ventana_productos = None
        self.ventana_empresas = None
        self.ventana_usuarios = None

        self.setWindowTitle(f"NEXUS ERP - {self.nombre_empresa}")
        self.resize(1280, 800)
        
        self.init_ui()

    def init_ui(self):
        # --- ESTILOS GENERALES ---
        self.setStyleSheet("""
            QMainWindow { background-color: #F0F2F5; }
            QWidget#Sidebar { background-color: #2C3E50; border-right: 1px solid #1a252f; }
            QLabel#Logo { color: white; font-size: 22px; font-weight: bold; padding: 20px; }
            QLabel#InfoSession { color: #555; font-size: 14px; font-weight: bold; }
            
            /* Botones del Menú */
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
            QPushButton.menu_btn:pressed {
                background-color: #2980B9;
            }
            
            /* Botón Salir */
            QPushButton#btn_salir {
                background-color: #c0392b; color: white; border-radius: 4px; padding: 10px;
            }
        """)

        # Widget Central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. SIDEBAR (Izquierda) ---
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Logo / Título
        lbl_logo = QLabel("NEXUS ERP", objectName="Logo")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(lbl_logo)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #7f8c8d;")
        sidebar_layout.addWidget(line)

        # --- BOTONES DE MÓDULOS ---
        
        # Grupo Operativo
        self.btn_productos = QPushButton("📦  Inventario / Productos")
        self.btn_productos.setProperty("class", "menu_btn") # Para CSS
        self.btn_productos.clicked.connect(self.abrir_productos)
        sidebar_layout.addWidget(self.btn_productos)
        
        self.btn_proveedores = QPushButton("🚛  Proveedores")
        self.btn_proveedores.setProperty("class", "menu_btn")
        self.btn_proveedores.clicked.connect(self.abrir_proveedores)
        sidebar_layout.addWidget(self.btn_proveedores)
        
        # Grupo Administrativo
        sidebar_layout.addSpacing(20)
        lbl_admin = QLabel("  ADMINISTRACIÓN")
        lbl_admin.setStyleSheet("color: #95a5a6; font-size: 12px; font-weight: bold;")
        sidebar_layout.addWidget(lbl_admin)

        self.btn_empresas = QPushButton("🏢  Config. Empresas")
        self.btn_empresas.setProperty("class", "menu_btn")
        self.btn_empresas.clicked.connect(self.abrir_empresas)
        sidebar_layout.addWidget(self.btn_empresas)

        self.btn_usuarios = QPushButton("👥  Seguridad / Usuarios")
        self.btn_usuarios.setProperty("class", "menu_btn")
        self.btn_usuarios.clicked.connect(self.abrir_usuarios)
        sidebar_layout.addWidget(self.btn_usuarios)

        sidebar_layout.addStretch() # Empujar todo hacia arriba

        # Botón Salir
        btn_salir = QPushButton("Cerrar Sesión", objectName="btn_salir")
        btn_salir.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_salir)
        sidebar_layout.setContentsMargins(10, 10, 10, 20)

        main_layout.addWidget(sidebar)

        # --- 2. ÁREA CENTRAL (Derecha) ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        
        # Barra Superior (Info)
        top_bar = QHBoxLayout()
        lbl_welcome = QLabel(f"Bienvenido, Usuario ID: {self.id_usuario} ({self.rol_usuario})")
        lbl_welcome.setObjectName("InfoSession")
        lbl_empresa = QLabel(f"Empresa Activa: {self.nombre_empresa.upper()}")
        lbl_empresa.setStyleSheet("color: #2980B9; font-size: 16px; font-weight: bold;")
        
        top_bar.addWidget(lbl_welcome)
        top_bar.addStretch()
        top_bar.addWidget(lbl_empresa)
        
        content_layout.addLayout(top_bar)
        
        # Espacio de trabajo (Placeholder o MDI)
        # Aquí podrías poner un Dashboard con gráficos en el futuro
        workspace = QFrame()
        workspace.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        workspace_layout = QVBoxLayout(workspace)
        
        lbl_instruccion = QLabel("Seleccione un módulo del menú lateral para comenzar.")
        lbl_instruccion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_instruccion.setStyleSheet("color: #ccc; font-size: 20px;")
        
        workspace_layout.addWidget(lbl_instruccion)
        content_layout.addWidget(workspace)
        
        main_layout.addWidget(content_area)

        # --- SEGURIDAD (Deshabilitar botones si no es Admin) ---
        if self.rol_usuario != "Administrador":
            self.btn_empresas.setEnabled(False)
            self.btn_usuarios.setEnabled(False)
            self.btn_empresas.setToolTip("Requiere permiso de Administrador")
            self.btn_usuarios.setToolTip("Requiere permiso de Administrador")
            # Estilo visual para deshabilitados
            self.btn_empresas.setStyleSheet("color: #555;")
            self.btn_usuarios.setStyleSheet("color: #555;")

    # --- FUNCIONES DE APERTURA DE MÓDULOS ---
    
    def abrir_proveedores(self):
        # Verificamos si ya está abierta para no abrirla 2 veces
        if self.ventana_proveedores is None or not self.ventana_proveedores.isVisible():
            self.ventana_proveedores = ProveedorForm(self.cod_compania, self.id_usuario, self.nombre_empresa)
            self.ventana_proveedores.show()
        else:
            self.ventana_proveedores.activateWindow() # Traer al frente

    def abrir_productos(self):
        if self.ventana_productos is None or not self.ventana_productos.isVisible():
            self.ventana_productos = ProductosForm(self.cod_compania, self.id_usuario, self.nombre_empresa)
            self.ventana_productos.show()
        else:
            self.ventana_productos.activateWindow()

    def abrir_empresas(self):
        if self.ventana_empresas is None or not self.ventana_empresas.isVisible():
            # EmpresasForm solo pide el ID del usuario
            self.ventana_empresas = EmpresasForm(self.id_usuario)
            self.ventana_empresas.show()
        else:
            self.ventana_empresas.activateWindow()

    def abrir_usuarios(self):
        if self.ventana_usuarios is None or not self.ventana_usuarios.isVisible():
            # UsuariosForm solo pide el ID del usuario
            self.ventana_usuarios = UsuariosForm(self.id_usuario)
            self.ventana_usuarios.show()
        else:
            self.ventana_usuarios.activateWindow()