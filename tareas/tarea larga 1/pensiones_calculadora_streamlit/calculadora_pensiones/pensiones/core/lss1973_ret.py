from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTES Y TABLAS LSS 1973
# ──────────────────────────────────────────────────────────────────────────────

UMA_DIARIA_DEFAULT = 117.31  # tu valor actual en el script
SEMANAS_MINIMAS = 500
DIAS_ANO = 365

# Tabla oficial LSS 1973 (cociente salario/UMA → cuantía básica %, incremento anual %)
TABLA_LSS1973: List[Tuple[float, float, float]] = [
    (1.00,  1.5000, 0.0000),
    (1.25,  0.4300, 0.0111), 
    (1.50,  0.4000, 0.0111),
    (1.75,  0.4000, 0.0111),
    (2.00,  0.4000, 0.0149),
    (2.25,  0.4000, 0.0187),
    (2.50,  0.4000, 0.0149),
    (2.75,  0.3550, 0.0149),
    (3.00,  0.3400, 0.0149),
    (3.25,  0.3400, 0.0149),
    (3.50,  0.3400, 0.0149),
    (3.75,  0.3400, 0.0149),
    (4.00,  0.2400, 0.0149),
    (4.25,  0.2200, 0.0149),
    (4.50,  0.2100, 0.0149),
    (4.75,  0.2000, 0.0149),
    (10.00, 0.1300, 0.0245),  # último renglón — aplica para > 4.75×UMA
]

# % de pensión según edad de retiro (Paso 12)
TABLA_EDAD_PCT: Dict[int, float] = {
    60: 0.75, 61: 0.80, 62: 0.85,
    63: 0.90, 64: 0.95, 65: 1.00,
}


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS (fiel al Excel)
# ──────────────────────────────────────────────────────────────────────────────

def buscar_tabla_lss1973(salario_diario: float, uma_diaria: float) -> tuple[float, float]:
    """Pasos 3-4: cociente sal/UMA → cuantía básica % e incremento anual %."""
    cociente = salario_diario / uma_diaria
    pct_basica, pct_incr = TABLA_LSS1973[-1][1], TABLA_LSS1973[-1][2]
    for limite, cb, ci in TABLA_LSS1973:
        if cociente <= limite:
            pct_basica, pct_incr = cb, ci
            break
    return pct_basica, pct_incr


def redondear_anos_excel(semanas_exceso: float) -> float:
    """
    Regla de redondeo del Excel (celda C10 del Detalle):
        anos_exact = semanas_exceso / 52
        frac_semanas = (anos_exact − INT(anos_exact)) × 52
          < 13  →  INT(anos_exact)
         13–26  →  INT(anos_exact) + 0.5
          > 26  →  INT(anos_exact) + 1.0
    """
    anos_exact = semanas_exceso / 52.0
    int_anos = math.floor(anos_exact)  # Excel INT() = floor
    frac_weeks = (anos_exact - int_anos) * 52.0
    if frac_weeks < 13:
        return float(int_anos)
    elif frac_weeks <= 26:
        return int_anos + 0.5
    else:
        return int_anos + 1.0


# ──────────────────────────────────────────────────────────────────────────────
# CORE: cálculo 13 pasos
# ──────────────────────────────────────────────────────────────────────────────

def calcular_pension_lss1973(
    *,
    edad_actual: int,
    salario_diario_avg: float,
    semanas_cotizadas: int,
    edad_retiro: int,
    densidad: float = 1,
    pct_conyuge: float = 0.15,
    pct_hijos_total: float = 0.00,
    pct_art14: float = 0.11,
    uma_diaria: float = UMA_DIARIA_DEFAULT,
    include_existing: bool = True,
) -> dict:
    """
    Replica los 13 pasos de la hoja 'Detalle 80%/100% DC' (fiel a tu script).

    - sem_futuras = INT((edad_retiro − edad_actual) × 52 × densidad)
    - sem_existentes = semanas_cotizadas si include_existing else 0
    - redondeo de años: regla Excel (3 tramos)
    - incr_diario = sal_d × pct_incr × anos_redondeado (usa C10)
    - clamp: [UMA diaria, salario diario]
    - pension_mensual = pension_diaria × 365/12
    - tasa_reemplazo = pension_mensual / (sal_d × 30)
    """
    sal_d = float(salario_diario_avg)

    # ── Paso 0-1
    sem_futuras = int((edad_retiro - edad_actual) * 52 * densidad)
    sem_existentes = int(semanas_cotizadas) if include_existing else 0
    total_semanas = sem_existentes + sem_futuras

    # ── Paso 2
    semanas_exceso = total_semanas - SEMANAS_MINIMAS
    anos_exacto = semanas_exceso / 52.0
    anos_redondeado = redondear_anos_excel(semanas_exceso)

    # ── Pasos 3-4
    pct_basica, pct_incr = buscar_tabla_lss1973(sal_d, uma_diaria)

    # ── Paso 5
    cuantia_basica_diaria = sal_d * pct_basica
    cuantia_basica_anual = cuantia_basica_diaria * DIAS_ANO

    # ── Paso 6
    incr_diario = sal_d * pct_incr * anos_redondeado
    incr_anual = incr_diario * DIAS_ANO

    # ── Paso 7
    cuantia_base_diaria = cuantia_basica_diaria + incr_diario
    cuantia_base_anual = cuantia_basica_anual + incr_anual

    # ── Pasos 8-10
    factor = (1 + pct_conyuge) * (1 + pct_hijos_total) * (1 + pct_art14)

    # ── Paso 11
    pension_base_diaria = cuantia_base_diaria * factor
    pension_base_anual = pension_base_diaria * DIAS_ANO

    # ── Paso 12
    pct_edad = TABLA_EDAD_PCT.get(int(edad_retiro), 1.0)
    pension_diaria_raw = pension_base_diaria * pct_edad

    # Cota inferior = UMA; cota superior = 100%×sal_d
    pension_diaria = max(float(uma_diaria), min(float(sal_d), float(pension_diaria_raw)))

    pension_mensual = pension_diaria * DIAS_ANO / 12
    pension_anual = pension_diaria * DIAS_ANO
    pension_aguinaldo = pension_diaria * DIAS_ANO / 12 * 13

    # ── Paso 13
    tasa_reemplazo = pension_mensual / (sal_d * 30.0) if sal_d > 0 else 0.0

    return {
        "edad_retiro": edad_retiro,
        "sem_futuras": sem_futuras,
        "sem_existentes": sem_existentes,
        "total_semanas": total_semanas,
        "semanas_exceso": round(semanas_exceso, 4),
        "anos_exacto": round(anos_exacto, 4),
        "anos_redondeado": float(anos_redondeado),
        "cociente_sal_uma": round(sal_d / uma_diaria, 4) if uma_diaria else float("nan"),
        "pct_cuantia_basica": float(pct_basica),
        "pct_incremento": float(pct_incr),
        "cuantia_basica_diaria": round(cuantia_basica_diaria, 4),
        "cuantia_basica_anual": round(cuantia_basica_anual, 2),
        "incr_diario": round(incr_diario, 4),
        "incr_anual": round(incr_anual, 2),
        "cuantia_base_diaria": round(cuantia_base_diaria, 4),
        "cuantia_base_anual": round(cuantia_base_anual, 2),
        "factor_familiar": round(factor, 6),
        "pension_base_diaria": round(pension_base_diaria, 4),
        "pension_base_anual": round(pension_base_anual, 2),
        "pct_edad": float(pct_edad),
        "pension_diaria_raw": round(pension_diaria_raw, 4),
        "cota_inferior": round(float(uma_diaria), 2),
        "cota_superior": round(float(sal_d), 2),
        "pension_diaria": round(pension_diaria, 4),
        "pension_mensual": round(pension_mensual, 2),
        "pension_anual": round(pension_anual, 2),
        "pension_aguinaldo": round(pension_aguinaldo, 2),
        "tasa_reemplazo": round(tasa_reemplazo, 6),
    }


def tabla_sensibilidades_lss1973(
    *,
    edad_actual: int,
    salario_diario_avg: float,
    semanas_cotizadas: int,
    min_age: int,
    max_age: int,
    densidad: float,
    pct_conyuge: float,
    pct_hijos_total: float,
    pct_art14: float,
    uma_diaria: float,
    include_existing: bool,
) -> pd.DataFrame:
    rows = []
    prev_rr = None
    acum_pp = 0.0

    for edad in range(int(min_age), int(max_age) + 1):
        r = calcular_pension_lss1973(
            edad_actual=edad_actual,
            salario_diario_avg=salario_diario_avg,
            semanas_cotizadas=semanas_cotizadas,
            edad_retiro=edad,
            densidad=densidad,
            pct_conyuge=pct_conyuge,
            pct_hijos_total=pct_hijos_total,
            pct_art14=pct_art14,
            uma_diaria=uma_diaria,
            include_existing=include_existing,
        )
        rr_pct = r["tasa_reemplazo"] * 100
        delta_pp = round(rr_pct - prev_rr, 4) if prev_rr is not None else None
        if delta_pp is not None:
            acum_pp = round(acum_pp + delta_pp, 4)

        rows.append(
            {
                "Edad": edad,
                "Pensión Mensual (MXN)": r["pension_mensual"],
                "Tasa de Reemplazo": r["tasa_reemplazo"],
                "Δ Marginal (pp)": delta_pp,
                "Δ Acumulado (pp)": round(acum_pp, 4) if prev_rr is not None else None,
            }
        )
        prev_rr = rr_pct

    return pd.DataFrame(rows)