from pathlib import Path
import hashlib
import json
import sys

def pytest_sessionfinish(session, exitstatus):
    pin = Path(__file__).resolve().parent
    imports = {}
    misplaced = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if not path.is_file():
            continue
        imports[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if name == "gene_annotation_episode" or name.startswith("gene_annotation_episode."):
            if not path.is_relative_to(pin):
                misplaced.append(name)
    receipt = {"pytest_exitstatus": int(exitstatus), "imports": imports, "misplaced_package_imports": misplaced,
        "executable": sys.executable, "version": sys.version}
    with (pin.parent / "ACTUAL_IMPORTS_008.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    if misplaced:
        session.exitstatus = 1
