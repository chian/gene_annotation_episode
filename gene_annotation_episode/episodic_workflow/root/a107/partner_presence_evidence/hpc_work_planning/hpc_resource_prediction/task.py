"""The task: one selected operation on the HPC ledger of the commission per unit.

Carried from the old ``task.py`` (``ResourcePredictionTask``), ``task_decision.py``, ``task_instructions.py``,
``prediction_operations.py`` (``PredictionOperations.catalog`` and ``execute``), ``prediction_state.py``,
``prediction_history.py``, ``portfolio_comparison.py``, ``queue_observations.py``, ``received_evidence.py``,
``decision_inputs.py`` (the part that comes from outside the Episode) and ``decision_state.py``. The old
decision-exchange loop, the saved decision exchanges, the action cache of the ledger (``cached`` /
``save_action``: the system journals each unit), checkpoints and the report redelivery are not carried. The task
always offers a unit and never ends the Episode: ``action`` accepts one of the offered tools at every decision, a
selection that names none is rejected with feedback and no unit.

**The ledger** is the work table ``HPC_LEDGER`` in custody (``episode_support/jobs/hpc_ledger.py``), not a service
and not a file. ``hpc_open`` (the first unit: ``decide`` issues it, the model is not offered it) opens the ledger
of the assignment's commission with ``HpcLedger.open(ctx.store, commission)``: the rows the commissioner passed
(``ledger_row_refs``) are found under it, and an Episode that was passed none creates it. Every later tool is
handed the ledger id in its arguments (``action`` adds it) and reads the held rows with
``HpcLedger.existing(ctx.store, ledger)``. Every tool ends by returning what the ledger shows (``ledger``, with
``ledger_id`` and ``ledger_refs``), from which the summary, the credit and the return are built. The rows this
Episode wrote reach the commissioner as ``hpc_ledger_refs`` of the return.

**The prompt** is ``INSTRUCTIONS`` (what the episode is for, what the model is shown, how to work, what earns
credit) and the tool descriptions of ``catalog``; ``decide`` shows the commission, the measured cases, the ledger,
the credit and the episode's own units, and nothing of the yield controller or the progress clock.

Tools: ``hpc_model_fit``, ``hpc_queue_observe``, ``hpc_compare``, ``hpc_candidate_propose``,
``hpc_discovery_run``, ``hpc_read`` and, with the shared memory, ``hpc_history_refresh``. A model argument that
breaks a rule (an unknown reference, training ids that are not original non-validation cases, a training set that
does not precede the temporal validation, a candidate that does not validate) returns an ``invalid`` outcome, and
a request the resource did not answer returns a ``failed`` outcome: each is a unit with its credit like any other.

**The resource** is reached only through the run's ``job_access`` service (``hpc_remote.command`` and
``hpc_queue.observe``: one login-mode command on the route bound to the commission's resource id, launched once
under the unit's operation key). **The shared execution memory** is the ``estimate_table`` service (``latest``,
``observe``, ``history``, ``as_record``), used when the setting ``shared_execution_memory`` is true.

Settings this episode reads (``ctx.settings``, its entry of the run's ``continuation`` collaborator): ``resources``
(the configured resources by id, one of kind ``pbs_ssh`` with its ``account``), ``commissions`` (the configured
commissions by id, for ``commission_id``), ``shared_execution_memory`` (boolean), and ``cost`` and ``parameters``
(``yield_estimator.py``).

Not carried into the prompt: the launch-instruction and tool-knowledge library texts (this episode offers no tool
that looks anything up in them), and the old ``resource_context``, ``execution_expectations``,
``resource_tool_estimates`` and ``native_execution_expectations`` of the decision inputs. No elapsed-time or count
cutoff is carried: the old discovery ``timeout=90`` and output truncation are not in this episode's code."""
import json
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue, hpc_remote
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HpcLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence import (
    hpc_commission_sources, hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_campaign import (
    validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_resource_prediction import (
    physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

MODEL_ROLE = 'REASONING'
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'hpc_prediction_argument_transport_not_carried'}
PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'

_TEXT = {'type': 'string', 'minLength': 1}
_STRINGS = {'type': 'array', 'uniqueItems': True, 'items': _TEXT}


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


INSTRUCTIONS = (
    'You are the resource-prediction episode of one HPC commission. Your job is to predict the time and resources '
    'the commissioned work needs on the resource and to record that expectation in the HPC ledger of the '
    'commission: a fitted time/resource model with its measured held-out quality, and a comparison of the candidate '
    'portfolios under it. The planning episode and the allocation-execution sister size, plan and launch the work '
    'from what you record. You launch, submit, install and compute nothing: preparation and submission belong to '
    'the execution sister.\n\n'
    'What you are shown. commission: the work, its obligations and their credit, the cost preferences and the '
    'model features. measured_cases: the measured earlier allocations; a case with role training may be fitted, a '
    'case with role validation belongs to the fixed held-out set. The fixed reference and validation set cannot '
    'change. ledger: what the HPC ledger of this commission holds now (the current model and its held-out quality, '
    'the model, queue and comparison records, the candidate portfolios). The ledger is shared with the planner and '
    'the execution sister, and everything you record in it is handed back to your commissioner when this episode '
    'ends. credit: what this episode has earned so far. units_so_far and last_outcome: what you already did and '
    'what the last tool returned.\n\n'
    'How to work. Each decision selects exactly one tool of tools with its arguments; it runs as one unit. Fit a '
    'model on a training selection (hpc_model_fit) and read its held-out quality against the reference model. '
    'Forecast CPU time and memory demand as well as queue, setup and work time where the model has those metrics. '
    'To record the expectation for the candidates, observe the queue once (hpc_queue_observe) and compare the '
    'portfolios under your model (hpc_compare): node and worker counts, memory capacity, workload parameters and '
    'elapsed cost. Propose an executable resource alternative (hpc_candidate_propose) only when the commission '
    'supplies none worth comparing. Use hpc_discovery_run only for a capacity, launcher or queue fact you need and '
    'do not have. Unknown inputs stay unknown: never invent a measurement, a queue state or a reference. When a '
    'tool reports that the resource could not be reached, do not repeat it; work with what the ledger holds.\n\n'
    'What earns credit. Credit is the measured improvement of the model: model_scale times (the held-out quality of '
    'the model you fitted minus the held-out quality of the model in place when you started), on the fixed '
    'validation cases. It is modest and signed: a worse model loses credit. Later the planner scores the forecasts '
    'frozen with your model against the real outcomes of the allocation. Reading, discovery, queue observation, '
    'proposing and comparing earn nothing by themselves; they are worth a unit only when they change what you fit '
    'or what the planner can decide. You do not end the episode: it ends by itself when further units stop '
    'earning. Stop improving the model when further improvement is less useful than running the next worthwhile '
    'portfolio.')


def catalog(memory_configured):
    """The tools offered, each with what it records in the ledger (old ``PredictionOperations.catalog``)."""
    entries = [
        ('hpc_model_fit', 'Fit the time/resource model on the measured cases you select and make it the current '
         'model of the ledger. training_ids are ids of measured_cases with role training, all earlier than the '
         'validation cases; the validation cases cannot be trained on. Returns the held-out quality of the fitted '
         'model beside the reference model\'s (higher is better). This is the tool that earns or loses credit.',
         _object({'training_ids': _STRINGS})),
        ('hpc_queue_observe', 'Observe the scheduler queue and the facility status once on the resource and record '
         'the observation in the ledger (a queue_ref). hpc_compare needs one.', _object({})),
        ('hpc_compare', 'Forecast every candidate portfolio under one model and one queue observation and record '
         'the comparison in the ledger: predicted queue, setup and work time (and CPU time and memory where the '
         'model forecasts them), success probability, expected credit and net expected value per candidate. '
         'model_ref is one of the ledger\'s model_refs, queue_ref one of its queue_refs. No work is selected or '
         'launched.', _object({'model_ref': _TEXT, 'queue_ref': _TEXT})),
        ('hpc_candidate_propose', 'Record an executable resource alternative in the ledger. candidate_json is JSON '
         'with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including '
         'worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing actual '
         'allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional '
         'reports_progress), optional files [{path: relative path, text: exact contents}], and preparation '
         'instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; '
         'workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the '
         'eventual directory. Existing candidate identities are immutable.',
         _object({'candidate_json': _TEXT})),
        ('hpc_discovery_run', 'Run one read-only shell command on the login node of the resource, in the project '
         'directory, and record its output in the ledger: a lightweight inspection of capacity, launcher or queue '
         'facts, or a documentation lookup. No job submission, installation or scientific computation.',
         _object({'command': _TEXT})),
        ('hpc_read', 'Read one record of the ledger by its exact identity: a model_ref, a queue_ref, a '
         'comparison_ref, the id of a measured case, or commission.', _object({'reference': _TEXT}))]
    if memory_configured:
        entries.append(('hpc_history_refresh', 'Read the shared timing history of earlier runs once and record it '
                        'in the ledger: its cases join measured_cases. No remote discovery, polling credit, or new '
                        'scientific work.', _object({})))
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]


# --- the shared memory (a service) and the ledger's evidence -------------------------------------------------------

def _memory(ctx):
    """The shared execution memory (the estimate table service), or ``None`` when the settings switch it off."""
    return ctx.services['estimate_table'] if ctx.settings['shared_execution_memory'] else None


def _recorded(ledger, identity, kind, value):
    """Keep ``value`` as the evidence ``identity`` of this unit."""
    ledger.put(kind, value, identity=identity)
    return value


def _first(ledger, identity, kind, calculate):
    """The evidence a ledger has once (``identity``): what the first Episode that needed it calculated."""
    held = [row['body'] for row in ledger.records(kind) if row['id'] == identity]
    return held[0] if held else _recorded(ledger, identity, kind, calculate())


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
        imported = _first(ledger, 'shared_history_entry', 'shared_history',
                          lambda: _shared_history(ledger, memory, resources))
        if imported['observations'] and not ledger.records('model_choice'):
            model = prediction.fit(ledger.commission['model'], imported['observations'])
            reference = ledger.put('model', model)
            ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')
    # The model this prediction episode starts from: its credit is the improvement over it.
    current = _current_model(ledger)
    ledger.put('model_entry', {'model_ref': current, 'quality': _quality(ledger, ledger.read(current))},
               identity='entry:' + episode_id)


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


async def _observe_queue(ctx, ledger, memory, configuration):
    """One queue observation ``{'snapshot', 'acquisition'}``: the shared memory's while it is fresh, else one
    acquisition on the resource through the run's job access; ``{'status': 'failed', 'failure'}`` when the
    resource could not be asked."""
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if memory is not None:
        cached = memory.latest(resource, 'queue')
        if (cached['state'] == 'fresh' and cached['age_seconds'] <=
                ledger.commission['limits']['queue_max_age_seconds']):
            return cached['data']
    acquired = await hpc_queue.observe(ctx, ledger.commission['resource_id'])
    if acquired['status'] != 'completed':
        return acquired
    value = {'snapshot': acquired['snapshot'], 'acquisition': acquired['acquisition']}
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
    """What the ledger of the commission shows now, as this episode needs it: for the model's next decision
    (``internal_summary`` arranges it), for the credit (``current_quality``, ``model_entry``,
    ``validation_credit``) and for the return (``ledger_refs``: every held row, to hand back in custody)."""
    commission = ledger.commission
    model_ref = _current_model(ledger)
    model = ledger.read(model_ref)
    contributions = ledger.credit_view()['contributions']
    entry = ledger.read('entry:' + episode_id)
    validation = sum(row['credit'] for row in contributions if row['kind'] == 'validation'
                     and ledger.read(row['evidence_id']).get('prediction_episode_id') == episode_id)
    held_out = set(commission['validation_ids'])
    cases = [{'id': row['id'], 'role': 'validation' if row['id'] in held_out else 'training',
              'observed_at': row['observed_at'], 'features': row['features'], 'metrics': row['metrics'],
              'success': row['success']}
             for row in sorted(_history(ledger).values(), key=lambda row: (row['observed_at'], row['id']))]
    return {
        'ledger_id': ledger.ledger, 'ledger_refs': ledger.refs(),
        'commission': {'objective': commission['objective'], 'resource_id': commission['resource_id'],
                       'obligations': {name: {'credit': row['credit']}
                                       for name, row in commission['obligations'].items()},
                       'preferences': commission['preferences'], 'credit': commission['credit'],
                       'model_features': commission['model']['features'],
                       'validation_ids': commission['validation_ids']},
        'resource': configuration, 'cases': cases, 'candidates': _candidates(ledger),
        'tool_requests': [row['body'] for row in ledger.records('tool_request')],
        'current_model_ref': model_ref, 'current_quality': _quality(ledger, model),
        'model_support': prediction.predict(model, {})['support'], 'model_entry': entry,
        'model_refs': [row['id'] for row in ledger.records('model')],
        'comparison_refs': [row['id'] for row in ledger.records('comparison')],
        'latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                               if key not in ('episode_id', 'operation_key')}}
                              for row in ledger.records('comparison')[-1:]],
        'plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                  for row in ledger.records('plan')],
        'queue_refs': [row['id'] for row in ledger.records('queue')],
        'shared_history_refs': [row['id'] for row in ledger.records('shared_history')],
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


def _failed(ctx, ledger, configuration, failure):
    """A request the resource did not answer: an outcome of the unit, with the route's own failure."""
    return _outcome(ctx, ledger, configuration, 'failed', feedback={'category': 'resource_request', **failure})


# --- tools -------------------------------------------------------------------------------------------------------

def _identity(value):
    return {key: value[key] for key in ('commission_id', 'commission_source_ref') if value.get(key) is not None}


def _commission(ctx, arguments, resources):
    """The commission of the assignment (old ``PredictionAssignment._commission``): a configured commission by id,
    or a host grant read from a held Store source."""
    if arguments.get('commission_source_ref') is not None:
        return hpc_commission_sources.read(ctx.store, arguments['commission_source_ref'],
                                           scope=plain(arguments['scope']), resources=resources)
    return validate_commission(plain(ctx.settings['commissions'][arguments['commission_id']]), resources)


def _opened(ctx, arguments):
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    resources = plain(ctx.settings['resources'])
    # The resource of this ledger's commission is also shown to the model (old ``hpc_resource``).
    return ledger, resources, ledger.commission, resources[ledger.commission['resource_id']], _memory(ctx)


def hpc_open(arguments, ctx):
    """Open the ledger of this assignment's commission (old ``PredictionState.state`` and ``initialize``). The
    ledger is named by its commission, so the rows the commissioner passed are found under it; an Episode that
    was passed none creates the ledger here and records the owner it works for. The owner's scope and
    commission identity must be this assignment's."""
    resources = plain(ctx.settings['resources'])
    ledger = HpcLedger.open(ctx.store, _commission(ctx, arguments, resources))
    if not ledger.records('owner'):
        ledger.put('owner', {'run_id': ctx.run_id, 'episode_id': arguments['owner_episode_id'],
                             'scope': plain(arguments['scope']), **_identity(arguments)}, identity='owner')
    original = ledger.read('owner')
    if original['scope'] != plain(arguments['scope']) or _identity(original) != _identity(arguments):
        raise ValueError('sister_scope_must_equal_original_parent_scope')
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
    result = _recorded(ledger, 'shared_history:' + ctx.operation_key, 'shared_history',
                       _shared_history(ledger, memory, resources))
    return _outcome(ctx, ledger, configuration, 'completed', result)


async def hpc_discovery_run(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    # Read-only discovery; every change and every submission belongs to the launch of the execution sister.
    command = 'cd ' + shlex.quote(PROJECT_DIRECTORY) + ' && ' + arguments['command']
    cache_key = resource_identity(commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
    cached = memory.latest(cache_key, 'inventory') if memory is not None else {'state': 'unknown'}
    if cached['state'] == 'fresh':
        value = cached['data']
    else:
        ran = await hpc_remote.command(ctx, commission['resource_id'], command, name='discovery')
        if ran['status'] != 'completed':
            return _failed(ctx, ledger, configuration, ran['failure'])
        value = {'command': arguments['command'], 'returncode': ran['returncode'],
                 'stdout': ran['files']['stdout.log'].decode('utf-8', 'replace'),
                 'stderr': ran['files']['stderr.log'].decode('utf-8', 'replace'), 'observed_at': time.time()}
        if memory is not None and ran['returncode'] == 0:
            memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                           provenance=[ledger.ledger, 'discovery:' + ctx.operation_key])
    _recorded(ledger, 'discovery:' + ctx.operation_key, 'discovery', value)
    return _outcome(ctx, ledger, configuration, 'completed', value)


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


async def hpc_queue_observe(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    observed = await _observe_queue(ctx, ledger, memory, configuration)
    if 'failure' in observed:
        return _failed(ctx, ledger, configuration, observed['failure'])
    reference = 'queue:' + hpc_queue.digest(ctx.operation_key)
    _recorded(ledger, reference, 'queue', observed)
    result = {'queue_ref': reference, 'features': [hpc_queue.features(observed['snapshot'], candidate)
                                                   for candidate in _candidates(ledger)],
              'snapshot': observed['snapshot']}
    return _outcome(ctx, ledger, configuration, 'completed', result)


def hpc_model_fit(arguments, ctx):
    ledger, resources, commission, configuration, memory = _opened(ctx, arguments)
    selected = set(arguments['training_ids'])
    if memory is not None:
        _recorded(ledger, 'shared_history:' + ctx.operation_key, 'shared_history',
                  _shared_history(ledger, memory, resources))
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


def decide(summary, feedback, ctx):
    """The first unit opens the ledger (no model is asked). After it the model is shown the commission, the
    measured cases, the ledger, this episode's credit and what it did so far, and selects one tool. The yield
    controller's own state and the progress clock are not shown: nothing in them is the model's to decide."""
    if summary['ledger'] is None:
        return ToolCall('hpc_open', {name: summary[name] for name in (
            'owner_episode_id', 'commission_id', 'commission_source_ref', 'scope')})
    memory_configured = bool(ctx.settings['shared_execution_memory'])
    context = {'commission': summary['commission'], 'resource': summary['resource'],
               'measured_cases': summary['measured_cases'], 'ledger': summary['ledger_state'],
               'credit': summary['hpc_credit'], 'units_so_far': summary['units_so_far'],
               'last_outcome': summary['last_outcome'], 'feedback': feedback,
               'tools': catalog(memory_configured)}
    if memory_configured:
        context['shared_memory'] = ctx.services['estimate_table'].read('as_record')
    schema = selection_schema(memory_configured)
    return ModelRequest(MODEL_ROLE, INSTRUCTIONS, context, strict_output_schema(schema, **TRANSPORT))


def action(response, summary, records, ctx):
    schema = selection_schema(bool(ctx.settings['shared_execution_memory']))
    try:
        decoded = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selected = decoded['selection']
    # What a tool needs beside the model's arguments (a tool is handed no summary): the ledger it works on, by its
    # id, and the scope of the assignment.
    return ToolCall(selected['tool'], {**selected['arguments'], 'ledger': summary['ledger']['ledger_id'],
                                       'scope': summary['scope']})
