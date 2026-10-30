"""Rerun existing primary-reader cases with complete frozen fixture inputs."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_003"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]
os.chdir(PIN)
import pytest

SELECTION = [
    "tests/test_literature_partner_native_integration.py::test_native_selected_and_saved_only_reconstruction_without_prepared_json[primary_native]",
    "tests/test_literature_partner_native_integration.py::test_native_ordinary_typed_parent_receives_actual_source_bindings[primary_native]",
    "tests/test_literature_partner_defined_integration.py::test_primary_defined_units_are_selected_and_saved_without_a_numeric_recipe",
    "tests/test_literature_partner_defined_integration.py::test_primary_defined_units_reach_the_actual_ordinary_parent_form"
]


def main():
    report = HERE / "ROOT_JOINED_003.xml"
    if report.exists():
        raise RuntimeError("Never overwrite a retained invocation")
    files = json.loads((HERE / "PIN_003.json").read_text())["files"]
    started = time.monotonic()
    code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp=" + str(HERE / "run003"), "--junitxml=" + str(report), *SELECTION])
    imports = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and name.startswith(("gene_annotation_episode", "method_loop", "test_")):
            imports[name] = str(Path(filename).resolve())
    outside = {name: filename for name, filename in imports.items()
        if not Path(filename).is_relative_to(PIN)}
    changed = [name for name, digest in files.items()
        if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
    result = {"pytest_exit_code": int(code), "elapsed_seconds": time.monotonic() - started,
        "selection": SELECTION, "pinned_file_count": len(files),
        "changed_pinned_files": changed, "imported_module_count": len(imports),
        "imports_outside_pin": outside,
        "scope": "Synthetic engineering verification of table scalar reading, missing input semantics, exact historical records, selected typed returns and saved reconstruction. Not scientific assay coverage or A105 adequacy."}
    (HERE / "ROOT_IMPORTS_003.json").write_text(json.dumps(imports, indent=2) + "\n")
    (HERE / "ROOT_RESULT_003.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
