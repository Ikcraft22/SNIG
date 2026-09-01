# Documentación completa del sistema

Fecha de actualización: 11 de agosto de 2026
Versión: 1.0.3
Estado: funcional

## 1. Introducción

Este proyecto implementa un sistema de inventario y punto de venta para comercios minoristas. Está diseñado para funcionar localmente con SQLite por defecto y ofrece una interfaz gráfica moderna y táctil basada en PyQt5, además de una capa web con Flask.

## 2. Objetivos del sistema

El sistema permite:

- gestionar productos y presentaciones
- controlar stock por entradas, salidas y ajustes
- registrar ventas y calcular totales automáticamente
- consultar productos por GTIN
- visualizar reportes de inventario y ventas
- usar varias interfaces: GUI, terminal y web
- trabajar con una experiencia optimizada para pantallas táctiles

## 3. Arquitectura general

El proyecto está organizado por módulos:

- config/: configuración global del sistema
- database/: modelos SQLAlchemy y conexión a la base de datos
- core/: lógica de negocio de inventario y POS
- api/: integra servicios de validación y búsqueda de GTIN
- ui/: interfaz gráfica y terminal
- web/: aplicación Flask con rutas y endpoints
- data/: datos locales y archivos auxiliares
- tests/: pruebas del proyecto

## 4. Componentes principales

### 4.1 Base de datos

Se usa SQLAlchemy y por defecto SQLite. La base se guarda como:

- inventario.db

Modelos clave:

- Producto
- Presentacion
- MovimientoInventario
- Venta
- VentaItem
- Usuario

### 4.2 Interfaz gráfica

La GUI maneja tres pestañas principales:

- Inventario
- POS
- Reportes

Además, existe una pestaña auxiliar de Logs que puede mostrarse desde acciones internas o desde reportes.

### 4.3 Interfaz web

La web se ejecuta con Flask y ofrece acceso HTTP a distintos endpoints del sistema.

### 4.4 APIs y servicios externos

El proyecto puede consultar proveedores y servicios de GTIN, siempre que la configuración correspondiente esté habilitada.

## 5. Configuración

### 5.1 SQLite (recomendado)

```env
DB_ENGINE=sqlite
SQLITE_FILE=./inventario.db
```

### 5.2 MySQL (opcional)

```env
DB_ENGINE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=inventario_general
```

## 6. Ejecución

### Desde la terminal

```bash
python main.py
```

La aplicación inicia la interfaz gráfica principal de forma directa.

### Desde la web

1. ejecutar la app
2. abrir la interfaz web desde Flask
3. revisar la ruta configurada en la salida del programa

## 7. Funcionalidades actuales

### Inventario

- crear productos
- asignar presentaciones
- registrar entradas y salidas
- revisar stock actual
- ver movimientos y estado del catálogo
- búsqueda rápida y panel de acciones amplio

### POS

- ingreso de GTIN o escaneo directo
- agregado inmediato al carrito
- cálculo automático del total
- flujo de cobro simplificado
- selección del método de pago por número
- eliminación y vaciado del carrito con botones grandes

### Reportes

- reporte de inventario
- reporte de ventas
- acceso a logs del sistema
- visualización orientada a decisiones rápidas

## 8. Mejoras recientes de la UI

La interfaz actual incorpora diversos refinamientos funcionales y visuales:

- tamaño uniforme de pestañas y mejor distribución horizontal
- tabla de inventario reactiva al ancho de la ventana
- botones de acción más grandes para pantallas táctiles
- diseño de inventario con barra de búsqueda y panel de acciones
- eliminación del campo de cajero al completar el cobro
- método de pago simplificado con opciones numeradas:
  - 1 = Efectivo
  - 2 = Tarjeta
  - 3 = Transferencia
- activación automática del foco en el campo GTIN del POS
- detección de modo oscuro del sistema para la parte superior de la UI

## 9. Observaciones técnicas

- la aplicación crea las tablas automáticamente al inicializar la base
- la lógica de negocio se centraliza en los módulos de core
- la capa visual está en ui/gui_ui.py
- la entrada principal del sistema sigue siendo main.py
- la GUI se abre maximizada y se adapta a pantallas grandes

## 10. Archivos clave

- main.py: ingreso principal del sistema
- config/settings.py: configuración global
- database/models.py: modelos relacionales
- database/connection.py: conexión y sesión de base de datos
- core/inventory_manager.py: lógica de inventario
- core/pos_manager.py: lógica del punto de venta
- ui/gui_ui.py: interfaz gráfica principal
- web/app.py: aplicación web y endpoints

## 11. Recomendaciones de uso

- usar SQLite durante desarrollo y pruebas locales
- mantener .env fuera del control de versiones
- instalar PyQt5 si se va a usar la GUI
- revisar logs si ocurre un error en la ejecución
- mantener la ventana maximizada para una mejor experiencia en tienda

## 12. Solución de problemas

### PyQt5 no está instalado

```bash
pip install PyQt5
```

### Flask no está instalado

```bash
pip install flask
```

### Error al conectarse a MySQL

- verifica que el servicio esté activo
- revisa credenciales en .env
- comprueba que la base de datos exista
- si usas SQLite, no necesitas MySQL

## 13. Roadmap sugerido

- autenticación de usuarios
- exportación a PDF/Excel
- reportes más detallados
- validación de negocio y alertas avanzadas
- pruebas automáticas
- mejora de sincronización y escalabilidad

---

Última actualización: 11 de agosto de 2026
Versión actual: 1.0.3
# APIs (Opcional)
GOOGLE_API_KEY=                    # Obtén desde Google Cloud Console
GOOGLE_SEARCH_ENGINE_ID=           # Obtén de Custom Search Engine

# Aplicación
DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_ENV=development

# Configuración
MONEDA=$
IDIOMA=es
```

### 8. Inicializar Base de Datos

```bash
python init_db.py
```

Este script:
- Valida el entorno
- Verifica dependencias
- Crea todas las tablas
- Crea usuario administrador
- Opcionalmente carga datos de prueba

### 9. ¡Ejecutar la Aplicación!

```bash
python main.py
```

Selecciona tu interfaz preferida:
```
1. 💻 Terminal (CLI)
2. 🖥️  Interfaz Gráfica (GUI)
3. 🌐 Web (Flask)
4. ⚙️  Configuración
5. 🚪 Salir
```

---

## Guía de Uso

### Interfaz Terminal (Opción 1)

#### Menú Principal
```
1. 📦 Gestión de Inventario
2. 🛒 Punto de Venta (POS)
3. 📊 Reportes
4. ⚙️  Configuración
5. 🚪 Salir
```

#### Gestión de Inventario
**Registrar nuevo producto:**
1. Selecciona opción 1 → 1
2. Escanea o ingresa GTIN
3. Completa información del producto
4. Agrega presentaciones (tableta, ampolla, etc.)
5. Establece precio de costo y venta
6. Define stock inicial

**Buscar producto:**
1. Selecciona opción 1 → 2
2. Escanea GTIN
3. Sistema muestra información completa
4. Ver stock de cada presentación

**Registrar entrada de stock:**
1. Selecciona opción 1 → 3
2. Escanea GTIN del producto
3. Selecciona presentación
4. Ingresa cantidad
5. Ingresa razón (factura, compra, etc.)
6. Completa número de referencia

**Registrar salida de stock:**
1. Selecciona opción 1 → 4
2. Escanea GTIN del producto
3. Selecciona presentación
4. Ingresa cantidad a salir
5. Ingresa razón del movimiento
6. Sistema valida stock disponible

#### Punto de Venta
**Crear una venta:**
1. Selecciona opción 2 → 1
2. Escanea cada producto
3. Sistema muestra presentaciones disponibles
4. Selecciona cantidad
5. El carrito se actualiza automáticamente
6. Ver carrito en cualquier momento (opción 3)
7. Selecciona método de pago
8. Sistema genera ticket automáticamente

**Ver carrito:**
1. Selecciona opción 2 → 3
2. Muestra todos los productos agregados
3. Subtotal, impuestos y total

**Procesar pago:**
1. Selecciona opción 2 → 4
2. Elige método de pago
3. Ingresa nombre del cajero
4. Sistema genera número de ticket
5. Imprime o guarda ticket

#### Reportes
1. Selecciona opción 3
2. Muestra reporte general
3. Stock del inventario
4. Valor total del inventario
5. Productos sin stock
6. Productos en alerta

### Interfaz Gráfica (Opción 2)

**Características visuales:**
- Ventana principal con pestañas
- Pestaña Inventario: búsqueda y gestión
- Pestaña POS: carrito visual
- Pestaña Reportes: datos en tablas

**Cómo usar:**
1. Ingresa GTIN en campo de búsqueda
2. Haz click en "Buscar"
3. Los datos se cargan en la tabla
4. Para POS, agrega productos al carrito
5. El carrito se actualiza en tiempo real
6. Ver botones de acción para cada operación

### Interfaz Web (Opción 3)

**Acceso:**
```
Abre en tu navegador: http://localhost:5000
```

**Páginas disponibles:**
- 🏠 **Inicio**: Dashboard con resumen
- 📦 **Inventario**: Búsqueda de productos
- 🛒 **POS**: Carrito de compra integrado
- 📊 **Reportes**: Gráficos y estadísticas

**Cómo usar POS Web:**
1. Panel izquierdo: ingresa GTIN
2. Haz click en "Agregar"
3. El producto aparece en la tabla del carrito
4. El resumen se actualiza automáticamente
5. Click en "Procesar Pago" para completar

**Cómo acceder desde otro dispositivo:**
1. Encuentra tu IP local: `ipconfig` (Windows) o `ifconfig` (Linux)
2. En otro dispositivo: `http://tu_ip:5000`
3. Ejemplo: `http://192.168.1.100:5000`

---

## Arquitectura Técnica

### Patrón de Diseño: MVC

```
MODEL (Modelos de Datos)
├── Producto
├── Presentacion
├── MovimientoInventario
├── Venta
├── VentaItem
└── Usuario

VIEW (Interfaz de Usuario)
├── Terminal (CLI)
├── GUI (PyQt5)
└── Web (Flask + HTML/CSS/JS)

CONTROLLER (Lógica de Negocio)
├── GestorInventario
├── GestorPOS
└── GTINBuscador
```

### Flujo de Datos

```
Usuario
   ↓
Interface (Terminal/GUI/Web)
   ↓
Core Module (inventory_manager, pos_manager)
   ↓
Database (SQLAlchemy ORM)
   ↓
SQLite local (o MySQL opcional)
```

### Stack Tecnológico

```
Backend:
├── Python 3.8+
├── Flask (web server)
├── SQLAlchemy (ORM)
└── SQLite / MySQL (base de datos)

Frontend:
├── Terminal: Menús en texto
├── GUI: PyQt5
└── Web: HTML5 + CSS3 + JavaScript

Integraciones:
├── OpenFoodFacts API (búsqueda GTIN)
├── Google Custom Search API (búsqueda avanzada)
└── BeautifulSoup (web scraping)
```

---

## Módulos y Componentes

### config/settings.py

**Responsabilidad**: Configuración centralizada

**Variables principales:**
```python
- MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
- DATABASE_URL (string de conexión)
- GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID
- FLASK_HOST, FLASK_PORT, DEBUG
- PRESENTACIONES (diccionario de tipos)
- MONEDA, IDIOMA
```

### database/connection.py

**Responsabilidad**: Gestionar conexiones a BD

**Funciones principales:**
```python
- create_engine() - Crear motor SQLAlchemy
- SessionLocal - Factory de sesiones
- get_db() - Generador para obtener sesiones
- create_tables() - Crear todas las tablas
- init_db() - Inicializar BD
```

### database/models.py

**Responsabilidad**: Definir estructura de BD

**Modelos:**
```python
- Producto: artículos del catálogo
- Presentacion: tabletas, ampollas, etc.
- MovimientoInventario: entrada/salida/ajuste
- Venta: tickets de caja
- VentaItem: items dentro de una venta
- Usuario: usuarios del sistema
```

### api/gtin_lookup.py

**Responsabilidad**: Búsqueda de productos por GTIN

**Clases:**
```python
- GTINLookup
  - buscar_por_openfoodfacts()
  - buscar_por_google()
  - buscar_gtin() (búsqueda combinada)
- GTINBuscador (interfaz simplificada)
```

### api/google_api.py

**Responsabilidad**: Integración avanzada con Google Custom Search

**Clases:**
```python
- GoogleSearchAPI
  - buscar()
  - buscar_producto_imagen()
  - buscar_informacion_producto()
```

### core/barcode_scanner.py

**Responsabilidad**: Lectura y validación de códigos de barras

**Clases:**
```python
- BarcodeLector
  - validar_gtin()
  - limpiar_codigo()
  - verificar_digito()
  - escanear_terminal()
  - leer_archivo_codigos()
- EscanerProducto (interfaz simplificada)
```

**Formatos soportados:**
- GTIN-8: 8 dígitos
- GTIN-12: 12 dígitos
- GTIN-13: 13 dígitos
- GTIN-14: 14 dígitos

### core/inventory_manager.py

**Responsabilidad**: Gestión del inventario

**Clase: GestorInventario**
```python
Métodos principales:
- registrar_producto()
- agregar_presentacion()
- registrar_movimiento()
- obtener_producto_por_gtin()
- obtener_stock()
- obtener_productos_stock_bajo()
- historial_movimientos()
- reporte_general()
```

**Ejemplo de uso:**
```python
from database.connection import SessionLocal
from core.inventory_manager import GestorInventario

db = SessionLocal()
gestor = GestorInventario(db)

# Registrar producto
producto = gestor.registrar_producto(
    gtin='7501001234567',
    nombre='Paracetamol 500mg',
    laboratorio='Lab Genérico'
)

# Agregar presentación
presentacion = gestor.agregar_presentacion(
    producto_id=producto.id,
    tipo_presentacion='tableta',
    cantidad=1,
    precio_unitario=100,
    precio_venta=250,
    stock_inicial=50
)

# Registrar entrada
movimiento = gestor.registrar_movimiento(
    producto_id=producto.id,
    presentacion_id=presentacion.id,
    tipo='entrada',
    cantidad=100,
    razon='Compra a proveedor',
    usuario='Admin'
)
```

### core/pos_manager.py

**Responsabilidad**: Gestión del punto de venta

**Clases:**
```python
- CarritoCompra
  - agregar_item()
  - eliminar_item()
  - vaciar_carrito()
  - obtener_resumen()
  - obtener_items()

- GestorPOS
  - crear_venta()
  - obtener_venta()
  - obtener_ventas_por_fecha()
  - reporte_ventas_diario()
```

**Ejemplo de uso:**
```python
from core.pos_manager import GestorPOS

db = SessionLocal()
pos = GestorPOS(db)

# Crear venta
venta = pos.crear_venta(
    numero_ticket='TK-20250531-001000',
    metodo_pago='efectivo',
    usuario='Juan Pérez'
)

# Ver resumen
resumen = pos.reporte_ventas_diario('2025-05-31')
```

### ui/terminal_ui.py

**Responsabilidad**: Interfaz de línea de comandos

**Clase: InterfazTerminal**
```python
Métodos públicos:
- menu_inventario()
- registrar_producto()
- buscar_producto()
- registrar_entrada()
- registrar_salida()
- menu_pos()
- agregar_a_carrito()
- procesar_pago()
- menu_reportes()
- ejecutar()
```

### ui/gui_ui.py

**Responsabilidad**: Interfaz gráfica con PyQt5

**Clases:**
```python
- InterfazGUI
- VentanaPrincipal (QMainWindow)
  - crear_ui()
  - crear_pestaña_inventario()
  - crear_pestaña_pos()
  - crear_pestaña_reportes()
```

### web/app.py

**Responsabilidad**: Aplicación web Flask y API REST

**Rutas principales:**
```python
GET  /                          # Página principal
GET  /inventario               # Página de inventario
GET  /pos                       # Página de POS
GET  /reportes                  # Página de reportes

GET  /api/productos             # Listar productos
GET  /api/productos/<gtin>      # Obtener producto
POST /api/productos             # Crear producto
GET  /api/buscar-gtin/<gtin>   # Buscar en APIs externas

GET  /api/inventario/stock-bajo # Productos con stock bajo
POST /api/inventario/movimiento # Registrar movimiento
GET  /api/inventario/reporte    # Reporte de inventario

GET  /api/ventas                # Listar ventas
GET  /api/ventas/reporte/<fecha> # Reporte de ventas
```

---

## APIs Integradas

### 1. OpenFoodFacts API

**Tipo**: Gratuita, sin autenticación  
**Endpoint**: `https://world.openfoodfacts.org/api/v0/product/{gtin}.json`

**Ventajas:**
✅ Gratuita  
✅ Sin límite de requests  
✅ Amplia base de datos  
✅ Información de productos

**Desventajas:**
❌ Resultados ocasionalmente incompletos  
❌ Información no siempre es precisa  

**Ejemplo de respuesta:**
```json
{
  "status": 1,
  "product": {
    "product_name": "Paracetamol 500mg",
    "brands": "Laboratorio Genérico",
    "ingredients_text": "Paracetamol...",
    "categories": "Productos"
  }
}
```

### 2. Google Custom Search API

**Tipo**: Pago, requiere autenticación  
**Limite**: 100 búsquedas/día (gratuito), 10,000/día (pago)  

**Para obtener credenciales:**
1. Ir a https://console.cloud.google.com
2. Crear nuevo proyecto
3. Activar "Custom Search API"
4. Crear credenciales (API Key)
5. Crear motor de búsqueda personalizado en https://cse.google.com
6. Copiar ID del motor

**Ventajas:**
✅ Muy preciso  
✅ Incluye imágenes  
✅ Información actualizada  

**Desventajas:**
❌ Requiere configuración  
❌ Límite de requests diarios  
❌ Requiere cuenta de Google  

**Configuración en .env:**
```env
GOOGLE_API_KEY=tu_clave_api
GOOGLE_SEARCH_ENGINE_ID=tu_id_motor
```

---

## Base de Datos

### Estructura de Tablas

#### Tabla: productos
```sql
id (PRIMARY KEY)
gtin (UNIQUE INDEX)
cum
nombre (INDEX)
descripcion
principio_activo
laboratorio
registro_sanitario
fecha_creacion
fecha_actualizacion
```

#### Tabla: presentaciones
```sql
id (PRIMARY KEY)
producto_id (FOREIGN KEY)
tipo (ENUM)
cantidad
precio_unitario
precio_venta
stock_actual
stock_minimo
codigo_interno (UNIQUE)
fecha_creacion
fecha_actualizacion
```

#### Tabla: movimientos_inventario
```sql
id (PRIMARY KEY)
producto_id (FOREIGN KEY)
presentacion_id (FOREIGN KEY)
tipo_movimiento (ENUM)
cantidad
razon
usuario
referencia_externa
fecha (INDEX)
```

#### Tabla: ventas
```sql
id (PRIMARY KEY)
numero_ticket (UNIQUE INDEX)
estado (ENUM)
subtotal
impuesto
total
metodo_pago
usuario
notas
fecha (INDEX)
```

#### Tabla: venta_items
```sql
id (PRIMARY KEY)
venta_id (FOREIGN KEY)
producto_id (FOREIGN KEY)
presentacion_id (FOREIGN KEY)
cantidad
precio_unitario
descuento
subtotal
```

#### Tabla: usuarios
```sql
id (PRIMARY KEY)
nombre
email (UNIQUE)
rol
activo
fecha_creacion
```

### Backups y Recuperación

**Crear backup:**
```bash
mysqldump -u root -p inventario_general > backup.sql
```

**Restaurar backup:**
```bash
mysql -u root -p inventario_general < backup.sql
```

**Backup automático con Python:**
```python
import subprocess
from datetime import datetime

fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
comando = f'mysqldump -u root inventario_general > backup_{fecha}.sql'
subprocess.run(comando, shell=True)
```

---

## Interfaces de Usuario

### Terminal (CLI) - Detallado

**Ventajas:**
- ⚡ Muy rápida
- 💻 Sin dependencias gráficas
- 📱 Ideal para escaneo contínuo
- 🖨️ Fácil de automatizar

**Desventajas:**
- ❌ Menos intuitiva para usuarios no técnicos
- ❌ No es visual

**Menú jerárquico:**
```
MENÚ PRINCIPAL
├── 1. GESTIÓN DE INVENTARIO
│   ├── 1. Registrar nuevo producto
│   ├── 2. Buscar producto por GTIN
│   ├── 3. Registrar entrada de stock
│   ├── 4. Registrar salida de stock
│   ├── 5. Ver productos con stock bajo
│   ├── 6. Historial de movimientos
│   └── 7. Volver al menú principal
├── 2. PUNTO DE VENTA (POS)
│   ├── 1. Agregar producto
│   ├── 2. Eliminar producto
│   ├── 3. Ver carrito
│   ├── 4. Procesar pago
│   ├── 5. Vaciar carrito
│   └── 6. Volver al menú principal
├── 3. REPORTES
│   └── Muestra reporte general
├── 4. CONFIGURACIÓN
│   └── (En desarrollo)
└── 5. SALIR
```

### GUI (PyQt5) - Detallado

**Ventajas:**
- 🎨 Interfaz visual moderna
- 👥 Ideal para usuarios no técnicos
- 🖥️ Totalmente intuitiva
- 📊 Tablas interactivas

**Desventajas:**
- ⚠️ Requiere instalación de PyQt5
- 🐢 Ligeramente más lenta que CLI
- 📦 Tamaño de aplicación mayor

**Componentes:**
```
VentanaPrincipal
├── Pestaña: Inventario
│   ├── Campo de búsqueda (GTIN)
│   ├── Tabla de productos
│   └── Botones de acción
├── Pestaña: POS
│   ├── Panel izquierdo: búsqueda
│   ├── Panel derecho: carrito
│   └── Resumen de compra
└── Pestaña: Reportes
    ├── Reporte de inventario
    ├── Reporte de ventas
    └── Productos con stock bajo
```

### Web (Flask) - Detallado

**Ventajas:**
- 🌐 Accesible desde cualquier dispositivo
- 📱 Interfaz responsiva
- 🔄 Actualización en tiempo real
- 👥 Multi-usuario

**Desventajas:**
- 📡 Requiere conexión de red
- 🔌 Requiere servidor corriendo
- 🐌 Ligeramente más lento que GUI

**Características del frontend:**
```
index.html
├── Navbar con navegación
├── Cards con accesos rápidos
└── Footer con información

inventario.html
├── Barra de búsqueda
├── Tabla de productos
├── Acciones por producto
└── Información detallada

pos.html
├── Panel de búsqueda (izq)
├── Panel de carrito (der)
├── Resumen dinámico
└── Botón de pago

reportes.html
├── Reporte de inventario
├── Reporte de ventas
├── Stock bajo
└── Actualización automática
```

---

## Ejemplos de Uso

### Ejemplo 1: Registrar un Producto Completo

```python
from database.connection import SessionLocal, init_db
from core.inventory_manager import GestorInventario
from api.gtin_lookup import GTINBuscador

# Inicializar
init_db()
db = SessionLocal()
gestor = GestorInventario(db)

# Buscar información en APIs
buscador = GTINBuscador()
info = buscador.buscar('7501001234567')

if info['encontrado']:
    # Registrar producto
    producto = gestor.registrar_producto(
        gtin='7501001234567',
        nombre=info['datos']['nombre'],
        laboratorio=info['datos'].get('marca'),
        descripcion=info['datos'].get('descripcion')
    )
    
    # Agregar presentación (Tableta 500mg)
    pres_tableta = gestor.agregar_presentacion(
        producto_id=producto.id,
        tipo_presentacion='tableta',
        cantidad=1,
        precio_unitario=150,      # Precio de costo
        precio_venta=350,         # Precio de venta
        stock_inicial=50
    )
    
    # Agregar presentación (Ampolla 10ml)
    pres_ampolla = gestor.agregar_presentacion(
        producto_id=producto.id,
        tipo_presentacion='ampolla',
        cantidad=1,
        precio_unitario=500,
        precio_venta=1200,
        stock_inicial=20
    )
    
    print(f"✅ Producto registrado: {producto.nombre}")
    print(f"   Presentaciones: {len(producto.presentaciones)}")

db.close()
```

### Ejemplo 2: Procesar una Venta

```python
from database.connection import SessionLocal
from core.pos_manager import GestorPOS

db = SessionLocal()
pos = GestorPOS(db)

# Agregar productos al carrito
pos.carrito.agregar_item(
    producto_id=1,
    presentacion_id=1,
    cantidad=2,
    precio_unitario=350,
    descuento=5  # 5% de descuento
)

pos.carrito.agregar_item(
    producto_id=2,
    presentacion_id=3,
    cantidad=1,
    precio_unitario=1200,
    descuento=0
)

# Ver resumen
resumen = pos.carrito.obtener_resumen()
print(f"Items: {resumen['cantidad_items']}")
print(f"Subtotal: ${resumen['subtotal']:.2f}")
print(f"IVA: ${resumen['impuesto']:.2f}")
print(f"Total: ${resumen['total']:.2f}")

# Procesar venta
numero_ticket = pos.generar_numero_ticket()
venta = pos.crear_venta(
    numero_ticket=numero_ticket,
    metodo_pago='efectivo',
    usuario='Juan Pérez',
    notas='Cliente regular'
)

if venta:
    print(f"✅ Venta completada: {venta.numero_ticket}")
    print(f"   Total: ${venta.total:.2f}")

db.close()
```

### Ejemplo 3: Generar Reporte Diario

```python
from database.connection import SessionLocal
from core.inventory_manager import GestorInventario
from core.pos_manager import GestorPOS
from datetime import datetime

db = SessionLocal()
gestor = GestorInventario(db)
pos = GestorPOS(db)

fecha_hoy = datetime.now().strftime("%Y-%m-%d")

# Reporte de inventario
reporte_inv = gestor.reporte_general()
print("📊 REPORTE DE INVENTARIO")
print(f"Total de productos: {reporte_inv['total_productos']}")
print(f"Stock total: {reporte_inv['total_stock']} unidades")
print(f"Valor inventario: ${reporte_inv['valor_inventario']:.2f}")
print(f"Productos sin stock: {reporte_inv['productos_sin_stock']}")

# Reporte de ventas
reporte_vtas = pos.reporte_ventas_diario(fecha_hoy)
print("\n📈 REPORTE DE VENTAS")
print(f"Cantidad de ventas: {reporte_vtas['cantidad_ventas']}")
print(f"Total vendido: ${reporte_vtas['total_ventas']:.2f}")
print(f"Promedio por venta: ${reporte_vtas['promedio_venta']:.2f}")
print(f"Impuestos: ${reporte_vtas['impuestos_totales']:.2f}")

# Productos con stock bajo
productos_alerta = gestor.obtener_productos_stock_bajo()
print("\n⚠️ PRODUCTOS CON STOCK BAJO")
for p in productos_alerta:
    print(f"{p['nombre']}: {p['stock_actual']}/{p['stock_minimo']}")

db.close()
```

---

## Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'mysql'"

**Causa:** MySQL Connector no está instalado

**Solución:**
```bash
pip install mysql-connector-python
```

### Error: "Access denied for user 'root'@'localhost'"

**Causa:** Contraseña incorrecta en .env o MySQL no tiene la contraseña vacía

**Soluciones:**
1. Verificar contraseña en XAMPP
2. Actualizar .env con la contraseña correcta
3. O resetear contraseña MySQL

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '';
FLUSH PRIVILEGES;
```

### Error: "Database 'inventario_general' does not exist"

**Causa:** La base de datos no fue creada

**Solución:**
```sql
CREATE DATABASE inventario_general CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Error: "PyQt5 is not installed"

**Causa:** PyQt5 no está en el entorno virtual

**Solución:**
```bash
pip install PyQt5
```

### Error: "Connection refused" en Flask

**Causa:** Puerto 5000 está siendo usado por otra aplicación

**Soluciones:**
1. Cerrar la otra aplicación
2. O cambiar puerto en .env:
```env
FLASK_PORT=5001
```

### Error: "GTIN inválido"

**Causa:** El código de barras no es válido

**Soluciones:**
1. Verifica que sea un GTIN válido (8, 12, 13 o 14 dígitos)
2. Verifica que el dígito de control sea correcto
3. Prueba sin espacios ni caracteres especiales

### Error: "No se encuentra el producto en las APIs"

**Causa:** El producto no existe en la base de datos externa

**Soluciones:**
1. Verifica GTIN correcto
2. Registra el producto manualmente
3. Intenta con la otra API

### Base de datos lenta

**Causa:** Falta de índices

**Solución:** Crear índices
```sql
CREATE INDEX idx_gtin ON productos(gtin);
CREATE INDEX idx_nombre ON productos(nombre);
CREATE INDEX idx_stock ON presentaciones(stock_actual);
```

---

## FAQ

### ¿Puedo usar SQLite en lugar de MySQL?

**Sí.** En `config/settings.py`, cambia:
```python
# De:
DATABASE_URL = f"mysql+pymysql://..."

# A:
DATABASE_URL = "sqlite:///./inventario.db"
```

**Ventajas:**
- Un archivo único
- No requiere servidor
- Perfecto para portátil

**Desventajas:**
- No es para múltiples usuarios simultáneos
- Menos escalable

### ¿Cómo hacer que funcione desde otra máquina?

**Para Interfaz Web:**
1. Obtén tu IP: `ipconfig` (Windows)
2. En otro dispositivo: `http://tu_ip:5000`
3. Ejemplo: `http://192.168.1.100:5000`

**Para Terminal/GUI:**
- Debe ejecutarse en la misma máquina con MySQL

### ¿Puedo cambiar el porcentaje de IVA?

**Sí.** En `core/pos_manager.py`, línea del cálculo de impuesto:
```python
# Cambiar 0.19 (19%) por el porcentaje deseado
self.impuesto = self.subtotal * 0.19
```

### ¿Cómo agregar más métodos de pago?

**En la interfaz:**
1. Modificar diccionario en cada interfaz
2. Agregar validación si es necesario
3. Guardar en BD con nombre del método

### ¿Puedo exportar reportes a PDF?

**Sí, agregando:**
```bash
pip install reportlab
```

Luego crear función en `core/` para generar PDF.

### ¿Cómo hacer backups automáticos?

**Script Python:**
```python
import subprocess
from datetime import datetime
import schedule
import time

def backup():
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    cmd = f'mysqldump -u root inventario_general > backup_{fecha}.sql'
    subprocess.run(cmd, shell=True)
    print(f"✅ Backup creado: backup_{fecha}.sql")

# Ejecutar diariamente a las 2 AM
schedule.every().day.at("02:00").do(backup)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### ¿Se pueden agregar más usuarios?

**Sí.** En `database/models.py` ya existe tabla `usuarios` con roles.

### ¿Cómo limitar acceso por usuario?

**Agregar sistema de login:**
1. Modificar `main.py` para pedir login
2. Verificar usuario en BD
3. Pasar usuario a interfaces

### ¿Puedo integrar más APIs?

**Sí.** Crear nuevo archivo en `api/` con la integración.

**Ejemplo:**
```python
# api/productos_api.py
class ProductosAPI:
    def buscar_producto(self, nombre):
        # Implementar búsqueda
        pass
```

---

## Roadmap Futuro

### v1.1.0 - Autenticación (Próxima)
- [ ] Sistema de login seguro
- [ ] Roles avanzados (admin, cajero, inventario)
- [ ] Auditoría de acciones
- [ ] Historial de accesos

### v1.2.0 - Reportes Avanzados
- [ ] Exportación a PDF
- [ ] Exportación a Excel
- [ ] Gráficas estadísticas
- [ ] Predicción de stock
- [ ] Análisis de ventas

### v1.3.0 - Integración Móvil
- [ ] App móvil (React Native)
- [ ] Sincronización en tiempo real (WebSockets)
- [ ] Modo offline

### v2.0.0 - Sistema Completo
- [ ] Gestión de proveedores
- [ ] Órdenes de compra automáticas
- [ ] Control de lotes y vencimiento
- [ ] Integración con código QR
- [ ] Reportes de auditoría
- [ ] Sistema de devoluciones

### v2.1.0 - Marketplace
- [ ] Catálogo online
- [ ] Pedidos por internet
- [ ] Pasarela de pagos

### v3.0.0 - Inteligencia Artificial
- [ ] Predicción de demanda
- [ ] Recomendaciones automáticas
- [ ] Detección de anomalías
- [ ] Chatbot de soporte

---

## Conclusión

Este sistema proporciona una **solución profesional, completa y escalable** para la gestión de inventario y ventas en comercios minoristas.

### Puntos Clave:
✅ **Modular**: Fácil de extender  
✅ **Escalable**: Crece con tu negocio  
✅ **Profesional**: Código limpio y bien documentado  
✅ **Flexible**: Múltiples interfaces  
✅ **Robusto**: Manejo de errores completo  
✅ **Documentado**: Guías completas incluidas  

### Para Comenzar:
1. Instala Python
2. Clona el proyecto
3. Corre `init_db.py`
4. Ejecuta `python main.py`
5. ¡Comienza a usar!

---

## Agradecimientos

- [opensource-coding/Dark-Light-Mode-Switch](https://github.com/opensource-coding/Dark-Light-Mode-Switch) — componente de interruptor de modo oscuro/claro integrado en la interfaz web del proyecto.

**Última actualización**: 31 de mayo de 2026  
**Versión**: 1.0.0  
**Estado**: Producción  
**Autor**: GitHub Copilot

Para soporte o preguntas, consulta [FAQ.md](FAQ.md) o [README.md](README.md)
