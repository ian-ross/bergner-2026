import importlib.util
import json
import shutil
import sys
from math import log
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes/003-figure1-auto-continuation/scripts/run_auto_figure1.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_auto_figure1", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_episode3_auto_templates_use_shared_model_core_and_log_w_parameter():
    module = _load_script_module()
    rendered = module._render_problem(230.0)
    constants = module._render_constants()

    assert "use bs2026_model, only: environment_t, equilibrium_residual" in rendered
    assert "include 'bs2026_constants.f90'" in rendered
    assert "include 'bs2026_model.f90'" in rendered
    assert "call equilibrium_residual(log_state, PAR(1), env, residual, status)" in rendered
    assert "ICP =  [1]" in constants
    assert f"{log(module.W_MAX):.17e}" in constants


def test_episode3_auto_parser_clips_requested_range_and_exposes_overrun_warning():
    module = _load_script_module()
    rows = [
        module.AutoRow(1, -1, 9, 1, module.LOG_W_MIN, 0.0, 1.0, -10.0, 1.2),
        module.AutoRow(1, -2, 0, 0, 0.0, 0.0, 1.1, -9.9, 1.21),
        module.AutoRow(1, -3, -4, 2, module.LOG_W_MAX, 0.0, 1.2, -9.8, 1.22),
        module.AutoRow(1, -4, 0, 0, module.LOG_W_MAX + 1.0, 0.0, 1.3, -9.7, 1.23),
    ]

    requested = module._requested_range_rows(rows)
    diagnostics = module._diagnose(rows, "", "")

    assert [row.log_w for row in requested] == [module.LOG_W_MIN, 0.0, module.LOG_W_MAX]
    assert diagnostics["ok"] is True
    assert diagnostics["row_count"] == 3
    assert diagnostics["raw_row_count"] == 4
    assert diagnostics["w_max_m_s"] == pytest.approx(module.W_MAX)
    assert diagnostics["raw_log_w_max"] > module.LOG_W_MAX
    assert any("continued beyond requested" in warning for warning in diagnostics["warnings"])


def test_episode3_auto_single_temperature_smoke_run(tmp_path):
    if shutil.which("gfortran") is None or not Path("/usr/local/bin/auto").exists():
        pytest.skip("gfortran and AUTO-07p at /usr/local/bin/auto are required for the Episode 3 AUTO smoke run")

    module = _load_script_module()
    diagnostics = module._run_temperature(230.0, tmp_path)

    assert diagnostics["ok"] is True
    assert diagnostics["row_count"] > 100
    assert diagnostics["w_min_m_s"] == pytest.approx(module.W_MIN, rel=1e-8)
    assert diagnostics["w_max_m_s"] == pytest.approx(module.W_MAX, rel=1e-8)
    assert Path(tmp_path, diagnostics["branch_csv"]).exists()
    raw_dir = tmp_path / "raw" / "bs2026_T230K"
    assert (raw_dir / "b.bs2026_T230K").exists()
    assert (raw_dir / "s.bs2026_T230K").exists()
    assert (raw_dir / "d.bs2026_T230K").exists()

    metadata = {"runs": [diagnostics]}
    assert json.dumps(metadata)
