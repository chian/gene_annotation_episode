from pathlib import Path
import hashlib,json,difflib,os,tomllib
p=Path('/tmp/configured-resource-caller-preparation-20261022-001-U7WRRlHE')
base=Path('/tmp/configured-literature-caller-plan-20261022-001-vujlt8m4')
plan=Path('/tmp/configured-resource-investigation-plan-20261022-001-DAGmrtaT')
code=Path('/tmp/gene-annotation-configured-caller-20261022-007')
sha=lambda b:hashlib.sha256(b).hexdigest()
def w(q):
 b=q.read_bytes();return {'path':str(q),'bytes':len(b),'sha256':sha(b)}
def save(n,x):
 b=x if isinstance(x,bytes) else (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with (p/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return w(p/n)
old=(base/'prepare_caller001.py').read_text().splitlines(keepends=True)
new=(p/'prepare_caller001.py').read_text().splitlines(keepends=True)
diff=''.join(difflib.unified_diff(old,new,fromfile=str(base/'prepare_caller001.py'),tofile=str(p/'prepare_caller001.py')))
save('OPERATOR_VS_BASELINE_DIFF001.patch',diff.encode())
readset={'version':'configured_resource_preparation_packet_readset_v1',
 'prior_complete_source_consumer_readset':w(plan/'READSET001.json'),
 'prior_reading_scope':'The sealed accepted-plan readset records complete relevant caller, assignment, adapter, service/composition, planner, receipt/credit and reconstruction functions. Current finalization does not claim a new whole-runtime audit.',
 'current_complete_packet_reads':[w(p/n) for n in ['prepare_caller001.py','INPUTS001.json','ADOPTED_SCOPE001.md','ADOPTED_INPUT_DELTAS001.json','focus.txt','OPERATOR_OUTPUT_SCHEMA001.json','INTENDED_INVOCATION001.json','PROVENANCE001.json','verify_static_packet001.py','STATIC_CHECKS001.json','STATIC_COMMAND_START001.json','STATIC_COMMAND_RESULT001.json']],
 'current_source_reinspection':[{'file':w(code/'gene_annotation_episode/api_planning_case_policy.py'),'scope':'complete file'},
  {'file':w(code/'gene_annotation_episode/case_execution.py'),'scope':'lines1-278: PolicyBindings, fixed material/configuration/evidence paths and complete prepare_case_run'},
  {'file':w(code/'gene_annotation_episode/scientific_checkpoint_fork.py'),'scope':'public signature, error/read-only helpers and public preparation body reinspection; prior complete source reading is in accepted-plan readset'}],
 'runtime_hash_guard':w(p/'STATIC_RUNTIME_GUARD001.json'),
 'runtime_guard_scope':'All137 runtime Python files hashed only; not all137 files semantically reinspected.',
 'authority':w(Path('/home/chia/repos/gene_annotation_episode/docs/CONFIGURED_RESOURCE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md')),
 'no_actual_source_database_reads':True,'active_workspace_files_read':0,'private_provider_files_read':0,
 'application_imports':0,'database_connections':0,'C_P_calls':0,'operator_main_calls':0,
 'model_HTTP_native_calls':0,'production_source_changes':0,'permanent_writes':0}
save('READSET001.json',readset)
def leaves(value,prefix=''):
 if isinstance(value,dict):
  out={}
  for k,v in value.items():out.update(leaves(v,(prefix+'.' if prefix else '')+k))
  return out
 return {prefix:value}
def changes(a,b):
 aa,bb=leaves(a),leaves(b)
 return [{'path':k,'original_value':aa.get(k),'new_value':bb.get(k)} for k in sorted(set(aa)|set(bb)) if aa.get(k)!=bb.get(k)]
rq=lambda n:json.loads((p/n).read_bytes())
cc=changes(rq('BASELINE_C_REQUEST001.json'),rq('C_REQUEST001.json'))
pc=changes(rq('BASELINE_PARAMETER_TEMPLATE001.json'),rq('PARAMETER_TEMPLATE001.json'))
fc=changes(tomllib.loads((p/'BASELINE_CONFIG001.toml').read_text()),tomllib.loads((p/'config.toml').read_text()))
assert len(cc)==1 and cc[0]['path']=='destination_workspace'
assert len(pc)==3 and len(fc)==5
parent_verified=[]
for root in (base,plan):
 m=json.loads((root/'MANIFEST_FINAL001.json').read_bytes())
 members=m['members']
 if isinstance(members,list):
  rows=[(item.get('path',item.get('relative_path')),item) for item in members]
 else:rows=members.items()
 for n,d in rows:
  q=Path(n) if Path(n).is_absolute() else root/n
  actual=w(q)
  assert actual['sha256']==d['sha256'] and actual['bytes']==d['bytes']
 parent_verified.append({'manifest':w(root/'MANIFEST_FINAL001.json'),'members_verified':len(members)})
for n,d in rq('INPUTS001.json')['members'].items():
 actual=w(p/n);assert actual==d
save('FINAL_STATIC_REVIEW001.json',{'version':'configured_resource_preparation_final_static_review_v1','status':'passed_static_only',
 'C_request_deltas':cc,'parameter_template_deltas':pc,'configuration_deltas':fc,
 'input_manifest':w(p/'INPUTS001.json'),'operator':w(p/'prepare_caller001.py'),
 'parent_manifests_verified':parent_verified,'input_members_rechecked':14,
 'operator_main_calls':0,'C_P_calls':0,'SQLite_connections':0,'model_HTTP_native_calls':0,
 'no_failed_static_check':True,'preparation_executed':False,
 'note':'This stdlib finalization only reads static files and writes new packet metadata; it is separate from the retained once-only static checker command.'})
print(json.dumps({'new_files':['OPERATOR_VS_BASELINE_DIFF001.patch','READSET001.json','FINAL_STATIC_REVIEW001.json'],
 'parent_members':[x['members_verified'] for x in parent_verified], 'diff_lines':len(diff.splitlines()),'input_manifest':w(p/'INPUTS001.json'),'operator':w(p/'prepare_caller001.py')},sort_keys=True))
