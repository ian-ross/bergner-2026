import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes/004-figure1-loca-continuation/scripts/create_loca_compile_commands.py"
LOCA_ROOT = REPO_ROOT / "loca"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("create_loca_compile_commands", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_loca_cmake_exports_compile_commands_by_default():
    cmake = (LOCA_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

    assert "CMAKE_EXPORT_COMPILE_COMMANDS ON" in cmake
    assert "compile_commands.json" in cmake


def test_loca_compile_commands_helper_configures_cmake_export():
    module = _load_script_module()

    command = module.cmake_configure_command(Path("build/loca-lsp"), Path("/trilinos/cmake"))

    assert command[:3] == ["cmake", "-S", str(LOCA_ROOT)]
    assert "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in command
    assert "-DTrilinos_DIR=/trilinos/cmake" in command


def test_loca_compile_commands_helper_installs_editor_friendly_links(tmp_path):
    module = _load_script_module()
    source = tmp_path / "build" / "compile_commands.json"
    source.parent.mkdir()
    source.write_text("[]\n", encoding="utf-8")
    repo_target = tmp_path / "compile_commands.json"
    loca_target = tmp_path / "loca" / "compile_commands.json"

    module.install_compilation_database(source, (repo_target, loca_target))

    assert repo_target.is_symlink()
    assert loca_target.is_symlink()
    assert repo_target.resolve() == source
    assert loca_target.resolve() == source


def test_episode4_docs_advertise_loca_compile_commands_helper():
    readme = (REPO_ROOT / "episodes/004-figure1-loca-continuation/README.md").read_text(encoding="utf-8")
    loca_readme = (REPO_ROOT / "episodes/004-figure1-loca-continuation/loca/README.md").read_text(encoding="utf-8")

    assert "create_loca_compile_commands.py" in readme
    assert "compile_commands.json" in readme
    assert "create_loca_compile_commands.py" in loca_readme
