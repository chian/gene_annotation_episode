"""The task: the execution of the HPC parent's commission, one operation or one child commission per unit.

The units are the old ``HPCWorkOperations.catalog`` (``hpc.read``, ``hpc.compare``, ``hpc.history.refresh``,
``hpc.discovery.run``, ``hpc.candidate.propose``, ``hpc.queue.observe``, ``hpc.plan``, ``hpc.handoff``,
``hpc.monitor``, ``hpc.monitor.wait``, ``hpc.results``, ``hpc.allocation.order``; each is a tool, the dots of the
old names are underscores) and the commissions of the launch, monitor and results children. The first unit is the
lookup of the ledger's decision state (``hpc_state``, with the old ``initialize``): the model chooses afterwards. The
task always offers a unit and never ends the Episode: the yield controller stops it. The old decision machine
(``HPCWorkTask.next``, ``call``, ``apply_response``, ``execute``, the decision exchange, the ``reason``, ``wait`` and
``redeliver_report`` actions, saved decision exchanges, checkpoints) is the system's loop now; the old report and
redelivery guidance of ``task_instructions`` described actions that no longer exist and is not carried.

BLOCKED-ON-JOB-SERVICE (LAUNCH_MONITOR_EXTRACT_MECHANICS.md, section 5 and "Not provided yet" items 2, 4 and 5): no
service exists yet for what the old episode reached through its configuration and the files beside the Store. The
episode names three services, and each call raises ``NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')`` where the
service does not offer it:

* ``hpc_ledger``: the ledger of the commissioned HPC parent that the parent and its sisters share (old
  ``HPCLedger.open_existing(directory / 'hpc' / digest([run_id, owner]))``): ``open(owner_episode_id, scope,
  commission)`` returns the ledger (``read``, ``records``, ``put``, ``once``, ``cached``, ``save_action``,
  ``freeze``, ``score``, ``accept``, ``credit_view``, ``commission``, ``path`` as the old class had them), and
  ``stage_launch_input(plan)`` writes the frozen plan as the launch child's supplied input file;
* ``job_access``: the scheduler, the transport and the original job's files (old ``hpc_queue.observe``, the
  ``ssh_argv`` subprocess of discovery, ``ExecutionTargetReader`` of ``execution_progress`` and its transports):
  ``observe_queue``, ``run_command``, ``read_target``, ``observe_target``, ``read_file``, ``write_allocation_control``;
* ``estimate_table``: the shared execution memory of earlier runs (old ``ExecutionMemory``): ``history``, ``latest``,
  ``observe``, ``record``, ``as_record``.

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id, old ``self.resources``),
``shared_execution_memory`` (optional: the old ``shared_execution_memory`` operands; its presence turns on
``hpc_history_refresh`` and the memory reads), ``launch_instructions_directory``, ``tool_knowledge_directory``, and
``cost`` and ``parameters`` (read by ``yield_estimator.py``)."""
import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc_campaign import (
    accepts, bind_progress, build_plan, incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc_history import (
    closed_measurement)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc_monitoring import (
    MonitorCronController)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc_resource_prediction import (
    forecast_metric, pbs_resource_metrics, physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.evolutionary_history_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    ContractError, RECORD_SCHEMAS, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

_ROOT = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/'
CHILD_SLOTS = {'launch': _ROOT + 'execution_job_submission', 'monitor': _ROOT + 'execution_progress_assessment',
               'results': _ROOT + 'execution_result_acquisition'}
SERVICES = ('hpc_ledger', 'job_access', 'estimate_table')

TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}
PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'
# The exposed fields of one monitor commission (the monitor child's own ``FIELD_OPTIONS``).
MONITOR_FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
                  'result_available')

# The old tool names, which the ledger keeps in its own records (a monitor schedule's ``wake_action``).
LEDGER_NAMES = {'hpc_read': 'hpc.read', 'hpc_compare': 'hpc.compare', 'hpc_history_refresh': 'hpc.history.refresh',
                'hpc_discovery_run': 'hpc.discovery.run', 'hpc_candidate_propose': 'hpc.candidate.propose',
                'hpc_queue_observe': 'hpc.queue.observe', 'hpc_plan': 'hpc.plan', 'hpc_handoff': 'hpc.handoff',
                'hpc_monitor': 'hpc.monitor', 'hpc_monitor_wait': 'hpc.monitor.wait',
                'hpc_results': 'hpc.results', 'hpc_allocation_order': 'hpc.allocation.order'}

INSTRUCTIONS = (
    'Iterate toward the original accomplishment while balancing expected credit against real elapsed time and '
    'resource demand. The hpc parent can commission prediction and execution as sisters: prediction fits/measures/'
    'compares; execution prepares, launches, monitors and parses the selected work. Both carry the hpc parent '
    'owner_episode_id and inherit exactly the hpc parent scope, including an empty subject_refs list for an '
    'operational task with no biological inputs. Candidate IDs, model IDs, queue observations and resource IDs are '
    'not biological subject_refs. Use the shared current model and comparisons; resource observations and candidate '
    'requests are different quantities. If suitable history is available, a prediction iteration can improve sizing '
    'before launching. No historical validation support means no invented model-improvement credit. Queue/setup '
    'costs belong to an allocation, which should carry enough useful work. When candidates are absent, discover the '
    'remote environment and documentation with hpc_discovery_run, then design candidate portfolios with '
    'hpc_candidate_propose. Discover is for lightweight inspection; leave installation and file staging to Launch, '
    'and scientific computation to the actual allocation. You choose the real inputs, database, executable '
    'commands, resources, worker code and preparation instructions. Never fabricate inputs or receipts. Every work '
    'unit writes result.json and progress.json under os.environ["HPC_UNIT_DIRECTORY"], its original per-unit '
    'working directory. The allocation workspace is for staged inputs, not these unit outputs; its fields must '
    'satisfy the caller acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. Candidate files use '
    'relative paths; {allocation_workspace} expands in files, argv, environment and preparation. Compute commands '
    'must run on allocated compute nodes using the facility launcher. Compare portfolios using current queue '
    'features and measured history. A plan freezes its original forecast, scientific manifest and acceptance '
    'criteria. Commission launch with that frozen plan (its plan_ref): the commission is the actual job and '
    'resource. The execution agent chooses its scripts, environment and operational commands from the supplied '
    'resource instructions and observations. Supplied reference sources are available in the local input file; do '
    'not transcribe them into a child goal or prescribe a setup/submit sequence. A launch commission returns the '
    'received original handoff; attach it to its plan with hpc_handoff. Use hpc_monitor once when another '
    'observation can affect your decision; it revises conditional predictions and attainable credit. Use '
    'hpc_results directly for known parsing. Commission monitor/results children only for actual investigation. '
    'Completed unit outputs can await parsing while PBS is still running or cleaning up: use hpc_results for those '
    'original outputs; completion is not acceptance. When hpc_monitor_controllers is present, select '
    'hpc_monitor_wait for a scheduled observation: its attached controller evaluates the conditional forecast, '
    'persists a wake time, and executes the original monitor at that time. This preserves pending accomplishment '
    'value across waits without credit for sleeping. The timer cannot turn into another unobserved wait. Do not '
    'poll for credit or duplicate a submitted attempt. Never replace an uncertain submission. Accepted '
    'accomplishment, model improvement, and fixed prospective forecast validation are the only credit components; '
    'launch-local credits are not added again.\n')
ACTION_BOUNDARY = ('Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, '
                   'term or observation.\n')
HOST_EXECUTION_GUIDANCE = 'Do not execute native provider tools. The host executes your selected action.\n'
ANSWER_INSTRUCTION = (' Answer with one selection: {kind: tool, tool, arguments} for one operation, or {kind: '
                      'episode_child, role (launch, monitor or results), assignment} for one child commission.')


# -- the services this episode names and where they are not provided yet ---------------------------------------

def _member(service, name, member, wanted):
    if not hasattr(service, member):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: %s.%s; wanted call: %s' % (name, member, wanted))
    return getattr(service, member)


def _job(ctx, member, wanted):
    return _member(ctx.services['job_access'], 'job_access', member, wanted)


def _memory(ctx):
    """The shared execution memory, when the run configures one (old ``self.memory``)."""
    if ctx.settings.get('shared_execution_memory') is None:
        return None
    return ctx.services['estimate_table']


def _memory_call(ctx, member, wanted):
    return _member(ctx.services['estimate_table'], 'estimate_table', member, wanted)


def _ledger(ctx, episode):
    """The old ``PortfolioState.state``: the owner's ledger of this commission and scope."""
    opener = _member(ctx.services['hpc_ledger'], 'hpc_ledger', 'open',
                     "ctx.services['hpc_ledger'].open(episode['owner_episode_id'], episode['scope'], "
                     "episode['commission'])")
    return opener(episode['owner_episode_id'], episode['scope'], episode['commission'])


# -- ledger readers (the old mix-ins' helpers; library candidates) ----------------------------------------------

def _candidates(ledger):
    return ledger.commission['candidates'] + [row['body'] for row in ledger.records('candidate')]


def _candidate(ledger, plan):
    return next(row for row in _candidates(ledger) if row['id'] == plan['candidate_id'])


def _features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def _current_model(ledger):
    records = ledger.records('model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'


def _accepted(ledger):
    return [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
            if row['kind'] == 'actual']


def _history(ledger):
    rows = {row['id']: row for row in ledger.commission['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()} - {None}
    for snapshot in ledger.records('shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    # Keep one latest observation per actual allocation, not one training example per poll. Failed unfinished work
    # retains a censored duration.
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


def _queue(ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def _collected_unit_ids(ledger, plan):
    return {row['body']['unit']['unit_id'] for row in ledger.records('result')
            if row['body'].get('plan_id') == plan['plan_id'] and isinstance(row['body'].get('unit'), dict)
            and isinstance(row['body']['unit'].get('unit_id'), str)}


def _uncollected_completed_unit_ids(ledger, plan, current):
    allowed = {unit['unit_id'] for unit in _candidate(ledger, plan)['units']}
    observed = set(current.get('telemetry', {}).get('completed_unit_ids', ()))
    return (observed & allowed) - _collected_unit_ids(ledger, plan)


def _last_forecast(ledger, plan):
    monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
    if monitors:
        return monitors[-1]
    forecasts = [row for row in ledger.records('forecast') if row['body']['plan_id'] == plan['plan_id']]
    return {'conditional_prediction': plan['original_prediction'], 'forecast_ref': forecasts[0]['id']}


def _handoff_ref(ledger, plan):
    rows = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']]
    return rows[-1]['handoff_ref'] if rows else None


# -- the decision state (old ``HPCSummary.decision_context``) ---------------------------------------------------

def _state(ctx, ledger, episode):
    """What the model is shown of the ledger, read after the effect of a unit; ``hpc_credit`` is the ledger's credit
    view (the credit of this Episode) and ``hpc_result_refs`` the result sources this Episode holds."""
    commission = ledger.commission
    current = _current_model(ledger)
    credit = ledger.credit_view()
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    plans = [{'plan_ref': row['id'], 'plan_id': row['body']['plan_id'], 'candidate_id': row['body']['candidate_id'],
              'launch_assignment': row['body']['launch_assignment'], 'manifest': row['body']['manifest'],
              'handoff_ref': _handoff_ref(ledger, row['body']), 'closed': row['body']['plan_id'] in closed}
             for row in ledger.records('plan')]
    results = [row['body']['source_ref'] for row in ledger.records('result')
               if ctx.store.holds(row['body']['source_ref'])]
    state = {'hpc_commission': commission, 'hpc_owner_episode_id': ledger.read('owner')['episode_id'],
             'hpc_candidates': _candidates(ledger), 'hpc_resource': ctx.settings['resources'][commission['resource_id']],
             'hpc_child_scope': plain(episode['scope']), 'hpc_child_commission': episode['commission'],
             'hpc_tool_request': [row['body'] for row in ledger.records('tool_request')],
             'hpc_model_ref': current, 'hpc_credit': credit,
             'hpc_latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                       if key not in ('episode_id', 'operation_key')}}
                                       for row in ledger.records('comparison')[-1:]],
             'hpc_model_support': prediction.predict(ledger.read(current), {})['support'],
             'hpc_plans': plans, 'hpc_latest_monitor': ledger.records('monitor')[-1:],
             'hpc_monitor_controllers': ledger.records('monitor_controller'),
             'hpc_queue_refs': [row['id'] for row in ledger.records('queue')],
             'hpc_accepted_obligations': [row['slot'].removeprefix('actual:') for row in credit['contributions']
                                          if row['kind'] == 'actual'],
             'hpc_result_refs': results,
             'hpc_available_training_ids': sorted(set(_history(ledger)) - set(commission['validation_ids']))}
    if ctx.settings.get('shared_execution_memory') is not None:
        state['hpc_shared_memory'] = ctx.settings['shared_execution_memory']
        state['hpc_shared_history_refs'] = [row['id'] for row in ledger.records('shared_history')]
    return state


def _shared_history(ctx, ledger):
    """The old ``MeasuredHistory._shared_history``: age-weighted shared timing history from the memory."""
    commission = ledger.commission
    configuration = ctx.settings['resources'][commission['resource_id']]
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], configuration)
    history = _memory_call(ctx, 'history', "ctx.services['estimate_table'].history(query, now=now, queue_only=True)")
    # Queue timing is resource-wide. Work timing requires explicit matching algorithm, parameters, software and
    # hardware, never just 'Aurora'.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in history(query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in history(profile, now=now)})
    queues = {candidate['queue'] for candidate in _candidates(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        queue = row.get('queue')
        # Different PBS queues are not interchangeable. Pool only when the portfolio has one matching queue, or the
        # model explicitly carries its categorical indicator.
        if 'queue' in row['metrics'] and not (queue and (queues == {queue} or 'queue:' + queue in model_features)):
            row['metrics'].pop('queue')
        if queue:
            row['features']['queue:' + queue] = 1.
        if row['metrics'] or row['success'] is not None:
            filtered.append(row)
    original = {row['id'] for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in commission['history']} - {None}
    policy = _memory_call(ctx, 'as_record', "ctx.services['estimate_table'].as_record()")()['policy']
    return {'captured_at': now, 'policy': policy,
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts][:2000]}


def _initialize(ctx, ledger):
    """The old ``PortfolioState.initialize``: the reference model, and the model fitted on the shared history."""
    prior = prediction.prior_model(ledger.commission['model'])
    ledger.put('model', prior, identity='reference_model')
    if _memory(ctx) is not None:
        imported = ledger.once('shared_history_entry', 'shared_history', lambda: _shared_history(ctx, ledger))
        if imported['observations'] and not ledger.records('model_choice'):
            model = prediction.fit(ledger.commission['model'], imported['observations'])
            reference = ledger.put('model', model)
            ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')


# -- the operations (each old method of the work-operations mix-ins) ---------------------------------------------

def _invalid(code, recovery=None):
    feedback = {'category': 'arguments_or_reference', 'code': code}
    if recovery is not None:
        feedback['recovery'] = recovery
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': feedback}


def _completed(references, result):
    return {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}


def _read_evidence(ctx, ledger, reference):
    """The old ``ReceivedEvidence.read_evidence``: a history row or a ledger record by its exact identity, or a
    result Source this Episode holds and the ledger owns (custody replaces the old received-reference check)."""
    history = _history(ledger)
    if reference in history:
        return history[reference]
    if not reference.startswith('source_'):
        return ledger.read(reference)
    rows = [row['body'] for row in ledger.records('result') if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or not ctx.store.holds(reference):
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    if source.get('provider') != 'episode.hpc_result' or not ctx.store.holds(source['artifact_ref']):
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


def _read_retained(ctx, ledger, arguments, references):
    try:
        result = _read_evidence(ctx, ledger, arguments['reference'])
    except (ValueError, KeyError) as error:
        return _invalid(str(error))
    return _completed(references, result)


def _comparisons(ledger, model_ref, queue_ref):
    model = ledger.read(model_ref)
    observed = _queue(ledger, queue_ref)
    actual = _accepted(ledger)
    results = []
    for candidate in _candidates(ledger):
        queue = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, _features(candidate, queue))
        row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                 ledger.commission['preferences'], already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def _compare_portfolios(ctx, ledger, arguments, references, key):
    try:
        result = {'comparisons': _comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
    except (ValueError, KeyError) as error:
        return _invalid(str(error), 'Use a model_ref from hpc.model.fit or hpc_model_ref and a queue_ref from '
                                    'hpc_queue_observe or hpc_queue_refs; a resource identity is not a queue '
                                    'observation.')
    result['comparison_ref'] = ledger.put('comparison', {**result, **arguments, 'episode_id': ctx.episode_id,
                                                         'operation_key': key})
    return _completed(references, result)


def _refresh_measured_history(ctx, ledger, key, references):
    result = ledger.once('shared_history:' + key, 'shared_history', lambda: _shared_history(ctx, ledger))
    return _completed(references, result)


def _observe_queue(ctx, ledger, configuration):
    """The old ``QueueObservations._observe_queue``: a fresh enough memory entry, else one acquisition."""
    commission = ledger.commission
    resource = resource_identity(commission['resource_id'], configuration)
    memory = _memory(ctx)
    if memory is not None:
        cached = _memory_call(ctx, 'latest', "ctx.services['estimate_table'].latest(resource, 'queue')")(
            resource, 'queue')
        if cached['state'] == 'fresh' and cached['age_seconds'] <= commission['limits']['queue_max_age_seconds']:
            return cached['data']
    value = _job(ctx, 'observe_queue', "ctx.services['job_access'].observe_queue(resource_id)")(
        commission['resource_id'])
    if memory is not None:
        _memory_call(ctx, 'observe', "ctx.services['estimate_table'].observe(resource, 'queue', value, "
                                     "observed_at=, provenance=)")(
            resource, 'queue', value, observed_at=value['snapshot']['captured_at'], provenance=value['acquisition'])
    return value


def _observe_resource_queue(ctx, ledger, configuration, references, key):
    reference = 'queue:' + hpc_queue.digest(key)
    result = ledger.once(reference, 'queue', lambda: _observe_queue(ctx, ledger, configuration))
    result = {'queue_ref': reference, 'snapshot': result['snapshot'],
              'features': [hpc_queue.features(result['snapshot'], candidate) for candidate in _candidates(ledger)]}
    return _completed(references, result)


async def _discover_resource(ctx, ledger, arguments, commission, configuration, references, key):
    command = 'cd ' + shlex.quote(PROJECT_DIRECTORY) + ' && ' + arguments['command']

    def observe():
        cache_key = resource_identity(commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
        memory = _memory(ctx)
        if memory is not None:
            cached = _memory_call(ctx, 'latest', "ctx.services['estimate_table'].latest(cache_key, 'inventory')")(
                cache_key, 'inventory')
            if cached['state'] == 'fresh':
                return cached['data']
        completed = _job(ctx, 'run_command', "ctx.services['job_access'].run_command(resource_id, command)")(
            commission['resource_id'], command)
        value = {'command': arguments['command'], 'returncode': completed['returncode'],
                 'stdout': completed['stdout'][:65536].decode('utf-8', 'replace'),
                 'stderr': completed['stderr'][:8192].decode('utf-8', 'replace'), 'observed_at': time.time(),
                 'truncated': len(completed['stdout']) > 65536}
        if memory is not None and completed['returncode'] == 0:
            _memory_call(ctx, 'observe', "ctx.services['estimate_table'].observe(cache_key, 'inventory', value, "
                                         "observed_at=, provenance=)")(
                cache_key, 'inventory', value, observed_at=value['observed_at'],
                provenance=[str(ledger.path), 'discovery:' + key])
        return value
    result = await asyncio.to_thread(ledger.once, 'discovery:' + key, 'discovery', observe)
    return _completed(references, result)


def _propose_portfolio(ctx, ledger, arguments, commission, references):
    try:
        candidate = json.loads(arguments['candidate_json'])
        candidates = _candidates(ledger)
        prior = next((row for row in candidates if row['id'] == candidate['id']), None)
        if prior is not None and prior != candidate:
            raise ValueError('candidate_identity_is_immutable')
        validate_commission({**commission, 'candidates': candidates if prior else candidates + [candidate]},
                            ctx.settings['resources'])
    except (ValueError, KeyError, TypeError) as error:
        return _invalid(str(error))
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates']
                 else ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return _completed(references, {'candidate_ref': reference, 'candidate_id': candidate['id']})


def _freeze(ledger, plan, predicted, reference, current, phase, key):
    elapsed = {'queue': current.get('queue_elapsed_seconds', 0.), 'work': current.get('work_elapsed_seconds', 0.)}
    slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
             if slot['phase'] == phase and elapsed.get(slot['metric'], elapsed['work']) >= slot['minimum_elapsed_seconds']
             and forecast_metric(predicted, slot['metric']) is not None]
    body = ledger.once('issued:' + key, 'forecast_issue', lambda: {
        'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted, 'reference': reference,
        'phase': phase, 'elapsed': elapsed, 'model_ref': plan.get('model_ref'),
        'prediction_episode_id': plan.get('prediction_episode_id')})
    return ledger.freeze(body, slots)


def _freeze_portfolio_plan(ctx, ledger, arguments, commission, configuration, references, key):
    existing = ledger.records('plan')
    own = next((row for row in existing if row['body'].get('operation_key') == key), None)
    if own is not None:
        plan = own['body']
        forecast_ref = _freeze(ledger, plan, plan['original_prediction'], plan['original_reference'], {}, 'planned',
                               key)
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                'result': {'plan_ref': own['id'], 'forecast_ref': forecast_ref,
                           **{name: value for name, value in plan.items() if name != 'prediction_episode_id'}}}
    observed = _queue(ledger, arguments['queue_ref'], require_fresh=True)
    candidate = next(row for row in _candidates(ledger) if row['id'] == arguments['candidate_id'])
    queue = hpc_queue.features(observed, candidate)
    rules = queue['queue_rules']
    if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
        raise ValueError('choose_an_observed_enabled_execution_queue')
    for name, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
        if (rules['min_' + name] is not None and value < rules['min_' + name]
                or rules['max_' + name] is not None and value > rules['max_' + name]):
            raise ValueError('candidate_violates_observed_queue_limits')
    plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
    features = _features(candidate, queue)
    predicted = prediction.predict(ledger.read(arguments['model_ref']), features)
    reference = prediction.predict(ledger.read('reference_model'), features)
    plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'], original_prediction=predicted,
                original_reference=reference, operation_key=key)
    choices = [row['body'] for row in ledger.records('model_choice') if row['body']['model_ref'] == arguments['model_ref']]
    plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
    plan_ref = ledger.put('plan', plan)
    forecast_ref = _freeze(ledger, plan, predicted, reference, {}, 'planned', key)
    # The old ``LaunchPreparation.initial_decision_context`` wrote the frozen plan as the launch child's supplied
    # input file beside the ledger: a file outside custody, staged by the ledger's service.
    stage = _member(ctx.services['hpc_ledger'], 'hpc_ledger', 'stage_launch_input',
                    "ctx.services['hpc_ledger'].stage_launch_input(plan)")
    result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref, 'supplied_input_file': stage(plan),
              **{name: value for name, value in plan.items() if name != 'prediction_episode_id'}}
    return _completed(references, result)


def _attach_original_handoff(ctx, ledger, arguments, commission, references):
    plan = ledger.read(arguments['plan_ref'])
    handoff_ref = arguments['handoff_ref']
    if not ctx.store.holds(handoff_ref):
        return _invalid('handoff_not_received')
    target = _read_target(ctx, handoff_ref)
    if target['assignment'] != plan['practical_assignment']:
        return _invalid('handoff_does_not_match_frozen_portfolio')
    ledger.put('handoff', {'handoff_ref': handoff_ref, 'job_id': target['execution_id'], 'plan_id': plan['plan_id']},
               identity='handoff:' + plan['plan_id'])
    result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
    if 'monitoring' in commission:
        result['monitor_controller_ref'] = MonitorCronController(ledger).attach(
            plan, target['execution_id'], commission['monitoring'])
    return _completed(references, result)


def _read_target(ctx, handoff_ref):
    """The old ``ExecutionTargetReader.read_target(handoff_ref, scope)``: the job the held handoff record names. The
    record is read through custody; what the job access makes of it is its own."""
    record = ctx.store.get(handoff_ref)
    reader = _job(ctx, 'read_target', "ctx.services['job_access'].read_target(handoff_ref, record)")
    return reader(handoff_ref, record)


def _target(ctx, ledger, plan):
    handoff = ledger.read('handoff:' + plan['plan_id'])
    if not ctx.store.holds(handoff['handoff_ref']):
        raise ValueError('original_handoff_not_received_by_this_parent')
    target = _read_target(ctx, handoff['handoff_ref'])
    if target['assignment'] != plan['practical_assignment']:
        raise ValueError('handoff_does_not_match_frozen_portfolio')
    return target


def _window(ctx, target, path, limit, key):
    reader = _job(ctx, 'read_file', "ctx.services['job_access'].read_file(target, path=, offset=0, limit=, "
                                    "key=ctx.operation_key)")
    value = reader(target, path=path, offset=0, limit=limit + 1, key=key)
    payload = base64.b64decode(value['bytes_base64'], validate=True)
    if len(payload) != value['size_bytes'] or len(payload) > limit:
        raise ValueError('compact_result_incomplete_or_too_large')
    return value, payload


def _allocation(ctx, target, plan, key):
    path = plan['manifest']['workspace'] + '/allocation-status.json'
    try:
        window, payload = _window(ctx, target, path, 512 * 1024, key)
    except (FileNotFoundError, ValueError) as error:
        # Absence before the runner starts is normal; other failures remain visible and do not manufacture a
        # progress estimate.
        return None, {'path': path, 'failure': str(error)}
    value = json.loads(payload)
    if (value['plan_id'] != plan['plan_id'] or value['job_id'] != target['execution_id']
            or value['manifest_sha256'] != plan['manifest_sha256']):
        raise ValueError('allocation_receipt_identity_conflict')
    expected = {unit['unit_id'] for unit in plan['manifest']['units']}
    if len({row['unit_id'] for row in value['units']}) != len(value['units']) or not {
            row['unit_id'] for row in value['units']} <= expected:
        raise ValueError('allocation_receipt_units_conflict')
    return value, window


def _measure(ledger, plan, observation, current, allocation):
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
        metrics['setup'] = {'seconds': max(0., allocation['started_at'] - current['started_at']), 'censored': False,
                            'observed_at': allocation['started_at']}
        if allocation.get('finished_at') is not None:
            metrics['work'] = {'seconds': allocation['finished_at'] - allocation['started_at'], 'censored': False,
                               'observed_at': allocation['finished_at']}
    measured = {'plan_id': plan['plan_id'], 'metrics': metrics, 'observed_at': now,
                'success': False if current['state'] == 'failed' else None}
    reference = ledger.put('measured', measured)
    ledger.score(reference)
    return reference


def _observe_original_allocation(ctx, ledger, plan, target, candidate, key):
    """The shared first half of ``hpc_monitor`` and ``hpc_results``: one status observation of the original job, the
    allocation's own status file, the current unit's progress, and the measurement of the outcome."""
    observer = _job(ctx, 'observe_target', "ctx.services['job_access'].observe_target(target, key=ctx.operation_key)")
    observation = ledger.once('status:' + key, 'native_status', lambda: observer(target, key=key))
    allocation, allocation_window = ledger.once('allocation:' + key, 'allocation_snapshot',
                                                lambda: list(_allocation(ctx, target, plan, key + ':allocation')))
    observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                                                 'allocation': allocation, 'allocation_window': allocation_window})
    current = telemetry(observation, allocation, candidate)
    if current.get('current_unit_id') is not None:
        unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
        if unit.get('reports_progress', False):
            progress_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/progress.json'
            try:
                progress_window = ledger.once('unit-progress:' + key, 'unit_progress',
                                              lambda: _window(ctx, target, progress_path, 16384, key + ':progress')[0])
                progress = bind_progress(json.loads(base64.b64decode(progress_window['bytes_base64'], validate=True)),
                                         plan['plan_id'])
                current = incorporate_progress(current, progress, candidate)
            except (OSError, ValueError, KeyError, TypeError) as error:
                current['progress_failure'] = str(error)
    prior_monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
    if prior_monitors:
        previous = prior_monitors[-1]['conditional_prediction']['telemetry']
        current['phase_changed'] = (previous.get('phase'), previous.get('current_unit_id')) != (
            current.get('phase'), current.get('current_unit_id'))
        dt = current['observed_at'] - previous['observed_at']
        if dt > 0 and 'completed_fraction' in current and 'completed_fraction' in previous:
            current['recent_fraction_per_second'] = max(
                0.0, current['completed_fraction'] - previous['completed_fraction']) / dt
    measured_ref = _measure(ledger, plan, observation, current, allocation)
    return observation, allocation, allocation_window, observation_ref, current, measured_ref


def _update_conditional_forecast(ctx, ledger, arguments, commission, configuration, references, key, plan, target,
                                 candidate, observation, observation_ref, current, measured_ref):
    refreshed = None
    queue_ref = plan['queue_ref']
    if arguments['refresh_queue']:
        queue_ref = 'queue:' + hpc_queue.digest(key)
        queue_value = ledger.once(queue_ref, 'queue', lambda: _observe_queue(ctx, ledger, configuration))
        queue = hpc_queue.features(queue_value['snapshot'], candidate, job_id=target['execution_id'])
        refreshed = prediction.predict(ledger.read(_current_model(ledger)), _features(candidate, queue))['times'][
            'queue']
    predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
    reference = prediction.update(plan['original_reference'], current)
    forecast_ref = _freeze(ledger, plan, predicted, reference, current, current['state'], key)
    orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
    ordered_candidate = deepcopy(candidate)
    if orders:
        units = {row['unit_id']: row for row in candidate['units']}
        first = [current['current_unit_id']] if current.get('current_unit_id') else []
        ids = list(dict.fromkeys([*first, *orders[-1]['unit_ids'], *units]))
        ordered_candidate['units'] = [units[identity] for identity in ids]
    result = {'plan_id': plan['plan_id'], 'observation_ref': observation_ref, 'measured_ref': measured_ref,
              'forecast_ref': forecast_ref, 'queue_ref': queue_ref, 'conditional_prediction': predicted,
              'remaining_work': prediction.compare(ordered_candidate, predicted, commission['obligations'],
                                                   commission['preferences']),
              'next_observation': 'Choose an event/elapsed threshold where changed evidence could alter a decision.'}
    ledger.put('monitor', result)
    return _completed(references, result)


def _publish(ctx, episode, body):
    """The old ``AllocationResults._publish``: one result Source, written through ``ctx.store`` (held as produced)."""
    artifact = ctx.store.artifact(hpc_queue.canonical(body), 'application/json')
    return ctx.store.put('source', {
        'provider': 'episode.hpc_result', 'accession': 'hpc_' + hpc_queue.digest([ctx.run_id, ctx.episode_id, body]),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': 'hpc_result_v1',
        'retrieved_at': datetime.fromtimestamp(body['unit']['finished_at'], timezone.utc).isoformat()},
        origin='tool')['id']


def _collect_original_results(ctx, ledger, episode, commission, references, key, plan, target, candidate,
                              allocation, observation_ref, current, measured_ref):
    accepted, failures = [], []
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
        window = ledger.once('result-window:' + key + ':' + unit['unit_id'], 'result_window',
                             lambda: _window(ctx, target, expected_path, commission['limits']['result_limit_bytes'],
                                             key + ':' + unit['unit_id'])[0])
        payload = base64.b64decode(window['bytes_base64'], validate=True)
        if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
            raise ValueError('result_changed_since_unit_completion')
        document = json.loads(payload)
        receipt = {'run_id': ctx.run_id, 'episode_id': ctx.episode_id, 'scope': plain(episode['scope']),
                   'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row, 'document': document,
                   'window': window, 'observation_ref': observation_ref}
        source_ref = _publish(ctx, episode, receipt)
        references.append(source_ref)
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
        _export_closed(ctx, ledger, plan)
    result = {'accepted': accepted, 'rejected': failures, 'observation_ref': observation_ref,
              'credit': ledger.credit_view()}
    return _completed(references, result)


def _export_closed(ctx, ledger, plan):
    """The old ``MeasuredHistory.export_closed``: a closed allocation's measurement enters the shared memory."""
    if _memory(ctx) is None:
        return
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('only_closed_allocations_enter_shared_history')
    measured = ledger.once('export_measurement:' + plan['plan_id'], 'export_measurement', lambda: [
        row for row in ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
    handoff = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']][-1]
    _memory_call(ctx, 'record', "ctx.services['estimate_table'].record(**closed_measurement(...))")(
        **closed_measurement(ledger.commission, plan, measured, handoff, resources=ctx.settings['resources'],
                             ledger=ledger.ledger))


def _order_original_units(ctx, ledger, arguments, references, key, plan, target, candidate):
    allowed = {unit['unit_id'] for unit in candidate['units']}
    if not set(arguments['unit_ids']) <= allowed:
        return _invalid('only_original_work_units_can_be_selected')
    control = _job(ctx, 'write_allocation_control',
                   "ctx.services['job_access'].write_allocation_control(target, unit_ids=, key=ctx.operation_key)")
    result = control(target, unit_ids=arguments['unit_ids'], key=key)
    ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': key,
                                    'unit_ids': arguments['unit_ids'], 'receipt': result})
    return _completed(references, result)


async def _wait_for_original_observation(ctx, ledger, episode, arguments, references, key, plan, target, candidate):
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor_controller')):
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'hpc_monitor_controller_not_attached',
                             'next_step': 'This original commission has no attached monitor controller. Use '
                                          'hpc_monitor on the original plan, then hpc_results when its outputs are '
                                          'ready. Retain the original submitted job; do not launch replacement '
                                          'work.'}}
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor')):
        await _execute(ctx, ledger, episode, 'hpc.monitor', {'plan_ref': arguments['plan_ref'],
                                                             'refresh_queue': True}, key + ':initial-monitor')
    monitor = _last_forecast(ledger, plan)
    ready = _uncollected_completed_unit_ids(ledger, plan, monitor['conditional_prediction'])
    if monitor['conditional_prediction']['telemetry']['state'] in ('complete', 'failed'):
        result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_terminal_job_collect_now'}
    elif ready:
        result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_unit_outputs_collect_now',
                  'ready_unit_ids': sorted(ready)}
    else:
        controller = MonitorCronController(ledger)
        schedule = controller.reserve(plan, candidate, monitor, key)
        if schedule['job_id'] != target['execution_id']:
            raise ValueError('monitor_schedule_original_job_conflict')
        if schedule['valuation']['schedule']:
            await controller.wait(schedule)
            observed = await _execute(ctx, ledger, episode, 'hpc.monitor',
                                      {'plan_ref': arguments['plan_ref'], 'refresh_queue': True}, key + ':monitor')
            ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'], 'job_id': target['execution_id'],
                                        'observed': observed}, identity='wake:' + key)
            result = {'schedule': schedule, 'monitor': observed['result']}
        else:
            result = {'schedule': schedule, 'monitor': None}
    return _completed(references, result)


# -- the catalogue and the dispatch -------------------------------------------------------------------------------

def catalog(settings):
    """The old ``HPCWorkOperations.catalog``: ``hpc.history.refresh`` is offered only with a shared memory."""
    shared = [('hpc.read', 'Read retained HPC evidence by its exact identity.', obj({'reference': TEXT})),
              ('hpc.compare', 'Compare all approved portfolios; no work is selected or launched.',
               obj({'model_ref': TEXT, 'queue_ref': TEXT}))]
    if settings.get('shared_execution_memory') is not None:
        shared.append(('hpc.history.refresh', 'Read age-weighted shared timing history once. No remote discovery, '
                                              'polling credit, or new scientific work.', obj({})))
    shared += [
        ('hpc.discovery.run', 'Run one lightweight remote inspection or documentation retrieval through the '
                              'established SSH transport. No job submission, installation or scientific '
                              'computation; those belong to Launch and the allocation.', obj({'command': TEXT})),
        ('hpc.candidate.propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON '
                                  'with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric '
                                  'map including worker_threads/workload sizes), optional resource_capacity '
                                  '{cpu_threads, memory_bytes} describing actual allocation capacity, units '
                                  '(unit_id, obligation_id, argv, environment, effort, optional reports_progress), '
                                  'optional files [{path: relative path, text: exact contents}], and preparation '
                                  'instructions for Launch. effort is a positive finite number expressing relative '
                                  'work, for example 1.0; workload sizes belong in features. No per-unit execution '
                                  'timers. Use {allocation_workspace} for the eventual directory. Existing '
                                  'candidate identities are immutable.', obj({'candidate_json': TEXT})),
        ('hpc.queue.observe', 'Acquire PBS queue and ALCF score/status once and transform them.', obj({}))]
    entries = shared + [
        ('hpc.plan', 'Freeze one useful portfolio and its forecasts; return a concrete launch assignment.',
         obj({'candidate_id': TEXT, 'model_ref': TEXT, 'queue_ref': TEXT})),
        ('hpc.handoff', 'Bind the original received PBS handoff to the exact frozen portfolio.',
         obj({'plan_ref': TEXT, 'handoff_ref': TEXT})),
        ('hpc.monitor', 'Observe the original job and progress once; update and freeze conditional forecasts.',
         obj({'plan_ref': TEXT, 'refresh_queue': {'type': 'boolean'}})),
        ('hpc.monitor.wait', 'Use the attached forecast-valued monitor controller: persist a timer, release the '
                             'coordinator while waiting, then observe this original job exactly once when due. No '
                             'earned credit for waiting.', obj({'plan_ref': TEXT})),
        ('hpc.results', 'Parse compact results from the original allocation and apply original acceptance '
                        'predicates.', obj({'plan_ref': TEXT})),
        ('hpc.allocation.order', 'Reorder original pending units at the next unit boundary, retaining all '
                                 'unstarted work.', obj({'plan_ref': TEXT, 'unit_ids': STRINGS}))]
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]


async def _execute(ctx, ledger, episode, name, arguments, key):
    """The old ``HPCWorkOperations.execute``: one operation of the catalogue, once per operation key."""
    entries = {row['name']: row for row in catalog(ctx.settings)}
    if name not in entries:
        raise ValueError('tool_not_available_to_hpc_role')
    arguments = plain(arguments)
    validate_schema(arguments, entries[name]['input_schema'])
    if not ledger.records('model'):
        _initialize(ctx, ledger)
    selection = {'tool': name, 'arguments': arguments, 'episode_id': ctx.episode_id}
    old = ledger.cached(key, selection)
    if old is not None:
        return old
    ledger.put('action_intent', selection, identity='action:' + key)
    references = []
    commission = ledger.commission
    configuration = ctx.settings['resources'][commission['resource_id']]
    if name == 'hpc.read':
        outcome = _read_retained(ctx, ledger, arguments, references)
    elif name == 'hpc.history.refresh':
        outcome = _refresh_measured_history(ctx, ledger, key, references)
    elif name == 'hpc.discovery.run':
        outcome = await _discover_resource(ctx, ledger, arguments, commission, configuration, references, key)
    elif name == 'hpc.candidate.propose':
        outcome = _propose_portfolio(ctx, ledger, arguments, commission, references)
    elif name == 'hpc.queue.observe':
        outcome = _observe_resource_queue(ctx, ledger, configuration, references, key)
    elif name == 'hpc.compare':
        outcome = _compare_portfolios(ctx, ledger, arguments, references, key)
    elif name == 'hpc.plan':
        outcome = _freeze_portfolio_plan(ctx, ledger, arguments, commission, configuration, references, key)
    elif name == 'hpc.handoff':
        outcome = _attach_original_handoff(ctx, ledger, arguments, commission, references)
    else:
        plan = ledger.read(arguments['plan_ref'])
        if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff')):
            outcome = _invalid('original_handoff_not_attached',
                               'If Launch already completed, attach the handoff it returned with hpc_handoff. Do '
                               'not launch replacement work.')
        else:
            target = _target(ctx, ledger, plan)
            candidate = _candidate(ledger, plan)
            if name == 'hpc.monitor.wait':
                outcome = await _wait_for_original_observation(ctx, ledger, episode, arguments,
                                                               references, key, plan, target, candidate)
            elif name == 'hpc.allocation.order':
                outcome = _order_original_units(ctx, ledger, arguments, references, key, plan, target, candidate)
            else:
                observation, allocation, _, observation_ref, current, measured_ref = _observe_original_allocation(
                    ctx, ledger, plan, target, candidate, key)
                if name == 'hpc.monitor':
                    outcome = _update_conditional_forecast(ctx, ledger, arguments, commission, configuration,
                                                           references, key, plan, target, candidate, observation,
                                                           observation_ref, current, measured_ref)
                else:
                    outcome = _collect_original_results(ctx, ledger, episode, commission, references,
                                                        key, plan, target, candidate, allocation, observation_ref,
                                                        current, measured_ref)
    return ledger.save_action(key, selection, outcome)


async def _run(ctx, call, name):
    episode = call['episode']
    ledger = _ledger(ctx, episode)
    outcome = await _execute(ctx, ledger, episode, name, call['arguments'], ctx.operation_key)
    return {**outcome, 'state': _state(ctx, ledger, episode)}


# -- the tools ------------------------------------------------------------------------------------------------------
# Every tool is handed ``{'arguments': <the model's arguments>, 'episode': {owner_episode_id, scope, commission}}``
# (``action`` and ``decide`` add the episode identity from the summary: a tool has no summary).

async def hpc_state(arguments, ctx):
    """The first unit: open the ledger of the commission, initialise it (old ``initialize``: the reference model and
    the model fitted on the shared history), and return the decision state the model is shown."""
    episode = arguments['episode']
    ledger = _ledger(ctx, episode)
    if not ledger.records('model'):
        _initialize(ctx, ledger)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'state': _state(ctx, ledger, episode)}


async def hpc_read(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.read')


async def hpc_compare(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.compare')


async def hpc_history_refresh(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.history.refresh')


async def hpc_discovery_run(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.discovery.run')


async def hpc_candidate_propose(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.candidate.propose')


async def hpc_queue_observe(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.queue.observe')


async def hpc_plan(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.plan')


async def hpc_handoff(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.handoff')


async def hpc_monitor(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.monitor')


async def hpc_monitor_wait(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.monitor.wait')


async def hpc_results(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.results')


async def hpc_allocation_order(arguments, ctx):
    return await _run(ctx, arguments, 'hpc.allocation.order')


TOOLS = {'hpc_state': hpc_state, 'hpc_read': hpc_read, 'hpc_compare': hpc_compare,
         'hpc_history_refresh': hpc_history_refresh, 'hpc_discovery_run': hpc_discovery_run,
         'hpc_candidate_propose': hpc_candidate_propose, 'hpc_queue_observe': hpc_queue_observe,
         'hpc_plan': hpc_plan, 'hpc_handoff': hpc_handoff, 'hpc_monitor': hpc_monitor,
         'hpc_monitor_wait': hpc_monitor_wait, 'hpc_results': hpc_results,
         'hpc_allocation_order': hpc_allocation_order}


# -- the decision ---------------------------------------------------------------------------------------------------

_TOOL_NAMES = {dotted: name for name, dotted in LEDGER_NAMES.items()}
_SELECTOR = {'type': 'object', 'additionalProperties': False,
             'properties': {'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT},
                            'path': TEXT, 'offset': {'type': 'integer', 'minimum': 0},
                            'limit': {'type': 'integer', 'minimum': 1}}}
CHILD_ARGUMENTS = {
    'launch': {'type': 'object', 'additionalProperties': False, 'required': ['plan_ref'],
               'properties': {'plan_ref': TEXT, 'launch_instructions': {'type': 'object'}}},
    'monitor': obj({'target_handle': TEXT,
                    'requested_fields': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(MONITOR_FIELDS)}},
                    'known_progress_refs': {'type': 'array', 'uniqueItems': True, 'items': TEXT},
                    'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                                         'items': {'enum': sorted(RECORD_SCHEMAS)}}}),
    'results': {'type': 'object', 'additionalProperties': False, 'required': ['plan_ref', 'selector'],
                'properties': {'plan_ref': TEXT, 'selector': _SELECTOR,
                               'initial_result_refs': {'type': 'array', 'uniqueItems': True, 'items': TEXT},
                               'initial_result_artifact_refs': {'type': 'array', 'uniqueItems': True,
                                                                'items': TEXT}}}}
CHILD_DESCRIPTIONS = {
    'launch': 'Commission the launch of one frozen plan (plan_ref): the child submits the original job and returns '
              'its original handoff, which you then attach with hpc_handoff. One launch per plan.',
    'monitor': 'Commission one monitor of an execution target: it reports which further exposed progress '
               'information is useful and returns the delivered observations you selected.',
    'results': 'Commission the acquisition of the requested original result windows (selector) of a frozen plan '
               'whose handoff is attached.'}


def _selection_schema(settings):
    options = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                'properties': {'kind': {'const': 'tool'}, 'tool': {'const': _TOOL_NAMES[entry['name']]},
                               'arguments': entry['input_schema']}} for entry in catalog(settings)]
    options += [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'role', 'assignment'],
                 'properties': {'kind': {'const': 'episode_child'}, 'role': {'const': slot},
                                'assignment': schema}} for slot, schema in CHILD_ARGUMENTS.items()]
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': options}}}


def _tool_catalogue(settings):
    return [{'name': _TOOL_NAMES[entry['name']], 'description': entry['description'],
             'input_schema': entry['input_schema']} for entry in catalog(settings)]


def decide(summary, feedback, ctx):
    """The ledger lookup first; then one selection by the model: an operation or a child commission."""
    if summary['state'] is None:
        return ToolCall('hpc_state', {'episode': summary['episode']})
    settings = ctx.settings
    library = LaunchInstructions(settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    state = summary['state']
    instructions = INSTRUCTIONS + ACTION_BOUNDARY + HOST_EXECUTION_GUIDANCE + KNOWLEDGE_INSTRUCTIONS \
        + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION
    context = {**state, 'feedback': feedback, 'current_credit': state['hpc_credit']['credit'],
               'launches': summary['launches'], 'monitors': summary['monitors'],
               'acquisitions': summary['acquisitions'], 'tools': _tool_catalogue(settings),
               'child_options': CHILD_DESCRIPTIONS, 'launch_instruction_library': library.context(),
               'tool_knowledge': knowledge.context(), 'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions, context, generation_schema(_selection_schema(settings)))


def _check_child(slot, assignment, summary, records, settings):
    if slot == 'launch':
        plan = summary['plans'].get(assignment['plan_ref'])
        launched = {entry['plan_ref'] for entry in summary['launches']}
        if (plan is None or plan['closed'] or plan['handoff_ref'] is not None
                or assignment['plan_ref'] in launched):
            raise ValueError('hpc_launch_requires_a_frozen_plan_without_a_launch_or_handoff')
        if assignment['plan_ref'] not in summary['staged_inputs']:
            raise ValueError('hpc_launch_requires_the_plan_frozen_by_this_episode')
        if 'launch_instructions' in assignment:
            LaunchInstructions(settings['launch_instructions_directory']).materialize(
                assignment['launch_instructions'])
    elif slot == 'results':
        plan = summary['plans'].get(assignment['plan_ref'])
        if plan is None or plan['handoff_ref'] is None or not records.holds(plan['handoff_ref']):
            raise ValueError('hpc_results_require_a_frozen_plan_with_its_original_handoff_attached')


def action(response, summary, records, ctx):
    """The one unit the answer selects, or a rejection. A model answer that selects none is invalid; a commission
    the model names with a record this Episode does not hold is an invalid answer (provisional rule)."""
    schema = _selection_schema(ctx.settings)
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
        selection = decoded['selection']
        if selection['kind'] == 'tool':
            arguments = selection['arguments']
            if selection['tool'] == 'hpc_handoff' and not records.holds(arguments['handoff_ref']):
                raise ValueError('handoff_not_received')
            return ToolCall(selection['tool'], {'arguments': arguments, 'episode': summary['episode']})
        slot, assignment = selection['role'], selection['assignment']
        _check_child(slot, assignment, summary, records, ctx.settings)
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ChildCall(slot, assignment)
