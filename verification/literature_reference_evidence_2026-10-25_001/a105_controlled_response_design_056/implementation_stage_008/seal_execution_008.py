"""Own synthetic-only source-reader execution pin; no service/runtime launch."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PIN = HERE / "execution_pin_008"
TESTS = [
    "tests/test_literature_controlled_response_inputs.py",
    "tests/test_literature_controlled_response_calculations.py",
    "tests/test_literature_rate_native_inputs.py",
    "tests/test_literature_binding_visual_inputs.py",
]


def digest(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    # Import just these pure test modules to discover their actual package
    # dependency closure. No tests, episode, storage or service are executed here.
    sys.path.insert(0, str(ROOT))
    for name in TESTS:
        runpy.run_path(str(ROOT / name), run_name="_pin_discovery_" + Path(name).stem)
    files = set(TESTS)
    for name, module in list(sys.modules.items()):
        if name == "gene_annotation_episode" or name.startswith("gene_annotation_episode."):
            path = Path(module.__file__).resolve()
            files.add(str(path.relative_to(ROOT)))
    synthetic = "verification/literature_reference_evidence_2026-10-25_001/a105_controlled_response_design_056/reader_stage_007/"
    files.update(synthetic + name for name in ["COMPATIBILITY_RECEIPT_007.json", "SOURCE_TEXT_007.txt", "SELECTION_SCHEMA_007.json"])
    PIN.mkdir()
    original = {}
    for relative in sorted(files):
        source = ROOT / relative
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        original[relative] = {"original_path": str(source), **digest(source)}
    (PIN / "pytest.ini").write_text("[pytest]\n")
    # This hook records actual imports from the test process and rejects live
    # checkout package imports. It makes no scientific/custody claim.
    (PIN / "conftest.py").write_text('''from pathlib import Path
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
        stream.write("\\n")
    if misplaced:
        session.exitstatus = 1
''')
    pin_manifest = {str(p.relative_to(PIN)): digest(p) for p in sorted(PIN.rglob("*")) if p.is_file()}
    write_json(HERE / "PIN_MANIFEST_008.json", {"scope": "Four pure source/calculation suites, own invented fixture bytes; excludes kinetic storage/runtime suites", "original_files": original, "pin_files": pin_manifest})
    for path in PIN.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", str(PIN / "pytest.ini"), *TESTS]
    environment = os.environ.copy()
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    completed = subprocess.run(command, cwd=PIN, env=environment, capture_output=True, text=True)
    with (HERE / "TERMINAL_STDOUT_008.txt").open("x") as stream:
        stream.write(completed.stdout)
    with (HERE / "TERMINAL_STDERR_008.txt").open("x") as stream:
        stream.write(completed.stderr)
    write_json(HERE / "TERMINAL_008.json", {"command": command, "cwd": str(PIN), "exit_code": completed.returncode,
        "pytest_plugin_autoload": False, "python_bytecode": False, "pytest_cacheprovider": False,
        "interpreter": {"path": str(ROOT / ".venv/bin/python"), "resolved": str((ROOT / ".venv/bin/python").resolve()), **digest((ROOT / ".venv/bin/python").resolve())},
        "stdout": digest(HERE / "TERMINAL_STDOUT_008.txt"), "stderr": digest(HERE / "TERMINAL_STDERR_008.txt")})
    unchanged = all(digest(PIN / relative) == value for relative, value in pin_manifest.items())
    write_json(HERE / "PIN_AFTER_008.json", {"all_pinned_files_unchanged": unchanged,
        "extra_pin_files": sorted(str(p.relative_to(PIN)) for p in PIN.rglob("*") if p.is_file() and str(p.relative_to(PIN)) not in pin_manifest)})
    print(completed.stdout, end="")
    print("exit_code=" + str(completed.returncode))
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode or not unchanged:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
