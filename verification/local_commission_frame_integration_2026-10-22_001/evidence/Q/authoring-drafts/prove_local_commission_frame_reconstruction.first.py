"""Run only the independent factual-frame reconstruction checks at a frozen pin.

This operator script never adopts a model or starts scientific/service/native
work.  The selected tests use scripted local transports and preserve all raw
synthetic fixtures, including first failures, beneath a new evidence directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def implementation_pin(root):
    digest = hashlib.sha256()
    members = []
    for path in sorted(path for package in ("gene_annotation_episode", "method_loop")
                       for path in (root/package).rglob("*.py")):
        name = str(path.relative_to(root))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(name.encode()+b"\0")
        digest.update(bytes.fromhex(sha))
        members.append({"path": name, "sha256": sha})
    return digest.hexdigest(), members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-implementation-sha256", required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    pin, members = implementation_pin(root)
    if pin != args.expected_implementation_sha256:
        raise SystemExit(f"source pin mismatch: expected {args.expected_implementation_sha256}; actual {pin}")
    evidence = args.evidence_directory.expanduser().resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    fixture_root = evidence/"raw-fixtures"
    fixture_root.mkdir()
    command = [sys.executable, "-B", "-m", "pytest", "-q",
        "tests/test_local_commission_frame_reconstruction.py", "--basetemp", str(evidence/"pytest-temp")]
    record = {"version": "local_commission_frame_reconstruction_proof_v1",
        "implementation_sha256": pin, "source_members": members,
        "test_sha256": hashlib.sha256((root/"tests/test_local_commission_frame_reconstruction.py").read_bytes()).hexdigest(),
        "operator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "command": command, "working_directory": str(root),
        "scripted_providers": True, "actual_model_network_native_science": False,
        "fixture_numerical_control": "existing test_case_execution fixture callback: exact 1 until stop_after, then exact 0; cost=0",
        "production_comparison": "available estimate upper <= caller cost",
        "started_at": datetime.now(timezone.utc).isoformat()}
    (evidence/"invocation.json").write_text(json.dumps(record, indent=2)+"\n")
    environment = dict(os.environ)
    environment["GENE_EPISODE_FRAME_RECONSTRUCTION_EVIDENCE_ROOT"] = str(fixture_root)
    with (evidence/"pytest.log").open("xb") as output:
        result = subprocess.run(command, cwd=root, env=environment, stdout=output,
                                stderr=subprocess.STDOUT, check=False)
    final_pin, _ = implementation_pin(root)
    record.update(exit_code=result.returncode, source_unchanged=final_pin == pin,
                  final_implementation_sha256=final_pin,
                  finished_at=datetime.now(timezone.utc).isoformat())
    (evidence/"results.json").write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps({key: record[key] for key in (
        "implementation_sha256", "exit_code", "source_unchanged")}))
    raise SystemExit(result.returncode if final_pin == pin else 2)


if __name__ == "__main__":
    main()
