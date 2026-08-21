"""
Interfaz de Terminal (CLI) para el sistema de inventario.
Proporciona un menú interactivo para:
- Gestión de inventario
- Punto de venta (POS)
- Reportes
"""

import logging
import os
from typing import Optional
from database.connection import SessionLocal, init_db
from database.models import Producto
from core.barcode_scanner import EscanerProducto
from core.inventory_manager import GestorInventario
from core.pos_manager import GestorPOS
from api.gtin_lookup import GTINBuscador
from config.settings import PRESENTACIONES, MONEDA

logger = logging.getLogger(__name__)

class InterfazTerminal:
    """Interfaz de línea de comandos"""
    
    def __init__(self):
        """Inicializa la interfaz de terminal"""
        self.db = SessionLocal()
        self.inventario = GestorInventario(self.db)
        self.pos = GestorPOS(self.db)
        self.escaneo = EscanerProducto()
        self.buscador = GTINBuscador()
        init_db()
    
    def limpiar_pantalla(self):
        """Limpia la pantalla"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def seleccionar_opcion(self, opciones, prompt="Selecciona una opción"):
        """Muestra opciones etiquetadas (a, b, c...) y retorna el valor seleccionado.

        `opciones` debe ser una lista de tuplas (clave, texto) o strings.
        Retorna el índice seleccionado (0-based) o None si se cancela.
        """
        # Normalizar opciones a lista de (clave, texto)
        items = []
        for o in opciones:
            if isinstance(o, tuple) and len(o) >= 2:
                items.append((o[0], o[1]))
            else:
                items.append((str(o), str(o)))

        letras = [chr(ord('a') + i) for i in range(len(items))]
        for i, (_, texto) in enumerate(items):
            print(f"{letras[i]}. {texto}")

        while True:
            choice = input(f"{prompt} ({'/'.join(letras)} / q para cancelar): ").strip().lower()
            if choice == 'q':
                return None
            if choice in letras:
                return letras.index(choice)
            # aceptar también índice numérico por compatibilidad
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    return idx
            print("Opción inválida. Intenta de nuevo (o pulsa q para cancelar).")
    
    def mostrar_menu_principal(self):
        """Muestra el menú principal"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("📦 SISTEMA DE INVENTARIO GENERAL".center(70))
        print("=" * 70)
        print("\n1. 📦 Gestión de Inventario")
        print("2. 🛒 Punto de Venta (POS)")
        print("3. 📊 Reportes")
        print("4. ⚙️  Configuración")
        print("5. 🚪 Salir")
        print("\n" + "=" * 70)
    
    def menu_inventario(self):
        """Menú de gestión de inventario"""
        while True:
            self.limpiar_pantalla()
            print("=" * 70)
            print("📦 GESTIÓN DE INVENTARIO".center(70))
            print("=" * 70)
            print("\n1. ➕ Registrar nuevo producto")
            print("2. 🔍 Buscar producto por GTIN")
            print("3. ➡️  Registrar entrada de stock")
            print("4. ⬅️  Registrar salida de stock")
            print("5. ⚠️  Ver productos con stock bajo")
            print("6. 📋 Historial de movimientos")
            print("7. ◀️  Volver al menú principal")
            print("\n" + "=" * 70)
            
            opcion = input("Selecciona una opción: ").strip()
            
            if opcion == "1":
                self.registrar_producto()
            elif opcion == "2":
                self.buscar_producto()
            elif opcion == "3":
                self.registrar_entrada()
            elif opcion == "4":
                self.registrar_salida()
            elif opcion == "5":
                self.ver_stock_bajo()
            elif opcion == "6":
                self.ver_historial()
            elif opcion == "7":
                break
            else:
                input("❌ Opción inválida. Presiona Enter...")
    
    def registrar_producto(self):
        """Registra un nuevo producto"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("➕ REGISTRAR NUEVO PRODUCTO".center(70))
        print("=" * 70)
        
        gtin = input("\n📱 Ingresa el GTIN (código de barras): ").strip()
        
        if not gtin:
            input("❌ GTIN no puede estar vacío. Presiona Enter...")
            return
        
        # Buscar información del producto
        print("\n🔍 Buscando información del producto...")
        info_api = self.buscador.buscar(gtin)
        
        if info_api["encontrado"]:
            print(f"\n✅ Información encontrada en {info_api['datos']['fuente']}")
            nombre = info_api['datos'].get('nombre', '')
            laboratorio = info_api['datos'].get('marca', '')
        else:
            print("\n⚠️ No se encontró información automática")
            nombre = input("Nombre del producto: ").strip()
            laboratorio = input("Laboratorio: ").strip()
        
        descripcion = input("Descripción (opcional): ").strip()
        
        # Registrar producto
        producto = self.inventario.registrar_producto(
            gtin=gtin,
            nombre=nombre,
            laboratorio=laboratorio,
            descripcion=descripcion
        )
        
        if producto:
            print(f"\n✅ Producto registrado exitosamente!")
            print(f"ID: {producto.id}")
            print(f"GTIN: {producto.gtin}")
            
            # Preguntar por presentaciones
            agregar_presentacion = input("\n¿Agregar presentación? (s/n): ").strip().lower()
            if agregar_presentacion == 's':
                self.agregar_presentacion_a_producto(producto.id)
        else:
            print("\n❌ Error al registrar producto")
        
        input("\nPresiona Enter para continuar...")
    
    def agregar_presentacion_a_producto(self, producto_id: int):
        """Agrega una presentación a un producto"""
        print("\n" + "=" * 70)
        print("PRESENTACIONES DISPONIBLES:")
        # Presentar opciones y permitir elegir con letras
        opciones = [(k, v['nombre']) for k, v in PRESENTACIONES.items()]
        idx = self.seleccionar_opcion(opciones, prompt="Selecciona tipo de presentación")
        if idx is None:
            print("Operación cancelada")
            return
        tipo_presentacion = opciones[idx][0]
        
        cantidad = int(input("Cantidad por envase: ") or "1")
        precio_unitario = float(input("Precio de costo unitario: ") or "0")
        precio_venta = float(input("Precio de venta: ") or "0")
        stock_inicial = int(input("Stock inicial: ") or "0")
        
        presentacion = self.inventario.agregar_presentacion(
            producto_id=producto_id,
            tipo_presentacion=tipo_presentacion,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            precio_venta=precio_venta,
            stock_inicial=stock_inicial
        )
        
        if presentacion:
            print(f"\n✅ Presentación agregada: {presentacion.tipo.value}")
    
    def buscar_producto(self):
        """Busca un producto por GTIN"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("🔍 BUSCAR PRODUCTO".center(70))
        print("=" * 70)
        
        gtin = input("\n📱 Escanea o ingresa el GTIN: ").strip()
        
        if not gtin:
            input("❌ GTIN no puede estar vacío. Presiona Enter...")
            return
        
        producto = self.inventario.obtener_producto_por_gtin(gtin)
        
        if producto:
            print(f"\n✅ PRODUCTO ENCONTRADO")
            print("=" * 70)
            print(f"Nombre: {producto.nombre}")
            print(f"GTIN: {producto.gtin}")
            print(f"Laboratorio: {producto.laboratorio}")
            print(f"Descripción: {producto.descripcion}")
            
            print("\nPRESENTACIONES:")
            for p in producto.presentaciones:
                print(f"  • {p.tipo.value}: {MONEDA}{p.precio_venta} - Stock: {p.stock_actual}")
        else:
            print(f"\n⚠️ Producto no encontrado: {gtin}")
            print("¿Deseas registrarlo? (s/n): ", end="")
            if input().strip().lower() == 's':
                self.registrar_producto()
        
        input("\nPresiona Enter para continuar...")
    
    def registrar_entrada(self):
        """Registra una entrada de stock"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("➡️  REGISTRAR ENTRADA DE STOCK".center(70))
        print("=" * 70)
        
        gtin = input("\n📱 Escanea o ingresa el GTIN: ").strip()
        producto = self.inventario.obtener_producto_por_gtin(gtin)
        
        if not producto:
            print(f"⚠️ Producto no encontrado: {gtin}")
            input("Presiona Enter...")
            return
        
        print(f"\n✅ Producto: {producto.nombre}")
        print("\nPRESENTACIONES:")
        opciones = [(p.id, f"{p.tipo.value} - Stock actual: {p.stock_actual}") for p in producto.presentaciones]
        idx = self.seleccionar_opcion(opciones, prompt="Selecciona presentación")
        if idx is None:
            print("Operación cancelada")
            input("\nPresiona Enter...")
            return
        presentacion = producto.presentaciones[idx]
        try:
            cantidad = int(input("Cantidad a entrar: "))
            razon = input("Razón (factura, compra, etc.): ").strip()
            referencia = input("Referencia (número de factura, etc.): ").strip()

            self.inventario.registrar_movimiento(
                producto_id=producto.id,
                presentacion_id=presentacion.id,
                tipo="entrada",
                cantidad=cantidad,
                razon=razon,
                referencia=referencia
            )

            print(f"✅ Entrada registrada: {cantidad} unidades")
        except ValueError:
            print("❌ Entrada inválida")

        input("\nPresiona Enter...")
    
    def registrar_salida(self):
        """Registra una salida de stock"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("⬅️  REGISTRAR SALIDA DE STOCK".center(70))
        print("=" * 70)
        
        gtin = input("\n📱 Escanea o ingresa el GTIN: ").strip()
        producto = self.inventario.obtener_producto_por_gtin(gtin)
        
        if not producto:
            print(f"⚠️ Producto no encontrado: {gtin}")
            input("Presiona Enter...")
            return
        
        print(f"\n✅ Producto: {producto.nombre}")
        print("\nPRESENTACIONES:")
        opciones = [(p.id, f"{p.tipo.value} - Stock actual: {p.stock_actual}") for p in producto.presentaciones]
        idx = self.seleccionar_opcion(opciones, prompt="Selecciona presentación")
        if idx is None:
            print("Operación cancelada")
            input("Presiona Enter...")
            return
        presentacion = producto.presentaciones[idx]
        try:
            cantidad = int(input("Cantidad a salir: "))

            if cantidad > presentacion.stock_actual:
                print(f"❌ Stock insuficiente. Stock disponible: {presentacion.stock_actual}")
            else:
                razon = input("Razón (ajuste, devolución, etc.): ").strip()

                self.inventario.registrar_movimiento(
                    producto_id=producto.id,
                    presentacion_id=presentacion.id,
                    tipo="salida",
                    cantidad=cantidad,
                    razon=razon
                )

                print(f"✅ Salida registrada: {cantidad} unidades")
        except ValueError:
            print("❌ Entrada inválida")

        input("\nPresiona Enter...")
    
    def ver_stock_bajo(self):
        """Muestra productos con stock bajo"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("⚠️  PRODUCTOS CON STOCK BAJO".center(70))
        print("=" * 70)
        
        productos_alerta = self.inventario.obtener_productos_stock_bajo()
        
        if productos_alerta:
            for p in productos_alerta:
                print(f"\n{p['nombre']} ({p['presentacion']})")
                print(f"  Stock: {p['stock_actual']} | Mínimo: {p['stock_minimo']}")
                print(f"  ⚠️  {p['urgencia']}")
        else:
            print("\n✅ No hay productos con stock bajo")
        
        input("\nPresiona Enter...")
    
    def ver_historial(self):
        """Muestra el historial de movimientos"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("📋 HISTORIAL DE MOVIMIENTOS".center(70))
        print("=" * 70)
        
        gtin = input("\n📱 Escanea o ingresa el GTIN: ").strip()
        producto = self.inventario.obtener_producto_por_gtin(gtin)
        
        if not producto:
            print(f"⚠️ Producto no encontrado: {gtin}")
        else:
            historial = self.inventario.historial_movimientos(producto.id)
            
            if historial:
                print(f"\n✅ Historial de: {producto.nombre}")
                print("-" * 70)
                for m in historial:
                    print(f"{m['fecha']}: {m['tipo'].upper()} - {m['cantidad']} unidades")
                    print(f"  Razón: {m['razon']}")
                    print(f"  Usuario: {m['usuario']}\n")
            else:
                print("\n⚠️ No hay movimientos registrados")
        
        input("Presiona Enter...")
    
    def menu_pos(self):
        """Menú del Punto de Venta"""
        while True:
            self.limpiar_pantalla()
            print("=" * 70)
            print("🛒 PUNTO DE VENTA (POS)".center(70))
            print("=" * 70)
            
            resumen = self.pos.carrito.obtener_resumen()
            print(f"\nCarrito: {resumen['cantidad_items']} items | Total: {MONEDA}{resumen['total']:.2f}")
            
            opciones = [
                ("agregar", "➕ Agregar producto"),
                ("eliminar", "🗑️  Eliminar producto"),
                ("ver", "📋 Ver carrito"),
                ("pagar", "💳 Procesar pago"),
                ("vaciar", "🗑️  Vaciar carrito"),
                ("volver", "◀️  Volver al menú principal"),
            ]
            print("\n" + "=" * 70)
            idx = self.seleccionar_opcion(opciones, prompt="Selecciona una opción")
            if idx is None:
                continue

            opcion = opciones[idx][0]
            if opcion == "agregar":
                self.agregar_a_carrito()
            elif opcion == "eliminar":
                self.eliminar_del_carrito()
            elif opcion == "ver":
                self.ver_carrito()
            elif opcion == "pagar":
                self.procesar_pago()
            elif opcion == "vaciar":
                self.pos.carrito.vaciar_carrito()
                print("✅ Carrito vaciado")
                input("Presiona Enter...")
            elif opcion == "volver":
                break
    
    def agregar_a_carrito(self):
        """Agrega un producto al carrito"""
        gtin = input("📱 Escanea o ingresa el GTIN: ").strip()
        producto = self.inventario.obtener_producto_por_gtin(gtin)
        
        if not producto:
            print(f"⚠️ Producto no encontrado: {gtin}")
            input("Presiona Enter...")
            return
        
        print(f"\n✅ Producto: {producto.nombre}")
        print("\nPRESENTACIONES:")
        opciones = [(p.id, f"{p.tipo.value} - {MONEDA}{p.precio_venta} (Stock: {p.stock_actual})") for p in producto.presentaciones]
        idx = self.seleccionar_opcion(opciones, prompt="Selecciona presentación")
        if idx is None:
            print("Operación cancelada")
            input("\nPresiona Enter...")
            return
        presentacion = producto.presentaciones[idx]
        try:
            cantidad = int(input("Cantidad: ") or "1")

            if cantidad > presentacion.stock_actual:
                print(f"❌ Stock insuficiente. Disponible: {presentacion.stock_actual}")
            else:
                self.pos.carrito.agregar_item(
                    producto_id=producto.id,
                    presentacion_id=presentacion.id,
                    cantidad=cantidad,
                    precio_unitario=presentacion.precio_venta
                )
                print(f"✅ {cantidad}x {presentacion.tipo.value} agregado al carrito")
        except ValueError:
            print("❌ Entrada inválida")

        input("\nPresiona Enter...")
    
    def ver_carrito(self):
        """Muestra el contenido del carrito"""
        self.limpiar_pantalla()
        items = self.pos.carrito.obtener_items()
        
        if not items:
            print("🛒 El carrito está vacío")
        else:
            print("=" * 70)
            print("🛒 CARRITO DE COMPRA".center(70))
            print("=" * 70)
            
            for item in items:
                print(f"\nProducto ID: {item['producto_id']}")
                print(f"Cantidad: {item['cantidad']}")
                print(f"Precio unitario: {MONEDA}{item['precio_unitario']:.2f}")
                print(f"Subtotal: {MONEDA}{item['subtotal']:.2f}")
            
            resumen = self.pos.carrito.obtener_resumen()
            print("\n" + "-" * 70)
            print(f"Subtotal: {MONEDA}{resumen['subtotal']:.2f}")
            print(f"TOTAL: {MONEDA}{resumen['total']:.2f}")
            print("=" * 70)
        
        input("\nPresiona Enter...")
    
    def eliminar_del_carrito(self):
        """Elimina un producto del carrito"""
        items = self.pos.carrito.obtener_items()
        
        if not items:
            print("🛒 El carrito está vacío")
            input("Presiona Enter...")
            return
        
        print("\nProductos en el carrito:")
        opciones = []
        for item in items:
            opciones.append((item['presentacion_id'], f"Producto {item['producto_id']} - Cantidad: {item['cantidad']}"))
        idx = self.seleccionar_opcion(opciones, prompt="Selecciona producto a eliminar")
        if idx is None:
            print("Operación cancelada")
            input("Presiona Enter...")
            return
        presentacion_id = opciones[idx][0]
        if self.pos.carrito.eliminar_item(presentacion_id):
            print("✅ Producto eliminado del carrito")
        else:
            print("❌ Error al eliminar")
        
        input("\nPresiona Enter...")
    
    def procesar_pago(self):
        """Procesa el pago de una venta"""
        resumen = self.pos.carrito.obtener_resumen()
        
        if resumen['cantidad_items'] == 0:
            print("🛒 El carrito está vacío")
            input("Presiona Enter...")
            return
        
        self.limpiar_pantalla()
        print("=" * 70)
        print("💳 PROCESAR PAGO".center(70))
        print("=" * 70)
        
        print(f"\nTotal a pagar: {MONEDA}{resumen['total']:.2f}")
        print("\nMétodos de pago:")
        opciones_pago = [("efectivo", "Efectivo"), ("tarjeta", "Tarjeta"), ("transferencia", "Transferencia")]
        idx = self.seleccionar_opcion(opciones_pago, prompt="Selecciona método de pago")
        if idx is None:
            print("Operación cancelada, usando efectivo por defecto")
            metodo = "efectivo"
        else:
            metodo = opciones_pago[idx][0]
        
        usuario = input("Nombre del cajero: ").strip() or "Sistema"
        notas = input("Notas (opcional): ").strip()
        
        numero_ticket = self.pos.generar_numero_ticket()
        
        venta = self.pos.crear_venta(
            numero_ticket=numero_ticket,
            metodo_pago=metodo,
            usuario=usuario,
            notas=notas
        )
        
        if venta:
            self.limpiar_pantalla()
            print("=" * 70)
            print("✅ VENTA COMPLETADA".center(70))
            print("=" * 70)
            print(f"\nNúmero de ticket: {venta.numero_ticket}")
            print(f"Total: {MONEDA}{venta.total:.2f}")
            print(f"Método de pago: {venta.metodo_pago}")
            print(f"Fecha: {venta.fecha}")
            print("\n¡Gracias por su compra!")
            print("=" * 70)
        else:
            print("❌ Error al procesar la venta")
        
        input("\nPresiona Enter...")
    
    def menu_reportes(self):
        """Menú de reportes"""
        self.limpiar_pantalla()
        print("=" * 70)
        print("📊 REPORTES".center(70))
        print("=" * 70)
        
        reporte = self.inventario.reporte_general()
        print(f"\nFecha: {reporte['fecha']}")
        print(f"Total de productos: {reporte['total_productos']}")
        print(f"Stock total: {reporte['total_stock']} unidades")
        print(f"Valor del inventario: {MONEDA}{reporte['valor_inventario']:.2f}")
        print(f"Productos sin stock: {reporte['productos_sin_stock']}")
        print(f"Productos en alerta: {reporte['productos_alerta']}")
        
        input("\nPresiona Enter...")
    
    def ejecutar(self):
        """Ejecuta el menú principal"""
        try:
            while True:
                self.mostrar_menu_principal()
                opciones = [
                    ("inventario", "📦 Gestión de Inventario"),
                    ("pos", "🛒 Punto de Venta (POS)"),
                    ("reportes", "📊 Reportes"),
                    ("configuracion", "⚙️  Configuración"),
                    ("salir", "🚪 Salir"),
                ]
                idx = self.seleccionar_opcion(opciones, prompt="Selecciona una opción")
                if idx is None:
                    # cancelar: volver a mostrar menú
                    continue

                opcion = opciones[idx][0]
                if opcion == "inventario":
                    self.menu_inventario()
                elif opcion == "pos":
                    self.menu_pos()
                elif opcion == "reportes":
                    self.menu_reportes()
                elif opcion == "configuracion":
                    self.limpiar_pantalla()
                    print("⚙️  Configuración (En desarrollo)")
                    input("Presiona Enter...")
                elif opcion == "salir":
                    print("\n👋 ¡Hasta luego!")
                    break
        
        except KeyboardInterrupt:
            print("\n\n👋 Aplicación interrumpida")
        finally:
            self.db.close()


def ejecutar_interfaz_terminal():
    """Punto de entrada para la interfaz de terminal"""
    interfaz = InterfazTerminal()
    interfaz.ejecutar()
