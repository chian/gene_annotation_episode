"""Independent tests of the frozen corrections; no configured model calls."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_002"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]
os.chdir(PIN)
import pytest

SELECTION = [
    "tests/test_literature_missing_input_semantics_156.py",
    "tests/test_literature_structural_scalar_contexts.py",
    "tests/test_literature_activity_calculations.py",
    "tests/test_literature_assay_inputs.py",
    "tests/test_literature_assay_integration.py",
    "tests/test_literature_quantity_integration.py",
    "tests/test_literature_source_locations.py",
    "tests/test_literature_rate_storage.py",
    "tests/test_literature_rate_native_inputs.py",
    "tests/test_literature_rate_native_storage.py",
    "tests/test_literature_rate_native_integration.py",
    "tests/test_literature_rate_meaning_delivery_143.py",
    "tests/test_literature_partner_source_fields.py",
    "tests/test_literature_partner_defined_units.py",
    "tests/test_literature_partner_defined_inputs.py",
    "tests/test_literature_numeric_range_scope.py",
    "tests/test_literature_partner_native_inputs.py",
    "tests/test_literature_partner_native_storage.py",
    "tests/test_literature_partner_native_integration.py",
    "tests/test_literature_partner_defined_integration.py",
    "tests/test_literature_reaction_native_inputs_129.py",
    "tests/test_literature_reaction_native_integration_129.py",
    "tests/test_literature_context_native_observations.py",
    "tests/test_literature_context_native_integration.py",
    "tests/test_literature_kinetic_inputs.py",
    "tests/test_literature_optical_inputs.py",
    "tests/test_a105_native_binding_dependency_142.py",
    "tests/test_literature_binding_interaction_storage.py",
    "tests/test_literature_binding_interaction_integration.py",
    "tests/test_literature_transport_integration.py",
    "tests/test_literature_active_site_integration.py",
    "tests/test_a105_partition_time_joined_149.py",
    "tests/test_communication.py",
]


def main():
    report = HERE / "ROOT_JOINED_002.xml"
    if report.exists():
        raise RuntimeError("Never overwrite a retained invocation")
    files = json.loads((HERE / "PIN_002.json").read_text())["files"]
    started = time.monotonic()
    code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp=" + str(HERE / "run002"), "--junitxml=" + str(report), *SELECTION])
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
    (HERE / "ROOT_IMPORTS_002.json").write_text(json.dumps(imports, indent=2) + "\n")
    (HERE / "ROOT_RESULT_002.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
