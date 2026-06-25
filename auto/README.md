# Shared AUTO Fortran model core

This top-level `auto/` directory contains shared AUTO-07p backend assets for the Bergner & Spichtinger (2026) model.  The code here is intentionally reusable infrastructure, not an episode-local continuation experiment.

## Files

- `src/bs2026_constants.f90` mirrors `src/bergner_spichtinger_2026/constants.py` with SI constants and paper-equation comments.
- `src/bs2026_model.f90` mirrors `src/bergner_spichtinger_2026/core.py` and `residuals.py`: environment parameters, coefficient calculations, process terms, vector field, and log-coordinate equilibrium residuals.
- `src/bs2026_evaluator.f90` is a small non-AUTO driver for evaluating model quantities without running continuation.
- `Makefile` builds the evaluator and checks the expected `/usr/local/bin/auto` installation path.

## Requirements

- `gfortran` on `PATH`.
- AUTO-07p available at `/usr/local/bin/auto` for later continuation tasks.  The standalone evaluator does not link against AUTO.

## Build and smoke test

```bash
make -C auto check-auto
make -C auto
make -C auto smoke
```

The executable is written to `auto/bin/bs2026_evaluator`.

## Evaluator commands

All inputs are SI values.  Optional `N_a`, `dz`, and `include_evaporation` default to the Python defaults (`3.0e8 m^-3`, `100 m`, false).

```bash
# Coefficients for p=30000 Pa, T=225 K, w=0.1 m/s, F=1
./auto/bin/bs2026_evaluator coefficients 30000 225 0.1 1

# Process terms at n=1e4 kg_dry_air^-1, q=1e-6 kg/kg_dry_air, s=1.4
./auto/bin/bs2026_evaluator terms 30000 225 0.1 1 1.0e4 1.0e-6 1.4

# Vector field, Eq. (4)--(6)
./auto/bin/bs2026_evaluator rhs 30000 225 0.1 1 1.0e4 1.0e-6 1.4

# Log-coordinate equilibrium residual [dn/dt/n, dq/dt/q, ds/dt]
./auto/bin/bs2026_evaluator residual 30000 225 -2.302585092994046 1 9.210340371976184 -13.815510557964274 1.4
```

Output is stable whitespace-delimited `name value` records with double-precision scientific notation so Python tests and continuation orchestration can parse it directly.
