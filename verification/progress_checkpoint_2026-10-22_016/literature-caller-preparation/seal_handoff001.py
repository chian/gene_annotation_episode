"""Read/copy actual preparation metadata only; no application or DB opens."""
from pathlib import Path
import hashlib,json,os
from jsonschema import Draft202012Validator,FormatChecker
OUT=Path(__file__).resolve().parent
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
OP=Path('/tmp/configured-literature-localization-preparation-20261022-001')
PLAN=Path('/tmp/configured-literature-caller-plan-20261022-001-vujlt8m4')
ROOT=Path('/home/chia/repos/gene_annotation_episode')
def d(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def save(p,x):
 b=x if isinstance(x,bytes) else (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.chmod(0o400)
copy_map=[]
(OUT/'outputs').mkdir(mode=0o700);(OUT/'operator-evidence').mkdir(mode=0o700);(OUT/'approved-inputs').mkdir(mode=0o700)
source_files={
 'outputs/PREPARATION_RESULT001.json':RUN/'caller-inputs/PREPARATION_RESULT001.json',
 'outputs/C_RESULT001.json':RUN/'caller-inputs/C_RESULT001.json',
 'outputs/C_VERIFICATION001.json':RUN/'caller-inputs/C_VERIFICATION001.json',
 'outputs/PREPARE_RESULT001.json':RUN/'caller-inputs/PREPARE_RESULT001.json',
 'outputs/parameters.json':RUN/'caller-inputs/parameters.json',
 'outputs/config.toml':RUN/'caller-inputs/config.toml',
 'outputs/focus.txt':RUN/'caller-inputs/focus.txt',
 'outputs/case-launch.json':RUN/'case-launch.json',
 'outputs/scientific-checkpoint-fork.json':RUN/'workspace/scientific-checkpoint-fork.json',
 'outputs/OPERATOR_INPUTS001.json':RUN/'caller-inputs/OPERATOR_INPUTS001.json',
 'approved-inputs/prepare_caller001.py':PLAN/'prepare_caller001.py',
 'approved-inputs/INPUTS001.json':PLAN/'INPUTS001.json',
 'approved-inputs/MANIFEST_FINAL001.json':PLAN/'MANIFEST_FINAL001.json',
 'approved-inputs/C_REQUEST001.json':PLAN/'C_REQUEST001.json',
 'approved-inputs/SCHEMAS004.json':PLAN/'SCHEMAS004.json',
 'approved-inputs/OPERATOR_OUTPUT_SCHEMA001.json':PLAN/'OPERATOR_OUTPUT_SCHEMA001.json',
 'approved-inputs/ADOPTED_SCOPE001.md':ROOT/'docs/CONFIGURED_LITERATURE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md',
}
for source in sorted(OP.iterdir()):
 if source.is_file():source_files['operator-evidence/'+source.name]=source
for relative,source in source_files.items():
 target=OUT/relative;before=d(source);save(target,source.read_bytes());after=d(source)
 assert before==after and all(d(target)[k]==before[k] for k in ('sha256','bytes'))
 copy_map.append({'source':before,'source_mode':oct(source.stat().st_mode&0o7777),'new_copy':d(target),'new_copy_mode':'0o400','content_and_embedded_paths_unchanged':True})
result=load(OUT/'outputs/PREPARATION_RESULT001.json');inv=load(OUT/'INVOCATION_RESULT001.json')
assert inv['exit_code']==0 and inv['attempt_number']==1
schema=load(OUT/'approved-inputs/OPERATOR_OUTPUT_SCHEMA001.json')
Draft202012Validator({'$ref':'#/$defs/result','$defs':schema['$defs']},format_checker=FormatChecker()).validate(result)
cresult=load(OUT/'outputs/C_RESULT001.json');receipt=load(OUT/'outputs/scientific-checkpoint-fork.json');request=load(OUT/'approved-inputs/C_REQUEST001.json');params=load(OUT/'outputs/parameters.json')
c_schema=load(OUT/'approved-inputs/SCHEMAS004.json')
for value,kind in [(cresult,'result'),(receipt,'receipt')]:Draft202012Validator({'$ref':'#/$defs/'+kind,'$defs':c_schema['$defs']},format_checker=FormatChecker()).validate(value)
assert cresult['initial_known_record_refs']==receipt['initial_known_record_refs']==params['policy']['scientific_progress']['initial_known_record_refs']
assert len(request['initial_known_record_refs'])==198 and len(cresult['initial_known_record_refs'])==200
assert set(cresult['initial_known_record_refs'])==set(request['initial_known_record_refs'])|set(cresult['lineage_source_refs'].values())
guards=[OUT/'operator-evidence'/n for n in ['SOURCE_BEFORE001.json','SOURCE_AFTER_C001.json','SOURCE_AFTER_PREPARE001.json']]
assert len({d(p)['sha256'] for p in guards})==1
assert not (RUN/'run.json').exists() and not (RUN/'policy-binding.json').exists() and not (RUN/'episode-execution-binding.json').exists()
handoff={'version':'actual_configured_literature_preparation_handoff_v1','status':'prepared_not_started',
 'execution':inv,'closed_result':result,'closed_result_descriptor':d(OUT/'outputs/PREPARATION_RESULT001.json'),
 'original_closed_result_path':str(RUN/'caller-inputs/PREPARATION_RESULT001.json'),
 'C_result':cresult,'original_C_result_path':str(RUN/'caller-inputs/C_RESULT001.json'),
 'source_guard_files':[d(p) for p in guards],'source_guard_byte_identity':True,
 'source_guard_file_count':len(load(guards[0])['files']),'original_implementation_file_count':load(guards[0])['implementation']['file_count'],
 'source_artifacts_and_authority_values_checked_by_actual_operator':True,
 'schema_checks':'actual closed preparation/C result and receipt valid; refs/list/union equality valid',
 'runtime_binding_files_absent_at_handoff':True,'additional_application_calls_during_handoff':0,'additional_DB_opens_during_handoff':0,
 'limitations':['No scientific run/episode/model/HTTP/native job launched by this invocation',
 'No initial scientific/native credit projection made during preparation',
 'Working database hash in result records post-prepare instant; custody-publication hash is earlier historical metadata',
 'Metadata copies retain original absolute paths; they are not relocated resumable application state',
 'Full inherited environment values not exported; exact overrides, inherited names and effective-environment digest retained',
 'Root independent review and any subsequent scientific launch remain separate']}
save(OUT/'COPY_PROVENANCE001.json',copy_map);save(OUT/'HANDOFF001.json',handoff)
readme='''Actual preparation succeeded once and stopped at prepared_not_started.

This directory preserves exact argv/cwd/start/end/exit, explicit adopted environment values plus inherited-variable names/effective-environment digest, empty stderr, stdout, closed result/receipt/caller metadata and all actual original-source guards. Credential environment values were not exported. Source guard snapshots are byte-identical:160 file witnesses plus122 original implementation files. No source Store/recovery was opened; only actual adopted C used readonly immutable original SQL. Native orders/handoffs/samples are0; old179 actions175 observations180 calls remain inherited. No new run/model/HTTP/native job was started.

Copies retain original content and embedded paths, with new names/modes and explicit COPY_PROVENANCE mapping. No content-address reference was rewritten. Database files are not copied into this handoff; the actual independent immutable checkpoint stays at the newly prepared workspace. This metadata bundle does not claim relocated resumability or scientific completion. The current working hash in the result is historical at the post-preparation instant once root launches later work. The earlier custody-publication working hash is separately historical.
'''
save(OUT/'README001.md',readme.encode())
manifest={'version':'actual_configured_literature_preparation_evidence_v1','members':{p.relative_to(OUT).as_posix():d(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST_FINAL001.json'}}
save(OUT/'MANIFEST_FINAL001.json',manifest)
print(json.dumps({'manifest':d(OUT/'MANIFEST_FINAL001.json'),'member_count':len(manifest['members']),'handoff':d(OUT/'HANDOFF001.json'),'closed_result':d(OUT/'outputs/PREPARATION_RESULT001.json'),'source_guard_sha256':d(guards[0])['sha256']},sort_keys=True))
