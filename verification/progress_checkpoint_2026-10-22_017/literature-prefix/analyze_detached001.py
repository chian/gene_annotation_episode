#!/usr/bin/env python3
"""Analyze only already detached capture files; no SQLite/application imports."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path

P=Path(__file__).resolve().parent
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(data):return hashlib.sha256(data).hexdigest()
def write(name,value,raw=False):
    data=value if raw else (canonical(value)+'\n').encode()
    with (P/name).open('xb') as f:f.write(data)
    return {'path':name,'bytes':len(data),'sha256':sha(data)}
def stamp(value):return datetime.fromisoformat(value)

d=json.loads((P/'CAPTURE001.json').read_text())
schema=json.loads((P/'MAIN_SCHEMA001.json').read_text())
tables={x['name'] for x in schema}
root=d['root_episode_id']
initial=json.loads((P/'INHERITED_COMMITTED_MANIFEST001.json').read_text())
old={x['reference'] for x in initial['records']}
known={x['record_ref'] for x in d['root_receipts']}
commissions=d['commission_intents']
assert len(commissions)==1
c=commissions[0];s=c['spec'];child=s['child']['episode_id']
identity={'run_id':d['run_id'],'parent_episode_id':c['parent_episode_id'],
    'original_decision_index':c['original_decision_index']}
suffix=sha(canonical(identity).encode())
assert c['handle']=='execution_'+suffix and c['operation_key']=='commission_'+suffix
assert c['commission_sha256']==sha(canonical(s).encode())
assert c['spec_text']['sha256']==c['commission_sha256']
spec=write('C1_ORIGINAL_SPEC001.json',canonical(s).encode(),True)
selection=write('C1_ORIGINAL_SELECTION001.json',canonical(c['selection']).encode(),True)
assert selection['sha256']==c['selection_text']['sha256']
assert s['child']['role']=='literature'
assert s['parent']['episode_id']==root and s['run_id']==d['run_id']
child_row=next(e for e in d['episodes'] if e['episode_id']==child)
assert child_row['request']==s['child']['request'] and child_row['path']==s['child']['path']
original=next(a for a in d['actions'] if a['episode_id']==root and a['decision_index']==0)
assert original['original_selection']==c['selection']
assert original['result_metadata']['pending_handle']==c['handle'] and original['credit'] is None
backend=next(x for x in d['durable_commissions'] if x['handle']==c['handle'])
assert backend['spec']==s and backend['commission_sha256']==c['commission_sha256']

overlaps=[]
for pc in d['model_call_metadata']:
    if pc['episode_id']!=root:continue
    for cc in d['model_call_metadata']:
        if cc['episode_id']!=child:continue
        for ps in (pc['timing'] or {}).get('intervals',[]):
            for cs in (cc['timing'] or {}).get('intervals',[]):
                if not ps.get('ended_at') or not cs.get('ended_at'):continue
                lo=max(stamp(ps['started_at']),stamp(cs['started_at']))
                hi=min(stamp(ps['ended_at']),stamp(cs['ended_at']))
                if lo<hi:
                    overlaps.append({'parent_call_index':pc['call_index'],'child_call_index':cc['call_index'],
                        'intersection_start':lo.isoformat(),'intersection_finish':hi.isoformat(),
                        'parent_owner':ps['owner'],'child_owner':cs['owner']})
assert overlaps
waits=[]
for row in d.get('root_waits',[]):
    request=json.loads(row['request']);outcome=None if row['outcome'] is None else json.loads(row['outcome'])
    waits.append({'original_decision_index':row['original_decision_index'],'wait_id':row['wait_id'],
        'selected_at':row['selected_at'],'condition':request['condition'],
        'request_sha256':row['request_sha256'],'outcome':outcome,
        'estimate_unavailable_reasons':request['estimate_snapshot']['unavailable_reasons']})

frames=[]
for row in d['root_saved_requests']:
    request=json.loads((P/row['descriptor']['path']).read_text())
    frame=request['local_commission_frame']
    context=request['context'];projected=request.get('model_presentation',{}).get('context',{})
    assert 'local_commission_frame' not in context and 'local_commission_frame' not in projected
    frames.append({'call_index':row['call_index'],'request_descriptor':row['descriptor'],
        'version':request['version'],'frame_version':frame['version'],
        'frame_outside_raw_and_saved_model_context':True,
        'population_status':frame['population_status'],'population_count':frame['population_count'],
        'pending_captured_at':frame['pending_captured_at'],'store_read_interval':frame['store_read_interval'],
        'return_scan':frame['return_scan'],'unavailable_reasons':frame['unavailable_reasons'],
        'child_report_count':len(context.get('child_reports') or []),
        'monitoring_information_credit':context.get('monitoring_information_credit'),
        'commissions':[{k:x[k] for k in ('handle','original_decision_index','accounting_status',
            'return_presence','return_metadata','admission_evidence','pending_status_fact')} for x in frame['commissions']]})
assert all(x['child_report_count']==0 for x in frames)
assert not d['durable_returns'] and not d['admissions'] and not d['report_attempts']

root_observations=[]
for row in d['observations']:
    if row['episode_id']!=root:continue
    o=row['observation']
    root_observations.append({'unit_index':row['unit_index'],'unit_ref':o['unit_ref'],
        'decision_index':o['decision_index'],'label':o['label'],
        'cumulative_credit':o['step']['credit'],'marginal_credit':o['step']['marginal_credit'],
        'stop':o['step']['stop'],'observation_text':row['observation_text']})
assert [o['decision_index'] for o in root_observations]==[1,2]
assert all(o['marginal_credit']==0 and o['cumulative_credit']==12 for o in root_observations)
new=[{k:x[k] for k in ('id','record_type','data_text')}|{'root_receipted_at_cut':x['id'] in known}
    for x in d['typed_committed_metadata'] if x['id'] not in old]
result={'version':'configured_literature_commission_prefix_analysis_v1','status':'prefix_verified_no_return',
    'run_id':d['run_id'],'root_episode_id':root,'child_episode_id':child,
    'capture_sha256':sha((P/'CAPTURE001.json').read_bytes()),
    'read_cut':{k:d[k] for k in ('main_read_started_at_utc','main_read_finished_at_utc',
        'durable_read_started_at_utc','durable_read_finished_at_utc','connection_explicitly_closed')},
    'runtime_pin':d['source_pin_authority'],'runtime_files':d['runtime_file_count'],
    'source_members_unchanged':d['source_members_unchanged'],
    'C1':{'parent_original_decision_index':0,'selected_at':c['selected_at'],'role':'literature',
        'handle':c['handle'],'operation_key':c['operation_key'],'commission_sha256':c['commission_sha256'],
        'original_spec':spec,'original_selection':selection,'scope':s['child']['scope'],
        'goal':s['child']['request']['goal'],'original_assignment':s['child']['request']['message'],
        'original_report_contract':s['child']['request']['report_contract'],
        'input_versions':s['input_versions'],'resource_selection':s['resource_selection'],
        'expectation_snapshot_refs':s['expectation_snapshot_refs'],
        'selection_extra_constructed_map_handle_present':any('map' in k or 'handle' in k for k in c['selection']),
        'identity_and_original_journal_backend_relationships_verified':True},
    'persisted_worker':{k:backend[k] for k in ('lifecycle_state','execution_identity','return_id','acknowledgment','failure')},
    'counts':{'episodes':len(d['episodes']),'actions':len(d['actions']),'observations':len(d['observations']),
        'model_calls':len(d['model_call_metadata']),'by_episode':{e:{
            'actions':sum(a['episode_id']==e for a in d['actions']),
            'observations':sum(a['episode_id']==e for a in d['observations']),
            'model_calls':sum(a['episode_id']==e for a in d['model_call_metadata'])} for e in (root,child)}},
    'overlapping_completed_model_intervals':overlaps,
    'selected_action_metadata':[{k:a[k] for k in ('episode_id','decision_index','credit',
        'selection_metadata','result_metadata','selection_text','result_text','timing')} for a in d['actions']],
    'observation_identity_metadata':[{k:o[k] for k in ('episode_id','unit_index','metadata','observation_text')}
        for o in d['observations']],
    'root_completed_observations':root_observations,'saved_root_requests':frames,
    'saved_root_waits':waits,
    'saved_completed_action_contexts':[{'decision_index':r['decision_index'],'version':r['data']['version'],
        'text':r['text'],'selected_frame_version':r['data']['local_commission_frame_at_selection']['version'],
        'after_frame_version':r['data']['local_commission_frame_after_action']['version']}
        for r in d['root_estimation_contexts']],
    'C3':{'durable_returns_table_present':True,'matching_return_rows':0},
    'C4':{'admissions_table_present':'runtime_return_admissions' in tables,'recorded_admissions':False,
        'report_attempt_table_present':'runtime_report_attempts' in tables,'report_attempt_rows':0},
    'new_typed_commit_identity_metadata_vs_checkpoint':new,
    'checkpoint_baseline_committed_refs':len(old),
    'meaning_limits':[
        'Recorded worker identity and running spans are persisted facts; no current liveness check was made.',
        'Separate main/backend read windows are not an atomic cross-database snapshot.',
        'Original selections and goals are instructions, not source evidence or scientific conclusions.',
        'Child private model requests/responses, reasoning bodies and unreturned forms were not exported.',
        'Novel typed record identities/hashes are not a received parent contribution; two novel source IDs are preparation lineage.',
        'No C3 return, C4 admission, root received child form or later parent scientific integration was observed at this cut.',
        'No full-source reading, scientific validity, annotation-support gain or completion is inferred from tool names/counts.',
        'No continuation override, scheduling, new runtime capture, application call or subsequent active-DB read was performed.'
    ]}
desc=write('ANALYSIS001.json',result)
print(canonical({'analysis':desc,'overlap_witnesses':len(overlaps),'status':result['status'],
    'C1_role':'literature','C3_rows':0,'C4_table_present':result['C4']['admissions_table_present']}))
