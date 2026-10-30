"""Root's independent final-module verification on the immutable final pin."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

OUT = Path(__file__).resolve().parent
LIVE = OUT.parents[2]
OWNER = OUT.parent / "a105_reported_curve_binding_231"
PIN = OWNER / "pin_003"
MANIFEST = json.loads((OWNER / "PIN_003.json").read_text())


def verify():
    for relative, expected in MANIFEST["hashes"].items():
        assert hashlib.sha256((PIN / relative).read_bytes()).hexdigest() == expected, relative
    for name, expected in MANIFEST["external_original_state_dependencies"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name


verify()
os.chdir(PIN)
sys.path[:] = [str(PIN), str(PIN / "tests"), *[
    value for value in sys.path
    if value and Path(value).resolve() not in (LIVE, LIVE / "tests", OUT)
]]
import pytest

started = time.time()
result = pytest.main([
    "-q", "tests/test_literature_reported_curve_binding_231.py",
    "--basetemp", str(OUT / "test_state_001"), "-o", "cache_dir=" + str(OUT / "pytest_cache_001"),
    "--junitxml", str(OUT / "ROOT_JUNIT_001.xml"),
])
imports = {}
for name, module in list(sys.modules.items()):
    if name == "gene_annotation_episode" or name.startswith(("gene_annotation_episode.", "method_loop.")):
        filename = getattr(module, "__file__", None)
        if filename:
            path = Path(filename).resolve()
            relative = str(path.relative_to(PIN))
            assert relative in MANIFEST["hashes"], relative
            imports[name] = {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
verify()
record = {
    "exit_code": int(result), "elapsed_seconds": time.time() - started,
    "pin_manifest": str(OWNER / "PIN_003.json"), "traced_imports": imports,
    "all_imports_inside_pin": True, "all_pinned_and_external_files_unchanged": True,
    "test_module": "tests/test_literature_reported_curve_binding_231.py",
    "controlled_provider_fixtures": True, "actual_model_execution": False,
    "A105_adequate": False, "goal_complete": False,
}
with (OUT / "ROOT_RESULT_001.json").open("x") as handle:
    json.dump(record, handle, indent=2)
    handle.write("\n")
print(json.dumps({key: value for key, value in record.items() if key != "traced_imports"}))
sys.exit(int(result))
