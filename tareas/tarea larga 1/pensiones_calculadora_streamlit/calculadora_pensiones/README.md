# Calculadora de Pensiones IMSS (LSS 1973 / LSS 1997) — Streamlit

App interactiva para **explorar y calcular escenarios de pensión** bajo el IMSS, enfocada en:
- **LSS 1973** (Cesantía en Edad Avanzada y Vejez)
- **LSS 1997** (Cuenta individual, pensión garantizada, tasa de reemplazo y ahorro voluntario)

🔗 **App en Streamlit:** https://lat4072-seguridad-social-y-pensiones-rmryh9tdm8s7botpvdrjjw.streamlit.app/

> Nota: Este proyecto es académico/educativo. No sustituye asesoría legal, actuarial o financiera.

---

## ¿Qué puedes hacer con la app?

- Calcular resultados para **LSS 1973** (lógica tipo “Excel” por pasos).
- Calcular resultados para **LSS 1997**:
  - estimación de **tasa de reemplazo (RR)**
  - solver para encontrar **tasa de ahorro voluntario** necesaria para una RR objetivo
  - curvas RR vs. aportación voluntaria (gráficas)
  - **pensión garantizada (PG)** vía tabla / lookup (periodo de transición 2021–2031).
- Visualizar resultados con gráficas y componentes interactivos (Streamlit / Plotly).


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
