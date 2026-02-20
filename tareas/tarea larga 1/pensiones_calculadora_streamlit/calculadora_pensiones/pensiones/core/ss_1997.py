from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

import pandas as pd

from pensiones.utils.io import load_json

def _cap_sbc(sbc_daily: float, uma_daily: float, min_uma: float, max_uma: float) -> float:
    # capea SBC entre min y max UMA
    sbc_min = min_uma * uma_daily
    sbc_max = max_uma * uma_daily
    return max(sbc_min, min(sbc_daily, sbc_max))

def ss_contributions_monthly(
    sbc_daily: float,
    days_in_month: int = 30
) -> Dict[str, Any]:
    """Calcula contribuciones mensuales a seguridad social (incluye INFONAVIT)
    desglosadas por seguro / componente y por aportante (patrón, trabajador, gobierno).

    *El detalle de tasas y bases se toma de pensiones/data/ss_1997_rates.json*
    """
    data = load_json("ss_1997_rates.json")
    params = data.get("params", {})
    uma_daily = float(params.get("uma_daily", 0.0))
    if uma_daily <= 0:
        raise ValueError("Config incompleta: setea params.uma_daily en ss_1997_rates.json")

    sbc = _cap_sbc(
        sbc_daily=float(sbc_daily),
        uma_daily=uma_daily,
        min_uma=float(params.get("sbc_min_uma", 1.0)),
        max_uma=float(params.get("sbc_max_uma", 25.0)),
    )

    # bases diarias:
    base_sbc = sbc
    base_uma = uma_daily
    base_excess_3uma = max(0.0, sbc - 3.0 * uma_daily)

    rows = []
    for ins in data.get("insurances", []):
        ins_name = ins.get("name", "Seguro")
        for comp in ins.get("components", []):
            comp_name = comp.get("component", "Componente")
            base_kind = comp.get("base", "SBC")

            if base_kind == "SBC":
                base_daily = base_sbc
            elif base_kind == "UMA":
                base_daily = base_uma
            elif base_kind == "SBC_excess_3UMA":
                base_daily = base_excess_3uma
            else:
                # base custom: tú puedes extender esto
                base_daily = base_sbc

            employer = float(comp.get("employer_rate", 0.0)) * base_daily * days_in_month
            employee = float(comp.get("employee_rate", 0.0)) * base_daily * days_in_month
            gov = float(comp.get("gov_rate", 0.0)) * base_daily * days_in_month

            rows.append({
                "Seguro": ins_name,
                "Componente": comp_name,
                "Base": base_kind,
                "Base_diaria": base_daily,
                "Patron": employer,
                "Trabajador": employee,
                "Gobierno": gov,
                "Total": employer + employee + gov
            })

    df = pd.DataFrame(rows)
    totals = df[["Patron", "Trabajador", "Gobierno", "Total"]].sum().to_dict()
    return {
        "sbc_daily_capped": sbc,
        "uma_daily": uma_daily,
        "days_in_month": days_in_month,
        "detail": df,
        "totals": totals
    }

def effective_rates(
    sbc_monthly: float,
    isr_monthly: float,
    ss_total_monthly: float
) -> Dict[str, float]:
    """Tasas efectivas sobre el SBC mensual (o ingreso mensual, según tu definición)."""
    if sbc_monthly <= 0:
        return {"isr_eff": 0.0, "ss_eff": 0.0}
    return {
        "isr_eff": isr_monthly / sbc_monthly,
        "ss_eff": ss_total_monthly / sbc_monthly
    }
