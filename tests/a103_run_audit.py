"""Read-only diagnostics for real A103 runs; never supplies scientific evidence."""
from __future__ import annotations

import json
import math
from pathlib import Path
from collections import Counter,defaultdict

from gene_annotation_episode.a103_credit import A103ContextCredit
from gene_annotation_episode.a103_publication import received_measurement


def audit(case,root_id,root_credit):
    store=case.store
    scorer=A103ContextCredit()
    owners=[]
    for row in store.db.execute('SELECT episode_id,path,request FROM runtime_episodes WHERE run_id=? ORDER BY rowid',
            (case.run_id,)):
        request=json.loads(row['request'])
        assignment=request.get('message',{}).get('episode_assignment',{})
        if assignment.get('selection',{}).get('evidence_axis',{}).get('option_id')!='A103':
            continue
        known=set(case.flow.receipts.known(row['episode_id']))
        value=scorer(store,request['message']['scope'],known_record_refs=known)['credit']
        owners.append({'episode_id':row['episode_id'],'path':json.loads(row['path']),'credit':value})
    parent_known=set(case.flow.receipts.known(root_id))
    coverage_gaps=case.context_gaps(parent_known)
    available_steps=case.native_context_steps(parent_known)
    if not case.smoke:
        assert not coverage_gaps,('required_context_coverage_incomplete',coverage_gaps)
        assert not available_steps,('available_native_context_work_unfinished',available_steps)
    blocked_results=store.db.execute('SELECT a.failure FROM runtime_report_attempts a '
        'JOIN runtime_episodes e ON e.run_id=a.run_id AND e.episode_id=a.child_episode_id '
        "WHERE a.run_id=? AND json_extract(e.path,'$[#-1][0]')='results' AND a.failure IS NOT NULL "
        'AND a.decision_index=(SELECT MAX(b.decision_index) FROM runtime_report_attempts b '
        'WHERE b.run_id=a.run_id AND b.delivery_ref=a.delivery_ref)',(case.run_id,)).fetchall()
    assert not blocked_results,('native_results_not_delivered',[json.loads(row[0]) for row in blocked_results])
    parent=scorer(store,case.scope,known_record_refs=parent_known)
    contributions=scorer.read_details(store,case.scope,known_record_refs=parent_known,details_limit=1000,details_offset=0)
    for item in contributions['source_contributions']:
        measured=received_measurement(store,item['measurement_ref'])
        assert measured is not None and (item['value']==0 or measured['grade']['raw_value'] is not None),item
    direct_owners=[r for r in owners if len(r['path'])==2]
    latest=direct_owners[-1] if direct_owners else None
    assert latest is not None,'The run must execute an A103 scientific owner.'
    assert math.isclose(latest['credit'],parent['credit'],abs_tol=1e-12),(latest,parent['credit'])
    assert math.isclose(parent['credit'],root_credit['axis_components']['A103'],abs_tol=1e-12)
    handles=[]
    for path in sorted(case.directory.rglob('*handle*.json')):
        body=json.loads(path.read_text())
        if body.get('version')!='durable_systemd_native_job_v2':continue
        receipt=Path(body['paths']['result'])
        native=json.loads(receipt.read_text()) if receipt.exists() else None
        assert native is not None and native['native_returncode']==0,(str(path),native)
        start,end=native['started'],native['ended']
        handles.append({'handle':str(path),'command':body['command'],'stage':body['stage'],
            'policy':body['metadata']['policy'],'cpu_threads':body['metadata']['cpu_threads'],
            'started_monotonic_ns':start['monotonic_ns'],'ended_monotonic_ns':end['monotonic_ns'],
            'wall_seconds':(end['monotonic_ns']-start['monotonic_ns'])/1e9,
            'observed_scratch_bytes':native['observed_scratch_bytes'],
            'resource_failure':native['resource_failure']})
    chronological=sorted(handles,key=lambda r:r['started_monotonic_ns'])
    assert all(a['ended_monotonic_ns']<=b['started_monotonic_ns'] for a,b in zip(chronological,chronological[1:])), 'Native jobs overlapped.'
    categories=Counter()
    for row in handles:
        command=row['command']
        if 'gene_annotation_episode.a103_native_worker' in command:
            category='context.'+json.loads(Path(command[-1]).read_text())['operation']
        elif 'gene_annotation_episode.phmmer_result_worker' in command:category='homology.parse'
        elif Path(command[0]).name=='phmmer':category='homology.search'
        else:category='other'
        categories[category]+=1
    if case.wiring_smoke:
        # The real two-locus control needs one anchor-family and one EF-P
        # search. Both native returns must travel through their typed child
        # reports; a reverse EF-P search would duplicate an existing map.
        assert categories['homology.search']==2,('redundant_or_missing_query',dict(categories))
        assert categories['homology.parse']==2,('native_query_not_parsed',dict(categories))
        assert parent['credit']>0,'The received maps must qualify the actual measured context.'
    trajectories=defaultdict(list)
    for receipt,raw in store.db.execute('SELECT r.receipt_index,a.body FROM runtime_record_receipts r '
            'JOIN a103_attachments a ON a.source_ref=r.record_ref WHERE r.run_id=? AND r.episode_id=? '
            'ORDER BY r.receipt_index',(case.run_id,root_id)):
        body=json.loads(raw)
        if body.get('score') is None:continue
        value={'score':body['score'],'bounds':body.get('bounds'),'missing':body['missing']}
        history=trajectories[body['measurement_ref']]
        if not history or value!={k:v for k,v in history[-1].items() if k!='receipt_index'}:
            history.append({'receipt_index':receipt,**value})
    return {'owners':owners,'receiving_parent_A103':parent['credit'],
        'required_context_coverage_complete':not coverage_gaps,
        'available_native_context_work_complete':not available_steps,
        'latest_owner_equals_parent':True,'all_credit_has_native_context_measurement':True,
        'qualified_context_contributions':contributions['source_contribution_count'],
        'native_jobs':handles,'jobs_by_category':dict(categories),'total_native_jobs':len(handles),'one_native_job_at_a_time':True,
        'attribution_trajectories_on_retained_measurements':dict(trajectories),
        'total_native_wall_seconds':sum(r['wall_seconds'] for r in handles),
        'peak_observed_job_scratch_bytes':max((r['observed_scratch_bytes'] for r in handles),default=0)}
