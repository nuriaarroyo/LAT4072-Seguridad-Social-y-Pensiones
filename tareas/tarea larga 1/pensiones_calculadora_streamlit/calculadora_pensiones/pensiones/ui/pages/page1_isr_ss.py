from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from pensiones.core.isr_2026 import isr_monthly
from pensiones.core.ss_1997 import ss_contributions_monthly, effective_rates
from pensiones.utils.plotting import line_plot, save_fig

def render():
    st.header("I) ISR 2026 + Seguridad Social (LSS 1997) + INFONAVIT")


    LEYENDA = """- Calcula ISR mensual (tarifa 2026)
            - ISR para nivel de ingresos en 2026 
            - Calcula cuotas mensuales IMSS + INFONAVIT desglose 
                    tipo de seguro
                    empleador
                    empleado
                    Gobierno
            - Reporta proporción de contribuciones vs. SBC
            - Grafica tasas efectivas (ISR y SS) por nivel de ingreso"""


    with st.expander("Qué hace esta sección", expanded=True):
        st.write(f"```text\n{LEYENDA}\n```")

    colL, colR = st.columns([1, 1])

    with colL:
        # Inputs  (ACA PUEDO AGREGAR VARIABLES)
        st.subheader("Entradas")
        with st.form("form_isr_ss"):
            salary_monthly = st.number_input("Sueldo mensual (ingreso gravable) [MXN]", min_value=0.0, value=20000.0, step=500.0)
            sbc_daily = st.number_input("SBC diario (Sueldo Base de Cotización) [MXN]", min_value=0.0, value=700.0, step=10.0)
            days = st.number_input("Días del mes", min_value=28, max_value=31, value=30, step=1)
            income_min = st.number_input("Ingreso mínimo para gráfica [MXN/mes]", min_value=0.0, value=5000.0, step=500.0)
            income_max = st.number_input("Ingreso máximo para gráfica [MXN/mes]", min_value=0.0, value=80000.0, step=500.0)
            n_points = st.slider("Puntos en la gráfica", min_value=10, max_value=80, value=40)
            #save_plots = st.checkbox("Guardar gráfica en carpeta plots/", value=True)
            submitted = st.form_submit_button("Calcular")

    if not submitted:
        st.info("Ingresa valores y presiona **Calcular**.")
        return

    # Cálculos
    isr_out = isr_monthly(salary_monthly)
    ss_out = ss_contributions_monthly(sbc_daily=sbc_daily, days_in_month=int(days))

    sbc_monthly = float(sbc_daily) * float(days)
    eff = effective_rates(
        sbc_monthly=sbc_monthly if sbc_monthly > 0 else salary_monthly,
        isr_monthly=float(isr_out["isr"]),
        ss_total_monthly=float(ss_out["totals"]["Total"])
    )

    with colR:
        st.subheader("Resultados")
        st.metric("ISR mensual", f"$ {isr_out['isr']:,.2f}")
        st.metric("SS total mensual (IMSS+INFONAVIT)", f"$ {ss_out['totals']['Total']:,.2f}")
        st.metric("Tasa efectiva ISR (sobre base)", f"{eff['isr_eff']:.2%}")
        st.metric("Tasa efectiva SS (sobre base)", f"{eff['ss_eff']:.2%}")

        st.caption("Rango ISR usado (tarifa 2026)")
        st.write({
            "límite inferior": isr_out["lower"],
            "límite superior": isr_out["upper"],
            "cuota fija": isr_out["fixed_quota"],
            "tasa marginal": isr_out["rate"],
        })

    st.subheader("Desglose de contribuciones a Seguridad Social")
    st.dataframe(ss_out["detail"], use_container_width=True)

    st.subheader("Gráfica: tasas efectivas por nivel de ingreso")
    if income_max <= income_min:
        st.warning("Para graficar, asegúrate de que ingreso máximo > ingreso mínimo.")
        return

    incomes = np.linspace(income_min, income_max, int(n_points))
    rows = []
    for inc in incomes:
        isr_val = isr_monthly(float(inc))["isr"]
        # Para la curva, aproximamos SBC mensual como el ingreso mensual/30 * días
        # (ajusta si tu definición de SBC difiere).
        sbc_m = float(inc)
        ss_total = ss_out["totals"]["Total"]  # usando el mismo SBC ingresado; puedes variar con inc si lo quieres
        isr_eff = isr_val / sbc_m if sbc_m > 0 else 0.0
        ss_eff = float(ss_total) / sbc_m if sbc_m > 0 else 0.0
        rows.append({"Ingreso_mensual": float(inc), "ISR_eff": isr_eff, "SS_eff": ss_eff})

    df_plot = pd.DataFrame(rows)

    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot["Ingreso_mensual"], y=df_plot["ISR_eff"], name="ISR_eff", mode="lines"))
    fig.add_trace(go.Scatter(x=df_plot["Ingreso_mensual"], y=df_plot["SS_eff"],  name="SS_eff",  mode="lines"))

    """# línea vertical en salario evaluado
    x0 = float(salary_monthly)
    fig.add_vline(x=x0)

    # punto marcado (asalariado evaluado)
    fig.add_trace(go.Scatter(
        x=[x0],
        y=[float(isr_out["isr"]) / x0 if x0 > 0 else 0.0],
        name="ISR (evaluado)",
        mode="markers"
    ))

    fig.add_trace(go.Scatter(
        x=[x0],
        y=[float(ss_out["totals"]["Total"]) / x0 if x0 > 0 else 0.0],
        name="SS (evaluado)",
        mode="markers"
    ))"""

    st.plotly_chart(fig, use_container_width=True)



    #fig = line_plot(
     #   df=df_plot,
      #  x="Ingreso_mensual",
       # y_cols=["ISR_eff", "SS_eff"],
        #title="Tasas efectivas: ISR vs Seguridad Social",
       # xlabel="Ingreso mensual [MXN]",
       # ylabel="Tasa efectiva"
    #)
    #st.pyplot(fig, clear_figure=False)

    # if save_plots:
    #     fname = "isr_ss_tasas_efectivas.png"
    #     path = save_fig(fig, out_dir="plots", filename=fname)
    #     st.success(f"Gráfica guardada en: {path}")
    html = fig.to_html(include_plotlyjs="cdn").encode("utf-8")
    st.download_button(
        "Descargar gráfica (HTML)",
        data=html,
        file_name="tasas_efectivas.html",
        mime="text/html"
    )

    with st.expander("Comentarios (para tu archivo separado)"):
        st.write(
            "Aquí puedes escribir tus observaciones: cómo cambia la tasa efectiva por ingreso, "
            "qué tan regresivo/progresivo resulta en tu rango, y qué parte de SS pesa más."
        )
