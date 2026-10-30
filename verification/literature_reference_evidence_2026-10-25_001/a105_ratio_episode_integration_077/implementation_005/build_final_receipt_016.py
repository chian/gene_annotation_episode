"""Build the final nonduplicated index only after the coherent test run ends."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
def read(path): return json.loads(path.read_text())
def identity(path):
    return {'path':str(path.relative_to(HERE)), 'bytes':path.stat().st_size,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

receipt = read(HERE/'PIN_RUN_RECEIPT_014.json')
assert receipt['exit_code']==0 and receipt['code_unchanged']
audits = [read(p) for p in sorted((HERE/'import_audit_014').glob('*.json'))]
assert audits and not any(a['outside_pin'] for a in audits)
pin = HERE/'coherent_pin_014'
assert all(Path(r['path']).is_relative_to(pin) for a in audits for r in a['imports'])
cases=[]
for path in sorted((HERE/'tmp_pinned_014').glob('*/CONNECTED_PROOF.json')):
    proof=read(path); readonly_path=path.with_name('READONLY_STDOUT.txt');ro=read(readonly_path)
    assert ro['query_only']==1 and ro['total_changes']==0
    assert ro['observation_count']==5 and ro['observation_identities_unchanged']
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
for row in read(HERE/'FINAL_OWNED_MANIFEST_010.json'):
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    assert hashlib.sha256((pin/row['path']).read_bytes()).hexdigest()==row['sha256']
native=pin/'gene_annotation_episode/literature_ratio_source_storage.py'
assert hashlib.sha256(native.read_bytes()).hexdigest()=='09ab57e50451f1265d94f244e91c96a89d3ca17c9bb7fbe605bbb5d6ff02636a'
roles=[]
for audit in audits:
    names={r['module'] for r in audit['imports']}
    roles.append({'pid':audit['pid'],'argv':audit['argv'],
        'import_count':len(audit['imports']),'outside_pin':[],
        'includes_actual_fixture': 'literature_ratio_source_worker_fixture_077' in names,
        'includes_fixture_controller': 'test_runtime' in names,
        'includes_native_storage':'gene_annotation_episode.literature_ratio_source_storage' in names})
index={'evidence_class':'constructed engineering; no primary/model scientific accuracy claim',
    'accepted_generation':'coherent_pin_014','pin_receipt':receipt,
    'final_log':identity(HERE/'pytest_pinned_014.log'),
    'owned_manifest':identity(HERE/'FINAL_OWNED_MANIFEST_010.json'),
    'exact_patch':identity(HERE/'FINAL_OWNED_PATCH_011.diff'),
    'nonduplicated_final_connected_cases':cases,'actual_import_processes':roles,
    'earlier_complete_selected_run':'pytest_connected_005.log:13 passed',
    'earlier_recovery':'pytest_recovery_008.log:1 passed,1 deselected',
    'preserved_failure_logs':['pytest_initial_001.log','pytest_jats_002.log','pytest_durable_006.log','pytest_pinned_009.log'],
    'artifact_corrections':['PATCH_CORRECTION_011.json','PIN_COMPLETENESS_CORRECTION_015.json'],
    'provenance_typo_correction':'015 says328-line read; actual wc-l is348. Full untruncated cat and exact byte/hash identity were correct.',
    'limits':['scripted scientific choices and finite test controller','production C1 restoration tested separately under forbidden external transport',
        'saved-only conservative label display, including multi-paragraph/image-box limits',
        'new repository subset readonly only; legacy broader constructor behavior unchanged',
        'primary/configured-model/other scientific coverage and W05 remain unproved']}
(HERE/'FINAL_PROOF_INDEX_016.json').write_text(json.dumps(index,indent=2))
files=[identity(p) for p in sorted(HERE.rglob('*')) if p.is_file() and not p.is_symlink()
    and p.name not in {'FINAL_ARTIFACT_MANIFEST_016.json','FINAL_ARTIFACT_MANIFEST_SHA256_016.txt'}]
manifest=HERE/'FINAL_ARTIFACT_MANIFEST_016.json';manifest.write_text(json.dumps({'files':files},indent=2))
digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
(HERE/'FINAL_ARTIFACT_MANIFEST_SHA256_016.txt').write_text(digest+'\n')
print(json.dumps({'final_proof_index':'FINAL_PROOF_INDEX_016.json','cases':len(cases),
    'audited_processes':len(audits),'manifest_files':len(files),'manifest_sha256':digest}))
