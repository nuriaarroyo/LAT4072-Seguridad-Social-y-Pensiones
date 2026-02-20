from __future__ import annotations

from typing import Dict, Any, Tuple, Callable, Optional
import numpy as np
import pandas as pd

from pensiones.utils.io import load_json

def replacement_rate_lss1997(
    age_now: int,
    salary_monthly: float,
    voluntary_rate: float,
    assumptions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Plantilla: tasa de reemplazo LSS 1997 (CESANTÍA/VEJEZ).

    Aquí debes implementar lo que viene en el Excel visto en clase.
    Esta función devuelve un dict con tasa de reemplazo, pensión estimada, y auxiliares.
    """
    if assumptions is None:
        assumptions = load_json("lss1997_assumptions.json").get("params", {})

    # TODO: reemplazar por tu modelo del Excel
    # Placeholder razonable: tasa de reemplazo crece con contribución voluntaria (solo para demo UI)
    base = 0.35
    rr = base + 1.5 * voluntary_rate
    rr = float(np.clip(rr, 0.0, 1.2))
    pension = rr * salary_monthly

    return {
        "replacement_rate": rr,
        "pension_monthly": pension,
        "age_now": age_now,
        "salary_monthly": salary_monthly,
        "voluntary_rate": voluntary_rate
    }

def solve_voluntary_rate_for_target(
    age_now: int,
    salary_monthly: float,
    target_rr: float,
    lo: float = 0.0,
    hi: float = 0.30,
    tol: float = 1e-4,
    max_iter: int = 60
) -> Dict[str, Any]:
    """Encuentra la tasa de ahorro voluntario (adicional) para alcanzar una RR objetivo.

    Implementa búsqueda binaria sobre voluntary_rate.
    """
    if target_rr <= 0:
        return {"voluntary_rate": 0.0, "achieved_rr": 0.0, "iters": 0}

    for i in range(max_iter):
        mid = 0.5 * (lo + hi)
        rr_mid = replacement_rate_lss1997(age_now, salary_monthly, mid)["replacement_rate"]
        if abs(rr_mid - target_rr) <= tol:
            return {"voluntary_rate": mid, "achieved_rr": rr_mid, "iters": i + 1}
        if rr_mid < target_rr:
            lo = mid
        else:
            hi = mid

    rr_final = replacement_rate_lss1997(age_now, salary_monthly, 0.5*(lo+hi))["replacement_rate"]
    return {"voluntary_rate": 0.5*(lo+hi), "achieved_rr": rr_final, "iters": max_iter}

def rr_curve(
    age_now: int,
    salary_monthly: float,
    voluntary_rates: np.ndarray
) -> pd.DataFrame:
    rows = []
    for v in voluntary_rates:
        out = replacement_rate_lss1997(age_now, salary_monthly, float(v))
        rows.append({"voluntary_rate": float(v), "replacement_rate": out["replacement_rate"]})
    return pd.DataFrame(rows)
