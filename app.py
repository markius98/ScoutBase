import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="ScoutBase", layout="wide")
st.title("ScoutBase - Premier League 2024/2025")

# ========= CARGA DE DATOS =========
@st.cache_data
def cargar_datos():
    df = pd.read_csv("datos/scoutbase_premier_league_updated.csv")
    # Conversión robusta de numéricos comunes
    num_cols = [
        "Age","MP","Starts","Min","90s","Gls","Ast","G+A","G-PK","PK","PKatt",
        "CrdY","CrdR","xG","npxG","xAG","npxG+xAG","PrgC","PrgP","PrgR",
        "G+A-PK","xG+xAG","npxG+xAG","Market Value (M€)"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # Strings clave
    for c in ["Player","Squad","Pos","Nation"]:
        if c in df.columns:
            df[c] = df[c].astype(str)
    return df

df = cargar_datos()

# ========= MENÚ PRINCIPAL =========
seccion = st.sidebar.selectbox(
    "Selecciona una sección",
    [
        "🔍 Buscar jugadores",
        "⚔️ Comparar jugadores",
        "🕵️ Buscar fichajes",
        "➕ Crear jugador",
        "⭐ Lista de seguimiento",
        "🧠 Perfil de jugador",
        "📊 Dashboard general"
    ]
)

# ========= 1) BUSCAR JUGADORES =========
if seccion == "🔍 Buscar jugadores":
    st.sidebar.header("Filtros de búsqueda")

    # Controles
    jugador = st.sidebar.text_input("Buscar por nombre")
    clubes = ["Todos"] + sorted(df["Squad"].dropna().unique().tolist()) if "Squad" in df.columns else ["Todos"]
    club = st.sidebar.selectbox("Filtrar por club", options=clubes)

    posiciones = ["Todas"] + sorted(df["Pos"].dropna().unique().tolist()) if "Pos" in df.columns else ["Todas"]
    pos = st.sidebar.selectbox("Filtrar por posición", options=posiciones)

    # Rango de edad
    if "Age" in df.columns and df["Age"].dropna().size > 0:
        age_min, age_max = int(df["Age"].min()), int(df["Age"].max())
    else:
        age_min, age_max = 15, 45
    edad_rango = st.sidebar.slider("Edad (rango)", min_value=15, max_value=45, value=(age_min, age_max))

    # Rango de valor de mercado
    if "Market Value (M€)" in df.columns and df["Market Value (M€)"].dropna().size > 0:
        mv_min, mv_max = int(df["Market Value (M€)"].fillna(0).min()), int(df["Market Value (M€)"].fillna(0).max())
    else:
        mv_min, mv_max = 0, 0
    mv_rango = st.sidebar.slider("Valor de mercado (M€)", min_value=mv_min, max_value=mv_max if mv_max>mv_min else mv_min, value=(mv_min, mv_max if mv_max>mv_min else mv_min))

    ordenar_por = st.sidebar.selectbox(
        "Ordenar por",
        [c for c in ["Player","Age","Pos","Squad","Gls","Ast","xG","xAG","Min","Market Value (M€)"] if c in df.columns],
        index=0
    )
    asc = st.sidebar.toggle("Orden ascendente", value=False)

    # Filtro base
    df_filtrado = df.copy()

    if jugador:
        df_filtrado = df_filtrado[df_filtrado["Player"].str.contains(jugador, case=False, na=False)]
    if club != "Todos" and "Squad" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Squad"] == club]
    if pos != "Todas" and "Pos" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Pos"] == pos]

    if "Age" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Age"].between(edad_rango[0], edad_rango[1], inclusive="both")]

    if "Market Value (M€)" in df_filtrado.columns:
        mv_series = df_filtrado["Market Value (M€)"].fillna(0)
        df_filtrado = df_filtrado[mv_series.between(mv_rango[0], mv_rango[1], inclusive="both")]

    # Ordenar
    if ordenar_por in df_filtrado.columns:
        df_filtrado = df_filtrado.sort_values(by=ordenar_por, ascending=asc)

    st.subheader("Jugadores encontrados")
    st.write(f"Total: **{len(df_filtrado)}**")
    st.dataframe(df_filtrado, use_container_width=True)

# ========= 2) COMPARAR JUGADORES =========
elif seccion == "⚔️ Comparar jugadores":
    st.markdown("## ⚔️ Comparar jugadores")

    jugadores = st.multiselect("Selecciona jugadores para comparar", sorted(df["Player"].unique()))

    columnas_numericas = [
        "Starts", "Min", "90s", "Gls", "Ast", "G+A", "G-PK", "PK", "PKatt",
        "CrdY", "CrdR", "xG", "npxG", "xAG", "npxG+xAG", "PrgC", "PrgP", "PrgR",
        "G+A-PK", "xG+xAG", "npxG+xAG", "Market Value (M€)"
    ]
    columnas_numericas = [c for c in dict.fromkeys(columnas_numericas) if c in df.columns]  # sin duplicados y existentes

    if jugadores:
        df_sel = df[df["Player"].isin(jugadores)].copy()

        for col in columnas_numericas:
            df_sel[col] = pd.to_numeric(df_sel[col], errors="coerce").fillna(0)

        st.markdown("### 📋 Tabla comparativa")
        st.dataframe(df_sel[["Player"] + columnas_numericas], use_container_width=True)

        # Selección de métricas para gráficos
        metricas = st.multiselect("Selecciona las métricas a comparar (mínimo 3)", columnas_numericas)

        if len(metricas) >= 3:
            # Normalización 0-100 por columna
            df_norm = df_sel.copy()
            for col in metricas:
                max_val = df_sel[col].max()
                df_norm[col] = (df_sel[col] / max_val * 100.0) if max_val and max_val != 0 else 0

            fig_radar = go.Figure()
            for _, row in df_norm.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=row[metricas].values,
                    theta=metricas,
                    fill='toself',
                    name=row["Player"]
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                title="📊 Radar comparativo (normalizado)"
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        if metricas:
            st.markdown("### 📊 Gráfico de barras")
            df_bar = df_sel[["Player"] + metricas].melt(id_vars="Player", var_name="Métrica", value_name="Valor")
            fig_bar = px.bar(df_bar, x="Métrica", y="Valor", color="Player", barmode="group")
            st.plotly_chart(fig_bar, use_container_width=True)

        # Dispersión xG vs Goles (si existen columnas)
        if all(c in df_sel.columns for c in ["xG", "Gls", "Min"]):
            st.markdown("### ⚽ Dispersión: xG vs Goles")
            fig_scatter = px.scatter(
                df_sel, x="xG", y="Gls", color="Player", size="Min", hover_name="Player",
                title="xG vs Goles (tamaño según minutos)"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# ========= 3) BUSCAR FICHAJES =========
elif seccion == "🕵️ Buscar fichajes":
    st.header("🎯 Buscar jugadores fichables")

    dfv = df.copy()
    for col in ["Age","Min","Gls","Ast","xG","xAG","G+A","xG+xAG","Market Value (M€)"]:
        if col in dfv.columns:
            dfv[col] = pd.to_numeric(dfv[col], errors="coerce").fillna(0)

    # Posición objetivo
    posiciones = sorted(dfv["Pos"].dropna().unique().tolist()) if "Pos" in dfv.columns else []
    pos_obj = st.selectbox("Posición objetivo", opciones := (["Todas"] + posiciones) if posiciones else ["Todas"], index=0)

    # Filtros comunes
    c1, c2, c3 = st.columns(3)
    with c1:
        edad_max = st.slider("Edad máxima", min_value=16, max_value=45, value=30)
    with c2:
        min_min = st.slider("Minutos mínimos", min_value=0, max_value=int(dfv["Min"].max() if "Min" in dfv.columns else 3000), value=900)
    with c3:
        market_max = st.slider("Valor de mercado máximo (M€)", min_value=0, max_value=int(dfv["Market Value (M€)"].max() if "Market Value (M€)" in dfv.columns else 0), value=int(dfv["Market Value (M€)"].max() if "Market Value (M€)" in dfv.columns else 0))

    # Filtros específicos por posición: usar métricas disponibles del CSV
    st.subheader("Filtros específicos por posición")
    if pos_obj in ["FW", "FWD", "FW ", "F", "ST"] or (pos_obj != "Todas" and pos_obj.startswith("F")):
        # Delanteros: énfasis en goles/xG
        g_min = st.slider("Goles mínimos (Gls)", 0, int(dfv["Gls"].max() if "Gls" in dfv.columns else 0), 5)
        xg_min = st.slider("xG mínimo", 0.0, float(dfv["xG"].max() if "xG" in dfv.columns else 0), 2.0, 0.1)
    elif pos_obj in ["MF", "MID", "M"] or (pos_obj != "Todas" and pos_obj.startswith("M")):
        # Mediocentros: asistencias/xAG
        a_min = st.slider("Asistencias mínimas (Ast)", 0, int(dfv["Ast"].max() if "Ast" in dfv.columns else 0), 3)
        xag_min = st.slider("xAG mínimo", 0.0, float(dfv["xAG"].max() if "xAG" in dfv.columns else 0), 1.5, 0.1)
    else:
        # Defensas/porteros u otros: usa G+A y xG+xAG si existen
        ga_min = st.slider("Contribuciones de gol mín (G+A)", 0, int(dfv["G+A"].max() if "G+A" in dfv.columns else 0), 1)
        xga_min = st.slider("xG+xAG mínimo", 0.0, float(dfv["xG+xAG"].max() if "xG+xAG" in dfv.columns else 0), 0.5, 0.1)

    # Subconjunto por posición si aplica
    base = dfv.copy()
    if pos_obj != "Todas" and "Pos" in base.columns:
        base = base[base["Pos"] == pos_obj]

    # Aplicar filtros comunes
    if "Age" in base.columns:
        base = base[base["Age"] <= edad_max]
    if "Min" in base.columns:
        base = base[base["Min"] >= min_min]
    if "Market Value (M€)" in base.columns:
        base = base[base["Market Value (M€)"] <= market_max]

    # Aplicar filtros específicos
    if pos_obj in ["FW", "FWD", "FW ", "F", "ST"] or (pos_obj != "Todas" and pos_obj.startswith("F")):
        if "Gls" in base.columns:
            base = base[base["Gls"] >= g_min]
        if "xG" in base.columns:
            base = base[base["xG"] >= xg_min]
        orden = ["Gls","xG","Min"]
    elif pos_obj in ["MF", "MID", "M"] or (pos_obj != "Todas" and pos_obj.startswith("M")):
        if "Ast" in base.columns:
            base = base[base["Ast"] >= a_min]
        if "xAG" in base.columns:
            base = base[base["xAG"] >= xag_min]
        orden = ["Ast","xAG","Min"]
    else:
        if "G+A" in base.columns:
            base = base[base["G+A"] >= ga_min]
        if "xG+xAG" in base.columns:
            base = base[base["xG+xAG"] >= xga_min]
        orden = ["G+A","xG+xAG","Min"] if "xG+xAG" in base.columns else ["G+A","Min"]

    st.markdown("---")
    st.write(f"🔎 Jugadores que cumplen criterios: **{len(base)}**")

    if len(base) == 0:
        st.info("No hay candidatos con estos filtros. Ajusta los deslizadores.")
    else:
        # Orden sugerido (desc)
        orden_presentes = [c for c in orden if c in base.columns]
        base = base.sort_values(by=orden_presentes, ascending=[False]*len(orden_presentes))

        cols_show_default = [c for c in ["Player","Age","Pos","Squad","Min","Gls","Ast","xG","xAG","G+A","xG+xAG","Market Value (M€)"] if c in base.columns]
        st.dataframe(base[cols_show_default].reset_index(drop=True), use_container_width=True)

# ========= 4) CREAR JUGADOR =========
elif seccion == "➕ Crear jugador":
    st.subheader("Formulario para añadir un nuevo jugador")

    with st.form("form_nuevo_jugador"):
        st.markdown("### 📌 Identificación básica")
        nombre = st.text_input("Nombre del jugador")
        club = st.text_input("Club")
        edad = st.number_input("Edad", min_value=15, max_value=45, value=18)
        posicion = st.text_input("Posición (DF, MF, FW, GK)")
        nacionalidad = st.text_input("Nacionalidad")
        nacimiento = st.text_input("Año de nacimiento (opcional)")

        st.markdown("### 🏃 Participación")
        partidos = st.number_input("Partidos jugados (MP)", min_value=0, value=0)
        titulares = st.number_input("Partidos como titular (Starts)", min_value=0, value=0)
        minutos = st.number_input("Minutos jugados (Min)", min_value=0, value=0)

        st.markdown("### ⚽ Estadísticas ofensivas")
        goles = st.number_input("Goles (Gls)", min_value=0, value=0)
        asistencias = st.number_input("Asistencias (Ast)", min_value=0, value=0)
        g_pk = st.number_input("Goles sin penaltis (G-PK)", min_value=0, value=0)

        st.markdown("### 🧠 Estadísticas avanzadas")
        xg = st.number_input("xG (Expected Goals)", min_value=0.0, value=0.0)
        xag = st.number_input("xAG (Expected Assists)", min_value=0.0, value=0.0)
        npxg = st.number_input("npxG (xG sin penaltis)", min_value=0.0, value=0.0)

        st.markdown("### 💰 Valor de mercado")
        valor_mercado = st.number_input("Valor de mercado (M€)", min_value=0.0, value=0.0)

        enviado = st.form_submit_button("Guardar jugador")

    if enviado:
        nuevo = {
            "Rk": 999999,
            "Player": nombre,
            "Nation": nacionalidad,
            "Pos": posicion,
            "Squad": club,
            "Age": edad,
            "Born": nacimiento,
            "MP": partidos,
            "Starts": titulares,
            "Min": minutos,
            "Gls": goles,
            "Ast": asistencias,
            "G+A": goles + asistencias,
            "G-PK": g_pk,
            "G+A-PK": (goles + asistencias) - g_pk,
            "xG": xg,
            "xAG": xag,
            "xG+xAG": xg + xag,
            "npxG": npxg,
            "npxG+xAG": npxg + xag,
            "Market Value (M€)": valor_mercado
        }

        # Asegurar todas las columnas del df original
        nuevo_completo = {}
        for col in df.columns:
            if col in nuevo:
                nuevo_completo[col] = nuevo[col]
            else:
                # Completar con 0 o string vacío si es texto
                if df[col].dtype.kind in "iufc":  # numérico
                    nuevo_completo[col] = 0
                else:
                    nuevo_completo[col] = ""

        df_actualizado = pd.concat([df, pd.DataFrame([nuevo_completo])], ignore_index=True)
        df_actualizado.to_csv("datos/scoutbase_premier_league_updated.csv", index=False)
        st.success(f"✅ Jugador '{nombre}' añadido y guardado.")
        st.cache_data.clear()  # limpiar cache para próxima lectura

# ========= 5) LISTA DE SEGUIMIENTO =========
elif seccion == "⭐ Lista de seguimiento":
    st.markdown("## ⭐ Lista de seguimiento")

    seguimiento_path = "datos/lista_seguimiento.csv"
    try:
        df_seguimiento = pd.read_csv(seguimiento_path)
    except FileNotFoundError:
        df_seguimiento = pd.DataFrame(columns=["Player","Notes"])

    st.write("Añade o quita jugadores a tu watchlist.")
    # Añadir
    col_a, col_b = st.columns([2,1])
    with col_a:
        jugador_add = st.selectbox("Jugador a añadir", sorted(df["Player"].unique()))
    with col_b:
        nota = st.text_input("Nota (opcional)", "")

    if st.button("➕ Añadir a la lista"):
        df_seguimiento = pd.concat([df_seguimiento, pd.DataFrame([{"Player": jugador_add, "Notes": nota}])], ignore_index=True)
        df_seguimiento.to_csv(seguimiento_path, index=False)
        st.success(f"'{jugador_add}' añadido a la lista.")
        st.rerun()

    st.markdown("### 📋 Tu lista")
    if df_seguimiento.empty:
        st.info("Tu lista de seguimiento está vacía.")
    else:
        st.dataframe(df_seguimiento, use_container_width=True)
        # Eliminar
        to_remove = st.multiselect("Selecciona jugadores para eliminar", df_seguimiento["Player"].unique().tolist())
        if to_remove and st.button("❌ Eliminar seleccionados"):
            df_seguimiento = df_seguimiento[~df_seguimiento["Player"].isin(to_remove)]
            df_seguimiento.to_csv(seguimiento_path, index=False)
            st.success("Eliminados correctamente.")
            st.rerun()

        csv_wl = df_seguimiento.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar lista como CSV", csv_wl, "lista_seguimiento.csv", "text/csv")

# ========= 6) PERFIL DE JUGADOR =========
elif seccion == "🧠 Perfil de jugador":
    st.markdown("## 🧠 Perfil individual de jugador")
    jugadores_disponibles = sorted(df["Player"].unique())
    jugador_sel = st.selectbox("Selecciona un jugador", jugadores_disponibles)

    df_jug = df[df["Player"] == jugador_sel]
    if df_jug.empty:
        st.warning("Jugador no encontrado.")
    else:
        jugador = df_jug.iloc[0]
        pos = jugador.get("Pos", "?")
        df_pos = df[df["Pos"] == pos] if "Pos" in df.columns else df.copy()

        columnas_clave = [c for c in ["Gls","Ast","xG","xAG","PrgP","PrgR","CrdY","Min","Market Value (M€)"] if c in df.columns]

        st.markdown("### 📋 Ficha del jugador")
        cols_ficha = [c for c in ["Player","Age","Pos","Squad","Market Value (M€)"] if c in df.columns]
        st.dataframe(jugador[cols_ficha].to_frame().T, use_container_width=True)

        st.markdown("### 📊 Estadísticas generales")
        st.dataframe(jugador[columnas_clave].to_frame().T, use_container_width=True)

        # Medias por posición
        df_media = df_pos[columnas_clave].apply(pd.to_numeric, errors="coerce").mean().fillna(0)

        # Radar
        if len(columnas_clave) >= 3:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[float(jugador[col]) for col in columnas_clave],
                theta=columnas_clave,
                fill='toself',
                name=jugador_sel
            ))
            fig.add_trace(go.Scatterpolar(
                r=[float(df_media[col]) for col in columnas_clave],
                theta=columnas_clave,
                fill='toself',
                name=f"Media {pos}"
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                showlegend=True,
                title="📈 Comparación con la media de su posición"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes métricas para el gráfico radar.")

# ========= 7) DASHBOARD GENERAL =========
elif seccion == "📊 Dashboard general":
    st.markdown("## 📊 Dashboard general de la liga")

    cols_num = ["Gls","Ast","xG","xAG","Min","Market Value (M€)","Age"]
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "xG" in df.columns and "xAG" in df.columns:
        df["xG+xAG"] = df["xG"] + df["xAG"]

    # Top 5
    if "Gls" in df.columns:
        st.subheader("🏆 Top 5 Goleadores")
        st.dataframe(df.sort_values("Gls", ascending=False).head(5)[["Player","Gls","Min","Market Value (M€)"]], use_container_width=True)

    if "Ast" in df.columns:
        st.subheader("🎯 Top 5 Asistentes")
        st.dataframe(df.sort_values("Ast", ascending=False).head(5)[["Player","Ast","Min","Market Value (M€)"]], use_container_width=True)

    if "xG+xAG" in df.columns:
        st.subheader("📈 Top 5 xG + xAG")
        st.dataframe(df.sort_values("xG+xAG", ascending=False).head(5)[["Player","xG","xAG","xG+xAG","Market Value (M€)"]], use_container_width=True)

    # Promedios por posición
    if "Pos" in df.columns and "xG+xAG" in df.columns:
        media_pos = df.groupby("Pos")[["Gls","xG+xAG","Market Value (M€)"]].mean().round(2).reset_index()
        st.subheader("📊 Promedios por posición")
        st.dataframe(media_pos, use_container_width=True)

    # Histogramas
    if "Age" in df.columns:
        st.subheader("📊 Distribución de edades")
        fig_age = px.histogram(df, x="Age", nbins=10)
        st.plotly_chart(fig_age, use_container_width=True)

    if "Market Value (M€)" in df.columns:
        st.subheader("💰 Distribución del valor de mercado")
        fig_value = px.histogram(df, x="Market Value (M€)", nbins=10)
        st.plotly_chart(fig_value, use_container_width=True)
