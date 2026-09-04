# Sistema de Inventario

Documentación actualizada el 11 de agosto de 2026.

## Resumen del proyecto

Este proyecto es un sistema local de inventario y punto de venta para negocios que necesitan gestionar stock, ventas y reportes con una interfaz pensada para uso rápido y táctil.

Actualmente incluye:

- gestión de productos y presentaciones
- control de stock por entradas, salidas y ajustes
- punto de venta con escaneo rápido por GTIN
- carrito de compra y cálculo automático de totales
- reportes interactivos avanzados con Streamlit y Plotly (gráficos de barras, líneas, áreas, dona/pastel, treemaps, dispersión y exportación a Excel/CSV)
- interfaz gráfica con PyQt5 y acceso en un clic a los reportes
- flujo de pago simplificado con selección numérica
- modo oscuro

## Estado actual

Versión actual: 1.0.3
Estado: funcional y listo para uso local con GUI

## Características principales de la GUI

La interfaz gráfica actual incluye varias mejoras orientadas a rapidez y ergonomía:

- pestañas de tamaño grande y distribuidas uniformemente
- tabla de inventario responsive y adaptada al ancho de la ventana
- botones de acción más grandes para uso táctil
- búsqueda rápida de productos con lupa
- agregado directo de artículos al carrito desde el POS
- flujo de cobro sin pedir nombre de cajero
- método de pago con selección numérica:
  - 1 = Efectivo
  - 2 = Tarjeta
  - 3 = Transferencia
- botón de pago, vaciar carrito y eliminar producto con tamaños ampliados

## Requisitos

- Python 3.10 o superior
- pip
- SQLite (incluido con Python)
- PyQt5 para la interfaz gráfica
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

```bash
python main.py
```

La aplicación inicia por defecto la interfaz gráfica principal.

## Uso recomendado

### Interfaz gráfica

Desde la app se presentan estas pestañas principales:

- Inventario
- POS
- Reportes
- Logs (oculto por defecto y accesible desde reportes o acciones avanzadas)

### Flujo de POS

- escribe o escanea el GTIN en el campo del POS
- presiona Enter para agregar el producto al carrito
- revisa los artículos agregados
- pulsa Pago
- selecciona el método de pago por número:
  - 1 para Efectivo
  - 2 para Tarjeta
  - 3 para Transferencia

### Flujo de inventario

- busca productos por texto o GTIN
- agrega nuevos productos o presentaciones
- gestiona movimientos de stock
- revisa en la tabla la información principal del catálogo

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
- exportación a Excel/PDF
- reportes más avanzados
- validaciones adicionales de negocio
- pruebas automáticas
- mejoras de sincronización y escalabilidad

## Agradecimientos

- [opensource-coding/Dark-Light-Mode-Switch](https://github.com/opensource-coding/Dark-Light-Mode-Switch) — por el componente de interruptor de modo oscuro/claro utilizado en la interfaz web del proyecto.

---

Última actualización: 11 de agosto de 2026
Versión: 1.0.3
