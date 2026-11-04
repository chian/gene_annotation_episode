"""Collect unparsed completed native searches without resubmitting them."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3


async def recover_unparsed_searches(store,original_case,known,*,directory):
    from .homology_results import HomologyResults,NativePhmmerInput
    from .local_jobs import LocalJobPolicy
    from .a103_detection import search_receipt
    from .workflow_budget import active_budget
    active_budget()
    original=Path(original_case)/'jobs'
    config=json.loads((original/'configuration.json').read_text())
    with closing(sqlite3.connect((original/'jobs.sqlite').as_uri()+'?mode=ro',uri=True)) as reader:
        reader.row_factory=sqlite3.Row
        orders=[dict(row) for row in reader.execute('SELECT * FROM orders WHERE staged=1 AND submission_requested=1')]
    complete=set()
    exists=store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone()
    if exists:
        for row in store.db.execute('SELECT body FROM homology_result_snapshots'):
            body=json.loads(row['body'])
            if body['native_termination_seen'] and body['parse_inventory']['parser_finished'] and not body['parse_execution']['failure']:
                complete.add((body['query_sequence_sha256'],body['database_sha256']))
    known=set(known)
    recovered=[]
    scope={'subject_refs':store.problem()['subject_refs']}
    adapter=HomologyResults(store,policy=LocalJobPolicy(128*1024**2,32*1024**2,180))
    for order in orders:
        query=store.get(order['query_ref'])
        peptide=store.get_artifact(query['sequence_ref']).decode().strip().upper()
        query_hash=hashlib.sha256(peptide.encode()).hexdigest()
        if (query_hash,config['reference_database']['sha256']) in complete:continue
        if order['query_ref'] not in known:raise ValueError('recovery_query_not_in_explicit_handover')
        job=original/order['job_ref']
        handle_path=job/'native.handle.json'
        handle=json.loads(handle_path.read_text())
        outcome_path=Path(handle['paths']['result'])
        if outcome_path.parent!=job or not outcome_path.is_file():continue
        outcome=json.loads(outcome_path.read_text())
        if outcome['native_returncode']!=0 or outcome['resource_failure'] is not None:continue
        command=handle['command']
        if (command[0]!=config['executable']['path'] or command[-2:]!=['query.faa','references.faa']
                or command[command.index('--cpu')+1]!=str(order['cpu'])):
            raise ValueError('recovery_registered_native_command_conflict')
        capture=Path(directory)/order['job_ref'];capture.mkdir(parents=True)
        for name in ('query.faa','references.faa','native.stdout','hits.tbl','domains.tbl'):
            shutil.copy2(job/name,capture/name)
        if hashlib.sha256((capture/'references.faa').read_bytes()).hexdigest()!=config['reference_database']['sha256']:
            raise ValueError('recovery_reference_database_changed')
        if hashlib.sha256(Path(config['executable']['path']).read_bytes()).hexdigest()!=config['executable']['sha256']:
            raise ValueError('recovery_native_executable_changed')
        provenance={'job_ref':order['job_ref'],'registry_ref':config['registry_ref'],'native_handle':handle,
            'native_parameters':{'command':command,'cpu':order['cpu'],'search_mode':order.get('search_mode','native_defaults')},
            'retained_native_result':{'original_handle_path':str(handle_path),'outcome':outcome,
                'mode':'completed_native_search_reused; fresh_bounded_parse_only'}}
        (capture/'CAPTURE.json').write_text(json.dumps(provenance,indent=2)+'\n')
        inputs=NativePhmmerInput(order['query_ref'],capture/'query.faa',capture/'references.faa',
            capture/'native.stdout',capture/'hits.tbl',config['reference_database']['sha256'],
            config['executable']['sha256'],provenance,capture/'domains.tbl')
        result=await adapter.extract(inputs,scope=scope,offset=0,limit=2048)
        if result['feedback'] is not None or result['result']['next_offset'] is not None:
            raise ValueError('recovery_requires_complete_bounded_result_collection')
        body=result['result']
        refs=set(result['record_refs'])|{order['query_ref'],body['snapshot_ref'],body['native_source_ref'],body['execution_source_ref']}
        known.update(refs)
        search_receipt(store,body['snapshot_ref'],body['native_source_ref'],order['query_ref'],known)
        recovered.append({'query_ref':order['query_ref'],'original_job_ref':order['job_ref'],
            'snapshot_ref':body['snapshot_ref'],'record_refs':sorted(refs),'new_homology_jobs':0,
            'new_steps':['native_result_parsing_and_grading']})
    return sorted(known),recovered
