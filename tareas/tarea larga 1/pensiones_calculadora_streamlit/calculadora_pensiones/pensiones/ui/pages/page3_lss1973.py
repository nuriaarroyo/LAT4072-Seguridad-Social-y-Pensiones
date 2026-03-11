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
Replica fielmente la lógica de 13 pasos del Excel
'Calculo_Pension_Cesantia_Edad_Avanzada_Vejez_LSS_1973'
por Dr. Francisco García Castillo
"""


def render() -> None:

    st.header("🏛️ LSS 1973 — Cesantía en Edad Avanzada y Vejez")
    st.caption(DISPLAY)

    with st.expander("ℹ️ ¿Qué hace esta calculadora?", expanded=False):
        st.markdown(
            """
Calcula la **pensión mensual** y la **tasa de reemplazo** bajo la **Ley del Seguro Social de 1973**,
siguiendo los 13 pasos del cálculo.

**Resultado principal:** tabla por edades (60–65) + gráfica RR y pensión + detalle paso a paso.
"""
        )

    # ── Sidebar ─────────────────────────────────────────
    with st.sidebar:
        pass

    st.header("⚙️ Datos del trabajador")

    nombre = st.text_input("Nombre", value="Trabajador")

    st.subheader("Perfil laboral")

    edad_actual = st.number_input(
        "Edad actual", min_value=15, max_value=80, value=55, step=1
    )

    semanas_cot = st.number_input(
        "Semanas cotizadas actualmente",
        min_value=0,
        max_value=5000,
        value=650,
        step=1,
    )

    # ── Salario ─────────────────────────────────────────
    st.subheader("Salario (Paso 1)")

    sal_mensual = st.number_input(
        "Salario mensual promedio últimas 250 sem. (MXN)",
        min_value=0.0,
        value=60000.0,
        step=500.0,
    )

    sal_diario = float(sal_mensual) / 30
    st.caption(f"Salario diario: **${sal_diario:,.4f}**")

    # ── Densidad ─────────────────────────────────────────
    st.subheader("Densidad de cotización")

    densidad = st.radio(
        "Densidad",
        [0.80, 1.00],
        format_func=lambda x: f"{int(x*100)}%",
        horizontal=True,
    )

    include_existing = st.checkbox(
        "Incluir semanas ya cotizadas",
        value=True,
    )

    # ── Factores familiares ─────────────────────────────
    st.subheader("Factores familiares")

    conyuge = st.checkbox("Tiene cónyuge / aplica asignación familiar", value=True)

    # 15% en ambos casos como solicitaste
    pct_conyuge = 0.15

    n_hijos = st.number_input(
        "Hijos en sistema educativo (≤25 años)",
        0,
        10,
        0,
        step=1,
    )

    pct_hijos = n_hijos * 0.10

    # Artículo 14 asumido
    pct_art14 = 0.11

    # ── UMA ─────────────────────────────────────────────
    st.subheader("UMA / SMGV")

    uma_diaria = st.number_input(
        "UMA diaria vigente (MXN)",
        min_value=50.0,
        value=float(UMA_DIARIA_DEFAULT),
        step=0.01,
    )

    # ── Edades fijas ────────────────────────────────────
    min_age = 60
    max_age = 65

    st.info("El cálculo se realiza automáticamente para edades **60 a 65 años**.")

    st.divider()

    calcular = st.button("🔢 Calcular", type="primary", use_container_width=True)

    if not calcular:
        st.info("Ingresa los datos y presiona **Calcular**.")
        return

    # ── Cálculos ────────────────────────────────────────
    df = tabla_sensibilidades_lss1973(
        edad_actual=int(edad_actual),
        salario_diario_avg=float(sal_diario),
        semanas_cotizadas=int(semanas_cot),
        min_age=min_age,
        max_age=max_age,
        densidad=float(densidad),
        pct_conyuge=float(pct_conyuge),
        pct_hijos_total=float(pct_hijos),
        pct_art14=float(pct_art14),
        uma_diaria=float(uma_diaria),
        include_existing=bool(include_existing),
    )

    best = df.loc[df["Tasa de Reemplazo"].idxmax()]
    worst = df.loc[df["Tasa de Reemplazo"].idxmin()]

    # ── Métricas ────────────────────────────────────────
    st.subheader(
        f"📊 Resultados — {nombre} · Densidad {int(float(densidad)*100)}% · Salario ${sal_mensual:,.2f}/mes"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Mejor tasa de reemplazo", f"{best['Tasa de Reemplazo']:.2%}")
    c2.metric("Edad óptima", str(int(best["Edad"])))
    c3.metric("Pensión mensual óptima", f"${best['Pensión Mensual (MXN)']:,.2f}")
    c4.metric(
        "Ganancia RR al esperar",
        f"+{(best['Tasa de Reemplazo'] - worst['Tasa de Reemplazo']) * 100:.2f} pp",
    )

    st.divider()

    # ── Tabla ───────────────────────────────────────────
    st.subheader("📋 Tabla de sensibilidades")

    fmt = {
        "Pensión Mensual (MXN)": "${:,.2f}",
        "Tasa de Reemplazo": "{:.4%}",
    }

    st.dataframe(
        df.style.format(fmt),
        use_container_width=True,
        hide_index=True,
    )

    # ── Gráfica ─────────────────────────────────────────
    st.subheader("📈 Gráfica")

    fig, ax1 = plt.subplots(figsize=(8, 4.5))

    ages = df["Edad"]
    rr_pct = df["Tasa de Reemplazo"] * 100
    pensions = df["Pensión Mensual (MXN)"]

    ax1.plot(ages, rr_pct, "o-", label="Tasa de reemplazo (%)")

    ax2 = ax1.twinx()
    ax2.plot(ages, pensions, "s--", label="Pensión mensual")

    ax1.set_xlabel("Edad de jubilación")
    ax1.set_ylabel("Tasa de reemplazo (%)")
    ax2.set_ylabel("Pensión mensual (MXN)")

    ax1.grid(True, alpha=0.3)

    fig.tight_layout()

    st.pyplot(fig)

    # ── Detalle paso a paso ─────────────────────────────
    st.subheader("🔍 Detalle paso a paso")

    edad_sel = st.selectbox(
        "Selecciona la edad de retiro:",
        list(range(min_age, max_age + 1)),
        index=5,
    )

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

    st.write(det)


if __name__ == "__main__":
    render()