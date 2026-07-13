"""Reusable model and continuation utilities for Bergner & Spichtinger (2026)."""

from .approximations import (
    TABLE_II_HOPF_WA_COEFFICIENTS,
    TABLE_II_HOPF_WB_COEFFICIENTS,
    HopfFitCoefficients,
    approximate_equilibrium,
    approximate_equilibrium_s,
    sigma_equilibrium,
    table_ii_hopf_w_a,
    table_ii_hopf_w_b,
    table_ii_lower_hopf_w,
    table_ii_upper_hopf_w,
)
from .continuation import ContinuationPoint, ContinuationResult, continue_branch
from .residuals import (
    equilibrium_residual,
    log_coordinates_from_physical_state,
    make_equilibrium_residual,
    physical_state_from_log_coordinates,
)
from .stability import (
    EigenvalueClassification,
    HopfCrossing,
    canonical_eigenvalues,
    classify_eigenvalues,
    detect_hopf_crossings,
    derive_physical_jacobian_expressions,
    physical_eigenvalues,
    physical_jacobian,
)

__all__ = [
    "TABLE_II_HOPF_WA_COEFFICIENTS",
    "TABLE_II_HOPF_WB_COEFFICIENTS",
    "HopfFitCoefficients",
    "approximate_equilibrium",
    "approximate_equilibrium_s",
    "sigma_equilibrium",
    "table_ii_hopf_w_a",
    "table_ii_hopf_w_b",
    "table_ii_lower_hopf_w",
    "table_ii_upper_hopf_w",
    "ContinuationPoint",
    "ContinuationResult",
    "continue_branch",
    "equilibrium_residual",
    "log_coordinates_from_physical_state",
    "make_equilibrium_residual",
    "physical_state_from_log_coordinates",
    "EigenvalueClassification",
    "HopfCrossing",
    "canonical_eigenvalues",
    "classify_eigenvalues",
    "detect_hopf_crossings",
    "derive_physical_jacobian_expressions",
    "physical_eigenvalues",
    "physical_jacobian",
    "main",
]


def main() -> None:
    print("Bergner & Spichtinger 2026 extraction workspace. See docs/MODEL_EXTRACTION.md.")
