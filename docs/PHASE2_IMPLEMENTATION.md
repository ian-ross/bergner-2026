# Phase 2 implementation notes

Implemented scope approved by user:

- Core ODE RHS, Eqs. (4)--(6), with process terms Eqs. (7)--(15)/(43)--(70).
- Canonical interpretation of `n`: ice-particle number concentration per dry-air mass; per-volume aerosol concentration is converted via `n_a = N_a / ρ`.
- Eq. (16) regularization is not implemented/enabled; the unregularized RHS requires `n > 0` and `q > 0`.
- `K_T(T)` uses the user-confirmed Eq. (A34) transcription: `(a_K T^b_K)/(T + T_K 10^(c_K/T))`.
- Initial qualitative reproduction target: Figure 4 only; B2SHARE measurement data not used.

Files:

- `src/bergner_spichtinger_2026/constants.py`: constants and `Environment` dataclass.
- `src/bergner_spichtinger_2026/core.py`: thermodynamic helpers, coefficients, process terms, ODE RHS, equilibrium helper, integration helper.
- `src/bergner_spichtinger_2026/units.py`: Pint boundary wrappers.
- `episodes/001-figure4-time-series/scripts/reproduce_figure4.py`: qualitative Fig. 4 reproduction.
- `episodes/001-figure4-time-series/outputs/figure4_reproduction.png`: generated trajectory plot.
- `tests/test_core.py`, `tests/test_units.py`: smoke/unit tests.

Validation status:

- Tests pass with `uv run pytest -q`.
- Equilibrium residuals are small for the three Fig. 4 environments.
- Figure 4 reproduction is qualitative because the paper caption does not specify initial conditions. The script uses `x_eq * 0.99`, matching the nearby description of perturbing equilibrium by `ε = 0.01` for trajectory/limit-cycle simulations.

Remaining risks:

- This is not a digitized reproduction of Fig. 4.
- Constants are implemented from extracted text plus the user-confirmed `K_T`; a final visual audit against rendered HTML/PDF is still advisable before treating numbers as publication-grade.
- Solver/tolerance choices are pragmatic and documented in the script, not specified by the paper.
