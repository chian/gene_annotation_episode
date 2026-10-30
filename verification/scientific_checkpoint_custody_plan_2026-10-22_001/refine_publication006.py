"""Additive publication identity/nullable-error contract; no application access."""
from pathlib import Path
import json
import hashlib
root=Path(__file__).resolve().parent
schemas=json.loads((root/'SCHEMAS002.json').read_text())
schemas['$id']='urn:scientific-checkpoint-custody-contract:20261022:003'
failure=schemas['$defs']['failure']
failure['properties']['publication_state']['enum'].append('published_location_unconfirmed')
nullable_path={'anyOf':[{'type':'string','pattern':'^/[^\u0000]*$'},{'type':'null'}]}
failure['properties']['staging_workspace']=nullable_path
failure['properties']['published_workspace']=nullable_path
def conditional(state, properties):
    return {'if':{'properties':{'publication_state':{'const':state}}},'then':{'properties':properties}}
null={'type':'null'}
absolute={'type':'string','pattern':'^/[^\u0000]*$'}
published={'staging_workspace':null,'phase':{'const':'publish'},
    'code':{'const':'publication_failure'},'source_unchanged':{'const':True}}
failure['allOf']=[
    conditional('not_created',{'staging_workspace':null,'published_workspace':null}),
    conditional('retained_stage',{'staging_workspace':absolute,'published_workspace':null}),
    conditional('published_durability_unconfirmed',{**published,'cause':{'const':'io_error'}}),
    conditional('published_location_unconfirmed',{**published,'cause':{'enum':['contract_error','io_error']}}),
]
with (root/'SCHEMAS003.json').open('x') as f:
    json.dump(schemas,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
text=(root/'CONTRACT005.md').read_text().replace('contract005','contract006',1)
text=text.replace('SCHEMAS002.json','SCHEMAS003.json').replace('VERIFICATION_PLAN.md','VERIFICATION_PLAN002.md')
old='After rename, fsync parent, then return the closed result.'
assert text.count(old)==1
text=text.replace(old,'After rename, fsync the pinned parent fd, then verify BOTH that the requested parent pathname still names that same parent device/inode and that the requested destination child entry names the exact published directory device/inode. Only after this final successful identity check return the closed result. Success linearizes at that final identity check; no guarantee is made against later external moves.')
old='If rename succeeded but parent fsync failed, report published_durability_unconfirmed and the actual published path, not a nonexistent old stage; do not return success or remove/overwrite it.'
assert text.count(old)==1
text=text.replace(old,'If rename succeeded but parent fsync failed, report published_durability_unconfirmed and an actual published path only if it is positively recovered/verified through the pinned parent fd, otherwise null; never report a nonexistent old stage or guess the original destination path. If parent fsync succeeded but the final parent/child identity check fails, report published_location_unconfirmed with code publication_failure/phase publish, not success. staging_workspace is null after either successful rename. published_workspace is the actual absolute path only when fd-based recovery plus parent/child inode verification positively establishes that path, otherwise null. Never clean up, overwrite or automatically retry either published state.')
text += '''

## Revision006 publication linearization and exact failure relations

CONTRACT006.md + SCHEMAS003.json + VERIFICATION_PLAN002.md are the final proposed review authority. All prior drafts remain unchanged and unadopted historical records. R independently found the parent-move race after the seed-style precheck: renameat2 through the still-open parent fd can succeed after its original pathname moves, and parent fsync can also succeed, while the requested destination pathname names no published output. Root adopted a post-rename/post-fsync check and distinct truthful location failure. This does not add a runtime/human gate; it specifies correct filesystem output custody before any success claim.

Before rename, retain stage directory device/inode and pinned parent device/inode. After fd-relative no-replace rename succeeds, staging_workspace must be null in a failure (the old stage name is gone). On parent fsync error, code publication_failure/phase publish/publication_state published_durability_unconfirmed/cause io_error, source_unchanged true after prior complete checks. Any published_workspace must be recovered from the pinned fd and verified as the same child inode; unknown is null. Do not claim that a successful rename/fd fsync established the original destination pathname.

After successful parent fsync, validate original requested parent device/inode and destination child device/inode. Any mismatch/unavailable path is code publication_failure/phase publish/publication_state published_location_unconfirmed with cause contract_error or io_error. Recover a current path by the pinned parent fd only if its resolved current parent path and child entry can be verified against the pinned identities; only then published_workspace names it. If no path is provable, published_workspace is null. affected_refs still contains the originally requested destination/parent and any positively established actual path; no invented replacement/reference rebinding. Keep published output/partial bytes and return the typed failure, with no cleanup/overwrite/resume. If both fsync and location verification fail, the actual fsync error remains durability_unconfirmed and the path remains nullable. A failure to store optional failure JSON cannot change the primary failure.

SCHEMAS003 adds only the distinct failure enum and exact conditional path/state relationships: not_created has both paths null; retained_stage has an absolute existing stage path and null published path; either published failure has null stage, nullable validated actual published path, publish phase/publication_failure code and source_unchanged true. Absolute-path strings are representation constraints; actual existence and inode identity still require the described relationship checks. Final success is a statement that, at the final check instant, the requested destination pathname named the published inode and required durability operations completed. It is not a future immobility promise. A later external mutation cannot retroactively change the recorded publication event.
'''
with (root/'CONTRACT006.md').open('x') as f:f.write(text)
plan=(root/'VERIFICATION_PLAN.md').read_text()
plan += '''

Revision006 additional exact cuts: reject ANY constructor schema delta, including a new empty table/index, and ANY extra old-record/artifact materialization; only declared lineage data rows are allowed. Add a deterministic race fixture that pauses after the pre-rename pathname/inode check, renames the original parent and replaces its old pathname, then permits fd-relative rename and parent fsync to succeed. The helper must not return success at the stale original path: it reports published_location_unconfirmed, null stage and only a positively fd/inode-validated actual published path (or null when unresolvable), without deletion/overwrite/automatic retry. Separately inject parent fsync failure after successful rename and require published_durability_unconfirmed even if the path is also unavailable; preserve the primary error. Positive success requires the final requested-parent and requested-child inode checks after parent fsync. Check all four closed failure-state nullable relationships through actual error.as_record, including invalid combinations rejected by SCHEMAS003. No source write/model/native/HTTP operation is needed for these fixture races.
'''
with (root/'VERIFICATION_PLAN002.md').open('x') as f:f.write(plan)
print(json.dumps({'status':'publication006_revision_written',
    'contract_sha256':hashlib.sha256((root/'CONTRACT006.md').read_bytes()).hexdigest(),
    'schemas_sha256':hashlib.sha256((root/'SCHEMAS003.json').read_bytes()).hexdigest(),
    'verification_plan_sha256':hashlib.sha256((root/'VERIFICATION_PLAN002.md').read_bytes()).hexdigest()},sort_keys=True))
