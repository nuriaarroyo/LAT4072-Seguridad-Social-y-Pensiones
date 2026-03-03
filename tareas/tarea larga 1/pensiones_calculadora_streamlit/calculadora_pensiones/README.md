# Calculadora de Pensiones IMSS (LSS 1973 / LSS 1997) — Streamlit

App interactiva para **explorar y calcular escenarios de pensión** bajo el IMSS, enfocada en:
- **LSS 1973** (Cesantía en Edad Avanzada y Vejez)
- **LSS 1997** (Cuenta individual, pensión garantizada, tasa de reemplazo y ahorro voluntario)

🔗 **App en Streamlit:** https://lat4072-seguridad-social-y-pensiones-rmryh9tdm8s7botpvdrjjw.streamlit.app/

> Nota: Este proyecto es académico/educativo. No sustituye asesoría legal, actuarial o financiera.

---

# LSS 1997 — Core (función por función)

Archivo: `pensiones/core/lss1997_ret.py`  
Objetivo: calcular **SCI al retiro**, convertirlo a **pensión mensual actuarial** y obtener **tasa de reemplazo (RR)**, incorporando **Pensión Garantizada (PG)** como piso.

---

---

## Requisitos

- Python 3.10+ (recomendado)
- Paquetes principales:
  - `streamlit`
  - `numpy`, `pandas`
  - `plotly` (para gráficas interactivas)
  - (opcional) `matplotlib`

---

## Instalación local

1) Clona el repo:
```bash
git clone <URL_DEL_REPO>
cd <CARPETA_DEL_REPO>
