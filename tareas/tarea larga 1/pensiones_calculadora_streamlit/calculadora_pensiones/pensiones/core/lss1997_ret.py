from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
from bisect import bisect_left

import numpy as np
import pandas as pd

from pensiones.utils.io import load_json
from pensiones.core.pension_garantizada import pension_garantizada_mensual

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

def uma_m() -> float:
    return float(UNITS["uma_monthly"])


def salario_maximo_cotizable() -> float:
    """Salario máximo cotizable mensual = 25 UMA (asumiendo tope 25)."""
    return float(25.0 * UNITS["uma_monthly"])


def salario_de_cotizacion(salary_monthly: float) -> float:
    """SBC mensual topado."""
    return float(min(salary_monthly, salario_maximo_cotizable()))


def sbc_entre_uma(salary_monthly: float) -> float:
    """SBC en UMAs."""
    return float(salary_monthly / UNITS["uma_monthly"])


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
       RATES["worker"]
       + RATES["employer_retirement"]
       + RATES["employer_ceav_fixed"]
       + RATES["government"]
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
# Conversión SCI -> pensión mensual (actuarial desde tabla qx por género)
# =============================================================================

def _sex_key(gender: Any) -> str:
    """
    Normaliza género a 'male' o 'female'.
    Soporta:
      - 0/1 (0=hombre, 1=mujer)
      - 'H','M','Hombre','Masculino','male'
      - 'F','Mujer','Femenino','female'
    """
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


def _qx(age: int, gender: Any) -> float:
    """
    qx anual desde JSON:
      TABLES["mortality_qx_2023"]["male"][str(edad)]
      TABLES["mortality_qx_2023"]["female"][str(edad)]
    """
    tab = TABLES.get("mortality_qx_2023")
    if tab is None:
        raise KeyError("Falta TABLES['mortality_qx_2023'] en el JSON (tabla qx por edad y género).")

    sex = _sex_key(gender)
    values = tab.get(sex)
    if not isinstance(values, dict):
        raise KeyError(f"TABLES['mortality_qx_2023']['{sex}'] no existe o no es dict.")

    k = str(int(age))
    if k not in values:
        raise KeyError(f"No hay qx para edad {age} en mortality_qx_2023['{sex}'].")

    q = float(values[k])
    # clamp por seguridad
    return float(min(max(q, 0.0), 1.0))


def _annuity_factor_monthly(exp_ret_age: int, gender: Any) -> float:
    """
    Factor actuarial mensual tipo ä̈_x^(12) (renta MENSUAL ANTICIPADA),
    calculado desde:
      - qx anual por edad y género (mortalidad_qx_2023)
      - tasa técnica anual i = ASS["tasa_tecnica"]

    === ECUACIÓN PRESENTACIÓN ===
      ä̈_x^(12) = sum_{k>=0} v_m^k * {}_k p_x,
      con v_m = (1+i)^(-1/12)

    Implementación:
      - Aproxima supervivencia mensual en edad a:
          p_m(age) = (1 - qx(age))^(1/12)
      - Recorre meses hasta omega=110 (tu tabla llega a 110).
    """
    i = float(ASS["tasa_tecnica"])
    v_m = (1.0 + i) ** (-1.0 / 12.0)

    x = int(exp_ret_age)
    omega = 110

    # si ya estás en omega, solo pago inmediato (ant.)
    if x >= omega:
        return 1.0

    pv = 0.0
    p_surv = 1.0  # {}_0 p_x

    # k=0 (pago anticipado inmediato)
    pv += 1.0

    months = (omega - x) * 12

    for k in range(1, months + 1):
        age_k = x + (k - 1) // 12  # edad vigente en ese mes (aprox)
        q = _qx(age_k, gender)
        p_year = 1.0 - q
        p_m = p_year ** (1.0 / 12.0)

        p_surv *= p_m
        pv += (v_m ** k) * p_surv

    return float(pv)


def pension_mensual_desde_sci(sci: float, age_ret: int, gender: Any) -> float:
    """
    === ECUACIÓN PRESENTACIÓN ===
      R = SCI / ä̈_x^(12)    (SIN primas)

    (tú pediste explícitamente ya no usar primas)
    """
    ax = _annuity_factor_monthly(int(age_ret), gender)
    if ax <= 0:
        return 0.0
    return float(sci / ax)


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
    Core LSS 1997 (compat con tu UI actual)

    Inputs (UI actual):
      - age_now
      - salary_monthly
      - voluntary_rate

    Internos (por default desde JSON):
      - edad retiro: ASS["default_retirement_age"] o 65
      - semanas actuales: ASS["default_weeks_now"] o 0
      - rendimiento anual: ASS["default_annual_return"] o ASS["tasa_retorno_anual"] o 0.05
      - género: ASS["default_gender"] o ASS["gender"] o "male"

    === DONDE CAE CADA ECUACIÓN DE LA PRESENTACIÓN ===
    (1) SCI al retiro: monto_acumulado_al_retiro()
        SCI_{t+1} = (SCI_t + C) * (1 + j_m)

    (2) Renta vitalicia mensual (actuarial):
        R = SCI / ä̈_x^(12)
        -> pension_mensual_desde_sci()

    (3) Factor actuarial mensual:
        ä̈_x^(12) = sum v_m^k * {}_k p_x
        -> _annuity_factor_monthly()

    (4) Pensión final con PG:
        pension = max(R, PG)
    """
    local_ASS = ASS.copy()
    if assumptions:
        local_ASS.update(assumptions)

    exp_ret_age = int(local_ASS.get("default_retirement_age", 65))
    weeks_now = int(local_ASS.get("default_weeks_now", 0))
    annual_return = float(local_ASS.get("default_annual_return", local_ASS.get("tasa_retorno_anual", 0.05)))

    # género sin romper UI: lo tomas de assumptions/default
    gender = local_ASS.get("default_gender", local_ASS.get("gender", "male"))

    sbc_m = salario_de_cotizacion(float(salary_monthly))
    weeks_at_ret = weeks_now + (exp_ret_age - int(age_now)) * 52
    ok = factibilidad_de_retiro(int(age_now), exp_ret_age, weeks_now)

    # (1) SCI al retiro
    sci = monto_acumulado_al_retiro(
        age_now=int(age_now),
        exp_retirement_age=exp_ret_age,
        salary_monthly=float(salary_monthly),
        voluntary_rate=float(voluntary_rate),
        tasa_retorno_anual=annual_return,
    )

    # (2)-(3) Pensión actuarial desde SCI y ä̈_x^(12)
    pension_R = pension_mensual_desde_sci(sci=float(sci), age_ret=exp_ret_age, gender=gender)

    # (4) PG si aplica
    pg = pension_garantizada_mensual(
    age_ret=exp_ret_age,
    weeks_at_ret=int(weeks_at_ret),
    sbc_m=float(sbc_m),
    assumptions=assumptions,   # <-- ESTA LÍNEA 
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
        "gender_used": _sex_key(gender),
        "annuity_factor_monthly": float(_annuity_factor_monthly(exp_ret_age, gender)),
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
    assumptions: Optional[Dict[str, Any]] = None,   # <-- NUEVO
) -> Dict[str, Any]:
    """Búsqueda binaria sobre voluntary_rate (consistente con assumptions)."""
    if target_rr <= 0:
        return {"voluntary_rate": 0.0, "achieved_rr": 0.0, "iters": 0}

    lo = float(lo)
    hi = float(hi)

    for it in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        rr_mid = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(mid),
            assumptions=assumptions,              # <-- PASA assumptions
        )["replacement_rate"]

        if abs(rr_mid - float(target_rr)) <= float(tol):
            return {"voluntary_rate": mid, "achieved_rr": rr_mid, "iters": it + 1}

        if rr_mid < float(target_rr):
            lo = mid
        else:
            hi = mid

    mid = 0.5 * (lo + hi)
    rr_final = replacement_rate_lss1997(
        int(age_now),
        float(salary_monthly),
        float(mid),
        assumptions=assumptions,                  # <-- PASA assumptions
    )["replacement_rate"]

    return {"voluntary_rate": mid, "achieved_rr": rr_final, "iters": int(max_iter)}


def rr_curve(
    age_now: int,
    salary_monthly: float,
    voluntary_rates: np.ndarray,
    assumptions: Optional[Dict[str, Any]] = None,   # <-- NUEVO
) -> pd.DataFrame:
    rows = []
    for v in voluntary_rates:
        out = replacement_rate_lss1997(
            int(age_now),
            float(salary_monthly),
            float(v),
            assumptions=assumptions,               # <-- PASA assumptions
        )
        rows.append({"voluntary_rate": float(v), "replacement_rate": out["replacement_rate"]})
    return pd.DataFrame(rows)