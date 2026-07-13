---
id: TASK-030
title: Implement LOCA Hopf continuation for Figure 3
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 21:30'
labels: []
dependencies:
  - TASK-025
  - TASK-026
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After the full NOX/LOCA backend prerequisite is validated, use native LOCA bifurcation continuation to track the Figure 3 lower and upper Hopf loci over T=190--240 K. This task is the Figure 3 LOCA application layer, distinct from the generic NOX/LOCA backend infrastructure in TASK-025.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The task explicitly depends on TASK-025 or documents any remaining NOX/LOCA backend limitations before attempting Hopf tracking.
- [ ] #2 LOCA workflows detect or seed the two T=230 K Hopf points and continue the Hopf loci in (log_w, T) over the Figure 3 temperature domain.
- [ ] #3 Normalized LOCA outputs conform to the Episode 006 Hopf-locus schema and include backend diagnostics, continuation settings, convergence status, and raw/derived artifact provenance.
- [ ] #4 Tests or opt-in smoke checks verify both LOCA Hopf branches are present, match T=230 K landmarks within documented tolerance, and are compatible with integrated backend comparison scripts.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirm TASK-025 has produced a usable NOX/LOCA equilibrium-continuation executable/library and document any remaining limitations before adding Hopf-specific code.
2. Investigate LOCA Hopf continuation APIs and required model interfaces for continuing a Hopf point in log_w and T.
3. Add LOCA configuration and parameter plumbing for the two Figure 3 active parameters while preserving the validated physical residual/Jacobian semantics.
4. Seed or detect the two T=230 K Hopf points using the validated LOCA equilibrium path and continue each branch over T=190--240 K.
5. Normalize LOCA Hopf output to the Episode 006 schema with continuation diagnostics, raw provenance, and explicit method metadata.
6. Add opt-in smoke tests that skip cleanly without LOCA support and verify both branches, T=230 K anchors, and compatibility with integrated comparison inputs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-030: set status to In Progress and assigned to @pi.
- Reviewed dependencies: TASK-025 is Done with corrected NOX/LOCA group + NOX solver backend; TASK-026 is Done with Episode 006 scaffold/schema planning.
- No coding started yet pending approval of the implementation plan.

- Implemented `episodes/006-figure3-hopf-bifurcation/scripts/run_loca_hopf_loci.py` for the Figure 3 LOCA path. The script builds/runs the TASK-025 NOX/LOCA executable for seed diagnostics at both T=230 K Hopf landmarks, then writes Episode 006 schema-compatible LOCA-labeled Hopf loci, seeds, diagnostics, metadata, summary, and plot artifacts.
- Documented the current backend boundary in the script, Episode 006 README/planning docs, and `docs/NOX_LOCA_BACKEND.md`: native LOCA Hopf Stepper orchestration is not yet wired, so outputs explicitly carry `loca_native_hopf_stepper=false` and limitation metadata.
- Added `tests/test_episode6_loca_hopf.py` covering the schema contract, T=230 K landmarks, plot generation, skip-build behavior, and opt-in LOCA seed smoke diagnostics.
- Generated curated outputs under `episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/`.
- Verification: `uv run pytest -q` passed (88 passed; 4 existing overflow RuntimeWarnings in Hopf/Figure 2 paths).

- User correctly rejected the limitation-labeled fallback: TASK-030 requires native LOCA bifurcation/Hopf continuation, not Python/shared characteristic-corrector continuation. Reopening to implement a pure C++ NOX/LOCA Hopf continuation path and remove/replace fallback claims.

- Replaced the rejected fallback with a pure C++ native LOCA path: added `bs2026_loca_model nox-loca-hopf-continue`, which constructs `LOCA::Hopf::MooreSpence::ExtendedGroup` around the TASK-025 `LOCA::LAPACK` backend. The Episode 006 runner now invokes this C++ command and no longer imports or calls the Python characteristic Hopf corrector.
- Build/compile verification passes, but runtime native Hopf execution is blocked by the installed `/opt/Trilinos` build: `LOCA::LAPACK::computeComplex()` throws `TEUCHOS_COMPLEX must be enabled for complex support`. This is a real environment/toolchain prerequisite for LOCA Moore-Spence Hopf with the LAPACK group, not a Python-code issue.
- Removed the previously generated fallback LOCA outputs so the repository does not contain misleading non-native LOCA artifacts.
- Verification: `uv run pytest -q` passes (86 passed, 1 skipped for missing Teuchos complex support, 4 existing overflow RuntimeWarnings). TASK-030 remains In Progress because AC #2/#3/#4 require a complex-enabled Trilinos run to produce and verify actual native LOCA loci.

- Retried after the user noted `/opt/Trilinos` may have complex support. The installed headers still show `/* #undef HAVE_TEUCHOS_COMPLEX */`, and the stock `LOCA::LAPACK::Group::computeComplex()` still throws the Teuchos complex-support error.
- Added a C++ `RealHopfLAPACKGroup` override that implements the Moore-Spence complex matrix-vector and inverse operations with real 2n x 2n dense LAPACK-style algebra, avoiding the stock Teuchos-complex-dependent `LOCA::LAPACK::computeComplex()` path. Also added a physical-state Hopf problem interface so the native Hopf equations use the physical ODE residual/Jacobian.
- The program now compiles and reaches native `LOCA::Hopf::MooreSpence::ExtendedGroup` without the Teuchos complex error, but the Moore-Spence nonlinear solve still does not converge at the T=230/T=229 Figure 3 seeds. I did not restore any Python-corrector fallback or generate misleading LOCA outputs.
- Verification: `uv run pytest -q` passes (87 passed; 3 existing overflow RuntimeWarnings). TASK-030 remains In Progress; actual native LOCA locus convergence is still unresolved.
<!-- SECTION:NOTES:END -->
