from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from src.selfies_calculator import (
    SelfiesAssumptions,
    bonds_needed,
    calculate_age_table,
    calculate_sensitivity_table,
    load_latest_udi,
    load_curve,
    price_one_selfies,
    validate_curve,
)

st.set_page_config(
    page_title="Calculadora SeLFIES/RSB en UDIS",
    page_icon="📈",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CURVE_PATH = BASE_DIR / "datos" / "curva_real_udis.csv"
DEFAULT_UDI_PATH = BASE_DIR / "datos" / "valor_udi.csv"

try:
    default_valor_udi = load_latest_udi(DEFAULT_UDI_PATH)
except Exception:
    default_valor_udi = 0.0

st.title("Calculadora de bonos de retiro tipo SeLFIES/RSB en UDIS")
st.caption(
    "Bono forward-starting, income-only, denominado en UDIS. "
    "Calcula el número de bonos y su costo para el rango de edades que elijas."
)

with st.sidebar:
    st.header("Supuestos del ejercicio")
    edad_min = st.number_input("Edad mínima", min_value=0, max_value=100, value=16, step=1)
    edad_max = st.number_input("Edad máxima", min_value=0, max_value=100, value=55, step=1)
    edad_retiro = st.number_input("Edad de retiro", min_value=1, max_value=110, value=65, step=1)
    pension_anual_udis = st.number_input(
        "Pensión anual objetivo (UDIS)", min_value=1.0, value=72_000.0, step=1_000.0
    )
    cupon_anual = st.number_input(
        "Cupón anual por bono (UDIS)", min_value=0.0001, value=5.0, step=1.0,
        help="En el paper usan ejemplo de $5 reales por bono. Aquí se usa 5 UDIS por defecto."
    )
    anios_pago = st.number_input("Años de pago del bono", min_value=1, max_value=60, value=20, step=1)
    payment_timing_label = st.selectbox(
        "Primer pago",
        options=["Al cumplir edad de retiro", "Un año después del retiro"],
        index=0,
    )
    payment_timing = "at_retirement" if payment_timing_label.startswith("Al") else "in_arrears"
    compounding_label = st.selectbox("Capitalización", options=["Anual", "Continua"], index=0)
    compounding = "annual" if compounding_label == "Anual" else "continuous"
    crecimiento_real = st.number_input(
        "Crecimiento real anual del estándar de vida (opcional)",
        min_value=-0.10,
        max_value=0.10,
        value=0.0,
        step=0.001,
        format="%.3f",
        help="Déjalo en 0 si quieres una valuación puramente en UDIS."
    )
    valor_udi = st.number_input(
        "Valor de la UDI en pesos (opcional)",
        min_value=0.0,
        value=float(default_valor_udi),
        step=0.000001,
        format="%.6f",
        help="Se carga desde datos/valor_udi.csv. Si lo dejas en 0, sólo se reporta en UDIS."
    )

    st.header("Curva real")
    uploaded_curve = st.file_uploader(
        "Sube curva_real_udis.csv", type=["csv"],
        help="Debe tener columnas tenor_years y annual_real_rate. Las tasas van en decimal, por ejemplo 0.035."
    )

try:
    if uploaded_curve is not None:
        curve = load_curve(uploaded_curve)
        curve_source = "archivo subido"
    else:
        curve = load_curve(DEFAULT_CURVE_PATH)
        curve_source = "datos/curva_real_udis.csv"

    assumptions = SelfiesAssumptions(
        edad_min=int(edad_min),
        edad_max=int(edad_max),
        edad_retiro=int(edad_retiro),
        pension_anual_udis=float(pension_anual_udis),
        cupon_anual_por_bono_udis=float(cupon_anual),
        anios_pago=int(anios_pago),
        crecimiento_real_estandar_vida=float(crecimiento_real),
        payment_timing=payment_timing,
        compounding=compounding,
        valor_udi_mxn=float(valor_udi) if valor_udi > 0 else None,
    )
    assumptions.validate()
    curve = validate_curve(curve)

    st.subheader("Resumen de la construcción")
    c1, c2, c3, c4 = st.columns(4)
    n_bonds = bonds_needed(assumptions)
    c1.metric("Bonos necesarios", f"{n_bonds:,.2f}")
    c2.metric("Pensión anual", f"{assumptions.pension_anual_udis:,.0f} UDIS")
    c3.metric("Cupón por bono", f"{assumptions.cupon_anual_por_bono_udis:,.2f} UDIS")
    c4.metric("Años de pago", f"{assumptions.anios_pago}")

    st.markdown(
        "La idea es que cada bono comprado entrega un cupón real anual durante el retiro. "
        "Por eso, el número de bonos se obtiene como `pensión anual objetivo / cupón anual por bono`. "
        "La edad no cambia el número de bonos; cambia el precio actual de esos bonos."
    )

    with st.expander("Ver curva real usada"):
        st.write(f"Fuente de curva: `{curve_source}`")
        st.dataframe(curve, use_container_width=True)

    table = calculate_age_table(assumptions, curve)

    st.subheader("Resultados por edad")
    st.dataframe(table, use_container_width=True)

    csv_bytes = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar resultados CSV",
        data=csv_bytes,
        file_name="resultados_selfies_udis.csv",
        mime="text/csv",
    )

    st.subheader("Gráficas")
    left, right = st.columns(2)
    with left:
        st.markdown("**Costo total para comprar la pensión**")
        st.line_chart(table.set_index("edad")[["costo_total_udis"]])
    with right:
        st.markdown("**Precio por bono**")
        st.line_chart(table.set_index("edad")[["precio_por_bono_udis"]])

    st.subheader("Sensibilidad a la curva real")
    sens = calculate_sensitivity_table(assumptions, curve, shocks_bps=[-100, 0, 100])
    pivot = sens.pivot(index="edad", columns="shock_bps", values="costo_total_udis")
    pivot.columns = [f"shock_{int(col):+d}_bps" for col in pivot.columns]
    st.dataframe(pivot.reset_index(), use_container_width=True)
    st.line_chart(pivot)

    st.subheader("Calendario de flujos de un bono para una edad específica")
    edad_detalle = st.slider("Edad para ver calendario", int(edad_min), int(edad_max), int(edad_max))
    precio, schedule = price_one_selfies(int(edad_detalle), assumptions, curve)
    st.write(f"Precio de un bono para edad {edad_detalle}: **{precio:,.4f} UDIS**")
    st.dataframe(schedule, use_container_width=True)

except Exception as exc:
    st.error(f"No se pudo calcular: {exc}")
    st.info("Revisa edades, cupón, años de pago y que el CSV de curva tenga las columnas correctas.")
