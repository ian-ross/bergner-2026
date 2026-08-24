#!/usr/bin/env python3
"""Validate Episode 008 Figure 5 production-v1 JSON artifacts.

Examples
--------

Validate one artifact and verify recorded file checksums relative to the
repository root::

    uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
        episodes/008-figure5-periodic-orbit-continuation/outputs/example.json

Print the machine-readable contract used by the validator::

    uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py --print-contract
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bergner_spichtinger_2026.episode8_production_schema import (
    ProductionSchemaValidationError,
    canonical_json_bytes,
    production_schema_contract,
    validate_production_artifact,
)

ROOT = Path(__file__).resolve().parents[3]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: production artifact must be a JSON object")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="*", type=Path, help="JSON artifact or manifest paths to validate")
    parser.add_argument("--root", type=Path, default=ROOT, help="root used for relative checksum paths")
    parser.add_argument("--no-checksums", action="store_true", help="validate schema shape without verifying referenced file hashes")
    parser.add_argument("--print-contract", action="store_true", help="print the production-v1 schema contract as canonical JSON")
    args = parser.parse_args()

    if args.print_contract:
        sys.stdout.buffer.write(canonical_json_bytes(production_schema_contract()))
        if not args.artifacts:
            return

    if not args.artifacts:
        parser.error("provide at least one artifact path or --print-contract")

    failed = False
    for path in args.artifacts:
        artifact = load_json(path)
        try:
            validate_production_artifact(
                artifact,
                root=args.root,
                artifact_path=path,
                verify_checksums=not args.no_checksums,
            )
        except ProductionSchemaValidationError as exc:
            failed = True
            print(f"{path}: INVALID", file=sys.stderr)
            print(exc, file=sys.stderr)
        else:
            print(f"{path}: valid")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
