from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
from bisect import bisect_left

import numpy as np
import pandas as pd

from pensiones.utils.io import load_json


# =============================================================================
# Carga de supuestos
# =============================================================================

DATA_PATH = Path(__file__).resolve().parents[1] / "data"
P = load_json(DATA_PATH / "lss1997_assumptions.json")

ASS: Dict[str, Any] = P["assumptions"]
UNITS: Dict[str, Any] = P.get("units", {})
ELIG: Dict[str, Any] = P["eligibility"]
RATES: Dict[str, Any] = P.get("contribution_rates_base", {})
TABLES: Dict[str, Any] = P["tables"]


# =============================================================================
# Helpers básicos (SBC, semanas, tramos)
# =============================================================================

def factibilidad_de_retiro(age_now: int, exp_retirement_age: int, weeks_now: int) -> bool:
    """Valida que se alcancen semanas mínimas a la edad esperada."""
    weeks_at_ret = weeks_now + (exp_retirement_age - age_now) * 52
    return bool(weeks_at_ret >= ELIG["min_weeks_required"])


def salario_maximo_cotizable() -> float:
    """Salario máximo cotizable mensual = 25 UMA (asumiendo tope 25)."""
    return float(25.0 * ASS["uma_m"])


def salario_de_cotizacion(salary_monthly: float) -> float:
    """SBC mensual topado."""
    return float(min(salary_monthly, salario_maximo_cotizable()))


def sbc_entre_uma(salary_monthly: float) -> float:
    """SBC en UMAs."""
    return float(salary_monthly / ASS["uma_m"])


def indicador_de_cotizacion(sbc_mensual: float) -> int:
    """
    Devuelve el id del tramo CEAV (3..11) según la tabla transitoria del JSON.
    Espera algo como:
        TABLES["ceav_employer_transitory"]["brackets"] = [
            {"id": 3, "upper": 8475.53}, ..., {"id": 11, "upper": None}
        ]
    """
    brackets = TABLES["ceav_employer_transitory"]["brackets"]

    uppers: list[float] = []
    ids: list[int] = []

    for b in brackets:
        ids.append(int(b["id"]))
        if b["upper"] is not None:
            uppers.append(float(b["upper"]))

    pos = bisect_left(uppers, float(sbc_mensual))
    if pos >= len(ids):
        return ids[-1]
    return ids[pos]


def tramo_por_brackets(x: float, brackets: list[dict]) -> int:
    """Helper genérico: devuelve id de tramo por lista de brackets con upper."""
    uppers: list[float] = []
    ids: list[int] = []
    for b in brackets:
        ids.append(int(b["id"]))
        if b["upper"] is not None:
            uppers.append(float(b["upper"]))
    pos = bisect_left(uppers, float(x))
    if pos >= len(ids):
        return ids[-1]
    return ids[pos]


# =============================================================================
# Aportaciones mensuales
# =============================================================================

def aportaciones_totales_mensuales(aport_obl: float, aport_vol: float) -> float:
    return float(aport_obl + aport_vol)


def tasa_obligatoria_total() -> float:
    """
    Tasa obligatoria total (sobre SBC).
    Ajusta llaves si tu JSON las llama distinto.
    """
    return float(
        ASS["aportacion_trabajador"]
        + ASS["aportacion_empleador_retiro"]
        + ASS["aportacion_empleador_ceav"]
        + ASS["aportacion_gobierno"]
    )


def aportacion_obligatoria(sbc_mensual: float) -> float:
    return float(sbc_mensual * tasa_obligatoria_total())


def aportacion_voluntaria(sbc_mensual: float, voluntary_rate: float) -> float:
    return float(sbc_mensual * float(voluntary_rate))


# =============================================================================
# Proyección SCI (saldo de cuenta individual) al retiro
# =============================================================================
def saldo_inicial_aprox_desde_semanas(
    weeks_now: int,
    salary_monthly: float,
    annual_return: float,
) -> float:
    """
    Aproximación simple:
    - Convierte semanas a meses de cotización pasada: months_past ≈ weeks_now / 4.3333
    - Asume SBC constante = salario_de_cotizacion(salary_monthly)
    - Aportación obligatoria mensual constante
    - Capitaliza a tasa annual_return/12 sobre el periodo pasado

    NO ajusta inflación. NO usa historia salarial. Es solo para tener SCI0 ~ razonable.
    """
    if weeks_now <= 0:
        return 0.0

    months_past = int(round(weeks_now / 4.3333333333))
    months_past = max(months_past, 0)

    sbc_m = salario_de_cotizacion(float(salary_monthly))
    c_obl = aportacion_obligatoria(sbc_m)

    j_m = float(annual_return) / 12.0

    sci0 = 0.0
    for _ in range(months_past):
        sci0 = (sci0 + c_obl) * (1.0 + j_m)

    return float(sci0)


def monto_acumulado_al_retiro(
    age_now: int,
    exp_retirement_age: int,
    salary_monthly: float,
    voluntary_rate: float,
    tasa_retorno_anual: float,
    saldo_inicial: float = 0.0,
) -> float:
    T = max((exp_retirement_age - age_now) * 12, 0)
    if T == 0:
        return float(saldo_inicial)

    sbc_m = salario_de_cotizacion(salary_monthly)

    c_obl = aportacion_obligatoria(sbc_m)
    c_vol = aportacion_voluntaria(sbc_m, voluntary_rate)
    contrib_m = aportaciones_totales_mensuales(c_obl, c_vol)

    j_m = tasa_retorno_anual / 12.0

    sci = float(saldo_inicial)
    for _ in range(T):
        sci = (sci + contrib_m) * (1.0 + j_m)

    return float(sci)

def sci0_from_inputs_simple(
    saldo_actual: Optional[float],
    weeks_now: Optional[int],
    salary_monthly: float,
    annual_return: float,
) -> float:
    """
    Regla simple:
    - Si saldo_actual no es None y > 0: usarlo.
    - Si no, pero weeks_now > 0: estimar SCI0 con función simple.
    - Si no: 0
    """
    if saldo_actual is not None and float(saldo_actual) > 0:
        return float(saldo_actual)

    if weeks_now is not None and int(weeks_now) > 0:
        return saldo_inicial_aprox_desde_semanas(
            weeks_now=int(weeks_now),
            salary_monthly=float(salary_monthly),
            annual_return=float(annual_return),
        )

    return 0.0


# =============================================================================
# Conversión SCI -> pensión mensual (actuarial / fallback)
# =============================================================================

def _life_expectancy_years_at_retirement(age_ret: int) -> float:
    """
    Fallback: usa esperanza de vida (años) desde tabla:
        TABLES["life_expectancy_at_retirement"]["values"][str(age_ret)]
    """
    tab = TABLES.get("life_expectancy_at_retirement")
    if tab is None:
        raise KeyError("Falta TABLES['life_expectancy_at_retirement'] para fallback.")
    values = tab.get("values", {})
    if str(age_ret) not in values:
        raise KeyError(f"No hay life_expectancy_at_retirement para edad {age_ret}.")
    return float(values[str(age_ret)])


def _annuity_factor_monthly(age_ret: int) -> float:
    """
    Intenta obtener factor actuarial tipo ä_x (mensual) del JSON.
    Si no existe, construye un factor muy simple con esperanza de vida:
        ax ~ 12 * e_x   (sin descuento, pago mensual constante)
    Ajusta el key si tu JSON lo nombra distinto.

    Opción preferida (si existe):
        TABLES["annuity_due_factor"]["values"][str(age_ret)]
    """
    # --- Opción 1: tienes factor actuarial directo
    ann = TABLES.get("annuity_due_factor")  # <<< AJUSTA nombre si difiere
    if ann is not None:
        values = ann.get("values", ann)
        if isinstance(values, dict) and str(age_ret) in values:
            return float(values[str(age_ret)])

    # --- Fallback: usa esperanza de vida
    e = _life_expectancy_years_at_retirement(age_ret)
    return float(12.0 * e)


def _primas_ss_factor() -> float:
    """
    Primas_SS como 'factor' (se resta del denominador ä_x - primas).
    Si no lo tienes, 0.
    Ajusta llave si tu JSON lo llama distinto.
    """
    return float(ASS.get("primas_ss_factor", 0.0))  # <<< AJUSTA si aplica


def pension_mensual_desde_sci(sci: float, age_ret: int) -> float:
    """
    Fórmula de la diapositiva:
        R = SCI / (ä_x - Primas_SS)
    """
    ax = _annuity_factor_monthly(age_ret)
    primas = _primas_ss_factor()
    denom = ax - primas
    if denom <= 0:
        # último fallback: divide entre meses de esperanza de vida
        e = _life_expectancy_years_at_retirement(age_ret)
        denom = max(12.0 * e, 1.0)
    return float(sci / denom)


# =============================================================================
# Pensión garantizada (opcional si existe tabla)
# =============================================================================

def pension_garantizada_mensual(age_ret: int, weeks_at_ret: int, sbc_m: float) -> float:
    """
    Si tienes una tabla de PG, impleméntala aquí.
    Para no romper nada: si no existe, devuelve 0.

    Estructura esperada (ejemplo, AJUSTA):
      TABLES["pension_garantizada"]["values"][str(age)][str(weeks_group)][str(sbc_tramo)] = monto
    y además:
      TABLES["pg_sbc_brackets"]["brackets"] = [...]
      TABLES["weeks_groups"] = [{"id":..,"lower":..,"upper":..}, ...]
    """
    pg = TABLES.get("pension_garantizada")
    if pg is None:
        return 0.0

    # brackets SBC para PG (AJUSTA nombres)
    sbc_br = TABLES.get("pg_sbc_brackets")
    weeks_groups = TABLES.get("weeks_groups")
    if sbc_br is None or weeks_groups is None:
        return 0.0

    sbc_id = tramo_por_brackets(sbc_m, sbc_br["brackets"])

    # weeks group
    wg_id = None
    for g in weeks_groups:
        lo = int(g["lower"])
        hi = g["upper"]
        if hi is None and weeks_at_ret >= lo:
            wg_id = int(g["id"])
            break
        if hi is not None and lo <= weeks_at_ret <= int(hi):
            wg_id = int(g["id"])
            break

    if wg_id is None:
        wg_id = int(weeks_groups[0]["id"])

    # lookup
    try:
        return float(pg["values"][str(age_ret)][str(wg_id)][str(sbc_id)])
    except Exception:
        return 0.0


# =============================================================================
# FUNCIÓN PRINCIPAL (NO rompe tu interfaz)
# =============================================================================

def replacement_rate_lss1997(
    age_now: int,
    salary_monthly: float,
    voluntary_rate: float,
    assumptions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Core LSS 1997 (compat con tu UI actual):

    Inputs (UI actual):
      - age_now
      - salary_monthly
      - voluntary_rate

    Internos (por ahora por default desde JSON):
      - edad retiro: ASS["default_retirement_age"] o 65
      - semanas actuales: ASS["default_weeks_now"] o 0
      - rendimiento anual: ASS["default_annual_return"] o ASS["tasa_retorno_anual"] o 0.05

    Devuelve:
      - replacement_rate
      - pension_monthly
      - sci
      - auxiliares para debug
    """
    # Compat: puedes pasar un dict assumptions para override sin tocar UI
    local_ASS = ASS.copy()
    if assumptions:
        local_ASS.update(assumptions)

    exp_ret_age = int(local_ASS.get("default_retirement_age", 65))
    weeks_now = int(local_ASS.get("default_weeks_now", 0))
    annual_return = float(
        local_ASS.get("default_annual_return", local_ASS.get("tasa_retorno_anual", 0.05))
    )

    sbc_m = salario_de_cotizacion(float(salary_monthly))
    weeks_at_ret = weeks_now + (exp_ret_age - int(age_now)) * 52
    ok = factibilidad_de_retiro(int(age_now), exp_ret_age, weeks_now)

    sci = monto_acumulado_al_retiro(
        age_now=int(age_now),
        exp_retirement_age=exp_ret_age,
        salary_monthly=float(salary_monthly),
        voluntary_rate=float(voluntary_rate),
        tasa_retorno_anual=annual_return,
    )

    pension_R = pension_mensual_desde_sci(sci=float(sci), age_ret=exp_ret_age)

    pg = pension_garantizada_mensual(
        age_ret=exp_ret_age,
        weeks_at_ret=int(weeks_at_ret),
        sbc_m=float(sbc_m),
    ) if ok else 0.0

    pension = float(max(pension_R, pg)) if ok else 0.0

    denom = float(salary_monthly) if float(salary_monthly) > 0 else 1.0
    rr = float(pension / denom)

    return {
        "replacement_rate": rr,
        "pension_monthly": pension,
        "sci": float(sci),
        "pension_actuarial_R": float(pension_R),
        "pension_garantizada": float(pg),
        # auxiliares útiles
        "age_now": int(age_now),
        "exp_retirement_age": int(exp_ret_age),
        "salary_monthly": float(salary_monthly),
        "sbc_monthly": float(sbc_m),
        "voluntary_rate": float(voluntary_rate),
        "annual_return": float(annual_return),
        "weeks_now": int(weeks_now),
        "weeks_at_ret": int(weeks_at_ret),
        "ok_eligibility": bool(ok),
    }


# =============================================================================
# Solver (NO rompe tu interfaz)
# =============================================================================

def solve_voluntary_rate_for_target(
    age_now: int,
    salary_monthly: float,
    target_rr: float,
    lo: float = 0.0,
    hi: float = 0.30,
    tol: float = 1e-4,
    max_iter: int = 60,
) -> Dict[str, Any]:
    """Búsqueda binaria sobre voluntary_rate (misma firma que ya usas en UI)."""
    if target_rr <= 0:
        return {"voluntary_rate": 0.0, "achieved_rr": 0.0, "iters": 0}

    lo = float(lo)
    hi = float(hi)

    for it in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        rr_mid = replacement_rate_lss1997(int(age_now), float(salary_monthly), float(mid))["replacement_rate"]

        if abs(rr_mid - float(target_rr)) <= float(tol):
            return {"voluntary_rate": mid, "achieved_rr": rr_mid, "iters": it + 1}

        if rr_mid < float(target_rr):
            lo = mid
        else:
            hi = mid

    mid = 0.5 * (lo + hi)
    rr_final = replacement_rate_lss1997(int(age_now), float(salary_monthly), float(mid))["replacement_rate"]
    return {"voluntary_rate": mid, "achieved_rr": rr_final, "iters": int(max_iter)}


def rr_curve(age_now: int, salary_monthly: float, voluntary_rates: np.ndarray) -> pd.DataFrame:
    rows = []
    for v in voluntary_rates:
        out = replacement_rate_lss1997(int(age_now), float(salary_monthly), float(v))
        rows.append({"voluntary_rate": float(v), "replacement_rate": out["replacement_rate"]})
    return pd.DataFrame(rows)