"""
app_invalidez_conyuge_hijos.py
==============================
Calculadora Streamlit — Monto Constitutivo del Seguro de Invalidez
Inválido con cónyuge e hijos (mínimo cuatro) — LSS / IMSS

Refleja la estructura de la presentación del Anexo 18.5.1 CUS:
  · Sección 4: Seguro de Invalidez (PBSI + PSIH → PNSI → MCSI)
  · Sección 5: Seguro de Sobrevivencia (PBSS + PSIH_SS + PFH → PNSS → MCSS)
  · MCT = MCSI + MCSS
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import streamlit as st

from pensiones.core.invalidez_conyuge_hijos import (
    Hijo,
    calcular_monto_constitutivo_invalido,
    salario_promedio_500_semanas,
    PCT_CUANTIA_BASICA,
    PCT_CONYUGE,
    PCT_HIJO,
    PCT_AYUDA_ASIST,
    PCT_VIUDEZ,
    TASA_INTERES,
    RECARGO_INVALIDEZ,
    RECARGO_SOBREVIVENCIA,
    FACBI,
)

TITULO = "Calculadora de Monto Constitutivo — Seguro de Invalidez (Inválido con Cónyuge e Hijos)"


def render() -> None:
    st.set_page_config(page_title="MC Invalidez — LSS", layout="wide")
    st.header("🏛️ Seguro de Invalidez — Inválido con Cónyuge e Hijos")
    st.caption("Anexo 18.5.1 LSS · Secciones 4 y 5 · Mínimo 4 hijos")

    with st.expander("💡 ¿Qué calcula esta herramienta?", expanded=False):
        st.markdown(
            """
Esta calculadora determina el **Monto Constitutivo Total (MCT)** requerido para contratar
el **Seguro de Renta Vitalicia por Invalidez** y el **Seguro de Sobrevivencia** conforme al
Anexo 18.5.1 de la Ley del Seguro Social.

**Sección 4 — Seguro de Invalidez**
- Prima básica del seguro de invalidez (**PBSI**): VP de la pensión del inválido.
- Prima del seguro de invalidez para hijos (**PSIH**): costo de la pensión de orfandad contingente.
- Prima neta (**PNSI**) = PBSI + PSIH.
- Monto constitutivo (**MCSI**) = PNSI × Recargo.

**Sección 5 — Seguro de Sobrevivencia**
- Prima básica del sobrevivencia (**PBSS**): VP de la pensión de viudez.
- Prima para hijos en sobrevivencia (**PSIH_SS**): VP de orfandad tras fallecimiento del inválido.
- Prima del finiquito para hijos (**PFH**): 3 mensualidades al extinguirse la pensión (Art. 136).
- Prima neta (**PNSS**) = PBSS + PSIH_SS + PFH.
- Monto constitutivo (**MCSS**) = PNSS × Recargo.

**MCT = MCSI + MCSS**
"""
        )

    # ── Sidebar: parámetros globales ──────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Parámetros actuariales")
        tasa_i = st.number_input(
            "Tasa de interés técnico anual (%)",
            min_value=0.0, max_value=20.0, value=TASA_INTERES * 100, step=0.1,
        ) / 100.0
        recargo_inv = st.number_input(
            "Recargo seguro de invalidez", min_value=1.0, max_value=2.0,
            value=RECARGO_INVALIDEZ, step=0.01,
        )
        recargo_sob = st.number_input(
            "Recargo seguro de sobrevivencia", min_value=1.0, max_value=2.0,
            value=RECARGO_SOBREVIVENCIA, step=0.01,
        )
        facbi = st.number_input(
            "FACBI (factor de actualización por inflación)",
            min_value=0.5, max_value=5.0, value=FACBI, step=0.01,
        )
        pct_aa = st.slider(
            "Ayuda asistencial (%)", min_value=0, max_value=20, value=16, step=1,
        ) / 100.0

    # Sobreescribir constantes en tiempo de ejecución
    import pensiones.core.invalidez_conyuge_hijos as _core
    _core.TASA_INTERES = tasa_i
    _core.RECARGO_INVALIDEZ = recargo_inv
    _core.RECARGO_SOBREVIVENCIA = recargo_sob
    _core.FACBI = facbi
    _core.PCT_AYUDA_ASIST = pct_aa

    # ── Datos del inválido ─────────────────────────────────────────────────────
    st.header("👤 Datos del asegurado inválido")
    col1, col2, col3 = st.columns(3)
    with col1:
        nombre = st.text_input("Nombre del asegurado")
        edad_inv = st.number_input("Edad actual", min_value=18, max_value=99, value=45, step=1)
    with col2:
        sexo_inv = st.selectbox(
            "Sexo del inválido",
            ["H", "M", "M_TRANS"],
            format_func=lambda s: {"H": "Hombre", "M": "Mujer", "M_TRANS": "Mujer transgénero"}[s],
        )
        sem_cot = st.number_input(
            "Semanas cotizadas", min_value=150, max_value=5000, value=500, step=1,
            help="Mínimo 250 (o 150 si invalidez ≥ 75%) — Art. 122 LSS",
        )
    with col3:
        sal_diario = st.number_input(
            "Salario diario promedio últimas 500 semanas (MXN)",
            min_value=0.0, value=1500.0, step=50.0,
        )
        st.caption(f"Salario mensual: **${sal_diario * 30:,.2f}**")

    # ── Datos del cónyuge ──────────────────────────────────────────────────────
    st.header("💑 Datos del cónyuge")
    col4, col5 = st.columns(2)
    with col4:
        edad_cony = st.number_input("Edad del cónyuge", min_value=18, max_value=99, value=43, step=1)
    with col5:
        sexo_cony = st.selectbox(
            "Sexo del cónyuge",
            ["M", "H"],
            format_func=lambda s: {"H": "Hombre", "M": "Mujer"}[s],
        )

    # ── Datos de los hijos ─────────────────────────────────────────────────────
    st.header("👧👦 Datos de los hijos")
    st.caption("Mínimo 4 hijos requeridos conforme al caso analizado.")

    n_hijos = st.number_input(
        "Número de hijos a capturar", min_value=4, max_value=10, value=4, step=1
    )

    hijos: list[Hijo] = []
    cols_hijos = st.columns(min(int(n_hijos), 4))
    for i in range(int(n_hijos)):
        col_idx = i % 4
        with cols_hijos[col_idx]:
            st.subheader(f"Hijo {i + 1}")
            edad_h = st.number_input(
                f"Edad hijo {i + 1}", min_value=0, max_value=24, value=max(0, 10 - i * 2), step=1,
                key=f"edad_h_{i}",
            )
            sexo_h = st.selectbox(
                f"Sexo hijo {i + 1}", ["H", "M"],
                format_func=lambda s: {"H": "Hombre", "M": "Mujer"}[s],
                key=f"sexo_h_{i}",
            )
            estudia_h = st.checkbox(
                f"¿Estudia? (límite 25 a.)", value=True, key=f"est_h_{i}"
            )
            invalido_h = st.checkbox(
                f"¿Inválido?", value=False, key=f"inv_h_{i}",
                help="Si es inválido, la pensión no tiene límite de edad (Art. 138).",
            )
            hijos.append(Hijo(edad=int(edad_h), sexo=sexo_h, estudia=estudia_h, invalido=invalido_h))

    st.divider()
    calcular = st.button("✅ Calcular Monto Constitutivo", type="primary", use_container_width=True)

    if not calcular:
        st.info("⚠️ Ingresa todos los datos y presiona **Calcular Monto Constitutivo**.")
        return

    # ── Cálculo ───────────────────────────────────────────────────────────────
    try:
        r = calcular_monto_constitutivo_invalido(
            edad_invalido=int(edad_inv),
            sexo_invalido=sexo_inv,
            edad_conyuge=int(edad_cony),
            sexo_conyuge=sexo_cony,
            hijos=hijos,
            salario_diario_prom=float(sal_diario),
        )
    except ValueError as e:
        st.error(str(e))
        return

    # ── Encabezado de resultados ───────────────────────────────────────────────
    st.subheader(f"📊 Resultados — {nombre or 'Asegurado'}")
    st.caption(
        f"Inválido {r['edad_invalido']} años · Cónyuge {r['edad_conyuge']} años · "
        f"{r['n_hijos']} hijos · Sal. ${r['salario_mensual_prom']:,.2f}/mes"
    )

    # ── Métricas principales ───────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pensión mensual", f"${r['pension_mensual']:,.2f}")
    m2.metric("MC Seg. Invalidez (MCSI)", f"${r['mcsi']:,.2f}")
    m3.metric("MC Seg. Sobrevivencia (MCSS)", f"${r['mcss']:,.2f}")
    m4.metric("🏆 Monto Constitutivo Total", f"${r['mct']:,.2f}")

    st.divider()

    # ── Tabs: desglose y gráfica ───────────────────────────────────────────────
    tab_sec4, tab_sec5, tab_graf, tab_hijos = st.tabs(
        ["📋 Sección 4 — Invalidez", "📋 Sección 5 — Sobrevivencia", "📈 Gráfica", "👨‍👩‍👧‍👦 Detalle hijos"]
    )

    with tab_sec4:
        st.subheader("Sección 4 — Seguro de Invalidez")
        pasos_sec4 = [
            ("Salario diario prom. (últimas 500 sem.)",  f"${r['salario_diario_prom']:,.4f}"),
            ("Salario mensual prom. (C × 30)",           f"${r['salario_mensual_prom']:,.2f}"),
            ("% Cuantía básica (Art. 141)",              f"{PCT_CUANTIA_BASICA:.0%}"),
            ("% Asignación cónyuge (Art. 138 I)",        f"{PCT_CONYUGE:.0%}"),
            (f"% Asignación hijos ({r['n_hijos']} × 10%)", f"{r['n_hijos'] * PCT_HIJO:.0%}"),
            ("% Ayuda asistencial (IMSS promedio)",      f"{_core.PCT_AYUDA_ASIST:.0%}"),
            ("% Total sobre salario",                    f"{r['pct_total_pension']:.2%}"),
            ("Pensión mensual del inválido",             f"${r['pension_mensual']:,.2f}"),
            ("Pensión anual del inválido",               f"${r['pension_anual']:,.2f}"),
            ("Anualidad ä_x^inv (EMSSA)",                f"{r['ax_invalido']:,.6f}"),
            ("FACBI",                                    f"{_core.FACBI:.4f}"),
            ("Prima básica seg. invalidez (PBSI)",       f"${r['pbsi']:,.2f}"),
            ("Prima seg. invalidez hijos (PSIH)",        f"${r['psih']:,.2f}"),
            ("Prima neta seg. invalidez (PNSI)",         f"${r['pnsi']:,.2f}"),
            ("Recargo invalidez",                        f"{_core.RECARGO_INVALIDEZ:.2f}"),
            ("Monto constitutivo seg. invalidez (MCSI)", f"${r['mcsi']:,.2f}"),
        ]
        st.dataframe(
            pd.DataFrame(pasos_sec4, columns=["Concepto", "Valor"]),
            use_container_width=True, hide_index=True,
        )

    with tab_sec5:
        st.subheader("Sección 5 — Seguro de Sobrevivencia")
        pasos_sec5 = [
            ("% Pensión de viudez sobre cuantía base (Art. 131)", f"{PCT_VIUDEZ:.0%}"),
            ("Anualidad ä_y^sano cónyuge (EMSSAH/M)",             f"{r['ax_conyuge']:,.6f}"),
            ("Prima básica seg. sobrevivencia (PBSS)",             f"${r['pbss']:,.2f}"),
            ("Prima seg. inval. hijos — sobrevivencia (PSIH_SS)",  f"${r['psih_ss']:,.2f}"),
            ("Prima finiquito hijos (PFH) — 3 mensualidades",      f"${r['pfh']:,.2f}"),
            ("Prima neta seg. sobrevivencia (PNSS)",               f"${r['pnss']:,.2f}"),
            ("Recargo sobrevivencia",                              f"{_core.RECARGO_SOBREVIVENCIA:.2f}"),
            ("Monto constitutivo seg. sobrevivencia (MCSS)",       f"${r['mcss']:,.2f}"),
        ]
        st.dataframe(
            pd.DataFrame(pasos_sec5, columns=["Concepto", "Valor"]),
            use_container_width=True, hide_index=True,
        )
        st.markdown(
            f"""
**Monto Constitutivo Total**

| Componente | Monto (MXN) | % del Total |
|------------|------------:|------------:|
| MCSI       | ${r['mcsi']:>14,.2f} | {r['mcsi']/r['mct']*100:.1f}% |
| MCSS       | ${r['mcss']:>14,.2f} | {r['mcss']/r['mct']*100:.1f}% |
| **MCT**    | **${r['mct']:>12,.2f}** | **100.0%** |
"""
        )

    with tab_graf:
        fig, ax = plt.subplots(figsize=(8, 5))
        etiquetas = ["PBSI", "PSIH", "PBSS", "PSIH_SS", "PFH"]
        valores = [r["pbsi"], r["psih"], r["pbss"], r["psih_ss"], r["pfh"]]
        colores = ["#2196F3", "#64B5F6", "#E53935", "#EF9A9A", "#FF7043"]
        bars = ax.barh(etiquetas, valores, color=colores)
        ax.bar_label(bars, fmt=lambda v: f"${v:,.0f}", padding=4, fontsize=9)
        ax.set_xlabel("Monto (MXN)")
        ax.set_title(
            f"Componentes del Monto Constitutivo\n"
            f"MCT = ${r['mct']:,.2f}  ·  i = {tasa_i:.1%}  ·  {r['n_hijos']} hijos"
        )
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.grid(axis="x", alpha=0.3)
        # Leyenda de secciones
        from matplotlib.patches import Patch
        leyenda = [
            Patch(color="#2196F3", label="Sección 4 — Invalidez"),
            Patch(color="#E53935", label="Sección 5 — Sobrevivencia"),
        ]
        ax.legend(handles=leyenda, loc="lower right")
        fig.tight_layout()
        st.pyplot(fig, clear_figure=False)

    with tab_hijos:
        st.subheader("Detalle de hijos capturados")
        filas_hijos = []
        for i, h in enumerate(hijos, 1):
            filas_hijos.append({
                "#": i,
                "Edad": h.edad,
                "Sexo": {"H": "Hombre", "M": "Mujer"}.get(h.sexo, h.sexo),
                "¿Estudia?": "Sí" if h.estudia else "No",
                "¿Inválido?": "Sí" if h.invalido else "No",
                "Edad límite pensión": h.edad_limite if not h.invalido else "Indefinida",
                "Años restantes": h.anios_restantes if not h.invalido else "Indefinidos",
            })
        st.dataframe(pd.DataFrame(filas_hijos), use_container_width=True, hide_index=True)

    st.divider()

    # ── Análisis e interpretación ─────────────────────────────────────────────
    with st.expander("💬 Análisis e interpretación"):
        st.markdown(
            f"""
**Composición familiar**
- Inválido: {r['edad_invalido']} años · Sexo: {r['sexo_invalido']}
- Cónyuge: {r['edad_conyuge']} años · Sexo: {r['sexo_conyuge']}
- Número de hijos: **{r['n_hijos']}**

**Pensión mensual calculada**
- Cuantía básica: {PCT_CUANTIA_BASICA:.0%} × ${r['salario_mensual_prom']:,.2f} = ${PCT_CUANTIA_BASICA * r['salario_mensual_prom']:,.2f}
- Asignación cónyuge: {PCT_CONYUGE:.0%}
- Asignación hijos: {r['n_hijos']} × {PCT_HIJO:.0%} = {r['n_hijos'] * PCT_HIJO:.0%}
- Ayuda asistencial: {_core.PCT_AYUDA_ASIST:.0%}
- **Total: {r['pct_total_pension']:.2%} → ${r['pension_mensual']:,.2f}/mes**

**Sección 4 — Seguro de Invalidez**
- PBSI = ${r['pbsi']:,.2f}  (anualidad ä = {r['ax_invalido']:.4f})
- PSIH = ${r['psih']:,.2f}  (contingencia invalidez de hijos)
- PNSI = ${r['pnsi']:,.2f}
- MCSI = ${r['mcsi']:,.2f}  (recargo {_core.RECARGO_INVALIDEZ:.0%})

**Sección 5 — Seguro de Sobrevivencia**
- PBSS = ${r['pbss']:,.2f}  (anualidad cónyuge ä = {r['ax_conyuge']:.4f})
- PSIH_SS = ${r['psih_ss']:,.2f}  (orfandad post-fallecimiento inválido)
- PFH = ${r['pfh']:,.2f}  (finiquito 3 mensualidades — Art. 136 LSS)
- PNSS = ${r['pnss']:,.2f}
- MCSS = ${r['mcss']:,.2f}  (recargo {_core.RECARGO_SOBREVIVENCIA:.0%})

**Monto Constitutivo Total: ${r['mct']:,.2f}**
- La suma asegurada = MCT − Saldo cuenta individual AFORE.
- Tasa técnica utilizada: {tasa_i:.2%} · FACBI: {_core.FACBI:.4f}
"""
        )


if __name__ == "__main__":
    render()