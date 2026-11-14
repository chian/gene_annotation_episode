"""HPC parent and prediction specializations of the ordinary Episode loop.

Launch remains the existing launch -> launch_hpc iteration. Known monitoring
and result parsing are single tools of the HPC parent. This binding never calls
a model, polls in a loop, or decides to commission children itself.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import asyncio
import shlex
import subprocess
import time

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.hpc_campaign import (YIELD_ROLES, accepts, bind_progress, build_plan,
    incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.root.library.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.root.library import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.root.library import hpc_queue
from gene_annotation_episode.episodic_workflow.root.library.hpc_resource_prediction import forecast_metric, pbs_resource_metrics, physical_attempt_key


TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


def catalog(self, context):
    shared = [
        ('hpc.read', 'Read retained HPC evidence by its exact identity.', obj({'reference': TEXT})),
        ('hpc.compare', 'Compare all approved portfolios; no work is selected or launched.',
            obj({'model_ref': TEXT, 'queue_ref': TEXT}))]
    if self.memory:
        shared.append(('hpc.history.refresh', 'Read age-weighted shared timing history once. '
            'No remote discovery, polling credit, or new scientific work.', obj({})))
    shared += [
            ('hpc.discovery.run', 'Run one lightweight remote inspection or documentation retrieval through the established SSH transport. No job submission, installation or scientific computation; those belong to Launch and the allocation.',
                obj({'command': TEXT})),
            ('hpc.candidate.propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: relative path, text: exact contents}], and preparation instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate identities are immutable.',
                obj({'candidate_json': TEXT})),
            ('hpc.queue.observe', 'Acquire PBS queue and ALCF score/status once and transform them.', obj({}))]
    entries = shared+[
        ('hpc.plan', 'Freeze one useful portfolio and its forecasts; return a concrete launch assignment.',
            obj({'candidate_id': TEXT, 'model_ref': TEXT, 'queue_ref': TEXT})),
        ('hpc.handoff', 'Bind the original received PBS handoff to the exact frozen portfolio.',
            obj({'plan_ref': TEXT, 'handoff_ref': TEXT})),
        ('hpc.monitor', 'Observe the original job and progress once; update and freeze conditional forecasts.',
            obj({'plan_ref': TEXT, 'refresh_queue': {'type': 'boolean'}})),
        ('hpc.monitor.wait', 'Use the attached forecast-valued monitor controller: persist a timer, release the coordinator while waiting, then observe this original job exactly once when due. No earned credit for waiting.',
            obj({'plan_ref': TEXT})),
        ('hpc.results', 'Parse compact results from the original allocation and apply original acceptance predicates.',
            obj({'plan_ref': TEXT})),
        ('hpc.allocation.order', 'Reorder original pending units at the next unit boundary, retaining all unstarted work.',
            obj({'plan_ref': TEXT, 'unit_ids': STRINGS}))]
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]

async def execute(self, context, tool_name, arguments, operation_key):
    entries = {row['name']: row for row in self.catalog(context)}
    if tool_name not in entries:
        raise ValueError('tool_not_available_to_hpc_role')
    arguments = plain(arguments)
    validate_schema(arguments, entries[tool_name]['input_schema'])
    ledger = self.state(context)
    if not ledger.records('model'):
        self.initialize(context)
    selection = {'tool': tool_name, 'arguments': arguments, 'episode_id': context.episode_id}
    old = ledger.cached(operation_key, selection)
    if old is not None:
        return old
    ledger.put('action_intent', selection, identity='action:'+operation_key)
    references = []
    commission = ledger.commission
    configuration = self.resources[commission['resource_id']]
    if tool_name == 'hpc.read':
        try:
            result = self.read_evidence(context, ledger, arguments['reference'])
        except (ValueError, KeyError) as error:
            return ledger.save_action(operation_key, selection, {
                'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error)}})
    elif tool_name == 'hpc.history.refresh':
        result = ledger.once('shared_history:'+operation_key, 'shared_history', lambda: self._shared_history(ledger))
    elif tool_name == 'hpc.discovery.run':
        # Read-only discovery can be repeated after interrupted observation;
        # all mutations and submissions use the durable Launch operations.
        command = ('cd '+shlex.quote('/lus/flare/projects/BioReason-Aurora-Test')+
                   ' && '+arguments['command'])
        def observe():
            from gene_annotation_episode.episodic_workflow.root.library.execution_resource_identity import resource_identity
            cache_key = resource_identity(commission['resource_id'], configuration)+':'+hpc_queue.digest(command)
            if self.memory:
                cached = self.memory.latest(cache_key, 'inventory')
                if cached['state'] == 'fresh':
                    return cached['data']
            completed = subprocess.run([*configuration['ssh_argv'], command],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            value = {'command': arguments['command'], 'returncode': completed.returncode,
                'stdout': completed.stdout[:65536].decode('utf-8', 'replace'),
                'stderr': completed.stderr[:8192].decode('utf-8', 'replace'),
                'observed_at': time.time(), 'truncated': len(completed.stdout) > 65536}
            if self.memory and completed.returncode == 0:
                self.memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                                    provenance=[str(ledger.path), 'discovery:'+operation_key])
            return value
        result = await asyncio.to_thread(ledger.once, 'discovery:'+operation_key, 'discovery', observe)
    elif tool_name == 'hpc.candidate.propose':
        try:
            candidate = json.loads(arguments['candidate_json'])
            candidates = self._candidates(ledger)
            prior = next((row for row in candidates if row['id'] == candidate['id']), None)
            if prior is not None and prior != candidate:
                raise ValueError('candidate_identity_is_immutable')
            validate_commission({**commission, 'candidates': candidates if prior else candidates+[candidate]}, self.resources)
        except (ValueError, KeyError, TypeError) as error:
            return ledger.save_action(operation_key, selection, {
                'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error)}})
        reference = ('caller_candidate:'+candidate['id'] if candidate in commission['candidates'] else
                     ledger.put('candidate', candidate, identity='candidate:'+candidate['id']))
        result = {'candidate_ref': reference, 'candidate_id': candidate['id']}
    elif tool_name == 'hpc.queue.observe':
        reference = 'queue:'+hpc_queue.digest(operation_key)
        result = ledger.once(reference, 'queue', lambda: self._observe_queue(ledger, configuration))
        result = {'queue_ref': reference, 'features': [hpc_queue.features(result['snapshot'], candidate)
                                                     for candidate in self._candidates(ledger)],
                  'snapshot': result['snapshot']}
    elif tool_name == 'hpc.compare':
        try:
            result = {'comparisons': self._comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
        except (ValueError, KeyError) as error:
            return ledger.save_action(operation_key, selection, {
                'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                    'recovery': 'Use a model_ref from hpc.model.fit or hpc_model_ref and a queue_ref '
                        'from hpc.queue.observe or hpc_queue_refs; a resource identity is not a queue observation.'}})
        result['comparison_ref'] = ledger.put('comparison', {**result, **arguments,
            'episode_id': context.episode_id, 'operation_key': operation_key})
    elif tool_name == 'hpc.plan':
        existing = ledger.records('plan')
        own = next((row for row in existing if row['body'].get('operation_key') == operation_key), None)
        if own is not None:
            plan = own['body']
            forecast_ref = self._freeze(ledger, plan, plan['original_prediction'], plan['original_reference'], {}, 'planned', operation_key)
            return ledger.save_action(operation_key, selection, {'status': 'completed', 'record_refs': [],
                'changed_record_refs': [], 'result': {'plan_ref': own['id'], 'forecast_ref': forecast_ref,
                    **{key: value for key, value in plan.items() if key != 'prediction_episode_id'}}})
        observed = self._queue(ledger, arguments['queue_ref'], require_fresh=True)
        candidate = next(row for row in self._candidates(ledger) if row['id'] == arguments['candidate_id'])
        queue = hpc_queue.features(observed, candidate)
        rules = queue['queue_rules']
        if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
            raise ValueError('choose_an_observed_enabled_execution_queue')
        for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
            if rules['min_'+key] is not None and value < rules['min_'+key] or rules['max_'+key] is not None and value > rules['max_'+key]:
                raise ValueError('candidate_violates_observed_queue_limits')
        plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
        features = self._features(candidate, queue)
        predicted = prediction.predict(ledger.read(arguments['model_ref']), features)
        reference = prediction.predict(ledger.read('reference_model'), features)
        plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'],
                    original_prediction=predicted, original_reference=reference, operation_key=operation_key)
        choices = [row['body'] for row in ledger.records('model_choice')
                   if row['body']['model_ref'] == arguments['model_ref']]
        plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
        plan_ref = ledger.put('plan', plan)
        forecast_ref = self._freeze(ledger, plan, predicted, reference, {}, 'planned', operation_key)
        result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref,
                  **{key: value for key, value in plan.items() if key != 'prediction_episode_id'}}
    elif tool_name == 'hpc.handoff':
        plan = ledger.read(arguments['plan_ref'])
        if (arguments['handoff_ref'] not in self._known(context)
                or not reference_in_context(self.services, context, arguments['handoff_ref'], None)):
            raise ValueError('handoff_not_received')
        target = self.targets.read_target(arguments['handoff_ref'], context.scope)
        if target['assignment'] != plan['practical_assignment']:
            raise ValueError('handoff_does_not_match_frozen_portfolio')
        ledger.put('handoff', {'handoff_ref': arguments['handoff_ref'], 'job_id': target['execution_id'],
            'plan_id': plan['plan_id']}, identity='handoff:'+plan['plan_id'])
        result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
        if 'monitoring' in commission:
            from gene_annotation_episode.episodic_workflow.root.library.hpc_monitoring import MonitorCronController
            result['monitor_controller_ref'] = MonitorCronController(ledger).attach(
                plan, target['execution_id'], commission['monitoring'])
    else:
        plan = ledger.read(arguments['plan_ref'])
        if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff')):
            return ledger.save_action(operation_key, selection, {
                'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'original_handoff_not_attached',
                    'recovery': 'If Launch already completed, redeliver_report using its existing '
                        'hpc_launch_deliveries delivery_ref and hpc_launch_report_form. Then attach '
                        'the returned reference with hpc.handoff. Do not launch replacement work.'}})
        target = self._target(context, ledger, plan)
        candidate = self._candidate(ledger, plan)
        if tool_name == 'hpc.monitor.wait':
            from gene_annotation_episode.episodic_workflow.root.library.hpc_monitoring import MonitorCronController
            if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor_controller')):
                return ledger.save_action(operation_key, selection, {
                    'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference',
                        'code': 'hpc_monitor_controller_not_attached',
                        'next_step': 'This original commission has no attached monitor controller. '
                            'Use hpc.monitor on the original plan, then hpc.results when its outputs are ready. '
                            'Retain the original submitted job; do not launch replacement work.'}})
            # Scheduling needs an actual post-submission observation. The
            # original plan has neither a queue-age clock nor knowledge
            # that Launch may already have observed a completed job.
            if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor')):
                await self.execute(context, 'hpc.monitor',
                    {'plan_ref': arguments['plan_ref'], 'refresh_queue': True}, operation_key+':initial-monitor')
            monitor = self._last_forecast(ledger, plan)
            ready = self._uncollected_completed_unit_ids(ledger, plan, monitor['conditional_prediction'])
            if monitor['conditional_prediction']['telemetry']['state'] in ('complete', 'failed'):
                result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_terminal_job_collect_now'}
            elif ready:
                result = {'schedule': None, 'monitor': monitor,
                    'reason': 'observed_unit_outputs_collect_now', 'ready_unit_ids': sorted(ready)}
            else:
                controller = MonitorCronController(ledger)
                schedule = controller.reserve(plan, candidate, monitor, operation_key)
                if schedule['job_id'] != target['execution_id']:
                    raise ValueError('monitor_schedule_original_job_conflict')
                if schedule['valuation']['schedule']:
                    await controller.wait(schedule)
                    observed = await self.execute(context, 'hpc.monitor',
                        {'plan_ref': arguments['plan_ref'], 'refresh_queue': True}, operation_key+':monitor')
                    ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'],
                        'job_id': target['execution_id'], 'observed': observed}, identity='wake:'+operation_key)
                    result = {'schedule': schedule, 'monitor': observed['result']}
                else:
                    result = {'schedule': schedule, 'monitor': None}
        elif tool_name == 'hpc.allocation.order':
            allowed = {unit['unit_id'] for unit in candidate['units']}
            if not set(arguments['unit_ids']) <= allowed:
                raise ValueError('only_original_work_units_can_be_selected')
            result = self.targets.operations[target['resource_id']].write_allocation_control(
                target['assignment'], target['execution_id'], **self.targets._native_identity(target),
                unit_ids=arguments['unit_ids'], operation_key=operation_key)
            ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': operation_key,
                                            'unit_ids': arguments['unit_ids'], 'receipt': result})
        else:
            observation = ledger.once('status:'+operation_key, 'native_status',
                lambda: self.targets.observe_target(target, operation_key=operation_key))
            allocation, allocation_window = ledger.once('allocation:'+operation_key, 'allocation_snapshot',
                lambda: list(self._allocation(target, plan, operation_key+':allocation')))
            observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                'allocation': allocation, 'allocation_window': allocation_window})
            current = telemetry(observation, allocation, candidate)
            if current.get('current_unit_id') is not None:
                unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
                if unit.get('reports_progress', False):
                    progress_path = plan['manifest']['workspace']+'/units/'+unit['unit_id']+'/progress.json'
                    try:
                        progress_window = ledger.once('unit-progress:'+operation_key, 'unit_progress',
                            lambda: self._window(target, progress_path, 16384, operation_key+':progress')[0])
                        progress = bind_progress(json.loads(base64.b64decode(
                            progress_window['bytes_base64'], validate=True)), plan['plan_id'])
                        current = incorporate_progress(current, progress, candidate)
                    except (OSError, ValueError, KeyError, TypeError) as error:
                        current['progress_failure'] = str(error)
            prior_monitors = [row['body'] for row in ledger.records('monitor')
                              if row['body']['plan_id'] == plan['plan_id']]
            if prior_monitors:
                previous = prior_monitors[-1]['conditional_prediction']['telemetry']
                current['phase_changed'] = (previous.get('phase'), previous.get('current_unit_id')) != (
                    current.get('phase'), current.get('current_unit_id'))
                dt = current['observed_at']-previous['observed_at']
                if dt > 0 and 'completed_fraction' in current and 'completed_fraction' in previous:
                    current['recent_fraction_per_second'] = max(0., current['completed_fraction']-previous['completed_fraction'])/dt
            measured_ref = self._measure(ledger, plan, observation, current, allocation)
            if tool_name == 'hpc.monitor':
                refreshed = None
                queue_ref = plan['queue_ref']
                if arguments['refresh_queue']:
                    queue_ref = 'queue:'+hpc_queue.digest(operation_key)
                    queue_value = ledger.once(queue_ref, 'queue', lambda: self._observe_queue(ledger, configuration))
                    queue = hpc_queue.features(queue_value['snapshot'], candidate, job_id=target['execution_id'])
                    refreshed = prediction.predict(ledger.read(self._current_model(ledger)),
                        self._features(candidate, queue))['times']['queue']
                predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
                reference = prediction.update(plan['original_reference'], current)
                forecast_ref = self._freeze(ledger, plan, predicted, reference, current, current['state'], operation_key)
                orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
                ordered_candidate = deepcopy(candidate)
                if orders:
                    units = {row['unit_id']: row for row in candidate['units']}
                    first = [current['current_unit_id']] if current.get('current_unit_id') else []
                    ids = list(dict.fromkeys([*first, *orders[-1]['unit_ids'], *units]))
                    ordered_candidate['units'] = [units[identity] for identity in ids]
                result = {'plan_id': plan['plan_id'], 'observation_ref': observation_ref,
                    'measured_ref': measured_ref, 'forecast_ref': forecast_ref, 'queue_ref': queue_ref,
                    'conditional_prediction': predicted, 'remaining_work': prediction.compare(ordered_candidate,
                        predicted, commission['obligations'], commission['preferences']),
                    'next_observation': 'Choose an event/elapsed threshold where changed evidence could alter a decision.'}
                ledger.put('monitor', result)
            else:
                accepted, failures = [], []
                for row in (allocation or {}).get('units', []):
                    if row['state'] not in {'complete', 'failed'}:
                        continue
                    unit = next(unit for unit in candidate['units'] if unit['unit_id'] == row['unit_id'])
                    expected_path = plan['manifest']['workspace']+'/units/'+unit['unit_id']+'/result.json'
                    if not row.get('result_path'):
                        failures.append({'unit_id': unit['unit_id'], 'reason': 'missing_original_result_receipt',
                            'expected_path': expected_path,
                            'detail': 'The unit did not record this output at completion. Files found elsewhere '
                                'cannot replace its missing completion hash. Future workers must write to HPC_UNIT_DIRECTORY.'})
                        continue
                    if row['result_path'] != expected_path or row['obligation_id'] != unit['obligation_id']:
                        raise ValueError('result_not_owned_by_original_work_unit')
                    window = ledger.once('result-window:'+operation_key+':'+unit['unit_id'], 'result_window',
                        lambda: self._window(target, expected_path, commission['limits']['result_limit_bytes'],
                                            operation_key+':'+unit['unit_id'])[0])
                    payload = base64.b64decode(window['bytes_base64'], validate=True)
                    if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
                        raise ValueError('result_changed_since_unit_completion')
                    document = json.loads(payload)
                    receipt = {'run_id': self.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope),
                        'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row,
                        'document': document, 'window': window, 'observation_ref': observation_ref}
                    source_ref = self._publish(context, receipt)
                    references.append(source_ref)
                    result_ref = ledger.put('result', {**receipt, 'source_ref': source_ref})
                    if row['state'] == 'complete' and row.get('returncode') == 0 \
                            and accepts(document, commission['obligations'][unit['obligation_id']]):
                        ledger.accept(unit['obligation_id'], result_ref)
                        accepted.append({'obligation_id': unit['obligation_id'], 'result_ref': result_ref})
                    else:
                        failures.append({'unit_id': unit['unit_id'], 'reason': 'original_acceptance_predicate_not_met'})
                if current['state'] in ('complete', 'failed'):
                    measured = ledger.read(measured_ref)
                    if allocation is not None:
                        measured['success'] = len(accepted) == len(candidate['units'])
                        measured['observed_at'] = max(measured['observed_at'], time.time())
                        ledger.put('measured', measured)
                    ledger.put('closed', {'plan_id': plan['plan_id'], 'observation_ref': observation_ref})
                    self.export_closed(ledger, plan)
                result = {'accepted': accepted, 'rejected': failures, 'observation_ref': observation_ref,
                          'credit': ledger.credit_view()}
    outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
    return ledger.save_action(operation_key, selection, outcome)

def permitted_common_actions(self, context):
    if 'monitoring' in self._commission(context.assignment, context.scope):
        return ('tool', 'child', 'redeliver_report')
    return ('tool', 'child', 'wait', 'redeliver_report')

