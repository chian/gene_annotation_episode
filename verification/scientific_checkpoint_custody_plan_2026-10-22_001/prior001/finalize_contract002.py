"""Add explicit closed provenance outputs in NEW revision files; no app access."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
source=json.loads((root/'SCHEMAS.json').read_text())
defs=source['$defs']
S={'type':'string','minLength':1}
N={'type':'integer','minimum':0}
H={'type':'string','pattern':'^[a-f0-9]{64}$'}
REF={'type':'string','pattern':'^[a-z][a-z_]*_[a-f0-9]{24,64}$'}
PATH={'type':'string','pattern':'^/[^\u0000]*$'}
def obj(fields):
    return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
def array(item):
    return {'type':'array','items':item}
def const(value):
    return {'const':value}
file=obj({'path':S,'sha256':H,'bytes':N})
nullable_file={'anyOf':[file,{'type':'null'}]}
mapping=obj({'source_path':PATH,'checkpoint_relative_path':S,'sha256':H,'bytes':N})
defs['receipt']['properties']['source']['properties']['authority_files']=array(mapping)
defs['implementation_file_manifest']=obj({
    'version':const('scientific_checkpoint_source_file_inventory_v1'),
    'source_implementation_root':PATH,'implementation_sha256':H,
    'files':array(obj({'relative_path':S,'sha256':H,'bytes':N}))})
defs['committed_reference_manifest']=obj({
    'version':const('scientific_checkpoint_committed_reference_inventory_v1'),
    'input_count':N,'record_count':N,
    'records':array(obj({'reference':REF,'record_type':S,
        'source_table':{'enum':['inputs','records']},
        'data_raw_utf8_sha256':H,'data_raw_utf8_bytes':N}))})
native_preservation=obj({'mode':const('read_only_immutable_database_absent_or_empty_wal'),
    'database_before':file,'database_after':file,'wal_before':nullable_file,'wal_after':nullable_file,
    'shm_before':nullable_file,'shm_after':nullable_file,'source_files_equal':const(True),
    'reader_bookkeeping_changes':const([])})
defs['execution_inventory']['properties']['native_registry_preservation']=native_preservation
defs['execution_inventory']['required'].append('native_registry_preservation')
# The receipt used a shared Python dictionary before JSON serialization; update
# its independent parsed nested copy explicitly, without changing prior bytes.
nested=defs['receipt']['properties']['source']['properties']['execution_inventory']
nested['properties']['native_registry_preservation']=native_preservation
nested['required'].append('native_registry_preservation')
source['$id']='urn:scientific-checkpoint-custody-contract:20261022:002'
with (root/'SCHEMAS002.json').open('x') as f:
    json.dump(source,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
    f.write('\n')
text=(root/'CONTRACT.md').read_text().replace('contract001','contract002',1).replace('SCHEMAS.json','SCHEMAS002.json')
text += '''

## Closed output details added in revision002

SCHEMAS002.json is the final proposed schema authority. The earlier SCHEMAS.json/CONTRACT.md and check-001 output remain preliminary planning history. The revised complete CONTRACT002.md incorporates the same semantics plus this final explicit provenance boundary; no actual custody/schema implementation is present.

Each receipt source.authority_files row is exactly {source_path,checkpoint_relative_path,sha256,bytes}. The source path is original and absolute; checkpoint_relative_path is a unique relative path under checkpoint/authority with no '..', empty component or symlink. Copy the exact raw bytes there; hash/size must match both paths. Do not change old absolute references inside those files or install them as run.json/case-launch.json/policy-binding.json at the new workspace root. The selected set is exactly run.json, case-launch.json, policy-binding.json, its declared policy source snapshot, episode-execution-binding.json, original native-jobs/configuration.json, and actual fixed-case case.json/target.fna/target.faa as resolved and matched through case-launch. The native jobs.sqlite is hashed/read for the empty-inventory precondition and is NOT copied/adopted. Its own DB/WAL/SHM before/after byte/existence witnesses are now explicit in execution_inventory.native_registry_preservation. Scientific DB preservation and native DB preservation must both pass zero-write rules.

checkpoint/source-implementation-files.json uses implementation_file_manifest: exact relative Python source names across both packages in the existing implementation pin order, byte sizes and SHA256, original root and computed expected implementation pin. It is an inventory only, not a source code snapshot or authority to import unpinned code. The exact source files remain independently pinned/external; no claim of relocating source executables. checkpoint/committed-references.json uses committed_reference_manifest: every inputs/records ID exactly once with table/kind and hash/length over the original data TEXT encoded UTF-8; entries are sorted by source_table then reference using UTF-8 byte order, counts equal observed tables. No JSON reserialization or scientific classification occurs. A final selected-ref resolution through actual destination Store.get checks the stored row identity/kind; existing explicit forward-reference semantics supply dependency checks. Receipt paths name checkpoint/state.sqlite3, checkpoint/tables.json, checkpoint/artifacts.json and checkpoint/committed-references.json, with actual hash/byte witnesses.

New source request metadata and observation-index payloads are canonical JSON bytes encoded UTF-8 without a trailing LF; the raw observation stream uses its separately declared one-LF framing. Inventory/receipt files are canonical JSON encoded UTF-8 plus exactly one trailing LF. Canonical means the existing domain.canonical rule: sort_keys=True,separators=(',',':'),allow_nan=False (including its default ensure_ascii=True); do not substitute another Unicode spelling for hashes. SHA fields always bind actual artifact/file bytes as just specified. Source settings/request/data TEXT hashes remain original UTF-8 bytes, even when their original spelling differs from canonical. The fork_id canonical identity material has the exact field names listed above and a sorted caller list. Neither final result nor failure is persisted into the old source. The return wrapper receipt.path is absolute at its published location; all checkpoint file paths in receipt are destination-relative, while source path witnesses are explicitly original absolute paths.

All source manifest/path/unique/count relationships are required in addition to closed shapes: authority destinations cannot collide; native_registry_database/configuration hashes match their explicit witnesses; table count and artifact count/bytes match their manifests; committed-reference counts/lists match snapshot tables and caller coverage; index count/ranges/hash/offsets match the raw stream; each added source's artifact/text/request/parent/operand fields must equal its declared actual payload. Source readonly preservation is for the declared databases/sidecars/authority files/all registered artifacts, not arbitrary unrelated/private workspace files. No private provider event traversal is authorized or needed.
'''
with (root/'CONTRACT002.md').open('x') as f:
    f.write(text)
checker=(root/'check_contract_syntax.py').read_text().replace("'SCHEMAS.json'","'SCHEMAS002.json'")
with (root/'check_contract_syntax002.py').open('x') as f:
    f.write(checker)
print(json.dumps({'status':'final_revision_files_written','application_imports':0,'DB_opens':0,
    'schemas_sha256':hashlib.sha256((root/'SCHEMAS002.json').read_bytes()).hexdigest(),
    'contract_sha256':hashlib.sha256((root/'CONTRACT002.md').read_bytes()).hexdigest()},sort_keys=True))
