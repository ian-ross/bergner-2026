from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SCRIPTS = EPISODE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_native_adaptive_floquet_diagnostics import multiplier_classification  # noqa: E402

SUMMARY = EPISODE / "outputs/native_adaptive_floquet_diagnostics.json"
GENERATOR = SCRIPTS / "generate_native_adaptive_floquet_diagnostics.py"
DOC = EPISODE / "docs/task077-floquet-postprocessing.md"
README = EPISODE / "README.md"
POINTS = EPISODE / "outputs/native_adaptive_full_domain_points.json"
EVENTS = EPISODE / "outputs/native_adaptive_full_domain_events.json"
ORBIT_MANIFEST = EPISODE / "outputs/native_adaptive_full_domain_orbit_manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(SUMMARY.read_text())


def test_task077_generator_is_current_and_upstream_artifacts_validate() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(SCRIPTS / "validate_production_artifacts.py"),
            str(POINTS),
            str(EVENTS),
            str(ORBIT_MANIFEST),
        ],
        cwd=ROOT,
        check=True,
    )


def test_task077_dop853_variational_ladder_records_multipliers_and_classification() -> None:
    row = load()["floquet_diagnostics"][0]
    assert row["target_id"] == "spine-210K"
    assert row["postprocessing_boundary"] == {
        "base_orbit_source": "saved native collocation polynomial from TASK-075 accepted production point",
        "not_a_continuation_acceptance_gate": True,
        "not_a_nonlinear_unknown": True,
        "not_task068_acceptance_evidence": True,
    }
    integrations = row["dop853_variational_integrations"]
    assert [item["name"] for item in integrations] == ["dop853_coarse", "dop853_production", "dop853_refined"]
    assert all(item["success"] for item in integrations)
    assert all(len(item["multipliers"]) == 3 for item in integrations)
    assert all(len(item["monodromy_matrix"]) == 3 for item in integrations)
    refinement = row["dop853_tolerance_refinement"]
    assert refinement["all_comparisons_pass"] is True
    assert len(refinement["comparisons"]) == 2
    assert all(item["max_abs_multiplier_delta"] < item["tolerance"] for item in refinement["comparisons"])
    classification = row["production_multiplier_classification"]
    assert classification["trivial_gate_pass"] is True
    assert classification["trivial_distance_from_one"] < 1.0e-4
    assert classification["max_nontrivial_modulus"] < 1.0
    assert classification["stability_classification"] == "orbitally_stable_autonomous_trivial_multiplier"
    assert classification["stable"] is True
    assert classification["ambiguous"] is False


def test_task077_radau_comparison_runs_and_records_unavailable_difficult_strata() -> None:
    data = load()
    row = data["floquet_diagnostics"][0]
    radau = row["radau_comparison"]
    assert radau["selection_status"] == "run"
    assert "canonical_accepted_production_point" in radau["selection_reasons"]
    assert radau["result"]["success"] is True
    assert radau["result"]["solver"]["method"] == "Radau"
    assert radau["max_abs_multiplier_delta_vs_dop853_production"] < radau["comparison_tolerance"]
    assert radau["comparison_gate_pass"] is True
    summary = data["radau_comparison_summary"]
    assert summary["radau_run_target_ids"] == ["spine-210K"]
    by_stratum = {item["stratum"]: item for item in summary["stratified_difficult_points"]}
    assert by_stratum["canonical accepted regular production point"]["status"] == "run"
    assert by_stratum["near-Hopf or long-period accepted approach point"]["status"] == "not_available_no_schema_valid_accepted_near_hopf_points"
    assert by_stratum["suspected nontrivial unit-circle crossing"]["status"] == "not_available_no_nontrivial_crossing_candidate_detected"
    assert summary["ambiguous_or_unstable_classifications_recorded_not_suppressed"] is True


def test_task077_links_to_continuation_records_and_does_not_relabel_non_orbits() -> None:
    data = load()
    assert data["input_validation"] == {
        "accepted_only_processing": True,
        "continuation_events_schema_valid": True,
        "continuation_points_schema_valid": True,
        "orbit_manifest_schema_valid": True,
        "production_schema_version": "episode8-figure5-production-v1",
        "schema_valid_accepted_point_ids": ["task075-point-spine-210K"],
    }
    row = data["floquet_diagnostics"][0]
    assert row["continuation_point_record_id"] == "task075-point-spine-210K"
    assert row["terminal_event_id"] == "task075-terminal-spine-210K"
    assert row["orbit_source"]["manifest_artifact_id"] == "task075-native-adaptive-full-domain-orbit-manifest"
    assert row["orbit_source"]["restart_vector_sha256"] == "795cd6ea64e3de0e5c47803ac98f0d3f38ab0b9fc15eab467c1e6e0ac12a85c9"
    policy = data["non_orbit_policy"]
    assert policy["accepted_regular_orbit_count"] == 1
    assert policy["unresolved_targets_not_relabelled"] == 297
    assert policy["failed_targets_not_relabelled"] == 0
    assert policy["hopf_limit_equilibrium_records_not_regular_orbits"] is True
    assert policy["interpolation_or_digitized_paper_used_for_floquet"] is False
    assert "move-225K-to-spine-rho0" in policy["nonaccepted_target_ids_sample"]


def test_task077_classification_policy_preserves_ambiguous_and_unstable_results() -> None:
    ambiguous = multiplier_classification([1.0 + 1.0e-7j, 0.99995 + 0.0j, 0.25 + 0.0j])
    assert ambiguous["stability_classification"] == "ambiguous_nontrivial_unit_circle"
    assert ambiguous["ambiguous"] is True
    unstable = multiplier_classification([1.0 + 0.0j, 1.02 + 0.0j, 0.1 + 0.0j])
    assert unstable["stability_classification"] == "unstable_nontrivial_multiplier_outside_unit_circle"
    assert unstable["unstable"] is True


def test_task077_hashes_and_documentation_links_are_current() -> None:
    data = load()
    for record in data["source_provenance"].values():
        assert sha(ROOT / record["path"]) == record["sha256"]
    doc = DOC.read_text()
    for required in (
        "native_adaptive_floquet_diagnostics.json",
        "DOP853 tolerance ladder",
        "Implicit Radau is run",
        "297` TASK-075 requested targets remain explicit `resolution_unresolved`",
        "not nonlinear unknowns",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task077-floquet-postprocessing.md" in readme
    assert "native_adaptive_floquet_diagnostics.json" in readme
    assert "DOP853 variational integrations" in readme
