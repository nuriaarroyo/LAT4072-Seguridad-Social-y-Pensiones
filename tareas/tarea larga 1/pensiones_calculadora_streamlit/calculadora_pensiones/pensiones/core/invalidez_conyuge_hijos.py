"""
invalidez_conyuge_hijos.py
==========================
Motor actuarial — Monto Constitutivo del Seguro de Invalidez
Inválido con cónyuge e hijos (mínimo cuatro) — LSS/IMSS

Anexo 18.5.1 CUS · Secciones 4 y 5
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

# ── Constantes globales ────────────────────────────────────────────────────────
TASA_INTERES:          float = 0.035
FACBI:                 float = 1.0
RECARGO_INVALIDEZ:     float = 1.09
RECARGO_SOBREVIVENCIA: float = 1.09

PCT_CUANTIA_BASICA: float = 0.35
PCT_CONYUGE:        float = 0.15
PCT_HIJO:           float = 0.10
PCT_AYUDA_ASIST:    float = 0.16
PCT_VIUDEZ:         float = 0.90
PCT_ORFANDAD:       float = 0.20
MESES_FINIQUITO:    int   = 3

# ── Tablas de mortalidad Makeham (calibración académica EMSSA/EMSSAH/M) ───────
_PARAMS = {
    "INV_H":  dict(A=0.0010, B=0.00005, c=1.115),
    "INV_M":  dict(A=0.0008, B=0.00004, c=1.110),
    "SANO_H": dict(A=0.0005, B=0.000025, c=1.100),
    "SANO_M": dict(A=0.0004, B=0.000018, c=1.095),
}


def _qx(edad: int, tabla: str) -> float:
    p = _PARAMS[tabla]
    mu = p["A"] + p["B"] * (p["c"] ** edad)
    return min(1.0, 1.0 - math.exp(-mu))


def qx_inv(edad: int, sexo: str) -> float:
    return _qx(edad, "INV_H" if sexo in ("H", "T") else "INV_M")


def qx_sano(edad: int, sexo: str) -> float:
    return _qx(edad, "SANO_H" if sexo == "H" else "SANO_M")


# ── Funciones actuariales ──────────────────────────────────────────────────────
def _v(n: int = 1) -> float:
    return (1.0 / (1.0 + TASA_INTERES)) ** n


def ax_invalido(edad: int, sexo: str) -> float:
    """Anualidad vitalicia anticipada — tabla inválidos (EMSSA)."""
    total, surv = 0.0, 1.0
    for k in range(110 - edad):
        total += _v(k) * surv
        surv  *= 1.0 - qx_inv(edad + k, sexo)
    return total


def ax_sano(edad: int, sexo: str) -> float:
    """Anualidad vitalicia anticipada — tabla sanos (EMSSAH/M)."""
    total, surv = 0.0, 1.0
    for k in range(110 - edad):
        total += _v(k) * surv
        surv  *= 1.0 - qx_sano(edad + k, sexo)
    return total


def ax_n_invalido(edad: int, sexo: str, n: int) -> float:
    """Anualidad temporal n años — tabla inválidos."""
    total, surv = 0.0, 1.0
    for k in range(min(n, 110 - edad)):
        total += _v(k) * surv
        surv  *= 1.0 - qx_inv(edad + k, sexo)
    return total


def ax_n_sano(edad: int, sexo: str, n: int) -> float:
    """Anualidad temporal n años — tabla sanos."""
    total, surv = 0.0, 1.0
    for k in range(min(n, 110 - edad)):
        total += _v(k) * surv
        surv  *= 1.0 - qx_sano(edad + k, sexo)
    return total


# ── Dataclass Hijo ─────────────────────────────────────────────────────────────
@dataclass
class Hijo:
    edad:     int
    sexo:     str  = "H"    # "H" hombre | "M" mujer
    estudia:  bool = True   # True → límite 25 años; False → 16 años
    invalido: bool = False  # True → sin límite de edad (Art. 138 LSS)

    @property
    def edad_limite(self) -> int:
        if self.invalido:
            return 110
        return 25 if self.estudia else 16

    @property
    def anios_restantes(self) -> int:
        return max(0, self.edad_limite - self.edad)


# ── Sección 4: Seguro de Invalidez ────────────────────────────────────────────
def _pension_mensual(sal_diario: float, n_hijos: int) -> float:
    """Cuantía mensual del inválido (Art. 141 + 138 LSS)."""
    pct = min(PCT_CUANTIA_BASICA + PCT_CONYUGE + n_hijos * PCT_HIJO + PCT_AYUDA_ASIST, 1.0)
    return sal_diario * 30.0 * pct


def _pbsi(edad_inv: int, sexo_inv: str, pension_m: float) -> float:
    """Prima básica del seguro de invalidez."""
    return pension_m * 12.0 * FACBI * ax_invalido(edad_inv, sexo_inv)


def _psih(edad_inv: int, sexo_inv: str, sal_diario: float, hijos: List[Hijo]) -> float:
    """Prima del seguro de invalidez para hijos."""
    c_basica = PCT_CUANTIA_BASICA * sal_diario * 30.0
    total = 0.0
    for h in hijos:
        n = h.anios_restantes
        if n <= 0:
            continue
        axn_inv  = ax_n_invalido(edad_inv, sexo_inv, n)
        axn_hijo = ax_n_sano(h.edad, h.sexo, n)
        total   += PCT_HIJO * c_basica * 12.0 * FACBI * abs(axn_inv - axn_hijo)
    return total


def _calcular_sec4(edad_inv: int, sexo_inv: str, sal_diario: float, hijos: List[Hijo]) -> dict:
    pm    = _pension_mensual(sal_diario, len(hijos))
    pbsi  = _pbsi(edad_inv, sexo_inv, pm)
    psih  = _psih(edad_inv, sexo_inv, sal_diario, hijos)
    pnsi  = pbsi + psih
    mcsi  = pnsi * RECARGO_INVALIDEZ
    return dict(pension_m=pm, pbsi=pbsi, psih=psih, pnsi=pnsi, mcsi=mcsi,
                ax_inv=ax_invalido(edad_inv, sexo_inv))


# ── Sección 5: Seguro de Sobrevivencia ────────────────────────────────────────
def _pbss(
    edad_inv: int, sexo_inv: str,
    edad_cony: int, sexo_cony: str,
    pension_m: float,
) -> float:
    """Prima básica del seguro de sobrevivencia (viudez)."""
    p_viudez    = PCT_VIUDEZ * (pension_m / (1 + PCT_CONYUGE + PCT_AYUDA_ASIST))
    total, surv = 0.0, 1.0
    for k in range(110 - edad_inv):
        q  = qx_inv(edad_inv + k, sexo_inv)
        ac = ax_sano(min(edad_cony + k, 109), sexo_cony)
        total += _v(k + 1) * surv * q * p_viudez * 12.0 * FACBI * ac
        surv  *= 1.0 - q
    return total


def _psih_ss(edad_inv: int, sexo_inv: str, sal_diario: float, hijos: List[Hijo]) -> float:
    """Prima de orfandad en el seguro de sobrevivencia."""
    c_basica = PCT_CUANTIA_BASICA * sal_diario * 30.0
    total = 0.0
    for h in hijos:
        n = h.anios_restantes
        if n <= 0:
            continue
        contrib, surv = 0.0, 1.0
        for k in range(min(n, 110 - edad_inv)):
            q  = qx_inv(edad_inv + k, sexo_inv)
            ac = ax_n_sano(min(h.edad + k, 109), h.sexo, n - k)
            contrib += _v(k + 1) * surv * q * PCT_ORFANDAD * c_basica * 12.0 * FACBI * ac
            surv    *= 1.0 - q
        total += contrib
    return total


def _pfh(edad_inv: int, sexo_inv: str, sal_diario: float, hijos: List[Hijo]) -> float:
    """Prima del finiquito — 3 mensualidades al extinguirse la orfandad (Art. 136 LSS)."""
    c_basica = PCT_CUANTIA_BASICA * sal_diario * 30.0
    total = 0.0
    for h in hijos:
        n = h.anios_restantes
        if n <= 0:
            continue
        surv_i = surv_h = 1.0
        for k in range(min(n, 110 - edad_inv)):
            surv_i *= 1.0 - qx_inv(edad_inv + k, sexo_inv)
        for k in range(min(n, 110 - h.edad)):
            surv_h *= 1.0 - qx_sano(h.edad + k, h.sexo)
        total += MESES_FINIQUITO * PCT_ORFANDAD * c_basica * _v(n) * surv_i * surv_h * FACBI
    return total


def _calcular_sec5(
    edad_inv: int, sexo_inv: str,
    edad_cony: int, sexo_cony: str,
    sal_diario: float, hijos: List[Hijo],
    pension_m: float,
) -> dict:
    pbss    = _pbss(edad_inv, sexo_inv, edad_cony, sexo_cony, pension_m)
    psih_ss = _psih_ss(edad_inv, sexo_inv, sal_diario, hijos)
    pfh     = _pfh(edad_inv, sexo_inv, sal_diario, hijos)
    pnss    = pbss + psih_ss + pfh
    mcss    = pnss * RECARGO_SOBREVIVENCIA
    return dict(pbss=pbss, psih_ss=psih_ss, pfh=pfh, pnss=pnss, mcss=mcss,
                ax_cony=ax_sano(edad_cony, sexo_cony))


# ── API pública ────────────────────────────────────────────────────────────────
def calcular_monto_constitutivo(
    *,
    edad_invalido:  int,
    sexo_invalido:  str,
    edad_conyuge:   int,
    sexo_conyuge:   str,
    hijos:          List[Hijo],
    salario_diario: float,
) -> dict:
    """
    Calcula el Monto Constitutivo Total (MCT = MCSI + MCSS).

    Parameters
    ----------
    edad_invalido  : edad del asegurado inválido
    sexo_invalido  : "H" hombre | "M" mujer | "T" mujer transgénero
    edad_conyuge   : edad del cónyuge
    sexo_conyuge   : "H" | "M"
    hijos          : lista de Hijo (mínimo 4)
    salario_diario : salario diario promedio de las últimas 500 semanas (MXN)

    Returns
    -------
    dict con todos los componentes del monto constitutivo.
    """
    if len(hijos) < 1:
        raise ValueError("Se requiere al menos 1 hijo.")

    s4 = _calcular_sec4(edad_invalido, sexo_invalido, salario_diario, hijos)
    s5 = _calcular_sec5(
        edad_invalido, sexo_invalido,
        edad_conyuge, sexo_conyuge,
        salario_diario, hijos, s4["pension_m"],
    )
    pct_total = min(
        PCT_CUANTIA_BASICA + PCT_CONYUGE + len(hijos) * PCT_HIJO + PCT_AYUDA_ASIST, 1.0
    )

    return {
        # Entradas
        "edad_invalido":   edad_invalido,
        "sexo_invalido":   sexo_invalido,
        "edad_conyuge":    edad_conyuge,
        "sexo_conyuge":    sexo_conyuge,
        "n_hijos":         len(hijos),
        "salario_diario":  round(salario_diario, 4),
        "salario_mensual": round(salario_diario * 30, 2),
        "pct_total":       round(pct_total, 4),
        # Sección 4
        "pension_mensual": round(s4["pension_m"], 2),
        "pension_anual":   round(s4["pension_m"] * 12, 2),
        "ax_invalido":     round(s4["ax_inv"], 6),
        "pbsi":            round(s4["pbsi"], 2),
        "psih":            round(s4["psih"], 2),
        "pnsi":            round(s4["pnsi"], 2),
        "mcsi":            round(s4["mcsi"], 2),
        # Sección 5
        "ax_conyuge":      round(s5["ax_cony"], 6),
        "pbss":            round(s5["pbss"], 2),
        "psih_ss":         round(s5["psih_ss"], 2),
        "pfh":             round(s5["pfh"], 2),
        "pnss":            round(s5["pnss"], 2),
        "mcss":            round(s5["mcss"], 2),
        # Total
        "mct":             round(s4["mcsi"] + s5["mcss"], 2),
        # Parámetros usados
        "tasa_interes":    TASA_INTERES,
        "recargo_inv":     RECARGO_INVALIDEZ,
        "recargo_sob":     RECARGO_SOBREVIVENCIA,
        "facbi":           FACBI,
    }