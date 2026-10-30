"""Constructed engineering custody proof;095 owns actual episode/worker proof."""
import ast
from copy import deepcopy as cp
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_controlled_response_storage as native
from gene_annotation_episode import literature_controlled_response_render as renderer
from test_literature_controlled_response_storage_v3 import native_case,seed_runtime_rows
from test_literature_controlled_response_uncertainty_units_v3 import configure_uncertainty_units
from test_literature_controlled_response_render_v3 import text_for


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


descriptor=native.implementation_descriptor(evidence_origin='synthetic_fixture')
snapshot=HERE/'final_source_snapshot'/'gene_annotation_episode';snapshot.mkdir(parents=True,exist_ok=False)
imports={};loaded={}
for name,pin in descriptor['modules'].items():
    path=ROOT/'gene_annotation_episode'/name;raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pin
    shutil.copyfile(path,snapshot/name)
    tree=ast.parse(raw)
    imports[name]=[{'line':n.lineno,'module':n.module,'level':n.level,'names':[a.name for a in n.names]}
        if isinstance(n,ast.ImportFrom) else {'line':n.lineno,'names':[a.name for a in n.names]}
        for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
    module=importlib.import_module('gene_annotation_episode.'+Path(name).stem)
    actual=Path(module.__file__).resolve();assert hashlib.sha256(actual.read_bytes()).hexdigest()==pin
    loaded[name]={'path':str(actual),'sha256':pin}
shutil.copyfile(ROOT/'gene_annotation_episode'/'__init__.py',snapshot/'__init__.py')
write(HERE/'FINAL_DESCRIPTOR.json',descriptor)
write(HERE/'FINAL_DIRECT_IMPORTS.json',imports)
write(HERE/'FINAL_IMPORT_PATHS.json',{'purpose':'Explicit import/hash verification, not a claim every module executed numerically','modules':loaded})


def unknown(f):f.args['joint_scopes'][0]['normalization']={'value':'unknown','witnesses':[]}
def conflicting(f):f.args['joint_scopes'][1]['calibration']={'value':'conflicting','witnesses':[f.witness('nmol/min'),f.witness('Physical A.')]}
def final_joint(f):
    f.args['companion_readings'][0]['reading']['measurement']=cp(f.args['arms']['protein_condition1']['measurement'])
    f.args['reading_reconciliations'][0]['authority']['reading']['reading_key']='A-display'
    for index,number in enumerate(('0.123456789','0.987654321')):
        quote='Calibration used '+number+' standards.';f.append(quote)
        f.args['joint_scopes'][index]['calibration']={'value':'same','witnesses':[f.witness(quote)]}


summary=[]
cases=[('unknown_scope',{'companion':True,'joints':True,'modify':unknown},'joint:0:controlled_response_difference'),
    ('conflicting_scope',{'companion':True,'joints':True,'modify':conflicting},'joint:1:controlled_response_difference'),
    ('final_joint',{'companion':True,'joints':True,'authority':True,'modify':final_joint},'final:controlled_response_difference'),
    ('different_uncertainty_unit',{'modify':lambda f:configure_uncertainty_units(f)},'raw:protein_condition1:primary'),
    ('unknown_response_unit',{'modify':lambda f:configure_uncertainty_units(f,unknown_response=True)},'raw:protein_condition1:primary')]
for name,kwargs,key in cases:
    folder=HERE/'final_cases'/name;folder.mkdir(parents=True,exist_ok=False)
    store,context,selection,_=native_case(folder/'store',**kwargs)
    try:
        repo=native.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture',expected_descriptor=descriptor)
        outcome=repo.populate_v3(context,selection,'fixture-run:fixture-child:4');ref=outcome['result']['sheet_ref']
        selected=repo.project_cells([ref],permitted_record_refs=[ref],components=[key])
        parent,delivery=seed_runtime_rows(store,context,outcome,selected)
        repo.receive_cells(parent,selected,delivery)
        assert repo.received_cells(parent)==selected
        refs=repo.cell_record_refs(selected);bindings=repo.semantic_bindings(selected)
        records={r:store.get(r) for r in refs}
        text=text_for(selected,records,bindings)
        if name=='final_joint':assert '0.987654321' not in text and '0.123456789' not in text
        if 'uncertainty_unit' in name or name=='unknown_response_unit':
            assert selected[0]['reported_uncertainty_unit']=='uM/min'
            assert 'magnitude_and_interval_unit' in text
        parent_state={**parent.as_record(),'received_record_refs':refs}
        for filename,value in [('selection.json',selection),('outcome.json',outcome),('private_payload.json',repo.read(ref)),
                               ('selected_cells.json',selected),('parent_context.json',parent_state)]:write(folder/filename,value)
        (folder/'rendered.txt').write_text(text+'\n')
        summary.append({'case':name,'exact_selected_keys':[key],'roster_count':len(outcome['result']['component_keys']),
            'status':selected[0]['cell']['status'],'uncertainty_unit':selected[0]['reported_uncertainty_unit'],
            'source_reading_unit':selected[0]['native_reading']['unit'] if selected[0]['native_reading'] else None,
            'runtime_digest_bound':True,'observations':len(store.list('observation')),
            'proof_kind':'Constructed source execution plus manually seeded runtime rows; NOT native episode/model/paper proof'})
    finally:store.close()

from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
def forbidden(*a,**k):raise AssertionError('scientific acquisition or numerical reexecution')
native.source.read_controlled_response_v3_inputs=forbidden
native.population.populate_controlled_response_v3=forbidden
local.populate_controlled_response_local=forbidden
owner.populate_controlled_response_owner=forbidden
for case in summary:
    folder=HERE/'final_cases'/case['case'];store=Store(folder/'store');store.db.execute('PRAGMA query_only=1')
    try:
        outcome=json.loads((folder/'outcome.json').read_text());ref=outcome['result']['sheet_ref']
        record=store.get(ref);allowed={record['artifact_ref'],record['request_ref']};get=store.get_artifact
        store.get_artifact=lambda r:get(r) if r in allowed else forbidden()
        repo=native.LiteratureControlledResponseRepository(store,'fixture-run',evidence_origin='synthetic_fixture',expected_descriptor=descriptor)
        assert repo.read(ref)==json.loads((folder/'private_payload.json').read_text())
        parent=BindingContext(**json.loads((folder/'parent_context.json').read_text()))
        assert repo.received_cells(parent)==json.loads((folder/'selected_cells.json').read_text())
        assert store.db.total_changes==0
        case.update(query_only_reconstruction=True,database_changes_on_reconstruction=0,
            source_acquisition_on_reconstruction=False,numerical_repopulation_on_reconstruction=False)
    finally:store.close()
write(HERE/'FINAL_CONSTRUCTED_CASES.json',summary)
print(json.dumps({'constructed_cases':len(summary),'snapshot_modules':len(descriptor['modules']),
    'query_only_replays':len(summary),'all_passed':True,'native_episode_proof':'Separate095 workload'}))
