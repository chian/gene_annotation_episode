"""Independent original244 plan checks and its explicitly controlled fixture."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.domain import validate_schema
HERE=Path(__file__).resolve().parent
OWN=HERE.parent/'a105_endpoint_signal_binding_244'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

manifest=json.loads((OWN/'PLAN_MANIFEST_001.json').read_text())
for f in manifest['files']:
    raw=(OWN/f['path']).read_bytes()
    assert len(raw)==f['bytes'] and hashlib.sha256(raw).hexdigest()==f['sha256'],f['path']
schema=json.loads((OWN/'EXACT_SCHEMAS_001.json').read_text())
paired=json.loads((OWN/'PAIRED_SELECTED_OUTPUT_001.json').read_text())
bad=deepcopy(paired['normal_typed_return']['numbers'])
bad[0]['unit']='pixel^2';bad[0]['formula']='s*(a-t)'
validate_schema(bad,schema['return_schema'])
# Exact context fragments must remain within the already reviewed role witness.
request=json.loads((OWN/'PAIRED_SELECTED_INPUT_001.json').read_text())['arguments']
fragments=0
for name,selected in request['return_context'].items():
    witness=request['selection']['context'][name]
    actual=paired['normal_typed_return']['numbers'][0]['source_context'][name]['fragments']
    assert len(actual)==len(selected)
    for bounds,returned in zip(selected,actual):
        assert witness['start']<=bounds['start']<bounds['end']<=witness['end']
        text=witness['quote'].encode()[bounds['start']-witness['start']:bounds['end']-witness['start']].decode()
        assert returned['text']==text
        fragments+=1
# This is closed, terminal, deliberately scripted fixture state. Immutable mode
# avoids sidecar creation; it must never be used for an actual live WAL run.
state=OWN/'controlled_reproducer_state_004'
before={str(p.relative_to(state)):sha(p) for p in state.rglob('*') if p.is_file()}
db=sqlite3.connect((state/'state.sqlite3').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
try:
    actions=[]
    for index,raw_action,raw_result in db.execute('SELECT decision_index,action,result FROM runtime_actions ORDER BY rowid'):
        action=json.loads(raw_action);result=json.loads(raw_result)
        row={'index':index,'kind':action['kind'],'tool':action.get('tool'),'status':result['status']}
        if action.get('tool')=='source.read':
            text=result['result']['text']
            row['explicit_derived_fixture_values_present']='617' in text and '647' in text
            row['explicit_original_fixture_present']='CONTROLLED ORIGINAL' in text
        actions.append(row)
    observations=db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
finally:db.close()
after={str(p.relative_to(state)):sha(p) for p in state.rglob('*') if p.is_file()}
assert before==after
assert len(actions)==4 and observations==4
assert any(x.get('explicit_derived_fixture_values_present') for x in actions)
assert any(x.get('explicit_original_fixture_present') for x in actions)
report={'status':'progress_plan_correction_required','manifest001_files_checked':len(manifest['files']),
    'wrong_pairing_reproduced':{'component':bad[0]['component'],'unit':bad[0]['unit'],
        'formula':bad[0]['formula'],'accepted_by_proposed001_schema':True},
    'schema001_sha256':sha(OWN/'EXACT_SCHEMAS_001.json'),
    'selected_context_fragments_checked':fragments,
    'controlled_fixture_actions':actions,'controlled_fixture_observations':observations,
    'closed_fixture_files_unchanged':len(before),
    'not_actual_endpoint_typed_delivery':True,'no_actual_provider_payload_inspected':True,
    'no_production_release_yet':True}
with (HERE/'ROOT_ORIGINAL_PLAN_CHECK_002.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'manifest_files':len(manifest['files']),'fragments':fragments,
    'wrong_component_pairing_accepted':True,'controlled_actions':len(actions),
    'controlled_observations':observations,'state_files_unchanged':len(before)}))
