"""Verify the applied catalog/selection/schema and real descriptor context."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "applied_verification_001"
OUT.mkdir(exist_ok=False)
TESTS = ["tests/test_bvbrc_proteome_catalog_integration.py",
         "tests/test_bvbrc_proteome_document_selection.py",
         "tests/test_bvbrc_appservice_contracts.py",
         "tests/test_execution_episodes_family.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    paths = {ROOT / "pyproject.toml"}
    for directory in ("gene_annotation_episode", "method_loop", "tests"):
        paths.update(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and (p.suffix in (".py", ".json") or "fixtures" in p.parts))
    manifest = json.loads((HERE / "DELTA_MANIFEST_002.json").read_text())
    paths.update(ROOT/row["path"] for row in manifest["unchanged_fixture_files"])
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def save(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value,stream,indent=2)
        stream.write("\n")


before = snapshot()
save("source_before.json",before)
applied = json.loads((HERE / "APPLICATION_RECEIPT_001.json").read_text())
assert applied["production_applied"]
assert all(before[row["path"]] == row["candidate_sha256"] for row in applied["files"])
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT))
command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--basetemp="+str(OUT/"temporary"), "--junitxml="+str(OUT/"pytest.xml"),*TESTS]
save("command.json",{"argv":command,"cwd":str(ROOT),
                     "environment":{"PYTHONDONTWRITEBYTECODE":"1","PYTHONPATH":str(ROOT)}})
start = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
with (OUT/"pytest.log").open("x") as log:
    process = subprocess.run(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
after = snapshot()
save("source_after.json",after)
changes = [p for p in sorted(set(before)|set(after)) if before.get(p) != after.get(p)]
suite = list(ET.parse(OUT/"pytest.xml").getroot().iter("testsuite"))
receipt = {"started_at":start,"ended_at":datetime.now(timezone.utc).isoformat(),
           "elapsed_seconds":time.monotonic()-clock,"exit_code":process.returncode,
           "cwd":str(ROOT),"testsuites":[s.attrib for s in suite],
           "source_count":len(before),"changed_sources":changes,
           "verification":"applied catalog, original requirement selection, schema compatibility and descriptor context; controlled host evidence retained separately from frozen013",
           "live_service_execution_verified":False,"full_workflow_verified":False}
save("receipt.json",receipt)
print(json.dumps(receipt))
sys.exit(process.returncode or bool(changes))
