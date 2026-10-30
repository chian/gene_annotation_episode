"""Static JSON/TOML/AST/hash derivation only; no application import."""
from pathlib import Path
import ast,copy,hashlib,json,tomllib,uuid,shutil
ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-008')
OUT=Path('/tmp/configured-direct-timing-caller-plan-R-20261022-hRKfbD')
OLD=Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
NEW=Path('/home/chia/gene_annotation_episode_runs/configured_direct_timing_investigation_001')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def write(n,v):
 with (OUT/n).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def literal(path,name):
 definitions={t.id:node.value for node in ast.parse(path.read_bytes()).body if isinstance(node,ast.Assign) for t in node.targets if isinstance(t,ast.Name)}
 class Expand(ast.NodeTransformer):
  def visit_Name(self,node):
   if node.id not in definitions:raise ValueError('unbound constant '+node.id)
   return self.visit(copy.deepcopy(definitions[node.id]))
 return ast.literal_eval(Expand().visit(copy.deepcopy(definitions[name])))
def leaves(v,p=''):
 if isinstance(v,dict):
  for k,x in v.items():yield from leaves(x,p+'/'+k)
 elif isinstance(v,list):
  if not v:yield p,[]
  for i,x in enumerate(v):yield from leaves(x,p+'/'+str(i))
 else:yield p,v
def delta(a,b,p=''):
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)):
   if k not in a:yield {'path':p+'/'+k,'kind':'added','proposed':b[k]}
   elif k not in b:yield {'path':p+'/'+k,'kind':'removed','original':a[k]}
   else:yield from delta(a[k],b[k],p+'/'+k)
 elif a!=b:yield {'path':p,'kind':'replaced','original':a,'proposed':b}
authority=OUT/'authority';authority.mkdir(exist_ok=True)
for name in ['parameters.json','config.toml','focus.txt','C_REQUEST001.json']:
 source=OLD/'caller-inputs'/name;target=authority/name
 if target.exists():assert target.read_bytes()==source.read_bytes()
 else:shutil.copy2(source,target)
original=json.loads((authority/'parameters.json').read_text());proposed=copy.deepcopy(original)
mode=literal(ROOT/'gene_annotation_episode/direct_hmmer_timing.py','DIRECT_MODE')
version=literal(ROOT/'gene_annotation_episode/api_planning_case_policy.py','DIRECT_VERSION')
registry='execution_registry_'+uuid.uuid4().hex
services=proposed['services'];services['version']=version;services['ordinary_hmmer_timing']=mode
services['api_timing']['history_path']=str(NEW/'statistics/run_statistics.sqlite')
services['api_timing']['ledger_path']=str(NEW/'statistics/api-timing.sqlite')
services['public_search_registry']['registry_ref']=registry
services['source_directory']=str(ROOT/'research/slotted_process_library/publications/2026-10-21-001')
proposed['policy']['operational']['registry_ref']=None
proposed['policy']['scientific_progress']['initial_known_record_refs']=None
config_text=(authority/'config.toml').read_text();assert config_text.count(str(OLD))==5
new_text=config_text.replace(str(OLD),str(NEW));(OUT/'CONFIG_PROPOSED001.toml').write_text(new_text)
config_before=tomllib.loads(config_text);config=tomllib.loads(new_text)
config_normalized=copy.deepcopy(config);config_normalized['local_jobs']['wall_seconds']=None
request_original=json.loads((authority/'C_REQUEST001.json').read_text());request=copy.deepcopy(request_original);request['destination_workspace']=str(NEW/'workspace')
write('C_REQUEST_PROPOSED001.json',request)
write('CONFIG_NORMALIZED_PROPOSED001.json',config_normalized)
write('PARAMETER_BLUEPRINT001.json',{'version':'configured_direct_timing_parameter_blueprint_v1','status':'not_runnable_until_exact_actual_C_and_prepare_outputs_fill_two_leaves','template':proposed,'deferred':[{'path':'/policy/scientific_progress/initial_known_record_refs','producer':'Verified actual new C successful result.initial_known_record_refs, exact original198 plus actual two lineage refs; never active-resource current200 list.'},{'path':'/policy/operational/registry_ref','producer':'Actual new prepare_case_run registry_configuration.registry_ref.'}]})
static_before=copy.deepcopy(original['policy']);static_after=copy.deepcopy(proposed['policy'])
for v in [static_before,static_after]:del v['operational']['registry_ref'];del v['scientific_progress']['initial_known_record_refs']
assert canonical(static_before)==canonical(static_after)
assert hashlib.sha256(canonical(static_after).encode()).hexdigest()=='dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1'
assert len(request['initial_known_record_refs'])==198 and len(set(request['initial_known_record_refs']))==198
source_pin=hashlib.sha256();source_files=[]
for f in sorted(p for package in ['gene_annotation_episode','method_loop'] for p in (ROOT/package).rglob('*.py')):
 relative=str(f.relative_to(ROOT));h=sha(f);source_pin.update(relative.encode()+b'\0');source_pin.update(bytes.fromhex(h));source_files.append({'path':relative,'sha256':h,'bytes':f.stat().st_size})
assert source_pin.hexdigest()=='6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30'
write('SOURCE_INPUTS008.json',{'version':'configured_direct_timing_source_inputs_v1','root':str(ROOT),'runtime_pin':source_pin.hexdigest(),'runtime_count':len(source_files),'files':source_files})
index=json.loads((Path(services['source_directory'])/'index.json').read_text());counts={s['slot']:s['count'] for s in index['slots']};assert counts=={'annotation_distinction':0,'thought_pattern':19}
write('INPUT_DELTAS001.json',{'version':'configured_direct_timing_exact_input_delta_v1','against_actual_resource_parameters_sha256':sha(authority/'parameters.json'),'C_request_delta':list(delta(request_original,request)),'config_parsed_delta':list(delta(config_before,config)),'parameter_delta_including_actual_output_only_placeholders':list(delta(original,proposed)),'unchanged_policy_remainder_sha256':hashlib.sha256(canonical(static_after).encode()).hexdigest(),'original198refs_canonical_sha256':hashlib.sha256(canonical(request['initial_known_record_refs']).encode()).hexdigest(),'fresh_public_registry_ref':registry,'registry_registered_by_this_plan':False,'library':{'source_directory':services['source_directory'],'index_sha256':sha(Path(services['source_directory'])/'index.json'),'slots':counts},'numeric_model_resource_library_semantics_changed':False,'fresh_history':{'path':services['api_timing']['history_path'],'created':False,'seed_samples':0},'fresh_ledger':{'path':services['api_timing']['ledger_path'],'created':False},'old_source_operands_preserved_except_destination':True})
write('STATIC_CHECKS001.json',{'version':'configured_direct_timing_plan_static_checks_v1','status':'passed_static_only','source_pin':source_pin.hexdigest(),'source_runtime_count':len(source_files),'parsed_config_relocations':len(list(delta(config_before,config))),'C_operand_delta_count':len(list(delta(request_original,request))),'caller_new_version_from_actual_AST':version,'direct_marker_from_actual_AST':mode,'numeric_policy_remainder_sha256':'dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1','original198refs_count':198,'library_slots':counts,'application_imports':0,'database_opens':0,'actual_preparations_or_launches':0,'models_HTTP_native_calls':0})
print('static_inputs_derived',registry)
