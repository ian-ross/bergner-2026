from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
PROFILE = EPISODE / "outputs/native_adaptive_resource_profile.json"
RUN_METADATA = EPISODE / "outputs/native_adaptive_resource_profile_run_metadata.json"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_resource_profile.py"
DOC = EPISODE / "docs/task071-resource-profile.md"
README = EPISODE / "README.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_profile() -> dict:
    return json.loads(PROFILE.read_text())


def test_task071_resource_profile_artifacts_are_checkable_and_schema_valid() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(json.loads(RUN_METADATA.read_text()), root=ROOT, artifact_path=RUN_METADATA)


def test_profile_records_nonplaceholder_resources_and_required_counters() -> None:
    data = load_profile()
    assert data["schema_version"] == "episode008-native-adaptive-resource-profile-v1"
    assert data["truthfulness_policy"] == {
        "replaces_task068_zero_resource_placeholders": True,
        "cost_measurements_are_not_scientific_acceptance": True,
        "failed_or_pending_targets_not_rebranded_as_accepted": True,
        "production_cpp_full_adaptive_backend_executed": False,
        "current_backend_seams_profiled": ["fixed_mesh", "remesh_restart", "pilot_style_native_adaptive_driver"],
    }
    by_type = {row["segment_type"]: row for row in data["measurements"]}
    assert set(by_type) == {"fixed_mesh", "remesh_restart", "pilot_style_native_adaptive_driver"}
    for row in by_type.values():
        resources = row["resources"]
        assert resources["wall_clock_s"] > 0.0
        assert resources["cpu_time_s"] >= 0.0
        assert resources["max_rss_kib"] > 0
        assert row["nonlinear_iterations"] > 0
        assert row["klu2"]["backend"] == "KLU2"
        assert row["klu2"]["reported"] is True
        assert row["klu2"]["solve_complete"] is True
        assert min(
            row["klu2"]["symbolic_factorizations"],
            row["klu2"]["numeric_factorizations"],
            row["klu2"]["linear_solves"],
        ) > 0
    assert by_type["fixed_mesh"]["nox_status"] == "converged"
    assert by_type["remesh_restart"]["restart_gates_passed"] is True
    assert by_type["pilot_style_native_adaptive_driver"]["driver_manifest_placeholder_resources_ignored"] is True


def test_klu2_review_keeps_cost_policy_separate_from_scientific_acceptance() -> None:
    review = load_profile()["klu2_iterative_solver_review"]
    assert review["policy_version"] == "task062-klu2-iterative-trigger-policy-v1"
    assert review["decision"] == "serial_KLU2_remains_acceptable_for_current_native_adaptive_pilot_seams"
    assert review["iterative_solver_thresholds_met"] is False
    assert review["cost_is_scientific_acceptance"] is False
    assert review["all_measured_klu2_solves_complete"] is True
    assert review["documented_triggers"]["realistic_N_256_to_512_factorization_memory_above_4_GiB"] is False
    assert "not_evaluated" in review["documented_triggers"]["median_factorization_or_solve_time_above_30_s_per_nonlinear_iteration"]
    assert "not_evaluated" in review["documented_triggers"]["more_than_70_percent_runtime_in_linear_algebra"]


def test_profile_sources_metadata_and_documentation_links_are_current() -> None:
    data = load_profile()
    assert data["production_schema_metadata_artifact"] == RUN_METADATA.relative_to(ROOT).as_posix()
    for source in data["source_provenance"].values():
        assert sha(ROOT / source["path"]) == source["sha256"]
    text = DOC.read_text()
    readme = README.read_text()
    assert "native_adaptive_resource_profile.json" in text
    assert "native_adaptive_resource_profile_run_metadata.json" in text
    assert "serial KLU2 remains acceptable" in text
    assert "docs/task071-resource-profile.md" in readme
    metadata = json.loads(RUN_METADATA.read_text())
    source_paths = {source["path"] for source in metadata["provenance"]["source_artifacts"]}
    assert PROFILE.relative_to(ROOT).as_posix() in source_paths
