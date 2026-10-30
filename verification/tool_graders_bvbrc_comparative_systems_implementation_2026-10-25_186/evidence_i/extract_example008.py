from pathlib import Path
import sqlite3,json,hashlib
root=Path('../evidence_i/pytest_002/test_actual_preparation_task_m0')
db=sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row
forms=[]
for row in db.execute('SELECT episode_id,form FROM runtime_forms WHERE form IS NOT NULL'):
 value=json.loads(row['form'])
 if any(key.startswith('facts_') for key in value): forms.append({'episode_id':row['episode_id'],'form':value})
assert len(forms)==2
assert forms[0]['form']==forms[1]['form']
publications=[]
for path in root.glob('api-service-execution/**/bundle_publication.json'):
 body=json.loads(path.read_text())
 if body['value']['requested_form_status']=='satisfied':
  inputs=json.loads(path.with_name('publication_inputs.json').read_text())
  publications.append({'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'original_inputs_sha256':hashlib.sha256(path.with_name('publication_inputs.json').read_bytes()).hexdigest(),
   'adapter_implementation_sha256':inputs['adapter_implementation_sha256'],'publication':body})
value={'classification':'controlled transport and selected Journal decisions; real executor/custody/provider/typed admission; source-executed synthetic family bytes associated with synthetic task 123; no live service/model/Workflow claim',
 'test':'test_actual_preparation_task_manifest_provider_and_two_parent_boundaries','terminal_receipt':'pytest_002.log; 1 passed in311.80s; exit0',
 'typed_returns':forms,'original_publications':publications,'new_observations_from_parsing_projection_or_forwarding':0}
Path('../evidence_i/FILLED_TYPED_RETURN_001.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print({'typed_returns':len(forms),'satisfied_publications':len(publications),'bytes':Path('../evidence_i/FILLED_TYPED_RETURN_001.json').stat().st_size})
