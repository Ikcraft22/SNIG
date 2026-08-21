# CHANGELOG - Historial de Cambios

## [1.0.3] - 11 de agosto de 2026

### Actualizado
- ✅ Se mejoró la distribución de botones y pestañas para una interfaz más amplia y táctil
- ✅ La tabla de inventario se adaptó al ancho de la ventana y mantiene proporciones más legibles
- ✅ Se ampliaron los botones principales del POS: eliminar, vaciar y procesar pago
- ✅ Se eliminó el paso de nombre de cajero al procesar el cobro
- ✅ El método de pago ahora se maneja con selección numérica: 1, 2, 3
- ✅ La pestaña de inventario fue reformada con una composición más clara y funcional
- ✅ El sistema detecta automáticamente si el sistema está en modo oscuro y adapta la parte superior de la UI
- ✅ La aplicación mantiene un estilo más uniforme y amigable para pantallas grandes y de uso diario

---

## [1.0.2] - 2 de agosto de 2026

### Actualizado
- ✅ UI del POS mejorada para escaneo rápido y uso táctil
- ✅ El campo GTIN del POS recibe foco automáticamente
- ✅ Agregado el flujo directo de agregar productos al carrito por Enter
- ✅ Implementada alerta de compra masiva tras 10 repeticiones seguidas
- ✅ UI de inventario adaptada para pantallas táctiles y botones de acción más accesibles
- ✅ La ventana principal inicia maximizada

---

## [1.0.1] - 13 de julio de 2026

### Actualizado
- ✅ Documentación alineada con el estado real del proyecto
- ✅ Se reflejó el uso de SQLite como base de datos por defecto
- ✅ Se documentaron las interfaces terminal, GUI y web
- ✅ Se añadieron instrucciones más claras de instalación y ejecución
- ✅ Se actualizaron los ejemplos de configuración para .env

### Estado actual del sistema
- Sistema funcional para inventario y ventas
- Soporte para productos, presentaciones, movimientos y ventas
- API web básica disponible con Flask
- Menú principal para elegir interfaz

---

## [1.0.0] - 31 de mayo de 2025

### Agregado
- sistema inicial de inventario y punto de venta
- soporte para GTIN y búsquedas externas
- modelos de base de datos con SQLAlchemy
- módulos para inventario, POS y escaneo
- documentación inicial del proyecto

---

## Próximas mejoras sugeridas

- autenticación de usuarios
- reportes más avanzados
- exportación a Excel/PDF
- mejores validaciones de negocio
- tests automáticos

**Última actualización**: 11 de agosto de 2026
**Versión actual**: 1.0.3
**Estado**: funcional
