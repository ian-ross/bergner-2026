#!/usr/bin/env python3
"""Create ``compile_commands.json`` links for LOCA C++ LSP support.

The top-level LOCA executable is built with CMake/Trilinos.  CMake writes the
compilation database into the build directory, while many editor LSP clients look
for ``compile_commands.json`` at either the repository root or the CMake project
root.  This helper configures the LOCA CMake project with
``CMAKE_EXPORT_COMPILE_COMMANDS=ON`` and then links (or copies) the generated
file to both convenient locations.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCA_ROOT = REPO_ROOT / "loca"
DEFAULT_BUILD_DIR = REPO_ROOT / ".pytest_cache" / "loca-lsp-build"
DEFAULT_TRILINOS_DIR = Path("/opt/Trilinos/lib64/cmake/Trilinos")
DEFAULT_LINK_TARGETS = (REPO_ROOT / "compile_commands.json", LOCA_ROOT / "compile_commands.json")


def cmake_configure_command(build_dir: Path, trilinos_dir: Path) -> list[str]:
    """Return the CMake configure command that emits a compilation database."""
    return [
        "cmake",
        "-S",
        str(LOCA_ROOT),
        "-B",
        str(build_dir),
        f"-DTrilinos_DIR={trilinos_dir}",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    ]


def _replace_existing_link_or_file(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        raise IsADirectoryError(f"Refusing to replace non-file path: {path}")


def _relative_symlink(source: Path, destination: Path) -> None:
    relative_source = os.path.relpath(source, start=destination.parent)
    destination.symlink_to(relative_source)


def install_compilation_database(source: Path, targets: tuple[Path, ...], *, copy: bool = False) -> None:
    """Install the build-directory compilation database at editor-friendly paths."""
    if not source.is_file():
        raise FileNotFoundError(f"CMake did not create {source}")
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        _replace_existing_link_or_file(target)
        if copy:
            shutil.copy2(source, target)
        else:
            _relative_symlink(source, target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR, help="CMake build directory to configure.")
    parser.add_argument("--trilinos-dir", type=Path, default=DEFAULT_TRILINOS_DIR, help="Directory containing TrilinosConfig.cmake.")
    parser.add_argument("--copy", action="store_true", help="Copy instead of symlinking compile_commands.json.")
    parser.add_argument(
        "--target",
        type=Path,
        action="append",
        dest="targets",
        help="Additional/alternative output path. May be passed more than once; defaults to repo root and loca/.",
    )
    args = parser.parse_args()

    build_dir = args.build_dir.resolve()
    trilinos_dir = args.trilinos_dir.resolve()
    targets = tuple(path.resolve() for path in args.targets) if args.targets else DEFAULT_LINK_TARGETS

    command = cmake_configure_command(build_dir, trilinos_dir)
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
        raise SystemExit(result.returncode)

    compile_commands = build_dir / "compile_commands.json"
    install_compilation_database(compile_commands, targets, copy=args.copy)
    print(f"Configured LOCA compilation database at {compile_commands}")
    for target in targets:
        print(f"Installed {target}")


if __name__ == "__main__":
    main()
