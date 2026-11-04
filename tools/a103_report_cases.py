"""Audit real-case jobs across explicit retained-data handovers for reporting."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget


def case_summary(result_path):
    result=json.loads(result_path.read_text())
    chain=[result_path.parent.resolve()]
    handover=result.get('retained_input_provenance')
    while handover is not None:
        directory=Path(handover['source_case']).resolve()
        if directory in chain:raise ValueError('retained_case_chain_cycle')
        chain.append(directory)
        handover=handover.get('prior_handover')
    categories=Counter()
    native=[]
    failures=[]
    unexecuted=[]
    intervals=defaultdict(list)
    for directory in chain:
        for path in sorted(directory.rglob('*handle*.json')):
            body=json.loads(path.read_text())
            if body.get('version')!='durable_systemd_native_job_v2':continue
            receipt=Path(body['paths']['result'])
            outcome=json.loads(receipt.read_text()) if receipt.exists() else None
            if (outcome is None and body['stage'] in {'prepared','submitting'}
                    and not Path(body['paths']['release']).exists()):
                # The protected wrapper cannot start the native command before
                # this token exists. A workflow can end during preparation or
                # while the wrapper waits for its verified cgroup release.
                unexecuted.append({'handle':str(path),'stage':body['stage'],
                    'native_release_present':False})
                continue
            if outcome is None or outcome['native_returncode']!=0 or outcome['resource_failure'] is not None:
                failures.append({'handle':str(path),'outcome':outcome})
                continue
            command=body['command']
            if 'gene_annotation_episode.a103_native_worker' in command:
                category='context.'+json.loads(Path(command[-1]).read_text())['operation']
            elif 'gene_annotation_episode.phmmer_result_worker' in command:category='homology.parse'
            elif Path(command[0]).name=='phmmer':category='homology.search'
            else:category='other'
            categories[category]+=1
            start,end=outcome['started'],outcome['ended']
            intervals[start['boot_id']].append((start['monotonic_ns'],end['monotonic_ns'],str(path)))
            native.append({'handle':str(path),'case_directory':str(directory),'category':category,
                'started':start,'ended':end,
                'wall_seconds':(end['monotonic_ns']-start['monotonic_ns'])/1e9,
                'cpu_threads':body['metadata']['cpu_threads'],'policy':body['metadata']['policy']})
    for events in intervals.values():
        ordered=sorted(events)
        if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):
            raise ValueError('retained_case_native_jobs_overlap')
    if any(job['cpu_threads']!=1 for job in native):raise ValueError('nonserial_native_cpu_request')
    if any(job['policy']['memory_bytes']>128*1024**2 or job['policy']['scratch_bytes']>32*1024**2
            or job['policy']['wall_seconds'] is None or job['policy']['wall_seconds']>180 for job in native):
        raise ValueError('real_case_native_budget_exceeded')
    workflows=[]
    for directory in chain:
        path=directory.parent/'workflow-result.json'
        if not path.exists():continue
        value=json.loads(path.read_text())
        workflows.append({'case_directory':str(directory),**{key:value[key] for key in
            ('returncode','elapsed_seconds','memory_peak_bytes','observed_scratch_bytes','memory_events','limits')}})
    audit=result['audit']
    if not audit['latest_owner_equals_parent'] or not audit['all_credit_has_native_context_measurement']:
        raise ValueError('real_case_credit_audit_incomplete')
    return {'case':result['case'],'result_path':str(result_path.resolve()),
        'decision_mode':result['decision_mode'],'axis_components':result['credit']['axis_components'],
        'root_credit':result['credit']['credit'],'owner_parent_agree':True,'native_credit_verified':True,
        'case_directories':list(map(str,chain)),'fresh_native_jobs_in_final_continuation':audit['total_native_jobs'],
        'completed_native_jobs_across_handover':len(native),'jobs_by_category_across_handover':dict(categories),
        'failed_native_jobs_across_handover':failures,'native_jobs':native,
        'unexecuted_preparations_across_handover':unexecuted,
        'native_wall_seconds_across_handover':sum(job['wall_seconds'] for job in native),
        'one_native_job_at_a_time_across_handover':True,'workflows':workflows,
        'final_workflow':workflows[0] if workflows else None}


def main():
    directory=Path(active_budget()['run_directory'])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',nargs='+',type=Path)
    args=parser.parse_args()
    results=[case_summary(path) for path in args.results]
    intervals=defaultdict(list)
    for result in results:
        for job in result['native_jobs']:
            intervals[job['started']['boot_id']].append((job['started']['monotonic_ns'],
                job['ended']['monotonic_ns'],job['handle']))
    for events in intervals.values():
        ordered=sorted(events)
        if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):
            raise ValueError('native_jobs_overlap_between_real_cases')
    (directory/'REAL_CASE_SUMMARY.json').write_text(json.dumps(results,indent=2)+'\n')
    for result in results:
        print(json.dumps({key:result[key] for key in ('case','axis_components','root_credit',
            'completed_native_jobs_across_handover','jobs_by_category_across_handover',
            'native_wall_seconds_across_handover','owner_parent_agree')}),flush=True)


if __name__=='__main__':main()
