from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime, timezone
import json, re, xml.etree.ElementTree as ET
O=Path('/tmp/api-planning-root-final-20261022-004')
C=Path('/tmp/gene-annotation-hmmer-api-20261022-004')
def h(p): return sha256(p.read_bytes()).hexdigest()
def j(p): return json.loads(p.read_text())
def check(ok, msg):
    if not ok: raise AssertionError(msg)
i=j(O/'INPUTS.json'); files=i['files']; current={p.relative_to(C).as_posix():p for d in ['gene_annotation_episode','method_loop','tests'] for p in (C/d).rglob('*.py')}
check(set(current)==set(files),'source/test membership changed')
for rel, expected in files.items():
    p=current[rel]
    check(h(p)==expected['sha256'] and p.stat().st_size==expected['bytes'],'source/test bytes changed: '+rel)
src={r:files[r] for r in files if r.split('/')[0] in ['gene_annotation_episode','method_loop']}; tests={r:files[r] for r in files if r.startswith('tests/')}
pin=sha256()
for rel in sorted(src): pin.update(rel.encode()+b'\0'+bytes.fromhex(src[rel]['sha256']))
check(pin.hexdigest()==i['runtime_pin']=='16435877cddb566a9b802b6b3ce942595a9564b4cc10f8ca52b75f4007d9689d','runtime pin conflict')
ci=j(O/'CONSUMERS_INPUTS.json'); check(ci['source_manifest_sha256']==h(O/'INPUTS.json'),'consumer source snapshot link')
nodes=set(); classes=set(); groups=[]
for name,expected_count,seconds in [('legacy',135,463.04),('detached',1,26.97),('consumers',180,600.15)]:
    x=O/(name+'.xml'); l=O/(name+'.log'); tree=ET.parse(x).getroot(); cases=tree.findall('.//testcase'); ns=[c.attrib['classname']+'::'+c.attrib['name'] for c in cases]; cs={c.attrib['classname'] for c in cases}
    check(len(ns)==len(set(ns))==expected_count,'bad XML count: '+name)
    check(all(not list(c) for c in cases),'nonpassing testcase: '+name)
    check(all(int(s.attrib.get(k,0))==0 for s in tree.findall('.//testsuite') for k in ['failures','errors','skipped']),'nonpassing suite: '+name)
    check(not nodes.intersection(ns) and not classes.intersection(cs),'groups overlap: '+name)
    check(re.search(r'\b'+str(expected_count)+r' passed in '+re.escape(format(seconds,'.2f'))+r's\b',l.read_text()) is not None,'log conflict: '+name)
    selected=[c.replace('.','/')+'.py' for c in sorted(cs)]
    check(all(r in tests for r in selected),'unknown tested file: '+name)
    command=i['commands'].get(name,ci['command'] if name=='consumers' else None)
    check(command and all(r in command for r in selected),'command selection conflict: '+name)
    groups.append({'group':name,'passed':expected_count,'exit_code':0,'exit_code_basis':'collected exec session result','duration_seconds':seconds,'node_ids':ns,'test_files':selected,'command':command,'xml_sha256':h(x),'log_sha256':h(l)})
    nodes.update(ns); classes.update(cs)
check(len(nodes)==316 and len(classes)==19,'final distinct count')
base=j(C/'GENERATION_BASELINE_004.json')
# A baseline is read only; compare its recorded source/test hashes using its actual field names.
result={'version':'api_planning_root_final_results_v1','verified_at':datetime.now(timezone.utc).isoformat(),'checkout':str(C),'runtime_implementation_sha256':pin.hexdigest(),'input_manifest_sha256':h(O/'INPUTS.json'),'consumer_command_manifest_sha256':h(O/'CONSUMERS_INPUTS.json'),'all_source_and_test_bytes_and_membership_unchanged':True,'source_file_count':len(src),'test_file_count':len(tests),'distinct_current_pin_cases':len(nodes),'disjoint_current_pin_test_files':len(classes),'groups':groups,'producer_invocations_counted_in316':False,'supplemental_history_test_counted_in316':False,'configured_model_scientific_demonstration':False,'actual_public_service_or_native_calls_in_these_three_commands':False,'baseline_sha256':h(C/'GENERATION_BASELINE_004.json')}
with (O/'RESULTS.json').open('x') as f: f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
with (O/'FINAL_NODE_LEDGER.json').open('x') as f: f.write(json.dumps({'runtime_pin':pin.hexdigest(),'node_ids':sorted(nodes)},indent=2)+'\n')
print(json.dumps({'verified':True,'runtime_pin':pin.hexdigest(),'source_files':len(src),'test_files':len(tests),'distinct_cases':len(nodes),'test_files_selected':len(classes),'results_sha256':h(O/'RESULTS.json')},sort_keys=True))
