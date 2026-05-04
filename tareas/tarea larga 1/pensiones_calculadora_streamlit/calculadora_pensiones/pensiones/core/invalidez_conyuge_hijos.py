"""
invalidez_conyuge_hijos.py — Motor actuarial MC10 (CNSF)
=========================================================
Replica la hoja de cálculo del Laboratorio MC10:

  1.  Historia salarial (sal diario × factor actualización) → Sal Prom Act 500 sem
  2.  CBIV = 35% × Sal_Prom_Diario  →  CBIV_mensual = CBIV_d × 365/12
  3.  PMG  = 1.3 × UMA × 30
  4.  base = max(CBIV_m, PMG)
  5.  b1(j) = base × (1 + 15% + j×10% + %AA)   [cónyuge vivo,  tope 100% sal]
      b2(j) = base × (1       + j×10% + %AA)   [cónyuge muerto, tope 100% sal]
  6.  B_mensual = Σ_k v^k × kpx_inv × [b1(j_k)×kpy_act + b2(j_k)×(1-kpy_act)] × Π kph_act(k)
      usando qx Activos CNSF para hijos y cónyuge, qx Invalidez 2020 para el inválido
  7.  PBSI = (1 + INC) × ä_x^inv × B_mensual
      donde ä_x^inv usa tabla Invalidez Val Act 2020
  8.  PNSI = PBSI × FACBI
  9.  MCSI = (PNSI − PV) × (1+a)/(1−b)

Nota: Las tablas qx exactas del CNSF son de acceso restringido. El módulo usa
      tablas Makeham calibradas al valor ä(49,H)=11.81 del Laboratorio MC10.
      La diferencia en B_mensual (~15%) se debe a las tablas qx de activos.

Valores de referencia MC10:
  ä_inv(49,H) = 11.81    B_mensual ≈ 384,048
  PBSI = 5,035,737    PNSI = 5,045,718    MCSI = 5,197,090
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

# ── Parámetros globales ────────────────────────────────────────────────────────
TASA_INTERES: float = 0.035        # i anual CNSF
UMA_DIARIA:   float = 117.31       # UMA vigente
PMG_FACTOR:   float = 1.3          # PMG = 1.3 × UMA × 30

PCT_CUANTIA_BASICA: float = 0.35
PCT_CONYUGE:        float = 0.15
PCT_HIJO:           float = 0.10
PCT_AYUDA_ASIST:    float = 0.16

INC:       float = 0.11   # recargo asegurador sobre PBSI
RECARGO_A: float = 0.02   # a: gastos de adquisición
RECARGO_B: float = 0.01   # b: gastos de administración
PV:        float = 0.0    # prima única diferida

# ── Tablas de mortalidad Makeham ───────────────────────────────────────────────
# Invalidez Val Act 2020 — calibradas para ä(49,H) = 11.81
_INV_H = dict(A=0.00169243, B=0.0000838155, c=1.1150)
_INV_M = dict(A=0.00132700, B=0.0000660800, c=1.1100)

# Activos CNSF (EMSSAH/M) — estimación Makeham (las tablas exactas son restringidas)
_ACT_H = dict(A=0.000278, B=0.0000226, c=1.1247)
_ACT_M = dict(A=0.000188, B=0.0000136, c=1.1180)


def _qx(edad: int, p: dict) -> float:
    mu = p["A"] + p["B"] * (p["c"] ** min(edad, 109))
    return min(1.0, 1.0 - math.exp(-mu))

def qx_inv(edad: int, sexo: str) -> float:
    return _qx(edad, _INV_H if sexo in ("H", "T") else _INV_M)

def qx_act(edad: int, sexo: str) -> float:
    return _qx(edad, _ACT_H if sexo == "H" else _ACT_M)

def _kpx(edad: int, sexo: str, fn, k: int) -> float:
    s = 1.0
    for t in range(k):
        if edad + t < 110:
            s *= 1.0 - fn(edad + t, sexo)
    return s

def kpx_inv(edad: int, sexo: str, k: int) -> float:
    return _kpx(edad, sexo, qx_inv, k)

def kpx_act(edad: int, sexo: str, k: int) -> float:
    return _kpx(edad, sexo, qx_act, k)


def _v(k: int = 1) -> float:
    return (1.0 / (1.0 + TASA_INTERES)) ** k


# ── Dataclass Hijo ─────────────────────────────────────────────────────────────
@dataclass
class Hijo:
    edad:     int
    sexo:     str  = "H"
    estudia:  bool = True
    invalido: bool = False

    @property
    def edad_limite(self) -> int:
        return 110 if self.invalido else (25 if self.estudia else 16)

    @property
    def anios_restantes(self) -> int:
        return max(0, self.edad_limite - self.edad)


# ── 1. Salario promedio 500 semanas ───────────────────────────────────────────
def salario_promedio_500(
    historia: List[Tuple[float, float]],   # (sal_diario_original, factor_actualizacion)
    sem_por_anio: float = 52.0,
) -> float:
    """
    Promedio del salario diario actualizado de las últimas 500 semanas.
    Los años con salario = 0 NO consumen semanas (no cotizó ese año).
    Ordenar de más reciente a más antiguo.
    """
    acum = suma = 0.0
    for sal, fac in historia:
        if sal == 0:
            continue                          # año sin cotización → no consume semanas
        sal_act = sal * fac
        disp    = min(sem_por_anio, 500.0 - acum)
        if disp <= 0:
            break
        suma += sal_act * disp
        acum += disp
    return suma / acum if acum > 0 else 0.0


# ── 2-4. CBIV, PMG, base, b1/b2 ──────────────────────────────────────────────
def cbiv_diario(sal_d: float) -> float:
    return PCT_CUANTIA_BASICA * sal_d

def cbiv_mensual(sal_d: float) -> float:
    """CBIV mensual = CBIV_diario × 365/12  (convención del lab)."""
    return cbiv_diario(sal_d) * 365.0 / 12.0

def pmg(uma: float = UMA_DIARIA) -> float:
    return PMG_FACTOR * uma * 30.0

def base_pension(sal_d: float, uma: float = UMA_DIARIA) -> float:
    return max(cbiv_mensual(sal_d), pmg(uma))

def b1(j: int, sal_d: float, uma: float = UMA_DIARIA) -> float:
    """Beneficio mensual con cónyuge vivo y j hijos. Tope: 100% del salario mensual."""
    pct  = 1.0 + PCT_CONYUGE + j * PCT_HIJO + PCT_AYUDA_ASIST
    tope = sal_d * 365.0 / 12.0
    return min(base_pension(sal_d, uma) * pct, tope)

def b2(j: int, sal_d: float, uma: float = UMA_DIARIA) -> float:
    """Beneficio mensual sin cónyuge y j hijos. Tope: 100% del salario mensual."""
    pct  = 1.0 + j * PCT_HIJO + PCT_AYUDA_ASIST
    tope = sal_d * 365.0 / 12.0
    return min(base_pension(sal_d, uma) * pct, tope)


# ── 5. ä del inválido ─────────────────────────────────────────────────────────
def ax_invalido(edad: int, sexo: str) -> float:
    """Anualidad vitalicia anticipada — tabla Invalidez Val Act 2020."""
    total = 0.0
    for k in range(110 - edad):
        total += _v(k) * kpx_inv(edad, sexo, k)
    return total


# ── 6. B_mensual conjunta (convoluciones) ─────────────────────────────────────
def b_mensual_conjunta(
    edad_x:  int, sexo_x:  str,     # inválido
    edad_y:  int, sexo_y:  str,     # cónyuge
    hijos:   List[Hijo],
    sal_d:   float,
    uma:     float = UMA_DIARIA,
    b1_override: dict | None = None,  # dict {j: valor} para usar valores del lab
    b2_override: dict | None = None,
) -> float:
    """
    B_mensual = Σ_{k=0}^{∞} v^k × kpx_inv × Π_i kpx_hijo_i(k)
                × [b1(j_k) × kpy + b2(j_k) × (1-kpy)]

    Los hijos activos en el año k son los que aún tienen derecho a pensión (k < nr_i).
    """
    total = 0.0
    for k in range(110 - edad_x):
        # Mortalidad del inválido
        sx = kpx_inv(edad_x, sexo_x, k)
        if sx < 1e-12:
            break

        # Hijos vigentes en el año k
        hijos_vivos = [h for h in hijos if k < h.anios_restantes]
        j_k = len(hijos_vivos)

        # Supervivencia conjunta de los hijos vigentes (tabla activos)
        sh = 1.0
        for h in hijos_vivos:
            sh *= kpx_act(h.edad, h.sexo, k)

        # Supervivencia del cónyuge (tabla activos)
        sy = kpx_act(edad_y, sexo_y, k)

        # Beneficios con y sin cónyuge
        if b1_override and j_k in b1_override:
            b1k = b1_override[j_k]
        else:
            b1k = b1(j_k, sal_d, uma)

        if b2_override and j_k in b2_override:
            b2k = b2_override[j_k]
        else:
            b2k = b2(j_k, sal_d, uma)

        ben = b1k * sy + b2k * (1.0 - sy)
        total += _v(k) * sx * sh * ben

    return total


# ── 7-9. PBSI, PNSI, MCSI ────────────────────────────────────────────────────
def calcular_pbsi(ax: float, B: float, inc: float = INC) -> float:
    """PBSI = (1 + INC) × ä_inv × B_mensual."""
    return (1.0 + inc) * ax * B

def calcular_pnsi(pbsi: float, facbi: float) -> float:
    """PNSI = PBSI × FACBI."""
    return pbsi * facbi

def calcular_mcsi(
    pnsi: float,
    a: float = RECARGO_A,
    b: float = RECARGO_B,
    pv: float = PV,
) -> float:
    """MCSI = (PNSI − PV) × (1+a) / (1−b)."""
    return (pnsi - pv) * (1.0 + a) / (1.0 - b)


# ── API pública ────────────────────────────────────────────────────────────────
def calcular_monto_constitutivo(
    *,
    edad_invalido:  int,
    sexo_invalido:  str,
    edad_conyuge:   int,
    sexo_conyuge:   str,
    hijos:          List[Hijo],
    sal_prom_diario: float,
    uma_diaria:     float = UMA_DIARIA,
    inc:            float = INC,
    facbi:          float = 1.0,
    a:              float = RECARGO_A,
    b_rec:          float = RECARGO_B,
    pv:             float = PV,
    b1_override:    dict | None = None,  # valores del lab para b1(j)
    b2_override:    dict | None = None,  # valores del lab para b2(j)
) -> dict:
    """Calcula paso a paso PBSI → PNSI → MCSI (Laboratorio MC10)."""
    if len(hijos) < 1:
        raise ValueError("Se requiere al menos 1 hijo.")

    n         = len(hijos)
    sal_m_365 = sal_prom_diario * 365.0 / 12.0   # salario mensual convención lab
    cb_d      = cbiv_diario(sal_prom_diario)
    cb_m      = cbiv_mensual(sal_prom_diario)
    pmg_m     = pmg(uma_diaria)
    base_m    = max(cb_m, pmg_m)

    # Tabla b1/b2
    tabla_b = {}
    for j in range(n + 1):
        bv1 = b1_override[j] if (b1_override and j in b1_override) else b1(j, sal_prom_diario, uma_diaria)
        bv2 = b2_override[j] if (b2_override and j in b2_override) else b2(j, sal_prom_diario, uma_diaria)
        tabla_b[j] = {"b1": round(bv1, 2), "b2": round(bv2, 2)}

    # Cálculo actuarial
    ax  = ax_invalido(edad_invalido, sexo_invalido)
    B   = b_mensual_conjunta(
        edad_invalido, sexo_invalido,
        edad_conyuge,  sexo_conyuge,
        hijos, sal_prom_diario, uma_diaria,
        b1_override, b2_override,
    )
    ax_cony = sum(_v(k) * kpx_act(edad_conyuge, sexo_conyuge, k)
                  for k in range(110 - edad_conyuge))

    pbsi = calcular_pbsi(ax, B, inc)
    pnsi = calcular_pnsi(pbsi, facbi)
    mcsi = calcular_mcsi(pnsi, a, b_rec, pv)

    return {
        # Entradas
        "edad_invalido":    edad_invalido,
        "sexo_invalido":    sexo_invalido,
        "edad_conyuge":     edad_conyuge,
        "sexo_conyuge":     sexo_conyuge,
        "n_hijos":          n,
        # Salario
        "sal_prom_diario":  round(sal_prom_diario, 4),
        "sal_prom_mensual": round(sal_m_365, 2),
        # CBIV y PMG
        "cbiv_diario":      round(cb_d, 4),
        "cbiv_mensual":     round(cb_m, 2),
        "pmg_mensual":      round(pmg_m, 2),
        "base_mensual":     round(base_m, 2),
        # b1/b2
        "tabla_b":          tabla_b,
        # Intermedios actuariales
        "ax_invalido":      round(ax, 6),
        "ax_conyuge":       round(ax_cony, 6),
        "b_mensual":        round(B, 2),
        # Primas
        "inc":              inc,
        "pbsi":             round(pbsi, 2),
        "facbi":            facbi,
        "pnsi":             round(pnsi, 2),
        "a":                a,
        "b_rec":            b_rec,
        "pv":               pv,
        "mcsi":             round(mcsi, 2),
        # Parámetros
        "tasa_interes":     TASA_INTERES,
        "uma_diaria":       uma_diaria,
    }

