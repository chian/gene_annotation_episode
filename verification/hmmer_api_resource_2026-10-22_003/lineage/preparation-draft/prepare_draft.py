"""Packaging-only draft preparation: reads frozen files, copies bytes, runs no tests."""
from pathlib import Path
import hashlib,json,re,shutil,stat

OUT=Path('/tmp/api-timing-publication-preparation-20261022-001')
REPO=Path('/home/chia/repos/gene_annotation_episode')
WORK=Path('/tmp/gene-annotation-hmmer-api-20261022-003')
PARENT=REPO/'verification/hmmer_api_resource_2026-10-22_002'
ROOT_FINAL=Path('/tmp/api-timing-root-final-20261022-001')
CAPSULE=OUT/'capsule.DRAFT'
PERMANENT=REPO/'verification/hmmer_api_resource_2026-10-22_003'
REPORT=REPO/'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_003.md'
CAPSULE.mkdir()

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def ident(path):
 if path.is_symlink() or not path.is_file():raise ValueError('regular file required: '+str(path))
 info=path.stat()
 return {'bytes':info.st_size,'mode':format(stat.S_IMODE(info.st_mode),'04o'),'sha256':sha(path)}
root_input=json.loads((ROOT_FINAL/'INPUTS.json').read_text())
assert root_input['runtime_implementation_sha256']=='cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623'
assert (len(root_input['source_files']),len(root_input['tests']))==(131,205)
assert sha(ROOT_FINAL/'INPUTS.json')=='b0e07e293e22a18e52a6a7c695a3ea7c6ed3a4a48a17e7a931085e0b8009aa6e'
parent_source=json.loads((PARENT/'SOURCE_IDENTITIES.json').read_text())
parent_manifest=json.loads((PARENT/'MANIFEST.json').read_text())
parent_copies=json.loads((PARENT/'COPIED_INPUT_IDENTITIES.json').read_text())
baseline=WORK/'GENERATION_BASELINE_001.json'
assert sha(baseline)==root_input['baseline_sha256']
entries=[];copied={}

def add(source,destination,category,*,expected=None,stage=True):
 source=Path(source); actual=ident(source)
 if expected is not None and actual['sha256']!=expected:raise ValueError('identity mismatch: '+str(source))
 item={'source_path':str(source),'source':actual,'candidate_relative_path':destination,
       'candidate_path':str(PERMANENT/destination),'category':category,
       'stage_state':'copied_for_review' if stage else 'exact_copy_planned',
       'planned_published_mode':'0555' if actual['mode'] in {'0555','0755'} else '0444'}
 entries.append(item)
 if stage:
  target=CAPSULE/destination;target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(source,target)
  staged=ident(target)
  assert staged['sha256']==actual['sha256'] and staged['bytes']==actual['bytes']
  copied[destination]={'source_path':str(source),'source':actual,'staged':staged,
       'planned_published_mode':item['planned_published_mode'],'redaction_count':0,
       'redaction_scan':'not_a_publication_scan; root final review pending'}

for name,digest in root_input['source_files'].items():add(WORK/name,name,'runtime_python',expected=digest)
for name,digest in root_input['tests'].items():add(WORK/name,name,'test_python',expected=digest)
static_prefixes=('cases/','research/','gene_annotation_episode/','method_loop/','resources/','tests/fixtures/')
assets={name:record for name,record in parent_copies['files'].items()
 if name not in parent_source['files'] and name not in parent_source['tests']
 and (name.startswith(static_prefixes) or name=='pyproject.toml')}
assert len(assets)==319
for name,record in sorted(assets.items()):add(PARENT/name,name,'unchanged_reproduction_asset_from_readonly_002',expected=record['published']['sha256'])
# The old capsule is not changed. Its complete member list has a separate
# exact lineage copy plan, including all earlier failures and overlap records.
parent_members={member['path']:member for member in parent_manifest['members']}
for name,record in sorted(parent_members.items()):
 add(PARENT/name,'parent-generation002/'+name,'complete_parent002_lineage',expected=record['sha256'],stage=False)
add(PARENT/'MANIFEST.json','parent-generation002/MANIFEST.json','complete_parent002_lineage',stage=False)
for name in ('MANIFEST.json','SOURCE_IDENTITIES.json','COPIED_INPUT_IDENTITIES.json','STATIC_COMPLETENESS_ADDITIONS.json','SOURCE_CUSTODY.json','VERIFICATION_COUNTS.json','LOG_REDACTIONS.json','README.md'):
 # Review metadata only; authoritative lineage target remains the same bytes.
 path=OUT/'parent002-review'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PARENT/name,path)
add(ROOT_FINAL/'INPUTS.json','evidence/root-final/INPUTS.json','frozen_root_inputs')
add(baseline,'lineage/GENERATION_BASELINE_001.json','immutable_generation002_baseline',expected=root_input['baseline_sha256'])
for index in range(16,26):
 name=f'docs/HMMER_API_RESOURCE_SCOPE_2026-10-22_{index:03}.md';add(REPO/name,name,'adopted_scope_record')
checklist=REPO/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_011.md'
assert sha(checklist)=='76eb448324a797c01174b28b13b7c7becfaac07fd1c7ee1c5586c3e573d82d86'
add(checklist,'references/SLOT_CORRECTION_2026-10-22_011.md','unchanged_fixed41_reference')
checks=[]
for number,line in enumerate(checklist.read_text().splitlines(),1):
 match=re.match(r'^- \[([ x])\] \*\*([^*]+)\*\*',line)
 if match:
  label=match.group(2).rstrip(':')
  checks.append({'label':label,'reference':str(checklist)+':'+str(number)})
assert len(checks)==41
# Completed evidence only. Explicitly scoped fixture backups are copied as
# bytes; no SQLite database is opened and no private/live workspace is read.
evidence_groups={
 'a-custody':WORK/'verification/api_timing_custody_20261022_001',
 'b-statistics':Path('/tmp/gene-annotation-hmmer-api-statistics-evidence-20261022-003'),
 'b-case-estimator':Path('/tmp/gene-annotation-hmmer-api-case-estimator-evidence-20261022-003'),
 'b-read-only-review':Path('/tmp/gene-annotation-hmmer-api-received-information-review-20261022-003'),
 'c-integration':WORK/'verification/api_timing_c003',
 'root-connected':Path('/tmp/api-timing-root-connected-20261022-001')}
for group,folder in evidence_groups.items():
 for source in sorted(folder.rglob('*')):
  if source.is_file():add(source,'evidence/'+group+'/'+source.relative_to(folder).as_posix(),'completed_task_evidence')
# Root retains final result ownership. No running root log is read or copied.
pending=[{'source_path':str(ROOT_FINAL/name),'candidate_relative_path':'evidence/root-final/'+name,
 'stage_state':'pending_root_completion_and_identity','category':'root_final_verification','source':None}
 for name in ('legacy-operations.log','connected-consumers.log')]
changed={name:{'generation002':parent_source['files'].get(name),'generation003':digest}
 for name,digest in root_input['source_files'].items() if parent_source['files'].get(name)!=digest}
assert len(changed)==15
assert [name for name in parent_source['files'] if name not in root_input['source_files']]==[]
assert len(root_input['added_tests'])==6 and root_input['changed_existing_tests']==['tests/test_run_statistics.py']
runtime=hashlib.sha256()
for name,digest in sorted(root_input['source_files'].items()):runtime.update(name.encode());runtime.update(b'\0');runtime.update(bytes.fromhex(digest))
assert runtime.hexdigest()==root_input['runtime_implementation_sha256']
source_identity={'version':'hmmer_api_resource_source_identities_v1','draft':True,
 'implementation_algorithm':parent_source['implementation_algorithm'],
 'implementation_sha256':runtime.hexdigest(),'files':root_input['source_files'],'tests':root_input['tests'],
 'runtime_source_count':131,'test_python_count':205,'static_assets_enter_runtime_pin':False,
 'parent_implementation_sha256':parent_source['implementation_sha256'],
 'parent_manifest_sha256':sha(PARENT/'MANIFEST.json'),'changed_or_new_runtime_sources_from_generation002':changed,
 'unchanged_runtime_sources_from_generation002':116,'new_tests':root_input['added_tests'],
 'changed_existing_tests':root_input['changed_existing_tests'],
 'unchanged_tests_from_generation002':198,'root_input_file_sha256':sha(ROOT_FINAL/'INPUTS.json')}
dump(OUT/'SOURCE_IDENTITIES.DRAFT.json',source_identity)
dump(OUT/'COPY_PLAN.DRAFT.json',{'version':'api003_copy_plan_draft_v1','draft':True,
 'candidate_capsule_path':str(PERMANENT),'candidate_report_path':str(REPORT),'entries':entries,
 'pending_entries':pending,'source_count':131,'test_count':205,'reproduction_asset_count':319,
 'parent002_member_count_plus_manifest':len(parent_members)+1,
 'parent_lineage_stage_policy':'Complete exact copy plan retained; original002 is untouched; only review metadata staged outside capsule.',
 'finalization_owner':'root only; no publication, readonly seal, final log claims or source edits performed'})
dump(OUT/'COPIED_INPUT_IDENTITIES.DRAFT.json',{'version':'api003_staged_copy_identities_v1','draft':True,'copied_file_count':len(copied),'files':copied})
dump(OUT/'CHECKLIST_REFERENCES.DRAFT.json',{'version':'fixed41_reference_links_v1','draft':True,
 'source':str(checklist),'source_sha256':sha(checklist),'reference_only':True,'entries':checks,
 'meaning':'All41 original IDs/order are linked. No checklist body, state or finite prior checkpoint is rewritten or newly checked.'})
counts={
 'version':'api003_counts_draft_v1','draft':True,'counts_are_per_invocation_and_overlap':True,
 'aggregate_final_unique_count':None,'root_final_status':'pending owner confirmation; running log bodies not read',
 'completed_invocations':[
  {'owner':'A','log':'evidence/a-custody/custody_final_003.log','passed':28,'seconds':144.16,'scope':'full then-existing custody module on final A source'},
  {'owner':'A','log':'evidence/a-custody/custody_identity_channels.log','passed':2,'seconds':15.91,'scope':'two added foreign algorithm/database failure-channel fixtures'},
  {'owner':'A','log':'evidence/a-custody/baseline_operations.log','passed':36,'seconds':64.78,'scope':'unopted provider operations; overlaps later root legacy verification'},
  {'owner':'B','log':'evidence/b-statistics/pytest-final.stdout.log','passed':77,'seconds':49.46,'scope':'statistical/native-contract group; earlier71 and selected32 overlap'},
  {'owner':'B','log':'evidence/b-case-estimator/pytest-001.log','passed':14,'seconds':135.88,'scope':'scope022 caller construction/default/resume'},
  {'owner':'C','log':'evidence/c-integration/final-owned-after-scope025.log','passed':7,'seconds':74.30,'scope':'six runtime cases plus actual detached fixed_case worker on final runtime pin; synthetic native receipt only'},
  {'owner':'C','log':'evidence/c-integration/first-regression.log','passed':56,'seconds':259.63,'scope':'earlier broader native-containing group; explicit subtask scope overrun, seven nodes/eight actual tiny local alignments; do not call no-native'},
  {'owner':'root','log':'evidence/root-connected/after-source-version-correction.log','passed':1,'seconds':13.26,'scope':'joined local fixture; retained before final scope024/025 pin, overlaps final connected group'}],
 'overlap_policy':'Do not add these rows or historical parent002 groups to any root final distinct-case total. Preserve each invocation and original source pin separately.',
 'failures_and_limits':'Original failure/debug logs remain byte-preserved; review evidence is inspection, not a test invocation.'}
dump(OUT/'VERIFICATION_COUNTS.DRAFT.json',counts)
provenance={'version':'api003_provenance_map_draft_v1','draft':True,
 'runtime_pin':runtime.hexdigest(),'root_inputs':{'path':str(ROOT_FINAL/'INPUTS.json'),'sha256':sha(ROOT_FINAL/'INPUTS.json')},
 'generation002_baseline':{'path':str(baseline),'sha256':sha(baseline)},
 'parent002':{'manifest':str(PARENT/'MANIFEST.json'),'sha256':sha(PARENT/'MANIFEST.json'),'runtime_pin':parent_source['implementation_sha256']},
 'task_evidence':{group:{'path':str(folder),'candidate_prefix':'evidence/'+group} for group,folder in evidence_groups.items()},
 'semantics_reference':str(REPO/'verification/hmmer_provider_elapsed_semantics_2026-10-22_001/MANIFEST.json'),
 'root_final_pending':pending,
 'excluded':'No private actual-service directory/database or active scientific workspace is accessed/copied. All old actual provider jobs remain unregistered, unexported and unrescored.',
 'scope_overrun':'C original first-regression invocation includes actual native sequence_worker/systemd alignment fixtures; recorded separately from its no-native final owned invocation.',
 'publication_candidates':{'capsule':str(PERMANENT),'report':str(REPORT)},
 'unperformed':'No test, HTTP/network, model, native execution, source/test edit, prior-record rewrite, publication or seal was performed during this packaging preparation.'}
dump(OUT/'PROVENANCE_MAP.DRAFT.json',provenance)
# A draft inventory is deliberately not named MANIFEST.json and carries no seal.
inv=[]
for path in sorted(CAPSULE.rglob('*')):
 if path.is_file():inv.append({'path':path.relative_to(CAPSULE).as_posix(),**ident(path)})
dump(OUT/'STAGING_INVENTORY.DRAFT.json',{'version':'api003_staging_inventory_draft_v1','draft':True,
 'implementation_sha256':runtime.hexdigest(),'members':inv,'candidate_not_published_or_sealed':True})
print(json.dumps({'out':str(OUT),'staged_files':len(inv),'copy_plan_entries':len(entries),'runtime':131,'tests':205,
 'assets':319,'parent_lineage_planned':len(parent_members)+1,'fixed41_references':len(checks),'runtime_pin':runtime.hexdigest()},sort_keys=True))
