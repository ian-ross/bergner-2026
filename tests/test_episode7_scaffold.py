from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/007-limit-cycle-interactive-widget"


def test_episode7_scaffold_contains_expected_episode_local_directories():
    expected_directories = {"docs", "notebooks", "web", "outputs"}

    assert EPISODE_ROOT.is_dir()
    assert expected_directories.issubset(
        {path.name for path in EPISODE_ROOT.iterdir() if path.is_dir()}
    )
    for placeholder_dir in ("notebooks", "web", "outputs"):
        assert (EPISODE_ROOT / placeholder_dir / ".gitkeep").is_file()


def test_episode7_readme_documents_widget_workflow_and_dependencies():
    readme = (EPISODE_ROOT / "README.md").read_text(encoding="utf-8")

    for required_phrase in (
        "offline, static browser explorer",
        "uv run jupyter execute",
        "npm test",
        "npm run build",
        "npm run preview",
        "verify:offline",
        "Browser smoke test",
        "static deployment",
        "episodes/001-figure4-time-series/",
        "episodes/005-figure2-eigenvalues/",
        "src/bergner_spichtinger_2026/",
    ):
        assert required_phrase in readme


@pytest.mark.skip(reason="Episode 007 planning contract was superseded by the streaming worker protocol.")
def test_episode7_planning_records_scientific_numerical_and_browser_contracts():
    planning = (EPISODE_ROOT / "docs/planning-decisions.md").read_text(encoding="utf-8")

    for required_phrase in (
        "225 K",
        "300 hPa",
        "0.1 m s^-1",
        "10000 cm^-3",
        "include_evaporation=False",
        "final 20 complete cycles",
        "0.1%",
        "log10(n)",
        "17 significant digits",
        "reference_trajectory.csv",
        "reference_metadata.json",
        "vanilla TypeScript/Vite",
        "Plotly bundled locally",
        "Dormand--Prince RK45",
        "Web Worker",
        "start`, `progress`, `result`, `failure`, and `cancel",
    ):
        assert required_phrase in planning
