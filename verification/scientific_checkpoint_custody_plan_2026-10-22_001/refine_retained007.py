"""Final additive nullable-stage/fixture-custody planning refinement."""
from pathlib import Path
import json
import hashlib
root=Path(__file__).resolve().parent
def sha(name):return hashlib.sha256((root/name).read_bytes()).hexdigest()
schemas=json.loads((root/'SCHEMAS003.json').read_text())
schemas['$id']='urn:scientific-checkpoint-custody-contract:20261022:004'
for relation in schemas['$defs']['failure']['allOf']:
    if relation['if']['properties']['publication_state']['const']=='retained_stage':
        relation['then']['properties']['staging_workspace']={'anyOf':[
            {'type':'string','pattern':'^/[^\u0000]*$'},{'type':'null'}]}
with (root/'SCHEMAS004.json').open('x') as f:
    json.dump(schemas,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
text=(root/'CONTRACT006.md').read_text().replace('contract006','contract007',1)
text=text.replace('SCHEMAS003.json defines exact','SCHEMAS004.json defines exact')
text=text.replace('SCHEMAS003.json may be mechanically checked','SCHEMAS004.json may be mechanically checked')
text=text.replace('SCHEMAS003.json is the final proposed schema authority','SCHEMAS004.json is the final proposed schema authority')
text=text.replace('SCHEMAS003.json remains the final proposed schema','SCHEMAS004.json remains the final proposed schema')
text=text.replace('VERIFICATION_PLAN002.md','VERIFICATION_PLAN003.md')
text=text.replace('A pre-rename failure retains its stage at the actual current parent-fd location and reports retained_stage.',
    'A pre-rename failure leaves its created stage untouched and reports retained_stage. staging_workspace names an actual absolute path only when positively verified through its pinned directory identity; if no location can be established it is null. Never guess a stale path or export an ephemeral /proc/self/fd path as a durable output.')
text=text.replace('CONTRACT006.md + SCHEMAS003.json + VERIFICATION_PLAN003.md are the final proposed review authority.',
    'CONTRACT007.md + SCHEMAS004.json + VERIFICATION_PLAN003.md are the final proposed review authority.')
text=text.replace('SCHEMAS003 adds only the distinct failure enum and exact conditional path/state relationships: not_created has both paths null; retained_stage has an absolute existing stage path and null published path;',
    'SCHEMAS004 preserves the prior distinct location-failure enum and exact conditional path/state relationships, with nullable retained stage: not_created has both paths null; retained_stage has a positively validated actual absolute stage path or null when location is unknown, and always null published path;')
text += '''

## Revision007 final nullable-stage and fixture-custody rules

Final review/adoption authority is this complete CONTRACT007.md, SCHEMAS004.json and VERIFICATION_PLAN003.md; earlier drafts remain exact history. R identified the symmetric pre-rename error edge: after an external parent move or inaccessible ancestry, a stage may have been created/left untouched while no actual absolute pathname can be positively validated. Root accepted staging_workspace=null for retained_stage in that case, alongside published_workspace=null. This remains distinct from not_created, which asserts no stage was created. A nonnull stage path requires positive pinned-inode/path verification; do not invent a stale original pathname or expose temporary fd paths. If external mutation has independently removed output, never claim the helper restored or preserved those externally deleted bytes. The helper itself performs no cleanup/delete/overwrite; affected_refs retains requested operands and any last positively established paths, and error phase/cause identifies the actual failed custody step. No general filesystem migration/recovery is promised.

SCHEMAS004 changes only retained_stage's conditional staging path from required absolute to nullable absolute relative to003; successful result/receipt/source/manifest schemas remain unchanged. not_created still has both paths null; any retained_stage has null published path; any post-rename published failure has null stage and a nullable positively established published path. Positively established paths and required source-zero-write checks remain semantic constraints, beyond representation validation. The final future-fixture plan additionally requires unique explicit never-reused --basetemp paths and immediate preservation of any raw fixture DB/artifact tree cited as evidence, avoiding pytest's rotating default roots. No actual fixture/application test was run for this planning bundle.
'''
with (root/'CONTRACT007.md').open('x') as f:f.write(text)
plan=(root/'VERIFICATION_PLAN002.md').read_text()
plan += '''

Final007 fixture custody: every evidence-bearing invocation uses an explicit unique --basetemp path that does not already exist and is never reused, outside pytest's rotating /tmp/pytest-of-chia roots. Keep command/stdout/stderr/XML/source guards and immediately preserve the passed fixture's exact raw configuration/journal/DB/artifact/archive tree before any later pytest invocation. Use only readonly immutable SQLite for any retained closed zero-WAL fixture inspection, without application reconstruction/checkpoint of the original fixture. Map original paths to a NEW backup explicitly, with exact file hashes/sizes/modes and no altered content addresses; do not claim relocated DB resumability. A missing/pruned fixture is a specific evidence limitation, not a passing raw-custody claim. No existing basetemp or prior fixture may be overwritten. A representative future command shape is `/home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest tests/test_scientific_checkpoint_fork.py --basetemp=/tmp/scientific-checkpoint-c006-tests-<new-unique-suffix> -q --junitxml=<new-evidence-dir>/results.xml`; this command was NOT executed here.

Final007 nullable retained-stage case: deterministically make a created stage's parent path unavailable/unresolvable before publication; require retained_stage with staging_workspace null and published_workspace null, no stale-path assertion/cleanup/overwrite. When the moved actual stage path is positively validated, require that exact absolute path instead. Update schema relationship examples so retained_stage/null is accepted while a relative/stale-unvalidated path is never claimed usable. These are future actual filesystem/error.as_record fixtures, distinct from the representation-only checks in this planning bundle.
'''
with (root/'VERIFICATION_PLAN003.md').open('x') as f:f.write(plan)
checker=(root/'check_schema003.py').read_text()
checker=checker.replace('CONTRACT006.md','CONTRACT007.md').replace('SCHEMAS003.json','SCHEMAS004.json')
checker=checker.replace('8d83579830c95e0780ec9f52087d771d2a26cb3fcd4e295eaefc048b1a9da40b',sha('CONTRACT007.md'))
checker=checker.replace('267019ce7be0f56aa3bd4d3d45707885c1ff6f06b48bea42f8ecb22c88644ab4',sha('SCHEMAS004.json'))
checker=checker.replace("positives=[base,retained,durability,location,{**location,'published_workspace':None}]",
    "positives=[base,retained,durability,location,{**location,'published_workspace':None},{**retained,'staging_workspace':None}]")
checker=checker.replace("{**retained,'staging_workspace':None},{**retained,'staging_workspace':'relative'},",
    "{**retained,'staging_workspace':'relative'},")
with (root/'check_schema004.py').open('x') as f:f.write(checker)
print(json.dumps({'status':'final007_planning_revision_written','contract_sha256':sha('CONTRACT007.md'),
    'schemas_sha256':sha('SCHEMAS004.json'),'verification_plan_sha256':sha('VERIFICATION_PLAN003.md')},sort_keys=True))
