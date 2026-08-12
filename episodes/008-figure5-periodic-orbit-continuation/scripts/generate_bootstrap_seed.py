#!/usr/bin/env python3
"""Freeze and evaluate the Episode 007 periodic-orbit bootstrap seed.

The generator deliberately consumes only the committed Episode 007 reference
CSV and metadata.  It does not rerun the long attracting-cycle IVP.
"""

from __future__ import annotations

import argparse
import csv
import json
from math import isfinite, log
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import coefficients, vector_field
from bergner_spichtinger_2026.periodic_seed import (
    PeriodicHermiteSeed,
    SeedValidationError,
    sha256_file,
)
from bergner_spichtinger_2026.residuals import log_coordinates_from_physical_state


REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAJECTORY = REPO_ROOT / "episodes/007-limit-cycle-interactive-widget/outputs/reference_trajectory.csv"
DEFAULT_METADATA = REPO_ROOT / "episodes/007-limit-cycle-interactive-widget/outputs/reference_metadata.json"
DEFAULT_OUTPUT = EPISODE_ROOT / "outputs/bootstrap_seed.json"
TRAJECTORY_COLUMNS = (
    "time_s",
    "n_kg_dry_air_minus1",
    "q_kg_kg_dry_air_minus1",
    "s",
)
EXPECTED_PARAMETERS = {
    "T": 225.0,
    "p": 30000.0,
    "w": 0.1,
    "F": 1.0,
    "N_a": 1.0e10,
    "Delta_z": 100.0,
    "include_evaporation": False,
}
SOURCE_CYCLE_KEY = "paper_0.99"
SOURCE_CLOSURE_TOLERANCE = 2.0e-3


def transformed_model_field(state: Sequence[float], env: Environment) -> np.ndarray:
    """Return ``g(x) = (dn/dt/n, dq/dt/q, ds/dt)`` at transformed state ``x``."""
    x = np.asarray(state, dtype=float)
    if x.shape != (3,) or not np.all(np.isfinite(x)):
        raise SeedValidationError("Transformed state must contain three finite values.")
    n, q = np.exp(x[:2])
    rhs = vector_field(float(n), float(q), float(x[2]), env)
    return np.array([rhs[0] / n, rhs[1] / q, rhs[2]], dtype=float)


def _environment(parameters: Mapping[str, Any]) -> Environment:
    if dict(parameters) != EXPECTED_PARAMETERS:
        raise SeedValidationError(
            "Episode 007 canonical parameters do not match the Episode 008 bootstrap contract."
        )
    return Environment(
        T=float(parameters["T"]),
        p=float(parameters["p"]),
        w=float(parameters["w"]),
        F=float(parameters["F"]),
        N_a=float(parameters["N_a"]),
        Δz=float(parameters["Delta_z"]),
        include_evaporation=bool(parameters["include_evaporation"]),
    )


def _read_trajectory(path: Path) -> np.ndarray:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != TRAJECTORY_COLUMNS:
            raise SeedValidationError(
                f"Unexpected trajectory columns: {reader.fieldnames!r}; expected {TRAJECTORY_COLUMNS!r}."
            )
        try:
            rows = [[float(row[column]) for column in TRAJECTORY_COLUMNS] for row in reader]
        except (TypeError, ValueError) as exc:
            raise SeedValidationError("Trajectory contains a non-numeric value.") from exc

    trajectory = np.asarray(rows, dtype=float)
    if trajectory.ndim != 2 or trajectory.shape[0] < 4 or trajectory.shape[1] != 4:
        raise SeedValidationError("Trajectory must contain at least four rows with four columns.")
    if not np.all(np.isfinite(trajectory)):
        raise SeedValidationError("Trajectory contains non-finite values.")
    if not np.all(np.diff(trajectory[:, 0]) > 0.0):
        raise SeedValidationError("Trajectory times must be strictly increasing.")
    if np.any(trajectory[:, 1:3] <= 0.0):
        raise SeedValidationError("Trajectory n and q values must be positive.")
    return trajectory


def _read_metadata(path: Path) -> dict[str, Any]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SeedValidationError(f"Could not read Episode 007 metadata: {exc}") from exc
    if metadata.get("schema_version") != "1.0.0":
        raise SeedValidationError("Unsupported Episode 007 metadata schema version.")
    if not isinstance(metadata.get("canonical_parameters"), dict):
        raise SeedValidationError("Episode 007 metadata has no canonical parameter mapping.")
    return metadata


def _validated_boundaries(metadata: Mapping[str, Any]) -> list[tuple[float, float]]:
    try:
        raw_boundaries = metadata["cycle_boundaries"][SOURCE_CYCLE_KEY]
    except (KeyError, TypeError) as exc:
        raise SeedValidationError(f"Missing cycle boundaries for {SOURCE_CYCLE_KEY!r}.") from exc
    if not isinstance(raw_boundaries, list) or not raw_boundaries:
        raise SeedValidationError("Cycle boundary list must be non-empty.")

    boundaries: list[tuple[float, float]] = []
    for index, item in enumerate(raw_boundaries):
        try:
            start = float(item["start_s"])
            end = float(item["end_s"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SeedValidationError(f"Malformed cycle boundary at index {index}.") from exc
        if not (isfinite(start) and isfinite(end) and end > start):
            raise SeedValidationError(f"Cycle boundary {index} must have finite increasing times.")
        if boundaries and not np.isclose(start, boundaries[-1][1], rtol=0.0, atol=1.0e-9):
            raise SeedValidationError(f"Cycle boundaries {index - 1} and {index} are not contiguous.")
        boundaries.append((start, end))
    return boundaries


def _time_field_slopes(transformed_states: np.ndarray, env: Environment) -> np.ndarray:
    coeff = coefficients(env)
    slopes = []
    for state in transformed_states:
        n, q = np.exp(state[:2])
        rhs = vector_field(float(n), float(q), float(state[2]), env, coeff)
        slopes.append([rhs[0] / n, rhs[1] / q, rhs[2]])
    result = np.asarray(slopes, dtype=float)
    if not np.all(np.isfinite(result)):
        raise SeedValidationError("Model-field evaluation produced a non-finite slope.")
    return result


def _hermite_value(
    t: float,
    t0: float,
    t1: float,
    x0: np.ndarray,
    x1: np.ndarray,
    dx0_dt: np.ndarray,
    dx1_dt: np.ndarray,
) -> np.ndarray:
    h = t1 - t0
    u = (t - t0) / h
    h00 = 2.0 * u**3 - 3.0 * u**2 + 1.0
    h10 = u**3 - 2.0 * u**2 + u
    h01 = -2.0 * u**3 + 3.0 * u**2
    h11 = u**3 - u**2
    return h00 * x0 + h10 * h * dx0_dt + h01 * x1 + h11 * h * dx1_dt


def _source_path_label(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_seed(
    trajectory_path: Path = DEFAULT_TRAJECTORY,
    metadata_path: Path = DEFAULT_METADATA,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Build the deterministic seed mapping from Episode 007 artifacts."""
    trajectory_path = Path(trajectory_path)
    metadata_path = Path(metadata_path)
    trajectory = _read_trajectory(trajectory_path)
    metadata = _read_metadata(metadata_path)
    env = _environment(metadata["canonical_parameters"])
    boundaries = _validated_boundaries(metadata)
    cycle_index = len(boundaries) - 1
    start_s, end_s = boundaries[-1]
    period_s = end_s - start_s

    times = trajectory[:, 0]
    if not np.isclose(times[-1], end_s, rtol=0.0, atol=1.0e-9):
        raise SeedValidationError("Final cycle end must be the final committed trajectory row.")
    insertion = int(np.searchsorted(times, start_s, side="left"))
    if insertion < 2 or insertion + 1 >= len(times):
        raise SeedValidationError("Final cycle start is not bracketed by enough trajectory samples.")
    if times[insertion] == start_s:
        raise SeedValidationError(
            "This seed schema expects the recorded saturation-maximum start to be bracketed, not sampled exactly."
        )
    if not (times[insertion - 1] < start_s < times[insertion]):
        raise SeedValidationError("Final cycle start is not strictly bracketed by trajectory times.")

    saturation = trajectory[:, 3]
    if not (
        saturation[insertion - 2] < saturation[insertion - 1]
        and saturation[insertion] > saturation[insertion + 1]
    ):
        raise SeedValidationError("Final cycle start does not bracket a saturation maximum.")
    if not saturation[-2] < saturation[-1]:
        raise SeedValidationError("Final cycle end is not approached as a saturation maximum.")

    interior_mask = (times > start_s) & (times < end_s)
    interior = trajectory[interior_mask]
    if len(interior) < 4:
        raise SeedValidationError("Final cycle has too few strict-interior trajectory samples.")

    terminal_physical_state = trajectory[-1, 1:4]
    terminal_transformed_state = log_coordinates_from_physical_state(terminal_physical_state)
    interior_transformed = np.column_stack(
        (np.log(interior[:, 1]), np.log(interior[:, 2]), interior[:, 3])
    )

    bracket_physical = trajectory[insertion - 1 : insertion + 1, 1:4]
    bracket_transformed = np.column_stack(
        (np.log(bracket_physical[:, 0]), np.log(bracket_physical[:, 1]), bracket_physical[:, 2])
    )
    bracket_time_slopes = _time_field_slopes(bracket_transformed, env)
    reconstructed_start = _hermite_value(
        start_s,
        times[insertion - 1],
        times[insertion],
        bracket_transformed[0],
        bracket_transformed[1],
        bracket_time_slopes[0],
        bracket_time_slopes[1],
    )
    closure_delta = terminal_transformed_state - reconstructed_start
    closure_max_abs = float(np.max(np.abs(closure_delta)))
    if closure_max_abs > SOURCE_CLOSURE_TOLERANCE:
        raise SeedValidationError(
            "Final source cycle is not periodic within the transformed-state closure tolerance: "
            f"{closure_max_abs:.17g} > {SOURCE_CLOSURE_TOLERANCE:.17g}."
        )

    theta = np.concatenate(
        ([0.0], (interior[:, 0] - start_s) / period_s, [1.0])
    )
    transformed_state = np.vstack(
        (terminal_transformed_state, interior_transformed, terminal_transformed_state)
    )
    time_slopes = _time_field_slopes(transformed_state, env)
    phase_slopes = period_s * time_slopes
    phase_slopes[-1] = phase_slopes[0]

    seed = {
        "schema_version": "1.0.0",
        "seed_id": "episode008-bootstrap-paper_0.99-final-cycle",
        "canonical_parameters": dict(metadata["canonical_parameters"]),
        "coordinates": {
            "phase": "normalized theta in [0, 1]",
            "state": ["log(n)", "log(q)", "s"],
            "phase_slope": "dx/dtheta = period_s * g(x)",
        },
        "units": {
            "phase": "1",
            "state": ["1", "1", "1"],
            "phase_slope": ["1", "1", "1"],
            "period": "s",
        },
        "period_s": period_s,
        "log_period": log(period_s),
        "knots": {
            "theta": theta.tolist(),
            "transformed_state": transformed_state.tolist(),
            "dstate_dtheta": phase_slopes.tolist(),
        },
        "extraction": {
            "source_cycle_key": SOURCE_CYCLE_KEY,
            "source_cycle_index_zero_based": cycle_index,
            "boundary_kind": "saturation_maximum_to_saturation_maximum",
            "start_time_s": start_s,
            "end_time_s": end_s,
            "strict_interior_sample_count": int(len(interior)),
            "periodic_endpoint_policy": (
                "The terminal saturation-maximum event state is reused at theta=0 and theta=1; "
                "the metadata start event is bracketed but absent from the sampled CSV."
            ),
            "start_boundary_bracket_s": [
                float(times[insertion - 1]),
                float(times[insertion]),
            ],
            "reconstructed_start_transformed_state": reconstructed_start.tolist(),
            "terminal_minus_reconstructed_start": closure_delta.tolist(),
            "source_closure_max_abs": closure_max_abs,
            "source_closure_tolerance": SOURCE_CLOSURE_TOLERANCE,
            "slope_method": "transformed paper model field evaluated at every stored knot",
            "long_ivp_rerun_required": False,
        },
        "upstream": {
            "reference_trajectory": {
                "path": _source_path_label(trajectory_path, repo_root),
                "sha256": sha256_file(trajectory_path),
            },
            "reference_metadata": {
                "path": _source_path_label(metadata_path, repo_root),
                "sha256": sha256_file(metadata_path),
            },
        },
    }
    PeriodicHermiteSeed.validate_mapping(seed)
    return seed


def render_seed(seed: Mapping[str, Any]) -> str:
    """Render a seed deterministically for regeneration checks."""
    return json.dumps(seed, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_seed(seed: Mapping[str, Any], output_path: Path = DEFAULT_OUTPUT) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_seed(seed), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", type=Path, default=DEFAULT_TRAJECTORY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing if the existing output differs from deterministic regeneration",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    seed = build_seed(args.trajectory, args.metadata)
    rendered = render_seed(seed)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"Frozen seed is missing or stale: {args.output}")
        print(f"Frozen seed is current: {args.output}")
        return
    write_seed(seed, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
