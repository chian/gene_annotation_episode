"""The task: one selected operation on the parent-owned HPC ledger per unit.

Carried from the old ``task.py`` (``ResourcePredictionTask``), ``task_decision.py``, ``task_instructions.py``,
``prediction_operations.py`` (``PredictionOperations.catalog`` and ``execute``), ``prediction_state.py``,
``prediction_history.py``, ``portfolio_comparison.py``, ``queue_observations.py``, ``received_evidence.py``,
``decision_inputs.py`` (the part that comes from outside the Episode) and ``decision_state.py``. The old
decision-exchange loop, the saved decision exchanges, the action cache of the ledger (``cached`` /
``save_action``: the system journals each unit and gives the tool ``ctx.operation_key``), checkpoints and the
report redelivery are not carried (README 3a, 3b, 3e). The task always offers a unit and never ends the Episode:
``action`` accepts one of the offered tools at every decision, a selection that names none is rejected with feedback
and no unit.

Tool names are the old names with ``_`` for ``.``: ``hpc_read``, ``hpc_compare``, ``hpc_history_refresh`` (offered
only with shared execution memory), ``hpc_discovery_run``, ``hpc_candidate_propose``, ``hpc_queue_observe``,
``hpc_model_fit``. ``hpc_open`` is this episode's initial lookup (old ``PredictionState.state`` and ``initialize``):
``decide`` issues it first, the model is not offered it. A model argument that breaks a rule (an unknown reference,
training ids that are not original non-validation cases, a training set that does not precede the temporal
validation, a candidate that does not validate) returns an ``invalid`` outcome, which is a unit with its credit like
any other; the old code raised the two training errors.

Settings this episode reads (``ctx.settings``, its entry of the run's ``continuation`` collaborator; old
``PredictionConfiguration``): ``resources`` (the configured resources, one of kind ``pbs_ssh``), ``commissions``
(the configured commissions by id, used for ``commission_id``), ``shared_execution_memory`` (``None``, or the old
``ExecutionMemory`` configuration), ``launch_instructions_directory`` and ``knowledge_library_directory`` (optional),
and ``cost`` and ``parameters`` (``yield_estimator.py``).

The ledger is outside the Store: every tool opens the owner's ledger through the ``hpc_ledger`` service and ends by
returning the ledger's present view in its outcome (``ledger``), from which the summary and the credit are built.

No elapsed-time or count cutoff is carried: the old discovery ``timeout=90`` and output truncation, and the old
first-2000-observations slice of the shared history, are not in this episode's code (README rule 2).

BLOCKED-ON-JOB-SERVICE: hpc_ledger (not provided): ``_open_ledger``; the parent-owned HPC ledger shared with the
allocation sister, a durable store outside the Store and outside custody, also written by that sister and by the HPC
parent (plans, monitors, measured outcomes, scores, results).

BLOCKED-ON-JOB-SERVICE: job_access (not provided): ``_remote`` (one read-only remote command) and
``_acquire_queue`` (one PBS queue and ALCF observation).

BLOCKED-ON-JOB-SERVICE: estimate_table (not provided): the shared execution memory (``ExecutionMemory``: ``latest``,
``observe``, ``history``, ``as_record``) is called as ``ctx.services['estimate_table']``; and the old
``resource_context``, ``execution_expectations``, ``resource_tool_estimates`` and ``native_execution_expectations``
of the decision inputs are not shown to the model (wanted call ``ctx.services['estimate_table'].read(...)``).

BLOCKED-ON-STORE-ACCESS: ``hpc_commission_sources.read`` (library not carried: ``store.db`` and ``sqlite_master``),
called as written with ``ctx.store`` in ``_commission``."""
import asyncio
import json
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions import (
    launch_instructions as launch_library)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence import (
    hpc_commission_sources, hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_campaign import (
    validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_resource_prediction import (
    physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools import tool_knowledge as knowledge_library
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from . import goal as goal_file

CHILD_SLOTS = {}
SERVICES = ('hpc_ledger', 'job_access', 'estimate_table')

MODEL_ROLE = 'REASONING'
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'hpc_prediction_argument_transport_not_carried'}
PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'

_TEXT = {'type': 'string', 'minLength': 1}
_STRINGS = {'type': 'array', 'uniqueItems': True, 'items': _TEXT}


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def catalog(memory_configured):
    """The tools offered (old ``PredictionOperations.catalog``)."""
    shared = [
        ('hpc_read', 'Read retained HPC evidence by its exact identity.', _object({'reference': _TEXT})),
        ('hpc_compare', 'Compare all approved portfolios; no work is selected or launched.',
         _object({'model_ref': _TEXT, 'queue_ref': _TEXT}))]
    if memory_configured:
        shared.append(('hpc_history_refresh', 'Read age-weighted shared timing history once. '
                       'No remote discovery, polling credit, or new scientific work.', _object({})))
    shared += [
        ('hpc_discovery_run', 'Run one lightweight remote inspection or documentation retrieval through the '
         'established SSH transport. No job submission, installation or scientific computation; those belong to '
         'Launch and the allocation.', _object({'command': _TEXT})),
        ('hpc_candidate_propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON '
         'with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including '
         'worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing actual '
         'allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional '
         'reports_progress), optional files [{path: relative path, text: exact contents}], and preparation '
         'instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; '
         'workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the '
         'eventual directory. Existing candidate identities are immutable.',
         _object({'candidate_json': _TEXT})),
        ('hpc_queue_observe', 'Acquire PBS queue and ALCF score/status once and transform them.', _object({}))]
    entries = shared + [('hpc_model_fit', 'Fit selected measured history; validate on the fixed disjoint cases.',
                         _object({'training_ids': _STRINGS}))]
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]


# --- the ledger, the job access and the shared memory (services) -------------------------------------------------

def _open_ledger(ctx, owner_episode_id):
    raise NotImplementedError(
        "BLOCKED-ON-JOB-SERVICE: hpc_ledger; wanted call: ctx.services['hpc_ledger'].open_existing(ctx.run_id, "
        "owner_episode_id), returning the owner's HPCLedger (old HPCLedger.open_existing(directory / 'hpc' / "
        "hpc_queue.digest([run_id, owner_episode_id])), the parent-owned ledger shared with the allocation sister)")


def _remote(ctx, configuration, command):
    raise NotImplementedError(
        "BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access'].run_remote("
        "configuration['ssh_argv'], command, key=ctx.operation_key), returning {'returncode', 'stdout', 'stderr'} "
        "of one read-only command through the established SSH transport (old subprocess.run of ssh_argv + command)")


def _acquire_queue(ctx, configuration):
    raise NotImplementedError(
        "BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access'].observe_queue("
        "configuration, key=ctx.operation_key), returning {'snapshot', 'acquisition'} of one PBS queue and ALCF "
        "observation (old hpc_queue.observe(configuration))")


def _memory(ctx):
    """The shared execution memory service, or ``None`` when the settings configure none."""
    return ctx.services['estimate_table'] if ctx.settings.get('shared_execution_memory') is not None else None


# --- state of the ledger (old prediction_state, prediction_history, portfolio_comparison, queue_observations) -----

def _current_model(ledger):
    records = ledger.records('model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'


def _candidates(ledger):
    return ledger.commission['candidates'] + [row['body'] for row in ledger.records('candidate')]


def _quality(ledger, model):
    if not set(model['training_ids']) <= {row['id'] for row in ledger.commission['history']}:
        return None
    selected = [row for row in ledger.commission['history'] if row['id'] in ledger.commission['validation_ids']]
    return prediction.quality(model, selected) if selected else None


def _history(ledger):
    rows = {row['id']: row for row in ledger.commission['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()} - {None}
    for snapshot in ledger.records('shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    # Keep one latest observation per actual allocation, not one training
    # example per poll. Failed unfinished work retains a censored duration.
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


def _shared_history(ledger, memory, resources):
    commission = ledger.commission
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], resources[commission['resource_id']])
    # Queue timing is resource-wide. Work timing requires explicit matching
    # algorithm, parameters, software and hardware, never just 'Aurora'.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in memory.history(query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in memory.history(profile, now=now)})
    queues = {candidate['queue'] for candidate in _candidates(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        queue = row.get('queue')
        # Different PBS queues are not interchangeable. Pool only when
        # the portfolio has one matching queue, or the model explicitly
        # carries its categorical indicator.
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
                             and physical_attempt_key(row) not in original_attempts]}


def _initialize(ledger, memory, resources, episode_id):
    prior = prediction.prior_model(ledger.commission['model'])
    ledger.put('model', prior, identity='reference_model')
    if memory is not None:
        imported = ledger.once('shared_history_entry', 'shared_history',
                               lambda: _shared_history(ledger, memory, resources))
        if imported['observations'] and not ledger.records('model_choice'):
            model = prediction.fit(ledger.commission['model'], imported['observations'])
            reference = ledger.put('model', model)
            ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')

    def entry():
        current = _current_model(ledger)
        return {'model_ref': current, 'quality': _quality(ledger, ledger.read(current))}
    ledger.once('entry:' + episode_id, 'model_entry', entry)


def _features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def _queue(ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def _comparisons(ledger, model_ref, queue_ref):
    model = ledger.read(model_ref)
    observed = _queue(ledger, queue_ref)
    actual = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
              if row['kind'] == 'actual']
    results = []
    for candidate in _candidates(ledger):
        queue = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, _features(candidate, queue))
        row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                 ledger.commission['preferences'], already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def _observe_queue(ctx, ledger, memory, configuration):
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if memory is not None:
        cached = memory.latest(resource, 'queue')
        if (cached['state'] == 'fresh' and cached['age_seconds'] <=
                ledger.commission['limits']['queue_max_age_seconds']):
            return cached['data']
    value = _acquire_queue(ctx, configuration)
    if memory is not None:
        memory.observe(resource, 'queue', value, observed_at=value['snapshot']['captured_at'],
                       provenance=value['acquisition'])
    return value


# --- received evidence (old received_evidence) -----------------------------------------------------------------

def _resolve_received_source(ctx, reference, scope):
    """Whether ``reference`` is a received ``episode.hpc_result`` source of this run and within the parent scope:
    ``None`` when it is not such a source, ``False`` when it is not received (held) or not owned."""
    if not ctx.store.holds(reference):
        return False
    source = ctx.store.get(reference)
    if source.get('provider') != 'episode.hpc_result':
        return None
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    if body['run_id'] != ctx.run_id:
        return False
    try:
        ctx.store.validate_scope(body['scope'], parent_scope=plain(scope))
    except ValueError:
        return False
    return True


def _read_evidence(ctx, ledger, reference, scope):
    history = _history(ledger)
    if reference in history:
        return history[reference]
    if not reference.startswith('source_'):
        return ledger.read(reference)
    # Results publish ordinary Store Sources as well as ledger receipts.
    # Resolve only a received Source owned by this original HPC ledger.
    rows = [row['body'] for row in ledger.records('result') if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or _resolve_received_source(ctx, reference, scope) is not True:
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


# --- the view of the ledger every outcome carries --------------------------------------------------------------

def _ledger_view(ledger, episode_id, configuration):
    commission = ledger.commission
    model_ref = _current_model(ledger)
    model = ledger.read(model_ref)
    contributions = ledger.credit_view()['contributions']
    entries = ledger.records('model_entry')
    entry = next((row['body'] for row in entries if row['id'] == 'entry:' + episode_id), None)
    validation = sum(row['credit'] for row in contributions if row['kind'] == 'validation'
                     and ledger.read(row['evidence_id']).get('prediction_episode_id') == episode_id)
    return {
        'commission': commission, 'resource': configuration, 'candidates': _candidates(ledger),
        'tool_requests': [row['body'] for row in ledger.records('tool_request')],
        'current_model_ref': model_ref, 'current_quality': _quality(ledger, model),
        'model_support': prediction.predict(model, {})['support'], 'model_entry': entry,
        'model_refs': [row['id'] for row in ledger.records('model')],
        'latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                               if key not in ('episode_id', 'operation_key')}}
                              for row in ledger.records('comparison')[-1:]],
        'plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                  for row in ledger.records('plan')],
        'latest_monitor': ledger.records('monitor')[-1:],
        'monitor_controllers': ledger.records('monitor_controller'),
        'queue_refs': [row['id'] for row in ledger.records('queue')],
        'shared_history_refs': [row['id'] for row in ledger.records('shared_history')],
        'available_training_ids': sorted(set(_history(ledger)) - set(commission['validation_ids'])),
        'validation_credit': validation,
        'accepted_obligations': [row['slot'].removeprefix('actual:') for row in contributions
                                 if row['kind'] == 'actual'],
        'result_source_refs': [row['body']['source_ref'] for row in ledger.records('result')]}


def _outcome(ctx, ledger, configuration, status, result=None, feedback=None):
    return {'status': status, 'record_refs': [], 'result': result,
            **({'feedback': feedback} if feedback is not None else {}),
            'ledger': _ledger_view(ledger, ctx.episode_id, configuration)}


def _invalid(ctx, ledger, configuration, code, **more):
    return _outcome(ctx, ledger, configuration, 'invalid',
                    feedback={'category': 'arguments_or_reference', 'code': code, **more})


# --- tools -------------------------------------------------------------------------------------------------------

def _identity(value):
    return {key: value[key] for key in ('commission_id', 'commission_source_ref') if value.get(key) is not None}


def _commission(ctx, arguments, resources):
    """The commission of the assignment (old ``PredictionAssignment._commission``)."""
    if arguments.get('commission_source_ref') is not None:
        return hpc_commission_sources.read(ctx.store, arguments['commission_source_ref'],
                                           scope=plain(arguments['scope']), resources=resources)
    return validate_commission(plain(ctx.settings['commissions'][arguments['commission_id']]), resources)


def _opened(ctx, arguments):
    ledger = _open_ledger(ctx, arguments['owner_episode_id'])
    resources = plain(ctx.settings['resources'])
    # The resource of this ledger's commission is also shown to the model (old ``hpc_resource``).
    return ledger, resources, ledger.commission, resources[ledger.commission['resource_id']], _memory(ctx)


def hpc_open(arguments, ctx):
    """Open the owner's ledger for this assignment (old ``PredictionState.state`` and ``initialize``)."""
    resources = plain(ctx.settings['resources'])
    _commission(ctx, arguments, resources)
    ledger = _open_ledger(ctx, arguments['owner_episode_id'])
    original = ledger.read('owner')
    if original['scope'] != plain(arguments['scope']) or _identity(original) != _identity(arguments):
        raise ValueError('sister_scope_must_equal_original_parent_scope')
    # initialize is idempotent (identities, ``once``); each prediction episode gets its own model_entry record.
    _initialize(ledger, _memory(ctx), resources, ctx.episode_id)
    return _outcome(ctx, ledger, resources[ledger.commission['resource_id']], 'completed')


def hpc_read(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    try:
        result = _read_evidence(ctx, ledger, arguments['reference'], arguments['scope'])
    except (ValueError, KeyError) as error:
        return _invalid(ctx, ledger, configuration, str(error))
    return _outcome(ctx, ledger, configuration, 'completed', result)


def hpc_history_refresh(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    if memory is None:
        raise ValueError('tool_not_available_to_hpc_role')
    result = ledger.once('shared_history:' + ctx.operation_key, 'shared_history',
                         lambda: _shared_history(ledger, memory, resources))
    return _outcome(ctx, ledger, configuration, 'completed', result)


async def hpc_discovery_run(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    # Read-only discovery can be repeated after interrupted observation;
    # all mutations and submissions use the durable Launch operations.
    command = 'cd ' + shlex.quote(PROJECT_DIRECTORY) + ' && ' + arguments['command']

    def observe():
        cache_key = resource_identity(commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
        if memory is not None:
            cached = memory.latest(cache_key, 'inventory')
            if cached['state'] == 'fresh':
                return cached['data']
        completed = _remote(ctx, configuration, command)
        value = {'command': arguments['command'], 'returncode': completed['returncode'],
                 'stdout': completed['stdout'], 'stderr': completed['stderr'], 'observed_at': time.time()}
        if memory is not None and completed['returncode'] == 0:
            memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                           provenance=['hpc_ledger:' + arguments['owner_episode_id'], 'discovery:' + ctx.operation_key])
        return value
    result = await asyncio.to_thread(ledger.once, 'discovery:' + ctx.operation_key, 'discovery', observe)
    return _outcome(ctx, ledger, configuration, 'completed', result)


def hpc_candidate_propose(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    try:
        candidate = json.loads(arguments['candidate_json'])
        candidates = _candidates(ledger)
        prior = next((row for row in candidates if row['id'] == candidate['id']), None)
        if prior is not None and prior != candidate:
            raise ValueError('candidate_identity_is_immutable')
        validate_commission({**commission, 'candidates': candidates if prior else candidates + [candidate]}, resources)
    except (ValueError, KeyError, TypeError) as error:
        return _invalid(ctx, ledger, configuration, str(error))
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates'] else
                 ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return _outcome(ctx, ledger, configuration, 'completed', {'candidate_ref': reference, 'candidate_id': candidate['id']})


def hpc_queue_observe(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    reference = 'queue:' + hpc_queue.digest(ctx.operation_key)
    observed = ledger.once(reference, 'queue', lambda: _observe_queue(ctx, ledger, memory, configuration))
    result = {'queue_ref': reference, 'features': [hpc_queue.features(observed['snapshot'], candidate)
                                                   for candidate in _candidates(ledger)],
              'snapshot': observed['snapshot']}
    return _outcome(ctx, ledger, configuration, 'completed', result)


def hpc_model_fit(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    selected = set(arguments['training_ids'])
    if memory is not None:
        ledger.once('shared_history:' + ctx.operation_key, 'shared_history',
                    lambda: _shared_history(ledger, memory, resources))
    cases = _history(ledger)
    if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
        return _invalid(ctx, ledger, configuration, 'training_ids_must_be_original_nonvalidation_cases')
    heldout = [cases[key] for key in commission['validation_ids']]
    historical_selected = selected.intersection(row['id'] for row in commission['history'])
    if historical_selected and heldout and (max(cases[key]['observed_at'] for key in historical_selected)
                                            >= min(row['observed_at'] for row in heldout)):
        return _invalid(ctx, ledger, configuration, 'training_must_precede_temporal_validation')
    model = prediction.fit(commission['model'], [cases[key] for key in selected])
    model_ref = ledger.put('model', model)
    # Fixed historical validation cannot measure a model trained on
    # later completed allocations. Those updates earn prospective
    # credit when the next real outcomes arrive, not retrospective Q.
    later_training = selected - set(row['id'] for row in commission['history'])
    quality = None if later_training else _quality(ledger, model)
    baseline = _quality(ledger, ledger.read('reference_model'))
    ledger.put('model_choice', {'operation_key': ctx.operation_key, 'model_ref': model_ref,
                                'episode_id': ctx.episode_id})
    if quality is not None:
        ledger.model_credit(model_ref, quality - baseline)
    else:
        ledger.model_credit(model_ref, 0.)
    return _outcome(ctx, ledger, configuration, 'completed', {'model_ref': model_ref, 'validation_quality': quality,
                                               'reference_quality': baseline, 'credit': ledger.credit_view()})


def hpc_compare(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    try:
        result = {'comparisons': _comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
    except (ValueError, KeyError) as error:
        return _invalid(ctx, ledger, configuration, str(error), recovery=(
            'Use a model_ref from hpc_model_fit or hpc_model_ref and a queue_ref from hpc_queue_observe or '
            'hpc_queue_refs; a resource identity is not a queue observation.'))
    result['comparison_ref'] = ledger.put('comparison', {**result, 'model_ref': arguments['model_ref'],
                                                         'queue_ref': arguments['queue_ref'],
                                                         'episode_id': ctx.episode_id,
                                                         'operation_key': ctx.operation_key})
    return _outcome(ctx, ledger, configuration, 'completed', result)


TOOLS = {'hpc_open': hpc_open, 'hpc_read': hpc_read, 'hpc_compare': hpc_compare,
         'hpc_history_refresh': hpc_history_refresh, 'hpc_discovery_run': hpc_discovery_run,
         'hpc_candidate_propose': hpc_candidate_propose, 'hpc_queue_observe': hpc_queue_observe,
         'hpc_model_fit': hpc_model_fit}


# --- deciding ----------------------------------------------------------------------------------------------------

def selection_schema(memory_configured):
    """The closed decision form: one offered tool with its arguments."""
    options = [_object({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                        'arguments': entry['input_schema']}) for entry in catalog(memory_configured)]
    return _object({'selection': {'anyOf': options}})


def instructions(settings):
    """Old ``task_instructions.instructions``: the goal, the tool knowledge text and the launch instruction text
    (no generic instructions, no reasoning, wait or redelivery text)."""
    text = goal_file.GOAL
    if settings.get('knowledge_library_directory') is not None:
        text += knowledge_library.INSTRUCTIONS
    if settings.get('launch_instructions_directory') is not None:
        text += launch_library.INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    if summary['ledger'] is None:
        return ToolCall('hpc_open', {name: summary[name] for name in (
            'owner_episode_id', 'commission_id', 'commission_source_ref', 'scope')})
    memory_configured = ctx.settings.get('shared_execution_memory') is not None
    context = {
        'goal': goal_file.GOAL,
        'hpc_commission': summary['hpc_commission'], 'hpc_candidates': summary['hpc_candidates'],
        'hpc_resource': summary['hpc_resource'], 'hpc_tool_request': summary['hpc_tool_request'],
        'hpc_model_ref': summary['hpc_model_ref'], 'hpc_credit': summary['hpc_credit'],
        'hpc_latest_comparison': summary['hpc_latest_comparison'], 'hpc_model_support': summary['hpc_model_support'],
        'hpc_plans': summary['hpc_plans'], 'hpc_latest_monitor': summary['hpc_latest_monitor'],
        'hpc_monitor_controllers': summary['hpc_monitor_controllers'], 'hpc_queue_refs': summary['hpc_queue_refs'],
        'hpc_available_training_ids': summary['hpc_available_training_ids'],
        'requested_action_history': summary['requested_action_history'],
        'tools': catalog(memory_configured), 'last_local_outcome': summary['last_local_outcome'],
        'feedback': feedback, 'current_credit': summary['current_credit'], 'controller': summary['controller'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
    }
    if memory_configured:
        context = extend_context(context, {
            'hpc_shared_memory': ctx.services['estimate_table'].read('as_record'),
            'hpc_shared_history_refs': summary['hpc_shared_history_refs']},
            conflict='initial_binding_context_field_conflict')
    library = ctx.settings.get('launch_instructions_directory')
    if library is not None:
        launch = LaunchInstructions(library)
        context = extend_context(context, {
            'launch_instruction_library': launch.context(),
            'selected_launch_instructions': launch.materialize(summary['launch_instructions'])},
            conflict='initial_binding_context_field_conflict')
    knowledge = ctx.settings.get('knowledge_library_directory')
    if knowledge is not None:
        context = extend_context(context, {'tool_knowledge': ToolKnowledge(knowledge).context()},
                                 conflict='initial_binding_context_field_conflict')
    schema = selection_schema(memory_configured)
    return ModelRequest(MODEL_ROLE, instructions(ctx.settings), context, strict_output_schema(schema, **TRANSPORT))


def action(response, summary, records, ctx):
    schema = selection_schema(ctx.settings.get('shared_execution_memory') is not None)
    try:
        decoded = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selected = decoded['selection']
    # What a tool needs of the assignment is copied into its arguments (a tool is handed no summary).
    return ToolCall(selected['tool'], {**selected['arguments'], 'owner_episode_id': summary['owner_episode_id'],
                                       'scope': summary['scope']})
