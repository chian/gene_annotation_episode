"""Hash already-read constructor code without importing application modules."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
roots={'original_main':'/home/chia/repos/gene_annotation_episode',
    'inspected004':'/tmp/gene-annotation-hmmer-api-20261022-004',
    'frozen005':'/tmp/gene-annotation-model-context-20261022-005'}
methods={
    'state.py':['Store.__init__','Store.get','Store._require','Store._refs','Store.put'],
    'materials.py':['install_tables','artifact_path','source_window'],
    'materials_packing.py':['install_tables','component_info','component_chunks','materialize (mutating path, prohibited)'],
    'library_targets.py':['install_tables','resolve'],
}
files=[]
for name,read in methods.items():
    witnesses=[]
    for label,base in roots.items():
        path=Path(base)/'gene_annotation_episode'/name
        raw=path.read_bytes()
        witnesses.append({'root_label':label,'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    assert len({(v['sha256'],v['bytes']) for v in witnesses})==1
    files.append({'name':name,'all_three_byte_equal':True,'complete_methods_read':read,'witnesses':witnesses})
value={'status':'read_only_source_equality_verified_not_database_verification',
    'files':files,'application_imports':0,'DB_opens':0,'code_or_state_writes':0,
    'limits':'No assertion that actual original DB schema was inspected. Future helper rejects any actual constructor schema/data delta; no materialize/import/parser call during validation.'}
with (root/'CONSTRUCTOR_READPATHS.json').open('x') as f:
    json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':'constructor_source_pins_equal','files':len(files),'copies_per_file':3,
    'sha256':hashlib.sha256((root/'CONSTRUCTOR_READPATHS.json').read_bytes()).hexdigest()},sort_keys=True))
