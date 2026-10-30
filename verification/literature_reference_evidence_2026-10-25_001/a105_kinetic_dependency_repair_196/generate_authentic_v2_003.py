from pathlib import Path
import sys,json,hashlib,dataclasses
from dataclasses import replace
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PIN=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_optical_parent_repair_138/pin_137_001'
sys.dont_write_bytecode=True;sys.path[:0]=[str(PIN),str(PIN/'tests')]
from gene_annotation_episode.communication import plain
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository,_FROZEN,VERSION
from gene_annotation_episode.literature_kinetic_model_storage import LiteratureKineticModelRepository,COMPONENTS as MODEL_COMPONENTS
from test_literature_kinetic_storage import setup
from test_literature_kinetic_model_inputs import setup_model
assert VERSION=='literature_kinetic_population_record_v2'
assert Path(sys.modules['gene_annotation_episode.literature_kinetic_storage'].__file__).resolve().is_relative_to(PIN)
assert Path(sys.modules['gene_annotation_episode.literature_kinetic_model_storage'].__file__).resolve().is_relative_to(PIN)
for name,sha in _FROZEN.items():assert hashlib.sha256((PIN/'gene_annotation_episode'/name).read_bytes()).hexdigest()==sha
BASE=OUT/'authentic_v2';BASE.mkdir(exist_ok=False)
def dump(name,value):
 with (BASE/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def context_record(c):return {field.name:plain(getattr(c,field.name)) for field in dataclasses.fields(c)}
rows=[]
for case in ('point','censored','missing_unit'):
 store,context,args=setup(BASE/case,kind='Km',unit='mM',n='<.008' if case=='censored' else '.008',d='.002',change=(lambda a:a['numerator']['measurement'].update(unit=None)) if case=='missing_unit' else None)
 repo=LiteratureKineticRepository(store,context.run_id);outcome=repo.populate(context,args,'original-selected')
 ref=outcome['result']['sheet_ref'];saved=repo.read(ref);projected=repo.project_cells([ref],permitted_record_refs=outcome['record_refs'])
 owner=replace(context,received_record_refs=(*context.received_record_refs,*outcome['record_refs']))
 parent=replace(owner,episode_id='parent',role='annotation',path=(('annotation','parent'),),assignment={})
 admitted=[projected[3]];repo.receive_cells(parent,admitted,'original-trusted-manual-admission')
 assert repo.received_cells(parent)==admitted
 raw=store.get_artifact(store.get(ref)['artifact_ref']);request=store.get_artifact(store.get(ref)['request_ref'])
 dump(case+'_SNAPSHOT.json',{'context':context_record(context),'parent':context_record(parent),'arguments':args,'outcome':outcome,'saved':saved,'projected':projected,'admitted':admitted,'sheet_ref':ref,'payload_sha256':hashlib.sha256(raw).hexdigest(),'request_sha256':hashlib.sha256(request).hexdigest()})
 store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
 rows.append({'case':case,'version':saved['version'],'extraction_version':saved['extraction']['version'],'source_module':str(Path(sys.modules['gene_annotation_episode.literature_kinetic_storage'].__file__).resolve())})
# Genuine original-v2 native + v1 model selected under the same intact code.
store,context,args,model_args,_,_=setup_model(BASE/'model')
native=LiteratureKineticRepository(store,context.run_id).populate(context,args,'original-native')
owner=replace(context,received_record_refs=(*context.received_record_refs,*native['record_refs']))
model_args={**model_args,'source_ref':native['result']['sheet_ref']}
repo=LiteratureKineticModelRepository(store,context.run_id);outcome=repo.populate(owner,model_args,'original-model')
ref=outcome['result']['sheet_ref'];saved=repo.read(ref);projected=repo.project_cells([ref],permitted_record_refs=outcome['record_refs'])
owner=replace(owner,received_record_refs=(*owner.received_record_refs,*outcome['record_refs']))
parent=replace(owner,episode_id='parent',role='annotation',path=(('annotation','parent'),),assignment={})
admitted=[projected[-1]];repo.receive_cells(parent,admitted,'original-trusted-manual-model-admission')
assert repo.received_cells(parent)==admitted
native_saved=LiteratureKineticRepository(store,context.run_id).read(native['result']['sheet_ref'])
dump('model_SNAPSHOT.json',{'context':context_record(owner),'parent':context_record(parent),'arguments':model_args,'outcome':outcome,'saved':saved,'projected':projected,'admitted':admitted,'sheet_ref':ref,'native_saved':native_saved,'native_sheet_ref':native['result']['sheet_ref']})
store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
files={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*') if p.is_file()}
dump('FILES_001.json',files)
metadata={'origin':'New before-change synthetic original-v2 operations genuinely executed using intact archived137code; not historical paper findings and no relabelled current results','pin':str(PIN),'all_six_original_dependencies_match':True,'states':rows,'model_native_version':native_saved['version'],'model_version':saved['version'],'no_production_edits_yet':True}
dump('GENERATION_RECEIPT_001.json',metadata)
print(json.dumps(metadata,indent=2))
