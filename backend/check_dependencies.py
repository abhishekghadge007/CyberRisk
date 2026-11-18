import ast
import sys
import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).parent

stdlib = sys.stdlib_module_names
local_modules = {
    file.stem for file in BASE_DIR.glob("*.py")
}

local_packages = {
    folder.name
    for folder in BASE_DIR.iterdir()
    if folder.is_dir() and folder.name != ".venv"
}

imports = set()

for file in BASE_DIR.rglob("*.py"):

    if ".venv" in file.parts or "__pycache__" in file.parts:
        continue

    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"Could not inspect {file}: {error}")
        continue

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for item in node.names:
                imports.add(item.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                imports.add(node.module.split(".")[0])

missing = []

for module in sorted(imports):

    if module in stdlib:
        continue

    if module in local_modules or module in local_packages:
        continue

    try:
        if importlib.util.find_spec(module) is None:
            missing.append(module)
    except (ImportError, ValueError, ModuleNotFoundError):
        missing.append(module)

print("\n========== DEPENDENCY AUDIT ==========")

if missing:
    print("\nPotentially missing external modules:")
    for module in missing:
        print("-", module)
else:
    print("\nNo missing imports detected.")

print("\n========== AUDIT COMPLETE ==========")
