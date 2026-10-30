"""Saved-only read-only verification, with scientific acquisition disabled."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from gene_annotation_episode import literature_controlled_response_storage as native
from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.state import Store

descriptor=json.loads((HERE/'IMPLEMENTATION_DESCRIPTOR.json').read_text())
assert native.implementation_descriptor(evidence_origin='synthetic_fixture')==descriptor
loaded={}
for name,pin in descriptor['modules'].items():
    module=importlib.import_module('gene_annotation_episode.'+Path(name).stem)
    path=Path(module.__file__).resolve()
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual==pin
    assert hashlib.sha256((HERE/'source_snapshot'/'gene_annotation_episode'/name).read_bytes()).hexdigest()==pin
    loaded[name]={'loaded_path':str(path),'sha256':actual,'snapshot_matches':True}

def forbidden(*a,**k):raise AssertionError('scientific acquisition/calculator rerun')
native.source.read_controlled_response_v3_inputs=forbidden
native.population.populate_controlled_response_v3=forbidden
local.populate_controlled_response_local=forbidden
owner.populate_controlled_response_owner=forbidden
verified=[]
for folder in sorted((HERE/'cases').iterdir()):
    outcome=json.loads((folder/'outcome.json').read_text());ref=outcome['result']['sheet_ref']
    store=Store(folder/'store');store.db.execute('PRAGMA query_only=1')
    try:
        repo=native.LiteratureControlledResponseRepository(store,'fixture-run',evidence_origin='synthetic_fixture',expected_descriptor=descriptor)
        record=store.get(ref);allowed={record['artifact_ref'],record['request_ref']};get=store.get_artifact
        store.get_artifact=lambda r:get(r) if r in allowed else forbidden()
        payload=repo.read(ref)
        assert payload==json.loads((folder/'private_payload.json').read_text())
        rows=repo.project_cells([ref],permitted_record_refs=[ref],components=outcome['result']['component_keys'])
        assert rows==outcome['result']['cells']
        assert store.db.total_changes==0
        verified.append({'case':folder.name,'exact_cells':len(rows),'query_only':True,
            'database_changes':0,'source_acquisition':False,'calculator_repopulation':False})
    finally:store.close()
result={'scope':'constructed engineering saved-only replay; no model/native episode claim',
        'implementation_imports':loaded,'cases':verified,'all_passed':True}
path=HERE/'READ_ONLY_REPLAY.json'
if path.exists():assert json.loads(path.read_text())==result
else:path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified_cases':len(verified),'verified_modules':len(loaded),'all_passed':True}))
