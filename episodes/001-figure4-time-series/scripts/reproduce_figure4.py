#!/usr/bin/env python
"""Attempt reproduction of Fig. 4 saturation-ratio trajectories.

This script uses the Phase 2 implementation of Eqs. (4)--(6) at T=225 K,
p=300 hPa, F=1 and w in {0.01, 0.1, 1} m/s. The paper caption does not give
initial conditions; following the text around the limit-cycle calculations, we
start at x_eq * (1 - epsilon) with epsilon=0.01. This is therefore a qualitative
trajectory reproduction, not a digitized point-by-point validation.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import equilibrium, integrate_trajectory

EPISODE_ROOT = Path(__file__).resolve().parents[1]
OUT = EPISODE_ROOT / "outputs"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.2), sharey=False)
    cases = [(0.01, "stable, lower regime"), (0.1, "limit cycle"), (1.0, "stable, higher regime")]
    for ax, (w, label) in zip(axes, cases):
        env = Environment(p=30000.0, T=225.0, w=w, F=1.0)
        x_eq = equilibrium(env)
        y0 = x_eq * 0.99
        sol = integrate_trajectory(env, y0, (0.0, 100_000.0), max_step=50.0, rtol=1e-8, atol=1e-13)
        if not sol.success:
            raise RuntimeError(sol.message)
        t_hours = sol.t / 3600.0
        ax.plot(t_hours, sol.y[2], color="firebrick", lw=1.2, label="s(t)")
        ax.axhline(x_eq[2], color="black", lw=0.9, alpha=0.7, label="equilibrium")
        ax.set_title(f"w = {w:g} m s$^{{-1}}$\n{label}")
        ax.set_xlabel("time [h]")
        ax.set_ylabel("saturation ratio s")
        ax.grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("Bergner & Spichtinger (2026) Fig. 4 qualitative reproduction")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    target = OUT / "figure4_reproduction.png"
    fig.savefig(target, dpi=200)
    print(f"wrote {target.relative_to(EPISODE_ROOT)}")


if __name__ == "__main__":
    main()
