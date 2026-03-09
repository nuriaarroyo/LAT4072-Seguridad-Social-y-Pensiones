# pensiones/core/pension_garantizada.py

from __future__ import annotations
from typing import Dict, Any


def _salary_bracket_from_uma(salario_uma: float) -> str:
    """
    Convierte salario expresado en UMA al bracket de la tabla PG.
    """
    if salario_uma < 1.0:
        raise ValueError("El salario en UMA no puede ser menor a 1 para esta tabla.")
    if salario_uma < 2.0:
        return "1"
    if salario_uma < 3.0:
        return "2"
    if salario_uma < 4.0:
        return "3"
    if salario_uma < 5.0:
        return "4"
    return "5"


def _weeks_column_index(year_ret: int, weeks_at_ret: int, tables: Dict[str, Any]) -> int:
    """
    Regresa el índice de columna correcto según año y semanas.
    La última columna es 'o más'.
    """
    year_key = str(year_ret)

    try:
        thresholds = tables["pg_weeks_thresholds_by_year"][year_key]
    except KeyError:
        raise ValueError(f"No existe tabla de semanas para el año {year_ret}.")

    if weeks_at_ret < thresholds[0]:
        raise ValueError(
            f"Semanas insuficientes para PG en {year_ret}. "
            f"Mínimo requerido: {thresholds[0]}."
        )

    for i, cutoff in enumerate(thresholds):
        if weeks_at_ret <= cutoff:
            return i

    return len(thresholds) - 1


def pension_garantizada_desde_tabla(
    *,
    year_ret: int,
    age_ret: int,
    weeks_at_ret: int,
    salario_uma: float,
    tables: Dict[str, Any],
) -> float:
    """
    Busca el monto de pensión garantizada directamente desde la tabla.
    
    Parámetros
    ----------
    year_ret : int
        Año de retiro (2021-2030)
    age_ret : int
        Edad de retiro (60-65)
    weeks_at_ret : int
        Semanas cotizadas al retiro
    salario_uma : float
        Salario expresado en UMA
    tables : dict
        Debe contener:
          - pg_weeks_thresholds_by_year
          - pension_garantizada -> values
    """
    if age_ret not in {60, 61, 62, 63, 64, 65}:
        raise ValueError("La edad debe estar entre 60 y 65.")

    bracket = _salary_bracket_from_uma(salario_uma)
    col_idx = _weeks_column_index(year_ret, weeks_at_ret, tables)

    try:
        monto = tables["pension_garantizada"]["values"][bracket][str(age_ret)][col_idx]
    except KeyError as e:
        raise ValueError(f"No se encontró la combinación en la tabla: {e}")
    except IndexError:
        raise ValueError("Índice de columna fuera de rango en la tabla PG.")

    return float(monto)