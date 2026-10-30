from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,xml.etree.ElementTree as ET
O=Path('/tmp/model-context-root-005-evidence'); C=Path('/tmp/gene-annotation-model-context-20261022-005'); P=Path('/tmp/model-context-p-005-evidence-NnuEqz7S'); R=Path('/tmp/model-context-r-005-evidence'); h=lambda p:sha256(p.read_bytes()).hexdigest(); j=lambda p:json.loads(p.read_text()); final=j(O/'FINAL_INPUTS001.json'); files=final['files']
actual={p.relative_to(C).as_posix() for pkg in ['gene_annotation_episode','method_loop','tests'] for p in (C/pkg).rglob('*.py')}; assert actual==set(files)
for rel,v in files.items():assert h(C/rel)==v['sha256'] and (C/rel).stat().st_size==v['bytes'],rel
pin=sha256()
for rel,v in sorted(files.items()):
 if not rel.startswith('tests/'):pin.update(rel.encode()+b'\0'+bytes.fromhex(v['sha256']))
assert pin.hexdigest()==final['runtime_pin']=='2c9dc895d0e7c6fa6f6d4df140cb9b88e1274894c8dc7213c46b4580dec68428'
pi=j(P/'INVOCATION001_INPUTS.json'); ri=j(R/'runtime-final-input.json'); ji=j(O/'JOINED001_INPUTS.json'); ci=j(O/'COMPATIBILITY001_INPUTS.json')
for rel,v in files.items():
 if not rel.startswith('tests/'):assert pi['files'][rel]==ri['files'][rel]==ji['source_files'][rel]==v,rel
assert ri['files']==files
# P ran while R expanded an unselected new test file. Its selected file and all
# runtime/old tests match; do not relabel its whole test snapshot as final.
assert pi['files']['tests/test_model_context_presentation.py']==files['tests/test_model_context_presentation.py']
for rel,v in ji['original_test_files'].items():assert pi['files'][rel]==files[rel]==v
assert ci['source_identity_sha256']==h(O/'JOINED001_INPUTS.json')
nodes=Counter(); classes=set(); groups=[]
for name,d,stem,count,seconds in [('P',P,'component001',67,.42),('R',R,'runtime-final',21,73.43),('root_detached',O,'connected002',1,19.40),('root_compatibility',O,'compatibility001',28,152.61)]:
 xp=d/(stem+'.xml');lp=d/(stem+'.log');xml=ET.parse(xp).getroot();cases=xml.findall('.//testcase');ids=[q.attrib['classname']+'::'+q.attrib['name'] for q in cases];assert len(ids)==len(set(ids))==count and all(not list(q) for q in cases)
 for q in xml.findall('.//testsuite'):assert all(int(q.attrib.get(k,0))==0 for k in ['failures','errors','skipped'])
 for q in cases:classes.add(q.attrib['classname'])
 nodes.update(ids);groups.append({'group':name,'passed':count,'exit_code':0,'duration_seconds':seconds,'xml_path':str(xp),'xml_sha256':h(xp),'log_path':str(lp),'log_sha256':h(lp),'node_ids':ids})
expected='tests.test_wait_estimation_inputs::test_only_actual_own_observations_are_returned_in_completion_order_with_signed_values';assert len(nodes)==116 and len(classes)==7 and sum(nodes.values())==117 and {k:v for k,v in nodes.items() if v>1}=={expected:2}
measurement=j(O/'ACTUAL_SAVED_CONTEXT_MEASUREMENT001.json');assert measurement['model_presentation_chars']==392252 and measurement['raw_history_rows']==175 and not measurement['source_run_reconstructed'] and measurement['model_provider_calls']==0
out={'version':'model_context_generation005_aggregate_results_v1','runtime_pin':pin.hexdigest(),'final_input_sha256':h(O/'FINAL_INPUTS001.json'),'source_count':134,'test_count':214,'all348_current_source_test_bytes_and_membership_match':True,'old211_tests_unchanged':True,'distinct_cases':116,'executed_final_group_testcases':117,'distinct_test_files':7,'repeated_node':expected,'repeated_node_executions':2,'groups':groups,'earlier_partial_or_failed_invocations_counted':False,'P_unselected_runtime_test_snapshot_is_historical':True,'actual_saved_context_measurement_sha256':h(O/'ACTUAL_SAVED_CONTEXT_MEASUREMENT001.json'),'configured_model_science_proved':False,'actual_scientific_source_resumed':False}
out['earlier_passing_connected001_excluded_as_same_node_rerun']=True
out['second_detached_input_sha256']=h(O/'JOINED002_INPUTS.json')
out['preserved_second_fixture_sha256']=h(O/'PRESERVED_DETACHED002/PRESERVATION.json')
with (O/'RESULTS002.json').open('x') as f:f.write(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'distinct_cases':len(nodes),'executed_final_testcases':sum(nodes.values()),'test_files':len(classes),'runtime_pin':pin.hexdigest(),'result_sha256':h(O/'RESULTS002.json')}))
