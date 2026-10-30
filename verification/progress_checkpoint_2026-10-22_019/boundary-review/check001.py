from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,stat
ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-008')
OUT=Path('/tmp/direct-hmmer008-boundary-audit-R-20261022-iADg2M')
def digest(b):return hashlib.sha256(b).hexdigest()
def write(n,v):
 with (OUT/n).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def now():return datetime.now(timezone.utc).isoformat()
def descriptor(p):
 s=p.lstat()
 if not stat.S_ISREG(s.st_mode):raise RuntimeError('nonregular_current_input:'+str(p))
 b=p.read_bytes()
 return {'sha256':digest(b),'bytes':len(b),'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
started=now();scope=json.loads((OUT/'SCOPE001.json').read_text());basepath=ROOT/scope['baseline'];basebytes=basepath.read_bytes();baseline=json.loads(basebytes)
assert len(baseline['files'])==700
expected={r['relative_path']:r for r in baseline['files']};assert len(expected)==700
omitted=set(baseline['omitted_directories']);assert omitted=={'__pycache__','.pytest_cache'}
current={};excluded=[];nonregular=[]
for directory,dirs,files in os.walk(ROOT,followlinks=False):
 for name in list(dirs):
  p=Path(directory)/name
  if name in omitted:excluded.append(str(p.relative_to(ROOT)));dirs.remove(name)
  elif p.is_symlink():nonregular.append({'path':str(p.relative_to(ROOT)),'kind':'symlink_directory','target':os.readlink(p)});dirs.remove(name)
 for name in files:
  p=Path(directory)/name;relative=str(p.relative_to(ROOT));s=p.lstat()
  if not stat.S_ISREG(s.st_mode):nonregular.append({'path':relative,'kind':'symlink' if p.is_symlink() else 'special'});continue
  current[relative]=descriptor(p)
missing=sorted(set(expected)-set(current));added=sorted(set(current)-set(expected))
comparisons=[];changed=[]
for name,original in sorted(expected.items()):
 actual=current.get(name);equal=actual is not None and actual['sha256']==original['sha256'] and actual['bytes']==original['bytes']
 comparisons.append({'path':name,'expected_sha256':original['sha256'],'expected_bytes':original['bytes'],'current':actual,'equal_bytes':equal})
 if not equal:changed.append(name)
authorization={name:owner for owner,names in scope['expected_old_changes'].items() for name in names}
expected_added=set(scope['expected_new_runtime']+scope['expected_new_tests']+['GENERATION_BASELINE_008.json'])
assert not missing and not nonregular,(missing,nonregular)
assert set(changed)==set(authorization),changed
assert set(added)==expected_added,added
for r in comparisons:
 if r['path'] in authorization:r['authorized_owner']=authorization[r['path']]
def runtime(name):return name.endswith('.py') and name.split('/')[0] in {'gene_annotation_episode','method_loop'}
def test(name):return name.endswith('.py') and name.startswith('tests/')
categories={}
for label,pred in [('runtime',runtime),('tests',test),('other_static',lambda n:not runtime(n) and not test(n))]:
 old=[n for n in expected if pred(n)];new=[n for n in current if pred(n)]
 categories[label]={'baseline_count':len(old),'current_count':len(new),'changed_old_count':len([n for n in changed if pred(n)]),'unchanged_old_count':len([n for n in old if n not in changed]),'added_count':len([n for n in added if pred(n)])}
pin=hashlib.sha256()
for name in sorted(n for n in current if runtime(n)):
 pin.update(name.encode()+b'\0');pin.update(bytes.fromhex(current[name]['sha256']))
actualpin=pin.hexdigest();assert actualpin=='6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30'
# Re-read all included current inputs to expose concurrent edits rather than
# silently claiming an atomic snapshot of a mutable checkout.
changed_during=[n for n,r in current.items() if descriptor(ROOT/n)!=r]
assert not changed_during,changed_during
write('READSET001.json',{'version':'direct_hmmer008_ownership_readset_v1','baseline_path':str(basepath),'baseline_sha256':digest(basebytes),'scope_sha256':digest((OUT/'SCOPE001.json').read_bytes()),'operator_sha256':digest(Path(__file__).read_bytes()),'started_at':started,'finished_at':now(),'excluded_cache_directories':sorted(excluded),'baseline_comparisons':comparisons,'added_inputs':{n:current[n] for n in added},'all_current_inputs_second_read_metadata_and_hash_equal':True,'application_imports':0,'database_opens':0,'tests_workers_transport_control_calls':0})
write('RESULT001.json',{'version':'direct_hmmer008_ownership_result_v1','status':'ownership_boundaries_verified_static_only','baseline_file_count':len(expected),'current_included_file_count':len(current),'missing':missing,'nonregular':nonregular,'authorized_changed_old_files':[{'path':n,'owner':authorization[n],'sha256':current[n]['sha256']} for n in changed],'added_files':[{'path':n,'classification':'new_runtime_B' if n in scope['expected_new_runtime'] else 'new_test' if n in scope['expected_new_tests'] else 'generation_baseline_metadata','sha256':current[n]['sha256']} for n in added],'categories':categories,'actual_implementation_sha256':actualpin,'old_tests_unchanged':all(r['equal_bytes'] for r in comparisons if test(r['path'])),'old_method_loop_unchanged':all(r['equal_bytes'] for r in comparisons if r['path'].startswith('method_loop/')),'other_unauthorized_old_source_or_static_changes':[],'all_included_inputs_stable_during_checker':not changed_during,'limits':'Pure static comparison only. Held source is not claimed final-tested; root worker/A tests are independent. No scientific completion or active-state assertion.'})
print(json.dumps({'pin':actualpin,'categories':categories,'current_files':len(current),'old_changes':changed,'added':added},indent=2))
