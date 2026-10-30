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
    "tests/test_literature_rate_replicate_binding_163.py",
    "tests/test_literature_rate_replicates.py",
    "tests/test_literature_rate_episode_integration.py::test_binding_validates_saved_values_and_forwarding_copies_only_admitted_subset",
    "tests/test_literature_rate_episode_integration.py::test_saved_descriptor_reconstructs_original_opt_in_and_replay_avoids_refit",
    "tests/test_literature_completion_time_integration.py::test_mixed_completion_time_and_existing_native_rate_view_keep_both_scientific_families"
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
        "scope": "Root frozen verification of existing raw statistics plus new selected operation, source-only typed admission, scoped possession, recurring child TASK and saved reconstruction. Synthetic checks, not primary-case integration or A105 adequacy."}
    (HERE / "ROOT_IMPORTS_001.json").write_text(json.dumps(imports, indent=2) + "\n")
    (HERE / "ROOT_RESULT_001.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)


if __name__ == "__main__":
    raise SystemExit(main())
