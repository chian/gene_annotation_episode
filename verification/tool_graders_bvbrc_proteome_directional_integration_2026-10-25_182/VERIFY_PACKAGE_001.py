"""Build/extract the frozen D/F candidate and verify its real installed facade.

Run only after D/F final-source coordination. Failures and source changes remain
in immutable receipts; this harness never applies files or modifies authority.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE/"candidate"
OUT = HERE/"package_verification_001"
SPECIMEN = HERE/"evidence_d/package_input_001.json"
assert SPECIMEN.is_file(), "D's retained controlled input specimen is not ready"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name,value):
    with (OUT/name).open("x") as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write("\n")

def snapshot():
    files = [CANDIDATE/"pyproject.toml"]
    for directory in ("gene_annotation_episode","method_loop","tests","research","verification"):
        files += [p for p in (CANDIDATE/directory).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc",".pyo")]
    # This host-only test is not imported or packaged by the installed probe.
    excluded = {"tests/test_bvbrc_proteome_directional_episode_path.py"}
    return {str(p.relative_to(CANDIDATE)):sha(p) for p in sorted(files)
            if str(p.relative_to(CANDIDATE)) not in excluded}

before = snapshot()
freeze_path = HERE/"FREEZE_INDEPENDENT_001.json"
freeze = json.loads(freeze_path.read_text())
assert before == freeze["sources"], "candidate differs from agreed final-source freeze"
OUT.mkdir(exist_ok=False)
save("source_before.json",before)
command = [sys.executable,"-m","pip","wheel","--no-deps","--wheel-dir",str(OUT/"wheel"),str(CANDIDATE)]
save("command.json",{"argv":command,"cwd":str(OUT)})
started = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
receipt = {"started_at":started,"passed":False,"live_service_execution_verified":False,
           "authenticated_publication_verified":False,"freeze_file":freeze_path.name,
           "freeze_sha256":sha(freeze_path)}
try:
    with (OUT/"build.log").open("x") as log:
        build = subprocess.run(command,cwd=OUT,stdout=log,stderr=subprocess.STDOUT)
    receipt["build_exit_code"] = build.returncode
    assert build.returncode == 0, "wheel build failed"
    wheels = list((OUT/"wheel").glob("*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]
    installed = OUT/"extracted_wheel"
    required = ["gene_annotation_episode/"+name for name in (
        "bvbrc_proteome_bundle_adapter_v2.py","bvbrc_proteome_bundle_v2_contracts.py",
        "bvbrc_proteome_bundle_v2_schemas.json","bvbrc_proteome_bundle_v2_resolution.py",
        "bvbrc_proteome_numerical_sheet.py","bvbrc_proteome_directional_saved_validation.py",
        "bvbrc_proteome_directional_fact_contracts.py","bvbrc_proteome_directional_projection.py",
        "bvbrc_proteome_directional_numerical_schemas.json")]
    with zipfile.ZipFile(wheel) as archive:
        assert set(required) <= set(archive.namelist())
        for name in required:
            assert archive.read(name) == (CANDIDATE/name).read_bytes(), name
        archive.extractall(installed)
    invocation = [sys.executable,"-I",str(HERE/"PACKAGE_PROBE_001.py"),str(installed),str(SPECIMEN)]
    save("installed_command.json",{"argv":invocation,"cwd":str(OUT)})
    result = subprocess.run(invocation,cwd=OUT,capture_output=True,text=True)
    (OUT/"installed_stdout.log").write_text(result.stdout)
    (OUT/"installed_stderr.log").write_text(result.stderr)
    receipt.update(wheel=str(wheel.relative_to(HERE)),wheel_sha256=sha(wheel),
                   required_packaged_files=required,installed_exit_code=result.returncode,
                   specimen_sha256=sha(SPECIMEN),probe_sha256=sha(HERE/"PACKAGE_PROBE_001.py"))
    assert result.returncode == 0, "installed provider probe failed"
    checked = json.loads(result.stdout)
    assert checked["legacy_implementation_sha256"] == "4a38563301a75481c9fc8cfcde77e0a09b9d8e08f3c0562e9635c18692e44a20"
    save("installed_result.json",checked)
    receipt.update(passed=True,installed_result_sha256=sha(OUT/"installed_result.json"),
                   numerical_answers={k:checked[k] for k in ("coverage","symbol_identity","resolved_identity","pair_population","native_expectation")})
except Exception as error:
    receipt.update(passed=False,error_type=type(error).__name__,error=str(error))
finally:
    after = snapshot()
    save("source_after.json",after)
    changes = [name for name in sorted(set(before)|set(after)) if before.get(name) != after.get(name)]
    receipt.update(ended_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-clock,
                   source_count=len(before),changed_sources=changes)
    receipt["passed"] = receipt["passed"] and not changes
    save("receipt.json",receipt)
    print(json.dumps(receipt))
sys.exit(0 if receipt["passed"] else 1)
