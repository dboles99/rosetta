"""The decision layer is optional: no existing core module may import it, and it may
not import any networking module. These are the offline and default-off invariants."""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "rosetta_core"
NETWORK_MODULES = {"socket", "ssl", "urllib", "http", "requests", "httpx", "aiohttp"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            names.add(f"{prefix}{node.module or ''}")
    return names


def test_existing_core_modules_do_not_import_the_decision_layer():
    for path in PACKAGE.glob("*.py"):
        for name in _imports(path):
            assert "decision" not in name, f"{path.name} imports {name}"


def test_decision_layer_has_no_network_imports():
    decision_files = list((PACKAGE / "decision").glob("*.py"))
    assert decision_files, "decision package not found"
    for path in decision_files:
        for name in _imports(path):
            root = name.lstrip(".").split(".")[0]
            assert root not in NETWORK_MODULES, f"{path.name} imports {name}"
