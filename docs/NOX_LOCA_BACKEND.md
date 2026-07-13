# Full NOX/LOCA backend notes

TASK-025 adds a dense NOX/LOCA-facing backend for the validated Bergner--Spichtinger C++ model in `loca/`.

## Scope

The adapter lives in `loca/include/bergner_spichtinger_2026_loca/nox_loca_backend.hpp` and implements `LOCA::LAPACK::Interface` for the existing three-variable equilibrium residual:

- state: `(log_n, log_q, s)`
- primary continuation parameter: `log_w`
- additional LOCA parameters exposed for later two-parameter work: `T`, `p`, `F`, `N_a`, and `dz`

The adapter calls the same `residual_values()` and Sacado-derived `state_jacobian()` functions as the lightweight C++ backend. It does not change the physical equations, log-coordinate semantics, physical eigenvalue semantics, or normalized CSV schema.

## Lightweight backend vs NOX/LOCA adapter

| Aspect | Lightweight Trilinos-side C++ backend | NOX/LOCA backend |
| --- | --- | --- |
| CLI command | `continue` | `nox-loca-continue` |
| Solver path | repository-owned natural-parameter predictor/corrector | repository-owned parameter grid, with each correction solved through `LOCA::LAPACK::Group` + `NOX::Solver::Generic` rather than `newton_correct` |
| Residual/Jacobian source | `model.hpp` residual and Sacado Jacobian | identical residual/Jacobian through NOX/LOCA callback types |
| Parameters | command-line environment fields plus `log_w` | `LOCA::ParameterVector` with `log_w`, `T`, `p`, `F`, `N_a`, `dz` |
| Diagnostics | branch residuals, convergence flags, eigenvalues | same normalized diagnostics plus `loca_continuation_mode=nox_loca_lapack_group_nox_solver` |
| Complexity added | minimal | NOX/LOCA vector/matrix callback plumbing and parameter-vector indirection |
| What LOCA adds here | none numerically for 1D Figure 1 validation; the value is an API-compatible foundation for later native LOCA bifurcation/Hopf continuation | exposes the problem in LOCA's expected dense-LAPACK form, including parameters needed by Episode 006 two-parameter Hopf work |

The current `nox-loca-continue` path is deliberately an equilibrium-continuation validation layer: LOCA supplies the dense problem group and parameter plumbing, NOX supplies the nonlinear solves, and the repository still chooses the validation `log_w` grid. It is not native LOCA Hopf-locus orchestration; that remains out of scope for TASK-025 and belongs to TASK-030.

## Commands

```bash
# Build the shared C++ executable.
cmake -S loca -B .pytest_cache/loca-build -DTrilinos_DIR=/opt/Trilinos/lib64/cmake/Trilinos
cmake --build .pytest_cache/loca-build --parallel 2

# Smoke-check NOX/LOCA callbacks at one point.
.pytest_cache/loca-build/bs2026_loca_model nox-loca-smoke LOG_N LOG_Q S LOG_W --T 230 --p 30000 --F 1 --N-a 10000000000 --dz 100

# Write normalized Figure 1-style NOX/LOCA branch outputs.
uv run python episodes/004-figure1-loca-continuation/scripts/run_nox_loca_figure1.py --clean
```

## Availability and skip conditions

Tests and scripts require:

- `/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake`
- CMake and a C++17 compiler
- Trilinos headers/libraries for Sacado, Teuchos LAPACK, NOX LAPACK, and LOCA LAPACK

Pytest smoke checks skip cleanly when the Trilinos CMake config, CMake, or the compiler is unavailable. A build failure usually indicates a Trilinos installation without the dense NOX/LOCA LAPACK interface headers/libraries.

## Validation target and tolerances

The NOX/LOCA branch runner preserves the Episode 4 normalized schema and can be compared directly with curated `episodes/004-figure1-loca-continuation/outputs/figure1_loca_branches/` artifacts. Because the continuation corrector and model equations are intentionally shared, rows at the same requested `log_w` should agree to roundoff-scale tolerances for `log_n`, `log_q`, `s`, residual norms, and eigenvalue-derived normalized fields. For test-time short branches, schema compatibility, convergence, positive `n/q`, finite residuals, and mode labeling are the primary smoke checks.
