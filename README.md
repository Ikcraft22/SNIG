# Sistema de Inventario

Documentación actualizada el 26 de octubre de 2026.

## Resumen del proyecto

Este proyecto es un sistema local de inventario y punto de venta para negocios que necesitan gestionar stock, ventas y reportes con una interfaz pensada para uso rápido y táctil.

Actualmente incluye:

- gestión de productos y presentaciones
- control de stock por entradas, salidas y ajustes
- punto de venta con escaneo rápido de Barcode
- carrito de compra con modificación de cantidad y descuentos por ítem
- reportes interactivos avanzados con Streamlit y Plotly (gráficos de barras, líneas, áreas, dona/pastel, treemaps, dispersión y exportación a PDF/Excel/CSV)
- interfaz gráfica con PyQt5 y acceso en un clic a los reportes
- panel de escritorio con navegación lateral, resumen y accesos rápidos
- flujo de pago simplificado con selección numérica
- modo oscuro / claro con memoria y persistencia automática entre sesiones
- interruptor de tema con transición animada de día a noche
- **búsqueda avanzada multi-criterio** (nombre, Barcode y descripción)
- **valorización financiera del inventario** (costo total, venta potencial, margen)
- **sugerencias automáticas de reabastecimiento** por stock mínimo
- **importación de catálogo desde CSV y exportación** en CSV/Excel
- **sistema de backups** de la base de datos con restauración
- **generador de códigos GTIN-13** con checksum EAN válido
- **cierre de caja diario** con resumen por cajero y método de pago
- **API REST ampliada** con nuevas rutas para inventario y caja
- feed API incremental de cambios (solo lectura; todavía no sincroniza automáticamente otras sucursales)
- validaciones de stock y ventas para evitar cantidades inválidas o inventario negativo
- mejoras de accesibilidad en web, dashboard y GUI: teclado, foco visible, etiquetas y alternativas tabulares para gráficas

Las mejoras de accesibilidad no representan una certificación formal de conformidad WCAG; se recomienda validar las interfaces con tecnologías de asistencia utilizadas en el entorno de despliegue.

### Nomenclatura del código de barras

En las pantallas de la aplicación el campo se muestra como **Barcode**. En esta documentación se identifica como **Barcode (GTIN)** para aclarar que corresponde al identificador técnico GTIN; la base de datos y la API conservan el nombre interno `gtin`.

## Estado actual

Versión actual: 1.2.0
Estado: funcional y listo para uso local con GUI, Dashboard Streamlit y API REST

La API publica `GET /api/sync/cursor` y `GET /api/sync/changes?cursor=0&limit=100` como feed de cambios de solo lectura. Requieren `SYNC_API_TOKEN` en `.env` y el encabezado `Authorization: Bearer <token>`; si no se configura el token, el feed queda deshabilitado. Todavía no existe un cliente que sincronice cambios entre sucursales, descargue un estado inicial, envíe cambios o resuelva conflictos.

Genera un token aleatorio (por ejemplo, con `python -c "import secrets; print(secrets.token_urlsafe(32))"`), configúralo en el servidor como `SYNC_API_TOKEN` y guárdalo de forma segura también en los clientes. No lo compartas ni lo subas al repositorio.

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
  - Tarjeta está desactivada temporalmente; los reportes conservan los pagos históricos
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

La aplicación y el ejecutable usan `Logo.ico` como icono de ventana y de la barra de tareas.

Para generar de nuevo la build desde Windows:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller==6.20.0
python -m PyInstaller --noconfirm --clean SNIG.spec
```

El ejecutable y sus dependencias se generan en `dist/SNIG/`. No se incluyen la base de datos local ni el archivo `.env`; la aplicación crea su base de datos al iniciar.

## Uso recomendado

### Interfaz gráfica

Por ahora, se omite el panel de inicio de sesión y la aplicación abre directamente. La sección **Usuarios**, el cambio de usuario y las restricciones por rol también están desactivados temporalmente. No se borraron las cuentas ni sus hashes de contraseña; permanecen guardados en la base de datos.

#### Reactivar autenticación y usuarios

En `config/settings.py`, cambia `AUTENTICACION_HABILITADA = False` a `AUTENTICACION_HABILITADA = True` y reinicia SNIG. Volverán a aparecer el inicio de sesión, la sección **Usuarios**, el cambio de usuario y los permisos por rol. `python init_db.py` también volverá a ofrecer la configuración del administrador inicial. Si la base aún no tiene una cuenta configurada, puedes crearla desde una terminal:

```powershell
python -m core.auth --crear-admin Administrador
```

Las contraseñas se guardan como hashes PBKDF2-SHA256 con salt aleatorio. La migración de `usuarios.password_hash` es aditiva y conserva los registros existentes. Al reactivar el acceso, los roles disponibles son Cajero, Inventario y Admin. Si usas el ejecutable de Windows, también debes reconstruirlo con las instrucciones de [Build de escritorio para Windows](#build-de-escritorio-para-windows).

#### Reactivar el pago con tarjeta

El pago con tarjeta está desactivado temporalmente en las interfaces y en la validación del backend; no se pueden registrar nuevas ventas con ese método. Los pagos anteriores no se eliminan y siguen apareciendo en los reportes. Para volver a habilitarlo en todas las interfaces, cambia `PAGO_TARJETA_HABILITADO = False` a `PAGO_TARJETA_HABILITADO = True` en `config/settings.py` y reinicia SNIG. Si usas el ejecutable de Windows, vuelve a generar el build para incluir la configuración actualizada.

La ventana principal tiene navegación lateral para estas secciones:

- Inicio: resumen de productos, stock, valor del inventario y alertas
- 📦 Inventario: catálogo, búsqueda, proveedor, movimientos y acciones rápidas
- 🛒 Punto de venta: escaneo, carrito y cobro
- 📊 Reportes (con botón directo para lanzar el Dashboard de Streamlit en el navegador)
- 🏭 Proveedores: gestión de contactos y asignación de productos
- 📝 Logs (oculto por defecto y accesible desde reportes o acciones avanzadas)

El catálogo de proveedores permite crear, editar y eliminar contactos, y relacionar varios productos con cada proveedor. La columna **Proveedor** del inventario muestra los nombres asignados o **Sin proveedor**.

### Arqueo y reportes

- Desde POS, **Arqueo / Cierre de Caja** muestra ingresos, tickets, ticket promedio y desglose diario por cajero y método de pago; permite exportar el resumen a PDF.
- La pestaña **Reportes** de escritorio genera un PDF completo de ventas, inventario, detalle y movimientos.
- El dashboard calcula por cajero total vendido, número de transacciones, ticket medio y tickets por hora observada. La velocidad se muestra como `0` cuando no existen al menos dos marcas de tiempo distintas.
- Web y Streamlit permiten exportar PDF, Excel multitabla y CSV. El CSV web admite seleccionar la tabla, rango de fechas inclusivo, método de pago y producto.
- Las exportaciones incluyen los filtros aplicados y una marca de tiempo ISO segura en el nombre del archivo.

Las alertas de stock bajo aparecen en el icono de la bandeja de Windows. Se comprueban cada 15 minutos por defecto; se puede cambiar el intervalo con `ALERTA_STOCK_INTERVALO_MINUTOS` en `.env` (mínimo 1 minuto). Al abrir una alerta, SNIG cambia a Inventario y filtra las presentaciones bajo su mínimo.

### Flujo de POS

- escribe o escanea el Barcode en el campo del POS
- presiona Enter para agregar el producto al carrito
- revisa los artículos agregados
- pulsa Pago
- selecciona el método de pago por número:
  - 1 para Efectivo
  - 2 para Transferencia

### Flujo de inventario

- busca productos por texto o Barcode
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

- volver a activar autenticación y gestión de usuarios cuando se requiera
- cliente seguro para sincronización multi-sucursal
- validaciones adicionales de negocio
- mejoras de escalabilidad

## Agradecimientos

- [opensource-coding/Dark-Light-Mode-Switch](https://github.com/opensource-coding/Dark-Light-Mode-Switch) — por el componente de interruptor de modo oscuro/claro utilizado en la interfaz web del proyecto.

---

Última actualización: 26 de octubre de 2026
Versión: 1.2.0
