from pathlib import Path
from hashlib import sha256
import json,xml.etree.ElementTree as ET
O=Path('/tmp/model-context-root-005-evidence'); inp=json.loads((O/'JOINED001_INPUTS.json').read_text()); C=Path(inp['checkout']); h=lambda p:sha256(p.read_bytes()).hexdigest(); current={p.relative_to(C).as_posix() for pkg in ['gene_annotation_episode','method_loop'] for p in (C/pkg).rglob('*.py')}; assert current==set(inp['source_files'])
for r,v in inp['source_files'].items():assert h(C/r)==v['sha256'] and (C/r).stat().st_size==v['bytes']
for r,v in inp['original_test_files'].items():assert h(C/r)==v['sha256']
assert h(C/inp['selected_test']['path'])==inp['selected_test']['sha256']; cases=ET.parse(O/'connected001.xml').getroot().findall('.//testcase'); assert len(cases)==1 and not list(cases[0])
actual=Path('/tmp/pytest-of-chia/pytest-906/test_opt_in_actual_worker_keep0'); run=json.loads((actual/'run/run.json').read_text()); assert run['restoration']=={'preview_size':0,'model_presentation':'bounded_wait_history_v1'}
r={'version':'model_context_joined001_result_v1','runtime_pin':inp['runtime_pin'],'source_files':len(current),'source_files_unchanged':True,'original_211_test_files_unchanged':True,'selected_wrapper_unchanged':True,'passed':1,'exit_code':0,'duration_seconds':20.78,'node_id':cases[0].attrib['classname']+'::'+cases[0].attrib['name'],'input_sha256':h(O/'JOINED001_INPUTS.json'),'log_sha256':h(O/'connected001.log'),'xml_sha256':h(O/'connected001.xml'),'fixture_directory':str(actual),'fixture_run_id':run['run_id'],'claim_limit':'Actual detached worker uses scripted model transport, no actual model/public-provider/native computation. Other unselected NEWtest-only writers were active; no full-test freeze asserted.'}
with (O/'JOINED001_RESULT.json').open('x') as f:f.write(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps({'passed':1,'runtime_pin':r['runtime_pin'],'fixture':str(actual),'result_sha256':h(O/'JOINED001_RESULT.json')}))
