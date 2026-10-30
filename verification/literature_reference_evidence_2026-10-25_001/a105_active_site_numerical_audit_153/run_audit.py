"""Run isolated synthetic checks and retain every invocation and code hash."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TEST = "tests/test_a105_active_site_numerical_audit_153.py"
FILES = [TEST, *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "gene_annotation_episode").glob("literature_active_site_*.py"))],
    "gene_annotation_episode/literature_assay_inputs.py", "gene_annotation_episode/literature_rate_native_inputs.py",
    "gene_annotation_episode/literature_rate_domains.py", "gene_annotation_episode/literature_experimental_contracts.py",
    "gene_annotation_episode/domain.py", "gene_annotation_episode/literature_rate_storage.py",
    "gene_annotation_episode/literature_product_partition_inputs.py"]


def hashes():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in FILES}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    run = HERE / ("check_" + stamp)
    run.mkdir()
    before = hashes()
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TEST]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    (run / "pytest.log").write_text(result.stdout + result.stderr)
    after = hashes()
    metadata = {"started_at_utc": stamp, "command": command, "exit_code": result.returncode,
        "fixture_kind": "synthetic_source_text_and_controlled_selections_no_actual_model",
        "code_hashes_before": before, "code_hashes_after": after, "files_changed_during_check":
            [path for path in before if before[path] != after[path]],
        "frozen_joined_proof": False,
        "limitations": ["No primary paper or paper packet read", "No configured model execution",
            "No method_loop/typed parent admission exercised", "Root must run against its joined frozen code"]}
    (run / "result.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"run": str(run), "exit_code": result.returncode,
        "files_changed_during_check": metadata["files_changed_during_check"]}))
    print(result.stdout + result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
