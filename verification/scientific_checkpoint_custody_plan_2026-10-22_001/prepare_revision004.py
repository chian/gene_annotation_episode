"""Additive planning correction; selected caller metadata/target hashes only."""
from pathlib import Path
import hashlib
import json
import shutil
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/tmp/scientific-checkpoint-custody-contract-20261022-001-9ILLrc')
LAUNCH=Path('/home/chia/repos/gene_annotation_episode/cases/gene_001/runs/configured_development_002/case-launch.json')
def sha(path):
    h=hashlib.sha256(); count=0
    with path.open('rb') as stream:
        for value in iter(lambda:stream.read(1024*1024),b''):
            h.update(value); count+=len(value)
    return {'path':str(path),'sha256':h.hexdigest(),'bytes':count}
def dump(name,value):
    with (ROOT/name).open('x') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
launch_raw=LAUNCH.read_bytes(); launch=json.loads(launch_raw)
case_dir=Path(launch['case_dir']).resolve()
case_path=case_dir/'case.json'; case_raw=case_path.read_bytes(); case=json.loads(case_raw)
assert case['target_kind']=='single_gene'
assert 'target.fna' in case['target_files']
assert set(case['target_files']) <= {'target.fna','target.faa'}
assert case['problem_ref']==launch['problem_ref'] and case['target_ref']==launch['target_ref']
files=[]
for name,expected in sorted(case['target_files'].items()):
    path=case_dir/name
    assert path.is_file() and not path.is_symlink()
    witness=sha(path)
    assert witness['sha256']==expected
    files.append({'declared_name':name,'declared_sha256':expected,'actual':witness,'matches':True})
proof={'status':'actual_selected_caller_authority_metadata_verified',
    'launch':{'path':str(LAUNCH),'sha256':hashlib.sha256(launch_raw).hexdigest(),'bytes':len(launch_raw)},
    'case_directory_from_selected_launch':str(case_dir),
    'case':{'path':str(case_path),'sha256':hashlib.sha256(case_raw).hexdigest(),'bytes':len(case_raw)},
    'target_kind':case['target_kind'],'declared_target_files':files,
    'target_faa_declared':'target.faa' in case['target_files'],
    'biological_sequence_bodies_printed_or_copied':False,'scientific_DB_opens':0,
    'access_scope':'Root expressly requested actual selected case declaration/presence verification; read launch/case JSON and streamed only declared caller target files for hashes, no Store/scientific DB/artifact/provider events.'}
dump('ACTUAL_CASE_AUTHORITY.json',proof)
shutil.copytree(PRIOR,ROOT/'prior001')
shutil.copyfile(PRIOR/'SCHEMAS002.json',ROOT/'SCHEMAS002.json')
shutil.copyfile(PRIOR/'VERIFICATION_PLAN.md',ROOT/'VERIFICATION_PLAN.md')
text=(PRIOR/'CONTRACT003.md').read_text().replace('contract003','contract004',1)
old='Source, run, implementation, case directories and destination must not overlap, contain one another, or share the existing caller/run ancestry markers as in the existing seed no-overlap boundary.'
assert text.count(old)==1
text=text.replace(old,'The DESTINATION must neither equal, contain nor lie inside any source_workspace, source_run_directory, source_implementation_root or the actual selected case_directory. Validate every relationship after non-symlink canonical path resolution. Source authority directories may legitimately nest inside one another: the actual source workspace is inside its original run directory, and the original implementation root contains that run and case. Require those original relationships to match the saved manifest/configuration; do not reject or rebase them. Destination ancestors must not already carry another case/run/policy/execution-binding marker as in the existing seed destination-ancestry boundary. This destination-only rule does not forbid existing source/case/run nesting.')
old='The selected set is exactly run.json, case-launch.json, policy-binding.json, its declared policy source snapshot, episode-execution-binding.json, original native-jobs/configuration.json, and actual fixed-case case.json/target.fna/target.faa as resolved and matched through case-launch.'
assert text.count(old)==1
text=text.replace(old,'The selected set is exactly run.json, case-launch.json, policy-binding.json, its declared policy source snapshot, episode-execution-binding.json, original native-jobs/configuration.json, actual fixed-case case.json and every target file actually declared by that case.json, as resolved and matched through case-launch. This narrow profile accepts target_files keys {target.fna} or {target.fna,target.faa}, requires target.fna and verifies every declared file SHA. target.faa is required/copied only when actually declared; never infer it from an existing scientific protein record or a reusable product. The actual original selected case authority proof is ACTUAL_CASE_AUTHORITY.json. DNA-only prepared() fixtures remain legitimate when their actual case declares only target.fna.')
text += '''

## Revision004 correction authority

This complete CONTRACT004.md supersedes the earlier planning contracts only for adoption; all earlier bytes and hashes are retained under prior001. Root found and rejected the earlier pairwise source-path rule: legitimate existing case/run/workspace nesting must be retained. Only the NEW destination is disjoint from every source authority root and forbidden from reusing run-ancestor markers. Root also required verification of target.faa against the actual selected case, rather than a reusable scientific protein record or fixture assumption. ACTUAL_CASE_AUTHORITY.json records that actual metadata/hash check without scientific DB access. Source and target bytes were read only; no caller configuration, factory, policy or scientific state was changed. The schema field shapes did not change, so SCHEMAS002.json remains byte-identical and the exact schema authority.
'''
with (ROOT/'CONTRACT004.md').open('x') as f:f.write(text)
dump('REVISION_HISTORY.json',{'status':'unadopted_additive_planning_correction',
    'final_contract':'CONTRACT004.md','final_schemas':'SCHEMAS002.json',
    'previous_bundle':str(PRIOR),'previous_manifest':sha(PRIOR/'MANIFEST.json'),
    'previous_contracts':[sha(PRIOR/n) for n in ('CONTRACT.md','CONTRACT002.md','CONTRACT003.md')],
    'schema_unchanged':sha(ROOT/'SCHEMAS002.json'),
    'corrections':['Destination-only nonoverlap; legitimate source nesting matched to original saved caller.',
        'Declared target file authority; target.faa required only when actually declared/present/hash-matching.'],
    'source_configuration_or_state_writes':0,'scientific_DB_opens':0,'application_imports':0})
print(json.dumps({'status':'revision004_written','contract':sha(ROOT/'CONTRACT004.md'),
    'schemas':sha(ROOT/'SCHEMAS002.json'),'actual_case_authority':sha(ROOT/'ACTUAL_CASE_AUTHORITY.json'),
    'target_faa_declared':proof['target_faa_declared'],'declared_file_count':len(files)},sort_keys=True))
