"""Bounded synthetic integration/preservation verification; no model or paper IO."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
OWNED=["gene_annotation_episode/literature_kinetic_storage.py","gene_annotation_episode/literature_kinetic_validation.py","gene_annotation_episode/literature_episodes.py","gene_annotation_episode/episode_services.py","gene_annotation_episode/literature_experimental_prompt.py","tests/test_literature_kinetic_storage.py","tests/test_literature_kinetic_integration.py","tests/test_literature_parent_population_information.py"]
TESTS=["tests/test_literature_kinetic_storage.py","tests/test_literature_kinetic_integration.py","tests/test_literature_parent_population_information.py","tests/test_literature_return_fact_selection.py","tests/test_literature_experimental_prompt.py","tests/test_literature_experimental_prompt_delivery.py","tests/test_literature_reference_parent_prompt.py","tests/test_literature_reference_parent_delivery.py"]
def hashes():return {s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in OWNED}
def write(name,value):
    with (OUT/name).open("x") as f:json.dump(value,f,indent=2);f.write("\n")
before=hashes();write("VERIFY_005_BEFORE_SHA256.json",before)
command=[str(ROOT/".venv/bin/python"),"-B","-m","pytest","-q",*TESTS,"--tb=short"]
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (OUT/"VERIFY_005_PYTEST.log").open("x") as f:
    result=subprocess.run(command,cwd=ROOT,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},stdout=f,stderr=subprocess.STDOUT)
after=hashes();write("VERIFY_005_AFTER_SHA256.json",after)
receipt={"started_at_utc":began,"elapsed_seconds":time.monotonic()-start,"exit_code":result.returncode,"command":command,"owned_files_stable":before==after,"sha256":after,"log":"VERIFY_005_PYTEST.log","scope":"controlled synthetic operations, actual shared runtime/C4/provider rendering and saved read-only reconstruction; no live models or scientific paper validation"}
write("VERIFY_005_RECEIPT.json",receipt)
print(json.dumps(receipt,indent=2));raise SystemExit(result.returncode or (0 if before==after else 1))
