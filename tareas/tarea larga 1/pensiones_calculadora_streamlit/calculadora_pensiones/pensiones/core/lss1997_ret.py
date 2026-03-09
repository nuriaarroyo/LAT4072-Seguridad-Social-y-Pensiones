from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
from bisect import bisect_left

import numpy as np
import pandas as pd

from pensiones.utils.io import load_json
from pensiones.core.pension_garantizada import pension_garantizada_desde_tabla

# =============================================================================
# Carga de supuestos
# =============================================================================

DATA_PATH = Path(__file__).resolve().parents[1] / "data"
P = load_json(DATA_PATH / "lss1997_assumptions.json")

ASS: Dict[str, Any] = P["assumptions"]
UNITS: Dict[str, Any] = P.get("units", {})
ELIG: Dict[str, Any] = P.get("eligibility", {})
RATES: Dict[str, Any] = P.get("contribution_rates_base", {})

TABLES: Dict[str, Any] = P.get("tables", {}).copy()
TABLES["pg_weeks_thresholds_by_year"] = P["pg_weeks_thresholds_by_year"]
TABLES["pension_garantizada"] = P["pension_garantizada"]

# =============================================================================
# Helpers básicos
# =============================================================================

def uma_m() -> float:
    return float(UNITS["uma_monthly"])


def salario_maximo_cotizable() -> float:
    """SBC mensual topado a 25 UMA."""
    return float(25.0 * uma_m())


def salario_de_cotizacion(salary_monthly: float) -> float:
    """SBC mensual topado."""
    return float(min(float(salary_monthly), salario_maximo_cotizable()))


def sbc_entre_uma(salary_monthly: float) -> float:
    """SBC mensual expresado en UMA."""
    return float(salario_de_cotizacion(float(salary_monthly)) / uma_m())


def indicador_de_cotizacion(sbc_mensual: float) -> int:
    """
    Devuelve el id del tramo CEAV según tabla transitoria.
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


# =============================================================================
# Año y elegibilidad
# =============================================================================

def pg_year_from_inputs(year_now: int, age_now: int, age_ret: int) -> int:
    """
    Año efectivo para tabla de PG.
    La tabla transitoria se usa hasta 2030; después queda congelada en 2030.
    """
    year_ret = int(year_now) + (int(age_ret) - int(age_now))
    return max(2021, min(year_ret, 2030))


def min_weeks_required_by_year(year_ret_real: int) -> int:
    """
    Requisito legal de semanas por año real de retiro.
    """
    if year_ret_real <= 2020:
        return 1250
    if year_ret_real == 2021:
        return 750
    if year_ret_real == 2022:
        return 775
    if year_ret_real == 2023:
        return 800
    if year_ret_real == 2024:
        return 825
    if year_ret_real == 2025:
        return 850
    if year_ret_real == 2026:
        return 875
    if year_ret_real == 2027:
        return 900
    if year_ret_real == 2028:
        return 925
    if year_ret_real == 2029:
        return 950
    if year_ret_real == 2030:
        return 975
    return 1000


def factibilidad_de_retiro(
    age_now: int,
    exp_retirement_age: int,
    weeks_now: int,
    year_now: int,
) -> bool:
    """
    Verifica semanas mínimas requeridas según el año real de retiro.
    """
    weeks_at_ret = int(weeks_now) + (int(exp_retirement_age) - int(age_now)) * 52
    year_ret_real = int(year_now) + (int(exp_retirement_age) - int(age_now))
    min_weeks = min_weeks_required_by_year(year_ret_real)
    return bool(weeks_at_ret >= min_weeks)


# =============================================================================
# Aportaciones mensuales
# =============================================================================

def aportaciones_totales_mensuales(aport_obl: float, aport_vol: float) -> float:
    return float(aport_obl + aport_vol)


def tasa_obligatoria_total(year_now: int, sbc_mensual: float) -> float:
    """
    Tasa obligatoria total sobre SBC:
      trabajador + retiro patronal fijo + CEAV patronal transitorio + gobierno

    Supuesto de mapeo con tu JSON:
      - worker                  -> aportación trabajador
      - employer_ceav_fixed     -> retiro patronal fijo (2%)
      - employer_retirement     -> NO se usa aquí porque en tu JSON trae 0.07513
                                   que no debe sumarse fijo junto con la tabla transitoria
      - government              -> aporte gobierno (si aplica)
    """
    worker = float(RATES.get("worker", 0.0))
    retiro_patron_fijo = float(RATES.get("employer_ceav_fixed", 0.0))
    government = float(RATES.get("government", 0.0))

    tramo_id = indicador_de_cotizacion(float(sbc_mensual))
    year_key = str(int(min(max(year_now, 2021), 2030)))

    ceav_rates = TABLES["ceav_employer_transitory"]["rates_by_year"][year_key]
    ceav_patron = float(ceav_rates[tramo_id - 1])

    return float(worker + retiro_patron_fijo + ceav_patron + government)


def aportacion_obligatoria(sbc_mensual: float, year_now: int) -> float:
    return float(sbc_mensual * tasa_obligatoria_total(int(year_now), float(sbc_mensual)))


def aportacion_voluntaria(sbc_mensual: float, voluntary_rate: float) -> float:
    return float(sbc_mensual * float(voluntary_rate))


# =============================================================================
# Proyección SCI
# =============================================================================

def saldo_inicial_aprox_desde_semanas(
    weeks_now: int,
    salary_monthly: float,
    annual_return: float,
    year_now: int,
) -> float:
    """
    Aproximación simple del saldo inicial:
    - convierte semanas a meses pasados
    - asume SBC constante
    - aporta tasa obligatoria constante del año actual
    """
    if int(weeks_now) <= 0:
        return 0.0

    months_past = int(round(float(weeks_now) / 4.3333333333))
    months_past = max(months_past, 0)

    sbc_m = salario_de_cotizacion(float(salary_monthly))
    c_obl = aportacion_obligatoria(sbc_m, int(year_now))
    

    sci0 = 0.0
    for _ in range(months_past):
        sci0 = (sci0 + c_obl) 

    return float(sci0)


def monto_acumulado_al_retiro(
    age_now: int,
    exp_retirement_age: int,
    salary_monthly: float,
    voluntary_rate: float,
    tasa_retorno_anual: float,
    year_now: int,
    saldo_inicial: float = 0.0,
) -> float:
    """
    Proyección mensual simple de SCI.
    Para no rehacer todo el backbone, se usa la tasa obligatoria del año actual
    como aproximación estable.
    """
    T = max((int(exp_retirement_age) - int(age_now)) * 12, 0)
    if T == 0:
        return float(saldo_inicial)

    sbc_m = salario_de_cotizacion(float(salary_monthly))

    c_obl = aportacion_obligatoria(sbc_m, int(year_now))
    c_vol = aportacion_voluntaria(sbc_m, float(voluntary_rate))
    contrib_m = aportaciones_totales_mensuales(c_obl, c_vol)

    

    sci = float(saldo_inicial)
    for _ in range(T):
        sci = (sci + contrib_m) 

    return float(sci)


def sci0_from_inputs_simple(
    saldo_actual: Optional[float],
    weeks_now: Optional[int],
    salary_monthly: float,
    annual_return: float,
    year_now: int,
) -> float:
    """
    Regla simple:
    - si hay saldo actual > 0, usarlo
    - si no, estimarlo desde semanas
    - si no, 0
    """
    if saldo_actual is not None and float(saldo_actual) > 0:
        return float(saldo_actual)

    if weeks_now is not None and int(weeks_now) > 0:
        return saldo_inicial_aprox_desde_semanas(
            weeks_now=int(weeks_now),
            salary_monthly=float(salary_monthly),
            annual_return=float(annual_return),
            year_now=int(year_now),
        )

    return 0.0


# =============================================================================
# Conversión SCI -> pensión mensual
# =============================================================================

def _sex_key(gender: Any) -> str:
    if gender is None:
        return "male"

    if isinstance(gender, (int, float)):
        return "female" if int(gender) == 1 else "male"

    g = str(gender).strip().lower()
    if g in {"1", "f", "mujer", "femenino", "female"}:
        return "female"
    if g in {"0", "h", "m", "hombre", "masculino", "male"}:
        return "male"

    return "male"


def life_exp(age_ret: int, gender: Any) -> float:
    """
    https://www.inegi.org.mx/app/tabulados/interactivos/?pxq=Mortalidad_Mortalidad_09_db78b87b-1e13-46d9-9adf-9c29fe345276
    """
    sex = _sex_key(gender)

    if sex == "male":
        exp = 72.70 - float(age_ret)
    else:        exp = 79.20 - float(age_ret)

    return float(exp)


def pension_mensual_desde_sci(sci: float, age_ret: int, gender: Any) -> float:
    """
    Pensión mensual simple:
      R = SCI / (e_x * 12)
    donde e_x son años restantes aproximados.
    """
    ex = life_exp(int(age_ret), gender)
    if ex <= 0:
        return 0.0
    return float(sci / (ex * 12.0))


# =============================================================================
# Función principal
# =============================================================================

def replacement_rate_lss1997(
    age_now: int,
    salary_monthly: float,
    voluntary_rate: float,
    assumptions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Core simplificado LSS 1997 compatible con tu UI actual.
    """
    local_ASS = ASS.copy()
    if assumptions:
        local_ASS.update(assumptions)

    exp_ret_age = int(
        local_ASS.get(
            "default_retirement_age",
            local_ASS.get("retirement_age_default", 65),
        )
    )
    weeks_now = int(local_ASS.get("default_weeks_now", 0))
    annual_return = float(
        local_ASS.get("default_annual_return", local_ASS.get("tasa_retorno_anual", 0.05))
    )
    gender = local_ASS.get("default_gender", local_ASS.get("gender", "male"))
    year_now = int(local_ASS.get("year_now", 2026))

    sbc_m = salario_de_cotizacion(float(salary_monthly))
    salario_uma = sbc_entre_uma(float(salary_monthly))

    year_ret_real = int(year_now) + (int(exp_ret_age) - int(age_now))
    year_ret_pg = pg_year_from_inputs(int(year_now), int(age_now), int(exp_ret_age))
    weeks_at_ret = int(weeks_now) + (int(exp_ret_age) - int(age_now)) * 52

    ok = factibilidad_de_retiro(
        age_now=int(age_now),
        exp_retirement_age=int(exp_ret_age),
        weeks_now=int(weeks_now),
        year_now=int(year_now),
    )

    saldo_actual = local_ASS.get("saldo_actual", None)
    sci0 = sci0_from_inputs_simple(
        saldo_actual=saldo_actual,
        weeks_now=weeks_now,
        salary_monthly=float(salary_monthly),
        annual_return=float(annual_return),
        year_now=int(year_now),
    )

    sci = monto_acumulado_al_retiro(
        age_now=int(age_now),
        exp_retirement_age=int(exp_ret_age),
        salary_monthly=float(salary_monthly),
        voluntary_rate=float(voluntary_rate),
        tasa_retorno_anual=float(annual_return),
        year_now=int(year_now),
        saldo_inicial=float(sci0),
    )

    pension_R = pension_mensual_desde_sci(
        sci=float(sci),
        age_ret=int(exp_ret_age),
        gender=gender,
    )

    if ok:
        pg = pension_garantizada_desde_tabla(
            year_ret=int(year_ret_pg),
            age_ret=int(exp_ret_age),
            weeks_at_ret=int(weeks_at_ret),
            salario_uma=float(salario_uma),
            tables=TABLES,
        )
    else:
        pg = 0.0

    pension = float(max(pension_R, pg)) if ok else 0.0
    rr = float(pension / float(salary_monthly)) if float(salary_monthly) > 0 else 0.0

    return {
        "replacement_rate": float(rr),
        "pension_monthly": float(pension),
        "sci": float(sci),
        "pension_actuarial_R": float(pension_R),
        "pension_garantizada": float(pg),
        "age_now": int(age_now),
        "exp_retirement_age": int(exp_ret_age),
        "year_now": int(year_now),
        "year_ret_real": int(year_ret_real),
        "year_ret_pg": int(year_ret_pg),
        "salary_monthly": float(salary_monthly),
        "sbc_monthly": float(sbc_m),
        "salario_uma": float(salario_uma),
        "voluntary_rate": float(voluntary_rate),
        "annual_return": float(annual_return),
        "weeks_now": int(weeks_now),
        "weeks_at_ret": int(weeks_at_ret),
        "ok_eligibility": bool(ok),
        "gender_used": _sex_key(gender),
        "tasa_obligatoria_total": float(tasa_obligatoria_total(int(year_now), float(sbc_m))),
        "aportacion_obligatoria_mensual": float(aportacion_obligatoria(float(sbc_m), int(year_now))),
        "aportacion_voluntaria_mensual": float(aportacion_voluntaria(float(sbc_m), float(voluntary_rate))),
    }


# =============================================================================
# Solver
# =============================================================================

def solve_voluntary_rate_for_target(
    age_now: int,
    salary_monthly: float,
    target_rr: float,
    lo: float = 0.0,
    hi: float = 0.30,
    tol: float = 1e-4,
    max_iter: int = 60,
    assumptions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Busca la tasa voluntaria necesaria para alcanzar una RR objetivo.
    """
    target_rr = float(target_rr)
    lo = float(lo)
    hi = float(hi)

    if target_rr <= 0:
        out0 = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            0.0,
            assumptions=assumptions,
        )
        return {
            "voluntary_rate": 0.0,
            "achieved_rr": float(out0["replacement_rate"]),
            "iters": 0,
            "status": "target_nonpositive",
        }

    rr_lo = replacement_rate_lss1997(
        int(age_now),
        float(salary_monthly),
        lo,
        assumptions=assumptions,
    )["replacement_rate"]

    if rr_lo >= target_rr:
        return {
            "voluntary_rate": float(lo),
            "achieved_rr": float(rr_lo),
            "iters": 0,
            "status": "already_reached_at_lo",
        }

    rr_hi = replacement_rate_lss1997(
        int(age_now),
        float(salary_monthly),
        hi,
        assumptions=assumptions,
    )["replacement_rate"]

    if rr_hi < target_rr:
        return {
            "voluntary_rate": float(hi),
            "achieved_rr": float(rr_hi),
            "iters": 0,
            "status": "target_not_reached_with_hi",
        }

    for it in range(int(max_iter)):
        mid = 0.5 * (lo + hi)

        rr_mid = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(mid),
            assumptions=assumptions,
        )["replacement_rate"]

        if abs(rr_mid - target_rr) <= tol:
            return {
                "voluntary_rate": float(mid),
                "achieved_rr": float(rr_mid),
                "iters": it + 1,
                "status": "ok",
            }

        if rr_mid < target_rr:
            lo = mid
        else:
            hi = mid

    mid = 0.5 * (lo + hi)
    rr_final = replacement_rate_lss1997(
        int(age_now),
        float(salary_monthly),
        float(mid),
        assumptions=assumptions,
    )["replacement_rate"]

    return {
        "voluntary_rate": float(mid),
        "achieved_rr": float(rr_final),
        "iters": int(max_iter),
        "status": "max_iter",
    }


# =============================================================================
# Curva RR
# =============================================================================

def rr_curve(
    age_now: int,
    salary_monthly: float,
    voluntary_rates: np.ndarray,
    assumptions: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    rows = []

    for v in voluntary_rates:
        out = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(v),
            assumptions=assumptions,
        )
        rows.append(
            {
                "voluntary_rate": float(v),
                "replacement_rate": float(out["replacement_rate"]),
                "pension_monthly": float(out["pension_monthly"]),
                "pension_garantizada": float(out["pension_garantizada"]),
                "pension_actuarial_R": float(out["pension_actuarial_R"]),
            }
        )

    return pd.DataFrame(rows)