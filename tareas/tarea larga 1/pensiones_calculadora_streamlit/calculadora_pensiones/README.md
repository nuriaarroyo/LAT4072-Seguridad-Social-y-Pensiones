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

## Helpers básicos (SBC, semanas, tramos)

### `factibilidad_de_retiro(age_now, exp_retirement_age, weeks_now) -> bool`
**Descripción:** valida si a la edad esperada se alcanzan semanas mínimas requeridas.  
**Fórmula:**
\[
weeks\_{ret} = weeks\_{now} + (age\_{ret}-age\_{now})\cdot 52
\]
Condición:
\[
weeks\_{ret} \ge \text{min\_weeks\_required}
\]

---

### `uma_m() -> float`
**Descripción:** regresa UMA mensual desde `UNITS["uma_monthly"]`.

---

### `salario_maximo_cotizable() -> float`
**Descripción:** calcula el tope de SBC mensual (25 UMA).  
**Fórmula:**
\[
SBC_{max,m} = 25 \cdot UMA_m
\]

---

### `salario_de_cotizacion(salary_monthly) -> float`
**Descripción:** aplica tope al salario mensual para obtener SBC mensual.  
**Fórmula:**
\[
SBC_m = \min(salary\_monthly, SBC_{max,m})
\]

---

### `sbc_entre_uma(salary_monthly) -> float`
**Descripción:** expresa el SBC mensual en UMAs.  
**Fórmula:**
\[
SBC_{\text{UMA}} = \frac{salary\_monthly}{UMA_m}
\]

---

### `indicador_de_cotizacion(sbc_mensual) -> int`
**Descripción:** asigna el **id de tramo** (CEAV) según brackets transitorios del JSON (`upper`).  
**Regla:** primer `upper` tal que \( sbc\_mensual \le upper \); si no hay, usa el último id.

---

### `tramo_por_brackets(x, brackets) -> int`
**Descripción:** helper genérico para devolver tramo por lista de brackets con `upper`.  
**Regla:** igual a `indicador_de_cotizacion`, pero genérico.

---

## Aportaciones mensuales

### `aportaciones_totales_mensuales(aport_obl, aport_vol) -> float`
**Descripción:** suma aportación obligatoria + voluntaria.  
**Fórmula:**
\[
C_m = C_{obl,m} + C_{vol,m}
\]

---

### `tasa_obligatoria_total() -> float`
**Descripción:** tasa obligatoria total sobre SBC (suma de componentes del JSON).  
**Fórmula:**
\[
\tau_{obl} = \tau_{worker} + \tau_{emp,ret} + \tau_{emp,ceav} + \tau_{gov}
\]

---

### `aportacion_obligatoria(sbc_mensual) -> float`
**Descripción:** monto mensual obligatorio depositado.  
**Fórmula:**
\[
C_{obl,m} = SBC_m \cdot \tau_{obl}
\]

---

### `aportacion_voluntaria(sbc_mensual, voluntary_rate) -> float`
**Descripción:** monto mensual voluntario.  
**Fórmula:**
\[
C_{vol,m} = SBC_m \cdot \alpha
\]
donde \(\alpha\) = `voluntary_rate`.

---

## Proyección SCI al retiro (saldo cuenta individual)

### `saldo_inicial_aprox_desde_semanas(weeks_now, salary_monthly, annual_return) -> float`
**Descripción:** estima SCI0 a partir de semanas cotizadas, asumiendo:
- meses pasados \(\approx weeks\_now / 4.3333\)
- SBC constante topado
- aportación obligatoria constante
- capitalización mensual

**Fórmulas:**
\[
months\_{past} \approx round\left(\frac{weeks\_{now}}{4.3333}\right)
\]
\[
j_m = \frac{r}{12}
\]
Recurrencia:
\[
SCI_{t+1} = (SCI_t + C_{obl,m})\,(1+j_m)
\]

---

### `monto_acumulado_al_retiro(age_now, exp_retirement_age, salary_monthly, voluntary_rate, tasa_retorno_anual, saldo_inicial=0) -> float`
**Descripción:** proyecta el SCI al retiro con aportaciones obligatorias+voluntarias.  
**Fórmulas:**
\[
T = (age_{ret}-age_{now})\cdot 12
\]
\[
j_m = \frac{r}{12}
\]
\[
C_m = SBC_m\cdot\tau_{obl} + SBC_m\cdot\alpha
\]
Recurrencia:
\[
SCI_{t+1} = (SCI_t + C_m)\,(1+j_m)
\]

---

### `sci0_from_inputs_simple(saldo_actual, weeks_now, salary_monthly, annual_return) -> float`
**Descripción:** regla para SCI0:
- si `saldo_actual` > 0 → usarlo
- si no, y `weeks_now` > 0 → aproximar con `saldo_inicial_aprox_desde_semanas`
- si no → 0

---

## Conversión SCI → pensión mensual (actuarial con qx por género)

### `_sex_key(gender) -> str`
**Descripción:** normaliza entradas a `"male"` o `"female"` (acepta 0/1 y strings).

---

### `_qx(age, gender) -> float`
**Descripción:** lee \(q_x\) anual desde JSON `TABLES["mortality_qx_2023"][sex][edad]`.  
**Definición:**
\[
q_x = \Pr(\text{muerte en el año }[x,x+1)\mid \text{vivo a }x)
\]

---

### `_annuity_factor_monthly(exp_ret_age, gender) -> float`
**Descripción:** calcula factor actuarial mensual de **renta anticipada**:
\[
\ddot{a}^{(12)}_x = \sum_{k\ge 0} v_m^k \, {}_k p_x
\]
donde:
\[
v_m = (1+i)^{-1/12}
\]

**Aproximación usada en el código (mensualizando \(q_x\)):**
\[
p_{\text{year}}(x)=1-q_x,\quad p_m(x)=p_{\text{year}}(x)^{1/12}
\]
Supervivencia acumulada:
\[
{}_k p_x \approx \prod_{j=1}^{k} p_m(\text{edad en }j)
\]
y se suma hasta \(\omega=110\).

---

### `pension_mensual_desde_sci(sci, age_ret, gender) -> float`
**Descripción:** convierte SCI a pensión mensual actuarial (sin primas/seguros).  
**Fórmula:**
\[
R = \frac{SCI}{\ddot{a}^{(12)}_x}
\]

---

## Función principal

### `replacement_rate_lss1997(age_now, salary_monthly, voluntary_rate, assumptions=None) -> dict`
**Descripción:** pipeline completo:
1) calcula SBC y semanas al retiro  
2) proyecta SCI al retiro  
3) calcula pensión actuarial \(R\)  
4) calcula PG (si cumple elegibilidad)  
5) pensión final = máximo entre \(R\) y PG  
6) RR = pensión / salario mensual

**Ecuaciones:**

1) semanas al retiro:
\[
weeks\_{ret} = weeks\_{now} + (age\_{ret}-age\_{now})\cdot 52
\]

2) SCI (recurrencia mensual):
\[
SCI_{t+1} = (SCI_t + C_m)\,(1+j_m)
\]

3) renta mensual actuarial:
\[
R = \frac{SCI}{\ddot{a}^{(12)}_x}
\]

4) piso por pensión garantizada:
\[
pension = \max(R,\; PG)
\]
con:
\[
PG = f(SBC,\;Edad,\;Semanas)
\]
(lookup vía `pension_garantizada_mensual`)

5) tasa de reemplazo:
\[
RR = \frac{pension}{salary\_monthly}
\]

**Salida (`dict`):**
- `replacement_rate`, `pension_monthly`, `sci`
- `pension_actuarial_R`, `pension_garantizada`
- auxiliares (`sbc_monthly`, `weeks_at_ret`, `annuity_factor_monthly`, etc.)

---

## Solver y curva

### `solve_voluntary_rate_for_target(age_now, salary_monthly, target_rr, lo=0, hi=0.30, tol=1e-4, max_iter=60, assumptions=None) -> dict`
**Descripción:** búsqueda binaria para encontrar \(\alpha\) tal que:
\[
RR(\alpha) \approx RR^\*
\]
Criterio:
\[
|RR(\alpha)-RR^\*|\le tol
\]

---

### `rr_curve(age_now, salary_monthly, voluntary_rates, assumptions=None) -> pd.DataFrame`
**Descripción:** evalúa una malla de tasas voluntarias y produce:
\[
\{(\alpha_i,\; RR(\alpha_i))\}_{i=1}^n
\]
**Salida:** DataFrame con columnas `voluntary_rate`, `replacement_rate`.
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
