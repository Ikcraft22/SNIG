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

1. ejecuta la aplicación
2. selecciona la opción 3
3. abre en el navegador la URL:

```text
http://localhost:5000
```

## ¿Qué pasa si la GUI no inicia?

Normalmente es por falta de PyQt5. Instálalo con:

```bash
pip install PyQt5
```

## ¿Cómo funciona el POS?

En la sección **Punto de venta** puedes escribir o escanear un GTIN y presionar Enter para agregar el producto directamente al carrito. Se puede pagar en Efectivo o por Transferencia; los botones también aceptan las teclas `1` y `2`. Si se repite el mismo producto 10 veces seguidas, el sistema muestra una alerta de compra masiva.

## ¿Cómo registro un proveedor y le asigno productos?

Abre **Proveedores** desde la navegación lateral, pulsa **Nuevo proveedor** y completa el nombre y los datos de contacto disponibles. Después selecciona al proveedor, elige **Asignar productos**, busca por nombre o GTIN y marca los productos que suministra. La columna **Proveedor** del inventario muestra las asignaciones. Eliminar al proveedor no elimina los productos.

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

Sí. Al iniciar la aplicación se inicializa la estructura de tablas automáticamente.

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

**Última actualización**: 23 de octubre de 2026
