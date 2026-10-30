"""Seal planning evidence only; no application imports or source/state writes."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
def dump(name,value):
    with (root/name).open('x') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
text=(root/'CONTRACT002.md').read_text().replace('contract002','contract003',1)
old="b'sqlite_storage_class_frame_v1\\\\0'"
assert text.count(old)==1
text=text.replace(old,"the ASCII bytes for 'sqlite_storage_class_frame_v1' followed by one NUL byte (0x00)")
text=text.replace('The revised complete CONTRACT002.md incorporates', 'The revised complete CONTRACT003.md incorporates')
text += '\nRevision003 clarifies the exact typed-row header terminator as byte0x00 (not printable backslash characters). SCHEMAS002.json remains the final proposed schema. Earlier documents/logs remain unchanged preliminary history.\n'
with (root/'CONTRACT003.md').open('x') as f:
    f.write(text)
commands=[]
for stem,script in [('build-001','build_planning_bundle.py'),('check-001','check_contract_syntax.py'),
        ('finalize-002','finalize_contract002.py'),('check-002','check_contract_syntax002.py')]:
    commands.append({'command':f'/home/chia/repos/gene_annotation_episode/.venv/bin/python {root/script} > {root/(stem+".stdout.log")} 2> {root/(stem+".stderr.log")}',
        'cwd':'/home/chia/repos/gene_annotation_episode','exit_code':0,
        'stdout':stem+'.stdout.log','stderr':stem+'.stderr.log'})
dump('COMMANDS.json',{'scope':'Exact executed planning artifact-generation/schema/readset commands. Read-only source display/discovery commands are described in READSET/DISCOVERY_LIMITS and tool history; no invented complete shell transcript.',
    'commands':commands})
check=json.loads((root/'check-002.stdout.log').read_text())
dump('RESULTS.json',{'status':'planning_complete_pending_root_adoption',
    'contract':'CONTRACT003.md','schemas':'SCHEMAS002.json','verification_plan':'VERIFICATION_PLAN.md',
    'representation_readset_checks':check,
    'schema_check_scope':'syntax/closed object representation plus immutable readset/P002/runtime hash checks only; no implementation or application test',
    'source_writes':0,'scientific_DB_opens':0,'application_imports':0,
    'custody_code_changes':0,'actual_forks':0,'model_public_native_calls':0,
    'root_confirmed_source_profile':{'main_database_bytes':211947520,'WAL_bytes':0},
    'not_done':['custody implementation','synthetic actual-consumer verification','actual scientific fork','new caller materialization or launch','permanent custody publication']})
with (root/'REVIEW_ENTRYPOINT.md').open('x') as f:
    f.write('Final review authority: CONTRACT003.md + SCHEMAS002.json + VERIFICATION_PLAN.md. All are planning-only/unadopted until root adopts exact bytes. Earlier CONTRACT.md/CONTRACT002.md/SCHEMAS.json and prior logs remain unmodified history. RESULTS.json and INPUT_PROVENANCE.json state checks/limits. No custody code/fork or scientific DB open occurred.\n')
members=[]
for path in sorted(root.iterdir()):
    if path.is_file():
        raw=path.read_bytes()
        members.append({'path':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'mode':'0444'})
dump('MANIFEST.json',{'version':'scientific_checkpoint_custody_planning_bundle_v1',
    'status':'unadopted_planning_only','final_contract':'CONTRACT003.md','final_schemas':'SCHEMAS002.json',
    'members':members,'member_count':len(members),'total_bytes':sum(x['bytes'] for x in members)})
for path in root.iterdir():
    if path.is_file(): path.chmod(0o444)
root.chmod(0o555)
print(json.dumps({'bundle':str(root),'members_excluding_manifest':len(members),
    'manifest_sha256':hashlib.sha256((root/'MANIFEST.json').read_bytes()).hexdigest(),
    'contract_sha256':hashlib.sha256((root/'CONTRACT003.md').read_bytes()).hexdigest(),
    'schemas_sha256':hashlib.sha256((root/'SCHEMAS002.json').read_bytes()).hexdigest(),
    'files_mode':'0444','directory_mode':'0555'},sort_keys=True))
