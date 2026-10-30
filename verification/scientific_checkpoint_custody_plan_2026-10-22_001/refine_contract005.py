"""Additive strict-constructor-delta correction; planning files only."""
from pathlib import Path
import json
import hashlib
root=Path(__file__).resolve().parent
text=(root/'CONTRACT004.md').read_text().replace('contract004','contract005',1)
old='New destination-only source/artifact rows are the sole permitted data delta; new empty tables/indexes installed by the unchanged actual Store constructor must be recorded, with no altered old schema objects/rows. Any other constructor-induced delta fails and retains the private stage.'
assert text.count(old)==1
text=text.replace(old,'New destination-only source/artifact rows are the sole permitted data delta. Reject ANY Store-constructor schema delta, including newly created empty tables/indexes or changed existing SQL/schema metadata; no constructor migration is supported. Verify exact schema equality immediately before and after the actual destination Store constructor, before adding lineage. Reject any new/changed old input/record/artifact/material/runtime row caused by constructor, reference resolution or validation. All old rows and schema objects remain identical; failure retains the private stage. The source and current unchanged Store/material/packing/library constructors already install the same required schema, so an unexpected delta is an out-of-scope source/implementation mismatch rather than a permitted upgrade.')
text += '''

## Revision005 strict constructor and read-only validation boundary

This complete CONTRACT005.md supersedes earlier contract drafts for adoption; keep all earlier bytes, hashes and review findings. R independently found that004 permitted constructor-created empty schema objects but its closed receipt had no delta slot. Root chose the narrower fixed-source rule: reject every schema delta, with no new field or generalized migration. SCHEMAS002.json remains byte-identical. The accepted data delta is only the exact two declared lineage source rows and actual declared payload/metadata artifact rows (reuse is permitted only for already identical rows); no other data delta is permitted.

Actual Store.get first reads inputs/records directly, then library_targets.resolve (metadata-only SELECT/JSON construction), material_members and artifact rows. Actual materials_packing.component_info/component_chunks reads existing member metadata/spans/chunk artifacts; materials.artifact_path verifies existing registered bytes. None of those functions materializes a member or inserts an old record/artifact. Never call packing.materialize, materials.member_reference or any parser/importer merely to validate custody. Existing requested input/record IDs resolve without entering a virtual read-subject path, and optional caller extras must use only these same pure lookup/forward-reference paths. All unexpected old-component materialization or any extra artifact/record/data/schema delta is a failure, not an implicit contribution or repair.

CONSTRUCTOR_READPATHS.json will identify the exact original/current state/material/packing/library constructor source hashes and complete methods read. The original/current equality is a source-level observation, not an actual source-database schema assertion; the future component must still compare copied schema before/after actual construction and reject a mismatch. Future custody code is NEW006 after separate adoption of this contract, never an edit to frozen005. No scientific SQLite was opened by this refinement.
'''
with (root/'CONTRACT005.md').open('x') as f:f.write(text)
print(json.dumps({'status':'contract005_written','sha256':hashlib.sha256((root/'CONTRACT005.md').read_bytes()).hexdigest(),
    'schema_sha256':hashlib.sha256((root/'SCHEMAS002.json').read_bytes()).hexdigest()},sort_keys=True))
