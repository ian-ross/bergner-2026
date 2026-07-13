#!/usr/bin/env python3
"""Run Figure 1 equilibrium continuation through the NOX/LOCA LAPACK adapter.

This is intentionally a thin orchestration wrapper around ``run_loca_figure1``:
the normalized schema and comparison target stay identical, while the C++ CLI
uses the ``nox-loca-continue`` command that exercises the LOCA::LAPACK::Interface
residual/Jacobian/parameter adapter before writing branch rows.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_SCRIPT = REPO_ROOT / "episodes/004-figure1-loca-continuation/scripts/run_loca_figure1.py"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "episodes/004-figure1-loca-continuation/outputs/figure1_nox_loca_branches"
DEFAULT_BUILD_DIR = REPO_ROOT / ".pytest_cache" / "nox-loca-figure1-build"


def _load_base_module():
    spec = importlib.util.spec_from_file_location("run_loca_figure1_base", BASE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = _load_base_module()
    original_argv = sys.argv[:]
    try:
        sys.argv = [
            original_argv[0],
            "--backend-command",
            "nox-loca-continue",
            "--backend-label",
            "nox_loca",
            "--output-dir",
            str(DEFAULT_OUTPUT_DIR),
            "--build-dir",
            str(DEFAULT_BUILD_DIR),
            *original_argv[1:],
        ]
        module.main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
