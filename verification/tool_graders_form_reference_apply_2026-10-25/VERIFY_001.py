"""Verify the applied report path through the actual controlled Workflow."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EVIDENCE = ROOT / "verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25"


def save(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def hashes():
    paths = [p for folder in ("gene_annotation_episode", "method_loop", "tests")
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and p.suffix in {".py", ".json"} and "__pycache__" not in p.parts]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)}


before = hashes()
old_runs = {str(p) for p in (EVIDENCE / "runs").iterdir()}
command = [sys.executable, "-m", "pytest", "-q",
    "tests/test_form_reference_validation.py",
    "tests/test_bvbrc_genome_alignment_episode_flow.py",
    "--junitxml=" + str(HERE / "pytest_001.xml")]
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
save("TEST_COMMAND_001.json", {"command": command, "cwd": str(ROOT),
    "started_at": datetime.now(timezone.utc).isoformat(), "source_before": before,
    "existing_runs": sorted(old_runs), "live_service": False,
    "configured_model": False, "new_native_scientific_execution": False})
started = time.monotonic()
with (HERE / "pytest_001.log").open("xb") as log:
    process = subprocess.Popen(command, cwd=ROOT, env=environment,
        stdout=log, stderr=subprocess.STDOUT)
    save("PROCESS_001.json", {"pid": process.pid, "command": command,
        "started_at": datetime.now(timezone.utc).isoformat()})
    code = process.wait()
after = hashes()
changed = {p: {"before": h, "after": after.get(p)} for p, h in before.items()
    if after.get(p) != h}
added = {p: h for p, h in after.items() if p not in before}
new_runs = sorted(str(p.relative_to(ROOT)) for p in (EVIDENCE / "runs").iterdir()
    if str(p) not in old_runs)
xml = HERE / "pytest_001.xml"
counts = [] if not xml.exists() else [dict(s.attrib) for s in ET.parse(xml).getroot().iter("testsuite")]
receipt = {"exit_code": code, "elapsed_seconds": time.monotonic() - started,
    "ended_at": datetime.now(timezone.utc).isoformat(), "source_after": after,
    "changed_sources": changed, "added_sources": added, "new_runs": new_runs,
    "testsuites": counts, "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
save("TEST_RECEIPT_001.json", receipt)
print(json.dumps({k: receipt[k] for k in ("exit_code", "elapsed_seconds", "changed_sources",
    "added_sources", "new_runs", "testsuites", "child_peak_rss_kib")}))
raise SystemExit(code or int(bool(changed)))
