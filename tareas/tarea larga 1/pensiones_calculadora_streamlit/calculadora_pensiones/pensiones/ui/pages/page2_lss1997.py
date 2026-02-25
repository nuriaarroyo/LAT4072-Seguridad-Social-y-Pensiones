from __future__ import annotations

import numpy as np
import streamlit as st

from pensiones.core.lss1997_ret import (
    replacement_rate_lss1997,
    solve_voluntary_rate_for_target,
    rr_curve,
)

import plotly.express as px


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

    col1, col2 = st.columns([1, 1], gap="large")

    # -------------------------
    # ENTRADAS (col1)
    # -------------------------
    with col1:
        st.subheader("Entradas")

        with st.form("form_lss97", border=False):
            with st.expander("👤 Biométricos del trabajador", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre = st.text_input("Nombre")
                    age_now = st.number_input(
                        "Edad actual x", min_value=15, max_value=80, value=30, step=1
                    )
                with c2:
                    exp_retirement_age = st.number_input(
                        "Edad esperada de jubilación",
                        min_value=50,
                        max_value=80,
                        value=65,
                        step=1,
                    )
                    gender = st.selectbox(
                        "Género", options=["Masculino", "Femenino"], index=0
                    )

            with st.expander("👨‍👩‍👧 Dependientes económicos", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    dependientes = st.number_input(
                        "Número de dependientes", min_value=0, value=0, step=1
                    )
                with c2:
                    partner = st.selectbox(
                        "¿Tiene pareja con derecho a pensión por viudez?",
                        options=["No", "Sí"],
                        index=0,
                    )
                    partner_age = None
                    gender_partner = None
                    if partner == "Sí":
                        partner_age = st.number_input(
                            "Edad pareja", min_value=15, max_value=80, value=30, step=1
                        )
                        gender_partner = st.selectbox(
                            "Género pareja", options=["Masculino", "Femenino"], index=1
                        )

            with st.expander("💼 Salario e historial", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    salary_monthly = st.slider(
                        "Salario mensual y [MXN]",
                        min_value=0.0,
                        max_value=80000.0,
                        value=20000.0,
                        step=100.0,
                    )
                    weeks_now = st.number_input(
                        "Semanas cotizadas hasta ahora",
                        min_value=0,
                        max_value=3000,
                        value=500,
                        step=1,
                    )
                with c2:
                    crecimiento = (
                        st.number_input(
                            "Crecimiento salarial anual (%)", value=0.0, step=0.5
                        )
                        / 100
                    )

            with st.expander("💰 Aportaciones & otros", expanded=False):
                st.caption("Estos valores vienen del JSON, pero puedes ajustarlos si quieres.")
                target_rr = st.slider("Tasa de reemplazo objetivo", 0.0, 1.2, 0.70)
                v_min = st.slider("Voluntaria mínima (para curva)", 0.0, 0.30, 0.0)
                v_max = st.slider("Voluntaria máxima (para curva)", 0.0, 0.30, 0.20)
                n_pts = st.slider("Puntos curva", 10, 100, 40)

            submitted = st.form_submit_button("Calcular")

    # -------------------------
    # RESULTADOS (col2)
    # -------------------------
    with col2:
        st.subheader("Resultados")

        if not submitted:
            st.info("Ingresa valores y presiona **Calcular**.")
            return

        # Nota: por ahora tu core usa (age_now, salary_monthly, target_rr)
        # Mantengo variables aunque aún no entren (exp_retirement_age, weeks_now, crecimiento, dependientes, partner...)
        sol = solve_voluntary_rate_for_target(
            age_now=int(age_now),
            salary_monthly=float(salary_monthly),
            target_rr=float(target_rr),
        )

        out = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(sol["voluntary_rate"]),
        )

        st.metric("Ahorro voluntario requerido", f"{sol['voluntary_rate']:.2%}")
        st.metric("RR alcanzada (modelo)", f"{sol['achieved_rr']:.2%}")
        st.metric("Pensión mensual estimada", f"$ {out['pension_monthly']:,.2f}")

        # (Opcional) mini-debug para ti, sin ensuciar:
        with st.expander("Ver inputs usados (debug)", expanded=False):
            st.write(
                {
                    "nombre": nombre,
                    "age_now": int(age_now),
                    "exp_retirement_age": int(exp_retirement_age),
                    "gender": gender,
                    "dependientes": int(dependientes),
                    "partner": partner,
                    "partner_age": partner_age,
                    "gender_partner": gender_partner,
                    "salary_monthly": float(salary_monthly),
                    "weeks_now": int(weeks_now),
                    "crecimiento": float(crecimiento),
                    "target_rr": float(target_rr),
                    "v_min": float(v_min),
                    "v_max": float(v_max),
                    "n_pts": int(n_pts),
                }
            )

    # -------------------------
    # CURVA (full width)
    # -------------------------
    st.subheader("Curva: RR vs. contribución voluntaria")

    if v_max <= v_min:
        st.warning("Para graficar, asegura voluntaria máxima > voluntaria mínima.")
        return

    rates = np.linspace(float(v_min), float(v_max), int(n_pts))
    df = rr_curve(int(age_now), float(salary_monthly), rates)

    fig = px.line(
        df,
        x="voluntary_rate",
        y="replacement_rate",
        title="Tasa de reemplazo vs contribución voluntaria",
        labels={
            "voluntary_rate": "Tasa de contribución voluntaria",
            "replacement_rate": "Tasa de reemplazo",
        },
        markers=True,
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        title_x=0.5,
    )

    st.plotly_chart(fig, use_container_width=True)

    html = fig.to_html(include_plotlyjs="cdn").encode("utf-8")
    st.download_button(
        "Descargar gráfica (HTML)",
        data=html,
        file_name="lss1997_rr_vs_voluntaria.html",
        mime="text/html",
    )

    with st.expander("Comentarios (para tu archivo separado)"):
        st.write(
            "Comenta: sensibilidad de RR a voluntaria, si hay rendimientos reales altos/bajos en supuestos, "
            "y cómo cambia el esfuerzo requerido para la meta."
        )