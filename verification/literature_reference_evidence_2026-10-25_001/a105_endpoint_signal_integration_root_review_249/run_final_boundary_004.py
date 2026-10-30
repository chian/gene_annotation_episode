"""Root-owned scoped execution against the final244 pin after its late fixes."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKET = HERE.parent / "a105_endpoint_signal_binding_244"
PIN = PACKET / "pin_005"
hashes = json.loads((PACKET / "PIN_005.json").read_text())["hashes"]

def verify():
    for name, digest in hashes.items():
        assert hashlib.sha256((PIN / name).read_bytes()).hexdigest() == digest, name

verify()
os.chdir(PIN)
sys.path[:0] = [str(PIN), str(PIN / "tests")]
import pytest

test = "tests/test_literature_endpoint_signal_binding_244.py::"
targets = [test + name for name in [
    "test_external_covariance_support_cannot_hydrate_unrequested_numbers",
    "test_wrong_source_record_kind_returns_normal_repair_feedback",
    "test_failed_endpoint_history_keeps_task_and_withholds_original_input_dump",
    "test_selected_shared_loop_and_first_readonly_composer[None-True-True]",
]]
started = time.monotonic()
with (HERE / "ROOT_FINAL_BOUNDARY_004.log").open("x") as log:
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        code = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
                            "--basetemp=" + str(HERE / "root_final_boundary_state_004"),
                            "--junitxml=" + str(HERE / "ROOT_FINAL_BOUNDARY_004.xml"), *targets])
verify()
imports = {}
for module in list(sys.modules.values()):
    filename = getattr(module, "__file__", None)
    if not filename:
        continue
    path = Path(filename).resolve()
    if path.is_relative_to(PIN) and path.is_file():
        relative = str(path.relative_to(PIN))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashes.get(relative) == digest, relative
        imports[relative] = digest
    elif getattr(module, "__name__", None) != "__main__" and path.is_relative_to(ROOT) and not path.is_relative_to(Path(sys.prefix)) and path.suffix == ".py":
        raise AssertionError("Project import escaped final pin: " + str(path))
result = {"status": "terminal", "exit_code": int(code), "seconds": time.monotonic() - started,
          "targets": targets, "pin_manifest_sha256": hashlib.sha256((PACKET / "PIN_005.json").read_bytes()).hexdigest(),
          "all_2091_input_hashes_unchanged": True, "actual_local_imports": imports,
          "controlled_fixture": True, "actual_model_execution": False,
          "private_provider_payloads_read": False, "A105_complete": False}
with (HERE / "ROOT_FINAL_BOUNDARY_004.json").open("x") as output:
    json.dump(result, output, indent=2)
    output.write("\n")
print(json.dumps({"exit_code": int(code), "seconds": result["seconds"], "actual_imports": len(imports)}))
raise SystemExit(code)
