"""
invalidez_conyuge_hijos.py
==========================
Cálculo actuarial del Monto Constitutivo del Seguro de Invalidez
para un trabajador inválido con cónyuge e hijos (mínimo cuatro),
conforme al Anexo 18.5.1 de la LSS — Secciones 4 y 5.

Estructura:
  Sección 4 — Seguro de Invalidez
    · Prima básica del seguro de invalidez (PBSI)
    · Prima del seguro de invalidez para hijos (PSIH)
    · Prima neta del seguro de invalidez (PNSI)
    · Monto constitutivo del seguro de invalidez (MCSI)

  Sección 5 — Seguro de Sobrevivencia
    · Prima básica del seguro de sobrevivencia (PBSS)
    · Prima del seguro de invalidez para hijos del sobrevivencia (PSIH_SS)
    · Prima del finiquito para hijos (PFH)
    · Prima neta del seguro de sobrevivencia (PNSS)
    · Monto constitutivo del seguro de sobrevivencia (MCSS)

  Monto Constitutivo Total (MCT) = MCSI + MCSS

Referencias:
  · LSS Arts. 119-145 (invalidez y vida)
  · Circular Única de Seguros, Anexo 18.5.1
  · Tablas de mortalidad EMSSA (inválidos) y EMSSAH/M (no inválidos)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTES GENERALES
# ──────────────────────────────────────────────────────────────────────────────

# Tasa de interés técnico anual (CNSF)
TASA_INTERES: float = 0.035          # 3.5 % anual

# Factor de actualización por inflación (FACBI); se asume 1.0 cuando el
# salario ya está expresado en pesos corrientes.
FACBI: float = 1.0

# Recargos sobre prima neta (gastos de administración + utilidad aseguradora)
RECARGO_INVALIDEZ: float = 1.09      # 9 %
RECARGO_SOBREVIVENCIA: float = 1.09  # 9 %

# Cuantía básica y asignaciones familiares (Art. 141 y 138 LSS)
PCT_CUANTIA_BASICA: float = 0.35     # 35 % del salario promedio
PCT_CONYUGE: float = 0.15            # 15 % asignación cónyuge
PCT_HIJO: float = 0.10               # 10 % por hijo (≤ 16 / ≤ 25 si estudia)
PCT_AYUDA_ASIST: float = 0.16        # 16 % ayuda asistencial (promedio IMSS)

# Pensión de viudez tras fallecimiento del inválido (Art. 130-131 LSS): 90 %
PCT_VIUDEZ: float = 0.90

# Pensión de orfandad (Art. 135 LSS)
PCT_ORFANDAD_SENCILLA: float = 0.20  # huérfano de padre o madre
PCT_ORFANDAD_DOBLE: float = 0.30     # huérfano de padre y madre

# Finiquito orfandad: 3 mensualidades (Art. 136 LSS)
MESES_FINIQUITO: int = 3

# Edad límite de hijos para pensión de orfandad (con posibilidad hasta 25)
EDAD_LIMITE_HIJOS_BASE: int = 16
EDAD_LIMITE_HIJOS_EST: int = 25

# ──────────────────────────────────────────────────────────────────────────────
# TABLAS DE MORTALIDAD SIMPLIFICADAS (EMSSA / EMSSAH / EMSSAM)
# Se representan como qx  (prob. de morir entre edad x y x+1).
# NOTA: En producción deben cargarse desde el Anexo 14.2.4.b CUS.
# Aquí se usan aproximaciones de la tabla Makeham calibradas a EMSSA/EMSSAH.
# ──────────────────────────────────────────────────────────────────────────────

def _makeham_qx(edad: int, A: float, B: float, c: float) -> float:
    """Probabilidad de muerte Makeham: qx ≈ 1 - exp(-(A + B*(c^x - c^(x+1))/(ln c)))."""
    mu = A + B * (c ** edad)
    return min(1.0, 1.0 - math.exp(-mu))


# Parámetros Makeham para cada tabla (calibración académica)
_PARAMS_INVALIDOS_H = dict(A=0.0010, B=0.00005, c=1.115)   # EMSSA hombres
_PARAMS_INVALIDOS_M = dict(A=0.0008, B=0.00004, c=1.110)   # EMSSA mujeres
_PARAMS_SANOS_H     = dict(A=0.0005, B=0.000025, c=1.100)  # EMSSAH hombres
_PARAMS_SANOS_M     = dict(A=0.0004, B=0.000018, c=1.095)  # EMSSAM mujeres


def qx_invalido(edad: int, sexo: str) -> float:
    p = _PARAMS_INVALIDOS_H if sexo.upper() in ("H", "M_TRANS") else _PARAMS_INVALIDOS_M
    return _makeham_qx(edad, **p)


def qx_sano(edad: int, sexo: str) -> float:
    p = _PARAMS_SANOS_H if sexo.upper() == "H" else _PARAMS_SANOS_M
    return _makeham_qx(edad, **p)


def px_invalido(edad: int, sexo: str) -> float:
    return 1.0 - qx_invalido(edad, sexo)


def px_sano(edad: int, sexo: str) -> float:
    return 1.0 - qx_sano(edad, sexo)


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIONES ACTUARIALES ELEMENTALES
# ──────────────────────────────────────────────────────────────────────────────

def v(n: int = 1) -> float:
    """Factor de descuento: v^n = (1/(1+i))^n."""
    return (1.0 / (1.0 + TASA_INTERES)) ** n


def ax_invalido(edad: int, sexo: str, max_edad: int = 110) -> float:
    """
    Anualidad vitalicia anticipada para inválido (tabla EMSSA).
    ä_x = Σ_{k=0}^{ω-x} v^k · k_p_x^inv
    """
    total = 0.0
    surv = 1.0
    for k in range(max_edad - edad):
        total += (v() ** k) * surv
        surv *= px_invalido(edad + k, sexo)
    return total


def ax_sano(edad: int, sexo: str, max_edad: int = 110) -> float:
    """Anualidad vitalicia anticipada para persona sana (tabla EMSSAH/M)."""
    total = 0.0
    surv = 1.0
    for k in range(max_edad - edad):
        total += (v() ** k) * surv
        surv *= px_sano(edad + k, sexo)
    return total


def ax_n_invalido(edad: int, sexo: str, n: int) -> float:
    """Anualidad temporal anticipada (n años) para inválido."""
    total = 0.0
    surv = 1.0
    for k in range(n):
        total += (v() ** k) * surv
        if edad + k < 110:
            surv *= px_invalido(edad + k, sexo)
        else:
            break
    return total


def ax_n_sano(edad: int, sexo: str, n: int) -> float:
    """Anualidad temporal anticipada (n años) para persona sana."""
    total = 0.0
    surv = 1.0
    for k in range(n):
        total += (v() ** k) * surv
        if edad + k < 110:
            surv *= px_sano(edad + k, sexo)
        else:
            break
    return total


def Ax_invalido(edad: int, sexo: str, max_edad: int = 110) -> float:
    """
    Seguro de vida entera pagadero al final del año de muerte (inválido).
    A_x = Σ_{k=0}^{ω-x-1} v^{k+1} · k_p_x^inv · q_{x+k}^inv
    """
    total = 0.0
    surv = 1.0
    for k in range(max_edad - edad):
        q = qx_invalido(edad + k, sexo)
        total += (v() ** (k + 1)) * surv * q
        surv *= (1.0 - q)
    return total


def Ax_diferido_invalido(edad: int, sexo: str, diferimiento: int,
                         max_edad: int = 110) -> float:
    """
    Seguro de vida entera con período de diferimiento t años (inválido).
    Se usa para la prima del seguro de sobrevivencia.
    """
    # Sobrevivencia hasta el diferimiento
    surv_t = 1.0
    for k in range(diferimiento):
        surv_t *= px_invalido(edad + k, sexo)
    # Seguro de vida entera desde la edad diferida
    return (v() ** diferimiento) * surv_t * Ax_invalido(edad + diferimiento, sexo, max_edad)


# ──────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE SALARIO PROMEDIO (últimas 500 semanas)
# ──────────────────────────────────────────────────────────────────────────────

def salario_promedio_500_semanas(historial: List[Tuple[float, int]]) -> float:
    """
    Calcula el salario diario promedio de las últimas 500 semanas (≈ 9.6 años).

    Parameters
    ----------
    historial : list of (salario_diario, semanas)
        Lista ordenada del más reciente al más antiguo. Cada elemento es
        (salario_diario_promedio_en_ese_período, número_de_semanas).

    Returns
    -------
    float : salario diario promedio ponderado.
    """
    semanas_acum = 0
    suma_ponderada = 0.0
    for sal_d, sem in historial:
        sem_disponibles = min(sem, 500 - semanas_acum)
        suma_ponderada += sal_d * sem_disponibles
        semanas_acum += sem_disponibles
        if semanas_acum >= 500:
            break
    return suma_ponderada / min(semanas_acum, 500) if semanas_acum > 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# DATACLASS DE HIJO
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Hijo:
    edad: int
    sexo: str = "H"            # "H" = hombre, "M" = mujer
    estudia: bool = True       # True → límite 25 años; False → límite 16
    invalido: bool = False     # True → pensión indefinida (Art. 138 LSS)

    @property
    def edad_limite(self) -> int:
        if self.invalido:
            return 110          # pensión sin límite de edad
        return EDAD_LIMITE_HIJOS_EST if self.estudia else EDAD_LIMITE_HIJOS_BASE

    @property
    def anios_restantes(self) -> int:
        return max(0, self.edad_limite - self.edad)


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 4 — SEGURO DE INVALIDEZ
# ──────────────────────────────────────────────────────────────────────────────

def calcular_pension_invalido(salario_diario_prom: float, n_hijos: int) -> float:
    """
    Cuantía mensual de pensión del inválido con cónyuge e hijos (Art. 141, 138 LSS).

    C = S * (CB + AF_conyuge + AF_hijos + AA)
    donde S = salario mensual promedio (= sal_d * 30).
    """
    sal_mensual = salario_diario_prom * 30.0
    total_pct = PCT_CUANTIA_BASICA + PCT_CONYUGE + n_hijos * PCT_HIJO + PCT_AYUDA_ASIST
    # Cota máxima: 100 % del salario (Art. 143)
    total_pct = min(total_pct, 1.0)
    return sal_mensual * total_pct


def pbsi_conyuge_hijos(
    edad_invalido: int,
    sexo_invalido: str,
    pension_mensual: float,
    hijos: List[Hijo],
) -> float:
    """
    Prima básica del seguro de invalidez — inválido con cónyuge e hijos.
    Sección 4a del Anexo 18.5.1.

    PBSI = P_mensual * 12 * FACBI * ä_x^inv

    La pensión mensual ya incluye cuantía básica + asignaciones familiares
    (cónyuge + hijos) + ayuda asistencial.
    """
    ax = ax_invalido(edad_invalido, sexo_invalido)
    pbsi = pension_mensual * 12.0 * FACBI * ax
    return pbsi


def psih_invalido(
    edad_invalido: int,
    sexo_invalido: str,
    salario_diario_prom: float,
    hijos: List[Hijo],
) -> float:
    """
    Prima del seguro de invalidez para hijos (PSIH) — Sección 4b Anexo 18.5.1.

    Garantiza el pago de pensión a los hijos que sufran invalidez después
    del cálculo de la PBSI.

    PSIH = Σ_i  [10% * C_basica * 12 * FACBI * (ä_{x,n_i}^inv_invalido - ä_{y_i,n_i}^inv_hijo)]

    donde n_i = años restantes del hijo i hasta su edad límite.
    C_basica = 35% * sal_mensual (cuantía base sin asignaciones).
    """
    c_basica_mensual = PCT_CUANTIA_BASICA * salario_diario_prom * 30.0
    total = 0.0
    for hijo in hijos:
        n = hijo.anios_restantes
        if n <= 0:
            continue
        # anualidad temporal del inválido durante n años
        ax_n = ax_n_invalido(edad_invalido, sexo_invalido, n)
        # anualidad temporal del hijo durante n años (sano, pues aún no es inválido)
        ax_n_hijo = ax_n_sano(hijo.edad, hijo.sexo, n)
        # diferencia: probabilidad de que el inválido muera antes de que el hijo
        # alcance su límite, multiplicada por el valor de la anualidad del hijo
        psih_hijo = PCT_HIJO * c_basica_mensual * 12.0 * FACBI * abs(ax_n - ax_n_hijo)
        total += psih_hijo
    return total


def pnsi_conyuge_hijos(pbsi: float, psih: float) -> float:
    """Prima neta del seguro de invalidez = PBSI + PSIH."""
    return pbsi + psih


def mcsi_conyuge_hijos(pnsi: float) -> float:
    """
    Monto constitutivo del seguro de invalidez.
    MCSI = PNSI * Recargo
    """
    return pnsi * RECARGO_INVALIDEZ


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 5 — SEGURO DE SOBREVIVENCIA
# ──────────────────────────────────────────────────────────────────────────────

def pbss_conyuge_hijos(
    edad_invalido: int,
    sexo_invalido: str,
    edad_conyuge: int,
    sexo_conyuge: str,
    pension_mensual_invalido: float,
) -> float:
    """
    Prima básica del seguro de sobrevivencia — cónyuge (Sección 5a).

    Cuando muere el inválido, la viuda/o recibe el 90 % de la pensión base
    (sin asignaciones familiares, Art. 139).

    PBSS = Σ_{k=0}^{ω_inv - x} [ v^{k+1} * k_p_x^inv * q_{x+k}^inv
                                   * P_viudez * 12 * FACBI
                                   * ä_{y+k}^sano ]

    donde P_viudez = 90% * C_basica_mensual.
    c_basica_mensual = 35% * sal_mensual  (sin asignaciones, Art. 139).
    """
    # La pensión de viudez es 90 % de la cuantía base (sin asignaciones)
    # Aproximamos la cuantía base: pension_mensual / (1 + pct_af + aa)
    factor_total = 1 + PCT_CONYUGE + PCT_AYUDA_ASIST  # sin hijos ya fallecidos
    c_basica_mensual = pension_mensual_invalido / factor_total
    p_viudez = PCT_VIUDEZ * c_basica_mensual

    total = 0.0
    surv_inv = 1.0
    max_k = 110 - edad_invalido
    for k in range(max_k):
        q_inv = qx_invalido(edad_invalido + k, sexo_invalido)
        # VP de la anualidad de la viuda/o desde edad (y+k) en adelante
        ax_conyuge = ax_sano(min(edad_conyuge + k, 109), sexo_conyuge)
        total += (v() ** (k + 1)) * surv_inv * q_inv * p_viudez * 12.0 * FACBI * ax_conyuge
        surv_inv *= (1.0 - q_inv)
    return total


def psih_sobrevivencia(
    edad_invalido: int,
    sexo_invalido: str,
    salario_diario_prom: float,
    hijos: List[Hijo],
    n_huerfanos_sencillos: int = 0,
    n_huerfanos_dobles: int = 0,
) -> float:
    """
    Prima del seguro de invalidez para hijos en el seguro de sobrevivencia
    (Sección 5b, Anexo 18.5.1).

    Al fallecer el inválido, sus hijos pasan a ser huérfanos y reciben:
      · Huérfano sencillo (un padre muerto): 20 % C_basica
      · Huérfano doble  (ambos padres muertos): 30 % C_basica

    La distribución entre beneficiarios se hace según la tabla legal D/S.

    PSIH_SS = Σ_i [ pct_i * C_basica * 12 * FACBI
                    * Σ_{k=0}^{n_i} v^k * k_p_x^inv * ... ]
    """
    c_basica_mensual = PCT_CUANTIA_BASICA * salario_diario_prom * 30.0
    total = 0.0
    # Para cada hijo activo, calcular la prima de orfandad tras muerte del inválido
    for hijo in hijos:
        n = hijo.anios_restantes
        if n <= 0:
            continue
        # Suma esperada de VP de la pensión de orfandad desde la muerte del inválido
        contrib = 0.0
        surv_inv = 1.0
        for k in range(min(n, 110 - edad_invalido)):
            q_inv = qx_invalido(edad_invalido + k, sexo_invalido)
            # años restantes del hijo en el momento k
            n_restante = n - k
            if n_restante <= 0:
                break
            # anualidad del hijo desde su edad actual + k durante n_restante años
            ax_hijo = ax_n_sano(min(hijo.edad + k, 109), hijo.sexo, n_restante)
            # pct de orfandad: sencilla por defecto (el otro progenitor vivo)
            pct_orf = PCT_ORFANDAD_SENCILLA
            contrib += (v() ** (k + 1)) * surv_inv * q_inv * pct_orf * c_basica_mensual * 12.0 * FACBI * ax_hijo
            surv_inv *= (1.0 - q_inv)
        total += contrib
    return total


def pfh_hijos(
    edad_invalido: int,
    sexo_invalido: str,
    salario_diario_prom: float,
    hijos: List[Hijo],
) -> float:
    """
    Prima del finiquito para hijos (PFH) — Sección 5c, Art. 136 LSS.

    Al extinguirse la pensión de orfandad (por edad límite), se pagan 3
    mensualidades de finiquito.

    PFH = Σ_i [ 3 * P_orfandad_i * v^{n_i} * n_i_p_x^inv * n_i_p_{y_i}^sano ]
    """
    c_basica_mensual = PCT_CUANTIA_BASICA * salario_diario_prom * 30.0
    total = 0.0
    for hijo in hijos:
        n = hijo.anios_restantes
        if n <= 0:
            continue
        # Sobrevivencia del inválido hasta n años
        surv_inv = 1.0
        for k in range(min(n, 110 - edad_invalido)):
            surv_inv *= px_invalido(edad_invalido + k, sexo_invalido)
        # Sobrevivencia del hijo hasta n años
        surv_hijo = 1.0
        for k in range(min(n, 110 - hijo.edad)):
            surv_hijo *= px_sano(hijo.edad + k, hijo.sexo)
        # Finiquito: 3 mensualidades de orfandad sencilla
        p_finiquito = MESES_FINIQUITO * PCT_ORFANDAD_SENCILLA * c_basica_mensual
        total += p_finiquito * (v() ** n) * surv_inv * surv_hijo * FACBI
    return total


def pnss_conyuge_hijos(pbss: float, psih_ss: float, pfh: float) -> float:
    """Prima neta del seguro de sobrevivencia = PBSS + PSIH_SS + PFH."""
    return pbss + psih_ss + pfh


def mcss_conyuge_hijos(pnss: float) -> float:
    """
    Monto constitutivo del seguro de sobrevivencia.
    MCSS = PNSS * Recargo
    """
    return pnss * RECARGO_SOBREVIVENCIA


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL — cálculo completo
# ──────────────────────────────────────────────────────────────────────────────

def calcular_monto_constitutivo_invalido(
    *,
    edad_invalido: int,
    sexo_invalido: str,
    edad_conyuge: int,
    sexo_conyuge: str,
    hijos: List[Hijo],
    salario_diario_prom: float,
) -> dict:
    """
    Calcula el Monto Constitutivo Total para un inválido con cónyuge e hijos.

    Parameters
    ----------
    edad_invalido      : edad actual del asegurado inválido
    sexo_invalido      : "H" hombre | "M" mujer | "M_TRANS" mujer transgénero
    edad_conyuge       : edad del cónyuge/concubina(o)
    sexo_conyuge       : "H" | "M"
    hijos              : lista de objetos Hijo (mínimo 4)
    salario_diario_prom: salario diario promedio de las últimas 500 semanas

    Returns
    -------
    dict con todos los componentes del monto constitutivo.
    """
    #n_hijos = len(hijos)
    #if n_hijos < 4:
    #   raise ValueError(f"Se requieren al menos 4 hijos; se proporcionaron {n_hijos}.")

    pension_mensual = calcular_pension_invalido(salario_diario_prom, n_hijos)

    # ── Sección 4: Seguro de Invalidez ────────────────────────────────────────
    pbsi = pbsi_conyuge_hijos(edad_invalido, sexo_invalido, pension_mensual, hijos)
    psih = psih_invalido(edad_invalido, sexo_invalido, salario_diario_prom, hijos)
    pnsi = pnsi_conyuge_hijos(pbsi, psih)
    mcsi = mcsi_conyuge_hijos(pnsi)

    # ── Sección 5: Seguro de Sobrevivencia ────────────────────────────────────
    pbss = pbss_conyuge_hijos(
        edad_invalido, sexo_invalido,
        edad_conyuge, sexo_conyuge,
        pension_mensual,
    )
    psih_ss = psih_sobrevivencia(
        edad_invalido, sexo_invalido,
        salario_diario_prom, hijos,
    )
    pfh = pfh_hijos(edad_invalido, sexo_invalido, salario_diario_prom, hijos)
    pnss = pnss_conyuge_hijos(pbss, psih_ss, pfh)
    mcss = mcss_conyuge_hijos(pnss)

    # ── Totales ───────────────────────────────────────────────────────────────
    mct = mcsi + mcss

    # ── Anualidades para reporte ───────────────────────────────────────────────
    ax_inv = ax_invalido(edad_invalido, sexo_invalido)
    ax_cony = ax_sano(edad_conyuge, sexo_conyuge)

    return {
        # Datos de entrada
        "edad_invalido": edad_invalido,
        "sexo_invalido": sexo_invalido,
        "edad_conyuge": edad_conyuge,
        "sexo_conyuge": sexo_conyuge,
        "n_hijos": n_hijos,
        "salario_diario_prom": round(salario_diario_prom, 4),
        "salario_mensual_prom": round(salario_diario_prom * 30, 2),
        # Pensión
        "pct_total_pension": round(
            min(PCT_CUANTIA_BASICA + PCT_CONYUGE + n_hijos * PCT_HIJO + PCT_AYUDA_ASIST, 1.0), 4
        ),
        "pension_mensual": round(pension_mensual, 2),
        "pension_anual": round(pension_mensual * 12, 2),
        # Anualidades
        "ax_invalido": round(ax_inv, 6),
        "ax_conyuge": round(ax_cony, 6),
        # Sección 4
        "pbsi": round(pbsi, 2),
        "psih": round(psih, 2),
        "pnsi": round(pnsi, 2),
        "mcsi": round(mcsi, 2),
        # Sección 5
        "pbss": round(pbss, 2),
        "psih_ss": round(psih_ss, 2),
        "pfh": round(pfh, 2),
        "pnss": round(pnss, 2),
        "mcss": round(mcss, 2),
        # Total
        "mct": round(mct, 2),
        # Parámetros usados
        "tasa_interes": TASA_INTERES,
        "recargo_invalidez": RECARGO_INVALIDEZ,
        "recargo_sobrevivencia": RECARGO_SOBREVIVENCIA,
        "facbi": FACBI,
    }