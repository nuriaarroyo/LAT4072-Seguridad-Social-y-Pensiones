# Calculadora de Pensiones (Streamlit) — plantilla de proyecto

Este repo es un **esqueleto listo** para que conectes tus funciones actuariales (ISR 2026, cuotas LSS 1997 + INFONAVIT, tasa de reemplazo LSS 1997, y pensión/tasa LSS 1973) a una **interfaz tipo app** en Streamlit.

> Nota importante: **Los parámetros y tablas legales** (tarifa ISR 2026, UMA, tasas IMSS/INFONAVIT, supuestos del Excel visto en clase) van en `pensiones/data/` para que tú los pegues/actualices sin tocar la UI.

---

## 1) Instalación rápida

### a) Crear entorno (opcional pero recomendado)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### b) Instalar dependencias
```bash
pip install -r requirements.txt
```

## 2) Correr la app
```bash
streamlit run app.py
```

---

## 3) Dónde poner tus cosas

### Motor (lógica)
- `pensiones/core/isr_2026.py`  → cálculo de ISR mensual 2026 (tarifa por rangos).
- `pensiones/core/ss_1997.py`   → cuotas IMSS + INFONAVIT (empleado/empleador/gobierno), desglose por seguro.
- `pensiones/core/lss1997_ret.py` → tasa de reemplazo (CESANTÍA/VEJEZ), y búsqueda de ahorro voluntario para meta.
- `pensiones/core/lss1973_ret.py` → pensión + tasa de reemplazo por edades 60–65.

### Datos / parámetros (tú los llenas)
- `pensiones/data/isr_2026_tarifa.json`
- `pensiones/data/ss_1997_rates.json`
- `pensiones/data/lss1997_assumptions.json`
- `pensiones/data/lss1973_assumptions.json`

### UI (Streamlit)
- `app.py` (router principal)
- `pensiones/ui/pages/` (3 páginas: ISR+SS, LSS97, LSS73)

### Plots
- La app **puede guardar** gráficos en `plots/` con `pensiones/utils/plotting.py`.

---

## 4) Qué te falta rellenar (checklist rápido)
- [ ] Pegar la **tarifa ISR 2026** en `pensiones/data/isr_2026_tarifa.json`.
- [ ] Pegar tasas de **cuotas IMSS + INFONAVIT** y reglas (topes/UMA/SBC) en `pensiones/data/ss_1997_rates.json`.
- [ ] Copiar supuestos del Excel LSS 1997 a `pensiones/data/lss1997_assumptions.json`.
- [ ] Copiar supuestos del Excel LSS 1973 a `pensiones/data/lss1973_assumptions.json`.
- [ ] Implementar/ajustar funciones en `pensiones/core/*` para que coincidan con tu clase.

---

## 5) Entrega sugerida para tu profe (actuario)
1) ZIP del proyecto (este repo).
2) Un PDF/Word con:
   - supuestos,
   - 2–3 casos de prueba,
   - comentarios de resultados,
   - screenshots de la app.

---

Si quieres, pega aquí tus tablas (ISR y tasas IMSS/INFONAVIT) y los supuestos del Excel y te dejo el **motor completo**.
