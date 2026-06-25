from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/004-figure1-loca-continuation"


def test_episode4_scaffold_contains_expected_episode_local_directories():
    expected_directories = {
        "docs",
        "scripts",
        "loca",
        "notebooks",
        "outputs",
    }

    assert EPISODE_ROOT.is_dir()
    assert expected_directories.issubset(
        {path.name for path in EPISODE_ROOT.iterdir() if path.is_dir()}
    )
    for placeholder_dir in ("scripts", "notebooks", "outputs"):
        assert (EPISODE_ROOT / placeholder_dir / ".gitkeep").is_file()


def test_episode4_readme_documents_goal_references_commands_and_scope():
    readme = (EPISODE_ROOT / "README.md").read_text(encoding="utf-8")

    assert "LOCA/Trilinos" in readme
    assert "Episode 2 Python-native continuation" in readme
    assert "Episode 3 AUTO-07p" in readme
    assert "uv run pytest" in readme
    assert "outputs/figure1_loca_branches/" in readme
    assert "Do not promote C++/Trilinos code" in readme


def test_episode4_planning_doc_records_loca_design_and_output_contract():
    planning = (EPISODE_ROOT / "docs/planning-decisions.md").read_text(encoding="utf-8")

    for required_phrase in (
        "serial dense LOCA",
        "LAPACK-backed dense linear algebra",
        "Sacado automatic differentiation",
        "Python as the semantic model reference",
        "backend-neutral branch schema",
        "Trilinos version",
        "LOCA-vs-Python",
        "LOCA-vs-AUTO",
    ):
        assert required_phrase in planning


def test_episode4_loca_assets_remain_episode_local():
    loca_readme = (EPISODE_ROOT / "loca/README.md").read_text(encoding="utf-8")

    assert "episode" in loca_readme.lower()
    assert "do not promote" in loca_readme.lower()
    assert not (REPO_ROOT / "loca").exists()
