#!/usr/bin/env python3
"""Derive and generate shared Gauss--Legendre collocation tables.

SymPy is required only to run this generator.  The generated Python and C++
tables contain ordinary binary64 literals and have no runtime SymPy dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import sympy as sp


REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = EPISODE_ROOT / "outputs/collocation_coefficients.json"
DEFAULT_PYTHON_OUTPUT = REPO_ROOT / "src/bergner_spichtinger_2026/collocation_coefficients.py"
DEFAULT_CPP_OUTPUT = (
    REPO_ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp"
)
GENERATOR_PATH = (
    "episodes/008-figure5-periodic-orbit-continuation/scripts/"
    "generate_collocation_coefficients.py"
)
SCHEMA_VERSION = "1.0.0"
STAGE_COUNTS = (1, 2, 3)
DECIMAL_SIGNIFICANT_DIGITS = 17


def _sorted_real_roots(polynomial: sp.Expr, variable: sp.Symbol) -> list[sp.Expr]:
    roots = sp.solve(polynomial, variable)
    if len(roots) != sp.degree(polynomial, variable):
        raise RuntimeError(f"Expected all roots of {polynomial}, got {roots}")
    roots = [sp.simplify(root) for root in roots]
    if any(root.is_real is not True for root in roots):
        raise RuntimeError(f"Expected real roots, got {roots}")
    return sorted(roots, key=lambda root: float(sp.N(root, 30)))


def _lagrange_basis(nodes: Sequence[sp.Expr], variable: sp.Symbol) -> list[sp.Expr]:
    basis: list[sp.Expr] = []
    for j, node in enumerate(nodes):
        factors = [
            (variable - other) / (node - other)
            for k, other in enumerate(nodes)
            if k != j
        ]
        basis.append(sp.factor(sp.prod(factors)))
    return basis


def _symbolic(value: sp.Expr) -> str:
    return sp.sstr(sp.simplify(value))


def _decimal(value: sp.Expr) -> str:
    numeric = float(sp.N(value, 30))
    if numeric == 0.0:
        numeric = 0.0
    return format(numeric, ".16e")


def _map_nested(value: Any, transform: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_map_nested(item, transform) for item in value]
    return transform(value)


def _quantity(value: Any) -> dict[str, Any]:
    return {
        "symbolic": _map_nested(value, _symbolic),
        "decimal": _map_nested(value, _decimal),
    }


def _polynomial_coefficients(
    polynomials: Iterable[sp.Expr], variable: sp.Symbol, degree: int
) -> list[list[sp.Expr]]:
    rows: list[list[sp.Expr]] = []
    for expression in polynomials:
        polynomial = sp.Poly(sp.expand(expression), variable)
        rows.append([sp.simplify(polynomial.nth(power)) for power in range(degree + 1)])
    return rows


def derive_rule(stage_count: int) -> dict[str, Any]:
    """Derive one shifted Gauss--Legendre collocation rule exactly."""
    if stage_count not in STAGE_COUNTS:
        raise ValueError(f"Unsupported Gauss--Legendre stage count: {stage_count}")

    tau = sp.Symbol("tau")
    shifted_legendre = sp.legendre(stage_count, 2 * tau - 1)
    nodes = _sorted_real_roots(shifted_legendre, tau)
    lagrange = _lagrange_basis(nodes, tau)
    transfer = [sp.integrate(polynomial, (tau, 0, tau)) for polynomial in lagrange]
    stage_coefficients = [
        [sp.simplify(polynomial.subs(tau, node)) for polynomial in transfer]
        for node in nodes
    ]
    weights = [sp.simplify(polynomial.subs(tau, 1)) for polynomial in transfer]
    transfer_coefficients = _polynomial_coefficients(transfer, tau, stage_count)

    # The (r + 1)-point Gauss rule is derived independently from the active
    # r-stage rule.  Its nodes are all interior and do not coincide with the
    # active collocation nodes for r = 1, 2, or 3.
    check_polynomial = sp.legendre(stage_count + 1, 2 * tau - 1)
    check_nodes = _sorted_real_roots(check_polynomial, tau)
    check_lagrange_values = [
        [sp.simplify(polynomial.subs(tau, node)) for polynomial in lagrange]
        for node in check_nodes
    ]
    check_transfer_values = [
        [sp.simplify(polynomial.subs(tau, node)) for polynomial in transfer]
        for node in check_nodes
    ]

    return {
        "id": f"gauss_legendre_{stage_count}",
        "family": "gauss-legendre",
        "stage_count": stage_count,
        "formal_order": 2 * stage_count,
        "nodes": _quantity(nodes),
        "stage_coefficients": _quantity(stage_coefficients),
        "quadrature_weights": _quantity(weights),
        "integrated_lagrange": {
            "variable": "tau",
            "coefficient_order": "ascending powers",
            "expressions": [_symbolic(expression) for expression in transfer],
            "coefficients": _quantity(transfer_coefficients),
        },
        "defect_check": {
            "construction": "shifted Gauss-Legendre rule with stage_count + 1 nodes",
            "node_count": stage_count + 1,
            "nodes": _quantity(check_nodes),
            "lagrange_evaluation": _quantity(check_lagrange_values),
            "integrated_lagrange_evaluation": _quantity(check_transfer_values),
        },
    }


def _canonical_payload_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def payload_checksum(payload: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 for an artifact payload without checksum."""
    return hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()


def build_artifact() -> dict[str, Any]:
    """Build the canonical language-neutral coefficient artifact."""
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR_PATH,
        "numeric_representation": {
            "kind": "IEEE-754 binary64 source literals",
            "decimal_significant_digits": DECIMAL_SIGNIFICANT_DIGITS,
            "format": ".16e",
        },
        "rules": [derive_rule(stage_count) for stage_count in STAGE_COUNTS],
    }
    return {
        **payload,
        "checksum": {
            "algorithm": "sha256",
            "canonicalization": "sorted-key compact UTF-8 JSON excluding checksum",
            "value": payload_checksum(payload),
        },
    }


def render_artifact(artifact: Mapping[str, Any]) -> str:
    return json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _python_tuple(value: Any, *, indent: int = 0) -> str:
    if isinstance(value, list):
        if not value:
            return "()"
        if all(not isinstance(item, list) for item in value):
            suffix = "," if len(value) == 1 else ""
            return "(" + ", ".join(str(item) for item in value) + suffix + ")"
        inner = ",\n".join(
            " " * (indent + 4) + _python_tuple(item, indent=indent + 4) for item in value
        )
        return "(\n" + inner + ",\n" + " " * indent + ")"
    return str(value)


def render_python(artifact: Mapping[str, Any]) -> str:
    checksum = artifact["checksum"]["value"]
    lines = [
        '"""Generated Gauss--Legendre collocation tables; do not edit by hand.\n',
        f"Generator: {GENERATOR_PATH}\n",
        'Runtime dependency: Python standard library only.\n"""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from types import MappingProxyType",
        "from typing import Final, Mapping",
        "",
        f'ARTIFACT_SCHEMA_VERSION: Final = "{artifact["schema_version"]}"',
        f'ARTIFACT_SHA256: Final = "{checksum}"',
        "",
        "",
        "@dataclass(frozen=True)",
        "class CollocationRule:",
        '    """Binary64 tables; matrices index ``[evaluation_point][stage]``.',
        "",
        "    ``transfer_coefficients[stage][power]`` uses ascending powers of the",
        '    element-local coordinate ``tau``.',
        '    """',
        "",
        "    family: str",
        "    stage_count: int",
        "    formal_order: int",
        "    nodes: tuple[float, ...]",
        "    stage_coefficients: tuple[tuple[float, ...], ...]",
        "    quadrature_weights: tuple[float, ...]",
        "    transfer_coefficients: tuple[tuple[float, ...], ...]",
        "    defect_check_nodes: tuple[float, ...]",
        "    defect_lagrange_evaluation: tuple[tuple[float, ...], ...]",
        "    defect_transfer_evaluation: tuple[tuple[float, ...], ...]",
        "",
        "",
        "_GAUSS_LEGENDRE_RULES = {",
    ]
    for rule in artifact["rules"]:
        stage_count = rule["stage_count"]
        lines.extend(
            [
                f"    {stage_count}: CollocationRule(",
                f'        family="{rule["family"]}",',
                f"        stage_count={stage_count},",
                f"        formal_order={rule['formal_order']},",
                "        nodes=" + _python_tuple(rule["nodes"]["decimal"], indent=8) + ",",
                "        stage_coefficients="
                + _python_tuple(rule["stage_coefficients"]["decimal"], indent=8)
                + ",",
                "        quadrature_weights="
                + _python_tuple(rule["quadrature_weights"]["decimal"], indent=8)
                + ",",
                "        transfer_coefficients="
                + _python_tuple(
                    rule["integrated_lagrange"]["coefficients"]["decimal"], indent=8
                )
                + ",",
                "        defect_check_nodes="
                + _python_tuple(rule["defect_check"]["nodes"]["decimal"], indent=8)
                + ",",
                "        defect_lagrange_evaluation="
                + _python_tuple(
                    rule["defect_check"]["lagrange_evaluation"]["decimal"], indent=8
                )
                + ",",
                "        defect_transfer_evaluation="
                + _python_tuple(
                    rule["defect_check"]["integrated_lagrange_evaluation"]["decimal"],
                    indent=8,
                )
                + ",",
                "    ),",
            ]
        )
    lines.extend(
        [
            "}",
            "GAUSS_LEGENDRE_RULES: Final[Mapping[int, CollocationRule]] = MappingProxyType(",
            "    _GAUSS_LEGENDRE_RULES",
            ")",
            "",
            "",
            "def gauss_legendre_rule(stage_count: int) -> CollocationRule:",
            '    """Return the generated Gauss--Legendre rule for 1, 2, or 3 stages."""',
            "    try:",
            "        return _GAUSS_LEGENDRE_RULES[stage_count]",
            "    except KeyError as exc:",
            "        raise ValueError(",
            '            f"Unsupported Gauss--Legendre stage count: {stage_count}; expected 1, 2, or 3"',
            "        ) from exc",
            "",
        ]
    )
    return "\n".join(lines)


def _cpp_rows(rows: Sequence[Sequence[str]], indent: str = "      ") -> str:
    return ",\n".join(indent + "{" + ", ".join(row) + "}" for row in rows)


def render_cpp(artifact: Mapping[str, Any]) -> str:
    checksum = artifact["checksum"]["value"]
    lines = [
        "// Generated Gauss--Legendre collocation tables; do not edit by hand.",
        f"// Generator: {GENERATOR_PATH}",
        "// Runtime dependency: C++ standard library only.",
        "#pragma once",
        "",
        "#include <cstddef>",
        "",
        "namespace bs2026_loca {",
        "namespace collocation {",
        "",
        f'inline constexpr char artifact_schema_version[] = "{artifact["schema_version"]}";',
        f'inline constexpr char artifact_sha256[] = "{checksum}";',
        "",
        "template <std::size_t Stages>",
        "struct GaussLegendreRule;",
        "",
    ]
    for rule in artifact["rules"]:
        n = rule["stage_count"]
        q = rule["defect_check"]["node_count"]
        nodes = rule["nodes"]["decimal"]
        stage = rule["stage_coefficients"]["decimal"]
        weights = rule["quadrature_weights"]["decimal"]
        transfer = rule["integrated_lagrange"]["coefficients"]["decimal"]
        check_nodes = rule["defect_check"]["nodes"]["decimal"]
        check_lagrange = rule["defect_check"]["lagrange_evaluation"]["decimal"]
        check_transfer = rule["defect_check"]["integrated_lagrange_evaluation"]["decimal"]
        lines.extend(
            [
                "template <>",
                f"struct GaussLegendreRule<{n}> {{",
                f"  inline static constexpr std::size_t stage_count = {n};",
                f"  inline static constexpr std::size_t formal_order = {2 * n};",
                f"  inline static constexpr std::size_t defect_check_count = {q};",
                '  inline static constexpr char family[] = "gauss-legendre";',
                f"  inline static constexpr double nodes[{n}] = {{{', '.join(nodes)}}};",
                f"  inline static constexpr double stage_coefficients[{n}][{n}] = {{",
                _cpp_rows(stage),
                "  };",
                f"  inline static constexpr double quadrature_weights[{n}] = "
                + "{" + ", ".join(weights) + "};",
                f"  inline static constexpr double transfer_coefficients[{n}][{n + 1}] = {{",
                _cpp_rows(transfer),
                "  };",
                f"  inline static constexpr double defect_check_nodes[{q}] = "
                + "{" + ", ".join(check_nodes) + "};",
                f"  inline static constexpr double defect_lagrange_evaluation[{q}][{n}] = {{",
                _cpp_rows(check_lagrange),
                "  };",
                f"  inline static constexpr double defect_transfer_evaluation[{q}][{n}] = {{",
                _cpp_rows(check_transfer),
                "  };",
                "};",
                "",
            ]
        )
    lines.extend(["}  // namespace collocation", "}  // namespace bs2026_loca", ""])
    return "\n".join(lines)


def generated_texts() -> dict[str, str]:
    artifact = build_artifact()
    return {
        "artifact": render_artifact(artifact),
        "python": render_python(artifact),
        "cpp": render_cpp(artifact),
    }


def _paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "artifact": args.artifact,
        "python": args.python_output,
        "cpp": args.cpp_output,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--python-output", type=Path, default=DEFAULT_PYTHON_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=DEFAULT_CPP_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail without writing if any committed generated artifact differs",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    texts = generated_texts()
    paths = _paths(args)
    encoded = {name: text.encode("utf-8") for name, text in texts.items()}
    stale = [
        name
        for name, path in paths.items()
        if not path.is_file() or path.read_bytes() != encoded[name]
    ]
    if args.check:
        if stale:
            details = ", ".join(f"{name} ({paths[name]})" for name in stale)
            raise SystemExit(f"Generated collocation artifacts are missing or stale: {details}")
        print("Generated collocation artifacts are current.")
        return

    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded[name])
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
