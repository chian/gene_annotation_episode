"""Build the final nonduplicated index only after the coherent test run ends."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
def read(path): return json.loads(path.read_text())
def identity(path):
    return {'path':str(path.relative_to(HERE)), 'bytes':path.stat().st_size,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

receipt = read(HERE/'PIN_RUN_RECEIPT_017.json')
assert receipt['exit_code']==0 and receipt['code_unchanged']
environment=read(HERE/'ENVIRONMENT_017.json')
versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
assert versions==environment['packages'] and sys.version==environment['python']
environment_identity={'versions_unchanged_after_tests':True,'python':sys.version,
    'interpreter_path':str(Path(sys.executable).resolve()),
    'interpreter_sha256':hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
    'scope':'Existing external virtual environment; versions recorded before and after, not vendored into source pin.'}
(HERE/'ENVIRONMENT_IDENTITY_018.json').write_text(json.dumps(environment_identity,indent=2))
audits = [read(p) for p in sorted((HERE/'import_audit_017').glob('*.json'))]
assert audits and not any(a['outside_pin'] for a in audits)
pin = HERE/'coherent_pin_017'
assert all(Path(r['path']).is_relative_to(pin) for a in audits for r in a['imports'])
cases=[]
for path in sorted((HERE/'tmp_pinned_017').glob('*/CONNECTED_PROOF.json')):
    if path.parent.is_symlink(): continue
    proof=read(path); readonly_path=path.with_name('READONLY_STDOUT.txt');ro=read(readonly_path)
    assert ro['query_only']==1 and ro['total_changes']==0
    assert ro['observation_count']==5 and ro['observation_identities_unchanged']
    assert not ro['source_image_decoder_model_population_receive_mutation_called']
    assert Path(ro['storage_import']).is_relative_to(pin)
    spec=proof['spec']; rows=proof['returned']['form']['requested_signal']
    assert ro['first_projection']==rows and len(rows)==1
    assert rows[0]['component']=='reported_ratio' and rows[0]['value']==.64
    assert len(proof['observation_identities'])==5
    cases.append({'directory':str(path.parent.relative_to(HERE)),
        'connected_proof':identity(path),'readonly_stdout':identity(readonly_path),
        'run_id':spec['run_id'],'parent_episode_id':spec['parent']['episode_id'],
        'child_episode_id':spec['child']['episode_id'],'commission_handle':spec['handle'],
        'requested_components':['reported_ratio'],'returned_value':.64,
        'observation_identities':proof['observation_identities'],
        'query_only':1,'total_changes':0,'saved_artifact_reads':ro['saved_artifact_read_count'],
        'original_source_image_model_population_receive_mutations_called':False})
assert len(cases)==2
for row in read(HERE/'FINAL_OWNED_MANIFEST_017.json'):
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    assert hashlib.sha256((pin/row['path']).read_bytes()).hexdigest()==row['sha256']
native=pin/'gene_annotation_episode/literature_ratio_source_storage.py'
assert hashlib.sha256(native.read_bytes()).hexdigest()=='09ab57e50451f1265d94f244e91c96a89d3ca17c9bb7fbe605bbb5d6ff02636a'
live_drift=[]
for package in ('gene_annotation_episode','method_loop'):
    for path in sorted((pin/package).rglob('*.py')):
        live=ROOT/path.relative_to(pin)
        current=hashlib.sha256(live.read_bytes()).hexdigest() if live.exists() else None
        frozen=hashlib.sha256(path.read_bytes()).hexdigest()
        if current!=frozen:
            live_drift.append({'path':str(path.relative_to(pin)),'pin':frozen,'live':current})
roles=[]
for audit in audits:
    names={r['module'] for r in audit['imports']}
    roles.append({'pid':audit['pid'],'argv':audit['argv'],
        'import_count':len(audit['imports']),'outside_pin':[],
        'includes_actual_fixture': 'literature_ratio_source_worker_fixture_077' in names,
        'includes_fixture_controller': 'test_runtime' in names,
        'includes_native_storage':'gene_annotation_episode.literature_ratio_source_storage' in names})
index={'evidence_class':'constructed engineering; no primary/model scientific accuracy claim',
    'final_tested_generation':'coherent_pin_017','pin_receipt':receipt,
    'source_review_generation':'source_review_017/SOURCE_REVIEW_MANIFEST_017.json',
    'historical_pin009':'185 passed and one missing dynamic test dependency; exact failure preserved',
    'historical_pin014':'119 passed; intentionally interrupted for same-source display correction; code unchanged',
    'final_log':identity(HERE/'pytest_pinned_017.log'),
    'owned_manifest':identity(HERE/'FINAL_OWNED_MANIFEST_017.json'),
    'exact_patch':identity(HERE/'FINAL_OWNED_PATCH_017.diff'),
    'nonduplicated_final_connected_cases':cases,'actual_import_processes':roles,
    'live_other_owner_drift_from_final_pin':live_drift,
    'environment_identity':environment_identity,
    'earlier_complete_selected_run':'pytest_connected_005.log:13 passed',
    'earlier_recovery':'pytest_recovery_008.log:1 passed,1 deselected',
    'preserved_failure_logs':['pytest_initial_001.log','pytest_jats_002.log','pytest_durable_006.log','pytest_pinned_009.log','pytest_pinned_014.log'],
    'report_builder_correction':'018 initially counted pytest current-directory symlink as an extra case;020 skips directory symlinks. Original builder preserved; tests/pin unchanged.',
    'artifact_corrections':['PATCH_CORRECTION_011.json','PIN_COMPLETENESS_CORRECTION_015.json','source_review_017/SOURCE_REVIEW_MANIFEST_017.json'],
    'provenance_typo_correction':'015 says328-line read; actual wc-l is348. Full untruncated cat and exact byte/hash identity were correct.',
    'limits':['scripted scientific choices and finite test controller','production C1 restoration tested separately under forbidden external transport',
        'saved-only conservative label display, including multi-paragraph/image-box limits',
        'new repository subset readonly only; legacy broader constructor behavior unchanged',
        'primary/configured-model/other scientific coverage and W05 remain unproved']}
(HERE/'FINAL_PROOF_INDEX_018.json').write_text(json.dumps(index,indent=2))
files=[identity(p) for p in sorted(HERE.rglob('*')) if p.is_file() and not p.is_symlink()
    and p.name not in {'FINAL_ARTIFACT_MANIFEST_018.json','FINAL_ARTIFACT_MANIFEST_SHA256_018.txt'}]
manifest=HERE/'FINAL_ARTIFACT_MANIFEST_018.json';manifest.write_text(json.dumps({'files':files},indent=2))
digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
(HERE/'FINAL_ARTIFACT_MANIFEST_SHA256_018.txt').write_text(digest+'\n')
print(json.dumps({'final_proof_index':'FINAL_PROOF_INDEX_018.json','cases':len(cases),
    'audited_processes':len(audits),'manifest_files':len(files),'manifest_sha256':digest}))
