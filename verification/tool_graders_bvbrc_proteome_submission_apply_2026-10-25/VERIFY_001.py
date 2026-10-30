"""Verify the applied request-binding change without live scientific execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TESTS = [
    "tests/test_bvbrc_appservice_request_content.py",
    "tests/test_bvbrc_proteome_submitted_parameters.py",
    "tests/test_bvbrc_appservice_contracts.py",
    "tests/test_bvbrc_proteome_bundle_contracts.py",
    "tests/test_bvbrc_proteome_bundle_resolution.py",
    "tests/test_bvbrc_proteome_bundle_projection.py",
    "tests/test_bvbrc_proteome_data_contracts.py",
    "tests/test_bvbrc_proteome_directional_contracts.py",
    "tests/test_bvbrc_proteome_native.py",
    "tests/test_bvbrc_proteome_sheet_contracts.py",
]


def hashes():
    paths = set(ROOT / name for name in TESTS)
    for folder in ("gene_annotation_episode", "method_loop"):
        paths.update(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in {".py", ".json"} and "__pycache__" not in p.parts)
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def save(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


before = hashes()
command = [sys.executable, "-m", "pytest", *TESTS, "-q", "--junitxml=" + str(HERE / "pytest_001.xml")]
save("TEST_COMMAND_001.json", dict(command=command, cwd=str(ROOT), source_before=before,
    started_at=datetime.now(timezone.utc).isoformat(), live_service=False))
started = time.monotonic()
with (HERE / "pytest_001.log").open("xb") as log:
    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
after = hashes()
changed = {path: dict(before=value, after=after.get(path)) for path, value in before.items() if after.get(path) != value}
receipt = dict(exit_code=result.returncode, elapsed_seconds=time.monotonic() - started,
    ended_at=datetime.now(timezone.utc).isoformat(), source_after=after,
    changed_sources=changed, added_sources={k:v for k,v in after.items() if k not in before})
save("TEST_RECEIPT_001.json", receipt)
print(json.dumps({key: receipt[key] for key in ("exit_code", "elapsed_seconds", "changed_sources")}))
raise SystemExit(result.returncode or int(bool(changed)))
