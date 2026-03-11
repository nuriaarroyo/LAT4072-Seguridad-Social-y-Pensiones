from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import streamlit as st

from pensiones.core.lss1973_ret import (
    UMA_DIARIA_DEFAULT,
    calcular_pension_lss1973,
    tabla_sensibilidades_lss1973,
)

DISPLAY = """Calculadora de Pensión por Cesantía en Edad Avanzada y Vejez — LSS 1973
"""


def render() -> None:
    st.header("🏛️ LSS 1973 — Cesantía en Edad Avanzada y Vejez")
    st.caption(DISPLAY)

    with st.expander("💡 ¿Qué hace esta calculadora?", expanded=False):
        st.markdown(
            """
Calcula la **pensión mensual**, la **tasa de reemplazo**  y la **tasa acumulada** bajo la **Ley del Seguro Social de 1973**,.
- Permite analizar el impacto de la edad de retiro (60-65 años) en la pensión.
- Considera factores familiares (cónyuge, hijos, Art. 14°) y la densidad de cotización (80% vs 100%).
- Genera una tabla de sensibilidades y una gráfica para visualizar el trade-off entre retirarse antes vs. después."""
        )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        pass
    
    st.header("👥 Datos de la o del trabajador")

    nombre = st.text_input("Nombre")
    edad_actual = st.number_input("Edad actual", min_value=15, max_value=80,  step=1)
    semanas_cot = st.number_input(
        "Semanas cotizadas actualmente", min_value=0, max_value=5000,  step=1)

    st.subheader("Salario")
    sal_mensual = st.number_input(
        "Salario mensual promedio de las últimas 250 sem. (MXN)",
        min_value=0.0,
        step=500.0,
    )
    sal_diario = float(sal_mensual) / 30.0
    st.caption(f"Salario diario: **${sal_diario:,.4f}**")

    st.subheader("Densidad de cotización")
    densidad_full = st.checkbox(
        "Cotizar con densidad del 100%",
        value=True,
        help="Si se desmarca se calcula con densidad del 80%"
    )
    densidad = 1.0 if densidad_full else 0.80

    #st.subheader("Densidad de cotización")
    #densidad = st.radio("Densidad", [0.80, 1.00], format_func=lambda x: f"{int(x*100)}%", horizontal=True)

    #include_existing = st.checkbox(
    #    "Incluir semanas ya cotizadas (I3)",
    #    value=True,
    #    help=(
    #        "100%DC incluye semanas existentes (I3=Carátula). "
    #        "80%DC las deja en blanco (I3=0)."
    #    ),
    #)

    st.subheader("Factores familiares")
    #pct_conyuge = st.slider("Cónyuge/Soledad", 0, 30, 15, step=5) / 100
    estado_familiar = st.radio(
        "Selecciona la asignación",
        ["Cónyuge (15%)", "Soledad (15%)"],
        index=0
    )
    pct_conyuge = 0.15  # Ambos casos tienen el mismo porcentaje
    n_hijos = st.number_input("Hijos en sistema educativo (≤25 años) o inválidos", 0, 10, 0, step=1)
    pct_hijos = float(n_hijos) * 0.10
    pct_art14 =0.11 #st.slider("Paso 10 — Art. 14° transitorio (%)", 0, 20, 11, step=1) / 100
    uma_diaria = float(UMA_DIARIA_DEFAULT)
    include_existing = True

    #st.subheader("UMA / SMGV")
    #uma_diaria = st.number_input(
    #    "UMA diaria vigente (MXN)",
    #    min_value=50.0,
    #    value=float(UMA_DIARIA_DEFAULT),
    #    step=0.01,
    #)

    #st.subheader("Rango de edades")
    min_age = 60 #st.slider("Edad mínima", 60, 65, 60)
    max_age = 65 #st.slider("Edad máxima", 60, 65, 65)

    #if min_age > max_age:
    #    st.error("La edad mínima no puede ser mayor que la máxima.")
    #    return

    st.divider()
    calcular = st.button("✅ Calcular", type="primary", use_container_width=True)

    if not calcular:
        st.info("⚠️Ingresa los datos completos en el panel y presiona **Calcular**.")
        return

    # ── Cálculos ──────────────────────────────────────────────────────────────
    df = tabla_sensibilidades_lss1973(
        edad_actual=int(edad_actual),
        salario_diario_avg=float(sal_diario),
        semanas_cotizadas=int(semanas_cot),
        min_age=int(min_age),
        max_age=int(max_age),
        densidad=float(densidad),
        pct_conyuge=float(pct_conyuge),
        pct_hijos_total=float(pct_hijos),
        pct_art14=float(pct_art14),
        uma_diaria=float(uma_diaria),
        include_existing=bool(include_existing),
    )
    # VIVA LA VECTORIZACION
    best = df.loc[df["Tasa de Reemplazo"].idxmax()]
    worst = df.loc[df["Tasa de Reemplazo"].idxmin()]

    # ── Métricas ──────────────────────────────────────────────────────────────
    st.subheader(f"📊 Resultados")
    st.caption(
    f"{nombre} · Densidad {int(float(densidad)*100)}% · Salario ${sal_mensual:,.2f}/mes"
        )           
    c1, c2, c3 = st.columns(3)
    c1.metric("Mejor tasa de reemplazo", f"{best['Tasa de Reemplazo']:.2%}")
    c2.metric("Edad óptima", str(int(best["Edad"])))
    c3.metric("Pensión mensual óptima", f"${best['Pensión Mensual (MXN)']:,.2f}")

    st.divider()

    # ── Tabla + Gráfica ───────────────────────────────────────────────────────
    tab_tabla, tab_graf = st.tabs(["📋 Tabla de sensibilidades", "📈 Gráfica"])

    with tab_tabla:
        fmt = {
            "Pensión Mensual (MXN)": "${:,.2f}",
            "Tasa de Reemplazo": "{:.4%}",
            "Δ Marginal (pp)": "{:.4f}",
            "Δ Acumulado (pp)": "{:.4f}",
        }
        st.dataframe(
            df.style.format(fmt, na_rep="—")
            .highlight_max(subset=["Tasa de Reemplazo", "Pensión Mensual (MXN)"], color="#d4f0d4")
            .highlight_min(subset=["Tasa de Reemplazo", "Pensión Mensual (MXN)"], color="#fde8e8"),
            use_container_width=True,
            hide_index=True,
        )

    with tab_graf:
        fig, ax1 = plt.subplots(figsize=(8, 4.5))
        ages = df["Edad"].tolist()
        rr_pct = (df["Tasa de Reemplazo"] * 100).tolist()
        pensions = df["Pensión Mensual (MXN)"].tolist()

        ax1.plot(ages, rr_pct, "o-", linewidth=2, label="Tasa de reemplazo (%)")
        for x, y in zip(ages, rr_pct):
            ax1.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8.5)

        ax2 = ax1.twinx()
        ax2.plot(ages, pensions, "s--", linewidth=2, label="Pensión mensual (MXN)")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax2.set_ylabel("Pensión mensual (MXN)")

        ax1.set_xlabel("Edad de jubilación")
        ax1.set_ylabel("Tasa de reemplazo (%)")
        ax1.set_xticks(ages)
        ax1.set_title(
            "LSS 1973 — Tasa de reemplazo y Pensión mensual vs Edad de retiro\n"
            f"({int(float(densidad)*100)}% DC · Sal. ${sal_mensual:,.0f}/mes · UMA ${uma_diaria:.2f}/día)"
        )
        ax1.grid(True, alpha=0.3)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        fig.tight_layout()
        st.pyplot(fig, clear_figure=False)

    st.divider()

    # ── Detalle paso a paso ───────────────────────────────────────────────────
#    st.subheader("🔍 Detalle paso a paso")
#    edad_sel = st.selectbox(
#        "Selecciona la edad de retiro:",
#        list(range(int(min_age), int(max_age) + 1)),
#        index=int(max_age - min_age),
#    )

    edad_sel = best["Edad"]
    det = calcular_pension_lss1973(
        edad_actual=int(edad_actual),
        salario_diario_avg=float(sal_diario),
        semanas_cotizadas=int(semanas_cot),
        edad_retiro=int(edad_sel),
        densidad=float(densidad),
        pct_conyuge=float(pct_conyuge),
        pct_hijos_total=float(pct_hijos),
        pct_art14=float(pct_art14),
        uma_diaria=float(uma_diaria),
        include_existing=bool(include_existing),
    )

#    pasos = [
#        ("Paso 0", "Edad actual del trabajador", str(int(edad_actual))),
#        ("", "Semanas cotizadas actualmente", f"{int(semanas_cot):,}"),
#        ("Paso 1", "Salario diario promedio 5 años", f"${float(sal_diario):,.4f}"),
#        ("", "Salario mensual promedio (C6 = C5×30)", f"${float(sal_diario)*30:,.2f}"),
#        ("Paso 2", "Semanas futuras: INT((edad_retiro−edad)×52×densidad) [I4]", f"{det['sem_futuras']:,}"),
#        ("", "Semanas existentes (I3)", f"{det['sem_existentes']:,}"),
#        ("", "Total semanas (I5 = I3+I4)", f"{det['total_semanas']:,}"),
#        ("", "Semanas en exceso (C8 = I5−500)", f"{det['semanas_exceso']:,.4f}"),
#        ("", "Años en exceso exactos (C9 = C8/52)", f"{det['anos_exacto']:,.4f}"),
#        ("", "Años en exceso redondeados (C10)", f"{det['anos_redondeado']:.1f}"),
#        ("Paso 3", "UMA diaria vigente (C12)", f"${float(uma_diaria):,.2f}"),
#        ("", "Cociente sal/UMA (C13 = C5/C12)", f"{det['cociente_sal_uma']:,.4f}"),
#        ("Paso 4", "% Cuantía básica según tabla (C16)", f"{det['pct_cuantia_basica']:.4f}"),
#        ("", "% Incremento anual según tabla (C17)", f"{det['pct_incremento']:.4f}"),
#        ("Paso 5", "Cuantía básica diaria (C19 = C16×C5)", f"${det['cuantia_basica_diaria']:,.4f}"),
#        ("", "Cuantía básica anual (C20 = C19×365)", f"${det['cuantia_basica_anual']:,.2f}"),
#        ("Paso 6", "Incremento diario por años (C22 = C5×C17×C10)", f"${det['incr_diario']:,.4f}"),
#        ("", "Incremento anual (C23 = C22×365)", f"${det['incr_anual']:,.2f}"),
#        ("Paso 7", "Cuantía base diaria (C25 = C19+C22)", f"${det['cuantia_base_diaria']:,.4f}"),
#        ("", "Cuantía base anual (C26 = C20+C23)", f"${det['cuantia_base_anual']:,.2f}"),
#        ("Paso 8", f"Asignación cónyuge/soledad: {float(pct_conyuge):.0%}", f"{float(pct_conyuge):.0%}"),
#        ("Paso 9", f"Asignación hijos ({int(n_hijos)} × 10%)", f"{float(pct_hijos):.0%}"),
#        ("Paso 10", "Art. 14° transitorio decreto 20/12/2001", f"{float(pct_art14):.0%}"),
#        ("Paso 11", "Factor total (1+P8)×(1+P9)×(1+P10)", f"{det['factor_familiar']:.6f}"),
#        ("", "Pensión base diaria (C35 = C25×factor)", f"${det['pension_base_diaria']:,.4f}"),
#        ("Paso 12", f"% según edad {int(edad_sel)} años (C38)", f"{det['pct_edad']:.0%}"),
#        ("", "Pensión diaria bruta (C39 = C38×C35)", f"${det['pension_diaria_raw']:,.4f}"),
#        ("", "Cota inferior: UMA diaria (C42)", f"${det['cota_inferior']:,.2f}"),
#        ("", "Cota superior: 100%×salario diario (C41)", f"${det['cota_superior']:,.2f}"),
#        ("", "Pensión diaria (C44) — clamp", f"${det['pension_diaria']:,.4f}"),
#        ("", "Pensión mensual (C45 = C44×365/12)", f"${det['pension_mensual']:,.2f}"),
#        ("Paso 13", "Tasa de reemplazo (C49 = C45 / (C5×30))", f"{det['tasa_reemplazo']:.4%}"),
#   ]
#
#    st.dataframe(pd.DataFrame(pasos, columns=["Paso", "Concepto", "Valor"]), use_container_width=True, hide_index=True)


# ── Análisis e interpretación ───────────────────────────────────────────
    with st.expander("💬 Análisis e interpretación"):
        delta_medio = df["Δ Marginal (pp)"].dropna().mean()
        rr_min = df.iloc[0]
        rr_max = df.iloc[-1]
        st.markdown(
            f"""
**Trade-off de jubilarse antes vs. después**
- A los **{int(rr_min['Edad'])} años**: pensión ${rr_min['Pensión Mensual (MXN)']:,.0f}/mes (RR {rr_min['Tasa de Reemplazo']:.1%})
- A los **{int(rr_max['Edad'])} años**: pensión ${rr_max['Pensión Mensual (MXN)']:,.0f}/mes (RR {rr_max['Tasa de Reemplazo']:.1%})

**Pendiente promedio de la RR:** {delta_medio:+.2f} pp por año adicional de espera.

**Parámetros usados**
- Densidad: {int(float(densidad)*100)}% · Semanas existentes {"incluidas" if include_existing else "excluidas"}
- Factor familiar: {det['factor_familiar']:.4f}
  = (1+{float(pct_conyuge):.0%}) × (1+{float(pct_hijos):.0%}) × (1+{float(pct_art14):.0%})
- UMA vigente: ${float(uma_diaria):.2f}/día
"""
        )


if __name__ == "__main__":
    render()
