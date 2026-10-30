"""Bounded operational evidence: original handle, format metadata and feedback.

No provider/model history, paper content, scientific operands, runtime mutation,
restart, cancellation, cost change, or source reacquisition is performed.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
OUT=Path(__file__).resolve().parent
launch=json.loads((BASE/'contract_profile_model_parent_review_062/LAUNCH_RECEIPT_007.json').read_text())
run=Path(launch['directory']);pin=Path(launch['pin']);state=run/'state'
stat=Path('/proc')/str(launch['pid'])/'stat'
fields=stat.read_text().rsplit(')',1)[1].split() if stat.exists() else None
process=dict(pid=launch['pid'],handle_present=fields is not None,
             original_start_match=bool(fields and fields[19]==launch['start_ticks']),
             state=fields[0] if fields else None,terminal_result_present=(run/'RESULT.json').is_file())
sources={};exceptions={};technical_details={}
with sqlite3.connect((state/'state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
    db.execute('pragma query_only=on');db.execute('begin')
    for action,result in db.execute("select action,result from runtime_actions where json_extract(result,'$.feedback.code')='xlsx_source_or_selection_invalid'"):
        action,result=json.loads(action),json.loads(result)
        ref=action['arguments']['source_ref']
        sources[ref]=sources.get(ref,0)+1
        feedback=result['feedback'];kind=feedback.get('exception_type')
        exceptions[kind]=exceptions.get(kind,0)+1
        detail=feedback.get('detail')
        # Retain only the known format diagnostic, never an arbitrary worker
        # message that could contain source text or private paths.
        detail=detail if detail in ('File is not a zip file',) else 'other technical detail not inspected'
        technical_details[detail]=technical_details.get(detail,0)+1
    artifacts=[]
    for ref,count in sources.items():
        data=json.loads(db.execute('select data from records where id=?',(ref,)).fetchone()[0])
        sha,media,size=db.execute('select sha256,media_type,size from artifacts where id=?',(data['artifact_ref'],)).fetchone()
        with (state/'artifacts'/sha[:2]/sha).open('rb') as stream:prefix=stream.read(8)
        signature=('zip_signature' if prefix.startswith(b'PK') else 'pdf_signature' if prefix.startswith(b'%PDF')
                   else 'ole_compound_signature' if prefix.startswith(bytes.fromhex('d0cf11e0a1b11ae1')) else 'other')
        artifacts.append(dict(source_ref=ref,attempts=count,artifact_ref=data['artifact_ref'],
                              stored_media_type=media,size=size,signature_kind=signature))
    readonly=dict(query_only=db.execute('pragma query_only').fetchone()[0],total_changes=db.total_changes)
assert readonly==dict(query_only=1,total_changes=0)
script="""
import json,sys
from pathlib import Path
import gene_annotation_episode.literature_experimental_prompt as m
pin=Path(sys.argv[1]).resolve()
feedback={'category':'acquisition','code':'xlsx_source_or_selection_invalid','exception_type':'BadZipFile','detail':'File is not a zip file','phase':'native_execution','operation':'sheets','selection':{}}
prompt=m._steering({'last_local_outcome':{'status':'failed','feedback':feedback}},[])
checks={s:s in prompt for s in ('xlsx_source_or_selection_invalid','BadZipFile','File is not a zip file')}
imports={n:str(Path(v.__file__).resolve()) for n,v in sys.modules.items() if n.startswith('gene_annotation_episode') and getattr(v,'__file__',None)}
assert all(checks.values()) and all(Path(p).is_relative_to(pin) for p in imports.values())
print(json.dumps({'module':str(Path(m.__file__).resolve()),'diagnostic_fields_rendered':checks,'project_imports_inside_frozen_pin':len(imports)}))
"""
result=subprocess.run([str(ROOT/'.venv/bin/python'),'-c',script,str(pin)],cwd='/tmp',text=True,capture_output=True,
                      env=dict(os.environ,PYTHONPATH=str(pin),PYTHONDONTWRITEBYTECODE='1'))
assert result.returncode==0,result.stderr
rendering=json.loads(result.stdout)
receipt=dict(utc=datetime.now(timezone.utc).isoformat(),process=process,readonly=readonly,
    failures=sum(sources.values()),distinct_selected_sources=len(sources),exception_types=exceptions,
    technical_details=technical_details,source_format_metadata=artifacts,
    isolated_frozen_formatter_check=rendering,
    conclusion='Observed XLSX failures involve non-ZIP HTML/JSON sources. The frozen deterministic formatter preserves code/type/detail; this does not prove every actual model prompt contained that state or establish why the model repeated the operation.',
    intervention=False,scientific_completion_claimed=False)
with (OUT/'OBSERVATION.json').open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
print(json.dumps({k:receipt[k] for k in ('utc','process','failures','distinct_selected_sources','exception_types','readonly')}))
