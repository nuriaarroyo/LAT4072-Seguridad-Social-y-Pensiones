from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from pensiones.core.lss1997_ret import (
    replacement_rate_lss1997,
    solve_voluntary_rate_for_target,
    rr_curve,
)


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

    # =========================
    # ENTRADAS (col1)
    # =========================
    with col1:
        st.subheader("Entradas")

        with st.form("form_lss97", border=False):
            with st.expander("👤 Biométricos del trabajador", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre = st.text_input("Nombre")
                    age_now = st.number_input(
                        "Edad actual x", min_value=15, max_value=100, value=30, step=1
                    )
                with c2:
                    exp_retirement_age = st.number_input(
                        "Edad esperada de jubilación",
                        min_value=16,
                        max_value=100,
                        value=65,
                        step=1,
                    )
                    gender_ui = st.selectbox(
                        "Género", options=["Masculino", "Femenino"], index=0
                    )

            """with st.expander("👨‍👩‍👧 Dependientes económicos", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
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
                            "Género pareja",
                            options=["Masculino", "Femenino"],
                            index=1,
                        )
                with c2:
                    dependientes = st.number_input(
                        "Número de dependientes", min_value=0, value=0, step=1
                    )
"""
            with st.expander("💼 Salario e historial", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    salary_monthly = st.slider(
                        "Salario mensual [MXN] (SBC)",
                        min_value=0.0,
                        max_value= 100000.0,
                        value=20000.0,
                        step=100.0,
                    )
                    
                with c2:
                    vol_actual = st.slider(
                        "Tasa de contribución voluntaria actual",
                        min_value=0.0,
                        max_value=0.50,
                        value=0.0,
                        step=0.01,
                    )

            with st.expander("📈 Semanas y saldo", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    weeks_now = st.number_input(
                        "Semanas cotizadas hasta ahora",
                        min_value=0,
                        max_value=3000,
                        value=0,
                        step=50,
                    )
                with c2:
                    saldo_actual = st.number_input(
                        "Saldo actual en cuenta individual (opcional) [MXN]",
                        min_value=0.0,
                        value=0.0,
                        step=1000.0,
                    )

                st.caption(
                    "Si saldo_actual > 0, el core puede usarlo como SCI0 (si lo conectaste en lss1997_ret). "
                    "Si no, puede aproximar con semanas (si así lo dejaste)."
                )

            with st.expander("🎯 Objetivo & curva", expanded=True):
                st.caption("Estos valores alimentan el solver y la gráfica.")
                target_rr = st.slider("Tasa de reemplazo objetivo", 0.0, 1.2, 0.70)
                v_min = st.slider("Voluntaria mínima (para curva)", 0.0, 0.30, 0.0)
                v_max = st.slider("Voluntaria máxima (para curva)", 0.0, 0.30, 0.20)
                n_pts = st.slider("Puntos curva", 10, 100, 40)

                udi_mxn = st.number_input(
                    "Tipo de cambio UDI (MXN por UDI) — para mostrar montos en UDIs",
                    min_value=0.0001,
                    value=8.50,
                    step=0.01,
                )

            submitted = st.form_submit_button("Calcular")

    # =========================
    # RESULTADOS (col2)
    # =========================
    with col2:
        st.subheader("Resultados")

        if not submitted:
            st.info("Ingresa valores y presiona **Calcular**.")
            return

        # ---------- helpers ----------
        def mxn(x: float) -> str:
            return f"$ {x:,.2f}"

        def pct(x: float) -> str:
            return f"{x:.2%}"

        def udi(x_mxn: float, udi_mxn_: float) -> float:
            return x_mxn / udi_mxn_ if udi_mxn_ > 0 else np.nan

        # ---------- assumptions / overrides ----------
        gender_core = "male" if gender_ui == "Masculino" else "female"

        overrides = {
            "default_retirement_age": int(exp_retirement_age),
            "default_weeks_now": int(weeks_now),
            #"default_annual_return": float(annual_return),
            "default_gender": gender_core,
            #"pg_mensual": 5000.0,  # TODO: cambia a input/tabla real cuando la conectes
        }

        if float(saldo_actual) > 0.0:
            overrides["saldo_actual"] = float(saldo_actual)

        # ---------- 1) Escenario ACTUAL ----------
        out_actual = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(vol_actual),
            assumptions=overrides,
        )

        # ---------- 2) Solver y escenario REQUERIDO ----------
        sol = solve_voluntary_rate_for_target(
            age_now=int(age_now),
            salary_monthly=float(salary_monthly),
            target_rr=float(target_rr),
            lo=float(v_min),
            hi=float(v_max),
            assumptions=overrides,
        )

        out_req = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(sol["voluntary_rate"]),
            assumptions=overrides,
        )

        # ---------- 3) Aportes (display) ----------
        contrib_vol_mxn_mes_actual = float(salary_monthly) * float(vol_actual)
        contrib_vol_mxn_mes_req = float(salary_monthly) * float(sol["voluntary_rate"])
        delta_contrib_mxn_mes = contrib_vol_mxn_mes_req - contrib_vol_mxn_mes_actual
        delta_rate = float(sol["voluntary_rate"]) - float(vol_actual)

        # ---------- métricas top (compacto) ----------
        st.metric("RR (voluntaria actual)", pct(float(out_actual["replacement_rate"])))
        st.metric("Pensión (voluntaria actual)", mxn(float(out_actual["pension_monthly"])))

        st.divider()

        st.markdown("### Contribución voluntaria")
        cA, cB, cC = st.columns(3)
        with cA:
            st.metric("Actual", pct(float(vol_actual)))
        with cB:
            st.metric("Requerida (RR objetivo)", pct(float(sol["voluntary_rate"])))
        with cC:
            st.metric("Incremento", f"{delta_rate*100:.2f} pp")

        st.markdown("### Aporte voluntario estimado (sobre salario mensual)")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Actual (MXN/mes)", mxn(contrib_vol_mxn_mes_actual))
        with c2:
            st.metric("Requerido (MXN/mes)", mxn(contrib_vol_mxn_mes_req))
        with c3:
            st.metric("Incremento (MXN/mes)", mxn(delta_contrib_mxn_mes))

        st.markdown("### Equivalente en UDIs")
        u1, u2, u3 = st.columns(3)
        with u1:
            st.metric("Actual (UDI/mes)", f"{udi(contrib_vol_mxn_mes_actual, float(udi_mxn)):,.2f}")
        with u2:
            st.metric("Requerido (UDI/mes)", f"{udi(contrib_vol_mxn_mes_req, float(udi_mxn)):,.2f}")
        with u3:
            st.metric("Incremento (UDI/mes)", f"{udi(delta_contrib_mxn_mes, float(udi_mxn)):,.2f}")

        st.markdown("### Resultados del modelo (RR y pensión)")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric("RR actual", pct(float(out_actual["replacement_rate"])))
        with r2:
            st.metric("RR objetivo", pct(float(target_rr)))
        with r3:
            st.metric("RR requerido", pct(float(out_req["replacement_rate"])))

        p1, p2 = st.columns(2)
        with p1:
            st.metric("Pensión actual (MXN/mes)", mxn(float(out_actual["pension_monthly"])))
        with p2:
            st.metric("Pensión requerida (MXN/mes)", mxn(float(out_req["pension_monthly"])))

        # ---------- tabla resumen ----------
        summary = pd.DataFrame(
            [
                {
                    "Escenario": "Actual",
                    "Tasa voluntaria": float(vol_actual),
                    "Aporte vol (MXN/mes)": contrib_vol_mxn_mes_actual,
                    "Aporte vol (UDI/mes)": udi(contrib_vol_mxn_mes_actual, float(udi_mxn)),
                    "RR": float(out_actual["replacement_rate"]),
                    "Pensión (MXN/mes)": float(out_actual["pension_monthly"]),
                    "Pensión (UDI/mes)": udi(float(out_actual["pension_monthly"]), float(udi_mxn)),
                },
                {
                    "Escenario": "Requerido",
                    "Tasa voluntaria": float(sol["voluntary_rate"]),
                    "Aporte vol (MXN/mes)": contrib_vol_mxn_mes_req,
                    "Aporte vol (UDI/mes)": udi(contrib_vol_mxn_mes_req, float(udi_mxn)),
                    "RR": float(out_req["replacement_rate"]),
                    "Pensión (MXN/mes)": float(out_req["pension_monthly"]),
                    "Pensión (UDI/mes)": udi(float(out_req["pension_monthly"]), float(udi_mxn)),
                },
            ]
        )

        st.dataframe(
            summary.style.format(
                {
                    "Tasa voluntaria": "{:.2%}",
                    "Aporte vol (MXN/mes)": "$ {:,.2f}",
                    "Aporte vol (UDI/mes)": "{:,.2f}",
                    "RR": "{:.2%}",
                    "Pensión (MXN/mes)": "$ {:,.2f}",
                    "Pensión (UDI/mes)": "{:,.2f}",
                }
            ),
            use_container_width=True,
        )

        with st.expander("Ver inputs usados (debug)", expanded=False):
            st.write(
                {
                    "nombre": nombre,
                    "age_now": int(age_now),
                    "exp_retirement_age": int(exp_retirement_age),
                    "gender_ui": gender_ui,
                    "gender_core": gender_core,
                    """"dependientes": int(dependientes),
                    "partner": partner,
                    "partner_age": partner_age,
                    "gender_partner": gender_partner,"""
                    "salary_monthly": float(salary_monthly),
                    "weeks_now": int(weeks_now),
                    # quiero llamarlo del jsson 
                    #"annual_return": float(annual_return),
                    "saldo_actual": float(saldo_actual),
                    "target_rr": float(target_rr),
                    "v_min": float(v_min),
                    "v_max": float(v_max),
                    "n_pts": int(n_pts),
                    "udi_mxn": float(udi_mxn),
                    "solver": sol,
                    "out_actual_keys": list(out_actual.keys()),
                    "out_req_keys": list(out_req.keys()),
                }
            )

    # =========================
    # CURVA (full width)
    # =========================
    st.subheader("Curva: RR vs. contribución voluntaria")

    if v_max <= v_min:
        st.warning("Para graficar, asegura voluntaria máxima > voluntaria mínima.")
        return

    rates = np.linspace(float(v_min), float(v_max), int(n_pts))

    df = rr_curve(
        int(age_now),
        float(salary_monthly),
        rates,
        assumptions=overrides,
    )

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

    # Línea: voluntaria actual
    fig.add_vline(
        x=float(vol_actual),
        line_width=2,
        line_dash="dot",
    )

    # Línea: voluntaria requerida
    fig.add_vline(
        x=float(sol["voluntary_rate"]),
        line_width=2,
        line_dash="dash",
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
            "Comenta: sensibilidad de RR a voluntaria, cómo cambia con rendimiento/edad retiro/semanas "
            "y el impacto del supuesto de mortalidad por género."
        )