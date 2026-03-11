from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from pensiones.core.lss1997_ret import (
    replacement_rate_lss1997,
    solve_voluntary_rate_for_target,
    rr_curve,
    trayectoria_salarial,
    trayectoria_pension,
)


def render():
    st.header("II) LSS 1997 — Tasa de reemplazo por cesantía en edad avanzada y vejez")

    with st.expander("Qué hace esta sección", expanded=True):
        st.write(
            """
- Estima la tasa de reemplazo (cesantía/vejez) para una edad de retiro elegida
- Encuentra la tasa de ahorro voluntario adicional necesaria para una RR objetivo
- Grafica la RR contra diferentes tasas de contribución voluntaria
- Muestra la trayectoria salarial hasta el retiro y la trayectoria de la pensión hasta la muerte esperada
- Compara la pensión del modelo contra la pensión implícita de la RR objetivo sobre el salario final
"""
        )

    col1, col2 = st.columns([1, 1], gap="large")

    # =========================
    # ENTRADAS (col1)
    # =========================
    with col1:
        st.subheader("Entradas")

        # =====================================
        # FUERA DEL FORM: UMA + salario sincronizado
        # =====================================
        with st.expander("💼 Salario base de cotización", expanded=True):
            c1, c2, c3 = st.columns(3)

            with c1:
                uma_mxn = st.number_input(
                    "UMA mensual [MXN]",
                    min_value=1.0,
                    value=3566.22,
                    step=1.0,
                )

            if "sbc_uma" not in st.session_state:
                st.session_state.sbc_uma = 5.0

            if "salary_monthly" not in st.session_state:
                st.session_state.salary_monthly = float(st.session_state.sbc_uma * uma_mxn)

            if "last_uma_mxn" not in st.session_state:
                st.session_state.last_uma_mxn = float(uma_mxn)

            if float(st.session_state.last_uma_mxn) != float(uma_mxn):
                st.session_state.salary_monthly = float(st.session_state.sbc_uma * uma_mxn)
                st.session_state.last_uma_mxn = float(uma_mxn)

            def sync_from_uma():
                st.session_state.salary_monthly = float(st.session_state.sbc_uma * uma_mxn)

            def sync_from_mxn():
                st.session_state.sbc_uma = float(st.session_state.salary_monthly / uma_mxn)

            with c2:
                st.slider(
                    "SBC mensual [UMA]",
                    min_value=1.0,
                    max_value=25.0,
                    step=0.1,
                    key="sbc_uma",
                    on_change=sync_from_uma,
                )

            with c3:
                st.number_input(
                    "SBC mensual [MXN]",
                    min_value=float(1.0 * uma_mxn),
                    max_value=float(25.0 * uma_mxn),
                    step=100.0,
                    key="salary_monthly",
                    on_change=sync_from_mxn,
                )

            sbc_uma = float(st.session_state.sbc_uma)
            salary_monthly = float(st.session_state.salary_monthly)

            st.caption(
                f"SBC actual: {sbc_uma:.4f} UMA = $ {salary_monthly:,.2f} MXN"
            )

        # =====================================
        # DENTRO DEL FORM: resto de inputs
        # =====================================
        with st.form("form_lss97", border=False):
            with st.expander("⚙️ Supuestos base", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    udi_mxn = st.number_input(
                        "UDI [MXN]",
                        min_value=0.0001,
                        value=8.50,
                        step=0.01,
                    )
                with c2:
                    year_now = st.number_input(
                        "Año actual",
                        min_value=2021,
                        max_value=2100,
                        value=2026,
                        step=1,
                    )

            with st.expander("👤 Biométricos del trabajador", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    nombre = st.text_input("Nombre")
                    age_now = st.number_input(
                        "Edad actual x",
                        min_value=15,
                        max_value=100,
                        value=30,
                        step=1,
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
                        "Género",
                        options=["Masculino", "Femenino"],
                        index=0,
                    )

            with st.expander("📈 Ahorro y crecimiento", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    vol_actual = st.slider(
                        "Tasa de contribución voluntaria actual",
                        min_value=0.0,
                        max_value=0.50,
                        value=0.0,
                        step=0.01,
                    )
                with c2:
                    salary_growth_annual = st.number_input(
                        "Crecimiento salarial real anual",
                        min_value=0.0,
                        max_value=0.08,
                        value=0.015,
                        step=0.005,
                        format="%.3f",
                    )

            with st.expander("📈 Semanas y saldo", expanded=True):
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
                    "Si saldo_actual > 0, el core usa ese saldo como SCI inicial. "
                    "Si no, aproxima el saldo con semanas cotizadas y trayectoria salarial."
                )

            with st.expander("🎯 Objetivo y curva", expanded=True):
                st.caption("Estos valores alimentan el solver y la gráfica.")
                target_rr = st.slider("Tasa de reemplazo objetivo", 0.0, 1.0, 0.70)
                v_min = st.slider("Voluntaria mínima (para curva)", 0.0, 0.30, 0.0)
                v_max = st.slider("Voluntaria máxima (para curva)", 0.0, 0.50, 0.20)
                n_pts = st.slider("Puntos curva", 10, 100, 40)

            submitted = st.form_submit_button("Calcular")

    # =========================
    # RESULTADOS (col2)
    # =========================
    with col2:
        st.subheader("Resultados")

        if not submitted:
            st.info("Ingresa valores y presiona **Calcular**.")
            return

        def mxn(x: float) -> str:
            return f"$ {x:,.2f}"

        def pct(x: float) -> str:
            return f"{x:.2%}"

        def udi(x_mxn: float, udi_mxn_: float) -> float:
            return x_mxn / udi_mxn_ if udi_mxn_ > 0 else np.nan

        if exp_retirement_age <= age_now:
            st.error("La edad esperada de jubilación debe ser mayor que la edad actual.")
            return

        gender_core = "male" if gender_ui == "Masculino" else "female"

        overrides = {
            "default_retirement_age": int(exp_retirement_age),
            "default_weeks_now": int(weeks_now),
            "default_gender": gender_core,
            "default_salary_growth_annual": float(salary_growth_annual),
            "year_now": int(year_now),
        }

        if float(saldo_actual) > 0.0:
            overrides["saldo_actual"] = float(saldo_actual)

        traj_sal = trayectoria_salarial(
            age_now=int(age_now),
            age_ret=int(exp_retirement_age),
            salary_monthly=float(salary_monthly),
            salary_growth_annual=float(salary_growth_annual),
            year_now=int(year_now),
        )

        salary_final = float(out_actual["salary_retirement_monthly"])

        
        years_to_ret = int(exp_retirement_age - age_now)
        growth_factor = salary_final / float(salary_monthly) if float(salary_monthly) > 0 else np.nan

        out_actual = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(vol_actual),
            assumptions=overrides,
        )

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

        contrib_vol_mxn_mes_actual = float(salary_monthly) * float(vol_actual)
        contrib_vol_mxn_mes_req = float(salary_monthly) * float(sol["voluntary_rate"])
        delta_contrib_mxn_mes = contrib_vol_mxn_mes_req - contrib_vol_mxn_mes_actual
        delta_rate = float(sol["voluntary_rate"]) - float(vol_actual)

        pension_target_on_final_salary = float(target_rr) * float(salary_final)

        rr_actual_on_final = (
            float(out_actual["pension_monthly"]) / float(salary_final)
            if salary_final > 0 else np.nan
        )
        rr_req_on_final = (
            float(out_req["pension_monthly"]) / float(salary_final)
            if salary_final > 0 else np.nan
        )

        pension_gap_req_vs_target = float(out_req["pension_monthly"]) - pension_target_on_final_salary
        pension_gap_actual_vs_target = float(out_actual["pension_monthly"]) - pension_target_on_final_salary

        st.markdown("### Resumen rápido")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("RR (voluntaria actual)", pct(float(out_actual["replacement_rate"])))
        with m2:
            st.metric("Pensión (voluntaria actual)", mxn(float(out_actual["pension_monthly"])))

        st.divider()

        st.markdown("### Salario de referencia")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Salario mensual actual", mxn(float(salary_monthly)))
        with s2:
            st.metric("Salario mensual final", mxn(float(salary_final)))
        with s3:
            st.metric("Multiplicador salarial", f"{growth_factor:.2f}x")

        st.caption(
            f"Años al retiro: {years_to_ret} | "
            f"Crecimiento salarial real anual supuesto: {salary_growth_annual:.2%}"
        )

        st.markdown("### Contribución voluntaria")
        cA, cB, cC = st.columns(3)
        with cA:
            st.metric("Actual", pct(float(vol_actual)))
        with cB:
            st.metric("Requerida (solver)", pct(float(sol['voluntary_rate'])))
        with cC:
            st.metric("Incremento", f"{delta_rate * 100:.2f} pp")

        st.markdown("### Aporte voluntario estimado (sobre salario mensual actual)")
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

        st.markdown("### RR y pensión: modelo vs referencia sobre salario final")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric("RR objetivo", pct(float(target_rr)))
        with r2:
            st.metric("RR modelo requerida", pct(float(out_req["replacement_rate"])))
        with r3:
            st.metric("RR implícita req. / salario final", pct(float(rr_req_on_final)))

        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric("Pensión objetivo = RR obj × salario final", mxn(pension_target_on_final_salary))
        with p2:
            st.metric("Pensión requerida (modelo)", mxn(float(out_req["pension_monthly"])))
        with p3:
            st.metric("Brecha modelo - objetivo", mxn(pension_gap_req_vs_target))

        st.markdown("### Escenario actual sobre salario final")
        a1, a2, a3 = st.columns(3)
        with a1:
            st.metric("Pensión actual", mxn(float(out_actual["pension_monthly"])))
        with a2:
            st.metric("RR implícita actual / salario final", pct(float(rr_actual_on_final)))
        with a3:
            st.metric("Brecha actual - objetivo", mxn(pension_gap_actual_vs_target))

        with st.expander("Diagnóstico de posible inflación en la pensión", expanded=True):
            st.write(
                """
**Cómo leer estas cifras:**

1. **Pensión objetivo = RR objetivo × salario final**  
   Esta es la pensión que uno esperaría si la RR se interpretara literalmente sobre el salario al retiro.

2. **Pensión requerida (modelo)**  
   Es la que devuelve tu `replacement_rate_lss1997()` usando la tasa voluntaria hallada por el solver.

3. **RR implícita sobre salario final**  
   Se calcula como pensión mensual del modelo / salario mensual final.
   Si esta RR implícita es muy distinta a la RR objetivo, entonces la base salarial de tu core
   probablemente no coincide con el salario final que tú estás usando como referencia visual.
"""
            )

            d1, d2, d3, d4 = st.columns(4)
            with d1:
                st.metric("Salario actual", mxn(float(salary_monthly)))
            with d2:
                st.metric("Salario final", mxn(float(salary_final)))
            with d3:
                st.metric("Pensión objetivo", mxn(pension_target_on_final_salary))
            with d4:
                st.metric("Pensión modelo", mxn(float(out_req["pension_monthly"])))

        summary = pd.DataFrame(
            [
                {
                    "Escenario": "Actual",
                    "Tasa voluntaria": float(vol_actual),
                    "Aporte vol (MXN/mes)": contrib_vol_mxn_mes_actual,
                    "Aporte vol (UDI/mes)": udi(contrib_vol_mxn_mes_actual, float(udi_mxn)),
                    "RR modelo": float(out_actual["replacement_rate"]),
                    "Pensión modelo (MXN/mes)": float(out_actual["pension_monthly"]),
                    "RR implícita sobre salario final": float(rr_actual_on_final),
                    "Pensión objetivo sobre salario final (MXN/mes)": pension_target_on_final_salary,
                    "Brecha vs objetivo (MXN/mes)": pension_gap_actual_vs_target,
                },
                {
                    "Escenario": "Requerido",
                    "Tasa voluntaria": float(sol["voluntary_rate"]),
                    "Aporte vol (MXN/mes)": contrib_vol_mxn_mes_req,
                    "Aporte vol (UDI/mes)": udi(contrib_vol_mxn_mes_req, float(udi_mxn)),
                    "RR modelo": float(out_req["replacement_rate"]),
                    "Pensión modelo (MXN/mes)": float(out_req["pension_monthly"]),
                    "RR implícita sobre salario final": float(rr_req_on_final),
                    "Pensión objetivo sobre salario final (MXN/mes)": pension_target_on_final_salary,
                    "Brecha vs objetivo (MXN/mes)": pension_gap_req_vs_target,
                },
            ]
        )

        st.markdown("### Tabla resumen")
        st.dataframe(
            summary.style.format(
                {
                    "Tasa voluntaria": "{:.2%}",
                    "Aporte vol (MXN/mes)": "$ {:,.2f}",
                    "Aporte vol (UDI/mes)": "{:,.2f}",
                    "RR modelo": "{:.2%}",
                    "Pensión modelo (MXN/mes)": "$ {:,.2f}",
                    "RR implícita sobre salario final": "{:.2%}",
                    "Pensión objetivo sobre salario final (MXN/mes)": "$ {:,.2f}",
                    "Brecha vs objetivo (MXN/mes)": "$ {:,.2f}",
                }
            ),
            use_container_width=True,
        )

        with st.expander("Ver inputs y outputs usados (debug)", expanded=False):
            st.write(
                {
                    "nombre": nombre,
                    "age_now": int(age_now),
                    "exp_retirement_age": int(exp_retirement_age),
                    "gender_ui": gender_ui,
                    "gender_core": gender_core,
                    "uma_mxn_ui": float(uma_mxn),
                    "sbc_uma": float(sbc_uma),
                    "salary_monthly_actual": float(salary_monthly),
                    "salary_monthly_final": float(salary_final),
                    "salary_growth_annual": float(salary_growth_annual),
                    "weeks_now": int(weeks_now),
                    "saldo_actual": float(saldo_actual),
                    "target_rr": float(target_rr),
                    "target_pension_on_final_salary": float(pension_target_on_final_salary),
                    "vol_actual": float(vol_actual),
                    "v_min": float(v_min),
                    "v_max": float(v_max),
                    "n_pts": int(n_pts),
                    "udi_mxn": float(udi_mxn),
                    "solver": sol,
                    "annual_return_used": float(out_actual["annual_return"]),
                    "out_actual_keys": list(out_actual.keys()),
                    "out_req_keys": list(out_req.keys()),
                }
            )

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

    fig.add_vline(x=float(vol_actual), line_width=2, line_dash="dot")
    fig.add_vline(x=float(sol["voluntary_rate"]), line_width=2, line_dash="dash")

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
            "Comenta la sensibilidad de la RR a la voluntaria, cómo cambia con edad de retiro, "
            "semanas cotizadas, crecimiento salarial y el impacto del supuesto biométrico."
        )

    st.subheader("Trayectoria salarial y de pensión")

    traj_pen_actual = trayectoria_pension(
        pension_monthly=float(out_actual["pension_monthly"]),
        age_ret=int(exp_retirement_age),
        gender=gender_core,
        year_ret=out_actual["year_ret_real"],
    )

    traj_pen_req = trayectoria_pension(
        pension_monthly=float(out_req["pension_monthly"]),
        age_ret=int(exp_retirement_age),
        gender=gender_core,
        year_ret=out_req["year_ret_real"],
    )

    fig_sal = px.line(
        traj_sal,
        x="age",
        y=[c for c in ["salary_monthly", "sbc_monthly"] if c in traj_sal.columns],
        labels={"value": "Monto mensual", "age": "Edad", "variable": "Serie"},
        title="Trayectoria salarial y salario base de cotización",
    )
    st.plotly_chart(fig_sal, use_container_width=True)

    fig_pen_actual = px.line(
        traj_pen_actual,
        x="age",
        y="pension_monthly",
        labels={"pension_monthly": "Pensión mensual", "age": "Edad"},
        title="Pensión mensual esperada (escenario actual)",
    )
    st.plotly_chart(fig_pen_actual, use_container_width=True)

    fig_pen_req = px.line(
        traj_pen_req,
        x="age",
        y="pension_monthly",
        labels={"pension_monthly": "Pensión mensual", "age": "Edad"},
        title="Pensión mensual esperada (escenario requerido por solver)",
    )
    st.plotly_chart(fig_pen_req, use_container_width=True)