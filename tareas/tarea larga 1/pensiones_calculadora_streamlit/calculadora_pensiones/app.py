from __future__ import annotations

import streamlit as st

from pensiones.ui.pages.page1_isr_ss import render as render_isr_ss
from pensiones.ui.pages.page2_lss1997 import render as render_lss1997
from pensiones.ui.pages.page3_lss1973 import render as render_lss1973

st.set_page_config(
    page_title="Calculadora de Pensiones",
    layout="wide",
)

st.title("Calculadora de Pensiones — LAT4072")
st.caption("Tarea Larga 1 — Seguridad Social y Pensiones")

section = st.sidebar.radio(
    "Secciones",
    options=[
        "I) ISR 2026 + SS (LSS 1997) + INFONAVIT",
        "II) LSS 1997 — Tasa de reemplazo",
        "IV) LSS 1973 — Pensión y RR (60–65)",
    ],
)

st.sidebar.markdown("---")
st.sidebar.write("Carpetas importantes:")
st.sidebar.code("pensiones/core\n pensiones/data\n plots/")

if section.startswith("I)"):
    render_isr_ss()
elif section.startswith("II)"):
    render_lss1997()
else:
    render_lss1973()

st.markdown("---")
st.caption("Tip: llena las tablas legales en `pensiones/data/` y ajusta las funciones en `pensiones/core/`.")
