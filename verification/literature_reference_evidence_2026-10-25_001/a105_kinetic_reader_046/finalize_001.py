"""Record focused synthetic verification and actual dependency identities."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNED = ("gene_annotation_episode/literature_kinetic_inputs.py",
         "tests/test_literature_kinetic_inputs.py")
DEPENDENCIES = (
    "gene_annotation_episode/literature_kinetic_calculations.py",
    "gene_annotation_episode/literature_assay_inputs.py",
    "gene_annotation_episode/literature_rate_native_inputs.py",
    "gene_annotation_episode/literature_partner_source_fields.py",
    "gene_annotation_episode/literature_experimental_contracts.py",
)
EXPECTED_HELPERS = {
    "gene_annotation_episode/literature_assay_inputs.py": "52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e",
    "gene_annotation_episode/literature_rate_native_inputs.py": "55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500",
    "gene_annotation_episode/literature_partner_source_fields.py": "20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17",
}


def hashes(paths):
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}


def main():
    before = hashes((*OWNED, *DEPENDENCIES))
    assert all(before[name] == value for name, value in EXPECTED_HELPERS.items())
    command = [sys.executable, "-B", "-m", "pytest", "-q", OWNED[1], "--tb=short"]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True)
    with (HERE / "CHECKS_001.txt").open("x") as stream:
        stream.write(result.stdout)
        stream.write(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    after = hashes((*OWNED, *DEPENDENCIES))
    assert before == after, "Changed source while checking"
    patch = "".join("".join(difflib.unified_diff([], (ROOT / name).read_text().splitlines(True),
        fromfile="/dev/null", tofile="b/" + name)) for name in OWNED)
    with (HERE / "NEW_FILES_001.patch").open("x") as stream:
        stream.write(patch)
    receipt = {
        "status": "passed", "utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Finite pure native kinetic parameter reader and045 calculator input compatibility",
        "synthetic_only": True, "primary_paper_reads": False,
        "model_calls": 0, "runtime_or_Store_execution": False,
        "selected_operation_or_typed_return_installed": False,
        "exit_code": result.returncode, "command": command,
        "terminal_result": result.stdout.strip().splitlines()[-1],
        "owned_new_source_sha256": {name: after[name] for name in OWNED},
        "actual_dependency_sha256": {name: after[name] for name in DEPENDENCIES},
        "owned_and_dependency_hashes_unchanged_during_checks": True,
        "expected_frozen_helper_hashes_match_actual": True,
        "output_sha256": hashlib.sha256((HERE / "CHECKS_001.txt").read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256((HERE / "NEW_FILES_001.patch").read_bytes()).hexdigest(),
        "limits": [
            "No covariance/model source reader, raw curve fit, image extraction or parameter quotient implementation.",
            "No scientific TASK, catalog, repository, renderer, episode, runtime accounting or historical state change.",
            "Caller authorizes source scope; this reader verifies bytes and lexical/typed relationships, not scientific truth.",
            "Static dependency labels are expected fingerprints, not runtime code attestation.",
        ],
    }
    with (HERE / "FINAL_RECEIPT_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "terminal_result": receipt["terminal_result"],
        "source_sha256": receipt["owned_new_source_sha256"]}))


if __name__ == "__main__":
    main()
