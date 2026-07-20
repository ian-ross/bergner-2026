import json
from pathlib import Path

import nbformat
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/007-limit-cycle-interactive-widget"
NOTEBOOK = EPISODE_ROOT / "notebooks/01_limit_cycle_diagnostics.ipynb"
OUTPUTS = EPISODE_ROOT / "outputs"


def test_episode7_diagnostics_notebook_records_the_required_solver_and_process_contract():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")

    for required_source in (
        "Environment(p=30000.0, T=225.0, w=0.1, F=1.0, N_a=1.0e10, Δz=100.0, include_evaporation=False)",
        "method='RK45'",
        "horizon_periods = 300",
        "'paper_0.99': 0.99 * x_eq",
        "'n_plus_1pct'",
        "'q_plus_1pct'",
        "'s_plus_1pct'",
        "analyze_late_cycle_drift",
        "phase_independent_orbit_distance",
        "'Nuc_n', 'Sed_n'",
        "'Nuc_q', 'Dep_q', 'Sed_q'",
        "'Cool', 'Nuc_s', 'Dep_s'",
        "float_format='%.17g'",
    ):
        assert required_source in source


def test_episode7_reference_outputs_satisfy_the_browser_validation_contract():
    for filename in (
        "limit_cycle_stability.png",
        "attractor_convergence_log10n_s.png",
        "one_cycle_state_process_budgets.png",
        "reference_trajectory.csv",
        "per_cycle_summary.csv",
        "reference_metadata.json",
    ):
        artifact = OUTPUTS / filename
        assert artifact.is_file()
        assert artifact.stat().st_size > 0

    metadata = json.loads((OUTPUTS / "reference_metadata.json").read_text(encoding="utf-8"))
    assert metadata["schema_version"] == "1.0.0"
    assert metadata["canonical_parameters"] == {
        "T": 225.0,
        "p": 30000.0,
        "w": 0.1,
        "F": 1.0,
        "N_a": 1.0e10,
        "Delta_z": 100.0,
        "include_evaporation": False,
    }
    assert metadata["solver_settings"]["coordinates"] == ["log(n)", "log(q)", "s"]
    assert metadata["integration_horizon"]["periods"] == 300
    assert metadata["convergence"]["passed"] is True
    assert metadata["convergence"]["final_window_cycles"] == 20
    assert all(item["passed"] for item in metadata["convergence"]["per_start"].values())
    assert all(item["distance"] <= 1e-3 for item in metadata["convergence"]["orbit_distances"].values())
    assert metadata["orbit_metric"]["states"] == ["n", "q", "s"]

    reference = pd.read_csv(OUTPUTS / "reference_trajectory.csv")
    summary = pd.read_csv(OUTPUTS / "per_cycle_summary.csv")
    assert list(reference.columns) == ["time_s", "n_kg_dry_air_minus1", "q_kg_kg_dry_air_minus1", "s"]
    assert reference["time_s"].iloc[0] == 0.0
    paper_summary = summary.loc[summary["start"] == "paper_0.99"]
    assert reference["time_s"].max() <= paper_summary["end_time_s"].max()
    assert reference["time_s"].max() == paper_summary["end_time_s"].iloc[-1]
    assert {"start", "cycle_index", "period_s", "s_max", "s_min", "s_amplitude", "period_relative_drift", "amplitude_relative_drift"}.issubset(summary.columns)
    assert set(summary["start"]) == {"paper_0.99", "n_plus_1pct", "q_plus_1pct", "s_plus_1pct"}
