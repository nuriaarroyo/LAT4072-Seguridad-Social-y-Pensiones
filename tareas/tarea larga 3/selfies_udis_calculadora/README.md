# Calculadora de bonos de retiro tipo SeLFIES/RSB en UDIS

Proyecto en Streamlit para la tarea: construir una metodología de valuación de bonos de retiro propuestos por Merton usando UDIS y calcular, para edades 16 a 55, cuántos bonos se requieren para financiar una pensión anual de 72,000 UDIS.

## 1. Qué calcula

La calculadora modela un bono tipo **SeLFIES / Retirement Security Bond** con estas características:

- **Forward-starting:** no paga antes de la edad de retiro.
- **Income-only:** paga cupones durante el retiro, sin principal final.
- **Real:** los pagos están denominados en UDIS.
- **Plazo de pago fijo:** por defecto 20 años, como en el ejemplo base del artículo.
- **Número de bonos:** se determina como ingreso objetivo anual dividido entre cupón anual por bono.

La edad no cambia el número de bonos. La edad cambia el precio actual de esos bonos, porque no cuesta lo mismo comprar hoy un flujo que empieza en 49 años que uno que empieza en 10 años.

## 2. Fórmulas principales

Supuestos:

- Edad actual: `x`.
- Edad de retiro: `R`.
- Años al retiro: `n = R - x`.
- Pensión anual objetivo: `B` UDIS.
- Cupón anual por bono: `c` UDIS.
- Años de pago: `L`.
- Tasa real spot para plazo `t`: `r(t)`.

Número de bonos:

```text
N = B / c
```

Precio de un bono:

```text
P_x = sum_{j=0}^{L-1} c * (1+g)^j * v(n+j)
```

con capitalización anual:

```text
v(t) = 1 / (1 + r(t))^t
```

Costo total para comprar la pensión:

```text
C_x = N * P_x
```

En la versión pura en UDIS se usa `g = 0`. Si se quiere simular indexación adicional al estándar de vida, se puede usar `g > 0`.

## 3. Archivos del proyecto

```text
selfies_udis_calculadora/
├── app.py
├── requirements.txt
├── README.md
├── METODOLOGIA.md
├── datos/
│   ├── curva_original_udibonos.csv
│   ├── curva_real_udis.csv
│   └── valor_udi.csv
├── src/
│   └── selfies_calculator.py
├── scripts/
│   ├── calcular_curva_udibonos.py
│   └── run_example.py
└── outputs/
```

## 4. Cómo correr la app

En terminal, dentro de la carpeta del proyecto:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para correr el ejemplo sin Streamlit:

```bash
python scripts/run_example.py
```

Para regenerar `datos/curva_real_udis.csv` desde la captura original de UDIBONOS:

```bash
python scripts/calcular_curva_udibonos.py
```

## 5. Qué datos debes llenar

### A. `datos/curva_original_udibonos.csv`

Este archivo guarda la captura de mercado original: fecha, plazo, precio y tasa de UDIBONOS. El script
`scripts/calcular_curva_udibonos.py` convierte la tasa porcentual a decimal y genera la curva que usa la app.

### B. `datos/curva_real_udis.csv`

Este es el archivo más importante. Debe contener una curva real de descuento en UDIS.

Columnas obligatorias:

```text
tenor_years,annual_real_rate
```

Ejemplo:

```text
tenor_years,annual_real_rate
1,0.025
2,0.027
3,0.029
5,0.032
10,0.035
20,0.0375
30,0.039
```

Las tasas van en decimal. Por ejemplo, 3.5% se captura como `0.035`.

Puedes usar tasas reales de UDIBONOS como proxy de la curva real mexicana. Si no tienes todos los plazos, la app interpola linealmente. Si el flujo queda más allá del último plazo disponible, la app usa la última tasa observada como tasa de largo plazo.

### C. `datos/valor_udi.csv`

Este archivo sólo sirve si quieres convertir resultados de UDIS a pesos.

Columnas:

```text
fecha,valor_udi_mxn
```

Ejemplo:

```text
fecha,valor_udi_mxn
2026-05-12,8.838416
```

En la app también puedes escribir directamente el valor de la UDI en la barra lateral.

## 6. Supuestos recomendados para la entrega

Para contestar la tarea de forma limpia, usa:

- Edad mínima: 16.
- Edad máxima: 55.
- Edad de retiro: 65.
- Pensión anual objetivo: 72,000 UDIS.
- Cupón anual por bono: 5 UDIS.
- Años de pago: 20.
- Primer pago: al cumplir edad de retiro.
- Curva real: curva de tasas reales en UDIS, usando UDIBONOS como proxy.
- Indexación adicional al estándar de vida: 0% en la versión base.
- Sin mortalidad en la versión base, porque el bono tiene pagos de plazo fijo y no es una renta vitalicia actuarial.

## 7. Nota metodológica importante

El artículo propone indexar a consumo per cápita para cubrir riesgo de estándar de vida. En esta adaptación con UDIS se cubre inflación, pero no necesariamente crecimiento del estándar de vida. Por eso la app permite capturar un crecimiento real adicional `g` como sensibilidad. Para la respuesta base de la tarea, lo más claro es dejar `g = 0` y explicar esta limitación.

## 8. Interpretación rápida

Si el cupón anual por bono es 5 UDIS y la pensión objetivo es 72,000 UDIS al año:

```text
N = 72,000 / 5 = 14,400 bonos
```

Ese número es igual para todas las edades. Lo que cambia por edad es el costo de comprar esos bonos hoy.
