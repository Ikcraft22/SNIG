# Preguntas frecuentes

## ¿Cómo inicio el proyecto?

Para abrir el programa de escritorio ejecuta:

```bash
python main.py
```

La interfaz gráfica se abre directamente. Para iniciar otros componentes:

- Dashboard:
  ```bash
  python main.py --reportes
  ```
- Aplicación web:
  ```bash
  python -m web.app
  ```

La interfaz de terminal sigue disponible mediante el módulo `ui.terminal_ui`.

Por ahora, se omite el panel de inicio de sesión y la gestión de usuarios está desactivada. Las cuentas y sus hashes se conservan. Para reactivar ambas funciones, cambia `AUTENTICACION_HABILITADA = False` a `True` en `config/settings.py` y reinicia. Si usas el ejecutable de Windows, vuelve a generar el build con PyInstaller. Si no hay administrador configurado, ejecuta `python init_db.py` o crea uno con `python -m core.auth --crear-admin Administrador`.

## ¿Qué base de datos usa por defecto?

SQLite. El archivo de base de datos se genera como:

```text
inventario.db
```

Puedes cambiarlo en el archivo .env con:

```env
DB_ENGINE=sqlite
SQLITE_FILE=./inventario.db
```

## ¿Cómo abrir la interfaz web?

Inicia Flask desde la raíz del proyecto:

```bash
python -m web.app
```

Luego abre la URL en el navegador:

```text
http://localhost:5000
```

## ¿Qué pasa si la GUI no inicia?

Normalmente es por falta de PyQt5. Instálalo con:

```bash
pip install PyQt5
```

## ¿Qué significa Barcode?

La interfaz muestra **Barcode** donde antes se mostraba GTIN. En esta documentación se indica como **Barcode (GTIN)**; el campo interno de la base de datos y la API sigue llamándose `gtin`.

## ¿Cómo funciona el POS?

En la sección **Punto de venta** puedes escribir o escanear el Barcode (GTIN) y presionar Enter para agregar el producto directamente al carrito. Se puede pagar en Efectivo o por Transferencia; los botones también aceptan las teclas `1` y `2`. Si se repite el mismo producto 10 veces seguidas, el sistema muestra una alerta de compra masiva.

## ¿Por qué no puedo pagar con tarjeta?

El pago con tarjeta está desactivado temporalmente en las interfaces y el backend rechaza nuevas ventas con ese método. Los pagos históricos con tarjeta se conservan y siguen apareciendo en los reportes. Para reactivarlo en GUI, terminal, web y API, cambia `PAGO_TARJETA_HABILITADO = False` a `PAGO_TARJETA_HABILITADO = True` en `config/settings.py` y reinicia SNIG. Para el ejecutable de Windows, genera un build actualizado.

## ¿Cómo registro un proveedor y le asigno productos?

Abre **Proveedores** desde la navegación lateral, pulsa **Nuevo proveedor** y completa el nombre y los datos de contacto disponibles. Después selecciona al proveedor, elige **Asignar productos**, busca por nombre o Barcode (GTIN) y marca los productos que suministra. La columna **Proveedor** del inventario muestra las asignaciones. Eliminar al proveedor no elimina los productos.

## ¿La interfaz está preparada para pantallas táctiles?

Sí. La interfaz de inventario y POS fue ajustada con botones más grandes, mejor espaciado y un diseño más cómodo para uso táctil.

## ¿Cómo hacer un backup de la base de datos?

Si usas SQLite, basta con copiar el archivo inventario.db a otra ubicación.

## ¿Cómo cambiar a MySQL?

Edita .env y define:

```env
DB_ENGINE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=inventario_general
```

## ¿La base de datos se crea sola?

Sí. Al iniciar la aplicación se inicializa la estructura de tablas automáticamente. Si la base ya existía, se añade `usuarios.password_hash` de forma aditiva y se conservan los registros existentes.

## ¿Se sincronizan automáticamente varias sucursales?

No. La API ofrece un feed incremental de solo lectura (`GET /api/sync/cursor` y `GET /api/sync/changes`), pero aún no hay cliente para aplicar/enviar cambios, sincronización inicial ni resolución de conflictos. Los endpoints no tienen autenticación, así que no deben exponerse en redes no confiables.

## ¿Qué permisos tienen los roles?

Los roles están temporalmente desactivados junto con el login. Al reactivar `AUTENTICACION_HABILITADA` en `config/settings.py`, se aplican estos permisos:
- **Cajero**: Inicio, POS y cierre de su propio turno.
- **Inventario**: Inicio, Inventario y Proveedores.
- **Admin**: todas las secciones, métricas financieras y gestión de usuarios.

## ¿Cómo abro el dashboard interactivo de reportes con gráficas (Streamlit)?

Tienes tres opciones fáciles:
1. **Desde la GUI (PyQt5)**: Ve a la pestaña **📊 Reportes** y presiona el botón `🚀 Abrir Dashboard Gráfico en Streamlit`.
2. **Desde la terminal**:
   ```bash
   python main.py --reportes
   ```
   o directamente:
   ```bash
   streamlit run reporting/streamlit_reports.py
   ```
3. **Desde la interfaz web (Flask)**: Ve a la sección `/reportes` y pulsa en el botón para abrir Streamlit.

## ¿Qué tipos de gráficas están disponibles en los reportes?

El dashboard soporta:
- **Barras verticales y horizontales** (ventas, top productos, stock por categoría).
- **Líneas y Áreas temporales** (evolución de ingresos y movimientos en el tiempo).
- **Dona y Circular / Pastel** (distribución por método de pago y proporciones de stock).
- **Treemaps (Mapas de árbol)** (volumen y valorización del catálogo).
- **Dispersión, Cajas (Box Plots) e Histogramas** en el Explorador Gráfico Personalizado.

## ¿Puedo exportar los reportes a Excel o CSV?

Sí. En la pestaña **📥 Centro de Exportación** de Streamlit puedes descargar un libro completo de Excel (`.xlsx`) con hojas separadas para Ventas, Inventario y Movimientos, o descargar archivos `.csv` individuales con un clic.

## ¿Cómo recuerda el sistema si estaba en modo oscuro o claro?

La aplicación guarda automáticamente la preferencia en el archivo local `.startup_state.json` cada vez que accionas el interruptor animado de tema Día / Noche, recuperando el mismo modo al volver a abrir el programa.

## ¿Dónde está la lógica principal?

- `main.py`: entrada del programa y lanzador CLI
- `reporting/streamlit_reports.py`: dashboard de reportes interactivos con Streamlit y Plotly
- `core/`: lógica de negocio (inventario, POS, escáner)
- `ui/gui_ui.py`: interfaz gráfica con PyQt5
- `web/app.py`: rutas y API web con Flask
- `database/models.py`: modelos de datos SQLAlchemy

**Última actualización**: 26 de octubre de 2026
