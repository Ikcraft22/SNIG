# Preguntas frecuentes

## ¿Cómo inicio el proyecto?

Ejecuta:

```bash
python main.py
```

Luego elige una de las opciones del menú:

- 1 para terminal
- 2 para GUI
- 3 para web

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

En la pestaña POS puedes escribir o escanear un GTIN y presionar Enter para agregar el producto directamente al carrito. Si se repite el mismo producto 10 veces seguidas, el sistema muestra una alerta de compra masiva.

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
MYSQL_DATABASE=inventario_medicamentos
```

## ¿La base de datos se crea sola?

Sí. Al iniciar la aplicación se inicializa la estructura de tablas automáticamente.

## ¿Dónde está la lógica principal?

- main.py: entrada del programa
- core/: lógica de negocio
- web/app.py: rutas y API web
- database/models.py: modelos de datos

**Última actualización**: 13 de julio de 2026
