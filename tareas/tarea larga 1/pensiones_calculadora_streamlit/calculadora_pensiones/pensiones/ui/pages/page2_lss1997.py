from __future__ import annotations

import numpy as np
import streamlit as st

from pensiones.core.lss1997_ret import (
    replacement_rate_lss1997,
    solve_voluntary_rate_for_target,
    rr_curve,
)
from pensiones.utils.plotting import line_plot, save_fig

def render():
    st.header("II) LSS 1997 — Tasa de reemplazo por cesantía en edad avanzada y vejez")

    with st.expander("Qué hace esta sección", expanded=True):
        st.write(
    """
    - Estima la tasa de reemplazo (CESANTÍA/VEJEZ) para edad x
    - Encuentra la tasa de ahorro voluntario adicional necesaria para una RR objetivo
    - Grafica RR (tasa de reemplazo) vs. diferentes tasas de contribución voluntaria
    """
)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Entradas")
        with st.form("form_lss97"):
            age_now = st.number_input("Edad actual x", min_value=15, max_value=80, value=30, step=1)
            salary_monthly = st.number_input("Salario mensual y [MXN]", min_value=0.0, value=20000.0, step=500.0)
            target_rr = st.slider("Tasa de reemplazo objetivo", 0.0, 1.2, 0.70)
            v_min = st.slider("Voluntaria mínima (para curva)", 0.0, 0.30, 0.0)
            v_max = st.slider("Voluntaria máxima (para curva)", 0.0, 0.30, 0.20)
            n_pts = st.slider("Puntos curva", 10, 100, 40)
            #save_plots = st.checkbox("Guardar gráfica en plots/", value=True)
            submitted = st.form_submit_button("Calcular")

    if not submitted:
        st.info("Ingresa valores y presiona **Calcular**.")
        return

    sol = solve_voluntary_rate_for_target(
        age_now=int(age_now),
        salary_monthly=float(salary_monthly),
        target_rr=float(target_rr),
    )
    out = replacement_rate_lss1997(int(age_now), float(salary_monthly), float(sol["voluntary_rate"]))

    with col2:
        st.subheader("Resultados")
        st.metric("Ahorro voluntario requerido", f"{sol['voluntary_rate']:.2%}")
        st.metric("RR alcanzada (modelo)", f"{sol['achieved_rr']:.2%}")
        st.metric("Pensión mensual estimada", f"$ {out['pension_monthly']:,.2f}")

    st.subheader("Curva: RR vs. contribución voluntaria")
    if v_max <= v_min:
        st.warning("Para graficar, asegura voluntaria máxima > voluntaria mínima.")
        return

    rates = np.linspace(float(v_min), float(v_max), int(n_pts))
    df = rr_curve(int(age_now), float(salary_monthly), rates)

    import plotly.express as px

    fig = px.line(
        df,
        x="voluntary_rate",
        y="replacement_rate",
        title="Tasa de reemplazo vs contribución voluntaria",
        labels={
            "voluntary_rate": "Tasa de contribución voluntaria",
            "replacement_rate": "Tasa de reemplazo"
        },
        markers=True
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        title_x=0.5
    )

    st.plotly_chart(fig, use_container_width=True)
    # fig = line_plot(
    #    df=df,
     #   x="voluntary_rate",
    #    y_cols=["replacement_rate"],
    #    title="Tasa de reemplazo vs contribución voluntaria",
    #    xlabel="Tasa de contribución voluntaria",
    #    ylabel="Tasa de reemplazo"
    #)
    #st.pyplot(fig, clear_figure=False)

    #if save_plots:
    #    path = save_fig(fig, out_dir="plots", filename="lss1997_rr_vs_voluntaria.png")
    #    st.success(f"Gráfica guardada en: {path}")
    html = fig.to_html(include_plotlyjs="cdn").encode("utf-8")
    st.download_button(
        "Descargar gráfica (HTML)",
        data=html,
        file_name="lss1997_rr_vs_voluntaria.html",
        mime="text/html"
    )


    with st.expander("Comentarios (para tu archivo separado)"):
        st.write(
            "Comenta: sensibilidad de RR a voluntaria, si hay rendimientos reales altos/bajos en supuestos, "
            "y cómo cambia el esfuerzo requerido para la meta."
        )
