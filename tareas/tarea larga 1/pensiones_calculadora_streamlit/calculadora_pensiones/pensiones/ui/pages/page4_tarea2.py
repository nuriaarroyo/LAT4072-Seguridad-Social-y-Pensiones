"""
app_invalidez_conyuge_hijos.py
===============================
Streamlit — Calculadora de Monto Constitutivo
Seguro de Invalidez · Inválido con cónyuge e hijos
Anexo 18.5.1 LSS · Secciones 4 y 5
 
Reglas de negocio:
  · La pensión total NO puede exceder el 100 % de la cuantía básica
    (salario mensual promedio). Art. 143 LSS.
  · Los campos de hijos se generan dinámicamente según el número indicado.
  · Sin sidebar: todos los parámetros en el cuerpo principal.
 
Ejecutar:
    streamlit run app_invalidez_conyuge_hijos.py
"""
 
from __future__ import annotations
 
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import streamlit as st
 
import pensiones.core.invalidez_conyuge_hijos as _core
from pensiones.core.invalidez_conyuge_hijos import (
    Hijo,
    calcular_monto_constitutivo,
    PCT_CUANTIA_BASICA,
    PCT_CONYUGE,
    PCT_HIJO,
    PCT_AYUDA_ASIST,
    PCT_VIUDEZ,
)
 
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MC Invalidez — LSS/IMSS",
    page_icon="🏛️",
    layout="wide"
)
 
# Sidebar vacía — mantiene la columna lateral visible
with st.sidebar:
    st.header("🏛️ MC Invalidez")
    st.caption("Seguro de Invalidez — LSS/IMSS")
    st.divider()
    st.markdown(
        """
**Secciones calculadas**
- Sección 4 — Seguro de Invalidez
- Sección 5 — Seguro de Sobrevivencia
 
**Referencias**
- Anexo 18.5.1 CUS
- Art. 131, 136, 138, 141, 143 LSS
 
**Tablas de mortalidad**
- EMSSA (inválidos)
- EMSSAH / EMSSAM (sanos)
"""
    )
 
st.header("🏛️ Seguro de Invalidez — Inválido con cónyuge e hijos")
st.caption("Anexo 18.5.1 LSS · Secciones 4 y 5 · Art. 143: pensión máx. = 100 % cuantía básica")
 
with st.expander("💡 ¿Qué calcula esta herramienta?", expanded=False):
    st.markdown(
        """
Determina el **Monto Constitutivo Total (MCT)** para contratar el seguro de
renta vitalicia por invalidez y el seguro de sobrevivencia (Anexo 18.5.1 LSS).
 
**Regla de tope (Art. 143 LSS)**
La suma de cuantía básica + asignaciones familiares (cónyuge + hijos) + ayuda
asistencial **no puede exceder el 100 % del salario mensual promedio**. Si se
supera, el porcentaje total se recorta al 100 %.
 
**Sección 4 — Seguro de Invalidez**
- **PBSI**: VP de la pensión vitalicia del inválido (tabla EMSSA).
- **PSIH**: prima de orfandad contingente para hijos.
- **MCSI** = (PBSI + PSIH) × Recargo.
 
**Sección 5 — Seguro de Sobrevivencia**
- **PBSS**: VP de la pensión de viudez al 90 % (Art. 131).
- **PSIH_SS**: VP de orfandad tras fallecimiento del inválido.
- **PFH**: finiquito 3 mensualidades (Art. 136).
- **MCSS** = (PBSS + PSIH_SS + PFH) × Recargo.
 
**MCT = MCSI + MCSS**
"""
    )
 
st.divider()
 
# ── 1. Datos del inválido ─────────────────────────────────────────────────────
st.subheader("👤 Datos del asegurado inválido")
c1, c2, c3, c4 = st.columns(4)
nombre   = c1.text_input("Nombre")
edad_inv = c2.number_input("Edad", 18, 99, value=45, step=1)
sexo_inv = c3.selectbox(
    "Sexo",
    ["H", "M", "T"],
    format_func=lambda s: {"H": "Hombre", "M": "Mujer", "T": "Mujer transgénero"}[s],
)
sal_d = c4.number_input(
    "Salario diario prom. últimas 500 sem. (MXN)",
    min_value=0.0, value=1_500.0, step=50.0,
)
sal_m = sal_d * 30.0
c4.caption(f"Salario mensual: **${sal_m:,.2f}**")
 
st.divider()
 
# ── 2. Datos del cónyuge ──────────────────────────────────────────────────────
st.subheader("💑 Datos del cónyuge")
c5, c6 = st.columns(2)
edad_cony = c5.number_input("Edad del cónyuge", 18, 99, value=43, step=1)
sexo_cony = c6.selectbox(
    "Sexo del cónyuge",
    ["M", "H"],
    format_func=lambda s: {"H": "Hombre", "M": "Mujer"}[s],
)
 
st.divider()
 
# ── 3. Número de hijos (primero se pregunta, luego aparecen los campos) ───────
st.subheader("👧👦 Hijos")
n_hijos = st.number_input(
    "¿Cuántos hijos tiene el asegurado?",
    min_value=1, max_value=10, value=1, step=1,
    help="",
)
 
# Vista previa del tope antes de capturar hijos
pct_bruto = PCT_CUANTIA_BASICA + PCT_CONYUGE + int(n_hijos) * PCT_HIJO + PCT_AYUDA_ASIST
pct_efectivo = min(pct_bruto, 1.0)
tope_activo  = pct_bruto > 1.0
 
col_prev1, col_prev2, col_prev3 = st.columns(3)
col_prev1.metric(
    "% bruto sobre salario",
    f"{pct_bruto:.2%}",
    help="CB 35% + cónyuge 15% + hijos (n×10%) + AA 16%",
)
col_prev2.metric(
    "% efectivo (tope Art. 143)",
    f"{pct_efectivo:.2%}",
    delta="⚠️ Tope aplicado" if tope_activo else "✅ Sin tope",
    delta_color="off",
)
col_prev3.metric(
    "Pensión mensual estimada",
    f"${sal_m * pct_efectivo:,.2f}",
)
 
if tope_activo:
    st.warning(
        f"⚠️ Con {int(n_hijos)} hijos el porcentaje total ({pct_bruto:.2%}) supera el 100 % "
        f"del salario. Se aplicará el tope del **Art. 143 LSS** y la pensión quedará en "
        f"**${sal_m:,.2f}/mes** (100 % de la cuantía básica)."
    )
 
st.caption("Captura los datos de cada hijo:")
 
edades_default = [14, 12, 9, 5, 3, 1, 0, 0, 0, 0]
hijos: list[Hijo] = []
 
cols_h = st.columns(min(int(n_hijos), 4))
for i in range(int(n_hijos)):
    with cols_h[i % 4]:
        st.markdown(f"**Hijo {i + 1}**")
        edad_h   = st.number_input(
            "Edad", 0, 24,
            value=edades_default[i] if i < len(edades_default) else 0,
            step=1, key=f"eh_{i}",
        )
        sexo_h   = st.selectbox(
            "Sexo", ["H", "M"],
            format_func=lambda s: {"H": "H", "M": "M"}[s],
            key=f"sh_{i}",
        )
        estudia  = st.checkbox("Estudia (límite 25 a.)", value=True,  key=f"est_{i}")
        inv_hijo = st.checkbox(
            "Inválido (sin límite)", value=False, key=f"inv_{i}",
            help="Art. 138: la pensión no tiene límite de edad si el hijo es inválido.",
        )
        hijos.append(Hijo(edad=int(edad_h), sexo=sexo_h, estudia=estudia, invalido=inv_hijo))
 
st.divider()
 
# ── 4. Parámetros actuariales (en el cuerpo, colapsados) ─────────────────────
with st.expander("⚙️ Parámetros actuariales (valores CNSF por defecto)", expanded=False):
    pa1, pa2, pa3, pa4, pa5 = st.columns(5)
    tasa    = pa1.number_input("Tasa interés (%)", 0.0, 20.0, value=3.5, step=0.1) / 100.0
    rec_inv = pa2.number_input("Recargo invalidez",     1.0, 2.0, value=1.09, step=0.01)
    rec_sob = pa3.number_input("Recargo sobrevivencia", 1.0, 2.0, value=1.09, step=0.01)
    pct_aa  = pa4.slider("Ayuda asistencial (%)", 0, 20, value=16, step=1) / 100.0
    facbi   = pa5.number_input("FACBI", 0.5, 5.0, value=1.0, step=0.01)
 
# Aplicar al módulo
_core.TASA_INTERES          = tasa
_core.RECARGO_INVALIDEZ     = rec_inv
_core.RECARGO_SOBREVIVENCIA = rec_sob
_core.PCT_AYUDA_ASIST       = pct_aa
_core.FACBI                 = facbi
 
# ── 5. Botón de cálculo ────────────────────────────────────────────────────────
calcular = st.button("✅ Calcular monto constitutivo", type="primary", use_container_width=True)
 
if not calcular:
    st.info("⚠️ Completa los datos y presiona **Calcular monto constitutivo**.")
    st.stop()
 
if sal_d <= 0:
    st.error("El salario diario debe ser mayor a cero.")
    st.stop()
 
# ── 6. Cálculo ─────────────────────────────────────────────────────────────────
try:
    r = calcular_monto_constitutivo(
        edad_invalido=int(edad_inv),
        sexo_invalido=sexo_inv,
        edad_conyuge=int(edad_cony),
        sexo_conyuge=sexo_cony,
        hijos=hijos,
        salario_diario=float(sal_d),
    )
except ValueError as e:
    st.error(str(e))
    st.stop()
 
# ── 7. Resultados ──────────────────────────────────────────────────────────────
st.subheader(f"📊 Resultados — {nombre or 'Asegurado'}")
st.caption(
    f"Inválido {r['edad_invalido']} a. · Cónyuge {r['edad_conyuge']} a. · "
    f"{r['n_hijos']} hijos · Sal. ${r['salario_mensual']:,.2f}/mes · "
    f"i = {tasa:.2%} · FACBI = {facbi:.4f}"
)
 
if r["pct_total"] == 1.0:
    st.warning(
        f"⚠️ **Tope Art. 143 aplicado.** El porcentaje bruto era {pct_bruto:.2%}; "
        f"la pensión se limitó al **100 % del salario mensual** (${r['salario_mensual']:,.2f})."
    )
 
m1, m2, m3, m4 = st.columns(4)
m1.metric("Pensión mensual",              f"${r['pension_mensual']:,.2f}")
m2.metric("MC seg. invalidez (MCSI)",     f"${r['mcsi']:,.2f}")
m3.metric("MC seg. sobrevivencia (MCSS)", f"${r['mcss']:,.2f}")
m4.metric("🏆 Monto constitutivo total",  f"${r['mct']:,.2f}")
 
st.divider()
 
# ── 8. Tabs de desglose ────────────────────────────────────────────────────────
tab4, tab5, tab_graf, tab_h = st.tabs([
    "📋 Sección 4 — Invalidez",
    "📋 Sección 5 — Sobrevivencia",
    "📈 Gráfica",
    "👨‍👩‍👧‍👦 Detalle hijos",
])
 
def _df(filas):
    st.dataframe(
        pd.DataFrame(filas, columns=["Concepto", "Valor"]),
        use_container_width=True, hide_index=True,
    )
 
with tab4:
    st.subheader("Sección 4 — Seguro de Invalidez")
    _df([
        ("Salario diario promedio",                         f"${r['salario_diario']:,.4f}"),
        ("Salario mensual promedio",                        f"${r['salario_mensual']:,.2f}"),
        ("% Cuantía básica (Art. 141)",                    f"{PCT_CUANTIA_BASICA:.2%}"),
        ("% Asignación cónyuge (Art. 138-I)",              f"{PCT_CONYUGE:.2%}"),
        (f"% Asignación hijos ({r['n_hijos']} × 10 %)",   f"{r['n_hijos'] * PCT_HIJO:.2%}"),
        ("% Ayuda asistencial",                            f"{pct_aa:.2%}"),
        ("% Bruto sobre salario",                          f"{pct_bruto:.2%}"),
        ("% Efectivo (tope 100 % Art. 143)",               f"{r['pct_total']:.2%}"),
        ("Pensión mensual del inválido",                   f"${r['pension_mensual']:,.2f}"),
        ("Pensión anual",                                  f"${r['pension_anual']:,.2f}"),
        ("Anualidad ä_x^inv (EMSSA)",                      f"{r['ax_invalido']:.6f}"),
        ("FACBI",                                          f"{facbi:.4f}"),
        ("Prima básica seg. invalidez (PBSI)",             f"${r['pbsi']:,.2f}"),
        ("Prima seg. invalidez hijos (PSIH)",              f"${r['psih']:,.2f}"),
        ("Prima neta seg. invalidez  PNSI = PBSI + PSIH",  f"${r['pnsi']:,.2f}"),
        ("Recargo invalidez",                              f"{rec_inv:.4f}"),
        ("Monto constitutivo seg. invalidez (MCSI)",       f"${r['mcsi']:,.2f}"),
    ])
 
with tab5:
    st.subheader("Sección 5 — Seguro de Sobrevivencia")
    _df([
        ("% Pensión de viudez (Art. 131)",                   f"{PCT_VIUDEZ:.2%}"),
        ("Anualidad ä_y^sano cónyuge (EMSSAH/M)",            f"{r['ax_conyuge']:.6f}"),
        ("Prima básica seg. sobrevivencia (PBSS)",           f"${r['pbss']:,.2f}"),
        ("Prima seg. inval. hijos — sobrevivencia (PSIH_SS)",f"${r['psih_ss']:,.2f}"),
        ("Prima finiquito hijos (PFH) — 3 mens. Art. 136",  f"${r['pfh']:,.2f}"),
        ("Prima neta seg. sobrevivencia  PNSS",              f"${r['pnss']:,.2f}"),
        ("Recargo sobrevivencia",                            f"{rec_sob:.4f}"),
        ("Monto constitutivo seg. sobrevivencia (MCSS)",     f"${r['mcss']:,.2f}"),
    ])
    pct_si = r["mcsi"] / r["mct"] * 100
    pct_ss = r["mcss"] / r["mct"] * 100
    st.markdown(f"""
| Componente | Monto (MXN) | % del MCT |
|---|---:|---:|
| MCSI | ${r['mcsi']:,.2f} | {pct_si:.1f} % |
| MCSS | ${r['mcss']:,.2f} | {pct_ss:.1f} % |
| **MCT** | **${r['mct']:,.2f}** | **100.0 %** |
""")
 
with tab_graf:
    etiquetas = ["PBSI", "PSIH", "PBSS", "PSIH_SS", "PFH"]
    valores   = [r["pbsi"], r["psih"], r["pbss"], r["psih_ss"], r["pfh"]]
    colores   = ["#2196F3", "#64B5F6", "#E53935", "#EF9A9A", "#FF7043"]
 
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(etiquetas, valores, color=colores)
    ax.bar_label(bars, fmt=lambda v: f"${v:,.0f}", padding=4, fontsize=9)
    ax.set_xlabel("Monto (MXN)")
    ax.set_title(
        f"Componentes del Monto Constitutivo\n"
        f"MCT = ${r['mct']:,.2f}  ·  i = {tasa:.2%}  ·  {r['n_hijos']} hijos"
        + ("  ·  ⚠️ Tope Art.143 activo" if r["pct_total"] == 1.0 else "")
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.grid(axis="x", alpha=0.3)
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color="#2196F3", label="Sección 4 — Invalidez"),
        Patch(color="#E53935", label="Sección 5 — Sobrevivencia"),
    ], loc="lower right")
    fig.tight_layout()
    st.pyplot(fig, clear_figure=False)
 
with tab_h:
    st.subheader("Detalle de hijos")
    st.dataframe(
        pd.DataFrame([{
            "#":                   i + 1,
            "Edad":                h.edad,
            "Sexo":                "Hombre" if h.sexo == "H" else "Mujer",
            "Estudia":             "Sí" if h.estudia else "No",
            "Inválido":            "Sí" if h.invalido else "No",
            "Edad límite pensión": "Indefinida" if h.invalido else h.edad_limite,
            "Años restantes":      "—" if h.invalido else h.anios_restantes,
        } for i, h in enumerate(hijos)]),
        use_container_width=True, hide_index=True,
    )
 
# ── 9. Análisis ────────────────────────────────────────────────────────────────
st.divider()
with st.expander("💬 Análisis e interpretación"):
    st.markdown(f"""
**Composición familiar**
- Inválido: {r['edad_invalido']} años · sexo: {r['sexo_invalido']}
- Cónyuge: {r['edad_conyuge']} años · sexo: {r['sexo_conyuge']}
- Número de hijos: **{r['n_hijos']}**
 
**Pensión mensual calculada**
- Cuantía básica (35 %): ${PCT_CUANTIA_BASICA * r['salario_mensual']:,.2f}
- Asignación cónyuge (15 %): ${PCT_CONYUGE * r['salario_mensual']:,.2f}
- Asignación hijos ({r['n_hijos']} × 10 %): ${r['n_hijos'] * PCT_HIJO * r['salario_mensual']:,.2f}
- Ayuda asistencial ({pct_aa:.0%}): ${pct_aa * r['salario_mensual']:,.2f}
- % Bruto: {pct_bruto:.2%} → % Efectivo (tope Art. 143): **{r['pct_total']:.2%}**
- **Pensión mensual: ${r['pension_mensual']:,.2f}**
 
**Sección 4 — Seguro de Invalidez**
- PBSI = ${r['pbsi']:,.2f}  (ä_x^inv = {r['ax_invalido']:.4f})
- PSIH = ${r['psih']:,.2f}
- PNSI = ${r['pnsi']:,.2f}
- MCSI = ${r['mcsi']:,.2f}  (recargo × {rec_inv:.2f})
 
**Sección 5 — Seguro de Sobrevivencia**
- PBSS = ${r['pbss']:,.2f}  (ä_y^sano cónyuge = {r['ax_conyuge']:.4f})
- PSIH_SS = ${r['psih_ss']:,.2f}
- PFH = ${r['pfh']:,.2f}  (3 mensualidades — Art. 136)
- PNSS = ${r['pnss']:,.2f}
- MCSS = ${r['mcss']:,.2f}  (recargo × {rec_sob:.2f})
 
**Monto Constitutivo Total: ${r['mct']:,.2f}**
- Suma asegurada = MCT − Saldo cuenta individual AFORE.
- Tasa técnica: {tasa:.2%} · FACBI: {facbi:.4f}
""")
 