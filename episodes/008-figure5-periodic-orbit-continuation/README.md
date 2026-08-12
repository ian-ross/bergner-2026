# Episode 008: Figure 5 periodic-orbit continuation

Goal: reproduce both panels of Bergner & Spichtinger (2026) Figure 5 by performing genuine continuation of periodic orbits with collocation, first in Python and then with NOX/LOCA in Trilinos.

This episode follows the conservative prototype-to-Trilinos path documented in the periodic-orbit continuation learning material: begin with implicit midpoint collocation on a fixed mesh, establish layout/residual/Jacobian and continuation parity, then add higher-order fixed-mesh collocation and adaptive remeshing before producing the final period map.

## Current documentation

- [`docs/collocation-phase-decisions.md`](docs/collocation-phase-decisions.md) records the binding decisions and unresolved questions for the initial collocation phase.

## Frozen Episode 007 bootstrap seed

[`outputs/bootstrap_seed.json`](outputs/bootstrap_seed.json) freezes the final complete `paper_0.99` saturation-maximum-to-maximum cycle from the committed Episode 007 reference trajectory. It contains normalized phase knots, `(log(n), log(q), s)`, `log(P)`, transformed model-field phase slopes, canonical parameters, source checksums, and extraction provenance. The reusable [`PeriodicHermiteSeed`](../../src/bergner_spichtinger_2026/periodic_seed.py) loader and cubic-Hermite evaluator can sample arbitrary endpoint or collocation-stage phases without rerunning the roughly 300-period IVP. The standalone [`scripts/generate_bootstrap_seed.py`](scripts/generate_bootstrap_seed.py) remains responsible only for Episode 007 extraction, provenance, deterministic serialization, and its CLI.

Regenerate the artifact or verify that it is current with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_bootstrap_seed.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_bootstrap_seed.py --check
```

The generator records that the final cycle's first event time is present in Episode 007 metadata but is bracketed rather than stored as an exact trajectory row. It therefore verifies source-cycle closure and reuses the terminal saturation-maximum event state at both periodic endpoints. Downstream Python code can load and verify the language-neutral artifact without importing an episode script:

```python
from bergner_spichtinger_2026.periodic_seed import PeriodicHermiteSeed

seed = PeriodicHermiteSeed.from_json(seed_path, verify_upstream_root=repo_root)
states = seed.evaluate(endpoint_or_stage_phases)
```

## Scope boundary

The episode will produce a schema-versioned browser-consumable Figure 5 dataset, but integrating that dataset into the Episode 007 web widget is deferred to follow-up work.
