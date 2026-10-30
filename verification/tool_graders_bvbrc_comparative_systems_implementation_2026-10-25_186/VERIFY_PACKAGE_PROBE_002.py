"""Complete the installed probe using the already verified unchanged wheel.

Attempt001 preserved a harness error: JSON arrays were not restored to the two
tuple inputs required by the actual provider ABI. No production source changes.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

from VERIFY_WORKFLOW_001 import CANDIDATE, HERE, save, sha, snapshot

assert len(sys.argv) == 2
expected_pin = sys.argv[1]
prior = HERE / "package_verification_001"
old = json.loads((prior / "receipt.json").read_text())
before = snapshot()
assert old["build_exit_code"] == 0 and not old["changed_sources"]
assert before == json.loads((prior / "source_before.json").read_text())
assert before == json.loads((prior / "source_after.json").read_text())
wheel, = (prior / "wheel").glob("*.whl")
assert sha(wheel) == old["wheel_sha256"]
installed = prior / "extracted_wheel"
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        if name.startswith(("gene_annotation_episode/", "method_loop/")) and not name.endswith("/"):
            assert archive.read(name) == (installed / name).read_bytes() == (CANDIDATE / name).read_bytes(), name
out = HERE / "package_verification_002"
out.mkdir(exist_ok=False)
save(out / "source_before.json", before)
specimen = HERE / "evidence_p/FILLED_PROVIDER_INPUT_003.json"
expected = HERE / "evidence_p/FILLED_PROVIDER_RESULT_003.json"
command = [sys.executable, "-I", str(HERE / "PACKAGE_PROBE_002.py"), str(installed),
           str(specimen), str(expected), expected_pin]
save(out / "command.json", {"argv": command, "cwd": str(out)})
receipt = {"passed": False, "started_at": datetime.now(timezone.utc).isoformat(),
    "harness_sha256": sha(Path(__file__)), "probe_sha256": sha(HERE / "PACKAGE_PROBE_002.py"),
    "provider_sha256": expected_pin, "wheel_sha256": sha(wheel),
    "original_build_receipt_sha256": sha(prior / "receipt.json"),
    "specimen_sha256": sha(specimen), "expected_result_sha256": sha(expected),
    "live_service_execution_verified": False, "authenticated_publication_verified": False}
clock = time.monotonic()
try:
    checked = subprocess.run(command, cwd=out, capture_output=True, text=True)
    for name, value in (("stdout.log", checked.stdout), ("stderr.log", checked.stderr)):
        with (out / name).open("x") as stream:
            stream.write(value)
    receipt["installed_exit_code"] = checked.returncode
    assert checked.returncode == 0, "installed provider probe failed"
    answer = json.loads(checked.stdout)
    save(out / "installed_result.json", answer)
    receipt.update(passed=True, installed_result_sha256=sha(out / "installed_result.json"),
        numerical_answers={key: answer[key] for key in ("native_percent", "later_percent", "later_operands",
            "native_reference_operands", "later_reference_operands", "active_genome_count", "reference_release")})
except Exception as error:
    receipt.update(error_type=type(error).__name__, error=str(error))
finally:
    after = snapshot()
    save(out / "source_after.json", after)
    changes = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - clock,
                   source_count=len(before), changed_sources=changes)
    receipt["passed"] = receipt["passed"] and not changes
    save(out / "receipt.json", receipt)
    print(json.dumps(receipt))
sys.exit(0 if receipt["passed"] else 1)
