import ssl
from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================
# BYPASS SSL
# =========================================
ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(
    page_title="Dashboard Seguimiento Reparto",
    layout="wide",
)

# =========================================
# CONFIG BASE
# =========================================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1pLeNHeCQnlbTj-dIat7LajVLZNVIDC5eeEzhyBssz7U/export?format=csv&gid=0"

PRODUCTOS_PRIORITARIOS_DEFAULT = [
    "BATATA",
    "AJO (COD: 0,45)",
    "LOCOTE PICANTE",
    "COLIFLOR (COD 1,8)",
    "BERENJENA (COD: 0,3)",
    "PEREJIL",
    "ZAPALLO BRASILERO (COD: 0,825)",
    "LOCOTE AMARILLO",
    "Calabacín/ Zucchini (COD: 0,52)",
    "cebolla morada (COD: 0,14)",
    "ALBAHACA",
    "CILANTRO",
    "ZANAHORIA (COD: 0,17)",
    "cebolla",
    "ZAPALLITO TRONCO (COD: 0,33)",
    "LOCOTE ROJO",
    "LECHUGA MANTECOSA",
    "LECHUGA MORADA",
    "PAPA",
    "PEPINO ( COD: 0,336)",
    "LECHUGA BLANCA",
    "LOCOTE (COD: 0,13)",
    "ACELGA",
    "TOMATE CHERRY",
    "RUCULA",
    "TOMATE",
    "LECHUGA PIRATI",
    "KIT VERDEOS + CHERRY",
]

# =========================================
# HELPERS
# =========================================
def gs_int(n):
    if pd.isna(n):
        n = 0
    return f"{int(round(float(n))):,}".replace(",", ".")


def gs_pct(n):
    if pd.isna(n):
        return "0,0%"
    return f"{float(n):.1f}%".replace(".", ",")


def normalizar_cliente(texto):
    if pd.isna(texto):
        return ""
    return " ".join(str(texto).replace("-", " ").split()).strip().upper()


def formato_py(numero):
    if pd.isna(numero):
        numero = 0
    return f"{int(round(float(numero))):,}".replace(",", ".")


def formato_py_decimal(numero, decimales=1):
    if pd.isna(numero):
        numero = 0
    texto = f"{float(numero):,.{decimales}f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


# =========================================
# DATA
# =========================================
PRODUCTO_DASHBOARD_COL = "Producto_base"

@st.cache_data(ttl=30)
def cargar_datos():
    df = pd.read_csv(GOOGLE_SHEET_CSV_URL)

    if df.empty:
        return df

    df.columns = [str(c).strip() for c in df.columns]

    columnas_esperadas = ["Fecha entrega", "Cliente", "Producto", "Total producto"]
    faltantes = [c for c in columnas_esperadas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en la hoja: {', '.join(faltantes)}")

    if "Vendedora" not in df.columns:
        df["Vendedora"] = ""

    df["Fecha entrega"] = pd.to_datetime(df["Fecha entrega"], dayfirst=True, errors="coerce")
    df["Total producto"] = pd.to_numeric(df["Total producto"], errors="coerce").fillna(0)
    df["Cliente"] = df["Cliente"].astype(str).str.strip()
    df["Producto"] = df["Producto"].astype(str).str.strip()
    if "Producto dashboard" in df.columns:
        df["Producto dashboard"] = df["Producto dashboard"].fillna("").astype(str).str.strip()
        df[PRODUCTO_DASHBOARD_COL] = df["Producto dashboard"]
    else:
        df[PRODUCTO_DASHBOARD_COL] = df["Producto"]
    df["Vendedora"] = df["Vendedora"].fillna("").astype(str).str.strip()
    df["Cliente_normalizado"] = df["Cliente"].apply(normalizar_cliente)

    df = df.dropna(subset=["Fecha entrega"])

    iso = df["Fecha entrega"].dt.isocalendar()
    df["ISO_Year"] = iso.year.astype(int)
    df["ISO_Week"] = iso.week.astype(int)
    df["Semana_label"] = df["ISO_Year"].astype(str) + "-S" + df["ISO_Week"].astype(str).str.zfill(2)
    df["Inicio_semana"] = df["Fecha entrega"] - pd.to_timedelta(df["Fecha entrega"].dt.weekday, unit="D")

    return df.sort_values("Fecha entrega").reset_index(drop=True)


# =========================================
# CARGA
# =========================================
df = cargar_datos()

st.title("Dashboard semanal de reparto")

if df.empty:
    st.warning("La hoja está vacía o no se pudieron cargar datos.")
    st.stop()

# =========================================
# DIAGNÓSTICO
# =========================================
with st.expander("Diagnóstico de lectura"):
    st.write("Columnas detectadas:", df.columns.tolist())
    st.write("Primeras 10 filas:")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    if "Vendedora" in df.columns:
        st.write("Primeros valores de Vendedora:")
        st.write(df["Vendedora"].head(20).tolist())
        st.write("Valores únicos de Vendedora:")
        st.write(sorted(df["Vendedora"].dropna().astype(str).str.strip().unique().tolist()))
    else:
        st.write("No existe la columna Vendedora")

# =========================================
# SIDEBAR
# =========================================
st.sidebar.header("Filtros")

semanas_disponibles = (
    df[["ISO_Year", "ISO_Week", "Semana_label", "Inicio_semana"]]
    .drop_duplicates()
    .sort_values(["ISO_Year", "ISO_Week"], ascending=False)
    .reset_index(drop=True)
)

semana_labels = semanas_disponibles["Semana_label"].tolist()
semana_sel = st.sidebar.selectbox("Semana a analizar", semana_labels, index=0)

fila_semana = semanas_disponibles.loc[semanas_disponibles["Semana_label"] == semana_sel].iloc[0]
year_sel = int(fila_semana["ISO_Year"])
week_sel = int(fila_semana["ISO_Week"])

vendedoras_validas = sorted(
    [
        v for v in df["Vendedora"].dropna().astype(str).str.strip().unique().tolist()
        if v and v.lower() != "sin dato"
    ]
)

vendedoras_sel = st.sidebar.multiselect(
    "Vendedora",
    vendedoras_validas,
    default=vendedoras_validas,
)

productos_prioritarios = st.sidebar.multiselect(
    "Productos prioritarios",
    sorted([p for p in df[PRODUCTO_DASHBOARD_COL].dropna().unique().tolist() if str(p).strip()]),
    default=[p for p in PRODUCTOS_PRIORITARIOS_DEFAULT if p in df[PRODUCTO_DASHBOARD_COL].unique()],
)

df_filtrado = df.copy()
df_filtrado = df_filtrado[df_filtrado["Vendedora"].astype(str).str.strip() != ""]
df_filtrado = df_filtrado[df_filtrado["Vendedora"].astype(str).str.lower().str.strip() != "sin dato"]

if vendedoras_sel:
    df_filtrado = df_filtrado[df_filtrado["Vendedora"].isin(vendedoras_sel)]
else:
    df_filtrado = df_filtrado.iloc[0:0]

actual = df_filtrado[
    (df_filtrado["ISO_Year"] == year_sel) & (df_filtrado["ISO_Week"] == week_sel)
].copy()

semanas_ordenadas = semanas_disponibles[["ISO_Year", "ISO_Week"]].drop_duplicates().values.tolist()
idx_actual = semanas_ordenadas.index([year_sel, week_sel]) if [year_sel, week_sel] in semanas_ordenadas else None

anterior = pd.DataFrame(columns=df_filtrado.columns)
if idx_actual is not None and idx_actual + 1 < len(semanas_ordenadas):
    year_prev, week_prev = semanas_ordenadas[idx_actual + 1]
    anterior = df_filtrado[
        (df_filtrado["ISO_Year"] == year_prev) & (df_filtrado["ISO_Week"] == week_prev)
    ].copy()

# =========================================
# KPIs
# =========================================
venta_actual = actual["Total producto"].sum()
venta_anterior = anterior["Total producto"].sum()

clientes_actual = actual["Cliente_normalizado"].nunique()
clientes_anterior = anterior["Cliente_normalizado"].nunique()

mov_actual = len(actual)
mov_anterior = len(anterior)

ticket_actual = venta_actual / clientes_actual if clientes_actual else 0
ticket_anterior = venta_anterior / clientes_anterior if clientes_anterior else 0

var_venta = ((venta_actual - venta_anterior) / venta_anterior * 100) if venta_anterior else 0
var_clientes = ((clientes_actual - clientes_anterior) / clientes_anterior * 100) if clientes_anterior else 0
var_ticket = ((ticket_actual - ticket_anterior) / ticket_anterior * 100) if ticket_anterior else 0
var_mov = ((mov_actual - mov_anterior) / mov_anterior * 100) if mov_anterior else 0

inicio_semana = pd.to_datetime(fila_semana["Inicio_semana"])
fin_semana = inicio_semana + timedelta(days=6)

st.caption(
    f"Semana analizada: {semana_sel} | "
    f"{inicio_semana.strftime('%d/%m/%Y')} al {fin_semana.strftime('%d/%m/%Y')}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Venta semanal", gs_int(venta_actual), gs_pct(var_venta))
c2.metric("Clientes activos", gs_int(clientes_actual), gs_pct(var_clientes))
c3.metric("Ticket promedio", gs_int(ticket_actual), gs_pct(var_ticket))
c4.metric("Movimientos", gs_int(mov_actual), gs_pct(var_mov))

st.divider()

# =========================================
# EVOLUCIÓN SEMANAL
# =========================================
st.subheader("Evolución semanal")

evolucion = (
    df_filtrado.groupby(["ISO_Year", "ISO_Week", "Semana_label"], as_index=False)["Total producto"]
    .sum()
    .sort_values(["ISO_Year", "ISO_Week"])
)

fig_evol = px.line(
    evolucion,
    x="Semana_label",
    y="Total producto",
    markers=True,
)

fig_evol.update_traces(
    hovertemplate="Semana: %{x}<br>Venta: %{y:,.0f}<extra></extra>"
)

fig_evol.update_layout(
    height=420,
    xaxis_title="Semana",
    yaxis_title="Venta",
    yaxis_tickformat=",.0f",
)

st.plotly_chart(fig_evol, use_container_width=True, key="fig_evol")

# =========================================
# PRODUCTOS
# =========================================
st.subheader("Productos")

prod_actual = (
    actual[actual[PRODUCTO_DASHBOARD_COL].astype(str).str.strip() != ""].groupby(PRODUCTO_DASHBOARD_COL, as_index=False)["Total producto"]
    .sum()
    .rename(columns={PRODUCTO_DASHBOARD_COL: "Producto", "Total producto": "Actual"})
)

prod_prev = (
    anterior[anterior[PRODUCTO_DASHBOARD_COL].astype(str).str.strip() != ""].groupby(PRODUCTO_DASHBOARD_COL, as_index=False)["Total producto"]
    .sum()
    .rename(columns={PRODUCTO_DASHBOARD_COL: "Producto", "Total producto": "Anterior"})
)

comparacion_prod = prod_actual.merge(prod_prev, on="Producto", how="outer").fillna(0)
comparacion_prod["Diferencia"] = comparacion_prod["Actual"] - comparacion_prod["Anterior"]
comparacion_prod["Variacion_%"] = comparacion_prod.apply(
    lambda r: ((r["Actual"] - r["Anterior"]) / r["Anterior"] * 100) if r["Anterior"] else 0,
    axis=1,
)

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Top 10 productos por venta**")
    top10_prod = comparacion_prod.sort_values("Actual", ascending=False).head(10).copy()
    top10_prod = top10_prod.sort_values("Actual", ascending=True)
    top10_prod["Texto_actual"] = top10_prod["Actual"].apply(formato_py)

    fig_top = px.bar(
        top10_prod,
        x="Actual",
        y="Producto",
        orientation="h",
        text="Texto_actual",
    )
    fig_top.update_traces(
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Venta: %{customdata[0]}<extra></extra>",
        customdata=top10_prod[["Texto_actual"]],
        cliponaxis=False,
    )
    fig_top.update_layout(
        height=550,
        xaxis_title="Venta",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=40, t=10, b=10),
    )
    fig_top.update_xaxes(tickformat=",.0f")
    st.plotly_chart(fig_top, use_container_width=True, key="fig_top_productos")

with col_b:
    st.markdown("**Productos que más subieron / bajaron vs semana anterior**")

    subidas = comparacion_prod.sort_values("Diferencia", ascending=False).head(5)
    bajadas = comparacion_prod.sort_values("Diferencia", ascending=True).head(5)

    delta10 = pd.concat([subidas, bajadas], ignore_index=True).drop_duplicates(subset=["Producto"]).copy()
    delta10 = delta10.sort_values("Diferencia", ascending=True)
    delta10["Texto_diferencia"] = delta10["Diferencia"].apply(formato_py)

    fig_delta = px.bar(
        delta10,
        x="Diferencia",
        y="Producto",
        orientation="h",
        text="Texto_diferencia",
    )
    fig_delta.update_traces(
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Diferencia: %{customdata[0]}<extra></extra>",
        customdata=delta10[["Texto_diferencia"]],
        cliponaxis=False,
    )
    fig_delta.update_layout(
        height=550,
        xaxis_title="Diferencia vs semana anterior",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=40, t=10, b=10),
    )
    fig_delta.update_xaxes(tickformat=",.0f")
    st.plotly_chart(fig_delta, use_container_width=True, key="fig_delta_productos")

if productos_prioritarios:
    st.markdown("**Comparación semanal de productos prioritarios**")
    pivote_prioritarios = (
        df_filtrado[(df_filtrado[PRODUCTO_DASHBOARD_COL].astype(str).str.strip() != "") & (df_filtrado[PRODUCTO_DASHBOARD_COL].isin(productos_prioritarios))]
        .groupby(["Semana_label", PRODUCTO_DASHBOARD_COL], as_index=False)["Total producto"]
        .sum()
        .pivot(index="Semana_label", columns=PRODUCTO_DASHBOARD_COL, values="Total producto")
        .fillna(0)
        .sort_index()
    )

    st.line_chart(pivote_prioritarios)

# =========================================
# CLIENTES
# =========================================
st.subheader("Clientes")

mapa_clientes = (
    df_filtrado.groupby("Cliente_normalizado", as_index=False)["Cliente"]
    .first()
)

ventas_cliente_actual = (
    actual.groupby("Cliente_normalizado", as_index=False)["Total producto"]
    .sum()
    .rename(columns={"Total producto": "Venta"})
)

ventas_cliente_prev = (
    anterior.groupby("Cliente_normalizado", as_index=False)["Total producto"]
    .sum()
    .rename(columns={"Total producto": "Venta_anterior"})
)

comparacion_clientes = ventas_cliente_actual.merge(
    ventas_cliente_prev,
    on="Cliente_normalizado",
    how="outer"
).fillna(0)

comparacion_clientes = comparacion_clientes.merge(
    mapa_clientes,
    on="Cliente_normalizado",
    how="left"
)

comparacion_clientes["Cliente"] = comparacion_clientes["Cliente"].fillna(comparacion_clientes["Cliente_normalizado"])
comparacion_clientes["Variacion"] = comparacion_clientes["Venta"] - comparacion_clientes["Venta_anterior"]

cx1, cx2, cx3 = st.columns(3)

with cx1:
    st.markdown("**Top 10 clientes de la semana**")
    top_clientes = comparacion_clientes.sort_values("Venta", ascending=False).head(10).copy()
    top_clientes = top_clientes.sort_values("Venta", ascending=True)
    top_clientes["Texto_venta"] = top_clientes["Venta"].apply(formato_py)

    fig_clientes = px.bar(
        top_clientes,
        x="Venta",
        y="Cliente",
        orientation="h",
        text="Texto_venta",
    )
    fig_clientes.update_traces(
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Venta: %{customdata[0]}<extra></extra>",
        customdata=top_clientes[["Texto_venta"]],
        cliponaxis=False,
    )
    fig_clientes.update_layout(
        height=550,
        xaxis_title="Venta",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=40, t=10, b=10),
    )
    fig_clientes.update_xaxes(tickformat=",.0f")
    st.plotly_chart(fig_clientes, use_container_width=True, key="fig_clientes")

with cx2:
    st.markdown("**Clientes que más subieron**")
    clientes_suben = comparacion_clientes[comparacion_clientes["Variacion"] > 0].copy()
    clientes_suben = clientes_suben.sort_values("Variacion", ascending=False).head(10)
    clientes_suben = clientes_suben.sort_values("Variacion", ascending=True)
    clientes_suben["Texto_var"] = clientes_suben["Variacion"].apply(formato_py)

    if not clientes_suben.empty:
        fig_suben = px.bar(
            clientes_suben,
            x="Variacion",
            y="Cliente",
            orientation="h",
            text="Texto_var",
        )
        fig_suben.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Subida: %{customdata[0]}<extra></extra>",
            customdata=clientes_suben[["Texto_var"]],
            cliponaxis=False,
        )
        fig_suben.update_layout(
            height=550,
            xaxis_title="Subida vs semana anterior",
            yaxis_title="",
            showlegend=False,
            margin=dict(l=10, r=40, t=10, b=10),
        )
        fig_suben.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig_suben, use_container_width=True, key="fig_clientes_suben")
    else:
        st.info("No hubo clientes con suba en esta semana.")

with cx3:
    st.markdown("**Clientes que más bajaron**")
    clientes_bajan = comparacion_clientes[comparacion_clientes["Variacion"] < 0].copy()
    clientes_bajan = clientes_bajan.sort_values("Variacion", ascending=True).head(10)
    clientes_bajan["Texto_var"] = clientes_bajan["Variacion"].apply(formato_py)

    if not clientes_bajan.empty:
        fig_bajan = px.bar(
            clientes_bajan,
            x="Variacion",
            y="Cliente",
            orientation="h",
            text="Texto_var",
        )
        fig_bajan.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Baja: %{customdata[0]}<extra></extra>",
            customdata=clientes_bajan[["Texto_var"]],
            cliponaxis=False,
        )
        fig_bajan.update_layout(
            height=550,
            xaxis_title="Baja vs semana anterior",
            yaxis_title="",
            showlegend=False,
            margin=dict(l=10, r=40, t=10, b=10),
        )
        fig_bajan.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig_bajan, use_container_width=True, key="fig_clientes_bajan")
    else:
        st.info("No hubo clientes con baja en esta semana.")

st.markdown("**Detalle clientes semana actual vs anterior**")
mostrar_clientes = comparacion_clientes[["Cliente", "Venta", "Venta_anterior", "Variacion"]].copy()
mostrar_clientes = mostrar_clientes.sort_values("Venta", ascending=False)
mostrar_clientes["Venta"] = mostrar_clientes["Venta"].apply(formato_py)
mostrar_clientes["Venta_anterior"] = mostrar_clientes["Venta_anterior"].apply(formato_py)
mostrar_clientes["Variacion"] = mostrar_clientes["Variacion"].apply(formato_py)

st.dataframe(mostrar_clientes, use_container_width=True, hide_index=True)

# =========================================
# VENDEDORAS
# =========================================
st.subheader("Vendedoras")

ven = (
    actual.groupby("Vendedora", as_index=False)
    .agg(
        Venta=("Total producto", "sum"),
        Clientes=("Cliente_normalizado", "nunique"),
        Movimientos=("Producto", "count"),
    )
    .sort_values("Venta", ascending=False)
)

vx1, vx2 = st.columns(2)

with vx1:
    st.markdown("**Venta por vendedora**")
    if not ven.empty:
        ven_venta = ven.copy().sort_values("Venta", ascending=True)
        ven_venta["Texto_venta"] = ven_venta["Venta"].apply(formato_py)

        fig_vendedora_venta = px.bar(
            ven_venta,
            x="Venta",
            y="Vendedora",
            orientation="h",
            text="Texto_venta",
        )
        fig_vendedora_venta.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Venta: %{customdata[0]}<extra></extra>",
            customdata=ven_venta[["Texto_venta"]],
            cliponaxis=False,
        )
        fig_vendedora_venta.update_layout(
            height=420,
            xaxis_title="Venta",
            yaxis_title="",
            showlegend=False,
            margin=dict(l=10, r=40, t=10, b=10),
        )
        fig_vendedora_venta.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig_vendedora_venta, use_container_width=True, key="fig_vendedora_venta")
    else:
        st.info("No hay datos para esta semana.")

with vx2:
    st.markdown("**Clientes atendidos por vendedora**")
    if not ven.empty:
        ven_clientes = ven.copy().sort_values("Clientes", ascending=True)
        ven_clientes["Texto_clientes"] = ven_clientes["Clientes"].apply(formato_py)

        fig_vendedora_clientes = px.bar(
            ven_clientes,
            x="Clientes",
            y="Vendedora",
            orientation="h",
            text="Texto_clientes",
        )
        fig_vendedora_clientes.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Clientes: %{customdata[0]}<extra></extra>",
            customdata=ven_clientes[["Texto_clientes"]],
            cliponaxis=False,
        )
        fig_vendedora_clientes.update_layout(
            height=420,
            xaxis_title="Clientes",
            yaxis_title="",
            showlegend=False,
            margin=dict(l=10, r=40, t=10, b=10),
        )
        fig_vendedora_clientes.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig_vendedora_clientes, use_container_width=True, key="fig_vendedora_clientes")
    else:
        st.info("No hay datos para esta semana.")

# =========================================
# TABLA FINAL PRODUCTOS
# =========================================
st.subheader("Tabla comparativa de productos")

tabla_prod = comparacion_prod.sort_values("Actual", ascending=False).copy()
tabla_prod["Actual"] = tabla_prod["Actual"].apply(formato_py)
tabla_prod["Anterior"] = tabla_prod["Anterior"].apply(formato_py)
tabla_prod["Diferencia"] = tabla_prod["Diferencia"].apply(formato_py)
tabla_prod["Variacion_%"] = tabla_prod["Variacion_%"].apply(lambda x: formato_py_decimal(x, 1) + "%")

st.dataframe(tabla_prod, use_container_width=True, hide_index=True)
