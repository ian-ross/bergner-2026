# TASK-069 evidence review and next-stage design

TASK-069 reviews the higher-order fixed-mesh, Python adaptive, and native adaptive-remesh evidence produced by TASK-064 through TASK-068. This is a scientific and implementation checkpoint, not a production Figure 5 artifact.

## Decision summary

The continuation approach is **promising but not yet sufficient for final Figure 5 production**.

Retained evidence supports the basic numerical direction: three-stage Gauss collocation, the external defect-driven `h/r` adaptive policy, sparse Tpetra/Thyra/NOX/KLU2 correction, native LOCA fixed-mesh ownership, nonuniform-remesh parity, and accepted-point Python/native parity. However, TASK-068 did not execute a full production native adaptive backend over the provisional skeleton. Its terminal ledger contains only six accepted targets and twenty-five explicit `failed` targets whose reason is that native adaptive remesh execution remains pending. Runtime and memory fields are deterministic zero placeholders. Near-Hopf approach points were not reached. Floquet, broader IVP/Radau validation, T=210 K linearized periods, final production schemas, and final interpolation/browser artifacts remain downstream work.

Therefore the approved next stage is a measured production-pipeline buildout and pilot, with explicit gaps where evidence is missing. No unresolved region may be filled by undocumented interpolation.

## Frozen review inputs

The review used the following authoritative artifacts and documentation.

| Evidence | Path |
| --- | --- |
| Fixed higher-order qualification | [`../outputs/higher_order_fixed_mesh_qualification.json`](../outputs/higher_order_fixed_mesh_qualification.json) |
| C++ higher-order correction/parity | [`../outputs/cpp_higher_order_correction_results.json`](../outputs/cpp_higher_order_correction_results.json) |
| Native higher-order fixed-mesh LOCA | [`../outputs/native_loca_higher_order_results.json`](../outputs/native_loca_higher_order_results.json) |
| Python adaptive qualification | [`../outputs/adaptive_qualification_results.json`](../outputs/adaptive_qualification_results.json) |
| C++ nonuniform adaptive parity fixtures | [`../outputs/cpp_adaptive_nonuniform_fixtures/manifest.json`](../outputs/cpp_adaptive_nonuniform_fixtures/manifest.json) |
| Native adaptive restart smoke | [`../outputs/native_adaptive_restart_smoke.json`](../outputs/native_adaptive_restart_smoke.json) |
| One integrated native remesh/restart boundary | [`../outputs/native_adaptive_one_branch_segment.json`](../outputs/native_adaptive_one_branch_segment.json) |
| Provisional spine-and-slices target ledger | [`../outputs/native_adaptive_spine_slices_run.json`](../outputs/native_adaptive_spine_slices_run.json) |
| Independent Python validation ledger | [`../outputs/native_adaptive_python_validation.json`](../outputs/native_adaptive_python_validation.json) |
| TASK-068 sink reconciliation | [`../outputs/native_adaptive_final_reconciliation.json`](../outputs/native_adaptive_final_reconciliation.json) |
| TASK-068 final evidence note | [`task068-final-evidence-reconciliation.md`](task068-final-evidence-reconciliation.md) |
| v1 design record | [`collocation-phase-decisions.md`](collocation-phase-decisions.md) |

The TASK-068 sink manifest records these input hashes for the principal post-TASK-067 evidence artifacts:

| Input artifact | Path | Schema | SHA-256 prefix | Role |
| --- | --- | --- | --- | --- |
| `native_adaptive_loca_manifest` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_loca_manifest.json` | `episode008-native-adaptive-loca-manifest-v1` | `8844e8212db4...` | structural remesh/restart and preparatory evidence ledger |
| `native_adaptive_restart_smoke` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_restart_smoke.json` | `episode008-native-adaptive-restart-smoke-v1` | `59aedaa2ab75...` | native controller/restart seam smoke evidence |
| `native_adaptive_one_branch_segment` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_one_branch_segment.json` | `episode008-native-adaptive-one-branch-segment-v1` | `0c3d60b71391...` | integrated one-branch accepted remesh/restart slice |
| `native_adaptive_spine_slices_summary` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_spine_slices_run.json` | `episode008-native-adaptive-spine-slices-run-v1` | `b8e2130d834e...` | provisional driver-run summary |
| `native_adaptive_spine_slices_run_manifest` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_spine_slices_run/manifest.json` | `episode008-native-adaptive-driver-v1` | `1a3b149a217e...` | resumable driver run manifest |
| `native_adaptive_python_validation` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_python_validation.json` | `episode008-native-adaptive-python-validation-v1` | `2ce350c4de17...` | independent same-coordinate Python validation |
| `cpp_adaptive_nonuniform_fixture_manifest` | `episodes/008-figure5-periodic-orbit-continuation/outputs/cpp_adaptive_nonuniform_fixtures/manifest.json` | `episode008-cpp-adaptive-nonuniform-fixtures-v1` | `f0325eaafd74...` | C++ nonuniform parity fixture manifest |
| `native_loca_higher_order_results` | `episodes/008-figure5-periodic-orbit-continuation/outputs/native_loca_higher_order_results.json` | `episode8-native-loca-higher-order-v1` | `1d98f8bc2872...` | native fixed-mesh LOCA input evidence |

## Evidence synthesis

### Fixed-order and fixed-mesh evidence

The fixed-uniform higher-order study accepts most finite-dimensional nonlinear systems but does not qualify fixed uniform meshes for production. In [`higher_order_fixed_mesh_qualification.json`](../outputs/higher_order_fixed_mesh_qualification.json), 20 cases pass nonlinear residual gates and one coarse canonical three-stage case is explicitly rejected, but the summary reports `fixed_uniform_mesh_qualified: false` and `qualified_case_count: 0`.

Representative fixed-order results:

| Case | Accepted | Period (s) | Max independent defect | Same-rule conclusion |
| --- | ---: | ---: | ---: | --- |
| canonical two-stage N=64 | yes | 2466.547840 | 6.47e-2 | N=64 -> 128 misses period/orbit gates |
| canonical two-stage N=128 | yes | 2461.910675 | 1.95e-2 | diagnostic order check only |
| canonical three-stage N=32 | yes | 2450.318212 | 4.68e-2 | N=32 -> 64 misses period/orbit gates |
| canonical three-stage N=64 | yes | 2461.617474 | 7.38e-3 | best fixed-uniform defect still above 1e-4 |
| T=210, rho=0 three-stage N=64 | yes | 5719.219759 | 1.58e-2 | guard pair misses gates |
| T=210, rho=-0.15 three-stage N=64 | yes | 6183.936613 | 1.00e-2 | guard pair misses gates |
| T=210, rho=+0.15 three-stage N=64 | yes | 5111.770986 | 1.73e-2 | guard pair misses gates |

The canonical best three-stage N=64 orbit has encouraging independent IVP evidence: collocation period `2461.6174737825213 s`, DOP853-derived period `2461.617091943471 s`, relative period difference `1.55e-7`, and phase-aligned weighted dense-orbit error `2.39e-5`. This validates the formulation at that point but does not override fixed-uniform defect/refinement failures.

### Python adaptive convergence, defects, mesh concentration, and aliasing

[`adaptive_qualification_results.json`](../outputs/adaptive_qualification_results.json) shows that the external three-stage Gauss `h/r` reference solves all four qualification points from N=32 starts. Final interval counts are 72, 75, 81, and 75. Final maximum independent defects are below the v1 `1e-4` gate:

| Case | Final N | Final max defect | Final period (s) | Terminal status | Aliasing |
| --- | ---: | ---: | ---: | --- | --- |
| canonical-g3-n32 | 72 | 8.05e-5 | 2461.604468 | converged | no persistent aliasing |
| guard-rho-0-g3-n32 | 75 | 6.53e-5 | 5718.140412 | converged | no persistent aliasing |
| guard-rho-minus-0.15-g3-n32 | 81 | 5.12e-5 | 6183.898590 | converged | one persistent adjacent-bin diagnostic, converged despite it |
| guard-rho-plus-0.15-g3-n32 | 75 | 7.32e-5 | 5109.345769 | converged | no persistent aliasing |

The one aliasing diagnostic is evidence to retain aliasing channels, not evidence that landmark alignment is currently required: targeted `h/r` refinement converged without snapping or local `hp` machinery.

### Transfer, restart, Python/native parity, and native continuation coverage

Native fixed-mesh higher-order LOCA is strong machinery evidence. [`native_loca_higher_order_results.json`](../outputs/native_loca_higher_order_results.json) records five required three-stage N=32 branches, exact target landings, two controlled phase-reference rebuilds, 32 accepted native points, and maximum all-point Python/native differences of `1.58e-12` relative in period and `2.83e-12` in the weighted orbit metric, far below the `2e-7` tolerance.

The TASK-068 native adaptive evidence validates structural seams but not the full production run:

- [`cpp_adaptive_nonuniform_fixtures/manifest.json`](../outputs/cpp_adaptive_nonuniform_fixtures/manifest.json) covers nonuniform residual, Jacobian, parameter-column, phase quadrature, metric, transfer, controller, and fixed-parameter correction parity for the four final adaptive qualification meshes.
- [`native_adaptive_restart_smoke.json`](../outputs/native_adaptive_restart_smoke.json) records native controller/restart seam smoke evidence for all projected fixtures and representative h+r corrections.
- [`native_adaptive_one_branch_segment.json`](../outputs/native_adaptive_one_branch_segment.json) records one accepted integrated remesh/restart boundary on the spine-negative-to-210 segment. Its restart passes residual, phase, positivity, finite-change, KLU2/linear, and tangent gates.
- [`native_adaptive_python_validation.json`](../outputs/native_adaptive_python_validation.json) validates 32 selected accepted fixed-mesh native points by independent Python correction, with the same maximum period/orbit errors as the fixed-mesh native artifact. The post-remesh restart is correctly recorded separately and is not rebranded as independent Python validation.

The provisional driver ledger in [`native_adaptive_spine_slices_run.json`](../outputs/native_adaptive_spine_slices_run.json) has exactly one terminal status for each target: six `accepted`, twenty-five `failed`, zero `resolution_unresolved`, zero `near_hopf_stop`, and zero `tripwire_stop`. The failed targets all preserve the reason `native_adaptive_remesh_run_pending; fixed-mesh/native or Python-adaptive evidence is not relabeled`. This is correct evidence hygiene and a blocker for final Figure 5 coverage.

### Near-Hopf behavior and fits

TASK-068 did not reach near-Hopf approach points. The sink reconciliation records `approach_point_count: 0`, an empty approach-point list, and status `not_reached_in_provisional_run`. Therefore the documented quadratic and quartic fits,

```text
P = P0 + c2 A^2
P = P0 + c2 A^2 + c4 A^4
```

are **not supported by current evidence**. There are no reliable monotone approach points, no amplitude span, no leave-one-out intercepts, and no justified comparison to Episode 006 Hopf periods. The current downstream policy is an explicit gap until a later task obtains enough approach evidence or records stop reasons that justify preserving a gap.

### Rejection, unresolved modes, and tripwires

No tripwire or near-Hopf terminal status is observed in the provisional run. The driver and final reconciliation do preserve channels for cap escalation, aliasing, Radau-trigger evidence, single-valued tripwires, rejection reasons, interruption/resume, stale checkpoint rejection, and `not_evaluated` IVP/Floquet evidence. The important unresolved mode is not a numerical failure hidden by interpolation; it is an explicit pending native adaptive execution boundary for 25 targets.

### Runtime, memory, and linear solver evidence

Runtime and memory evidence was insufficient for TASK-069 production policy because TASK-068 artifacts recorded executable/source/runtime identities but kept provisional `segment_wall_clock_s`, `segment_cpu_s`, and `max_rss_kib` as deterministic zero placeholders. TASK-071 supersedes those placeholder policy fields for the current pilot seams with [`native_adaptive_resource_profile.json`](../outputs/native_adaptive_resource_profile.json) and production-v1 companion metadata in [`native_adaptive_resource_profile_run_metadata.json`](../outputs/native_adaptive_resource_profile_run_metadata.json). The TASK-071 profile records measured wall-clock time, CPU time, max RSS, nonlinear iterations, KLU2 symbolic/numeric factorization counts, linear solves, and source/build/runtime identity for representative fixed-mesh, remesh/restart, and pilot-style native adaptive seams. It remains cost evidence only, not scientific acceptance of the unresolved continuation targets. Its review keeps serial KLU2 acceptable for the current pilot seams; documented iterative-solver thresholds are not met by the available measured evidence, while backend-unexposed factorization/solve timing split channels remain explicitly not evaluated.

### Paper Figure 5 digitization

TASK-063 is still `To Do`, so there is no digitized Figure 5 dataset available for this review. The comparison is deferred. When available, it must remain image-derived external evidence only and must not override convergence, defect, Python/native parity, or independent IVP evidence. The discrepancy rule from TASK-062 remains: investigate differences when `|Delta log(P)| > max(3*sigma_digitized_logP, 0.02)`.

## TASK-062 v1 hypothesis disposition matrix

| TASK-062 v1 hypothesis or downstream option | Disposition | Evidence and method-version decision |
| --- | --- | --- |
| Three-stage Gauss as primary collocation family | Retain | Fixed-uniform defects show the need for adaptivity, but Python adaptive three-stage converges at all four qualification points and native fixed-mesh parity is excellent. Retain method family as `external-gauss3-hr-adaptive-v1`; no method-version change. |
| Two-stage Gauss order check | Retain as diagnostic | Two-stage fixed ladders expose order/refinement behavior; not a production method. No method-version change. |
| Fixed uniform meshes as possible production data | Revise/reject | Zero fixed-uniform cases qualify; defects remain above `1e-4`. Fixed uniform data remain fixtures/diagnostics only. Production records must require adaptive evidence. |
| Independent two-grid defect, material disagreement, 16-point probe, and 128-bin recurrence | Retain | Adaptive qualification uses this gate and converges; one aliasing diagnostic is preserved. No loosening. |
| `1e-4` defect and `1e-3` period/orbit convergence gates | Retain for production candidates | Python adaptive evidence passes at four points. Full native adaptive production has not yet been run, so gates remain required rather than waived. |
| Defect-driven h marking and 50% growth cap | Retain | Final N<=81 and no soft cap escalation; no evidence for coarsening or alternate marking. |
| Composite r monitor weights and bounded global-beta movement | Retain provisionally | Meshes converge without pathological movement; no evidence supports changing weights. Reassess only if measured production run stalls or aliases persist. |
| No v1 coarsening | Retain | No N=256/512 pressure or overresolved-cost evidence. Coarsening is not warranted now. |
| No v1 landmark snapping/alignment | Retain, with trigger channel | One persistent aliasing diagnostic converged. Landmark alignment is not warranted unless same-region aliasing or convergence stagnation blocks production. |
| No local hp adaptation | Retain | h/r with fixed three-stage order succeeds on qualification points; no evidence that local order variation is needed. |
| Remesh/restart retry order and gates | Retain | Fixture parity, restart smoke, and one integrated remesh/restart pass the documented gates. No method-version change. |
| Phase refresh triggers and full-stack rebuild semantics | Retain | Native fixed-mesh runs and one remesh boundary record controlled refresh/rebuild lineage. No evidence supports mutation inside a segment. |
| Near-Hopf stopping and quadratic/quartic fit policy | Defer, retain policy as unevaluated | No near-Hopf approach points. Fits are not performed. Later tasks must either acquire at least five reliable approach points or preserve explicit gaps. |
| Radau whole-orbit collocation comparison | Not warranted now; defer trigger-only | Evaluated evidence does not show defect-passing/Gauss-failing production points, persistent ringing/nonphysical values, or mesh-cap stagnation. Broader IVP/Radau validation remains downstream for selected difficult points, not a replacement method. |
| Floquet postprocessing and gates | Defer but approve downstream implementation | Floquet is not evaluated through TASK-068. It is warranted downstream as postprocessing/diagnostic evidence for production records, not as a TASK-068 acceptance gate. |
| Serial KLU2 direct solver | Retain after TASK-071 pilot-seam profiling | TASK-071 records measured current-seam wall-clock, CPU, RSS, nonlinear-iteration, KLU2 factorization, and solve evidence. The available measured evidence does not meet documented iterative-solver triggers; KLU2 remains oracle/reference pending larger production profiling. |
| Single-valued tripwire and multibranch confirmation | Retain tripwire only; multibranch not warranted now | No tripwire observed. Confirmation/display machinery should be created only after a real trigger. |
| Provisional sampling/interpolation skeleton | Revise | Keep solved target ideas, but interpolation is blocked until a real native adaptive production run supplies accepted or explicit unresolved statuses and holdout tests. Never interpolate across pending/failed targets. |
| TASK-063 paper digitization comparison | Deferred | TASK-063 is not complete. Future comparison is external image-derived evidence only. |
| Broader independent IVP validation | Approve downstream selected validation | TASK-064 canonical IVP evidence is strong, but broader IVP evidence is not evaluated. A selected production-validation task is justified after accepted native adaptive points exist. |
| T=210 K linearized-period curve | Approve downstream implementation | Required for lower Figure 5 panel and independent of periodic-orbit continuation. Not yet implemented. |
| Formal production schemas and curated-vector retention | Approve downstream implementation | Needed before production artifacts, but exact records can now be based on observed evidence categories and explicit-gap policy. |

## Sufficiency for remaining Figure 5 work

Current evidence is sufficient to justify **continued development of the native adaptive Figure 5 pipeline**, not sufficient to publish or browser-display final Figure 5 data.

Scientific/numerical blockers before final Figure 5 production:

1. The full native adaptive backend has not accepted or explicitly resolved the 25 pending provisional targets.
2. Full-domain production runtime and linear-algebra timing split evidence remains absent; TASK-071 has replaced the prior pilot-seam zero placeholders with measured current-seam resource/counter evidence only.
3. Near-Hopf approach evidence is absent, so nonlinear-period/Hopf-limit connection is unresolved.
4. Floquet and broader IVP validation are not evaluated for production accepted points.
5. The T=210 K equilibrium-linearized period curve is absent.
6. Formal production schemas, holdout-tested interpolation, and browser/paper artifacts are absent.
7. TASK-063 paper digitization is unavailable.

None of these blockers permits interpolation across failed or pending ledger entries. Any display artifact must carry solved/interpolated/invalid/gap provenance and must not treat digitized pixels as numerical ground truth.

## Next-stage design decisions

The next stage should be created as atomic tasks depending on TASK-069. The justified scope is:

1. Freeze formal `episode8-figure5-production-v1` schemas and validators before producing new production data.
2. Measure native adaptive runtime/resource costs with real wall-clock, CPU, RSS, nonlinear iteration, KLU2 factorization/solve counters, and source/build identity.
3. Execute a real native adaptive pilot over the observed 210--226 K skeleton, replacing pending targets with accepted/unresolved/near-Hopf/tripwire/failed statuses.
4. Validate accepted native adaptive points with independent same-coordinate Python corrections and selected IVP checks. Use IVP Radau only for difficult/headline or triggered cases.
5. Acquire near-Hopf approach evidence where reachable; perform the quadratic/quartic fit review only after sufficient points exist, otherwise preserve explicit gaps.
6. Implement Floquet postprocessing for saved native collocation orbits as downstream diagnostics.
7. Generate the independent T=210 K equilibrium-linearized period curve.
8. Only after the pilot review, execute full-domain native adaptive continuation and canonical sampling/holdout refinement across the Figure 5 domain.
9. Produce final interpolation, paper-comparison, plot, and browser-facing artifacts from authoritative solved points plus explicit Hopf-limit and invalid/gap records.

Downstream tasks created from this review are recorded in the section below after Backlog CLI creation.

## Downstream task graph created from TASK-069

The following tasks were created through the Backlog CLI after the decisions above were documented. Each task depends on TASK-069 and has no creation-time implementation plan.

| Task | Scope | Additional dependency intent |
| --- | --- | --- |
| TASK-070 | Define Episode 008 production schemas and validators | Root schema gate for all production artifacts |
| TASK-071 | Profile native adaptive continuation resource usage | Depends on TASK-070; replaces TASK-068 placeholder cost fields |
| TASK-072 | Run measured native adaptive pilot on 210--226 K skeleton | Depends on TASK-070 and TASK-071; resolves the observed provisional skeleton before full-domain work |
| TASK-073 | Reconcile native adaptive pilot with independent validation | Depends on TASK-070 and TASK-072; gate before full-domain continuation |
| TASK-074 | Generate T=210 K linearized-period curve | Depends on TASK-070; independent lower-panel equilibrium/eigenvalue artifact |
| TASK-075 | Execute full-domain native adaptive continuation and sampling refinement | Depends on TASK-070, TASK-071, and TASK-073; authoritative production continuation |
| TASK-076 | Acquire near-Hopf approach evidence and decide gap policy | Depends on TASK-070 and TASK-075; performs fits only where prerequisites are met |
| TASK-077 | Implement Floquet postprocessing for native production orbits | Depends on TASK-070 and TASK-075; downstream diagnostics, not nonlinear unknowns |
| TASK-078 | Run stratified independent IVP validation for production points | Depends on TASK-070, TASK-075, and TASK-077; selected DOP853/Radau/attractor validation |
| TASK-079 | Build Figure 5 interpolation and browser dataset artifact | Depends on TASK-070, TASK-074, TASK-075, TASK-076, TASK-077, and TASK-078 |
| TASK-080 | Produce final Figure 5 paper comparison and browser-ready artifacts | Depends on TASK-063, TASK-070, TASK-074, and TASK-079; paper comparison remains image-derived |

## Independent review notes

Two independent read-only reviews were run during TASK-069. Both agreed that the method is structurally promising but not production-sufficient, that near-Hopf fits are unsupported by current evidence, that runtime/memory placeholders are a blocker, that TASK-063 comparison must be deferred, and that Radau-collocation/coarsening/local-hp/landmark/iterative/multibranch machinery is not automatically warranted by the current evidence.
