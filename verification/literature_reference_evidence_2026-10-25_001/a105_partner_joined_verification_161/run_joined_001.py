"""Rerun existing primary-reader cases with complete frozen fixture inputs."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_001"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]
os.chdir(PIN)
import pytest

SELECTION = [
    "tests/test_literature_partner_interpretation_task_160.py",
    "tests/test_literature_partner_calculations.py::test_baseline_copy_cannot_manufacture_an_addback",
    "tests/test_literature_partner_calculations.py::test_missing_addback_preserves_the_two_arm_contrast",
    "tests/test_literature_partner_calculations.py::test_same_physical_measurement_is_not_an_independent_role",
    "tests/test_literature_partner_calculations.py::test_one_sided_condition_factor_is_missing_information_not_a_difference",
    "tests/test_literature_partner_operand_bindings.py::test_actual_typed_subset_next_decisions_and_first_readonly_reconstruction",
    "tests/test_literature_partner_integration.py::test_partner_task_repeats_after_lookup_delta_and_reconstruction",
    "tests/test_literature_partner_native_integration.py::test_native_task_repeats_across_lookup_and_restoration"
]

def main():
    report = HERE / "ROOT_JOINED_001.xml"
    if report.exists():
        raise RuntimeError("Never overwrite a retained invocation")
    files = json.loads((HERE / "PIN_001.json").read_text())["files"]
    started = time.monotonic()
    code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp=" + str(HERE / "run001"), "--junitxml=" + str(report), *SELECTION])
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
        "scope": "Root frozen verification of recurring partner scientific TASK, partial comparisons, shared/addback identity, ordinary scoped return and read-only reconstruction. Synthetic engineering checks, not configured-model interpretation or A105 adequacy."}
    (HERE / "ROOT_IMPORTS_001.json").write_text(json.dumps(imports, indent=2) + "\n")
    (HERE / "ROOT_RESULT_001.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
