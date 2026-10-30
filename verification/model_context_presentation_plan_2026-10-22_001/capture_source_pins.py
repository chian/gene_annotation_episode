"""Read file identities only; never imports application code or opens state DB."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
ROOT=Path('/home/chia/repos/gene_annotation_episode')
FOUR=Path('/tmp/gene-annotation-hmmer-api-20261022-004')
OLD=Path('/tmp/scientific-context-boundary-s3we0xqg')
OUT=Path('/tmp/scientific-context-proposal002-xmmw8Rca')
RUN=ROOT/'cases/gene_001/runs/configured_development_002'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def item(path): return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def tree(root,folders):
    h=hashlib.sha256(); entries={}
    paths=sorted(p for folder in folders for p in (root/folder).rglob('*.py'))
    for p in paths:
        rel=str(p.relative_to(root)); value=sha(p)
        h.update(rel.encode()+b'\0'); h.update(bytes.fromhex(value))
        entries[rel]={'bytes':p.stat().st_size,'sha256':value}
    return {'count':len(paths),'sha256':h.hexdigest(),'files':entries}
prior=json.loads((OLD/'SOURCE_PINS.json').read_text())
readset=list(prior['files'])+[
 'gene_annotation_episode/materials_packing.py','gene_annotation_episode/library_targets.py',
 'gene_annotation_episode/homology_jobs.py','gene_annotation_episode/homology_episodes.py','gene_annotation_episode/resource_episodes.py','gene_annotation_episode/provider_jobs.py',
 'gene_annotation_episode/investigation_policy.py','gene_annotation_episode/tool_configuration.py',
 'method_loop/durable.py','method_loop/identities.py',
 'tests/test_wait_estimation_inputs.py','tests/test_runtime_history.py',
 'tests/test_episode_receipts.py','tests/test_fixed_target_seed.py','tests/test_application_execution_binding.py','tests/test_runtime.py',
]
readset=sorted(set(readset))
main=tree(ROOT,('gene_annotation_episode','method_loop'))
four=tree(FOUR,('gene_annotation_episode','method_loop'))
old_manifest=json.loads((OLD/'MANIFEST.json').read_text())
old_ok=all(sha(OLD/name)==v['sha256'] and (OLD/name).stat().st_size==v['bytes'] for name,v in old_manifest['members'].items())
result={
 'captured_at':datetime.now(timezone.utc).isoformat(),
 'status':'readonly_source_identity_not_implementation_or_test_execution',
 'immutable_goal':item(Path('/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt')),
 'original_expected_implementation_sha256':'a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a',
 'original_main_implementation':main,
 'original_main_pin_matches':main['sha256']=='a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a',
 'observed_current004_implementation_not_an_adopted005':four,
 'observed_current004_test_identities':tree(FOUR,('tests',)),
 'complete_relevant_readset':{name:item(ROOT/name) for name in readset},
 'additional004_readset':{name:item(FOUR/name) for name in ('gene_annotation_episode/runtime.py','gene_annotation_episode/tools.py','tests/test_api_execution_planning_runtime.py','tests/test_api_execution_planning_reconstruction.py','gene_annotation_episode/assembled_service_setup.py','gene_annotation_episode/resource_service_setup.py','gene_annotation_episode/public_search_operations.py','gene_annotation_episode/hmmer_resource_adapter.py','gene_annotation_episode/provider_jobs.py')},
 'actual_original_policy_snapshot':item(RUN/'policy-787117fa5d397694ea1377413f6932401b5cfec9acd92af934517ea044e71dfc.py'),
 'original_caller_file_identities':{name:item(RUN/name) for name in ('policy-binding.json','case-launch.json','episode-execution-binding.json')},
 'retained001_manifest':item(OLD/'MANIFEST.json'),
 'retained001_all_members_unchanged':old_ok,
}
assert result['original_main_pin_matches'] and old_ok
(OUT/'SOURCE_PINS002.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
readhash=hashlib.sha256(json.dumps(result['complete_relevant_readset'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
(OUT/'READSET_SHA256.txt').write_text(readhash+'\n')
print(json.dumps({'original_source_count':main['count'],'original_source_sha256':main['sha256'],'current004_source_count':four['count'],'current004_sha256':four['sha256'],'current004_py_test_file_count':result['observed_current004_test_identities']['count'],'retained001_unchanged':old_ok,'relevant_main_readset_count':len(readset),'relevant_readset_sha256':readhash},indent=2))
