"""
Calculadora de bonos de retiro tipo SeLFIES/RSB denominados en UDIS.

La construcción sigue la idea económica de Merton y Muralidhar:
- bono forward-starting: no paga antes del retiro;
- income-only: paga cupones reales, sin principal final;
- indexado en unidad real: aquí se usa UDI como unidad de cuenta real;
- número de bonos = ingreso objetivo anual / cupón anual por bono.

El precio se calcula como valor presente de los cupones reales futuros usando una curva real en UDIS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np
import pandas as pd

Compounding = Literal["annual", "continuous"]
PaymentTiming = Literal["at_retirement", "in_arrears"]


@dataclass(frozen=True)
class SelfiesAssumptions:
    """Supuestos centrales de la valuación."""

    edad_min: int = 16
    edad_max: int = 55
    edad_retiro: int = 65
    pension_anual_udis: float = 72_000.0
    cupon_anual_por_bono_udis: float = 5.0
    anios_pago: int = 20
    crecimiento_real_estandar_vida: float = 0.0
    payment_timing: PaymentTiming = "at_retirement"
    compounding: Compounding = "annual"
    valor_udi_mxn: float | None = None

    def validate(self) -> None:
        if self.edad_min < 0 or self.edad_max < self.edad_min:
            raise ValueError("Las edades deben cumplir 0 <= edad_min <= edad_max.")
        if self.edad_retiro <= self.edad_max:
            raise ValueError("La edad de retiro debe ser mayor que la edad máxima evaluada.")
        if self.pension_anual_udis <= 0:
            raise ValueError("La pensión anual objetivo debe ser positiva.")
        if self.cupon_anual_por_bono_udis <= 0:
            raise ValueError("El cupón anual por bono debe ser positivo.")
        if self.anios_pago <= 0:
            raise ValueError("Los años de pago deben ser positivos.")
        if self.payment_timing not in ("at_retirement", "in_arrears"):
            raise ValueError("payment_timing debe ser 'at_retirement' o 'in_arrears'.")
        if self.compounding not in ("annual", "continuous"):
            raise ValueError("compounding debe ser 'annual' o 'continuous'.")


def load_curve(path_or_file) -> pd.DataFrame:
    """Carga una curva real desde CSV.

    Columnas requeridas:
    - tenor_years: plazo en años.
    - annual_real_rate: tasa real anual en decimal, por ejemplo 0.035 para 3.5%.
    """
    curve = pd.read_csv(path_or_file)
    return validate_curve(curve)


def load_latest_udi(path_or_file) -> float:
    """Carga el ultimo valor de la UDI disponible en un CSV."""
    values = pd.read_csv(path_or_file)
    required = {"fecha", "valor_udi_mxn"}
    missing = required.difference(values.columns)
    if missing:
        raise ValueError(
            "El archivo de UDI debe tener las columnas: fecha, valor_udi_mxn. "
            f"Faltan: {sorted(missing)}"
        )

    out = values.loc[:, ["fecha", "valor_udi_mxn"]].copy()
    out["fecha"] = pd.to_datetime(out["fecha"], errors="coerce")
    out["valor_udi_mxn"] = pd.to_numeric(out["valor_udi_mxn"], errors="coerce")
    out = out.dropna(subset=["valor_udi_mxn"])
    if out.empty:
        raise ValueError("El archivo de UDI no tiene valores numericos validos.")
    if (out["valor_udi_mxn"] <= 0).any():
        raise ValueError("El valor de la UDI debe ser positivo.")
    if out["fecha"].notna().any():
        out = out.sort_values("fecha")
    return float(out.iloc[-1]["valor_udi_mxn"])


def validate_curve(curve: pd.DataFrame) -> pd.DataFrame:
    required = {"tenor_years", "annual_real_rate"}
    missing = required.difference(curve.columns)
    if missing:
        raise ValueError(
            "La curva debe tener las columnas: tenor_years, annual_real_rate. "
            f"Faltan: {sorted(missing)}"
        )
    out = curve.loc[:, ["tenor_years", "annual_real_rate"]].copy()
    out["tenor_years"] = pd.to_numeric(out["tenor_years"], errors="coerce")
    out["annual_real_rate"] = pd.to_numeric(out["annual_real_rate"], errors="coerce")
    out = out.dropna().sort_values("tenor_years")
    out = out.drop_duplicates("tenor_years", keep="last")
    if out.empty:
        raise ValueError("La curva no tiene datos numéricos válidos.")
    if (out["tenor_years"] <= 0).any():
        raise ValueError("Todos los plazos deben ser positivos.")
    if (out["annual_real_rate"] <= -0.99).any():
        raise ValueError("Hay tasas imposibles: deben ser mayores a -99%.")
    return out.reset_index(drop=True)


def interpolate_zero_rate(t: float, curve: pd.DataFrame) -> float:
    """Interpola linealmente la tasa spot real para un plazo t.

    Si t está fuera de la curva, usa extrapolación plana:
    - antes del primer nodo: primera tasa;
    - después del último nodo: última tasa.
    """
    curve = validate_curve(curve)
    tenors = curve["tenor_years"].to_numpy(dtype=float)
    rates = curve["annual_real_rate"].to_numpy(dtype=float)
    return float(np.interp(t, tenors, rates, left=rates[0], right=rates[-1]))


def discount_factor(t: float, rate: float, compounding: Compounding = "annual") -> float:
    if t < 0:
        raise ValueError("El plazo t no puede ser negativo.")
    if compounding == "annual":
        return float((1.0 + rate) ** (-t))
    if compounding == "continuous":
        return float(np.exp(-rate * t))
    raise ValueError("compounding debe ser 'annual' o 'continuous'.")


def payment_times(years_to_retirement: int, payout_years: int, timing: PaymentTiming) -> list[float]:
    """Plazos, desde la valuación, en que paga el bono.

    at_retirement: primer pago al cumplir la edad de retiro.
    in_arrears: primer pago un año después del retiro.
    """
    if timing == "at_retirement":
        start = years_to_retirement
    elif timing == "in_arrears":
        start = years_to_retirement + 1
    else:
        raise ValueError("timing debe ser 'at_retirement' o 'in_arrears'.")
    return [start + j for j in range(payout_years)]


def price_one_selfies(
    edad_actual: int,
    assumptions: SelfiesAssumptions,
    curve: pd.DataFrame,
) -> tuple[float, pd.DataFrame]:
    """Precio en UDIS de un bono tipo SeLFIES para una edad dada.

    Retorna:
    - precio en UDIS;
    - calendario de flujos descontados.
    """
    assumptions.validate()
    curve = validate_curve(curve)
    years_to_retirement = assumptions.edad_retiro - edad_actual
    if years_to_retirement <= 0:
        raise ValueError("La edad actual debe ser menor a la edad de retiro.")

    times = payment_times(
        years_to_retirement=years_to_retirement,
        payout_years=assumptions.anios_pago,
        timing=assumptions.payment_timing,
    )

    rows = []
    for j, t in enumerate(times):
        # El crecimiento real del estándar de vida es opcional.
        # En UDIS puras se usa 0.0. Si se quiere aproximar indexación a consumo real,
        # se puede capturar un g > 0 para que el cupón crezca en términos reales.
        cashflow = assumptions.cupon_anual_por_bono_udis * (
            (1.0 + assumptions.crecimiento_real_estandar_vida) ** j
        )
        r_t = interpolate_zero_rate(t, curve)
        df_t = discount_factor(t, r_t, assumptions.compounding)
        pv_t = cashflow * df_t
        rows.append(
            {
                "payment_number": j + 1,
                "time_years": t,
                "cashflow_udis": cashflow,
                "zero_real_rate": r_t,
                "discount_factor": df_t,
                "pv_udis": pv_t,
            }
        )
    schedule = pd.DataFrame(rows)
    price = float(schedule["pv_udis"].sum())
    return price, schedule


def bonds_needed(assumptions: SelfiesAssumptions) -> float:
    assumptions.validate()
    return assumptions.pension_anual_udis / assumptions.cupon_anual_por_bono_udis


def calculate_age_table(
    assumptions: SelfiesAssumptions,
    curve: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula número de bonos, precio por bono y costo total por edad."""
    assumptions.validate()
    curve = validate_curve(curve)
    n_bonds = bonds_needed(assumptions)
    rows = []
    for edad in range(assumptions.edad_min, assumptions.edad_max + 1):
        price, _ = price_one_selfies(edad, assumptions, curve)
        costo_total_udis = n_bonds * price
        row = {
            "edad": edad,
            "anios_al_retiro": assumptions.edad_retiro - edad,
            "bonos_a_comprar": n_bonds,
            "precio_por_bono_udis": price,
            "costo_total_udis": costo_total_udis,
            "pension_anual_objetivo_udis": assumptions.pension_anual_udis,
            "cupon_anual_por_bono_udis": assumptions.cupon_anual_por_bono_udis,
        }
        if assumptions.valor_udi_mxn is not None:
            row["precio_por_bono_mxn"] = price * assumptions.valor_udi_mxn
            row["costo_total_mxn"] = costo_total_udis * assumptions.valor_udi_mxn
            row["pension_anual_objetivo_mxn"] = (
                assumptions.pension_anual_udis * assumptions.valor_udi_mxn
            )
        rows.append(row)
    return pd.DataFrame(rows)


def calculate_sensitivity_table(
    assumptions: SelfiesAssumptions,
    base_curve: pd.DataFrame,
    shocks_bps: Iterable[int] = (-100, 0, 100),
) -> pd.DataFrame:
    """Sensibilidad por desplazamientos paralelos de la curva real."""
    base_curve = validate_curve(base_curve)
    outputs = []
    for shock in shocks_bps:
        curve = base_curve.copy()
        curve["annual_real_rate"] = curve["annual_real_rate"] + shock / 10_000.0
        table = calculate_age_table(assumptions, curve)
        table["shock_bps"] = shock
        outputs.append(table)
    return pd.concat(outputs, ignore_index=True)
