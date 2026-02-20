from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from pensiones.utils.io import load_json

def pension_lss1973(
    age_now: int,
    retirement_age: int,
    salary_monthly: float,
    assumptions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Plantilla: pensión LSS 1973 + tasa de reemplazo.

    Debes implementar con base en el Excel LSS 1973 visto en clase.
    """
    if assumptions is None:
        assumptions = load_json("lss1973_assumptions.json").get("params", {})

    # TODO: reemplazar por tu modelo del Excel
    # Placeholder demo UI: penaliza jubilación temprana
    base_rr_65 = 0.75
    penalty_per_year = 0.06
    rr = base_rr_65 - penalty_per_year * max(0, 65 - retirement_age)
    rr = float(np.clip(rr, 0.0, 1.2))
    pension = rr * salary_monthly

    return {
        "retirement_age": retirement_age,
        "replacement_rate": rr,
        "pension_monthly": pension,
        "age_now": age_now,
        "salary_monthly": salary_monthly,
    }

def rr_by_retirement_age(
    age_now: int,
    salary_monthly: float,
    min_age: int = 60,
    max_age: int = 65
) -> pd.DataFrame:
    rows = []
    for ra in range(min_age, max_age + 1):
        out = pension_lss1973(age_now, ra, salary_monthly)
        rows.append({"retirement_age": ra, "replacement_rate": out["replacement_rate"], "pension_monthly": out["pension_monthly"]})
    return pd.DataFrame(rows)
