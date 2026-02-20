from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

def save_fig(fig: plt.Figure, out_dir: str = "plots", filename: str = "plot.png") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(out_dir) / filename
    fig.savefig(out_path, bbox_inches="tight", dpi=200)
    return str(out_path)

def line_plot(df: pd.DataFrame, x: str, y_cols: list[str], title: str, xlabel: str, ylabel: str) -> plt.Figure:
    fig, ax = plt.subplots()
    for col in y_cols:
        ax.plot(df[x], df[col], label=col)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True)
    return fig
