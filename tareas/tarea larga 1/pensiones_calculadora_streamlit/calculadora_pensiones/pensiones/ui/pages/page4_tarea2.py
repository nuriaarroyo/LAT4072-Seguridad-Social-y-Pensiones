"""
app_invalidez_conyuge_hijos.py
===============================
Streamlit — Calculadora MCSI (Laboratorio MC10 / CNSF)
Inválido con cónyuge e hijos

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
    salario_promedio_500,
    cbiv_diario, cbiv_mensual, pmg, base_pension, b1, b2,
    PCT_CUANTIA_BASICA, PCT_CONYUGE, PCT_HIJO, PCT_AYUDA_ASIST,
    INC, RECARGO_A, RECARGO_B, UMA_DIARIA,
)

# ── Página ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MCSI — MC10", page_icon="🏛️", layout="wide")

with st.sidebar:
    st.header("🏛️ MCSI — MC10")
    st.caption("Seguro de Invalidez — LSS/IMSS")
    st.divider()
    st.markdown("""
**Pasos del cálculo**
1. Historia salarial → Sal Prom Act 500 sem.
2. CBIV = 35 % × Sal Prom · CBIV_m = CBIV_d × 365/12
3. PMG = 1.3 × UMA × 30
4. base = max(CBIV_m, PMG)
5. b1(j) con cónyuge / b2(j) sin cónyuge
6. B_mensual: convoluciones hijos + cónyuge (qx Activos CNSF)
7. ä_x^inv (qx Invalidez Val Act 2020)
8. PBSI = (1+INC) × ä × B_mensual
9. PNSI = PBSI × FACBI
10. MCSI = (PNSI−PV) × (1+a)/(1−b)

**Referencias**
- Anexo 18.5.1 CUS
- Arts. 131, 136, 138, 141, 143 LSS

**Nota sobre tablas**
Las tablas qx Activos CNSF son de acceso restringido. Puedes ingresar los valores
b1(j)/b2(j) del laboratorio directamente para replicar los resultados exactos.
""")

st.header("🏛️ Monto Constitutivo — Seguro de Invalidez")
st.caption("Laboratorio MC10 · Anexo 18.5.1 CUS · Metodología CNSF")

with st.expander("💡 ¿Qué calcula esta herramienta?", expanded=False):
    st.markdown("""
| Paso | Concepto | Referencia MC10 |
|------|----------|----------------|
| 1 | Historia salarial → **Sal Prom Act 500 sem** | $1,680/día |
| 2-4 | **CBIV**, **PMG**, **base** = max(CBIV_m, PMG) | $588/d · $17,887/m · $4,177 PMG |
| 5 | **b1(j)** con cónyuge / **b2(j)** sin cónyuge (j = 0…n) | b1(0)=$24,922 … b1(3)=$30,288 |
| 6 | **B_mensual**: convoluciones sobre hijos y cónyuge (qx Activos CNSF) | 384,048 |
| 7 | **ä_x^inv** (qx Invalidez Val Act 2020) | 11.81 |
| 8 | **PBSI** = (1+INC) × ä × B_mensual | 5,035,737 |
| 9 | **PNSI** = PBSI × FACBI | 5,045,718 |
| 10 | **MCSI** = (PNSI−PV) × (1+a)/(1−b) | 5,197,090 |
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 1. HISTORIA SALARIAL
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📅 1 · Historia salarial")
st.caption("Salario diario original y factor de actualización por año (más reciente primero). "
           "Años con salario = 0 no consumen semanas.")

ANIOS_DEF = list(range(2024, 2013, -1))
SALS_DEF  = [2369, 2300, 2172, 2031, 1014, 472, 413, 0, 200, 1619, 1558]
FACTS_DEF = [1.064904559, 1.119951059, 1.17521364, 1.270294877,
             1.343206438, 1.390217949, 1.444347362, 0.0,
             1.60880516,  1.649478213, 1.696764172]

n_anios = st.number_input("Número de años en la historia", 1, 30,
                           value=len(ANIOS_DEF), step=1)

c0, c1, c2, c3 = st.columns([1, 2, 2, 2])
c0.markdown("**Año**"); c1.markdown("**Sal. diario orig. ($)**")
c2.markdown("**Factor actualiz.**"); c3.markdown("**Sal. actualizado ($)**")

historia: list[tuple[float, float]] = []
for i in range(int(n_anios)):
    a_d = ANIOS_DEF[i] if i < len(ANIOS_DEF) else (2024 - i)
    s_d = float(SALS_DEF[i])  if i < len(SALS_DEF)  else 0.0
    f_d = float(FACTS_DEF[i]) if i < len(FACTS_DEF) else 1.0
    cc0, cc1, cc2, cc3 = st.columns([1, 2, 2, 2])
    anio = cc0.number_input("", value=a_d, step=1,    key=f"yr_{i}", label_visibility="collapsed")
    sal  = cc1.number_input("", value=s_d, step=10.0, key=f"sl_{i}", label_visibility="collapsed", min_value=0.0)
    fac  = cc2.number_input("", value=f_d, step=0.001,key=f"fc_{i}", label_visibility="collapsed",
                             min_value=0.0, format="%.9f")
    cc3.markdown(f"**${sal*fac:,.2f}**")
    historia.append((float(sal), float(fac)))

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 2. DATOS DEL ASEGURADO, CÓNYUGE E HIJOS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("👤 2 · Información del asegurado")
d1, d2, d3, d4 = st.columns(4)
nombre    = d1.text_input("Nombre")
edad_inv  = d2.number_input("Edad (x)", 18, 99, value=49, step=1)
sexo_inv  = d3.selectbox("Sexo", ["H","M","T"],
               format_func=lambda s:{"H":"Hombre","M":"Mujer","T":"Mujer transgénero"}[s])
sem_cot   = d4.number_input("Semanas cotizadas", 0, 5000, value=557, step=1)

st.subheader("💑 Cónyuge")
e1, e2 = st.columns(2)
edad_cony = e1.number_input("Edad (y)", 18, 99, value=47, step=1)
sexo_cony = e2.selectbox("Sexo cónyuge", ["M","H"],
               format_func=lambda s:{"H":"Hombre","M":"Mujer"}[s])

st.subheader("👧👦 Hijos")
n_hijos = st.number_input("¿Cuántos hijos?", min_value=1, max_value=10, value=3, step=1)

EDADES_H = [13, 19, 21, 5, 3, 1, 0, 0, 0, 0]
SEXOS_H  = ["M","H","H","H","H","M","H","H","H","H"]

hijos: list[Hijo] = []
cols_h = st.columns(min(int(n_hijos), 4))
for i in range(int(n_hijos)):
    with cols_h[i % 4]:
        st.markdown(f"**Hijo {i+1}**")
        eh = st.number_input("Edad", 0, 30,
                             value=EDADES_H[i] if i<len(EDADES_H) else 0,
                             step=1, key=f"eh_{i}")
        sh = st.selectbox("Sexo", ["H","M"],
                          index=0 if (SEXOS_H[i] if i<len(SEXOS_H) else "H")=="H" else 1,
                          key=f"sh_{i}",
                          format_func=lambda s:{"H":"H","M":"M"}[s])
        est = st.checkbox("Estudia (25 a.)", value=True,  key=f"est_{i}")
        inv = st.checkbox("Inválido",        value=False, key=f"inv_{i}")
        hijos.append(Hijo(edad=int(eh), sexo=sh, estudia=est, invalido=inv))

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 3. PARÁMETROS ACTUARIALES
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("⚙️ 3 · Parámetros actuariales")

with st.expander("Parámetros generales (valores MC10 por defecto)", expanded=True):
    p1,p2,p3,p4,p5 = st.columns(5)
    tasa    = p1.number_input("Tasa i (%)", 0.0, 20.0, value=3.5, step=0.1) / 100.0
    uma     = p2.number_input("UMA diaria ($)", 50.0, 500.0, value=117.31, step=0.01)
    inc     = p3.number_input("INC (%)", 0.0, 50.0, value=11.0, step=0.5) / 100.0
    pct_aa  = p4.slider("Ayuda asistencial (%)", 0, 20, value=16, step=1) / 100.0
    facbi   = p5.number_input("FACBI", 0.9, 2.0, value=1.001982139,
                               step=0.000001, format="%.9f")
    r1, r2, r3 = st.columns(3)
    rec_a   = r1.number_input("a — recargo adquisición", 0.0, 0.2, value=0.02, step=0.005, format="%.3f")
    rec_b   = r2.number_input("b — recargo admón.",      0.0, 0.2, value=0.01, step=0.005, format="%.3f")
    pv_val  = r3.number_input("PV (prima única diferida)", value=0.0, step=1.0)

_core.TASA_INTERES    = tasa
_core.PCT_AYUDA_ASIST = pct_aa

# ── Opción: ingresar b1/b2 del lab directamente ────────────────────────────────
st.subheader("📋 4 · b1(j) / b2(j)  —  valores manuales (opcional)")
st.caption("Si tienes los valores exactos del laboratorio (qx Activos CNSF), "
           "ingrésalos aquí para reproducir el resultado exacto. "
           "Si los dejas en cero, se calculan automáticamente.")

usar_manual = st.checkbox("Usar valores manuales de b1(j) / b2(j)", value=False)

b1_over: dict | None = None
b2_over: dict | None = None
b_mens_override: float | None = None

if usar_manual:
    LAB_B1 = {0:24922, 1:26711, 2:28499, 3:30288}
    LAB_B2 = {0:22060, 1:24028, 2:25816, 3:27605}
    b1_over = {}
    b2_over = {}
    hdr = st.columns([1,2,2])
    hdr[0].markdown("**j**"); hdr[1].markdown("**b1(j) con cónyuge ($)**"); hdr[2].markdown("**b2(j) sin cónyuge ($)**")
    for j in range(int(n_hijos)+1):
        jc0,jc1,jc2 = st.columns([1,2,2])
        jc0.markdown(f"**{j}**")
        bv1 = jc1.number_input("", value=float(LAB_B1.get(j,0)), step=1.0,
                                key=f"b1_{j}", label_visibility="collapsed")
        bv2 = jc2.number_input("", value=float(LAB_B2.get(j,0)), step=1.0,
                                key=f"b2_{j}", label_visibility="collapsed")
        b1_over[j] = bv1
        b2_over[j] = bv2

    st.markdown("**B_mensual conjunta** (resultado de convoluciones — dejar en 0 para calcular automáticamente)")
    b_mens_val = st.number_input("B_mensual del laboratorio ($)", value=384048.0, step=1.0,
                                  min_value=0.0, key="b_mens_lab")
    if b_mens_val > 0:
        b_mens_override = b_mens_val

st.divider()

# ── Botón ──────────────────────────────────────────────────────────────────────
calcular = st.button("✅ Calcular MCSI", type="primary", use_container_width=True)
if not calcular:
    st.info("⚠️ Completa los datos y presiona **Calcular MCSI**.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# CÁLCULO
# ══════════════════════════════════════════════════════════════════════════════
sal_d = salario_promedio_500(historia)
if sal_d <= 0:
    st.error("El salario promedio es cero. Revisa la historia salarial.")
    st.stop()

# Si hay override de B_mensual, parcheamos el resultado post-cálculo
try:
    r = calcular_monto_constitutivo(
        edad_invalido=int(edad_inv),
        sexo_invalido=sexo_inv,
        edad_conyuge=int(edad_cony),
        sexo_conyuge=sexo_cony,
        hijos=hijos,
        sal_prom_diario=sal_d,
        uma_diaria=uma,
        inc=inc,
        facbi=facbi,
        a=rec_a,
        b_rec=rec_b,
        pv=pv_val,
        b1_override=b1_over,
        b2_override=b2_over,
    )
except ValueError as e:
    st.error(str(e))
    st.stop()

# Si el usuario proporcionó B_mensual exacta del lab, recalcular PBSI→MCSI
if usar_manual and b_mens_override and b_mens_override > 0:
    from pensiones.core.invalidez_conyuge_hijos import calcular_pbsi, calcular_pnsi, calcular_mcsi
    ax_v   = r["ax_invalido"]
    pbsi_v = calcular_pbsi(ax_v, b_mens_override, inc)
    pnsi_v = calcular_pnsi(pbsi_v, facbi)
    mcsi_v = calcular_mcsi(pnsi_v, rec_a, rec_b, pv_val)
    r = {**r,
         "b_mensual": round(b_mens_override, 2),
         "pbsi": round(pbsi_v, 2),
         "pnsi": round(pnsi_v, 2),
         "mcsi": round(mcsi_v, 2)}

# ══════════════════════════════════════════════════════════════════════════════
# RESULTADOS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader(f"📊 Resultados — {nombre or 'Asegurado'}")
st.caption(
    f"x={r['edad_invalido']} · y={r['edad_conyuge']} · {r['n_hijos']} hijos · "
    f"i={tasa:.2%} · INC={inc:.0%} · FACBI={facbi:.9f}"
)

m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("Sal. Prom. Act. 500 sem.", f"${r['sal_prom_diario']:,.2f}/día")
m2.metric("B_mensual conjunta",       f"${r['b_mensual']:,.0f}")
m3.metric("PBSI",  f"${r['pbsi']:,.0f}")
m4.metric("PNSI",  f"${r['pnsi']:,.0f}")
m5.metric("🏆 MCSI", f"${r['mcsi']:,.0f}")

# Comparación con el lab
if not usar_manual:
    diff_pbsi = abs(r['pbsi'] - 5_035_737) / 5_035_737 * 100
    st.info(
        f"**Comparación con MC10:** PBSI={r['pbsi']:,.0f} vs lab=5,035,737 "
        f"(diferencia {diff_pbsi:.1f}% por tablas qx Activos CNSF restringidas). "
        f"Activa **'Usar valores manuales de b1/b2'** para replicar el resultado exacto."
    )
else:
    st.success(
        f"**Resultado con valores manuales del lab:** "
        f"PBSI={r['pbsi']:,.0f} · PNSI={r['pnsi']:,.0f} · MCSI={r['mcsi']:,.0f}"
    )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_sal, tab_cbiv, tab_b, tab_pbsi, tab_graf, tab_h = st.tabs([
    "💰 Salario",
    "📋 CBIV / PMG / base",
    "📋 b1(j) / b2(j)",
    "📋 PBSI → MCSI",
    "📈 Gráfica",
    "👨‍👩‍👧‍👦 Hijos",
])

def _df(filas, cols=("Concepto","Valor")):
    st.dataframe(pd.DataFrame(filas, columns=cols),
                 use_container_width=True, hide_index=True)

with tab_sal:
    st.subheader("Carrera salarial")
    rows = []
    for i,(sal,fac) in enumerate(historia):
        rows.append({
            "Año":               2024-i,
            "Sal. diario ($)":   f"${sal:,.2f}",
            "Factor actualizac.":f"{fac:.9f}",
            "Sal. actualizado":  f"${sal*fac:,.2f}",
            "¿Cotizó?":         "Sí" if sal>0 else "No",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    _df([
        ("Semanas cotizadas (informativo)", f"{int(sem_cot):,}"),
        ("Sal. Prom. Act. 500 sem. (diario)", f"${r['sal_prom_diario']:,.4f}"),
        ("Sal. Prom. Act. 500 sem. (mensual 365/12)", f"${r['sal_prom_mensual']:,.2f}"),
    ])

with tab_cbiv:
    st.subheader("Paso 2-4 · CBIV, PMG y base")
    _df([
        ("Sal. Prom. Act. (diario)",          f"${r['sal_prom_diario']:,.4f}"),
        ("CBIV (%) — cuantía básica",         f"{PCT_CUANTIA_BASICA:.0%}"),
        ("CBIV diario = 35% × Sal_d",         f"${r['cbiv_diario']:,.4f}"),
        ("CBIV mensual = CBIV_d × 365/12",    f"${r['cbiv_mensual']:,.2f}"),
        ("UMA diaria vigente",                f"${uma:,.2f}"),
        ("PMG = 1.3 × UMA × 30",             f"${r['pmg_mensual']:,.2f}"),
        ("base = máx{CBIV_m, PMG}",           f"${r['base_mensual']:,.2f}"),
    ])
    if r['cbiv_mensual'] >= r['pmg_mensual']:
        st.success(f"✅ CBIV_m (${r['cbiv_mensual']:,.2f}) ≥ PMG (${r['pmg_mensual']:,.2f}) → base = CBIV_m")
    else:
        st.warning(f"⚠️ PMG (${r['pmg_mensual']:,.2f}) > CBIV_m (${r['cbiv_mensual']:,.2f}) → base = PMG")

with tab_b:
    st.subheader("Paso 5 · b1(j) y b2(j)")
    rows_b = []
    for j, vals in r["tabla_b"].items():
        lab_b1 = {0:24922,1:26711,2:28499,3:30288}
        lab_b2 = {0:22060,1:24028,2:25816,3:27605}
        rows_b.append({
            "j":                  j,
            "b1(j) con cónyuge":  f"${vals['b1']:,.2f}",
            "b1 lab (ref.)":      f"${lab_b1.get(j,'—'):,}" if j in lab_b1 else "—",
            "b2(j) sin cónyuge":  f"${vals['b2']:,.2f}",
            "b2 lab (ref.)":      f"${lab_b2.get(j,'—'):,}" if j in lab_b2 else "—",
        })
    st.dataframe(pd.DataFrame(rows_b), use_container_width=True, hide_index=True)
    st.caption(
        f"b1(j) = base×(1 + {PCT_CONYUGE:.0%} + j×{PCT_HIJO:.0%} + {pct_aa:.0%})  "
        f"· b2(j) = base×(1 + j×{PCT_HIJO:.0%} + {pct_aa:.0%})  "
        f"· Tope: 100% del salario mensual (Art. 143 LSS)"
    )

with tab_pbsi:
    st.subheader("Pasos 6-10 · B_mensual → PBSI → PNSI → MCSI")
    _df([
        ("B_mensual conjunta (convolución hijos + cónyuge)",  f"${r['b_mensual']:,.2f}"),
        ("   Lab MC10 (ref.)",                                "$384,048"),
        ("ä_x^inv (tabla Invalidez Val Act 2020)",            f"{r['ax_invalido']:.6f}"),
        ("   Lab MC10 (ref.)",                                "11.81"),
        ("ä_y^act  (tabla Activos CNSF — cónyuge)",          f"{r['ax_conyuge']:.6f}"),
        ("INC (recargo asegurador sobre PBSI)",               f"{inc:.0%}"),
        ("PBSI = (1+INC) × ä_inv × B_mensual",               f"${r['pbsi']:,.2f}"),
        ("   Lab MC10 (ref.)",                                "$5,035,737"),
        ("mp  (mes de cálculo)",                              "2"),
        ("ap  (año de cálculo)",                              "2026"),
        ("UDI₉,₂₀₂₄",                                        "8.682563"),
        ("UDI₁₂,₂₀₂₃",                                       "8.665387"),
        ("FACBI",                                              f"{facbi:.9f}"),
        ("PNSI = PBSI × FACBI",                               f"${r['pnsi']:,.2f}"),
        ("   Lab MC10 (ref.)",                                "$5,045,718"),
        ("PV (prima única diferida)",                          f"${pv_val:,.2f}"),
        ("a  (recargo adquisición)",                           f"{rec_a:.2%}"),
        ("b  (recargo administración)",                        f"{rec_b:.2%}"),
        ("MCSI = (PNSI−PV) × (1+a)/(1−b)",                   f"${r['mcsi']:,.2f}"),
        ("   Lab MC10 (ref.)",                                "$5,197,090"),
    ])

with tab_graf:
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig, ax = plt.subplots(figsize=(5, 3.5))
        etiq = ["PBSI","PNSI","MCSI"]
        vals = [r["pbsi"], r["pnsi"], r["mcsi"]]
        cols_c = ["#2196F3","#64B5F6","#185FA5"]
        bars = ax.bar(etiq, vals, color=cols_c, width=0.5)
        ax.bar_label(bars, fmt=lambda v:f"${v:,.0f}", padding=3, fontsize=8)
        ax.set_ylabel("Monto (MXN)")
        ax.set_title(f"PBSI → PNSI → MCSI\nx={edad_inv}, y={edad_cony}, {int(n_hijos)} hijos")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_:f"${v:,.0f}"))
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        st.pyplot(fig, clear_figure=False)

    with col_g2:
        # Gráfica b1/b2
        fig2, ax2 = plt.subplots(figsize=(5, 3.5))
        js   = list(r["tabla_b"].keys())
        b1vs = [r["tabla_b"][j]["b1"] for j in js]
        b2vs = [r["tabla_b"][j]["b2"] for j in js]
        ax2.plot(js, b1vs, "o-", color="#2196F3", label="b1(j) con cónyuge")
        ax2.plot(js, b2vs, "s--",color="#E53935", label="b2(j) sin cónyuge")
        for j,v in zip(js,b1vs): ax2.annotate(f"${v:,.0f}",(j,v),textcoords="offset points",xytext=(0,6),ha="center",fontsize=7)
        for j,v in zip(js,b2vs): ax2.annotate(f"${v:,.0f}",(j,v),textcoords="offset points",xytext=(0,-12),ha="center",fontsize=7)
        ax2.set_xlabel("j  (número de hijos vigentes)")
        ax2.set_ylabel("Beneficio mensual ($)")
        ax2.set_title("b1(j) y b2(j)")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_:f"${v:,.0f}"))
        ax2.legend(); ax2.grid(alpha=0.3)
        fig2.tight_layout()
        st.pyplot(fig2, clear_figure=False)

with tab_h:
    st.subheader("Detalle de hijos")
    st.dataframe(pd.DataFrame([{
        "#":               i+1,
        "Edad":            h.edad,
        "Sexo":            "Hombre" if h.sexo=="H" else "Mujer",
        "Estudia":         "Sí" if h.estudia else "No",
        "Inválido":        "Sí" if h.invalido else "No",
        "Edad límite":     "Indefinida" if h.invalido else h.edad_limite,
        "Años restantes":  "—" if h.invalido else h.anios_restantes,
    } for i,h in enumerate(hijos)]),
    use_container_width=True, hide_index=True)

# ── Análisis ───────────────────────────────────────────────────────────────────
st.divider()
with st.expander("💬 Análisis e interpretación"):
    st.markdown(f"""
**Composición familiar**
- Inválido: {r['edad_invalido']} años · sexo: {r['sexo_invalido']} · {int(sem_cot):,} semanas cotizadas
- Cónyuge: {r['edad_conyuge']} años · sexo: {r['sexo_conyuge']}
- Hijos: {r['n_hijos']}

**Salario y cuantía básica**
- Sal. Prom. Act. 500 sem.: **${r['sal_prom_diario']:,.4f}/día** → ${r['sal_prom_mensual']:,.2f}/mes (×365/12)
- CBIV: ${r['cbiv_diario']:,.4f}/día → **${r['cbiv_mensual']:,.2f}/mes** (×365/12)
- PMG: **${r['pmg_mensual']:,.2f}/mes** (1.3 × ${uma:,.2f} × 30)
- base = max(CBIV_m, PMG) = **${r['base_mensual']:,.2f}/mes**

**b1(0)** = ${r['tabla_b'][0]['b1']:,.2f}  ·  **b1({r['n_hijos']})** = ${r['tabla_b'][r['n_hijos']]['b1']:,.2f}
**b2(0)** = ${r['tabla_b'][0]['b2']:,.2f}  ·  **b2({r['n_hijos']})** = ${r['tabla_b'][r['n_hijos']]['b2']:,.2f}

**Cálculo actuarial**
- B_mensual (convolución) = **${r['b_mensual']:,.2f}**  _(lab: 384,048)_
- ä_x^inv (tabla Invalidez) = **{r['ax_invalido']:.4f}**  _(lab: 11.81)_
- PBSI = (1+{inc:.0%}) × {r['ax_invalido']:.4f} × {r['b_mensual']:,.2f} = **${r['pbsi']:,.2f}**  _(lab: 5,035,737)_

**Primas**
- PNSI = PBSI × FACBI ({facbi:.9f}) = **${r['pnsi']:,.2f}**  _(lab: 5,045,718)_
- MCSI = (PNSI−{pv_val:.0f}) × (1+{rec_a:.0%})/(1−{rec_b:.0%}) = **${r['mcsi']:,.2f}**  _(lab: 5,197,090)_
""")
