# Episode 007: limit-cycle interactive widget

Goal: establish the scientific and browser contracts for a reproducible long-integration investigation of the Bergner & Spichtinger (2026) Figure 4 center-case limit cycle, then provide a fully client-side interactive widget. This scaffold deliberately contains no generated trajectories, figures, reference fixtures, or web build output yet.

## Contents

- `docs/planning-decisions.md` — binding scientific, numerical, reference-data, and browser-architecture decisions for this episode.
- `notebooks/` — placeholder for the authoritative clean-run long-integration diagnostics notebook.
- `web/` — placeholder for the static vanilla TypeScript/Vite/locally bundled Plotly application.
- `outputs/` — placeholder for curated figures and Python-generated browser-validation fixtures.

Empty directories are retained with `.gitkeep` placeholders until their follow-on work produces concrete artifacts.

## Intended workflow (not implemented by this scaffold)

The following are the intended commands after the corresponding notebook and web tasks add their source files and dependencies. They are documentation of the planned interface, not claims that an output currently exists or that these commands can yet succeed.

From the repository root, the notebook rerun is intended to be:

```bash
uv run jupyter execute episodes/007-limit-cycle-interactive-widget/notebooks/01_limit_cycle_diagnostics.ipynb --inplace
```

The browser application is intended to install, test, and build from its episode-local directory:

```bash
cd episodes/007-limit-cycle-interactive-widget/web
npm ci
npm test
npm run build
```

After a production build, it is intended to be served as static files (for example):

```bash
cd episodes/007-limit-cycle-interactive-widget/web
npm run preview
```

The completed widget will require no server-side model, Python process, notebook kernel, CDN, or network runtime dependency.

## Cross-episode dependencies

- `src/bergner_spichtinger_2026/` remains the Python semantic reference for the no-evaporation model, equilibrium, and reference-data generation.
- `episodes/001-figure4-time-series/` supplies Figure 4 provenance and the initial qualitative-reproduction context.
- `episodes/005-figure2-eigenvalues/` supplies stability/eigenvalue context for estimating the linearized oscillation period.
- `docs/PHASE2_IMPLEMENTATION.md`, `docs/REPRODUCTION_NOTES.md`, and `docs/testing.md` record shared model semantics, high-aerosol provenance, and tested physical domains.

Keep Episode 007 notebooks, web sources, generated fixtures, figures, and build outputs under this directory. Only reusable model infrastructure belongs in `src/bergner_spichtinger_2026/`.
