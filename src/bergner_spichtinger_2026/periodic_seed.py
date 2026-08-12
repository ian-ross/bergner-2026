"""Reusable loading and interpolation for frozen periodic-orbit seeds.

This module is intentionally independent of episode-specific extraction logic.
A seed is a JSON-compatible mapping containing normalized phase knots,
transformed states, phase derivatives, and a positive period.  Producers may
attach additional provenance and parameter metadata; the loader validates the
numerical interpolation contract while preserving a language-neutral artifact.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite, log
from pathlib import Path
from typing import Any, Mapping

import numpy as np


class SeedValidationError(ValueError):
    """Raised when a frozen periodic seed violates its numerical contract."""


def sha256_file(path: Path) -> str:
    """Return the hexadecimal SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_upstream_checksums(seed: Mapping[str, Any], root: Path) -> None:
    """Verify every upstream path/checksum record in a frozen seed.

    Upstream paths must resolve beneath ``root``.  Each record in the seed's
    ``upstream`` mapping must contain ``path`` and ``sha256`` fields.
    """
    resolved_root = Path(root).resolve()
    if not isinstance(seed, Mapping):
        raise SeedValidationError("Frozen seed JSON must contain a top-level object.")
    upstream = seed.get("upstream")
    if not isinstance(upstream, Mapping) or not upstream:
        raise SeedValidationError("Seed has no valid upstream checksum records.")

    for name, raw_entry in upstream.items():
        if not isinstance(raw_entry, Mapping):
            raise SeedValidationError(f"Malformed upstream checksum record: {name}")
        try:
            relative_path = Path(raw_entry["path"])
            expected = str(raw_entry["sha256"])
        except (KeyError, TypeError) as exc:
            raise SeedValidationError(f"Malformed upstream checksum record: {name}") from exc

        source = (resolved_root / relative_path).resolve()
        if not source.is_relative_to(resolved_root):
            raise SeedValidationError("Upstream path escapes the verification root.")
        if not source.is_file():
            raise SeedValidationError(f"Upstream artifact is missing: {relative_path}")
        actual = sha256_file(source)
        if actual != expected:
            raise SeedValidationError(
                f"Upstream artifact drift detected for {relative_path}: "
                f"expected {expected}, found {actual}."
            )


@dataclass(frozen=True)
class PeriodicHermiteSeed:
    """Validated periodic cubic-Hermite representation of a transformed orbit."""

    theta: np.ndarray
    transformed_state: np.ndarray
    dstate_dtheta: np.ndarray
    period_s: float
    log_period: float

    @classmethod
    def from_mapping(cls, seed: Mapping[str, Any]) -> "PeriodicHermiteSeed":
        """Validate and load a JSON-compatible periodic-seed mapping."""
        try:
            theta = np.array(seed["knots"]["theta"], dtype=float, copy=True)
            state = np.array(seed["knots"]["transformed_state"], dtype=float, copy=True)
            slope = np.array(seed["knots"]["dstate_dtheta"], dtype=float, copy=True)
            period_s = float(seed["period_s"])
            log_period = float(seed["log_period"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SeedValidationError("Malformed periodic Hermite seed arrays or period.") from exc

        if theta.ndim != 1 or len(theta) < 2:
            raise SeedValidationError("Seed theta must be a one-dimensional knot array.")
        if state.shape != (len(theta), 3) or slope.shape != state.shape:
            raise SeedValidationError("Seed state and slope arrays must have shape (number_of_knots, 3).")
        if not (
            np.all(np.isfinite(theta))
            and np.all(np.isfinite(state))
            and np.all(np.isfinite(slope))
            and isfinite(period_s)
            and isfinite(log_period)
        ):
            raise SeedValidationError("Seed contains non-finite values.")
        if theta[0] != 0.0 or theta[-1] != 1.0 or not np.all(np.diff(theta) > 0.0):
            raise SeedValidationError("Seed phase knots must increase strictly from exactly 0 to exactly 1.")
        if period_s <= 0.0 or not np.isclose(log_period, log(period_s), rtol=0.0, atol=2.0e-15):
            raise SeedValidationError("Seed period and log period are inconsistent.")
        if not np.array_equal(state[0], state[-1]):
            raise SeedValidationError("Periodic seed endpoint values do not match exactly.")
        if not np.array_equal(slope[0], slope[-1]):
            raise SeedValidationError("Periodic seed endpoint slopes do not match exactly.")

        theta.setflags(write=False)
        state.setflags(write=False)
        slope.setflags(write=False)
        return cls(theta, state, slope, period_s, log_period)

    @classmethod
    def validate_mapping(cls, seed: Mapping[str, Any]) -> None:
        """Raise if a mapping cannot be consumed as a periodic Hermite seed."""
        cls.from_mapping(seed)

    @classmethod
    def from_json(
        cls,
        path: Path,
        *,
        verify_upstream_root: Path | None = None,
    ) -> "PeriodicHermiteSeed":
        """Load a frozen seed, optionally checking all recorded upstream files."""
        try:
            mapping = json.loads(Path(path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise SeedValidationError(f"Could not read frozen seed: {exc}") from exc
        if not isinstance(mapping, Mapping):
            raise SeedValidationError("Frozen seed JSON must contain a top-level object.")
        if verify_upstream_root is not None:
            verify_upstream_checksums(mapping, verify_upstream_root)
        return cls.from_mapping(mapping)

    def _evaluate(self, phase: Any, *, derivative: bool) -> np.ndarray:
        values = np.asarray(phase, dtype=float)
        if not np.all(np.isfinite(values)):
            raise SeedValidationError("Evaluation phases must be finite.")
        wrapped = np.mod(values, 1.0)
        flat = wrapped.reshape(-1)
        interval = np.searchsorted(self.theta, flat, side="right") - 1
        interval = np.clip(interval, 0, len(self.theta) - 2)
        left = self.theta[interval]
        h = self.theta[interval + 1] - left
        u = (flat - left) / h
        x0 = self.transformed_state[interval]
        x1 = self.transformed_state[interval + 1]
        m0 = self.dstate_dtheta[interval]
        m1 = self.dstate_dtheta[interval + 1]

        if derivative:
            result = (
                ((6.0 * u**2 - 6.0 * u) / h)[:, None] * x0
                + (3.0 * u**2 - 4.0 * u + 1.0)[:, None] * m0
                + ((-6.0 * u**2 + 6.0 * u) / h)[:, None] * x1
                + (3.0 * u**2 - 2.0 * u)[:, None] * m1
            )
        else:
            h00 = 2.0 * u**3 - 3.0 * u**2 + 1.0
            h10 = u**3 - 2.0 * u**2 + u
            h01 = -2.0 * u**3 + 3.0 * u**2
            h11 = u**3 - u**2
            result = (
                h00[:, None] * x0
                + (h10 * h)[:, None] * m0
                + h01[:, None] * x1
                + (h11 * h)[:, None] * m1
            )

        return result.reshape(values.shape + (3,))

    def evaluate(self, phase: Any) -> np.ndarray:
        """Evaluate transformed state at arbitrary scalar or array-like phases."""
        return self._evaluate(phase, derivative=False)

    def derivative(self, phase: Any) -> np.ndarray:
        """Evaluate ``dx/dtheta`` at arbitrary scalar or array-like phases."""
        return self._evaluate(phase, derivative=True)
