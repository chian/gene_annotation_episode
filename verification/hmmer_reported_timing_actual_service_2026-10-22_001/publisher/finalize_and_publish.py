"""Supplemental read-only identity checks and exclusive token-free publication."""
from pathlib import Path
from urllib.parse import quote,quote_plus
from datetime import datetime,timezone
import hashlib,json,os,re,shutil,sqlite3
E=Path('/tmp/hmmer-reported-timing-service-verification-20261022-001')
W=Path('/tmp/hmmer-reported-timing-fixed-target-20261022-001')
O=Path('/tmp/hmmer-reported-timing-publication-20261022-001');S=O/'staged'
R=Path('/home/chia/repos/gene_annotation_episode')
D=R/'verification/hmmer_reported_timing_actual_service_2026-10-22_001'
DOC=R/'docs/HMMER_REPORTED_TIMING_ACTUAL_SERVICE_2026-10-22_001.md'
def load(p):return json.loads(p.read_bytes())
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v):return hashlib.sha256(v).hexdigest()
def digest(v):return sha(canon(v).encode())
def ensure(v,code):
    if not v:raise ValueError(code)
def put(name,value):
    p=S/name;ensure(not p.exists(),'new_stage_member_required');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(value if isinstance(value,bytes) else (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
ensure(not D.exists() and not DOC.exists(),'new_publication_paths_required')
checks=load(S/'CHECKS.json');store=load(S/'logical/store.json');ledger=load(S/'logical/timing-ledger.json');history=load(S/'logical/reported-history.json');b=load(E/'selected-binding.json')
records={v['id']:v for v in store['records']};submit=checks['original_submit_receipt']
ensure(sum(r.get('provider')=='episode.hmmer_reported_timing' for r in records.values())==1,'one_actual_timing_source_required')
claim=store['claims'][0]
ensure(claim['job_ref']==checks['job_ref'] and claim['registry_ref']==b['registry']['registry_ref'] and claim['operation_key']==submit['operation_key'] and claim['request_sha256']==b['order']['request_sha256'] and claim['retry_of'] is None,'original_submission_claim_mismatch')
def data(n):return json.loads(ledger['tables'][n][0]['data'])
owner=data('api_timing_bindings');order=data('api_timing_orders');intent=data('api_timing_submission_intents');bound=data('api_timing_submission_bindings')
ensure(ledger['tables']['api_timing_bindings'][0]['binding_ref']=='api_timing_binding_'+digest(owner),'owner_content_identity_mismatch')
for value,key,prefix in ((order,'binding_ref','api_timing_order_binding_'),(intent,'intent_ref','api_timing_submission_intent_'),(bound,'binding_ref','api_timing_submission_binding_')):
    ensure(value[key]==prefix+digest({k:v for k,v in value.items() if k!=key}),'timing_content_identity_mismatch')
for receipt in store['operations']:
    expected='provider_operation_'+digest({'registry_ref':b['registry']['registry_ref'],'operation_key':receipt['operation_key']})[:24]
    ensure(receipt['receipt_ref']==expected,'operation_receipt_content_identity_mismatch')
for row in history['tables']['expectation_snapshots']:
    value=json.loads(row['data']);ensure(row['id']=='execution_expectation_'+digest(value),'expectation_content_identity_mismatch')
for rec in records.values():
    if rec['record_type']=='source':
        payload={k:v for k,v in rec.items() if k not in {'id','record_type','origin'}}
        ensure(rec['id']=='source_'+digest({'origin':rec['origin'],'record':payload})[:24],'source_record_content_identity_mismatch')
# Validate every retained original seed reference in the NEW workspace only.
db=sqlite3.connect((W/'state.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=0);db.row_factory=sqlite3.Row
try:
    db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
    for entry in b['seed']['intake_records']:
        value=None
        for table in ('inputs','records','material_members'):
            row=db.execute('SELECT data FROM '+table+' WHERE id=?',(entry['reference'],)).fetchone()
            if row is not None:value=json.loads(row[0]);break
        if value is None:
            row=db.execute('SELECT * FROM artifacts WHERE id=?',(entry['reference'],)).fetchone()
            if row is not None:value={**dict(row),'record_type':'artifact'}
        ensure(value is not None and value['record_type']==entry['record_type'] and digest(value)==entry['content_sha256'],'seed_reference_content_mismatch')
    ensure(digest(json.loads(db.execute('SELECT data FROM problem').fetchone()[0]))==b['seed']['source']['problem_sha256'],'seed_problem_content_mismatch')
    db.rollback()
finally:db.close()
# Preserve the exact scripts used for file-based validation, their commands and
# the separately retained schema-only probe failure. No service phase is run.
for name in ('inspect_structure.py','validate_and_stage.py','finalize_and_publish.py'):
    put('publisher/'+name,(O/name).read_bytes())
for name in ('PLAN.md','STRUCTURE.json','inspection-probe-001-failure.json','validation-001.stdout.log','validation-001.stderr.log'):
    put('publisher/'+name,(O/name).read_bytes())
commands=[]
for p in sorted((E/'invocations').iterdir()):
    args=load(p/'intent.json')['arguments']
    argv=['/home/chia/repos/gene_annotation_episode/.venv/bin/python',str(E/'verify_hmmer_reported_timing.py'),'--expected-runtime-pin',args['expected_runtime_pin'],'--operation-key',args['operation_key'],args['phase']]
    for key in ('translation_operation_key','registry_ref','resource_id','page','receipt_ref'):
        if key in args:argv.extend(['--'+key.replace('_','-'),str(args[key])])
    commands.append({'invocation':p.name,'recorded_parsed_arguments':args,'canonical_argv':argv})
put('COMMANDS.json',{'service_commands_representation':'Canonical argv reconstructed from exact parsed intent records; NOT verbatim original shell token order/text. No separate original shell log was retained.','service_commands':commands,'publisher_commands':[{'command':'/home/chia/repos/gene_annotation_episode/.venv/bin/python /tmp/hmmer-reported-timing-publication-20261022-001/inspect_structure.py > /tmp/hmmer-reported-timing-publication-20261022-001/structure.stdout.json','exit_code':0},{'command':'/home/chia/repos/gene_annotation_episode/.venv/bin/python /tmp/hmmer-reported-timing-publication-20261022-001/validate_and_stage.py > /tmp/hmmer-reported-timing-publication-20261022-001/validation-001.stdout.log 2> /tmp/hmmer-reported-timing-publication-20261022-001/validation-001.stderr.log','exit_code':0},{'command':'/home/chia/repos/gene_annotation_episode/.venv/bin/python /tmp/hmmer-reported-timing-publication-20261022-001/finalize_and_publish.py > /tmp/hmmer-reported-timing-publication-20261022-001/publication-001.stdout.json 2> /tmp/hmmer-reported-timing-publication-20261022-001/publication-001.stderr.log','meaning':'This exact publication invocation; completion is recorded in its external stdout/exit result.'}],'publisher_probe_failures':[{'metadata':'publisher/inspection-probe-001-failure.json','meaning':'Read-only stdin schema inspection assumed a mapping for an actual list; no application/service call, no raw data repair.'}]})
report=(O/'REPORT_DRAFT.md').read_bytes();put('REPORT.md',report)
put('PUBLICATION_CHECKS.json',{'version':'actual_service_publication_checks_v1','validated_at':datetime.now(timezone.utc).isoformat(),'supplemental_checks':['one actual timing source by provider','original submission claim/key/request','owner/order/intent/submission content identities','operation receipt identities','all source record identities','immutable expectation content identities','all11 seed reference contents','original seed problem content'],'application_imports_or_calls':0,'service_phase_calls':0,'HTTP_calls':0,'model_calls':0,'native_calls':0,'scientific_or_episode_credit_assigned':False,'raw_originals_repaired':False})
# Re-derive original private session value(s) only in memory; do not print/save.
values=set()
for p in W.rglob('*'):
    if p.is_file() and '.sqlite3' not in p.name:
        for m in re.finditer(rb'(?i)sessionid\s*=\s*([^;\s,"\\]+)',p.read_bytes()):values.add(m.group(1).decode())
ensure(bool(values),'private_session_witness_missing')
forms={x.encode() for v in values for x in (v,quote(v,safe=''),quote_plus(v,safe=''),json.dumps(v)[1:-1])}
def clean(raw):return not any(v in raw for v in forms)
ensure(all(clean(p.read_bytes()) for p in S.rglob('*') if p.is_file()) and clean(report),'prepublication_session_scan_failed')
# Every original file remains identical; newly created SQLite reader sidecars
# are declared in WORKING_CUSTODY, never removed/checkpointed here.
before=load(O/'PRIVATE_BEFORE.json')
for root,files in before.items():
    for name,value in files.items():
        p=Path(root)/name;ensure(p.is_file() and p.stat().st_size==value['bytes'] and sha(p.read_bytes())==value['sha256'] and oct(p.stat().st_mode&0o777)==value['mode'],'private_original_changed_before_publication')
members={str(p.relative_to(S)):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(S.rglob('*')) if p.is_file()}
manifest={'version':'token_free_actual_reported_timing_publication_v1','source_pin':checks['source_pin'],'report_sha256':sha(report),'publication_kind':'partial token-free derivative; not complete DB or standalone replay','original_private_roots':[str(E),str(W)],'members':members,'manifest_excludes_itself':True,'member_count_excluding_manifest':len(members),'member_bytes_excluding_manifest':sum(v['bytes'] for v in members.values()),'original_copy_count':checks['copied_original_file_count'],'original_omission_count':checks['omitted_original_file_count'],'redacted_derivative_count':0,'privacy_scan':{'actual_private_session_values_compared':len(values),'forms_compared':len(forms),'matches':0,'raw_headers_published':False,'credential_values_disclosed':False}}
put('MANIFEST.json',manifest);ensure(clean((S/'MANIFEST.json').read_bytes()),'manifest_session_scan_failed')
# Both target paths are new. Creation never overwrites any prior publication.
shutil.copytree(S,D)
with DOC.open('xb') as f:f.write(report)
for p in D.rglob('*'):
    if p.is_dir():p.chmod(0o755)
    else:p.chmod(0o644)
D.chmod(0o755);DOC.chmod(0o644)
ensure(all((D/name).read_bytes()==(S/name).read_bytes() for name in members),'publication_copy_mismatch')
ensure((D/'MANIFEST.json').read_bytes()==(S/'MANIFEST.json').read_bytes() and DOC.read_bytes()==report,'published_report_or_manifest_mismatch')
ensure(all(clean(p.read_bytes()) for p in D.rglob('*') if p.is_file()) and clean(DOC.read_bytes()),'published_output_session_scan_failed')
print(json.dumps({'version':'actual_service_publication_result_v1','state':'published','documentation':str(DOC),'documentation_sha256':sha(DOC.read_bytes()),'evidence_directory':str(D),'manifest_sha256':sha((D/'MANIFEST.json').read_bytes()),'member_count_excluding_manifest':len(members),'member_bytes_excluding_manifest':manifest['member_bytes_excluding_manifest'],'report_is_exact_manifested_copy':True,'private_originals_unchanged':True,'privacy_scan_matches':0,'HTTP_model_native_application_calls':0},sort_keys=True,indent=2))
