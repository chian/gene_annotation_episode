"""Independent regression of root249's alias defect on immutable joined pin002."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import asyncio
import hashlib
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OWNER=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_binding_244'
PIN=OWNER/'pin_002'
hashes=json.loads((OWNER/'PIN_002.json').read_text())['hashes']

def verify():
    for name,wanted in hashes.items():
        assert hashlib.sha256((PIN/name).read_bytes()).hexdigest()==wanted,name
    return len(hashes)

before=verify()
sys.path[:0]=[str(PIN),str(PIN/'tests')]
from test_literature_endpoint_signal_binding_244 import setup

results=[]
for representation in ('original','text'):
    state=HERE/('fixed_context_alias_state_002_'+representation)
    assert not state.exists(),'Preserve prior fixture state; choose a new suffix.'
    store,ctx,args,binding,source=setup(state)
    try:
        article=args['selection']['source_ref'];metadata=store.get(article)
        alias=source(b'','controlled_public_alias_root249',artifact=metadata['text_ref'],parents=[article])
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,alias))
        excluded=deepcopy(args['selection']['context']['correction_discussion'])
        args['selection']['context']['condition']={**excluded,'source_ref':alias,'representation':representation}
        args['return_context']['condition']=[{k:excluded[k] for k in ('start','end')}]
        outcome=asyncio.run(binding.execute(ctx,'literature.figure.populate',args,'root_fixed_alias_002'))
        assert outcome['status']=='invalid'
        assert outcome['feedback']['code']=='endpoint_context_overlaps_private_correction_result'
        assert outcome['result'] is None and not outcome['record_refs']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_endpoint_signal_operations'").fetchone()
        public=asyncio.run(binding.execute(ctx,'source.read',{'source_ref':alias,
            'representation':representation,'offset':0,'limit':40},'root_public_alias_002'))
        assert public['status']=='completed' and public['result']['text']
        results.append({'representation':representation,'same_artifact':store.get(alias)['artifact_ref']==metadata['text_ref'],
            'projection_status':outcome['status'],'feedback':outcome['feedback']['code'],
            'ordinary_public_source_read':public['status'],'endpoint_operation_table_created':False})
    finally:store.close()
imports=[]
for name,module in sorted(sys.modules.items()):
    if name.startswith(('gene_annotation_episode','method_loop','test_literature')) and getattr(module,'__file__',None):
        path=Path(module.__file__).resolve();assert path.is_relative_to(PIN),str(path)
        imports.append({'module':name,'path':str(path.relative_to(PIN)),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
report={'status':'passed','pin_manifest_sha256':hashlib.sha256((OWNER/'PIN_002.json').read_bytes()).hexdigest(),
    'pinned_files_before':before,'pinned_files_after':verify(),'checks':results,'actual_local_imports':imports,
    'scope':'Controlled selected adapter and typed-context guard; no method_loop/model run or new scientific case.',
    'goal_changed':False,'A105_complete':False}
with (HERE/'ROOT_CONTEXT_ALIAS_REPAIR_002.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'status':'passed','pinned_files':before,'checks':results,'imports':len(imports)}))
