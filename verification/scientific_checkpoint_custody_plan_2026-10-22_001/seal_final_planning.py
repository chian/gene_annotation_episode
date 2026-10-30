"""Seal only this private planning bundle after independent review; no app."""
from pathlib import Path
import hashlib
import json
import shutil
root=Path(__file__).resolve().parent
rroot=Path('/tmp/scientific-checkpoint-r-review-20261022-001-vaoqiyiq')
def witness(path):
    raw=path.read_bytes();return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def dump(name,value):
    with (root/name).open('x') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
expected={
    'CONTRACT007.md':'48da8518ccd4509b9d2f28bccb771af92a088646f795e5db425e14aec9782be7',
    'SCHEMAS004.json':'b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112',
    'VERIFICATION_PLAN003.md':'37fb2346786bdd1363b24c6e07fbaf1e7480413e6fe842a4dbfbef10954e2415'}
for name,sha in expected.items():assert witness(root/name)['sha256']==sha
rmanifest=json.loads((rroot/'MANIFEST001.json').read_text())
assert witness(rroot/'MANIFEST001.json')['sha256']=='300843c93a0f30af89d84f72cd2c0e445e237c419279044ee012d133bb7c1379'
assert {p.name for p in rroot.iterdir()}=={v['name'] for v in rmanifest['files']}|{'MANIFEST001.json'}
for item in rmanifest['files']:
    path=rroot/item['name'];w=witness(path)
    assert not path.is_symlink() and w['bytes']==item['bytes'] and w['sha256']==item['sha256']
shutil.copytree(rroot,root/'independent-r-review')
for path in rroot.iterdir():assert witness(path)['sha256']==witness(root/'independent-r-review'/path.name)['sha256']
old=json.loads((root/'SCHEMAS002.json').read_text())['$defs']
new=json.loads((root/'SCHEMAS004.json').read_text())['$defs']
assert set(old)==set(new)
changed=[name for name in sorted(old) if old[name]!=new[name]]
assert changed==['failure']
dump('SCHEMA_SUCCESS_COMPATIBILITY.json',{'status':'all_success_receipt_source_inventory_index_request_shapes_unchanged',
    'definitions_unchanged':len(new)-1,'changed_definition_names':changed,
    'source_schema':witness(root/'SCHEMAS002.json'),'final_schema':witness(root/'SCHEMAS004.json')})
dump('FINAL_REVIEW_INPUTS.json',{'status':'planning_complete_pending_root_adoption',
    'final_authorities':[witness(root/name) for name in expected],
    'independent_review':witness(root/'independent-r-review'/'R_REVIEW001.md'),
    'independent_manifest':witness(root/'independent-r-review'/'MANIFEST001.json'),
    'actual_case_authority':witness(root/'ACTUAL_CASE_AUTHORITY.json'),
    'constructor_source_readpaths':witness(root/'CONSTRUCTOR_READPATHS.json'),
    'prior_exact_bundle_manifest':witness(root/'prior001'/'MANIFEST.json'),
    'future_code_scope':'NEW006 after exact root adoption; no005 or earlier source edits here'})
commands=[]
for stem,script in [('prepare-004','prepare_revision004.py'),('check-004','check_revision004.py'),
    ('refine-005','refine_contract005.py'),('constructor-005','capture_constructor_pins.py'),
    ('publication-006','refine_publication006.py'),('schema-003','check_schema003.py'),
    ('retained-007','refine_retained007.py'),('schema-004','check_schema004.py')]:
    assert (root/(stem+'.stderr.log')).read_bytes()==b''
    commands.append({'command':f'/home/chia/repos/gene_annotation_episode/.venv/bin/python {root/script} > {root/(stem+".stdout.log")} 2> {root/(stem+".stderr.log")}',
        'cwd':'/home/chia/repos/gene_annotation_episode','exit_code':0,
        'stdout':stem+'.stdout.log','stderr':stem+'.stderr.log'})
dump('FINAL_COMMANDS.json',{'scope':'Exact planning generation/source-pin/schema-guard commands only; read-display commands are retained in tool history/readset. No invented complete shell transcript.',
    'commands':commands,'administrative_note':'CONTRACT006.PRECHECK.md preserves precheck bytes before historical-schema wording clarified in final006. A cp --no-clobber metadata-copy command emitted only its portability warning and exited0; no source/application action or test failed.'})
dump('FINAL_RESULTS.json',{'status':'planning_complete_independent_review_no_remaining_concrete_conflict',
    'adoption':'not_adopted_by_this_bundle; root decides exact future code scope',
    'final_authorities':list(expected),
    'B_representation_only_check':json.loads((root/'schema-004.stdout.log').read_text()),
    'R_representation_only_check':json.loads((root/'independent-r-review'/'representation-check.log').read_text()),
    'actual_selected_case_files_verified':2,'prior_bundle_files_preserved_exact':27,
    'independent_review_files_copied_exact':8,
    'all_success_schema_definitions_unchanged_from002':12,
    'scientific_DB_opens':0,'application_imports':0,'custody_code_changes':0,
    'actual_forks':0,'new_scientific_runs':0,'application_tests':0,'model_public_native_calls':0,
    'limits':['Original execution counts/zero-WAL size attributed to P002/root retained facts, not fresh B/R DB reads.',
        'Schema examples/readset hashes are not actual filesystem/Store/custody verification.',
        'Actual source-backed implementation and unique-basetemp synthetic consumer proofs remain future work.',
        'Actual fork/new caller/publication remain separately scoped after code verification.']})
with (root/'FINAL_ENTRYPOINT.md').open('x') as f:
    f.write('Final proposed authority is CONTRACT007.md + SCHEMAS004.json + VERIFICATION_PLAN003.md, pinned by FINAL_REVIEW_INPUTS.json and this bundle manifest. Root adoption is still required before NEW006 code. All earlier README/contracts/schema/check outputs are preserved historical drafts, superseded for final review by these exact files. Independent R review found no remaining concrete conflict after accepted corrections; its exact8-file bundle is copied under independent-r-review. No custody implementation/application test/scientific DB open/fork/new run/model/HTTP/native action occurred. Source/score/policy/default caller remain unchanged.\n')
members=[]
for path in sorted(root.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        value=witness(path);value['path']=str(path.relative_to(root));value['mode']='0444';members.append(value)
dump('MANIFEST_FINAL.json',{'version':'scientific_checkpoint_custody_planning_bundle_v2',
    'status':'planning_complete_pending_root_adoption','final_contract':'CONTRACT007.md',
    'final_schemas':'SCHEMAS004.json','final_verification_plan':'VERIFICATION_PLAN003.md',
    'members':members,'member_count':len(members),'total_bytes':sum(v['bytes'] for v in members)})
for path in root.rglob('*'):
    if path.is_file():path.chmod(0o444)
for path in sorted((p for p in root.rglob('*') if p.is_dir()),reverse=True):path.chmod(0o555)
root.chmod(0o555)
print(json.dumps({'bundle':str(root),'manifest':witness(root/'MANIFEST_FINAL.json'),
    'members_excluding_manifest':len(members),'bytes_excluding_manifest':sum(v['bytes'] for v in members),
    'final_contract':witness(root/'CONTRACT007.md'),'final_schema':witness(root/'SCHEMAS004.json'),
    'final_verification_plan':witness(root/'VERIFICATION_PLAN003.md'),
    'file_modes':'0444','directory_modes':'0555'},sort_keys=True))
