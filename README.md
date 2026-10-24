# Sistema de Inventario

Documentación actualizada el 23 de octubre de 2026.

## Resumen del proyecto

Este proyecto es un sistema local de inventario y punto de venta para negocios que necesitan gestionar stock, ventas y reportes con una interfaz pensada para uso rápido y táctil.

Actualmente incluye:

- gestión de productos y presentaciones
- control de stock por entradas, salidas y ajustes
- punto de venta con escaneo rápido por GTIN
- carrito de compra con modificación de cantidad y descuentos por ítem
- reportes interactivos avanzados con Streamlit y Plotly (gráficos de barras, líneas, áreas, dona/pastel, treemaps, dispersión y exportación a PDF/Excel/CSV)
- interfaz gráfica con PyQt5 y acceso en un clic a los reportes
- panel de escritorio con navegación lateral, resumen y accesos rápidos
- flujo de pago simplificado con selección numérica
- modo oscuro / claro con memoria y persistencia automática entre sesiones
- interruptor de tema con transición animada de día a noche
- **búsqueda avanzada multi-criterio** (nombre, GTIN, laboratorio, descripción)
- **valorización financiera del inventario** (costo total, venta potencial, margen)
- **sugerencias automáticas de reabastecimiento** por stock mínimo
- **importación de catálogo desde CSV y exportación** en CSV/Excel
- **sistema de backups** de la base de datos con restauración
- **generador de códigos GTIN-13** con checksum EAN válido
- **cierre de caja diario** con resumen por cajero y método de pago
- **API REST ampliada** con nuevas rutas para inventario y caja
- API de sincronización incremental de solo lectura para preparar clientes móviles
- validaciones de stock y ventas para evitar cantidades inválidas o inventario negativo
- mejoras de accesibilidad en web, dashboard y GUI: teclado, foco visible, etiquetas y alternativas tabulares para gráficas

Las mejoras de accesibilidad no representan una certificación formal de conformidad WCAG; se recomienda validar las interfaces con tecnologías de asistencia utilizadas en el entorno de despliegue.

## Estado actual

Versión actual: 1.2.0
Estado: funcional y listo para uso local con GUI, Dashboard Streamlit y API REST

## Características principales de la GUI

La interfaz gráfica actual incluye varias mejoras orientadas a rapidez y ergonomía:

- panel de escritorio con navegación lateral y accesos directos
- tabla de inventario responsive y adaptada al ancho de la ventana
- botones de acción más grandes para uso táctil
- búsqueda rápida de productos con lupa
- catálogo de proveedores con datos de contacto y asignación de productos
- columna de proveedor en inventario, con indicador cuando no hay uno asignado
- formularios de producto y proveedor con ayuda contextual y acciones claras
- agregado directo de artículos al carrito desde el POS
- flujo de cobro sin pedir nombre de cajero
- método de pago con selección numérica:
  - 1 = Efectivo
  - 2 = Transferencia
- botón de pago, vaciar carrito y eliminar producto con tamaños ampliados
- interruptor de tema animado (Día / Noche) con guardado automático del último modo usado

## Requisitos

- Python 3.10 o superior
- pip
- SQLite (incluido con Python)
- PyQt5 para la interfaz gráfica
- Streamlit y Plotly para el dashboard de reportes
- Flask para la versión web

## Instalación rápida

1. Crear y activar entorno virtual

```bash
python -m venv venv
venv\Scripts\activate
```

2. Instalar dependencias

```bash
pip install -r requirements.txt
```

3. Ejecutar la aplicación

- **Interfaz Gráfica Principal (PyQt5)**:
  ```bash
  python main.py
  ```
- **Dashboard de Reportes en Streamlit (Directo)**:
  ```bash
  python main.py --reportes
  # o también:
  streamlit run reporting/streamlit_reports.py
  ```

### Build de escritorio para Windows

La primera build de Windows se puede descargar como `SNIG-v1.2.0-Windows-x64.zip` desde la sección Releases de GitHub. Descarga y extrae la carpeta completa, luego inicia `SNIG.exe`; no ejecutes el EXE separado de la carpeta `_internal`.

Para generar de nuevo la build desde Windows:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller==6.20.0
python -m PyInstaller --noconfirm --clean SNIG.spec
```

El ejecutable y sus dependencias se generan en `dist/SNIG/`. No se incluyen la base de datos local ni el archivo `.env`; la aplicación crea su base de datos al iniciar.

## Uso recomendado

### Interfaz gráfica

La ventana principal tiene navegación lateral para estas secciones:

- Inicio: resumen de productos, stock, valor del inventario y alertas
- 📦 Inventario: catálogo, búsqueda, proveedor, movimientos y acciones rápidas
- 🛒 Punto de venta: escaneo, carrito y cobro
- 📊 Reportes (con botón directo para lanzar el Dashboard de Streamlit en el navegador)
- 🏭 Proveedores: gestión de contactos y asignación de productos
- 📝 Logs (oculto por defecto y accesible desde reportes o acciones avanzadas)

El catálogo de proveedores permite crear, editar y eliminar contactos, y relacionar varios productos con cada proveedor. La columna **Proveedor** del inventario muestra los nombres asignados o **Sin proveedor**.

### Flujo de POS

- escribe o escanea el GTIN en el campo del POS
- presiona Enter para agregar el producto al carrito
- revisa los artículos agregados
- pulsa Pago
- selecciona el método de pago por número:
  - 1 para Efectivo
  - 2 para Transferencia

### Flujo de inventario

- busca productos por texto o GTIN
- agrega nuevos productos o presentaciones
- gestiona movimientos de stock
- revisa en la tabla la información del catálogo y sus proveedores

### Flujo de proveedores

- abre **Proveedores** desde la navegación lateral
- crea un proveedor con su nombre y los datos de contacto disponibles
- selecciona el proveedor y usa **Asignar productos** para marcar los productos que suministra
- la tabla de inventario refleja los proveedores asignados; eliminar un proveedor no elimina los productos

## Configuración

La configuración por defecto usa SQLite:

```env
DB_ENGINE=sqlite
SQLITE_FILE=./inventario.db
```

Si quieres usar MySQL, puedes configurarlo en .env:

```env
DB_ENGINE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=inventario_general
```

## Estructura principal del proyecto

- config/: configuración del sistema
- database/: modelos SQLAlchemy y conexión a la base de datos
- core/: lógica del inventario y del punto de venta
- api/: integrations con servicios externos de GTIN
- ui/: interfaces de terminal, GUI y componentes visuales
- web/: aplicación Flask
- data/: recursos y archivos de datos
- tests/: pruebas del proyecto

## Funcionalidades actuales

- registro de productos y presentaciones
- control de stock y movimientos
- ventas y cálculo de totales
- generador de reportes
- consulta por GTIN
- soporte para múltiples interfaces
- interfaz gráfica potente y adaptable a diferentes tamaños de pantalla
- modo oscuro automático

## CRUD

| Operación | Método | Descripción |
|-----------|--------|-------------|
| **Create** | `registrar_producto()`, `agregar_presentacion()`, `registrar_movimiento()` | Crea productos, presentaciones y movimientos de inventario |
| **Read** | `obtener_producto_por_gtin()`, `obtener_productos()`, `obtener_stock()`, `historial_movimientos()`, `reporte_general()` | Consulta productos, stock e historial |
| **Update** | Actualización de `stock_actual` al registrar movimientos | Modifica el stock al registrar entradas, salidas y ajustes |
| **Delete** | `eliminar_producto()` | Elimina un producto y sus ítems de venta relacionados |

## Solución de problemas rápidos

### PyQt5 no está instalado
```bash
pip install PyQt5
```

### Flask no está instalado
```bash
pip install flask
```

### Error con MySQL
- verifica que XAMPP o el servicio MySQL esté activo
- revisa .env
- confirma que la base de datos existe

## Documentación adicional

- [CHANGELOG.md](CHANGELOG.md)
- [DOCUMENTACION_COMPLETA.md](DOCUMENTACION_COMPLETA.md)
- [FAQ.md](FAQ.md)

## Roadmap

- autenticación de usuarios
- exportación de reportes a PDF
- validaciones adicionales de negocio
- mejoras de sincronización y escalabilidad

## Agradecimientos

- [opensource-coding/Dark-Light-Mode-Switch](https://github.com/opensource-coding/Dark-Light-Mode-Switch) — por el componente de interruptor de modo oscuro/claro utilizado en la interfaz web del proyecto.

---

Última actualización: 23 de octubre de 2026
Versión: 1.2.0
