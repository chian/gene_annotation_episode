"""Constructed native repository proof; no model, paper or episode-run claim."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]

from gene_annotation_episode.domain import canonical
from gene_annotation_episode import literature_controlled_response_storage as native
from gene_annotation_episode import literature_controlled_response_render
from test_literature_controlled_response_storage_v3 import native_case,seed_runtime_rows


def write(name,value):
    path=HERE/name
    if path.exists():
        assert json.loads(path.read_text())==value
        return
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


descriptor=native.implementation_descriptor(evidence_origin='synthetic_fixture')
snapshot=HERE/'source_snapshot'/'gene_annotation_episode'
snapshot.mkdir(parents=True,exist_ok=True)
imports={}
for name,pin in descriptor['modules'].items():
    path=ROOT/'gene_annotation_episode'/name
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pin
    shutil.copyfile(path,snapshot/name)
    tree=ast.parse(raw)
    imports[name]=[{'line':node.lineno,'module':node.module,'level':node.level,
        'names':[entry.name for entry in node.names]} if isinstance(node,ast.ImportFrom)
        else {'line':node.lineno,'names':[entry.name for entry in node.names]}
        for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
shutil.copyfile(ROOT/'gene_annotation_episode'/'__init__.py',snapshot/'__init__.py')
write('IMPLEMENTATION_DESCRIPTOR.json',descriptor)
write('DIRECT_IMPORTS.json',imports)
def package(name):
    try:return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:return None
write('ENVIRONMENT.json',{'python':sys.version,'packages':{
    name:package(name) for name in ('jsonschema','Pillow','lxml')}})

summary=[]
for name,kwargs in [('text',{}),('graph',{'index':6}),('conditional',{'companion':True,'joints':True}),
                    ('source_authority',{'companion':True,'joints':True,'authority':True})]:
    folder=HERE/'cases'/name
    folder.mkdir(parents=True,exist_ok=False)
    store,context,selection,_=native_case(folder/'store',**kwargs)
    try:
        repository=native.LiteratureControlledResponseRepository(store,context.run_id,
            evidence_origin='synthetic_fixture',expected_descriptor=descriptor)
        outcome=repository.populate_v3(context,selection,'constructed_selected_operation')
        reference=outcome['result']['sheet_ref'];payload=repository.read(reference)
        assert repository.project_cells([reference],permitted_record_refs=[reference],
            components=outcome['result']['component_keys'])==outcome['result']['cells']
        assert repository.populate_v3(context,selection,'constructed_selected_operation')==outcome
        if name=='text':
            selected=[outcome['result']['cells'][0]]
            parent,key=seed_runtime_rows(store,context,outcome,selected)
            repository.receive_cells(parent,selected,key)
            assert repository.received_cells(parent)==selected
        assert not store.list('observation')
        for filename,value in [('selection.json',selection),('outcome.json',outcome),('private_payload.json',payload)]:
            (folder/filename).write_text(json.dumps(value,indent=2)+'\n')
        summary.append({'case':name,'sheet_ref':reference,'projection_status':payload['extraction']['projection_status'],
            'component_keys':payload['component_roster'],'component_count':len(payload['component_roster']),
            'source_artifacts':payload['source_associations'],'observation_count':0,
            'proof_kind':'constructed Store execution; text receipt additionally uses manually seeded journal rows'})
    finally:store.close()
write('CONSTRUCTED_CASES.json',summary)
loaded={}
for name,pin in descriptor['modules'].items():
    module=sys.modules.get('gene_annotation_episode.'+Path(name).stem)
    path=Path(module.__file__).resolve() if module and getattr(module,'__file__',None) else None
    loaded[name]={'loaded_path':str(path) if path else None,
        'loaded_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path else None}
    if path:assert loaded[name]['loaded_file_sha256']==pin
write('ACTUAL_IMPORT_PATHS.json',loaded)
print(json.dumps({'snapshot_modules':len(descriptor['modules']),'constructed_cases':len(summary),
    'component_counts':[case['component_count'] for case in summary],
    'scope':'engineering repository proof only; native LiteratureEpisodes integration owned by095'}))
