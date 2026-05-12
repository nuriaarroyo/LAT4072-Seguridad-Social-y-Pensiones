from pathlib import Path
import sys

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.selfies_calculator import (
    SelfiesAssumptions,
    calculate_age_table,
    load_curve,
    load_latest_udi,
)

curve = load_curve(BASE / "datos" / "curva_real_udis.csv")
valor_udi = load_latest_udi(BASE / "datos" / "valor_udi.csv")

assumptions = SelfiesAssumptions(
    edad_min=16,
    edad_max=55,
    edad_retiro=65,
    pension_anual_udis=72_000,
    cupon_anual_por_bono_udis=5,
    anios_pago=20,
    crecimiento_real_estandar_vida=0.0,
    payment_timing="at_retirement",
    compounding="annual",
    valor_udi_mxn=valor_udi,
)

out = calculate_age_table(assumptions, curve)
output_path = BASE / "outputs" / "resultados_selfies_udis.csv"
out.to_csv(output_path, index=False)
print(f"Resultados guardados en: {output_path}")
print(out.head())
