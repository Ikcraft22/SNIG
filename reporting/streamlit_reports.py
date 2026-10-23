"""
Módulo de Reportes y Visualización Avanzada con Streamlit y Plotly.
Proporciona un dashboard interactivo con múltiples tipos de gráficas:
- Métricas KPI en tiempo real
- Reportes de Ventas (Evolución temporal, Métodos de pago, Top productos, Desglose por cajero)
- Reportes de Inventario (Stock actual, Valorización, Alertas de stock bajo/crítico)
- Reportes de Movimientos de Inventario (Entradas vs Salidas vs Ajustes)
- Explorador Gráfico Personalizado (Gráficos de Barras, Líneas, Áreas, Pastel/Dona, Treemaps, Dispersión, Histogramas)
- Centro de Exportación a Excel y CSV
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

from database.connection import SessionLocal, init_db
from database.models import (
    EstadoMovimiento,
    MovimientoInventario,
    Presentacion,
    Producto,
    Usuario,
    Venta,
    VentaItem,
)
from config.settings import MONEDA
from reporting.pdf_export import generar_reporte_pdf


# ==============================================================================
# FUNCIONES DE PREPARACIÓN DE DATOS
# ==============================================================================

def preparar_datos_dashboard(productos: List[Dict[str, Any]], ventas: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """
    Procesa y estructura los datos tabulares de productos y ventas para el dashboard.

    Args:
        productos: Lista de productos con 'nombre' y 'stock_total' (o 'stock').
        ventas: Lista de ventas con 'metodo_pago' y 'total'.

    Returns:
        Diccionario con DataFrames:
        - 'stock': columnas ['Producto', 'Stock'] ordenado descendentemente por Stock.
        - 'ventas': columnas ['MetodoPago', 'Total'] agrupado por MetodoPago y ordenado por Total descendente.
    """
    if productos:
        filas_stock = [
            {"Producto": p.get("nombre", "Sin nombre"), "Stock": p.get("stock_total", p.get("stock", 0))}
            for p in productos
        ]
        df_stock = pd.DataFrame(filas_stock)
        df_stock = df_stock.sort_values(by="Stock", ascending=False).reset_index(drop=True)
    else:
        df_stock = pd.DataFrame(columns=["Producto", "Stock"])

    if ventas:
        filas_ventas = [
            {"MetodoPago": v.get("metodo_pago", "desconocido"), "Total": float(v.get("total", 0.0))}
            for v in ventas
        ]
        df_ventas = pd.DataFrame(filas_ventas)
        df_ventas = df_ventas.groupby("MetodoPago", as_index=False)["Total"].sum()
        df_ventas = df_ventas.sort_values(by="Total", ascending=False).reset_index(drop=True)
    else:
        df_ventas = pd.DataFrame(columns=["MetodoPago", "Total"])

    return {
        "stock": df_stock,
        "ventas": df_ventas
    }


# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==============================================================================

def configurar_pagina():
    """Configura el tema y título de la página Streamlit."""
    st.set_page_config(
        page_title="Dashboard de Inventario & Reportes",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        :focus-visible {
            outline: 3px solid #b45309 !important;
            outline-offset: 3px !important;
        }
        button, input, select, textarea {
            min-height: 2.75rem;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stWidgetLabel"] {
            line-height: 1.5;
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            color: #64748b;
            font-size: 1.05rem;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 0.85rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 4px;
        }
        .metric-subtitle {
            font-size: 0.85rem;
            color: #166534;
            margin-top: 4px;
        }
        .badge-danger {
            background-color: #fee2e2;
            color: #991b1b;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        .badge-warning {
            background-color: #fef3c7;
            color: #92400e;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        .badge-success {
            background-color: #dcfce7;
            color: #166534;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def mostrar_grafica_accesible(
    figura: go.Figure,
    datos: pd.DataFrame,
    clave: str,
) -> None:
    """Muestra una gráfica con controles de teclado y una alternativa tabular."""
    figura.update_layout(
        font=dict(size=14),
        title_font_size=18,
        margin=dict(l=28, r=24, t=56, b=32),
    )
    st.plotly_chart(
        figura,
        use_container_width=True,
        config={"displayModeBar": True, "displaylogo": False, "scrollZoom": False},
    )
    with st.expander(f"Ver datos de la gráfica: {clave}", expanded=False):
        st.dataframe(datos, use_container_width=True, hide_index=True)


# ==============================================================================
# CARGA Y PROCESAMIENTO DE DATOS DESDE BASE DE DATOS
# ==============================================================================

def obtener_sesion_db() -> Session:
    """Retorna una sesión de SQLAlchemy."""
    return SessionLocal()


def cargar_datos_completos() -> Dict[str, pd.DataFrame]:
    """Carga todas las tablas relacionales y las estructura en DataFrames optimizados."""
    init_db()
    db = obtener_sesion_db()
    try:
        # 1. Productos y Presentaciones
        productos = db.query(Producto).all()
        prod_rows = []
        pres_rows = []

        for p in productos:
            total_stock_p = 0
            valor_costo_p = 0.0
            valor_venta_p = 0.0

            for pres in p.presentaciones:
                stock = int(pres.stock_actual or 0)
                costo = round(pres.precio_unitario or 0.0)
                venta = round(pres.precio_venta or 0.0)
                minimo = int(pres.stock_minimo or 0)

                total_stock_p += stock
                valor_costo_p += stock * costo
                valor_venta_p += stock * venta

                # Estado de stock
                if stock == 0:
                    estado_stock = "Sin Stock"
                elif stock <= minimo:
                    estado_stock = "Crítico / Bajo"
                else:
                    estado_stock = "Normal"

                pres_rows.append({
                    "PresentacionID": pres.id,
                    "ProductoID": p.id,
                    "GTIN": p.gtin,
                    "Producto": p.nombre,
                    "Laboratorio": p.laboratorio or "Sin especificar",
                    "TipoPresentacion": pres.tipo.value if hasattr(pres.tipo, "value") else str(pres.tipo),
                    "CantidadPorEnvase": pres.cantidad,
                    "PrecioCosto": costo,
                    "PrecioVenta": venta,
                    "MargenUnitario": round(venta - costo),
                    "MargenPorcentaje": round(((venta - costo) / venta * 100), 2) if venta > 0 else 0.0,
                    "StockActual": stock,
                    "StockMinimo": minimo,
                    "EstadoStock": estado_stock,
                    "ValorTotalCosto": round(stock * costo),
                    "ValorTotalVenta": round(stock * venta),
                })

            prod_rows.append({
                "ProductoID": p.id,
                "GTIN": p.gtin,
                "Nombre": p.nombre,
                "Laboratorio": p.laboratorio or "Sin especificar",
                "PrincipioActivo": p.principio_activo or "N/A",
                "TotalStock": total_stock_p,
                "ValorInventarioCosto": round(valor_costo_p),
                "ValorInventarioVenta": round(valor_venta_p),
                "TotalPresentaciones": len(p.presentaciones),
                "FechaCreacion": p.fecha_creacion,
            })

        df_productos = pd.DataFrame(prod_rows) if prod_rows else pd.DataFrame(columns=[
            "ProductoID", "GTIN", "Nombre", "Laboratorio", "PrincipioActivo",
            "TotalStock", "ValorInventarioCosto", "ValorInventarioVenta", "TotalPresentaciones", "FechaCreacion"
        ])

        df_presentaciones = pd.DataFrame(pres_rows) if pres_rows else pd.DataFrame(columns=[
            "PresentacionID", "ProductoID", "GTIN", "Producto", "Laboratorio",
            "TipoPresentacion", "CantidadPorEnvase", "PrecioCosto", "PrecioVenta",
            "MargenUnitario", "MargenPorcentaje", "StockActual", "StockMinimo",
            "EstadoStock", "ValorTotalCosto", "ValorTotalVenta"
        ])

        # 2. Ventas y VentaItems
        ventas = db.query(Venta).all()
        ventas_rows = []
        items_rows = []

        for v in ventas:
            fecha_v = v.fecha if v.fecha else datetime.now()
            metodo = str(v.metodo_pago or "Efectivo").capitalize()
            usuario = str(v.usuario or "Cajero").capitalize()
            total_v = round(v.total or 0.0)

            ventas_rows.append({
                "VentaID": v.id,
                "Ticket": v.numero_ticket,
                "FechaHora": fecha_v,
                "Fecha": fecha_v.date(),
                "Hora": fecha_v.strftime("%H:%M"),
                "DiaSemana": fecha_v.strftime("%A"),
                "Mes": fecha_v.strftime("%Y-%m"),
                "MetodoPago": metodo,
                "Usuario": usuario,
                "Total": total_v,
                "Subtotal": round(v.subtotal or total_v),
                "CantidadItems": len(v.items),
            })

            for item in v.items:
                prod_obj = getattr(item, "producto", None)
                prod_nombre = prod_obj.nombre if prod_obj else f"Prod #{item.producto_id}"
                pres_obj = getattr(item, "presentacion", None)
                pres_tipo = pres_obj.tipo.value if (pres_obj and hasattr(pres_obj.tipo, "value")) else "unidad"
                cant = int(item.cantidad or 0)
                precio_u = round(item.precio_unitario or 0.0)
                subt = round(item.subtotal or (cant * precio_u))

                items_rows.append({
                    "ItemID": item.id,
                    "VentaID": v.id,
                    "Ticket": v.numero_ticket,
                    "FechaHora": fecha_v,
                    "Fecha": fecha_v.date(),
                    "ProductoID": item.producto_id,
                    "Producto": prod_nombre,
                    "Presentacion": pres_tipo,
                    "Cantidad": cant,
                    "PrecioUnitario": precio_u,
                    "Subtotal": subt,
                    "MetodoPago": metodo,
                    "Usuario": usuario,
                })

        df_ventas = pd.DataFrame(ventas_rows) if ventas_rows else pd.DataFrame(columns=[
            "VentaID", "Ticket", "FechaHora", "Fecha", "Hora", "DiaSemana", "Mes",
            "MetodoPago", "Usuario", "Total", "Subtotal", "CantidadItems"
        ])
        if not df_ventas.empty:
            df_ventas["Fecha"] = pd.to_datetime(df_ventas["Fecha"])
            df_ventas["FechaHora"] = pd.to_datetime(df_ventas["FechaHora"])

        df_items = pd.DataFrame(items_rows) if items_rows else pd.DataFrame(columns=[
            "ItemID", "VentaID", "Ticket", "FechaHora", "Fecha", "ProductoID",
            "Producto", "Presentacion", "Cantidad", "PrecioUnitario", "Subtotal", "MetodoPago", "Usuario"
        ])
        if not df_items.empty:
            df_items["Fecha"] = pd.to_datetime(df_items["Fecha"])

        # 3. Movimientos de Inventario
        movimientos = db.query(MovimientoInventario).all()
        mov_rows = []
        for m in movimientos:
            fecha_m = m.fecha if m.fecha else datetime.now()
            p_nom = m.producto.nombre if m.producto else f"Prod #{m.producto_id}"
            tipo_m = m.tipo_movimiento.value if hasattr(m.tipo_movimiento, "value") else str(m.tipo_movimiento)

            mov_rows.append({
                "MovimientoID": m.id,
                "FechaHora": fecha_m,
                "Fecha": fecha_m.date(),
                "ProductoID": m.producto_id,
                "Producto": p_nom,
                "TipoMovimiento": tipo_m.capitalize(),
                "Cantidad": int(m.cantidad or 0),
                "Razon": m.razon or "Sin razón",
                "Usuario": m.usuario or "Sistema",
                "Referencia": m.referencia_externa or "-",
            })

        df_movimientos = pd.DataFrame(mov_rows) if mov_rows else pd.DataFrame(columns=[
            "MovimientoID", "FechaHora", "Fecha", "ProductoID", "Producto",
            "TipoMovimiento", "Cantidad", "Razon", "Usuario", "Referencia"
        ])
        if not df_movimientos.empty:
            df_movimientos["Fecha"] = pd.to_datetime(df_movimientos["Fecha"])

        return {
            "productos": df_productos,
            "presentaciones": df_presentaciones,
            "ventas": df_ventas,
            "items": df_items,
            "movimientos": df_movimientos,
        }
    finally:
        db.close()


# ==============================================================================
# COMPONENTES DE FILTROS EN BARRA LATERAL
# ==============================================================================

def render_sidebar_filtros(datos: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Genera los controles interactivos de filtrado en la barra lateral."""
    st.sidebar.image("https://img.icons8.com/fluency/96/combo-chart.png", width=70)
    st.sidebar.title("Filtros Globales")
    st.sidebar.markdown("Personaliza los datos y reportes a continuación:")

    df_ventas = datos["ventas"]
    df_presentaciones = datos["presentaciones"]

    # 1. Filtro de Rango de Fechas
    st.sidebar.subheader("📅 Período de Análisis")
    periodo_opcion = st.sidebar.selectbox(
        "Rango predefinido:",
        ["Todo el Historial", "Hoy", "Últimos 7 Días", "Últimos 30 Días", "Este Mes", "Rango Personalizado"],
        index=0,
    )

    hoy = datetime.now().date()
    fecha_inicio = hoy - timedelta(days=365)
    fecha_fin = hoy

    if periodo_opcion == "Hoy":
        fecha_inicio = hoy
        fecha_fin = hoy
    elif periodo_opcion == "Últimos 7 Días":
        fecha_inicio = hoy - timedelta(days=7)
        fecha_fin = hoy
    elif periodo_opcion == "Últimos 30 Días":
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy
    elif periodo_opcion == "Este Mes":
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy
    elif periodo_opcion == "Rango Personalizado":
        rango = st.sidebar.date_input(
            "Selecciona rango de fechas:",
            value=(hoy - timedelta(days=30), hoy),
        )
        if isinstance(rango, (list, tuple)) and len(rango) == 2:
            fecha_inicio, fecha_fin = rango[0], rango[1]
        elif isinstance(rango, (list, tuple)) and len(rango) == 1:
            fecha_inicio = fecha_fin = rango[0]

    # 2. Filtro por Método de Pago
    metodos_disponibles = ["Todos"]
    if not df_ventas.empty and "MetodoPago" in df_ventas.columns:
        metodos_disponibles += sorted(df_ventas["MetodoPago"].dropna().unique().tolist())
    metodo_seleccionado = st.sidebar.selectbox("💳 Método de pago:", metodos_disponibles)

    # 3. Filtro por Productos
    productos_disponibles = ["Todos"]
    if not df_presentaciones.empty and "Producto" in df_presentaciones.columns:
        productos_disponibles += sorted(df_presentaciones["Producto"].dropna().unique().tolist())
    producto_seleccionado = st.sidebar.selectbox("📦 Producto específico:", productos_disponibles)

    # 4. Umbral de alerta de stock
    st.sidebar.subheader("⚙️ Configuración")
    umbral_alerta = st.sidebar.slider("Umbral Stock Crítico (Unidades):", min_value=1, max_value=50, value=10)

    # Botón de refrescar
    if st.sidebar.button("🔄 Recargar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    return {
        "periodo_opcion": periodo_opcion,
        "fecha_inicio": pd.to_datetime(fecha_inicio),
        "fecha_fin": pd.to_datetime(fecha_fin) + pd.Timedelta(days=1, microseconds=-1),
        "metodo_pago": metodo_seleccionado,
        "producto": producto_seleccionado,
        "umbral_alerta": umbral_alerta,
    }


def aplicar_filtros(datos: Dict[str, pd.DataFrame], filtros: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Aplica los filtros seleccionados a todos los DataFrames."""
    df_ventas = datos["ventas"].copy()
    df_items = datos["items"].copy()
    df_presentaciones = datos["presentaciones"].copy()
    df_productos = datos["productos"].copy()
    df_movimientos = datos["movimientos"].copy()

    # Filtro de fechas en ventas
    if not df_ventas.empty and "Fecha" in df_ventas.columns and filtros["periodo_opcion"] != "Todo el Historial":
        df_ventas = df_ventas[
            (df_ventas["Fecha"] >= filtros["fecha_inicio"]) & (df_ventas["Fecha"] <= filtros["fecha_fin"])
        ]

    # Filtro de método de pago
    if filtros["metodo_pago"] != "Todos" and not df_ventas.empty:
        df_ventas = df_ventas[df_ventas["MetodoPago"] == filtros["metodo_pago"]]

    # Filtro de items según ventas filtradas
    if not df_items.empty and not df_ventas.empty:
        df_items = df_items[df_items["VentaID"].isin(df_ventas["VentaID"])]
    elif df_ventas.empty and not df_items.empty and filtros["periodo_opcion"] != "Todo el Historial":
        df_items = df_items.iloc[0:0]

    # Filtro por producto
    if filtros["producto"] != "Todos":
        if not df_presentaciones.empty:
            df_presentaciones = df_presentaciones[df_presentaciones["Producto"] == filtros["producto"]]
        if not df_productos.empty:
            df_productos = df_productos[df_productos["Nombre"] == filtros["producto"]]
        if not df_items.empty:
            df_items = df_items[df_items["Producto"] == filtros["producto"]]
        if not df_movimientos.empty:
            df_movimientos = df_movimientos[df_movimientos["Producto"] == filtros["producto"]]

    # Actualizar estado de stock con el umbral personalizado
    if not df_presentaciones.empty:
        def categorizar(row):
            if row["StockActual"] == 0:
                return "Sin Stock"
            elif row["StockActual"] <= filtros["umbral_alerta"] or row["StockActual"] <= row["StockMinimo"]:
                return "Crítico / Bajo"
            return "Normal"

        df_presentaciones["EstadoStock"] = df_presentaciones.apply(categorizar, axis=1)

    return {
        "ventas": df_ventas,
        "items": df_items,
        "presentaciones": df_presentaciones,
        "productos": df_productos,
        "movimientos": df_movimientos,
    }


# ==============================================================================
# TARJETAS DE MÉTRICAS PRINCIPALES (KPIS)
# ==============================================================================

def render_kpis_principales(datos: Dict[str, pd.DataFrame]):
    """Renderiza tarjetas KPI estilizadas con métricas clave."""
    df_ventas = datos["ventas"]
    df_presentaciones = datos["presentaciones"]

    total_ingresos = df_ventas["Total"].sum() if not df_ventas.empty else 0.0
    cant_ventas = len(df_ventas) if not df_ventas.empty else 0
    ticket_promedio = round(total_ingresos / cant_ventas) if cant_ventas > 0 else 0

    total_unidades_stock = df_presentaciones["StockActual"].sum() if not df_presentaciones.empty else 0
    valor_inventario_costo = df_presentaciones["ValorTotalCosto"].sum() if not df_presentaciones.empty else 0.0
    valor_inventario_venta = df_presentaciones["ValorTotalVenta"].sum() if not df_presentaciones.empty else 0.0

    alertas_stock = len(df_presentaciones[df_presentaciones["EstadoStock"].isin(["Sin Stock", "Crítico / Bajo"])]) if not df_presentaciones.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">💰 Total Ventas</div>
                <div class="metric-value">{MONEDA}{total_ingresos:,.0f}</div>
                <div class="metric-subtitle">🛒 {cant_ventas} transacciones</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">🧾 Ticket Promedio</div>
                <div class="metric-value">{MONEDA}{ticket_promedio:,.0f}</div>
                <div class="metric-subtitle">por compra</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">📦 Total en Stock</div>
                <div class="metric-value">{total_unidades_stock:,}</div>
                <div class="metric-subtitle">unidades físicas</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">🏷️ Valor de Inventario</div>
                <div class="metric-value">{MONEDA}{valor_inventario_venta:,.0f}</div>
                <div class="metric-subtitle">Costo: {MONEDA}{valor_inventario_costo:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c5:
        color_badge = "badge-danger" if alertas_stock > 0 else "badge-success"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">⚠️ Stock en Alerta</div>
                <div class="metric-value">{alertas_stock}</div>
                <div class="metric-subtitle"><span class="{color_badge}">{'Requiere reposición' if alertas_stock > 0 else 'Stock óptimo'}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# PESTAÑA 1: REPORTES Y GRÁFICAS DE VENTAS
# ==============================================================================

def render_modulo_ventas(datos: Dict[str, pd.DataFrame]):
    """Renderiza gráficos interactivos y tablas de análisis de ventas."""
    st.subheader("📈 Análisis de Ventas y Facturación")

    df_ventas = datos["ventas"]
    df_items = datos["items"]

    if df_ventas.empty:
        st.info("ℹ️ No hay registros de ventas para los filtros seleccionados.")
        return

    # Controles de visualización
    c_tipo, c_agrup = st.columns([1, 1])
    with c_tipo:
        tipo_grafico_tiempo = st.radio(
            "Tipo de gráfica temporal:",
            ["Líneas", "Áreas", "Barras"],
            horizontal=True,
            key="tipo_graf_ventas",
        )
    with c_agrup:
        agrupacion_tiempo = st.selectbox(
            "Agrupar ventas por:",
            ["Día", "Hora del Día", "Día de la Semana", "Mes"],
            index=0,
            key="agrup_ventas",
        )

    col_izq, col_der = st.columns([3, 2])

    with col_izq:
        # Preparación de datos temporales
        if agrupacion_tiempo == "Día":
            df_tiempo = df_ventas.groupby("Fecha").agg(
                TotalVentas=("Total", "sum"),
                CantidadVentas=("Total", "count")
            ).reset_index()
            x_col = "Fecha"
            titulo_grafico = "Evolución Diaria de Ventas"
        elif agrupacion_tiempo == "Hora del Día":
            df_tiempo = df_ventas.groupby("Hora").agg(
                TotalVentas=("Total", "sum"),
                CantidadVentas=("Total", "count")
            ).reset_index()
            x_col = "Hora"
            titulo_grafico = "Ventas por Franja Horaria"
        elif agrupacion_tiempo == "Día de la Semana":
            dias_orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            df_tiempo = df_ventas.groupby("DiaSemana").agg(
                TotalVentas=("Total", "sum"),
                CantidadVentas=("Total", "count")
            ).reset_index()
            df_tiempo["DiaSemana"] = pd.Categorical(df_tiempo["DiaSemana"], categories=dias_orden, ordered=True)
            df_tiempo = df_tiempo.sort_values("DiaSemana")
            x_col = "DiaSemana"
            titulo_grafico = "Ventas por Día de la Semana"
        else:
            df_tiempo = df_ventas.groupby("Mes").agg(
                TotalVentas=("Total", "sum"),
                CantidadVentas=("Total", "count")
            ).reset_index()
            x_col = "Mes"
            titulo_grafico = "Evolución Mensual de Ventas"

        # Renderizar gráfica según selección
        if tipo_grafico_tiempo == "Líneas":
            fig_tiempo = px.line(
                df_tiempo,
                x=x_col,
                y="TotalVentas",
                markers=True,
                title=f"<b>{titulo_grafico}</b> ({MONEDA})",
                color_discrete_sequence=["#2563eb"],
                labels={"TotalVentas": f"Total ({MONEDA})", x_col: agrupacion_tiempo},
            )
        elif tipo_grafico_tiempo == "Áreas":
            fig_tiempo = px.area(
                df_tiempo,
                x=x_col,
                y="TotalVentas",
                title=f"<b>{titulo_grafico}</b> ({MONEDA})",
                color_discrete_sequence=["#3b82f6"],
                labels={"TotalVentas": f"Total ({MONEDA})", x_col: agrupacion_tiempo},
            )
        else:
            fig_tiempo = px.bar(
                df_tiempo,
                x=x_col,
                y="TotalVentas",
                title=f"<b>{titulo_grafico}</b> ({MONEDA})",
                color="TotalVentas",
                color_continuous_scale="Blues",
                labels={"TotalVentas": f"Total ({MONEDA})", x_col: agrupacion_tiempo},
            )

        fig_tiempo.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
        mostrar_grafica_accesible(fig_tiempo, df_tiempo, "Ventas en el tiempo")

    with col_der:
        # Distribución por Método de Pago
        df_metodos = df_ventas.groupby("MetodoPago", as_index=False)["Total"].sum()
        tipo_grafico_metodo = st.selectbox(
            "Visualización de Métodos de Pago:",
            ["Gráfico de Dona", "Gráfico Circular (Pastel)", "Barras Horizontales"],
            index=0,
            key="tipo_graf_metodo",
        )

        if tipo_grafico_metodo == "Gráfico de Dona":
            fig_metodo = px.pie(
                df_metodos,
                names="MetodoPago",
                values="Total",
                hole=0.45,
                title="<b>Distribución por Método de Pago</b>",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
        elif tipo_grafico_metodo == "Gráfico Circular (Pastel)":
            fig_metodo = px.pie(
                df_metodos,
                names="MetodoPago",
                values="Total",
                title="<b>Distribución por Método de Pago</b>",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
        else:
            fig_metodo = px.bar(
                df_metodos.sort_values("Total", ascending=True),
                x="Total",
                y="MetodoPago",
                orientation="h",
                title="<b>Métodos de Pago</b>",
                color="MetodoPago",
                labels={"Total": f"Total ({MONEDA})", "MetodoPago": "Método"},
            )

        fig_metodo.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
        mostrar_grafica_accesible(fig_metodo, df_metodos, "Ventas por método de pago")

    # Top Productos Vendidos
    if not df_items.empty:
        st.markdown("---")
        st.subheader("🏆 Ranking de Productos Más Vendidos")

        col_top1, col_top2 = st.columns([1, 1])

        df_top_recaudacion = (
            df_items.groupby("Producto", as_index=False)["Subtotal"]
            .sum()
            .sort_values("Subtotal", ascending=False)
            .head(10)
        )

        df_top_unidades = (
            df_items.groupby("Producto", as_index=False)["Cantidad"]
            .sum()
            .sort_values("Cantidad", ascending=False)
            .head(10)
        )

        with col_top1:
            fig_top_rec = px.bar(
                df_top_recaudacion.sort_values("Subtotal", ascending=True),
                x="Subtotal",
                y="Producto",
                orientation="h",
                title=f"<b>Top 10 por Recaudación Monetaria ({MONEDA})</b>",
                color="Subtotal",
                color_continuous_scale="Viridis",
                labels={"Subtotal": f"Ingresos ({MONEDA})", "Producto": "Producto"},
            )
            fig_top_rec.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
            mostrar_grafica_accesible(fig_top_rec, df_top_recaudacion, "Productos por recaudación")

        with col_top2:
            fig_top_uni = px.bar(
                df_top_unidades.sort_values("Cantidad", ascending=True),
                x="Cantidad",
                y="Producto",
                orientation="h",
                title="<b>Top 10 por Unidades Físicas Vendidas</b>",
                color="Cantidad",
                color_continuous_scale="Teal",
                labels={"Cantidad": "Unidades", "Producto": "Producto"},
            )
            fig_top_uni.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
            mostrar_grafica_accesible(fig_top_uni, df_top_unidades, "Productos por unidades vendidas")

    # Tabla interactiva de ventas
    with st.expander("📄 Ver detalle completo de transacciones (Ventas)", expanded=False):
        st.dataframe(
            df_ventas[[
                "Ticket", "FechaHora", "MetodoPago", "Usuario", "CantidadItems", "Total"
            ]].sort_values("FechaHora", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# PESTAÑA 2: REPORTES Y GRÁFICAS DE INVENTARIO
# ==============================================================================

def render_modulo_inventario(datos: Dict[str, pd.DataFrame]):
    """Renderiza gráficos interactivos de stock, valorización y alertas."""
    st.subheader("📦 Análisis de Inventario y Almacén")

    df_presentaciones = datos["presentaciones"]
    df_productos = datos["productos"]

    if df_presentaciones.empty:
        st.info("ℹ️ No hay productos registrados en el inventario.")
        return

    col1, col2 = st.columns([3, 2])

    with col1:
        tipo_grafico_stock = st.radio(
            "Tipo de gráfica de stock:",
            ["Barras Verticales", "Barras Horizontales", "Treemap (Mapa de Árbol)"],
            horizontal=True,
            key="tipo_graf_stock",
        )

        df_stock_top = df_presentaciones.sort_values("StockActual", ascending=False).head(15)

        if tipo_grafico_stock == "Barras Verticales":
            fig_stock = px.bar(
                df_stock_top,
                x="Producto",
                y="StockActual",
                color="TipoPresentacion",
                title="<b>Stock Actual por Producto (Top 15)</b>",
                labels={"StockActual": "Unidades en Stock", "Producto": "Producto"},
            )
        elif tipo_grafico_stock == "Barras Horizontales":
            fig_stock = px.bar(
                df_stock_top.sort_values("StockActual", ascending=True),
                x="StockActual",
                y="Producto",
                orientation="h",
                color="EstadoStock",
                color_discrete_map={"Normal": "#10b981", "Crítico / Bajo": "#f59e0b", "Sin Stock": "#ef4444"},
                title="<b>Stock Actual por Producto con Estado</b>",
                labels={"StockActual": "Unidades", "Producto": "Producto"},
            )
        else:
            fig_stock = px.treemap(
                df_presentaciones,
                path=["TipoPresentacion", "Producto"],
                values="StockActual",
                title="<b>Distribución de Stock por Presentación y Producto (Treemap)</b>",
                color="StockActual",
                color_continuous_scale="Blues",
            )

        fig_stock.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
        mostrar_grafica_accesible(fig_stock, df_stock_top, "Stock actual")

    with col2:
        # Valorización del inventario
        st.write(" ")
        fig_valor = px.pie(
            df_presentaciones,
            names="TipoPresentacion",
            values="ValorTotalVenta",
            hole=0.4,
            title=f"<b>Valor del Inventario por Presentación ({MONEDA})</b>",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_valor.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
        mostrar_grafica_accesible(
            fig_valor,
            df_presentaciones.groupby("TipoPresentacion", as_index=False)["ValorTotalVenta"].sum(),
            "Valor del inventario por presentación",
        )

    # Semáforo de stock bajo / crítico
    st.markdown("---")
    st.subheader("🚨 Semáforo de Alertas y Reposición de Stock")

    df_alertas = df_presentaciones[df_presentaciones["EstadoStock"].isin(["Sin Stock", "Crítico / Bajo"])].sort_values(
        "StockActual", ascending=True
    )

    if not df_alertas.empty:
        st.warning(f"Se encontraron **{len(df_alertas)} productos** que requieren reposición inmediata.")
        st.dataframe(
            df_alertas[[
                "GTIN", "Producto", "TipoPresentacion", "StockActual", "StockMinimo",
                "EstadoStock", "PrecioCosto", "PrecioVenta"
            ]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ ¡Excelente! Todos los productos cuentan con niveles de stock saludables.")

    # Tabla general de inventario
    with st.expander("📋 Ver catálogo completo de presentaciones y precios", expanded=False):
        st.dataframe(
            df_presentaciones[[
                "GTIN", "Producto", "Laboratorio", "TipoPresentacion", "PrecioCosto",
                "PrecioVenta", "MargenUnitario", "MargenPorcentaje", "StockActual", "ValorTotalVenta"
            ]],
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# PESTAÑA 3: REPORTES Y GRÁFICAS DE MOVIMIENTOS (KARDEX)
# ==============================================================================

def render_modulo_movimientos(datos: Dict[str, pd.DataFrame]):
    """Renderiza gráficos de auditoría de entradas, salidas y ajustes."""
    st.subheader("🔄 Auditoría de Movimientos de Inventario (Kardex)")

    df_mov = datos["movimientos"]
    if df_mov.empty:
        st.info("ℹ️ No hay movimientos registrados en el inventario.")
        return

    col1, col2 = st.columns([3, 2])

    with col1:
        # Flujo de movimientos en el tiempo
        df_mov_tiempo = df_mov.groupby(["Fecha", "TipoMovimiento"], as_index=False)["Cantidad"].sum()
        tipo_grafico_mov = st.radio(
            "Tipo de gráfica de movimientos:",
            ["Barras Agrupadas", "Líneas de Flujo", "Áreas Apiladas"],
            horizontal=True,
            key="tipo_graf_mov",
        )

        color_map_mov = {"Entrada": "#10b981", "Salida": "#ef4444", "Ajuste": "#f59e0b", "Devolucion": "#6366f1"}

        if tipo_grafico_mov == "Barras Agrupadas":
            fig_mov = px.bar(
                df_mov_tiempo,
                x="Fecha",
                y="Cantidad",
                color="TipoMovimiento",
                barmode="group",
                title="<b>Flujo de Entradas, Salidas y Ajustes por Fecha</b>",
                color_discrete_map=color_map_mov,
            )
        elif tipo_grafico_mov == "Líneas de Flujo":
            fig_mov = px.line(
                df_mov_tiempo,
                x="Fecha",
                y="Cantidad",
                color="TipoMovimiento",
                markers=True,
                title="<b>Tendencia de Movimientos de Inventario</b>",
                color_discrete_map=color_map_mov,
            )
        else:
            fig_mov = px.area(
                df_mov_tiempo,
                x="Fecha",
                y="Cantidad",
                color="TipoMovimiento",
                title="<b>Volumen de Movimientos en el Tiempo</b>",
                color_discrete_map=color_map_mov,
            )

        fig_mov.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
        mostrar_grafica_accesible(fig_mov, df_mov_tiempo, "Movimientos en el tiempo")

    with col2:
        # Proporción por Tipo de Movimiento
        df_mov_tipo = df_mov.groupby("TipoMovimiento", as_index=False)["Cantidad"].sum()
        fig_pie_mov = px.pie(
            df_mov_tipo,
            names="TipoMovimiento",
            values="Cantidad",
            hole=0.4,
            title="<b>Distribución por Tipo de Movimiento</b>",
            color="TipoMovimiento",
            color_discrete_map=color_map_mov,
        )
        fig_pie_mov.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
        mostrar_grafica_accesible(fig_pie_mov, df_mov_tipo, "Movimientos por tipo")

    # Detalle de movimientos
    with st.expander("📝 Registro histórico detallado de movimientos", expanded=False):
        st.dataframe(
            df_mov[[
                "FechaHora", "Producto", "TipoMovimiento", "Cantidad", "Razon", "Usuario", "Referencia"
            ]].sort_values("FechaHora", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# PESTAÑA 4: EXPLORADOR GRÁFICO PERSONALIZADO (CUSTOM CHART STUDIO)
# ==============================================================================

def render_explorador_personalizado(datos: Dict[str, pd.DataFrame]):
    """Permite al usuario diseñar cualquier tipo de gráfica cruzando variables a su elección."""
    st.subheader("🎨 Explorador Gráfico Personalizado (Custom Chart Studio)")
    st.caption("Crea y personaliza cualquier tipo de gráfica combinando variables, métricas y dimensiones.")

    fuente_opcion = st.selectbox(
        "1. Selecciona la fuente de datos:",
        ["Ventas (Transacciones)", "Productos e Inventario", "Items Detallados de Ventas", "Movimientos de Inventario"],
        index=0,
    )

    if fuente_opcion == "Ventas (Transacciones)":
        df_target = datos["ventas"]
    elif fuente_opcion == "Productos e Inventario":
        df_target = datos["presentaciones"]
    elif fuente_opcion == "Items Detallados de Ventas":
        df_target = datos["items"]
    else:
        df_target = datos["movimientos"]

    if df_target.empty:
        st.warning("⚠️ No hay datos disponibles en la fuente seleccionada para generar gráficos.")
        return

    columnas_disponibles = df_target.columns.tolist()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        tipo_grafica = st.selectbox(
            "2. Tipo de Gráfica:",
            [
                "📊 Barras Verticales (Bar)",
                "📊 Barras Horizontales (Horizontal Bar)",
                "📈 Líneas (Line)",
                "🌊 Áreas (Area)",
                "🍩 Dona / Circular (Pie/Donut)",
                "🌲 Treemap (Mapa de Árbol)",
                "🔴 Dispersión (Scatter)",
                "📦 Diagrama de Cajas (Box Plot)",
                "📉 Histograma (Histogram)",
            ],
            index=0,
        )

    with c2:
        eje_x = st.selectbox("3. Eje X (Categoría / Dimensión):", columnas_disponibles, index=0)

    with c3:
        columnas_numericas = df_target.select_dtypes(include=["number"]).columns.tolist()
        if not columnas_numericas:
            columnas_numericas = columnas_disponibles
        eje_y = st.selectbox("4. Eje Y (Métrica / Valor):", columnas_numericas, index=0)

    with c4:
        opciones_color = ["Ninguno"] + columnas_disponibles
        color_var = st.selectbox("5. Agrupar por Color:", opciones_color, index=0)

    color_param = None if color_var == "Ninguno" else color_var

    st.markdown("---")

    try:
        if "Barras Verticales" in tipo_grafica:
            fig = px.bar(
                df_target,
                x=eje_x,
                y=eje_y,
                color=color_param,
                title=f"<b>Gráfica de Barras: {eje_y} por {eje_x}</b>",
            )
        elif "Barras Horizontales" in tipo_grafica:
            fig = px.bar(
                df_target,
                x=eje_y,
                y=eje_x,
                orientation="h",
                color=color_param,
                title=f"<b>Gráfica de Barras Horizontales: {eje_y} por {eje_x}</b>",
            )
        elif "Líneas" in tipo_grafica:
            fig = px.line(
                df_target,
                x=eje_x,
                y=eje_y,
                color=color_param,
                markers=True,
                title=f"<b>Gráfica de Líneas: {eje_y} por {eje_x}</b>",
            )
        elif "Áreas" in tipo_grafica:
            fig = px.area(
                df_target,
                x=eje_x,
                y=eje_y,
                color=color_param,
                title=f"<b>Gráfica de Áreas: {eje_y} por {eje_x}</b>",
            )
        elif "Dona / Circular" in tipo_grafica:
            fig = px.pie(
                df_target,
                names=eje_x,
                values=eje_y,
                hole=0.4,
                title=f"<b>Gráfica Circular: {eje_y} por {eje_x}</b>",
            )
        elif "Treemap" in tipo_grafica:
            path_cols = [eje_x]
            if color_param and color_param != eje_x:
                path_cols = [color_param, eje_x]
            fig = px.treemap(
                df_target,
                path=path_cols,
                values=eje_y,
                title=f"<b>Treemap: {eje_y} por {eje_x}</b>",
            )
        elif "Dispersión" in tipo_grafica:
            fig = px.scatter(
                df_target,
                x=eje_x,
                y=eje_y,
                color=color_param,
                title=f"<b>Gráfica de Dispersión: {eje_y} vs {eje_x}</b>",
            )
        elif "Diagrama de Cajas" in tipo_grafica:
            fig = px.box(
                df_target,
                x=eje_x,
                y=eje_y,
                color=color_param,
                title=f"<b>Diagrama de Cajas: {eje_y} por {eje_x}</b>",
            )
        else:  # Histograma
            fig = px.histogram(
                df_target,
                x=eje_x,
                y=eje_y,
                color=color_param,
                title=f"<b>Histograma de {eje_x} ({eje_y})</b>",
            )

        fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=50, b=20))
        mostrar_grafica_accesible(fig, df_target, "Explorador gráfico personalizado")

    except Exception as e:
        st.error(f"❌ Error al generar la gráfica con la combinación seleccionada: {e}")

    with st.expander("🔍 Explorar los datos de esta fuente"):
        st.dataframe(df_target, use_container_width=True)


# ==============================================================================
# PESTAÑA 5: CENTRO DE EXPORTACIÓN Y DESCARGA
# ==============================================================================

def generar_excel_completo(datos: Dict[str, pd.DataFrame]) -> bytes:
    """Genera un archivo Excel con múltiples hojas para Ventas, Inventario y Movimientos."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        if not datos["ventas"].empty:
            # Convert tz-aware datetimes to tz-naive if needed
            df_v = datos["ventas"].copy()
            for col in df_v.select_dtypes(include=["datetime64[ns, UTC]"]).columns:
                df_v[col] = df_v[col].dt.tz_localize(None)
            df_v.to_excel(writer, sheet_name="Ventas", index=False)

        if not datos["presentaciones"].empty:
            datos["presentaciones"].to_excel(writer, sheet_name="Inventario", index=False)

        if not datos["items"].empty:
            datos["items"].to_excel(writer, sheet_name="Detalle_Ventas", index=False)

        if not datos["movimientos"].empty:
            datos["movimientos"].to_excel(writer, sheet_name="Movimientos", index=False)

    return buffer.getvalue()


def render_modulo_exportacion(datos: Dict[str, pd.DataFrame]):
    """Permite descargar reportes completos en formato PDF, Excel y CSV."""
    st.subheader("📥 Centro de Exportación de Reportes")
    st.caption("Descarga informes listos para auditorías, contabilidad o análisis externo.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("#### 📊 Reporte Completo Multitabla (Excel)")
        excel_data = generar_excel_completo(datos)
        st.download_button(
            label="💾 Descargar Libro Excel Completo (.xlsx)",
            data=excel_data,
            file_name=f"Reporte_General_Inventario_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with c2:
        st.markdown("#### 🛒 Reporte de Ventas (CSV)")
        csv_ventas = datos["ventas"].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Descargar Ventas (.csv)",
            data=csv_ventas,
            file_name=f"Reporte_Ventas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c3:
        st.markdown("#### 📦 Reporte de Stock e Inventario (CSV)")
        csv_inventario = datos["presentaciones"].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Descargar Inventario (.csv)",
            data=csv_inventario,
            file_name=f"Reporte_Inventario_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c4:
        st.markdown("#### 📄 Reporte completo (PDF)")
        pdf_data = generar_reporte_pdf(datos)
        st.download_button(
            label="💾 Descargar Reporte (.pdf)",
            data=pdf_data,
            file_name=f"Reporte_General_Inventario_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ==============================================================================
# ENTRADA PRINCIPAL DEL DASHBOARD
# ==============================================================================

def main():
    """Función principal de ejecución de la aplicación Streamlit."""
    configurar_pagina()

    st.title("📊 Dashboard de Reportes y Analítica")
    st.caption(
        "Visualización integral de ventas, control de inventario y auditoría de movimientos "
        "con múltiples tipos de gráficas interactivas."
    )

    # 1. Cargar datos
    datos_brutos = cargar_datos_completos()

    # 2. Renderizar sidebar y obtener filtros
    filtros = render_sidebar_filtros(datos_brutos)

    # 3. Aplicar filtros a los datos
    datos_filtrados = aplicar_filtros(datos_brutos, filtros)

    # 4. Renderizar KPIs principales
    render_kpis_principales(datos_filtrados)

    # 5. Pestañas de módulos de reportes
    tab_ventas, tab_inventario, tab_movimientos, tab_custom, tab_export = st.tabs([
        "📈 Ventas & Facturación",
        "📦 Inventario & Stock",
        "🔄 Movimientos & Kardex",
        "🎨 Explorador Gráfico Personalizado",
        "📥 Centro de Exportación",
    ])

    with tab_ventas:
        render_modulo_ventas(datos_filtrados)

    with tab_inventario:
        render_modulo_inventario(datos_filtrados)

    with tab_movimientos:
        render_modulo_movimientos(datos_filtrados)

    with tab_custom:
        render_explorador_personalizado(datos_filtrados)

    with tab_export:
        render_modulo_exportacion(datos_filtrados)


if __name__ == "__main__":
    main()
