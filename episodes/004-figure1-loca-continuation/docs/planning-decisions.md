# Episode 4 planning decisions

Episode 4 prepares the LOCA/Trilinos backend-equivalence path for the Figure 1 equilibrium branch family. It should extend the Episode 2 Python-native reference and Episode 3 AUTO-07p backend comparison without changing the underlying Bergner & Spichtinger (2026) model semantics.

## Backend-comparison goal

LOCA should answer the same question as AUTO did in Episode 3: can an independent continuation backend reproduce the Figure 1 equilibrium branches when given the same residual equations, continuation coordinate, environmental constants, and output contract?

For this episode the target remains:

- `p = 300 hPa`
- `F = 1`
- `T ∈ {190, 210, 230} K`
- `w ∈ [0.005, 2.0] m s^-1`
- continuation in `log_w = log(w_m_s)`
- normalized comparison in physical `n`, `q`, and `s`

## Agreed LOCA design choices

- Use a serial dense LOCA setup first. The initial problem size is the three-state Figure 1 equilibrium residual, so distributed vectors, sparse matrix infrastructure, and MPI should be deferred until a larger model justifies them.
- Use LAPACK-backed dense linear algebra through Trilinos/LOCA/NOX rather than introducing a custom linear solver in the first implementation.
- Use Sacado automatic differentiation for the state Jacobian of the residual. This keeps the C++ Jacobian tied to the residual implementation and reduces hand-derived algebra drift.
- Treat Python as the semantic model reference. The Python package implementation and Episode 2 branch outputs define the intended coefficients, residuals, transformed coordinates, and physical normalization.
- Reuse the backend-neutral branch schema from Episode 3. LOCA-specific diagnostics may be added as optional columns, but comparison scripts should not need a separate LOCA-only schema.
- Keep orchestration and generated artifacts episode-local until there is a demonstrated cross-episode reason to promote C++/Trilinos infrastructure.

## Build and toolchain assumptions

The first LOCA implementation is expected to require an external Trilinos installation with at least these capabilities enabled:

- LOCA and NOX
- Teuchos
- Sacado
- LAPACK or a compatible dense linear algebra backend
- a C++ compiler matching the Trilinos build ABI
- CMake for configuring the episode-local executable or driver

The initial build should be serial. MPI, Tpetra/Epetra distributed operators, and sparse preconditioners are intentionally out of scope for the Figure 1 three-variable equilibrium problem.

Every curated run should record toolchain provenance, including the Trilinos version or install path, C++ compiler identity, CMake generator/configuration, relevant LOCA/NOX solver parameters, command lines, git commit, and input/output paths.

## Residual and Jacobian contract

The C++ residual should implement the same equilibrium residual semantics used by `src/bergner_spichtinger_2026/` and the Episode 2/3 scripts. Internal state coordinates may use transformed variables such as `log_n` and `log_q` for positivity and conditioning, but normalized outputs must include physical values.

Sacado should provide derivatives with respect to the state variables. The continuation parameter `log_w` should be treated as the LOCA continuation parameter, with `w_m_s = exp(log_w)` passed into residual evaluation. Coefficients that depend only on the environment must not be recomputed as if they depended on the continuation step except through the controlled vertical velocity.

## Output contract

LOCA branch outputs should follow the Episode 3 backend-neutral branch schema where applicable. Required fields for curated CSV outputs are:

| Field | Meaning |
| --- | --- |
| `backend` | Literal `loca`. |
| `branch_id` | Stable branch name such as `figure1_T190K`. |
| `T_K` or `temperature_K` | Branch temperature in kelvin; prefer consistency with existing comparison scripts. |
| `p_Pa` or `pressure_Pa` | Environmental pressure. |
| `F` | Sedimentation scaling factor. |
| `N_a_m3` | Aerosol number concentration per cubic metre. |
| `log_w` | Continuation control coordinate. |
| `w_m_s` | Physical vertical velocity. |
| `log_n` | Log ice-number state coordinate when available. |
| `log_q` | Log ice-mass state coordinate when available. |
| `n` or `n_kg_dry_air_inv` | Physical ice crystal number concentration. |
| `q` or `q_kg_kg` | Physical ice crystal mass mixing ratio. |
| `s` | Saturation ratio. |
| `residual_norm` | Backend-normalized residual norm at the branch point. |
| `converged` | Whether LOCA/NOX reported convergence for the point. |
| `backend_step_index` | Original point order within the LOCA run. |
| `source_file` | Relative path to the raw or normalized source artifact. |

Recommended optional fields include LOCA step ids, continuation status, nonlinear iteration counts, linear iteration counts, step size, continuation parameter bounds, bifurcation/fold labels, row-scaling metadata, and solver tolerances.

## Expected curated artifacts

When implemented, Episode 4 should produce artifacts analogous to Episode 3:

- `outputs/figure1_loca_branches/branch_T190K.csv`, `branch_T210K.csv`, and `branch_T230K.csv` — normalized LOCA branch rows clipped to the requested Figure 1 velocity interval.
- `outputs/figure1_loca_branches/branches_all.csv` — combined normalized LOCA branch table.
- `outputs/figure1_loca_branches/run_metadata.json` — build, toolchain, solver, command, schema, and provenance metadata.
- `outputs/figure1_loca_backend_comparison/backend_comparison_details.csv` — pointwise LOCA-vs-Python, LOCA-vs-AUTO, LOCA-vs-Eq. 92--94, root-solve, and digitized-figure comparisons where inputs are available.
- `outputs/figure1_loca_backend_comparison/backend_comparison_summary.csv` and `.json` — per-variable and per-temperature error summaries.
- `outputs/figure1_loca_backend_comparison/figure1_backend_comparison.png` and `figure1_backend_residuals.png` — visual overlays and residual diagnostics that clearly distinguish LOCA, AUTO, Python, Eq. 92--94, and digitized paper curves.

## Comparison scope

LOCA should be compared first against the Episode 2 Python continuation because Python is the semantic reference. AUTO from Episode 3 is an independent backend cross-check. Eq. 92--94 approximations and digitized Figure 1 curves remain scientific reproduction benchmarks, but their tolerances are looser than solver-to-solver equivalence because the equations are approximations and digitization includes rendered-pixel uncertainty.

Backend-equivalence claims should distinguish:

1. residual/Jacobian equivalence between Python and C++ at fixed states;
2. schema and normalization invariants for LOCA outputs;
3. branch-level agreement between LOCA, Python, and AUTO on common or interpolated `log_w` grids;
4. agreement with analytic approximations and digitized paper curves as external reproduction checks.

The curated TASK-017 comparison implements these distinctions in `scripts/compare_loca_figure1.py`. LOCA is compared pointwise with Python and AUTO by interpolating those backend-neutral branches onto the LOCA `log_w` grid; Eq. 92--94 values are evaluated directly at LOCA branch points; independent Python root-solve and digitized paper checks are evaluated by interpolating LOCA onto their `w`/`log_w` samples. Solver-to-solver tolerances are expected to be near numerical-continuation precision, while analytic and digitized-paper tolerances should remain looser because they include approximation and digitization error.

## Shared versus episode-local infrastructure

The initial scaffold kept LOCA-specific source, CMake files, run configurations, generated outputs, logs, and notebooks under `episodes/004-figure1-loca-continuation/`. TASK-015 promotes only the reusable residual/Jacobian model core and its CMake build to top-level `loca/` because subsequent Episode 4 continuation and comparison tasks need the same C++/Trilinos executable. Episode-local run scripts, notebooks, generated outputs, logs, and curated artifacts still belong under `episodes/004-figure1-loca-continuation/` unless a later documented task promotes them as shared infrastructure.
