"""Real hmmscan failure with a deliberately mismatched, explicitly hashed h3p."""
from pathlib import Path
import hashlib
import json
import sys

from run_native import DIRECTORY, NUCLEOTIDE, POLICY, ROOT, make_job, write
from gene_annotation_episode.local_jobs import run_local_job
from gene_annotation_episode.native_hmmer_contracts import native_hmmer_digest, requested_job_from_native
from gene_annotation_episode.native_hmmer_driver import run_native_hmmer


def main():
    work = DIRECTORY / "runs/hmmscan_wrong_pressed_companion"
    work.mkdir(parents=True, exist_ok=True)
    prepared = work / "selected-inputs"
    prepared.mkdir(exist_ok=True)
    job = make_job("hmmscan", "search", "ordinary")
    for row in job["operands"]:
        if row["role"].startswith("profile_database"):
            source = Path(row["path"])
            supplied = NUCLEOTIDE/"model.hmm.h3p" if row["role"] == "profile_database_h3p" else source
            target = prepared/source.name
            raw = supplied.read_bytes()
            if target.exists():
                assert target.read_bytes() == raw
            else:
                target.write_bytes(raw)
            row.update(path=str(target), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), artifact_ref=None)
    request = requested_job_from_native(job)
    plan = {"version": "native_hmmer_run_plan_v1", "identity": {"run_id": "producer-native-verification-2026-10-24",
        "episode_id": "no-episode-standalone-verification", "resource_id": "local", "execution_id": "hmmscan-wrong-index",
        "attempt_id": "original", "operation_key": "hmmscan-wrong-index", "requested_job_sha256": native_hmmer_digest(request)},
        "requested_job": request, "attempt_directory": str(work/"attempt"), "policy": POLICY.to_dict()}
    plan_path = work/"plan.json"
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == plan
        bundle = run_native_hmmer(plan)
    else:
        write(plan_path, plan)
        command = [sys.executable, "-m", "gene_annotation_episode.native_hmmer_driver", str(plan_path)]
        outcome = run_local_job(command, cwd=work, policy=POLICY, stdout_path=work/"producer.stdout",
            stderr_path=work/"producer.stderr", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
        write(work/"runner_receipt.json", {"fixture_kind": "deliberately_mismatched_native_pressed_companion",
            "command": command, "returncode": outcome.returncode, "metadata": outcome.metadata})
        bundle = json.loads((work/"attempt/bundle.json").read_text())
    assert bundle["returncode"] != 0
    assert any(f["code"] == "native_hmmer_nonzero_returncode" for f in bundle["failures"])
    assert any(a["role"] == "stdout" for a in bundle["artifacts"])
    assert any(a["role"] == "stderr" and a["size_bytes"] > 0 for a in bundle["artifacts"])
    assert run_native_hmmer(plan) == bundle
    example = {"native_returncode": bundle["returncode"], "failures": bundle["failures"],
        "artifacts": bundle["artifacts"], "sealed_failure_replay_equal": True,
        "meaning": "supplied digests/stems matched; this deliberately incompatible pressed companion caused native failure",
        "native_stderr": (work/"attempt/outputs/stderr").read_text()}
    write(work/"example.json", example)
    print(json.dumps(example, allow_nan=False))


if __name__ == "__main__":
    main()
