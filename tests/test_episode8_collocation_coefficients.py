import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import sympy as sp


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SCRIPTS = EPISODE_ROOT / "scripts"
ARTIFACT_PATH = EPISODE_ROOT / "outputs/collocation_coefficients.json"
PYTHON_PATH = REPO_ROOT / "src/bergner_spichtinger_2026/collocation_coefficients.py"
CPP_PATH = REPO_ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp"
GENERATOR_PATH = SCRIPTS / "generate_collocation_coefficients.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_collocation_coefficients as generator
from bergner_spichtinger_2026.collocation_coefficients import (
    ARTIFACT_SCHEMA_VERSION,
    ARTIFACT_SHA256,
    GAUSS_LEGENDRE_RULES,
    gauss_legendre_rule,
)


def _artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def _float_array(quantity: dict) -> np.ndarray:
    return np.asarray(quantity["decimal"], dtype=float)


def _evaluate_ascending(coefficients: np.ndarray, points: np.ndarray) -> np.ndarray:
    return np.polynomial.polynomial.polyval(points, coefficients)


def test_canonical_artifact_schema_checksum_and_decimal_precision():
    artifact = _artifact()
    checksum = artifact.pop("checksum")

    assert artifact["schema_version"] == "1.0.0"
    assert artifact["numeric_representation"] == {
        "decimal_significant_digits": 17,
        "format": ".16e",
        "kind": "IEEE-754 binary64 source literals",
    }
    assert checksum["algorithm"] == "sha256"
    assert checksum["value"] == generator.payload_checksum(artifact)
    assert checksum["value"] == ARTIFACT_SHA256
    assert ARTIFACT_SCHEMA_VERSION == artifact["schema_version"]

    decimal_literal = re.compile(r"^-?\d\.\d{16}e[+-]\d{2}$")

    def check_decimal_values(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "decimal":
                    check_decimal_literals(item)
                else:
                    check_decimal_values(item)
        elif isinstance(value, list):
            for item in value:
                check_decimal_values(item)

    def check_decimal_literals(value):
        if isinstance(value, list):
            for item in value:
                check_decimal_literals(item)
        else:
            assert decimal_literal.fullmatch(value), value
            assert np.isfinite(float(value))

    check_decimal_values(artifact["rules"])


def test_symbolic_derivation_and_generated_runtime_tables_are_consistent():
    artifact = _artifact()
    tau = sp.Symbol("tau")

    assert [rule["stage_count"] for rule in artifact["rules"]] == [1, 2, 3]
    for record in artifact["rules"]:
        stage_count = record["stage_count"]
        generated = generator.derive_rule(stage_count)
        runtime = gauss_legendre_rule(stage_count)

        assert generated == record
        assert record["family"] == runtime.family == "gauss-legendre"
        assert record["formal_order"] == runtime.formal_order == 2 * stage_count
        assert runtime.stage_count == stage_count

        nodes = _float_array(record["nodes"])
        np.testing.assert_array_equal(runtime.nodes, nodes)
        np.testing.assert_array_equal(
            runtime.stage_coefficients, _float_array(record["stage_coefficients"])
        )
        np.testing.assert_array_equal(
            runtime.quadrature_weights, _float_array(record["quadrature_weights"])
        )
        np.testing.assert_array_equal(
            runtime.transfer_coefficients,
            _float_array(record["integrated_lagrange"]["coefficients"]),
        )
        np.testing.assert_array_equal(
            runtime.defect_check_nodes, _float_array(record["defect_check"]["nodes"])
        )
        np.testing.assert_array_equal(
            runtime.defect_lagrange_evaluation,
            _float_array(record["defect_check"]["lagrange_evaluation"]),
        )
        np.testing.assert_array_equal(
            runtime.defect_transfer_evaluation,
            _float_array(record["defect_check"]["integrated_lagrange_evaluation"]),
        )

        symbolic_nodes = [sp.sympify(value) for value in record["nodes"]["symbolic"]]
        shifted_legendre = sp.legendre(stage_count, 2 * tau - 1)
        assert all(sp.simplify(shifted_legendre.subs(tau, node)) == 0 for node in symbolic_nodes)

        symbolic_check_nodes = [
            sp.sympify(value) for value in record["defect_check"]["nodes"]["symbolic"]
        ]
        shifted_check_legendre = sp.legendre(stage_count + 1, 2 * tau - 1)
        assert len(symbolic_check_nodes) == stage_count + 1
        assert all(
            sp.simplify(shifted_check_legendre.subs(tau, node)) == 0
            for node in symbolic_check_nodes
        )

    with pytest.raises(ValueError, match="expected 1, 2, or 3"):
        gauss_legendre_rule(4)
    assert set(GAUSS_LEGENDRE_RULES) == {1, 2, 3}
    with pytest.raises(TypeError):
        GAUSS_LEGENDRE_RULES[4] = gauss_legendre_rule(3)  # type: ignore[index]


def test_generated_runtime_tables_do_not_import_sympy():
    code = f"""
import builtins
import sys

real_import = builtins.__import__
def without_sympy(name, *args, **kwargs):
    if name == "sympy" or name.startswith("sympy."):
        raise AssertionError("runtime attempted to import SymPy")
    return real_import(name, *args, **kwargs)

builtins.__import__ = without_sympy
sys.path.insert(0, {str(REPO_ROOT / 'src')!r})
from bergner_spichtinger_2026.collocation_coefficients import gauss_legendre_rule
assert gauss_legendre_rule(3).formal_order == 6
"""
    subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, check=True)


@pytest.mark.parametrize("stage_count", [1, 2, 3])
def test_gauss_rule_identities_transfer_data_and_polynomial_exactness(stage_count):
    rule = gauss_legendre_rule(stage_count)
    nodes = np.asarray(rule.nodes)
    stage = np.asarray(rule.stage_coefficients)
    weights = np.asarray(rule.quadrature_weights)
    transfer = np.asarray(rule.transfer_coefficients)
    check_nodes = np.asarray(rule.defect_check_nodes)
    check_lagrange = np.asarray(rule.defect_lagrange_evaluation)
    check_transfer = np.asarray(rule.defect_transfer_evaluation)

    assert np.all((0.0 < nodes) & (nodes < 1.0))
    assert np.all((0.0 < check_nodes) & (check_nodes < 1.0))
    assert all(np.min(np.abs(check_nodes - node)) > 1.0e-12 for node in nodes)
    np.testing.assert_allclose(np.sum(weights), 1.0, rtol=0.0, atol=2.0e-16)
    np.testing.assert_allclose(np.sum(stage, axis=1), nodes, rtol=0.0, atol=3.0e-16)

    # An r-point Gauss rule integrates every polynomial through degree 2r-1.
    for degree in range(2 * stage_count):
        numerical = np.dot(weights, nodes**degree)
        exact = 1.0 / (degree + 1)
        assert numerical == pytest.approx(exact, rel=0.0, abs=3.0e-16)

    # Collocation integrates the interpolating monomials through degree r-1
    # from zero to each stage node.
    for degree in range(stage_count):
        numerical = stage @ (nodes**degree)
        exact = nodes ** (degree + 1) / (degree + 1)
        np.testing.assert_allclose(numerical, exact, rtol=0.0, atol=4.0e-16)

    # The transfer polynomial coefficients reproduce A and b, while their
    # values and derivatives at independently derived check nodes reproduce
    # the committed defect-check matrices.
    reconstructed_stage = np.column_stack(
        [_evaluate_ascending(coefficients, nodes) for coefficients in transfer]
    )
    reconstructed_weights = np.array(
        [_evaluate_ascending(coefficients, np.asarray(1.0)) for coefficients in transfer]
    )
    reconstructed_check_transfer = np.column_stack(
        [_evaluate_ascending(coefficients, check_nodes) for coefficients in transfer]
    )
    derivative_coefficients = np.asarray(
        [
            [power * coefficient for power, coefficient in enumerate(coefficients)][1:]
            for coefficients in transfer
        ]
    )
    reconstructed_check_lagrange = np.column_stack(
        [
            _evaluate_ascending(coefficients, check_nodes)
            for coefficients in derivative_coefficients
        ]
    )

    np.testing.assert_allclose(reconstructed_stage, stage, rtol=0.0, atol=6.0e-16)
    np.testing.assert_allclose(reconstructed_weights, weights, rtol=0.0, atol=6.0e-16)
    np.testing.assert_allclose(
        reconstructed_check_transfer, check_transfer, rtol=0.0, atol=7.0e-16
    )
    np.testing.assert_allclose(
        reconstructed_check_lagrange, check_lagrange, rtol=0.0, atol=8.0e-16
    )
    np.testing.assert_allclose(np.sum(check_lagrange, axis=1), 1.0, rtol=0.0, atol=5.0e-16)
    np.testing.assert_allclose(
        np.sum(check_transfer, axis=1), check_nodes, rtol=0.0, atol=6.0e-16
    )


def test_all_generated_artifacts_regenerate_byte_for_byte_and_check_detects_drift(tmp_path):
    expected = generator.generated_texts()
    assert ARTIFACT_PATH.read_bytes() == expected["artifact"].encode("utf-8")
    assert PYTHON_PATH.read_bytes() == expected["python"].encode("utf-8")
    assert CPP_PATH.read_bytes() == expected["cpp"].encode("utf-8")

    paths = {
        "artifact": tmp_path / "collocation_coefficients.json",
        "python": tmp_path / "collocation_coefficients.py",
        "cpp": tmp_path / "collocation_coefficients.hpp",
    }
    command = [
        sys.executable,
        str(GENERATOR_PATH),
        "--artifact",
        str(paths["artifact"]),
        "--python-output",
        str(paths["python"]),
        "--cpp-output",
        str(paths["cpp"]),
    ]
    subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    subprocess.run(command + ["--check"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)

    artifact_bytes = paths["artifact"].read_bytes()
    paths["artifact"].write_bytes(artifact_bytes.replace(b"\n", b"\r\n"))
    stale = subprocess.run(
        command + ["--check"], cwd=REPO_ROOT, check=False, capture_output=True, text=True
    )
    assert stale.returncode != 0
    assert "artifact" in stale.stderr
    assert b"\r\n" in paths["artifact"].read_bytes()


def test_generated_cpp_header_compiles_and_exposes_matching_metadata(tmp_path):
    compiler = shutil.which("c++")
    if compiler is None:
        pytest.skip("No C++ compiler is available")

    source = tmp_path / "coefficients.cpp"
    executable = tmp_path / "coefficients"
    source.write_text(
        r"""
#include "bergner_spichtinger_2026_loca/collocation_coefficients.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>

template <std::size_t N>
bool valid_rule() {
  using Rule = bs2026_loca::collocation::GaussLegendreRule<N>;
  double weight_sum = 0.0;
  for (std::size_t j = 0; j < N; ++j) weight_sum += Rule::quadrature_weights[j];
  if (std::abs(weight_sum - 1.0) > 1.0e-15) return false;
  for (std::size_t i = 0; i < N; ++i) {
    double row_sum = 0.0;
    for (std::size_t j = 0; j < N; ++j) row_sum += Rule::stage_coefficients[i][j];
    if (std::abs(row_sum - Rule::nodes[i]) > 1.0e-15) return false;
  }
  return true;
}

template <std::size_t N>
void print_rule() {
  using Rule = bs2026_loca::collocation::GaussLegendreRule<N>;
  std::cout << N;
  const auto emit = [](double value) { std::cout << ' ' << value; };
  for (std::size_t i = 0; i < N; ++i) emit(Rule::nodes[i]);
  for (std::size_t i = 0; i < N; ++i)
    for (std::size_t j = 0; j < N; ++j) emit(Rule::stage_coefficients[i][j]);
  for (std::size_t i = 0; i < N; ++i) emit(Rule::quadrature_weights[i]);
  for (std::size_t i = 0; i < N; ++i)
    for (std::size_t j = 0; j < N + 1; ++j) emit(Rule::transfer_coefficients[i][j]);
  for (std::size_t i = 0; i < N + 1; ++i) emit(Rule::defect_check_nodes[i]);
  for (std::size_t i = 0; i < N + 1; ++i)
    for (std::size_t j = 0; j < N; ++j) emit(Rule::defect_lagrange_evaluation[i][j]);
  for (std::size_t i = 0; i < N + 1; ++i)
    for (std::size_t j = 0; j < N; ++j) emit(Rule::defect_transfer_evaluation[i][j]);
  std::cout << '\n';
}

int main() {
  static_assert(bs2026_loca::collocation::GaussLegendreRule<1>::formal_order == 2);
  static_assert(bs2026_loca::collocation::GaussLegendreRule<2>::formal_order == 4);
  static_assert(bs2026_loca::collocation::GaussLegendreRule<3>::formal_order == 6);
  if (!(valid_rule<1>() && valid_rule<2>() && valid_rule<3>())) return 1;
  std::cout << bs2026_loca::collocation::artifact_sha256 << '\n';
  std::cout << std::setprecision(17);
  print_rule<1>();
  print_rule<2>();
  print_rule<3>();
}
""".lstrip(),
        encoding="utf-8",
    )
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-pedantic",
            f"-I{REPO_ROOT / 'loca/include'}",
            str(source),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
    lines = result.stdout.splitlines()
    assert lines[0] == ARTIFACT_SHA256
    assert len(lines) == 4

    for stage_count, line in zip((1, 2, 3), lines[1:], strict=True):
        rule = gauss_legendre_rule(stage_count)
        cpp_values = np.fromstring(line, sep=" ")
        expected_values = np.concatenate(
            [
                [float(stage_count)],
                np.asarray(rule.nodes),
                np.asarray(rule.stage_coefficients).ravel(),
                np.asarray(rule.quadrature_weights),
                np.asarray(rule.transfer_coefficients).ravel(),
                np.asarray(rule.defect_check_nodes),
                np.asarray(rule.defect_lagrange_evaluation).ravel(),
                np.asarray(rule.defect_transfer_evaluation).ravel(),
            ]
        )
        np.testing.assert_array_equal(cpp_values, expected_values)
