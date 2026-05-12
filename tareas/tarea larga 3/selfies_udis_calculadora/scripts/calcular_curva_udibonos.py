from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = BASE / "datos" / "curva_original_udibonos.csv"
DEFAULT_OUTPUT = BASE / "datos" / "curva_real_udis.csv"


def _as_numeric(series: pd.Series, column_name: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.isna().any():
        bad_rows = values[values.isna()].index.tolist()
        raise ValueError(f"La columna {column_name} tiene valores no numericos en filas: {bad_rows}")
    return values


def construir_curva_real_udibonos(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """Convierte datos originales de UDIBONOS a la curva que usa la app.

    La app descuenta flujos reales en UDIS con columnas:
    - tenor_years
    - annual_real_rate

    Las tasas de UDIBONOS vienen en porcentaje anual real; aqui se guardan en
    decimal, por ejemplo 4.02% -> 0.0402.
    """
    original = pd.read_csv(input_path)
    required = {"fecha", "plazo", "tenor_years", "precio", "tasa_percent"}
    missing = required.difference(original.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {input_path.name}: {sorted(missing)}")

    curve = original.copy()
    curve["tenor_years"] = _as_numeric(curve["tenor_years"], "tenor_years")
    curve["precio"] = _as_numeric(curve["precio"], "precio")
    curve["tasa_percent"] = _as_numeric(curve["tasa_percent"], "tasa_percent")
    curve["annual_real_rate"] = (curve["tasa_percent"] / 100.0).round(6)

    curve = curve.sort_values("tenor_years").drop_duplicates("tenor_years", keep="last")
    if (curve["tenor_years"] <= 0).any():
        raise ValueError("Todos los plazos deben ser positivos.")
    if (curve["annual_real_rate"] <= -0.99).any():
        raise ValueError("Hay tasas imposibles: deben ser mayores a -99%.")

    return curve.loc[
        :,
        [
            "tenor_years",
            "annual_real_rate",
            "fecha",
            "plazo",
            "precio",
            "tasa_percent",
        ],
    ].reset_index(drop=True)


def guardar_curva_real_udibonos(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    curve = construir_curva_real_udibonos(input_path)
    curve.to_csv(output_path, index=False)
    return curve


if __name__ == "__main__":
    out = guardar_curva_real_udibonos()
    print(f"Curva real en UDIS guardada en: {DEFAULT_OUTPUT}")
    print(out)
