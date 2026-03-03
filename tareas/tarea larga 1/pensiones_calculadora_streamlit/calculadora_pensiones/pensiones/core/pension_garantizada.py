# pensiones/core/pension_garantizada.py

from __future__ import annotations
from typing import Dict, Any


def pension_garantizada_mensual(
    *,
    age_ret: int,
    weeks_at_ret: int,
    sbc_m: float,
    assumptions: Dict[str, Any] | None = None,
) -> float:
    """
    Calcula la pensión garantizada mensual bajo LSS 1997.

    Esta firma está alineada con lss1997_ret.py:
      - age_ret
      - weeks_at_ret
      - sbc_m

    assumptions puede incluir:
      - pg_mensual (override directo)
      - pg_table (tabla para lookup)
    """

    assumptions = assumptions or {}

    # 1) Override directo (útil para solver)
    if "pg_mensual" in assumptions:
        return float(assumptions["pg_mensual"])

    # 2) Lookup desde tabla si existe
    if "pg_table" in assumptions:
        table = assumptions["pg_table"]

        # Ejemplo de estructura:
        # table[str(age_ret)][str(weeks_at_ret)] = monto
        try:
            return float(table[str(age_ret)][str(weeks_at_ret)])
        except KeyError:
            raise ValueError(
                f"No se encontró PG en pg_table para age_ret={age_ret}, "
                f"weeks_at_ret={weeks_at_ret}."
            )

    # 3) No hay definición
    raise ValueError(
        "No se proporcionó pensión garantizada. "
        "Incluye 'pg_mensual' o 'pg_table' en assumptions."
    )