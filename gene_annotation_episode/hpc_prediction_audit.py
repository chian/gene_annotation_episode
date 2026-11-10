"""Read-only evidence checks for the real prediction/execution sister test."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from .hpc_prediction import quantile
from .hpc_resource_prediction import forecast_metric, measured_value
from .execution_memory import ExecutionMemory


def audit(directory):
    directory = Path(directory).resolve()
    ledgers = list((directory/'episode'/'hpc').glob('*/hpc.sqlite'))
    if len(ledgers) != 1:
        return {'passed': False, 'failure': 'one_original_parent_ledger_required'}
    with sqlite3.connect(ledgers[0].as_uri()+'?mode=ro', uri=True) as db:
        records = [(identity, kind, json.loads(body)) for identity, kind, body in
                   db.execute('SELECT id,kind,body FROM evidence ORDER BY recorded,id')]
        credits = [dict(zip(('slot', 'kind', 'credit', 'evidence_id'), row))
                   for row in db.execute('SELECT slot,kind,value,evidence_id FROM credits')]
    def values(kind):
        return [body for _, name, body in records if name == kind]
    by_id = {identity: body for identity, _, body in records}
    with sqlite3.connect((directory/'state'/'state.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
        episodes = {identity: json.loads(path) for identity, path in
                    db.execute('SELECT episode_id,path FROM runtime_episodes')}
        submissions = []
        for tool, result in db.execute("SELECT json_extract(action,'$.tool'),result FROM runtime_actions WHERE "
                "json_extract(action,'$.tool') IN ('exec_command','practical.job.start') AND result IS NOT NULL"):
            outcome = (json.loads(result).get('result') or {}).get('outcome', {})
            if tool == 'exec_command':
                for event in (outcome.get('native_outcome') or {}).get('scheduler_events', []):
                    native = event.get('native_job')
                    if event.get('command') == 'qsub' and event.get('returncode') == 0 and native:
                        submissions.append({'attempt_id': native['submission_event'],
                            'job_id': native['job_id']})
            else:
                # Historical immutable runs used this tool name. It is read
                # here only; the current execution catalog does not expose it.
                native = outcome.get('native_outcome') or {}
                if native.get('attempt_id'):
                    submissions.append({'attempt_id': native['attempt_id'], 'job_id': native.get('pbs_job_id')})
    predictors = {key: path for key, path in episodes.items() if path[-1][0] == 'hpc_prediction'}
    executors = {key: path for key, path in episodes.items() if path[-1][0] == 'hpc_execution'}
    comparisons = [row for row in values('comparison') if row['episode_id'] in predictors]
    models = {row['model_ref'] for row in values('model_choice') if row.get('episode_id') in predictors}
    candidates = values('commission')[0]['candidates']+values('candidate')
    alternatives = {(row['nodes'], row['features'].get('worker_threads')) for row in candidates}
    plans = values('plan')
    plans_by_id = {row['plan_id']: row for row in plans}
    results = values('result')
    accepted = [row for row in credits if row['kind'] == 'actual']
    validations = [by_id[row['evidence_id']] for row in credits if row['kind'] == 'validation']
    slots = {row['id']: row for row in values('commission')[0]['credit']['validation_slots']}
    scored_metrics = {slots[row['slot']]['metric'] for row in validations
                      if row.get('prediction_episode_id') in predictors}
    monitor_states = [row['conditional_prediction']['telemetry']['state'] for row in values('monitor')]
    measurements = {row['body']['plan_id']: row['body'] for row in values('export_measurement')}
    jobs = {row['job_id'] for row in values('handoff')}
    scheduler = directory/'scheduled-resume.json'
    dispatched = (scheduler.exists() and
        (Path(json.loads(scheduler.read_text())['controller_run_directory'])/'workflow-budget.json').exists())
    shared_jobs = set()
    memory = ExecutionMemory.configured()
    if memory.path.exists():
        with sqlite3.connect(memory.path.as_uri()+'?mode=ro', uri=True) as db:
            for (body,) in db.execute('SELECT body FROM execution_measurements'):
                observation = json.loads(body)['observation']
                if {'cpu_seconds', 'memory_bytes'} <= set(observation['metrics']):
                    shared_jobs.update(jobs.intersection(observation['provenance']))
    forecasts = []
    for plan in plans:
        measured = measurements.get(plan['plan_id'])
        if not measured:
            continue
        for metric, item in measured['metrics'].items():
            predicted = forecast_metric(plan['original_prediction'], metric)
            if predicted is None:
                continue
            actual = measured_value(metric, item)
            lo, median, hi = (predicted['elapsed']+quantile(predicted, q) for q in (.1, .5, .9))
            forecasts.append({'plan_id': plan['plan_id'], 'metric': metric, 'actual': actual,
                'unit': item.get('unit', 'seconds'), 'p10': lo, 'p50': median, 'p90': hi,
                'inside_p10_p90': lo <= actual <= hi})
    checks = {
        'prediction_and_execution_are_sisters': any(p[:-1] == e[:-1]
            for p in predictors.values() for e in executors.values()),
        'predictor_fitted_real_history': bool(models) and all(by_id[ref]['training_ids'] for ref in models),
        'multiple_resource_alternatives_compared': len(alternatives) >= 2 and any(
            len(row['comparisons']) >= 2 for row in comparisons),
        'resource_predictions_present': bool(comparisons) and all(
            {'cpu_seconds', 'memory_bytes'} <= set(row['resource_estimates']['demand'])
            for comparison in comparisons for row in comparison['comparisons']),
        'execution_used_sister_model': bool(plans) and all(plan['model_ref'] in models for plan in plans),
        'selected_model_learned_resource_demand': bool(plans) and all(
            by_id[plan['model_ref']]['metrics'][metric]['observations'] > 0
            for plan in plans for metric in ('cpu_seconds', 'memory_bytes')),
        'queue_congestion_is_a_model_input': bool(plans) and all(
            {'queued_jobs', 'queued_node_hours'} <= {field['name'] for field in
                by_id[plan['model_ref']]['specification']['features']} for plan in plans),
        'pending_job_forecast_updated': any(state in ('queued', 'running') for state in monitor_states),
        'calendar_monitor_woke': bool(values('monitor_wake')) and dispatched,
        'one_original_submission': len(submissions) == 1 and {row['job_id'] for row in submissions} == jobs,
        'original_result_accepted': bool(accepted),
        'executed_work_matches_prediction_features': bool(results) and all(
            all(row['document'].get(field) == plans_by_id[row['plan_id']]['original_prediction']['features'].get(field)
                and row['document'].get(field) is not None
                for field in ('iterations', 'chains', 'worker_threads', 'total_iterations'))
            and row['document'].get('pbs_job_id') == row['job_id'] for row in results),
        'resource_predictions_scored_to_predictor': {'cpu_seconds', 'memory_bytes'} <= scored_metrics,
        'measured_resources_exported': bool(jobs) and jobs <= shared_jobs and bool(measurements) and all(
            {'cpu_seconds', 'memory_bytes'} <= set(row['metrics']) for row in measurements.values()),
    }
    return {'passed': all(checks.values()), 'checks': checks,
        'pbs_jobs': [row['job_id'] for row in values('handoff')], 'monitor_states': monitor_states,
        'submission_attempts': submissions,
        'prediction_episode_ids': sorted(predictors), 'execution_episode_ids': sorted(executors),
        'forecast_vs_actual': forecasts, 'credits': credits,
        'accuracy_note': 'Passing verifies actual wiring, custody and scoring. Interval coverage and signed '
                         'prediction credit are reported separately; one job does not establish calibration.'}
