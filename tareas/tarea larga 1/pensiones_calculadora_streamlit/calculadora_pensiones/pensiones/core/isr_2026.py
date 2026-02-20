from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from pensiones.utils.io import load_json

@dataclass(frozen=True)
class ISRTariffBracket:
    lower: float
    upper: Optional[float]  # None = sin límite superior
    fixed_quota: float
    rate: float  # tasa marginal (p.ej. 0.1792)

def load_isr_2026_tariff() -> List[ISRTariffBracket]:
    data = load_json("isr_2026_tarifa.json")
    brackets = []
    for b in data.get("brackets", []):
        brackets.append(ISRTariffBracket(
            lower=float(b["lower"]),
            upper=None if b["upper"] is None else float(b["upper"]),
            fixed_quota=float(b["fixed_quota"]),
            rate=float(b["rate"]),
        ))
    if not brackets:
        raise ValueError("La tarifa ISR está vacía. Rellena pensiones/data/isr_2026_tarifa.json")
    return brackets

def isr_monthly(gross_monthly_income: float, brackets: Optional[List[ISRTariffBracket]] = None) -> Dict[str, Any]:
    """Calcula ISR mensual usando tarifa por rangos.

    Devuelve un dict con:
    - isr
    - bracket (rango usado)
    - marginal_excess, fixed_quota, rate
    """
    if gross_monthly_income < 0:
        raise ValueError("El ingreso mensual no puede ser negativo.")

    if brackets is None:
        brackets = load_isr_2026_tariff()

    income = float(gross_monthly_income)

    chosen = None
    for b in brackets:
        if income >= b.lower and (b.upper is None or income <= b.upper):
            chosen = b
            break
    if chosen is None:
        # si no cayó en ninguno, usamos el último por seguridad
        chosen = brackets[-1]

    excess = max(0.0, income - chosen.lower)
    tax = chosen.fixed_quota + excess * chosen.rate

    return {
        "isr": tax,
        "lower": chosen.lower,
        "upper": chosen.upper,
        "fixed_quota": chosen.fixed_quota,
        "rate": chosen.rate,
        "excess": excess,
    }
