"""Independent joined checks using an immutable, bounded source snapshot."""
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
    "tests/test_literature_completion_time_inputs.py",
    "tests/test_literature_completion_time_storage.py",
    "tests/test_literature_completion_time_integration.py",
    "tests/test_literature_product_partition_inputs.py",
    "tests/test_literature_product_partition_storage.py",
    "tests/test_literature_product_partition_integration.py",
    "tests/test_a105_partition_time_joined_149.py",
    "tests/test_communication.py",
    "tests/test_literature_rate_meaning_delivery_143.py",
    "tests/test_literature_parent_population_information.py",
    "tests/test_literature_prompt_surface_144.py",
    "tests/test_literature_amount_integration.py",
    "tests/test_literature_binding_interaction_model_integration.py",
]


def main():
    report = HERE / "ROOT_JOINED_001.xml"
    if report.exists():
        raise RuntimeError("Never overwrite a retained test invocation")
    files = json.loads((HERE / "PIN_001.json").read_text())["files"]
    start = time.monotonic()
    code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
                       "--basetemp=" + str(HERE / "run001"),
                       "--junitxml=" + str(report), *SELECTION])
    imports = {}
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and name.startswith(("gene_annotation_episode", "method_loop", "test_")):
            imports[name] = str(Path(file).resolve())
    outside = {name: file for name, file in imports.items() if not Path(file).is_relative_to(PIN)}
    changed = [name for name, digest in files.items()
               if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
    result = {"pytest_exit_code": int(code), "elapsed_seconds": time.monotonic() - start,
              "selection": SELECTION, "pinned_file_count": len(files),
              "changed_pinned_files": changed, "imported_module_count": len(imports),
              "imports_outside_pin": outside,
              "scope": "Reader arithmetic, custody, typed delivery, configured binding reconstruction and compatibility engineering. Controlled decisions are fixtures; this is not an actual-model scientific investigation or A105 adequacy claim."}
    (HERE / "ROOT_IMPORTS_001.json").write_text(json.dumps(imports, indent=2) + "\n")
    (HERE / "ROOT_RESULT_001.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
