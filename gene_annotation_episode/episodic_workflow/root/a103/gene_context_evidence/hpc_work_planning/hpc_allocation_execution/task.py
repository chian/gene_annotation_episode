"""The task: the model chooses one HPC action per unit, a tool of the HPC portfolio (read, compare, discover,
propose, observe the queue, freeze a plan, attach the received handoff, monitor, wait, parse results, order units)
or the commission of one of its three children (launch, monitor, results). Carried from the old ``task.py``,
``task_decision.py``, ``task_instructions.py``, ``work_operations.py``, ``decision_inputs.py``,
``decision_state.py``, ``internal_summary.py``, ``waiting.py`` and the operation files ``received_evidence.py``,
``measured_history.py``, ``queue_observations.py``, ``resource_discovery.py``, ``portfolio_candidates.py``,
``portfolio_comparison.py``, ``portfolio_planning.py``, ``portfolio_state.py``, ``allocation_handoff.py``,
``allocation_observations.py``, ``forecast_observations.py``, ``allocation_results.py``, ``allocation_order.py``
and ``to_child_execution_job_submission.py`` (``LaunchPreparation``).

The task always offers a unit and never ends the Episode: its completion controller stops it. A tool that
executes and returns is a unit, an invalid or failed outcome included (the old ``save_action`` results); it
enters the iterator with the credit view it carries. An answer that selects no offered unit, or that names a
record this Episode does not hold, is rejected by ``action``.

State. The old HPC ledger (``HPCLedger``, one SQLite file per owner under the run directory, shared with the
planner and its prediction sister) is called as it was written: ``HPCLedger.open_existing(directory)`` (library
not carried). Every tool returns, beside its result, ``hpc_state``: the ledger as the model and the summary see
it, with ``credit_view`` (the ledger's ``credit_view()``), so ``credit`` and ``internal_summary`` read it from the
outcomes and never open the ledger.

Settings read here (this binding path's entry of the run's ``continuation`` collaborator): ``directory`` (the run's
HPC directory; the old ``self.directory``), ``resources`` (the configured resources by resource_id; the old
``self.resources``), ``monitor_information_unit`` and ``acquired_record_unit`` (the credit units of the monitor and
results children's assignments; new fields of theirs), and, optionally, ``shared_execution_memory`` (true when the
estimate table is the shared execution memory; the old ``self.memory``), ``tool_knowledge_directory`` and
``launch_instructions_directory``.

BLOCKED-ON-JOB-SERVICE (no such service exists yet; a link raises ``LinkError('service_required:...')`` until the
caller supplies the factories). ``job_access``, called by the tools, idempotent on the key where it acts:
``observe_queue(resource_id, key=)`` (the old ``hpc_queue.observe(configuration)``); ``discover(resource_id,
command, key=)`` (the old ``subprocess.run([*ssh_argv, command])``); ``stage_input(plan_id, plan, key=)`` (the old
``LaunchPreparation`` writing ``launch-inputs/<plan>.json``); ``observe_target(target, key=)``;
``read_file(target, path=, offset=, limit=, key=)``; ``write_allocation_control(target, unit_ids=, key=)`` (the old
``ExecutionTargetReader`` and ``operations[resource].write_allocation_control``). ``estimate_table`` (the old
shared ``ExecutionMemory``): ``history(query, now=, queue_only=)``, ``latest(resource, kind)``,
``observe(resource, kind, value, observed_at=, provenance=)``, ``record(**measurement)``, ``as_record()``, called by
the tools, and the read ``read('resource_tool_estimates', 'hpc_execution')`` by ``decide`` (the old
``resource_estimator`` context). The handoff record kind is not defined: ``read_target`` raises."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.gene_context_evidence.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_campaign import (
    accepts, bind_progress, build_plan, incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_history import (
    closed_measurement)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import (
    HpcLedger)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_resource_prediction import (
    forecast_metric, measured_value, pbs_resource_metrics, physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import (
    canonical, digest, features as queue_features)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

_PARENT = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/'
CHILD_SLOTS = {
    'launch': _PARENT + 'execution_job_submission',
    'monitor': _PARENT + 'execution_progress_assessment',
    'results': _PARENT + 'execution_result_acquisition',
}
SERVICES = ('estimate_table', 'job_access')

DISCOVERY_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'
RESULT_PROVIDER = 'episode.hpc_result'
RESULT_VERSION = 'hpc_result_v1'
TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}
MONITOR_FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
                  'result_available')

# What the model reads: the old goal text of this role (``HPCGoal.instructions``), less the sentences about the old
# report forms and the redelivery of a report (the system admits the return; a commission has one return), and with
# the tool names spelt as form names (a tool name is a lowercase identifier).
INSTRUCTIONS = (
    'Iterate toward the original accomplishment while balancing expected credit against real elapsed time and '
    'resource demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction '
    'fits/measures/compares; execution prepares, launches, monitors and parses the selected work. Both '
    'assignments copy hpc_child_commission exactly and carry the hpc parent owner_episode_id. Both sisters inherit '
    'exactly hpc_child_scope, including an empty subject_refs list for an operational task with no biological '
    'inputs. Candidate IDs, model IDs, queue observations and resource IDs are not biological subject_refs. Use the '
    'shared current model and comparisons; resource observations and candidate requests are different quantities. '
    'If suitable history is available, a prediction iteration can improve sizing before launching. No historical '
    'validation support means no invented model-improvement credit. Queue/setup costs belong to an allocation, '
    'which should carry enough useful work. When candidates are absent, discover the remote environment and '
    'documentation with hpc_discovery_run, then design candidate portfolios with hpc_candidate_propose. Discover is '
    'for lightweight inspection; leave installation and file staging to Launch, and scientific computation to the '
    'actual allocation. You choose the real inputs, database, executable commands, resources, worker code and '
    'preparation instructions. Never fabricate inputs or receipts. Every work unit writes result.json and '
    'progress.json under os.environ["HPC_UNIT_DIRECTORY"], its original per-unit working directory. The '
    'allocation workspace is for staged inputs, not these unit outputs; its fields must satisfy the caller '
    'acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. Candidate files use relative paths; '
    '{allocation_workspace} expands in files, argv, environment and preparation. Compute commands must run on '
    'allocated compute nodes using the facility launcher. Compare portfolios using current queue features and '
    'measured history. A plan freezes its original forecast, scientific manifest and acceptance criteria. '
    'Commission launch with the plan_ref of that actual job and resource; it returns the actual handoff, and a '
    'plan is launched once, never again. The execution agent chooses its scripts, environment and operational '
    'commands from the supplied resource instructions and observations. Supplied reference sources are available '
    'in the local input file; do not transcribe them into a child goal or prescribe a setup/submit sequence. '
    'Attach the received handoff with hpc_handoff. Use hpc_monitor once when another observation can affect your '
    'decision; it revises conditional predictions and attainable credit. Use hpc_results directly for known '
    'parsing. Commission monitor/results children only for actual investigation. Completed unit outputs can await '
    'parsing while PBS is still running or cleaning up. When pending_action is collect, use hpc_results for those '
    'original outputs; completion is not acceptance. When hpc_monitor_controllers is present, select '
    'hpc_monitor_wait for a scheduled observation: its attached controller evaluates the conditional forecast, '
    'persists a wake time, and executes the original monitor at that time. This preserves pending accomplishment '
    'value across waits without credit for sleeping. The timer cannot turn into another unobserved wait. Do not '
    'poll for credit or duplicate a submitted attempt. Never replace an uncertain submission. Accepted '
    'accomplishment, model improvement, and fixed prospective forecast validation are the only parent credit '
    'components; launch-local credits are not added again. The episode iterator decides continuation from credit; '
    'add no stopping budget.')

TOOL_SPECS = {
    'hpc_read': ('Read retained HPC evidence by its exact identity.', obj({'reference': TEXT})),
    'hpc_compare': ('Compare all approved portfolios; no work is selected or launched.',
                    obj({'model_ref': TEXT, 'queue_ref': TEXT})),
    'hpc_history_refresh': ('Read age-weighted shared timing history once. No remote discovery, polling credit, or '
                            'new scientific work.', obj({})),
    'hpc_discovery_run': ('Run one lightweight remote inspection or documentation retrieval through the '
                          'established SSH transport. No job submission, installation or scientific computation; '
                          'those belong to Launch and the allocation.', obj({'command': TEXT})),
    'hpc_candidate_propose': (
        'Retain an executable portfolio selected by this episode. candidate_json is JSON with id, queue, nodes, '
        'wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), '
        'optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units '
        '(unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: '
        'relative path, text: exact contents}], and preparation instructions for Launch. effort is a positive '
        'finite number expressing relative work, for example 1.0; workload sizes belong in features. No per-unit '
        'execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate identities '
        'are immutable.', obj({'candidate_json': TEXT})),
    'hpc_queue_observe': ('Acquire PBS queue and ALCF score/status once and transform them.', obj({})),
    'hpc_plan': ('Freeze one useful portfolio and its forecasts; return a concrete plan to launch.',
                 obj({'candidate_id': TEXT, 'model_ref': TEXT, 'queue_ref': TEXT})),
    'hpc_handoff': ('Bind the original received PBS handoff to the exact frozen portfolio.',
                    obj({'plan_ref': TEXT, 'handoff_ref': TEXT})),
    'hpc_monitor': ('Observe the original job and progress once; update and freeze conditional forecasts.',
                    obj({'plan_ref': TEXT, 'refresh_queue': {'type': 'boolean'}})),
    'hpc_monitor_wait': ('Use the attached forecast-valued monitor controller: persist a timer, release the '
                         'coordinator while waiting, then observe this original job exactly once when due. No '
                         'earned credit for waiting.', obj({'plan_ref': TEXT})),
    'hpc_results': ('Parse compact results from the original allocation and apply original acceptance predicates.',
                    obj({'plan_ref': TEXT})),
    'hpc_allocation_order': ('Reorder original pending units at the next unit boundary, retaining all unstarted '
                             'work.', obj({'plan_ref': TEXT, 'unit_ids': STRINGS})),
}
CHILD_SPECS = {
    'launch': ('Commission the Launch child with one frozen plan: it submits that plan\'s actual job on its '
               'resource and returns the usable handoff.', obj({'plan_ref': TEXT})),
    'monitor': ('Commission the progress monitor for one execution target. This requests information; it never '
                'polls here.', obj({'assignment': obj({
                    'target_handle': TEXT,
                    'requested_fields': {'type': 'array', 'uniqueItems': True,
                                         'items': {'type': 'string', 'enum': list(MONITOR_FIELDS)}},
                    'known_progress_refs': STRINGS, 'permitted_committed_record_types': STRINGS})})),
    'results': ('Commission result acquisition for the attached handoff of one plan, only for an actual '
                'investigation (hpc_results parses known outputs directly). selector is the generic native '
                'selector: paths, or one path with offset and limit.',
                obj({'plan_ref': TEXT, 'selector': {'type': 'object'}})),
}


def selection_options(settings):
    """The selections this decision offers, one schema each (the old ``action_schema`` of tools and children)."""
    options = []
    for name, (description, schema) in TOOL_SPECS.items():
        if name == 'hpc_history_refresh' and not settings.get('shared_execution_memory'):
            continue
        options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                            'arguments': schema}))
    for slot, (description, schema) in CHILD_SPECS.items():
        options.append(obj({'kind': {'type': 'string', 'const': 'child'}, 'slot': {'type': 'string', 'const': slot},
                            'arguments': schema}))
    return options


def action_schema(settings):
    return obj({'selection': {'anyOf': selection_options(settings)}})


def catalog(settings):
    """The tool and child descriptions the model reads (the old ``HPCWorkOperations.catalog``)."""
    entries = [{'kind': 'tool', 'name': name, 'description': description, 'input_schema': schema}
               for name, (description, schema) in TOOL_SPECS.items()
               if not (name == 'hpc_history_refresh' and not settings.get('shared_execution_memory'))]
    return entries + [{'kind': 'child', 'name': slot, 'description': description, 'input_schema': schema}
                      for slot, (description, schema) in CHILD_SPECS.items()]


# ---------------------------------------------------------------------------------------------------------------
# The ledger, as the old operation files read it (library candidates: they take the ledger and plain values).

def candidates_of(ledger):
    """The old ``PortfolioComparison._candidates``."""
    return ledger.commission['candidates'] + [row['body'] for row in ledger.records('candidate')]


def candidate_of(ledger, plan):
    """The old ``PortfolioComparison._candidate``."""
    return next(row for row in candidates_of(ledger) if row['id'] == plan['candidate_id'])


def candidate_features(candidate, queue):
    """The old ``PortfolioComparison._features``."""
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def current_model(ledger):
    """The old ``PortfolioState._current_model``."""
    records = ledger.records('model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'


def actual_obligations(ledger):
    return [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
            if row['kind'] == 'actual']


def comparisons(ledger, model_ref, queue_ref):
    """The old ``PortfolioComparison._comparisons``: every candidate predicted and compared, best first."""
    model = ledger.read(model_ref)
    observed = queue_snapshot(ledger, queue_ref)
    actual = actual_obligations(ledger)
    results = []
    for candidate in candidates_of(ledger):
        queue = queue_features(observed, candidate)
        forecast = prediction.predict(model, candidate_features(candidate, queue))
        row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                 ledger.commission['preferences'], already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def queue_snapshot(ledger, reference, *, require_fresh=False):
    """The old ``QueueObservations._queue``."""
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def history_rows(ledger):
    """The old ``MeasuredHistory._history``: commission history, the latest shared history and one latest
    observation per closed allocation."""
    rows = {row['id']: row for row in ledger.commission['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()} - {None}
    for snapshot in ledger.records('shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    latest = {}
    for row in ledger.records('measured'):
        if row['body']['plan_id'] in closed:
            latest[row['body']['plan_id']] = row
    for plan_id, row in latest.items():
        body = row['body']
        rows['allocation:' + plan_id] = {
            'id': 'allocation:' + plan_id, 'observed_at': body['observed_at'],
            'features': plans[plan_id]['original_prediction']['features'], 'metrics': body['metrics'],
            'success': body['success'], 'provenance': [row['id']]}
    return rows


def shared_history(ctx, ledger):
    """The old ``MeasuredHistory._shared_history``: the shared memory's rows, queue timing resource-wide, work
    timing only with the matching profile, PBS queues not pooled unless modelled, at most 2000 rows."""
    memory = ctx.services['estimate_table']
    commission = ledger.commission
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], ctx.settings['resources'][commission['resource_id']])
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in memory.history(query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in memory.history(profile, now=now)})
    queues = {candidate['queue'] for candidate in candidates_of(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        queue = row.get('queue')
        if 'queue' in row['metrics'] and not (queue and (queues == {queue} or 'queue:' + queue in model_features)):
            row['metrics'].pop('queue')
        if queue:
            row['features']['queue:' + queue] = 1.
        if row['metrics'] or row['success'] is not None:
            filtered.append(row)
    original = {row['id'] for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in commission['history']} - {None}
    return {'captured_at': now, 'policy': memory.as_record()['policy'],
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts][:2000]}


def export_closed(ctx, ledger, plan):
    """The old ``MeasuredHistory.export_closed``: a closed allocation enters the shared memory (no remote work)."""
    if not ctx.settings.get('shared_execution_memory'):
        return
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('only_closed_allocations_enter_shared_history')
    measured = once(ledger, 'export_measurement:' + plan['plan_id'], 'export_measurement', lambda: [
        row for row in ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
    handoff = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']][-1]
    ctx.services['estimate_table'].record(**closed_measurement(
        ledger.commission, plan, measured, handoff, resources=ctx.settings['resources'], ledger=ledger.ledger))


def last_forecast(ledger, plan):
    """The old ``ForecastObservations._last_forecast``."""
    monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
    if monitors:
        return monitors[-1]
    forecasts = [row for row in ledger.records('forecast') if row['body']['plan_id'] == plan['plan_id']]
    return {'conditional_prediction': plan['original_prediction'], 'forecast_ref': forecasts[0]['id']}


def collected_unit_ids(ledger, plan):
    """The old ``AllocationResults._collected_unit_ids``."""
    return {row['body']['unit']['unit_id'] for row in ledger.records('result')
            if row['body'].get('plan_id') == plan['plan_id'] and isinstance(row['body'].get('unit'), dict)
            and isinstance(row['body']['unit'].get('unit_id'), str)}


def uncollected_completed_unit_ids(ledger, plan, current):
    """The old ``AllocationResults._uncollected_completed_unit_ids``."""
    allowed = {unit['unit_id'] for unit in candidate_of(ledger, plan)['units']}
    observed = set(current.get('telemetry', {}).get('completed_unit_ids', ()))
    return (observed & allowed) - collected_unit_ids(ledger, plan)


def freeze(ledger, plan, predicted, reference, current, phase, operation_key):
    """The old ``ForecastObservations._freeze``: a forecast frozen with its validation slots."""
    elapsed = {'queue': current.get('queue_elapsed_seconds', 0.), 'work': current.get('work_elapsed_seconds', 0.)}
    slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
             if slot['phase'] == phase and elapsed.get(slot['metric'], elapsed['work']) >= slot['minimum_elapsed_seconds']
             and forecast_metric(predicted, slot['metric']) is not None]
    body = once(ledger, 'issued:' + operation_key, 'forecast_issue', lambda: {
        'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted, 'reference': reference,
        'phase': phase, 'elapsed': elapsed, 'model_ref': plan.get('model_ref'),
        'prediction_episode_id': plan.get('prediction_episode_id')})
    return ledger.freeze(body, slots)


def measure(ledger, plan, observation, current, allocation):
    """The old ``ForecastObservations._measure``: queue, setup and work durations, censored when unfinished."""
    now = current['observed_at']
    metrics = pbs_resource_metrics(observation)
    if current['queued_at'] is not None:
        metrics['queue'] = {'seconds': current['queue_elapsed_seconds'], 'censored': current['started_at'] is None,
                            'observed_at': current['started_at'] or now}
    receipt = observation['native'].get('exit_receipt')
    if receipt:
        metrics['work'] = {'seconds': receipt['duration_seconds'], 'censored': current['state'] == 'failed',
                           'observed_at': timestamp(receipt['finished_at'])}
    elif current['started_at'] is not None:
        metrics['work'] = {'seconds': current['work_elapsed_seconds'], 'censored': True, 'observed_at': now}
    if allocation and current['started_at'] is not None:
        metrics['setup'] = {'seconds': max(0., allocation['started_at'] - current['started_at']),
                            'censored': False, 'observed_at': allocation['started_at']}
        if allocation.get('finished_at') is not None:
            metrics['work'] = {'seconds': allocation['finished_at'] - allocation['started_at'],
                               'censored': False, 'observed_at': allocation['finished_at']}
    measured = {'plan_id': plan['plan_id'], 'metrics': metrics, 'observed_at': now,
                'success': False if current['state'] == 'failed' else None}
    reference = ledger.put('measured', measured)
    ledger.score(reference, log_score=prediction.log_score, measured_value=measured_value,
                 forecast_metric=forecast_metric)
    return reference


def plan_view(plan):
    """A plan as shown: the supplied files by path and digest (their text is in the staged input)."""
    return {**{key: value for key, value in plan.items() if key != 'supplied_files'},
            'supplied_files': [{'path': row['path'], 'sha256': row['sha256']} for row in plan['supplied_files']]}


def hpc_state(ledger):
    """The ledger as the old ``HPCSummary.decision_context`` showed it, plus what ``msg_to_child`` and the
    summary need (plans, handoffs, staged launch inputs). Returned by every tool in its outcome."""
    commission = ledger.commission
    model = current_model(ledger)
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    plans = {row['id']: plan_view(row['body']) for row in ledger.records('plan')}
    ready = {}
    for row in ledger.records('plan'):
        plan = row['body']
        if plan['plan_id'] not in closed and any(c['body']['plan_id'] == plan['plan_id']
                                                 for c in ledger.records('monitor_controller')):
            current = last_forecast(ledger, plan)['conditional_prediction']
            ready[plan['plan_id']] = {'terminal': current.get('telemetry', {}).get('state') in ('complete', 'failed'),
                                      'ready_unit_ids': sorted(uncollected_completed_unit_ids(ledger, plan, current))}
    return {
        'credit_view': ledger.credit_view(), 'model_ref': model,
        'model_support': prediction.predict(ledger.read(model), {})['support'],
        'candidates': candidates_of(ledger), 'plans': plans,
        'handoffs': {row['body']['plan_id']: row['body'] for row in ledger.records('handoff')},
        'launch_inputs': {row['body']['plan_id']: row['body'] for row in ledger.records('launch_input')},
        'closed': sorted(closed), 'tool_requests': [row['body'] for row in ledger.records('tool_request')],
        'latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                               if key not in ('episode_id', 'operation_key')}}
                              for row in ledger.records('comparison')[-1:]],
        'latest_monitor': ledger.records('monitor')[-1:],
        'monitor_controllers': ledger.records('monitor_controller'), 'pending_collect': ready,
        'queue_refs': [row['id'] for row in ledger.records('queue')],
        'shared_history_refs': [row['id'] for row in ledger.records('shared_history')],
        'available_training_ids': sorted(set(history_rows(ledger)) - set(commission['validation_ids'])),
        'accepted_obligations': actual_obligations(ledger)}


# ---------------------------------------------------------------------------------------------------------------
# Opening the ledger, outcomes, and the places where the job services are wanted.

def read_target(ctx, handoff_ref):
    """The target (resource id, execution id, assignment, native identity) of a received handoff."""
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: the handoff record kind and its work table (JOB_LEDGER); wanted call: '
        "row = ctx.store.table(JOB_LEDGER).get(handoff_ref); target = ctx.services['job_access']"
        '.read_target(row)')


def monitor_controller(ledger):
    """The scheduled-monitor controller (``attach``, ``reserve``, ``wait``) and ``choose_schedule``."""
    raise NotImplementedError(
        'hpc_monitoring.MonitorCronController and choose_schedule are not in the library of '
        'gene_context_evidence (jobs/hpc/gene_context_evidence/hpc_monitoring.py holds only validate_policy); '
        'wanted call: MonitorCronController(ledger)')


def once(ledger, identity, kind, calculate):
    """Recover a committed step without another observation (the old ``HPCLedger.once``): the recorded evidence
    under ``identity``, or ``calculate()`` recorded under it."""
    try:
        return ledger.read(identity)
    except ValueError as error:
        if not str(error).startswith('unknown_hpc_evidence:'):
            raise
    value = calculate()
    ledger.put(kind, value, identity=identity)
    return value


def open_ledger(ctx, arguments):
    """The old ``PortfolioState.state``: the ledger of this Episode's owner, with the reference model (the old
    ``initialize``). The check that the sister's scope and commission equal the owner's was a check of the
    commission and is not carried."""
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    if not ledger.records('model'):
        prior = prediction.prior_model(ledger.commission['model'])
        ledger.put('model', prior, identity='reference_model')
        if ctx.settings.get('shared_execution_memory'):
            imported = once(ledger, 'shared_history_entry', 'shared_history', lambda: shared_history(ctx, ledger))
            if imported['observations'] and not ledger.records('model_choice'):
                model = prediction.fit(ledger.commission['model'], imported['observations'])
                reference = ledger.put('model', model)
                ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                           identity='shared_history_initial_model')
    return ledger


def outcome_of(ledger, status, result, references=(), *, feedback=None, extra=None):
    """The unit outcome of an HPC tool: the old ``{'status', 'record_refs', 'changed_record_refs', 'result'}``
    with the ledger state it leaves behind."""
    outcome = {'status': status, 'record_refs': list(references), 'changed_record_refs': list(references),
               'result': result, 'hpc_state': hpc_state(ledger)}
    if feedback is not None:
        outcome['feedback'] = feedback
    outcome.update(extra or {})
    return outcome


def invalid_outcome(ledger, error, **extra):
    """The old ``save_action`` of an invalid result: arguments or references the operation refuses."""
    feedback = {'category': 'arguments_or_reference', 'code': str(error), **extra}
    return outcome_of(ledger, 'invalid', None, feedback=feedback)


def run(arguments, ctx, body):
    """One synchronous tool: open the ledger, run ``body(ctx, ledger, operation, arguments)``, and return its
    result as a completed outcome, or the refusal of a value the operation does not accept as an invalid one."""
    ledger = open_ledger(ctx, arguments)
    try:
        result = body(ctx, ledger, arguments['operation'], arguments)
    except (ValueError, KeyError, TypeError, OSError) as error:
        return invalid_outcome(ledger, error)
    if isinstance(result, tuple):
        result, references, extra = result
        return outcome_of(ledger, 'completed', result, references, extra=extra)
    return outcome_of(ledger, 'completed', result)


# ---------------------------------------------------------------------------------------------------------------
# The tools of the HPC portfolio.

def resolve_received_reference(ctx, reference, namespace, scope):
    """The old ``ReceivedEvidence.resolve_received_reference``: a held ``episode.hpc_result`` source of this run
    and scope. A reference this Episode does not hold is not received."""
    if not ctx.store.holds(reference):
        return False
    source = ctx.store.get(reference)
    if source.get('provider') != RESULT_PROVIDER:
        return None
    if namespace not in (None, 'source'):
        return False
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    if body['run_id'] != ctx.run_id:
        return False
    try:
        ctx.store.validate_scope(body['scope'], parent_scope=plain(scope))
    except ValueError:
        return False
    return True


def read_evidence(ctx, ledger, reference, scope):
    """The old ``ReceivedEvidence.read_evidence``: history rows, ledger records and owned received results."""
    history = history_rows(ledger)
    if reference in history:
        return history[reference]
    if not reference.startswith('source_'):
        return ledger.read(reference)
    rows = [row['body'] for row in ledger.records('result') if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or resolve_received_reference(ctx, reference, 'source', scope) is not True:
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


def read_body(ctx, ledger, operation, arguments):
    return read_evidence(ctx, ledger, operation['reference'], arguments['scope'])


def hpc_read(arguments, ctx):
    return run(arguments, ctx, read_body)


def history_refresh_body(ctx, ledger, operation, arguments):
    if not ctx.settings.get('shared_execution_memory'):
        raise ValueError('shared_execution_memory_not_configured')
    return once(ledger, 'shared_history:' + ctx.operation_key, 'shared_history', lambda: shared_history(ctx, ledger))


def hpc_history_refresh(arguments, ctx):
    return run(arguments, ctx, history_refresh_body)


def discovery_body(ctx, ledger, operation, arguments):
    commission = ledger.commission
    configuration = ctx.settings['resources'][commission['resource_id']]
    command = 'cd ' + shlex.quote(DISCOVERY_DIRECTORY) + ' && ' + operation['command']

    def observe():
        cache_key = resource_identity(commission['resource_id'], configuration) + ':' + digest(command)
        memory = ctx.services['estimate_table'] if ctx.settings.get('shared_execution_memory') else None
        if memory:
            cached = memory.latest(cache_key, 'inventory')
            if cached['state'] == 'fresh':
                return cached['data']
        completed = ctx.services['job_access'].discover(commission['resource_id'], command, key=ctx.operation_key)
        value = {'command': operation['command'], 'returncode': completed['returncode'],
                 'stdout': completed['stdout'][:65536].decode('utf-8', 'replace'),
                 'stderr': completed['stderr'][:8192].decode('utf-8', 'replace'), 'observed_at': time.time(),
                 'truncated': len(completed['stdout']) > 65536}
        if memory and completed['returncode'] == 0:
            memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                           provenance=['hpc_ledger:' + ledger.ledger, 'discovery:' + ctx.operation_key])
        return value
    return once(ledger, 'discovery:' + ctx.operation_key, 'discovery', observe)


def hpc_discovery_run(arguments, ctx):
    return run(arguments, ctx, discovery_body)


def candidate_body(ctx, ledger, operation, arguments):
    commission = ledger.commission
    candidate = json.loads(operation['candidate_json'])
    candidates = candidates_of(ledger)
    prior = next((row for row in candidates if row['id'] == candidate['id']), None)
    if prior is not None and prior != candidate:
        raise ValueError('candidate_identity_is_immutable')
    validate_commission({**commission, 'candidates': candidates if prior else candidates + [candidate]},
                        ctx.settings['resources'])
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates']
                 else ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return {'candidate_ref': reference, 'candidate_id': candidate['id']}


def hpc_candidate_propose(arguments, ctx):
    return run(arguments, ctx, candidate_body)


def observe_queue(ctx, ledger, key):
    """The old ``QueueObservations._observe_queue``: a fresh shared-memory observation, else one acquisition."""
    commission = ledger.commission
    configuration = ctx.settings['resources'][commission['resource_id']]
    memory = ctx.services['estimate_table'] if ctx.settings.get('shared_execution_memory') else None
    resource = resource_identity(commission['resource_id'], configuration)
    if memory:
        cached = memory.latest(resource, 'queue')
        if cached['state'] == 'fresh' and cached['age_seconds'] <= commission['limits']['queue_max_age_seconds']:
            return cached['data']
    value = ctx.services['job_access'].observe_queue(commission['resource_id'], key=key)
    if memory:
        memory.observe(resource, 'queue', value, observed_at=value['snapshot']['captured_at'],
                       provenance=value['acquisition'])
    return value


def queue_body(ctx, ledger, operation, arguments):
    reference = 'queue:' + digest(ctx.operation_key)
    result = once(ledger, reference, 'queue', lambda: observe_queue(ctx, ledger, ctx.operation_key))
    return {'queue_ref': reference,
            'features': [queue_features(result['snapshot'], candidate) for candidate in candidates_of(ledger)],
            'snapshot': result['snapshot']}


def hpc_queue_observe(arguments, ctx):
    return run(arguments, ctx, queue_body)


def compare_body(ctx, ledger, operation, arguments):
    result = {'comparisons': comparisons(ledger, operation['model_ref'], operation['queue_ref'])}
    result['comparison_ref'] = ledger.put('comparison', {**result, **operation, 'episode_id': ctx.episode_id,
                                                         'operation_key': ctx.operation_key})
    return result


def hpc_compare(arguments, ctx):
    ledger = open_ledger(ctx, arguments)
    try:
        return outcome_of(ledger, 'completed', compare_body(ctx, ledger, arguments['operation'], arguments))
    except (ValueError, KeyError) as error:
        return invalid_outcome(
            ledger, error, recovery='Use a model_ref from hpc_model_ref and a queue_ref from hpc_queue_observe or '
            'hpc_queue_refs; a resource identity is not a queue observation.')


def plan_body(ctx, ledger, operation, arguments):
    commission = ledger.commission
    configuration = ctx.settings['resources'][commission['resource_id']]
    existing = ledger.records('plan')
    own = next((row for row in existing if row['body'].get('operation_key') == ctx.operation_key), None)
    if own is not None:
        plan, plan_ref = own['body'], own['id']
        forecast_ref = freeze(ledger, plan, plan['original_prediction'], plan['original_reference'], {}, 'planned',
                              ctx.operation_key)
    else:
        observed = queue_snapshot(ledger, operation['queue_ref'], require_fresh=True)
        candidate = next(row for row in candidates_of(ledger) if row['id'] == operation['candidate_id'])
        queue = queue_features(observed, candidate)
        rules = queue['queue_rules']
        if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
            raise ValueError('choose_an_observed_enabled_execution_queue')
        for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
            if (rules['min_' + key] is not None and value < rules['min_' + key]
                    or rules['max_' + key] is not None and value > rules['max_' + key]):
                raise ValueError('candidate_violates_observed_queue_limits')
        plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
        features = candidate_features(candidate, queue)
        predicted = prediction.predict(ledger.read(operation['model_ref']), features)
        reference = prediction.predict(ledger.read('reference_model'), features)
        plan.update(model_ref=operation['model_ref'], queue_ref=operation['queue_ref'],
                    original_prediction=predicted, original_reference=reference, operation_key=ctx.operation_key)
        choices = [row['body'] for row in ledger.records('model_choice')
                   if row['body']['model_ref'] == operation['model_ref']]
        plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
        plan_ref = ledger.put('plan', plan)
        forecast_ref = freeze(ledger, plan, predicted, reference, {}, 'planned', ctx.operation_key)
    # The old ``LaunchPreparation.initial_decision_context``: the plan is the Launch child's supplied input, kept
    # immutable. It is a record in custody (named in the launch assignment) and a file the job service stages.
    artifact = ctx.store.artifact(canonical(plan).encode('utf-8'), 'application/json')
    staged = once(ledger, 'launch_input:' + plan['plan_id'], 'launch_input', lambda: {
        'plan_id': plan['plan_id'],
        **ctx.services['job_access'].stage_input(plan['plan_id'], plan, key=ctx.operation_key),
        'input_ref': artifact})
    result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref,
              **{key: value for key, value in plan.items() if key != 'prediction_episode_id'},
              'launch_input': staged}
    return result, [artifact], {}


def hpc_plan(arguments, ctx):
    return run(arguments, ctx, plan_body)


def handoff_body(ctx, ledger, operation, arguments):
    commission = ledger.commission
    plan = ledger.read(operation['plan_ref'])
    if not ctx.store.holds(operation['handoff_ref']):
        raise ValueError('handoff_not_received')
    target = read_target(ctx, operation['handoff_ref'])
    if target['assignment'] != plan['practical_assignment']:
        raise ValueError('handoff_does_not_match_frozen_portfolio')
    ledger.put('handoff', {'handoff_ref': operation['handoff_ref'], 'job_id': target['execution_id'],
                           'plan_id': plan['plan_id']}, identity='handoff:' + plan['plan_id'])
    result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
    if 'monitoring' in commission:
        result['monitor_controller_ref'] = monitor_controller(ledger).attach(plan, target['execution_id'],
                                                                             commission['monitoring'])
    return result


def hpc_handoff(arguments, ctx):
    return run(arguments, ctx, handoff_body)


class AttachmentMissing(ValueError):
    """The plan's handoff is not attached (the old ``original_handoff_not_attached`` refusal)."""


def allocation_target(ctx, ledger, plan):
    """The old ``AllocationObservations._target``: the original handoff this Episode holds, for this plan."""
    handoff = ledger.read('handoff:' + plan['plan_id'])
    if not ctx.store.holds(handoff['handoff_ref']):
        raise ValueError('original_handoff_not_received_by_this_parent')
    target = read_target(ctx, handoff['handoff_ref'])
    if target['assignment'] != plan['practical_assignment']:
        raise ValueError('handoff_does_not_match_frozen_portfolio')
    return target


def read_window(ctx, target, path, limit, key):
    """The old ``AllocationObservations._window``: one compact file window, complete and within its limit."""
    value = ctx.services['job_access'].read_file(target, path=path, offset=0, limit=limit + 1, key=key)
    payload = base64.b64decode(value['bytes_base64'], validate=True)
    if len(payload) != value['size_bytes'] or len(payload) > limit:
        raise ValueError('compact_result_incomplete_or_too_large')
    return value, payload


def read_allocation(ctx, target, plan, key):
    """The old ``AllocationObservations._allocation``: ``allocation-status.json`` (at most 512 KiB), identity
    checked against the plan, the job and the manifest."""
    path = plan['manifest']['workspace'] + '/allocation-status.json'
    try:
        window, payload = read_window(ctx, target, path, 512 * 1024, key)
    except (FileNotFoundError, ValueError) as error:
        # Absence before the runner starts is normal; other failures remain visible and do not manufacture a
        # progress estimate.
        return None, {'path': path, 'failure': str(error)}
    value = json.loads(payload)
    if (value['plan_id'] != plan['plan_id'] or value['job_id'] != target['execution_id']
            or value['manifest_sha256'] != plan['manifest_sha256']):
        raise ValueError('allocation_receipt_identity_conflict')
    expected = {unit['unit_id'] for unit in plan['manifest']['units']}
    if (len({row['unit_id'] for row in value['units']}) != len(value['units'])
            or not {row['unit_id'] for row in value['units']} <= expected):
        raise ValueError('allocation_receipt_units_conflict')
    return value, window


def observe_allocation(ctx, ledger, plan, target, candidate, key):
    """The old ``AllocationObservations._observe_original_allocation`` up to the dispatch: one observation of the
    original job (status, allocation status, the current unit's progress) and its measurement."""
    access = ctx.services['job_access']
    observation = once(ledger, 'status:' + key, 'native_status', lambda: access.observe_target(target, key=key))
    allocation, allocation_window = once(ledger, 
        'allocation:' + key, 'allocation_snapshot', lambda: list(read_allocation(ctx, target, plan, key + ':allocation')))
    observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                                                 'allocation': allocation, 'allocation_window': allocation_window})
    current = telemetry(observation, allocation, candidate)
    if current.get('current_unit_id') is not None:
        unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
        if unit.get('reports_progress', False):
            progress_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/progress.json'
            try:
                progress_window = once(ledger, 
                    'unit-progress:' + key, 'unit_progress',
                    lambda: read_window(ctx, target, progress_path, 16384, key + ':progress')[0])
                progress = bind_progress(json.loads(base64.b64decode(progress_window['bytes_base64'], validate=True)),
                                         plan['plan_id'])
                current = incorporate_progress(current, progress, candidate)
            except (OSError, ValueError, KeyError, TypeError) as error:
                current['progress_failure'] = str(error)
    prior_monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
    if prior_monitors:
        previous = prior_monitors[-1]['conditional_prediction']['telemetry']
        current['phase_changed'] = ((previous.get('phase'), previous.get('current_unit_id'))
                                    != (current.get('phase'), current.get('current_unit_id')))
        dt = current['observed_at'] - previous['observed_at']
        if dt > 0 and 'completed_fraction' in current and 'completed_fraction' in previous:
            current['recent_fraction_per_second'] = max(
                0.0, current['completed_fraction'] - previous['completed_fraction']) / dt
    measured_ref = measure(ledger, plan, observation, current, allocation)
    return observation, allocation, allocation_window, observation_ref, current, measured_ref


def update_conditional_forecast(ctx, ledger, operation, plan, target, candidate, observation_ref, current,
                                measured_ref, key):
    """The old ``ForecastObservations._update_conditional_forecast``."""
    refreshed = None
    queue_ref = plan['queue_ref']
    if operation['refresh_queue']:
        queue_ref = 'queue:' + digest(key)
        queue_value = once(ledger, queue_ref, 'queue', lambda: observe_queue(ctx, ledger, key))
        queue = queue_features(queue_value['snapshot'], candidate, job_id=target['execution_id'])
        refreshed = prediction.predict(ledger.read(current_model(ledger)),
                                       candidate_features(candidate, queue))['times']['queue']
    predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
    reference = prediction.update(plan['original_reference'], current)
    forecast_ref = freeze(ledger, plan, predicted, reference, current, current['state'], key)
    orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
    ordered_candidate = deepcopy(candidate)
    if orders:
        units = {row['unit_id']: row for row in candidate['units']}
        first = [current['current_unit_id']] if current.get('current_unit_id') else []
        ids = list(dict.fromkeys([*first, *orders[-1]['unit_ids'], *units]))
        ordered_candidate['units'] = [units[identity] for identity in ids]
    commission = ledger.commission
    result = {'plan_id': plan['plan_id'], 'observation_ref': observation_ref, 'measured_ref': measured_ref,
              'forecast_ref': forecast_ref, 'queue_ref': queue_ref, 'conditional_prediction': predicted,
              'remaining_work': prediction.compare(ordered_candidate, predicted, commission['obligations'],
                                                   commission['preferences']),
              'next_observation': 'Choose an event/elapsed threshold where changed evidence could alter a decision.'}
    ledger.put('monitor', result)
    return result


def publish_result(ctx, body):
    """The old ``AllocationResults._publish``: the retained result as an artifact and an ``episode.hpc_result``
    source, both produced by this unit. Returns the source and its artifact."""
    artifact = ctx.store.artifact(canonical(body).encode('utf-8'), 'application/json')
    source = ctx.store.put('source', {
        'provider': RESULT_PROVIDER, 'accession': 'hpc_' + digest([ctx.run_id, ctx.episode_id, body]),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': RESULT_VERSION,
        'retrieved_at': datetime.fromtimestamp(body['unit']['finished_at'], timezone.utc).isoformat()},
        origin='tool')['id']
    return source, artifact


def collect_original_results(ctx, ledger, scope, plan, target, candidate, allocation, observation_ref, current,
                             measured_ref):
    """The old ``AllocationResults._collect_original_results``: each finished unit's ``result.json`` at its
    original directory, its completion hash verified, published, and accepted when the frozen predicate holds;
    the allocation is closed and exported when the job is terminal."""
    commission = ledger.commission
    accepted, failures, sources, artifacts = [], [], [], []
    for row in (allocation or {}).get('units', []):
        if row['state'] not in {'complete', 'failed'}:
            continue
        unit = next(unit for unit in candidate['units'] if unit['unit_id'] == row['unit_id'])
        expected_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/result.json'
        if not row.get('result_path'):
            failures.append({'unit_id': unit['unit_id'], 'reason': 'missing_original_result_receipt',
                             'expected_path': expected_path,
                             'detail': 'The unit did not record this output at completion. Files found elsewhere '
                                       'cannot replace its missing completion hash. Future workers must write to '
                                       'HPC_UNIT_DIRECTORY.'})
            continue
        if row['result_path'] != expected_path or row['obligation_id'] != unit['obligation_id']:
            raise ValueError('result_not_owned_by_original_work_unit')
        key = ctx.operation_key + ':' + unit['unit_id']
        window = once(ledger, 'result-window:' + key, 'result_window', lambda: read_window(
            ctx, target, expected_path, commission['limits']['result_limit_bytes'], key)[0])
        payload = base64.b64decode(window['bytes_base64'], validate=True)
        if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
            raise ValueError('result_changed_since_unit_completion')
        document = json.loads(payload)
        receipt = {'run_id': ctx.run_id, 'episode_id': ctx.episode_id, 'scope': plain(scope),
                   'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row, 'document': document,
                   'window': window, 'observation_ref': observation_ref}
        source_ref, artifact_ref = publish_result(ctx, receipt)
        sources.append(source_ref)
        artifacts.append(artifact_ref)
        result_ref = ledger.put('result', {**receipt, 'source_ref': source_ref})
        if (row['state'] == 'complete' and row.get('returncode') == 0
                and accepts(document, commission['obligations'][unit['obligation_id']])):
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
        export_closed(ctx, ledger, plan)
    result = {'accepted': accepted, 'rejected': failures, 'observation_ref': observation_ref,
              'credit': ledger.credit_view()}
    return result, sources + artifacts, {'result_source_refs': sources, 'result_artifact_refs': artifacts}


def order_body(ctx, ledger, plan, target, candidate, operation):
    """The old ``AllocationOrder._order_original_units``: only original unit ids, written through the native
    allocation control."""
    allowed = {unit['unit_id'] for unit in candidate['units']}
    if not set(operation['unit_ids']) <= allowed:
        raise ValueError('only_original_work_units_can_be_selected')
    result = ctx.services['job_access'].write_allocation_control(target, unit_ids=operation['unit_ids'],
                                                                 key=ctx.operation_key)
    ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': ctx.operation_key,
                                    'unit_ids': operation['unit_ids'], 'receipt': result})
    return result


def allocation_work(ctx, ledger, tool, operation, arguments):
    """The old ``AllocationHandoff._work_on_original_allocation``: monitor, results and order work on the plan's
    original allocation, after its handoff is attached."""
    plan = ledger.read(operation['plan_ref'])
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff')):
        raise AttachmentMissing
    target = allocation_target(ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    if tool == 'hpc_allocation_order':
        return order_body(ctx, ledger, plan, target, candidate, operation)
    observation, allocation, window, observation_ref, current, measured_ref = observe_allocation(
        ctx, ledger, plan, target, candidate, ctx.operation_key)
    if tool == 'hpc_monitor':
        return update_conditional_forecast(ctx, ledger, operation, plan, target, candidate, observation_ref, current,
                                           measured_ref, ctx.operation_key)
    return collect_original_results(ctx, ledger, arguments['scope'], plan, target, candidate, allocation,
                                    observation_ref, current, measured_ref)


def allocation_tool(tool, arguments, ctx):
    ledger = open_ledger(ctx, arguments)
    try:
        result = allocation_work(ctx, ledger, tool, arguments['operation'], arguments)
    except AttachmentMissing:
        return invalid_outcome(
            ledger, 'original_handoff_not_attached',
            recovery='If Launch already completed, attach the handoff its return carries with hpc_handoff. Do not '
                     'launch replacement work.')
    except (ValueError, KeyError, TypeError, OSError) as error:
        return invalid_outcome(ledger, error)
    if isinstance(result, tuple):
        result, references, extra = result
        return outcome_of(ledger, 'completed', result, references, extra=extra)
    return outcome_of(ledger, 'completed', result)


def hpc_monitor(arguments, ctx):
    return allocation_tool('hpc_monitor', arguments, ctx)


def hpc_results(arguments, ctx):
    return allocation_tool('hpc_results', arguments, ctx)


def hpc_allocation_order(arguments, ctx):
    return allocation_tool('hpc_allocation_order', arguments, ctx)


async def hpc_monitor_wait(arguments, ctx):
    """The old ``HPCActivityAdvice._wait_for_original_observation``: through the attached monitor controller,
    schedule the next observation, wait, observe the original job once. A terminal job or ready outputs mean
    collect now. Scheduling earns no credit."""
    ledger = open_ledger(ctx, arguments)
    operation = arguments['operation']
    try:
        plan = ledger.read(operation['plan_ref'])
        if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff')):
            raise AttachmentMissing
        if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor_controller')):
            return invalid_outcome(
                ledger, 'hpc_monitor_controller_not_attached',
                next_step='This original commission has no attached monitor controller. Use hpc_monitor on the '
                          'original plan, then hpc_results when its outputs are ready. Retain the original '
                          'submitted job; do not launch replacement work.')
        target = allocation_target(ctx, ledger, plan)
        candidate = candidate_of(ledger, plan)
        controller = monitor_controller(ledger)
        if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor')):
            # The first observation of the original job, as the old ``execute('hpc.monitor', ...)`` under
            # ``operation_key + ':initial-monitor'``.
            key = ctx.operation_key + ':initial-monitor'
            observation_ref, current, measured_ref = observe_allocation(ctx, ledger, plan, target, candidate, key)[3:]
            update_conditional_forecast(ctx, ledger, {'refresh_queue': True}, plan, target, candidate,
                                        observation_ref, current, measured_ref, key)
        monitor = last_forecast(ledger, plan)
        ready = uncollected_completed_unit_ids(ledger, plan, monitor['conditional_prediction'])
        if monitor['conditional_prediction']['telemetry']['state'] in ('complete', 'failed'):
            result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_terminal_job_collect_now'}
        elif ready:
            result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_unit_outputs_collect_now',
                      'ready_unit_ids': sorted(ready)}
        else:
            schedule = controller.reserve(plan, candidate, monitor, ctx.operation_key)
            if schedule['job_id'] != target['execution_id']:
                raise ValueError('monitor_schedule_original_job_conflict')
            if schedule['valuation']['schedule']:
                await controller.wait(schedule)
                key = ctx.operation_key + ':monitor'
                observation_ref, current, measured_ref = observe_allocation(
                    ctx, ledger, plan, target, candidate, key)[3:]
                observed = update_conditional_forecast(ctx, ledger, {'refresh_queue': True}, plan, target, candidate,
                                                       observation_ref, current, measured_ref, key)
                ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'],
                                            'job_id': target['execution_id'], 'observed': observed},
                           identity='wake:' + ctx.operation_key)
                result = {'schedule': schedule, 'monitor': observed}
            else:
                result = {'schedule': schedule, 'monitor': None}
    except AttachmentMissing:
        return invalid_outcome(ledger, 'original_handoff_not_attached')
    except (ValueError, KeyError, TypeError, OSError) as error:
        return invalid_outcome(ledger, error)
    return outcome_of(ledger, 'completed', result)


TOOLS = {'hpc_read': hpc_read, 'hpc_compare': hpc_compare, 'hpc_history_refresh': hpc_history_refresh,
         'hpc_discovery_run': hpc_discovery_run, 'hpc_candidate_propose': hpc_candidate_propose,
         'hpc_queue_observe': hpc_queue_observe, 'hpc_plan': hpc_plan, 'hpc_handoff': hpc_handoff,
         'hpc_monitor': hpc_monitor, 'hpc_monitor_wait': hpc_monitor_wait, 'hpc_results': hpc_results,
         'hpc_allocation_order': hpc_allocation_order}


# ---------------------------------------------------------------------------------------------------------------
# Deciding.

def activity_advice(hpc):
    """The old ``HPCActivityAdvice.activity_advice``, from the ledger state instead of the old estimator's
    diagnostics: ``collect`` when an open plan with a monitor controller has a terminal job or ready outputs,
    else ``wait``; ``None`` without an attached controller."""
    if not hpc['monitor_controllers']:
        return None
    collect = any(row['terminal'] or row['ready_unit_ids'] for row in hpc['pending_collect'].values())
    mode = 'collect' if collect else 'wait'
    tool = 'hpc_results' if collect else 'hpc_monitor_wait' if hpc['latest_monitor'] else 'hpc_monitor'
    return {'mode': mode, 'suggested_tool': tool}


def decision_context(summary, feedback, ctx):
    """The model's context (the old ``HPCSummary.decision_context`` and the generic decision state)."""
    settings = ctx.settings
    hpc = summary['hpc']
    commission = summary['commission']
    context = {
        'hpc_commission': commission, 'hpc_owner_episode_id': summary['owner_episode_id'],
        'hpc_candidates': hpc['candidates'], 'hpc_resource': settings['resources'][commission['resource_id']],
        'hpc_child_scope': summary['scope'], 'hpc_child_commission': summary['commission_identity'],
        'hpc_launch_deliveries': summary['launches'], 'hpc_tool_request': hpc['tool_requests'],
        'hpc_model_ref': hpc['model_ref'], 'hpc_credit': hpc['credit_view'],
        'hpc_latest_comparison': hpc['latest_comparison'], 'hpc_model_support': hpc['model_support'],
        'hpc_plans': [{'plan_ref': ref, 'candidate_id': plan['candidate_id']} for ref, plan in hpc['plans'].items()],
        'hpc_latest_monitor': hpc['latest_monitor'], 'hpc_monitor_controllers': hpc['monitor_controllers'],
        'hpc_activity_decision': activity_advice(hpc), 'hpc_queue_refs': hpc['queue_refs'],
        'hpc_available_training_ids': hpc['available_training_ids'],
        'current_credit': hpc['credit_view']['credit'], 'credit_binding': {'kind': 'operational',
                                                                         'components': ['actual', 'model', 'validation']},
        'received_progress': {'refs': summary['received_progress_refs'],
                              'snapshots': summary['received_progress_snapshots']},
        'time_accounting': time_accounting(ctx.clock.progress_time), 'actions': summary['actions'],
        'last_local_outcome': summary['last_outcome'], 'feedback': feedback, 'tools': catalog(settings),
        # BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: the read below. No such service exists yet.
        'resource_tool_estimates': ctx.services['estimate_table'].read('resource_tool_estimates', 'hpc_execution')}
    if settings.get('shared_execution_memory'):
        context['hpc_shared_memory'] = True
        context['hpc_shared_history_refs'] = hpc['shared_history_refs']
    if summary['action_yields'] is not None:
        context['action_yields'] = summary['action_yields']
    if 'tool_knowledge_directory' in settings:
        context['tool_knowledge'] = ToolKnowledge(settings['tool_knowledge_directory']).context()
    if 'launch_instructions_directory' in settings:
        library = LaunchInstructions(settings['launch_instructions_directory'])
        context['launch_instruction_library'] = library.context()
        context['selected_launch_instructions'] = library.materialize(summary['launch_instructions'])
    elif summary['launch_instructions'] is not None:
        raise ValueError('launch_instructions_directory_required_for_a_launch_instruction_selection')
    return context


def instructions(settings):
    """The old ``task_instructions.instructions``: the goal text and, when present, the tool-knowledge and the
    launch-library texts. The text about pending children, redelivery, the wait action and native event targets
    described actions that no longer exist and is not carried."""
    text = INSTRUCTIONS
    if 'tool_knowledge_directory' in settings:
        text += KNOWLEDGE_INSTRUCTIONS
    if 'launch_instructions_directory' in settings:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    if not summary['hpc_loaded']:
        # The initial lookup of this task, offered through its own tool: the ledger's owner record. Its outcome
        # carries the ledger state (plans, candidates, models, queue observations) the old decision showed first.
        return ToolCall('hpc_read', {'operation': {'reference': 'owner'}, 'scope': summary['scope'],
                                     'ledger': summary['ledger'],
                                     'owner_episode_id': summary['owner_episode_id']})
    context = decision_context(summary, feedback, ctx)
    return ModelRequest('REASONING', instructions(ctx.settings), context, generation_schema(action_schema(ctx.settings)))


def action(response, summary, records, ctx):
    """The one tool or child the model chose. An answer that selects no offered unit, or names a record this
    Episode does not hold, creates no unit: the model decides again with the feedback."""
    schema = action_schema(ctx.settings)
    try:
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    arguments = selection['arguments']
    hpc = summary['hpc']
    if selection['kind'] == 'tool':
        if selection['tool'] == 'hpc_handoff' and not records.holds(arguments['handoff_ref']):
            raise Rejected(rejection_feedback(ValueError('handoff_not_received'), category='arguments_or_reference'))
        return ToolCall(selection['tool'], {'operation': arguments, 'owner_episode_id': summary['owner_episode_id'],
                                            'ledger': summary['ledger'],
                                            'scope': summary['scope']})
    slot = selection['slot']
    if slot == 'monitor':
        return ChildCall('monitor', {'assignment': arguments['assignment'],
                                     'information_unit': ctx.settings['monitor_information_unit']})
    plan = hpc['plans'].get(arguments['plan_ref'])
    if plan is None:
        raise Rejected(rejection_feedback(ValueError('unknown_hpc_plan_ref:' + arguments['plan_ref']),
                                          category='arguments_or_reference'))
    if slot == 'launch':
        if plan['plan_id'] in hpc['closed']:
            raise Rejected(rejection_feedback(ValueError('hpc_allocation_already_closed'),
                                              category='arguments_or_reference'))
        if plan['plan_id'] not in hpc['launch_inputs']:
            raise Rejected(rejection_feedback(ValueError('hpc_launch_input_not_staged_for_plan'),
                                              category='arguments_or_reference'))
        if any(row['plan_ref'] == arguments['plan_ref'] for row in summary['launches']):
            raise Rejected(rejection_feedback(ValueError('hpc_launch_must_match_original_planned_portfolio'),
                                              category='arguments_or_reference'))
        return ChildCall('launch', {'plan_ref': arguments['plan_ref']})
    if plan['plan_id'] not in hpc['handoffs']:
        raise Rejected(rejection_feedback(ValueError('original_handoff_not_attached'),
                                          category='arguments_or_reference'))
    return ChildCall('results', {'plan_ref': arguments['plan_ref'], 'selector': arguments['selector'],
                                 'acquired_record_unit': ctx.settings['acquired_record_unit']})
