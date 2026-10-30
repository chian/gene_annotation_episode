"""Controlled engineering probe of endpoint return-context artifact aliases.

Only the already reviewed238 fixture is used. No actual provider payload or
new scientific paper interpretation participates in this check.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_literature_endpoint_signal_binding_244 import setup,selected

state=HERE/'context_alias_state_001'
assert not state.exists(),'Preserve the original controlled state; choose a new suffix.'
store,ctx,args,binding,source=setup(state)
try:
    article=args['selection']['source_ref']
    original=store.get(article)
    alias=source(b'', 'controlled_public_text_alias_root249',
        artifact=original['text_ref'],parents=[article])
    ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,alias))
    excluded=deepcopy(args['selection']['context']['correction_discussion'])
    args['selection']['context']['condition']={**excluded,'source_ref':alias}
    args['return_context']['condition']=[{k:excluded[k] for k in ('start','end')}]
    current,outcome,rows=selected(store,ctx,args,binding)
    fragments=rows[0]['source_context']['condition']['fragments']
    assert fragments and fragments[0]['text']==excluded['quote']
    report={'status':'defect_reproduced','fixture':'explicitly controlled reviewed source fixture; no model call',
        'original_source_ref':article,'alias_source_ref':alias,
        'both_text_artifact_refs_equal':store.get(alias)['text_ref']==original['text_ref'],
        'selected_status':outcome['status'],
        'normal_validated_typed_rows':[r['component'] for r in rows],
        'returned_excluded_condition_text':fragments[0]['text'],
        'expected':'Known excluded correction-discussion bytes must not re-enter typed return context through an artifact alias.',
        'source_read_permission':'No public original-source reading permission is changed by this probe.',
        'scope':'Source/return projection guard only; no new scientific acceptance or controller rule.',
        'current_storage_sha256':hashlib.sha256((ROOT/'gene_annotation_episode/literature_endpoint_signal_storage.py').read_bytes()).hexdigest()}
    with (HERE/'ROOT_CONTEXT_ALIAS_PROBE_001.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','both_text_artifact_refs_equal','selected_status','normal_validated_typed_rows')}))
finally:store.close()
