"""Independent joined checks against a fixed current source snapshot."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_002"
sys.path[:0] = [str(PIN), str(PIN / "tests")]
os.chdir(PIN)
import pytest

SELECTION = ['tests/test_literature_rate_meaning_delivery_143.py', 'verification/literature_reference_evidence_2026-10-25_001/a105_native_rate_meaning_delivery_143/test_primary_meaning_delivery_143.py', 'tests/test_literature_binding_interaction_model_integration.py', 'tests/test_literature_kinetic_model_integration.py::test_selected_child_to_parent_model_subset_and_ordinary_observations', 'tests/test_literature_binding_interaction_integration.py::test_actual_c4_admission_rollback_original_receipt_tamper_and_read_only_reopen', 'tests/test_literature_parent_population_information.py', 'tests/test_communication.py', 'tests/test_joined_native_context_reaction_render_129.py::test_joined_own_outcomes_and_typed_native_returns_keep_family_meanings']


def main():
    files = json.loads((HERE / "PIN_002.json").read_text())["files"]
    start = time.monotonic()
    code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
                       "--basetemp=" + str(HERE / "run002"),
                       "--junitxml=" + str(HERE / "ROOT_JOINED_002.xml"), *SELECTION])
    imports = {}
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and (name.startswith(("gene_annotation_episode", "method_loop", "test_"))
                     or name.endswith(("test_primary_delivery_139", "test_primary_meaning_delivery_143"))):
            imports[name] = str(Path(file).resolve())
    outside = {name: file for name, file in imports.items() if not Path(file).is_relative_to(PIN)}
    changed = [name for name, digest in files.items()
               if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
    result = {"pytest_exit_code": int(code), "elapsed_seconds": time.monotonic()-start,
              "selection": SELECTION, "pinned_file_count": len(files),
              "changed_pinned_files": changed, "imported_module_count": len(imports),
              "imports_outside_pin": outside,
              "scope": "Synthetic model/compatibility engineering plus published control values under scripted decisions/controllers; no actual-model science, full suite or A105 adequacy claim"}
    (HERE / "ROOT_JOINED_IMPORTS_002.json").write_text(json.dumps(imports, indent=2)+"\n")
    (HERE / "ROOT_JOINED_RESULT_002.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
