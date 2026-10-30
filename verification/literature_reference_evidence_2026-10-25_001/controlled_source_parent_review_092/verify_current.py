"""Parent check of final089/090 bytes, import custody and current source tests."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
OUT=Path(__file__).resolve().parent


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(name,data):
    with (OUT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')


stage=BASE/'controlled_source_stages_089'
population=BASE/'controlled_source_population_090'
manifest=read(stage/'PIN_MANIFEST_002.json')['files']
for name,sha in manifest.items():
    assert digest(ROOT/name)==sha
    assert digest(stage/'pin_002'/name)==sha
imports=read(stage/'PIN_IMPORTS_002.json')
for name,row in imports.items():
    path=Path(row['path']);assert path.is_relative_to(stage/'pin_002')
    assert digest(path)==row['sha256']
artifact_hashes=read(population/'ARTIFACT_HASHES.json')
for name,sha in artifact_hashes.items():assert digest(population/name)==sha
receipt=read(population/'final_002/EXECUTION_RECEIPT.json')
assert receipt['status']=='passed' and len(receipt['cases'])==8
for name,row in receipt['actual_imported_project_modules'].items():
    path=Path(row['path']);assert path.is_relative_to(population/'final_002/pin')
    assert digest(path)==row['sha256']
command=[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',
    'tests/test_literature_controlled_response_v3_stages.py',
    'tests/test_literature_controlled_response_v3_inputs.py',
    'tests/test_literature_controlled_response_local_calculations.py',
    'tests/test_literature_controlled_response_v3_population.py']
run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,
                   env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
with (OUT/'ROOT_TEST_RESULT.txt').open('x') as f:f.write(run.stdout);f.write(run.stderr)
for name,sha in manifest.items():assert digest(ROOT/name)==sha
save('ROOT_VERIFICATION.json',dict(source_fixture_files_verified=len(manifest),
    pinned_stage_imports_verified=len(imports),population_artifacts_verified=len(artifact_hashes),
    population_replay_cases=len(receipt['cases']),population_pinned_imports_verified=len(receipt['actual_imported_project_modules']),
    current_test_exit_code=run.returncode,test_command=command,
    scope='Constructed source stages, saved science, local and conditional population; no primary/model/native episode proof',
    full_fixed_goal_complete=False))
assert run.returncode==0
print(run.stdout)
print('Final089/090 byte and import evidence independently verified; native integration remains unfinished.')
