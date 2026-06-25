import math

import pandas as pd
import pytest

from bergner_spichtinger_2026.figure1_backend_comparison import (
    backend_detail_columns,
    comparison_frames,
    interp_branch_at_log_w,
    relative_error,
)


def _minimal_branch(backend: str = "generic"):
    log_ws = [math.log(0.01), math.log(0.1), math.log(1.0)]
    return pd.DataFrame(
        {
            "backend": [backend, backend, backend],
            "schema_version": ["figure1-branch-schema-v1"] * 3,
            "T_K": [190.0, 190.0, 190.0],
            "log_w": log_ws,
            "w_m_s": [math.exp(x) for x in log_ws],
            "n": [100.0, 1000.0, 10000.0],
            "q": [1.0e-8, 1.0e-7, 1.0e-6],
            "s": [1.45, 1.50, 1.55],
            "residual_norm": [1.0e-10, 2.0e-10, 3.0e-10],
            "N_a_m3": [1.0e10, 1.0e10, 1.0e10],
        }
    )


def test_shared_interpolation_and_relative_error_match_backend_contract():
    branch = pd.DataFrame(
        {
            "log_w": [math.log(0.01), math.log(1.0)],
            "n": [1.0e2, 1.0e6],
            "q": [1.0e-8, 1.0e-4],
            "s": [1.4, 1.6],
        }
    )
    midpoint = [(math.log(0.01) + math.log(1.0)) / 2.0]

    assert interp_branch_at_log_w(branch, "n", midpoint)[0] == pytest.approx(1.0e4)
    assert interp_branch_at_log_w(branch, "q", midpoint)[0] == pytest.approx(1.0e-6)
    assert interp_branch_at_log_w(branch, "s", midpoint)[0] == pytest.approx(1.5)
    assert relative_error(9.0, 10.0) == pytest.approx(0.1)


def test_shared_comparison_frames_support_multiple_backend_references():
    primary = _minimal_branch("loca")
    python = _minimal_branch("python")
    auto = _minimal_branch("auto")
    python.loc[:, "n"] = [101.0, 1001.0, 10001.0]
    auto.loc[:, "q"] = [1.1e-8, 1.1e-7, 1.1e-6]
    checks = pd.DataFrame(
        {
            "T_K": [190.0],
            "source": ["root_solve"],
            "log_w": [math.log(0.1)],
            "w_m_s": [0.1],
            "n_check": [999.0],
            "q_check": [1.1e-7],
            "s_check": [1.49],
            "check_converged": [True],
            "check_residual_norm": [1.0e-12],
        }
    )
    digitized = pd.DataFrame(
        {
            "panel": ["number_concentration", "mass_concentration", "saturation_ratio"],
            "T_K": [190, 190, 190],
            "w_m_s": [0.1, 0.1, 0.1],
            "value": [1000.0, 1.0e-7, 1.5],
        }
    )

    details, summary, analytic = comparison_frames(
        primary,
        backend="loca",
        branch_references=[
            (python, "loca_vs_python_continuation", "python_continuation_interpolated_on_loca_log_w"),
            (auto, "loca_vs_auto_continuation", "auto_continuation_interpolated_on_loca_log_w"),
        ],
        python_checks=checks,
        digitized=digitized,
        eq_comparison="loca_vs_eq92_94",
        eq_reference="analytic_eq92_94_at_loca_log_w",
        root_comparison="loca_vs_python_root_solve",
        digitized_comparison="loca_vs_digitized_figure1",
    )

    assert list(details.columns) == backend_detail_columns("loca")
    assert set(details["comparison"]) == {
        "loca_vs_python_continuation",
        "loca_vs_auto_continuation",
        "loca_vs_eq92_94",
        "loca_vs_python_root_solve",
        "loca_vs_digitized_figure1",
    }
    assert not analytic.empty
    assert set(summary["comparison"]) == set(details["comparison"])
    assert "max_loca_residual_norm" in summary.columns
