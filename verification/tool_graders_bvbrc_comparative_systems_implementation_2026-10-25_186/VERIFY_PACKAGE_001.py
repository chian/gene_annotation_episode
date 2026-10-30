"""Verify packaged ComparativeSystems code and data against the Workflow freeze."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

from VERIFY_WORKFLOW_001 import CANDIDATE, HERE, save, sha, snapshot


def main():
    assert len(sys.argv) == 3
    attempt, expected_pin = sys.argv[1:]
    freeze_path = HERE / ("final_workflow_" + attempt) / "source_before.json"
    before = snapshot()
    assert before == json.loads(freeze_path.read_text()), "candidate differs from Workflow source freeze"
    out = HERE / ("package_verification_" + attempt)
    out.mkdir(exist_ok=False)
    save(out / "source_before.json", before)
    specimen = HERE / "evidence_p/FILLED_PROVIDER_INPUT_003.json"
    expected = HERE / "evidence_p/FILLED_PROVIDER_RESULT_003.json"
    command = [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(out / "wheel"), str(CANDIDATE)]
    save(out / "command.json", {"argv": command, "cwd": str(out)})
    receipt = {"passed": False, "started_at": datetime.now(timezone.utc).isoformat(),
               "harness_sha256": sha(Path(__file__)), "provider_sha256": expected_pin,
               "freeze_sha256": sha(freeze_path), "live_service_execution_verified": False,
               "authenticated_publication_verified": False}
    clock = time.monotonic()
    try:
        with (out / "build.log").open("x") as log:
            result = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT)
        receipt["build_exit_code"] = result.returncode
        assert result.returncode == 0
        wheels = list((out / "wheel").glob("*.whl"))
        assert len(wheels) == 1
        wheel, installed = wheels[0], out / "extracted_wheel"
        required = sorted(str(p.relative_to(CANDIDATE)) for p in
            (CANDIDATE / "gene_annotation_episode").glob("bvbrc_comparative_systems*") if p.is_file())
        assert required and any(name.endswith("handoff_schemas.json") for name in required)
        with zipfile.ZipFile(wheel) as archive:
            for name in required:
                assert archive.read(name) == (CANDIDATE / name).read_bytes(), name
            archive.extractall(installed)
        invocation = [sys.executable, "-I", str(HERE / "PACKAGE_PROBE_001.py"), str(installed),
                      str(specimen), str(expected), expected_pin]
        save(out / "installed_command.json", {"argv": invocation, "cwd": str(out)})
        checked = subprocess.run(invocation, cwd=out, capture_output=True, text=True)
        with (out / "installed_stdout.log").open("x") as stream:
            stream.write(checked.stdout)
        with (out / "installed_stderr.log").open("x") as stream:
            stream.write(checked.stderr)
        receipt.update(wheel_sha256=sha(wheel), required_packaged_files=required,
                       installed_exit_code=checked.returncode, specimen_sha256=sha(specimen),
                       expected_result_sha256=sha(expected), probe_sha256=sha(HERE / "PACKAGE_PROBE_001.py"))
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
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
