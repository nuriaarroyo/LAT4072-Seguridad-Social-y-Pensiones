from __future__ import annotations

import streamlit as st

from pensiones.core.lss1973_ret import rr_by_retirement_age
from pensiones.utils.plotting import line_plot, save_fig

def render():
    st.header("IV) LSS 1973 — Pensión y tasa de reemplazo por edad de jubilación (60–65)")

    with st.expander("Qué hace esta sección", expanded=True):
        st.write(
            """- Calcula pensión y tasa de reemplazo para edades 60 a 65
"
            "- Grafica tasa de reemplazo por edad de jubilación
"
            "- Te deja espacio para comentar resultados"""
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Entradas")
        with st.form("form_lss73"):
            age_now = st.number_input("Edad actual x", min_value=15, max_value=80, value=55, step=1)
            salary_monthly = st.number_input("Salario mensual y [MXN]", min_value=0.0, value=20000.0, step=500.0)
            min_age = st.slider("Edad mínima jubilación", 60, 65, 60)
            max_age = st.slider("Edad máxima jubilación", 60, 65, 65)
            save_plots = st.checkbox("Guardar gráfica en plots/", value=True)
            submitted = st.form_submit_button("Calcular")

    if not submitted:
        st.info("Ingresa valores y presiona **Calcular**.")
        return

    df = rr_by_retirement_age(int(age_now), float(salary_monthly), int(min_age), int(max_age))

    with col2:
        st.subheader("Vista rápida")
        best = df.loc[df["replacement_rate"].idxmax()]
        st.metric("Mejor RR (en rango)", f"{best['replacement_rate']:.2%}")
        st.metric("Edad asociada", f"{int(best['retirement_age'])}")

    st.subheader("Tabla de resultados")
    st.dataframe(df, use_container_width=True)

    st.subheader("Gráfica: RR vs edad de jubilación")
    fig = line_plot(
        df=df,
        x="retirement_age",
        y_cols=["replacement_rate"],
        title="Tasa de reemplazo por edad de jubilación (LSS 1973)",
        xlabel="Edad de jubilación",
        ylabel="Tasa de reemplazo"
    )
    st.pyplot(fig, clear_figure=False)

    if save_plots:
        path = save_fig(fig, out_dir="plots", filename="lss1973_rr_por_edad.png")
        st.success(f"Gráfica guardada en: {path}")

    with st.expander("Comentarios (para tu archivo separado)"):
        st.write(
            "Comenta: trade-off de jubilarse antes vs. después, pendiente de la RR, "
            "y consistencia con reglas/supuestos del Excel."
        )
