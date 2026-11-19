"""The task: iterate on a generalized time/resource model over the parent-owned HPC ledger.

One unit is one tool action. The first unit opens the ledger (``hpc_initialize``); then the model picks one of
the offered tools each time: read retained HPC evidence, compare portfolios, refresh shared history, run one
lightweight remote discovery, propose a candidate portfolio, observe the PBS queue, or fit the model on selected
measured history. The task never ends the Episode: only its yield controller does.

The ledger (the parent's retained model, history, candidate, queue, comparison, plan, monitor and credit
records, shared with the execution sister) and the job access (remote discovery and the PBS queue) are the
job design of LAUNCH_MONITOR_EXTRACT_MECHANICS.md, sections 5 and 6. The system does not provide either yet:
``open_ledger`` raises where the ledger would be opened, and every tool opens it first."""
import json
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.gene_context_evidence.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_campaign import (
    validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_resource_prediction import (
    physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

DISCOVERY_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'

INSTRUCTIONS = (
    'Iterate on a generalized time/resource model using measured historical cases. '
    'Refresh shared history, inspect support and held-out quality, fit a disjoint training selection, '
    'and compare useful portfolios. Inspect missing capacity, launcher and queue facts with '
    'lightweight discovery; propose executable resource alternatives when the parent has not '
    'supplied them. Preparation and submission belong to the execution sister. '
    'Forecast CPU time and memory demand as well as queue, setup '
    'and work time. Compare node/worker counts, memory capacity, workload parameters and elapsed cost. '
    'The paired execution episode owns Launch, monitoring and parsing. Both sisters use this '
    'parent-owned ledger; preserve model and comparison identities for that sibling. '
    'The fixed reference and validation set cannot change. Model credit is modest measured improvement; '
    'the HPC parent later scores frozen predictions against real outcomes. Unknown inputs stay unknown. '
    'Return when further model improvement is less useful than running the next worthwhile portfolio. '
    'You cannot end the episode yourself: every answer selects one of the offered tools, and the '
    'episode ends when its continuation rule stops it.')

TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'properties': properties,
            'required': list(properties)}


def catalog(memory):
    """The tools the model may select, with their meaning and operands (the history refresh only with shared memory)."""
    entries = [
        ('hpc_read', 'Read retained HPC evidence by its exact identity.', _object({'reference': TEXT})),
        ('hpc_compare', 'Compare all approved portfolios; no work is selected or launched.',
         _object({'model_ref': TEXT, 'queue_ref': TEXT}))]
    if memory:
        entries.append(('hpc_history_refresh', 'Read age-weighted shared timing history once. '
                        'No remote discovery, polling credit, or new scientific work.', _object({})))
    entries += [
        ('hpc_discovery_run', 'Run one lightweight remote inspection or documentation retrieval through the '
         'established SSH transport. No job submission, installation or scientific computation; those belong to '
         'Launch and the allocation.', _object({'command': TEXT})),
        ('hpc_candidate_propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON '
         'with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including '
         'worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing actual '
         'allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional '
         'reports_progress), optional files [{path: relative path, text: exact contents}], and preparation '
         'instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; '
         'workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the '
         'eventual directory. Existing candidate identities are immutable.', _object({'candidate_json': TEXT})),
        ('hpc_queue_observe', 'Acquire PBS queue and ALCF score/status once and transform them.', _object({})),
        ('hpc_model_fit', 'Fit selected measured history; validate on the fixed disjoint cases.',
         _object({'training_ids': STRINGS}))]
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]


# ---------------------------------------------------------------------------------------------------------
# The ledger and the job access (not provided yet)

def open_ledger(store, owner_episode_id):
    """The ledger the commissioning HPC parent owns, as records held in custody.

    BLOCKED-ON-JOB-SERVICE: hpc_ledger (the job record kind and its declared work table; the library
    ``jobs/hpc/gene_context_evidence/hpc_ledger.py::HPCLedger`` is a sqlite file outside the Store).
    Wanted call: ``ledger = HPCLedger.open_existing(store, owner_episode_id)``, an object over the parent's
    held ledger rows with ``commission``, ``read(id)``, ``records(kind)``, ``put(kind, body, identity=None)``,
    ``once(identity, kind, calculate)``, ``model_credit(model_ref, improvement)`` and ``credit_view()``.
    """
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: hpc_ledger; wanted call: HPCLedger.open_existing(ctx.store, '
                              'owner_episode_id) over the commissioning HPC parent\'s ledger rows held in custody')


def _memory(ctx):
    return ctx.settings.get('shared_execution_memory') is not None


def _resource(ctx, ledger):
    return ctx.settings['resources'][ledger.commission['resource_id']]


def _operands(arguments):
    return {name: value for name, value in arguments.items() if name != 'owner_episode_id'}


# ---------------------------------------------------------------------------------------------------------
# State of the model, history, candidates and comparisons over the ledger

def current_model(ledger):
    records = ledger.records('model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'


def quality(ledger, model):
    if not set(model['training_ids']) <= {row['id'] for row in ledger.commission['history']}:
        return None
    selected = [row for row in ledger.commission['history'] if row['id'] in ledger.commission['validation_ids']]
    return prediction.quality(model, selected) if selected else None


def candidates(ledger):
    return ledger.commission['candidates'] + [row['body'] for row in ledger.records('candidate')]


def features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def queue(ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def comparisons(ledger, model_ref, queue_ref):
    model = ledger.read(model_ref)
    observed = queue(ledger, queue_ref)
    actual = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
              if row['kind'] == 'actual']
    results = []
    for candidate in candidates(ledger):
        queue_features = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, features(candidate, queue_features))
        row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                 ledger.commission['preferences'], already_credited=actual)
        row['queue_features'] = queue_features
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def history(ledger):
    rows = {row['id']: row for row in ledger.commission['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()} - {None}
    for snapshot in ledger.records('shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    # Keep one latest observation per actual allocation, not one training example per poll. Failed unfinished
    # work retains a censored duration.
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


def shared_history(ledger, ctx):
    memory = ctx.services['estimate_table']
    commission = ledger.commission
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], _resource(ctx, ledger))
    # Queue timing is resource-wide. Work timing requires explicit matching algorithm, parameters, software and
    # hardware, never just 'Aurora'.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in memory.history(query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in memory.history(profile, now=now)})
    queues = {candidate['queue'] for candidate in candidates(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        row_queue = row.get('queue')
        # Different PBS queues are not interchangeable. Pool only when the portfolio has one matching queue, or
        # the model explicitly carries its categorical indicator.
        if 'queue' in row['metrics'] and not (row_queue and
                                              (queues == {row_queue} or 'queue:' + row_queue in model_features)):
            row['metrics'].pop('queue')
        if row_queue:
            row['features']['queue:' + row_queue] = 1.
        if row['metrics'] or row['success'] is not None:
            filtered.append(row)
    original = {row['id'] for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in commission['history']} - {None}
    return {'captured_at': now, 'policy': memory.as_record()['policy'],
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts]}


def observe_queue(ledger, ctx, configuration):
    memory = ctx.services['estimate_table'] if _memory(ctx) else None
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if memory:
        cached = memory.latest(resource, 'queue')
        if (cached['state'] == 'fresh' and cached['age_seconds'] <=
                ledger.commission['limits']['queue_max_age_seconds']):
            return cached['data']
    value = ctx.services['job_access'].observe_queue(configuration, key=ctx.operation_key)
    if memory:
        memory.observe(resource, 'queue', value, observed_at=value['snapshot']['captured_at'],
                       provenance=value['acquisition'])
    return value


def resolve_received_reference(store, run_id, reference, namespace):
    """True when ``reference`` is an HPC result Source this Episode holds and that belongs to this run; None when
    it is not an HPC result Source; False otherwise. What the Episode holds is what it received (custody)."""
    if not store.holds(reference):
        return None
    source = store.get(reference)
    if source.get('provider') != 'episode.hpc_result':
        return None
    if namespace not in (None, 'source'):
        return False
    body = json.loads(store.get_artifact(source['artifact_ref']))
    return body['run_id'] == run_id


def read_evidence(ctx, ledger, reference):
    rows_by_id = history(ledger)
    if reference in rows_by_id:
        return rows_by_id[reference]
    if not reference.startswith('source_'):
        return ledger.read(reference)
    # Results publish ordinary Store Sources as well as ledger receipts. Resolve only a received Source owned by
    # this original HPC ledger.
    rows = [row['body'] for row in ledger.records('result') if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or resolve_received_reference(ctx.store, ctx.run_id, reference, 'source') is not True:
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


def initialize(ledger, ctx):
    prior = prediction.prior_model(ledger.commission['model'])
    ledger.put('model', prior, identity='reference_model')
    if _memory(ctx):
        imported = ledger.once('shared_history_entry', 'shared_history', lambda: shared_history(ledger, ctx))
        if imported['observations'] and not ledger.records('model_choice'):
            model = prediction.fit(ledger.commission['model'], imported['observations'])
            reference = ledger.put('model', model)
            ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')

    def entry():
        current = current_model(ledger)
        return {'model_ref': current, 'quality': quality(ledger, ledger.read(current))}
    ledger.once('entry:' + ctx.episode_id, 'model_entry', entry)


def credit_inputs(ledger, ctx):
    """What this Episode's credit reads (credit has no services): the values of the ledger."""
    entries = ledger.records('model_entry')
    entry = next((row['body'] for row in entries if row['id'] == 'entry:' + ctx.episode_id), None)
    validation = sum(row['credit'] for row in ledger.credit_view()['contributions']
                     if row['kind'] == 'validation'
                     and ledger.read(row['evidence_id']).get('prediction_episode_id') == ctx.episode_id)
    return {'model_scale': ledger.commission['credit']['model_scale'],
            'entry_quality': None if entry is None else entry['quality'],
            'current_quality': quality(ledger, ledger.read(current_model(ledger))),
            'prospective_validation_credit': validation}


def ledger_view(ledger, ctx):
    """The ledger's state as the model and the report need it (the old decision-context block of the binding)."""
    model_ref = current_model(ledger)
    training_ids = sorted(set(history(ledger)) - set(ledger.commission['validation_ids']))
    view = {
        'hpc_candidates': candidates(ledger),
        'hpc_tool_request': [row['body'] for row in ledger.records('tool_request')],
        'hpc_model_ref': model_ref,
        'hpc_latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                   if key not in ('episode_id', 'operation_key')}}
                                  for row in ledger.records('comparison')[-1:]],
        'hpc_model_support': prediction.predict(ledger.read(model_ref), {})['support'],
        'hpc_plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                      for row in ledger.records('plan')],
        'hpc_latest_monitor': ledger.records('monitor')[-1:],
        'hpc_monitor_controllers': ledger.records('monitor_controller'),
        'hpc_queue_refs': [row['id'] for row in ledger.records('queue')],
        'hpc_available_training_ids': training_ids,
        'hpc_model_refs': [row['id'] for row in ledger.records('model')],
        'hpc_accepted_obligations': [row['slot'].removeprefix('actual:')
                                     for row in ledger.credit_view()['contributions'] if row['kind'] == 'actual'],
        'hpc_result_source_refs': [row['body']['source_ref'] for row in ledger.records('result')]}
    if _memory(ctx):
        view['hpc_shared_memory'] = ctx.services['estimate_table'].as_record()
        view['hpc_shared_history_refs'] = [row['id'] for row in ledger.records('shared_history')]
    return view


def _outcome(ledger, ctx, status, result, feedback=None):
    outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': result,
               'ledger_view': ledger_view(ledger, ctx), 'credit_inputs': credit_inputs(ledger, ctx)}
    if feedback is not None:
        outcome['feedback'] = feedback
    return outcome


def _invalid(error, **more):
    return {'category': 'arguments_or_reference', 'code': str(error), **more}


# ---------------------------------------------------------------------------------------------------------
# The tools

def hpc_initialize(arguments, ctx):
    """Open the ledger: the reference model, the shared history (with its first fitted model) and this
    Episode's entry quality. The first part of the task, before the model chooses anything."""
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    if not ledger.records('model'):
        initialize(ledger, ctx)
    return {**_outcome(ledger, ctx, 'completed', {'initialized': True}), 'commission': ledger.commission}


def hpc_read(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    try:
        result = read_evidence(ctx, ledger, arguments['reference'])
    except (ValueError, KeyError) as error:
        return _outcome(ledger, ctx, 'invalid', None, _invalid(error))
    return _outcome(ledger, ctx, 'completed', result)


def hpc_history_refresh(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    result = ledger.once('shared_history:' + ctx.operation_key, 'shared_history',
                         lambda: shared_history(ledger, ctx))
    return _outcome(ledger, ctx, 'completed', result)


def hpc_discovery_run(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    configuration = _resource(ctx, ledger)
    command = 'cd ' + shlex.quote(DISCOVERY_DIRECTORY) + ' && ' + arguments['command']

    def observe():
        memory = ctx.services['estimate_table'] if _memory(ctx) else None
        cache_key = (resource_identity(ledger.commission['resource_id'], configuration) + ':'
                     + hpc_queue.digest(command))
        if memory:
            cached = memory.latest(cache_key, 'inventory')
            if cached['state'] == 'fresh':
                return cached['data']
        value = ctx.services['job_access'].run_discovery(configuration, command, key=ctx.operation_key)
        if memory and value['returncode'] == 0:
            memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                           provenance=['hpc_ledger:' + arguments['owner_episode_id'],
                                       'discovery:' + ctx.operation_key])
        return value
    result = ledger.once('discovery:' + ctx.operation_key, 'discovery', observe)
    return _outcome(ledger, ctx, 'completed', result)


def hpc_candidate_propose(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    commission = ledger.commission
    try:
        candidate = json.loads(arguments['candidate_json'])
        known = candidates(ledger)
        prior = next((row for row in known if row['id'] == candidate['id']), None)
        if prior is not None and prior != candidate:
            raise ValueError('candidate_identity_is_immutable')
        validate_commission({**commission, 'candidates': known if prior else known + [candidate]},
                            ctx.settings['resources'])
    except (ValueError, KeyError, TypeError) as error:
        return _outcome(ledger, ctx, 'invalid', None, _invalid(error))
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates'] else
                 ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return _outcome(ledger, ctx, 'completed', {'candidate_ref': reference, 'candidate_id': candidate['id']})


def hpc_queue_observe(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    configuration = _resource(ctx, ledger)
    reference = 'queue:' + hpc_queue.digest(ctx.operation_key)
    result = ledger.once(reference, 'queue', lambda: observe_queue(ledger, ctx, configuration))
    result = {'queue_ref': reference,
              'features': [hpc_queue.features(result['snapshot'], candidate) for candidate in candidates(ledger)],
              'snapshot': result['snapshot']}
    return _outcome(ledger, ctx, 'completed', result)


def hpc_model_fit(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    commission = ledger.commission
    selected = set(arguments['training_ids'])
    if _memory(ctx):
        ledger.once('shared_history:' + ctx.operation_key, 'shared_history', lambda: shared_history(ledger, ctx))
    cases = history(ledger)
    if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
        return _outcome(ledger, ctx, 'invalid', None,
                        _invalid('training_ids_must_be_original_nonvalidation_cases'))
    heldout = [cases[key] for key in commission['validation_ids']]
    historical_selected = selected.intersection(row['id'] for row in commission['history'])
    if historical_selected and heldout and max(cases[key]['observed_at'] for key in historical_selected) >= min(
            row['observed_at'] for row in heldout):
        return _outcome(ledger, ctx, 'invalid', None, _invalid('training_must_precede_temporal_validation'))
    model = prediction.fit(commission['model'], [cases[key] for key in selected])
    model_ref = ledger.put('model', model)
    # Fixed historical validation cannot measure a model trained on later completed allocations. Those updates
    # earn prospective credit when the next real outcomes arrive, not retrospective Q.
    later_training = selected - set(row['id'] for row in commission['history'])
    model_quality = None if later_training else quality(ledger, model)
    baseline = quality(ledger, ledger.read('reference_model'))
    ledger.put('model_choice', {'operation_key': ctx.operation_key, 'model_ref': model_ref,
                                'episode_id': ctx.episode_id})
    if model_quality is not None:
        ledger.model_credit(model_ref, model_quality - baseline)
    else:
        ledger.model_credit(model_ref, 0.)
    result = {'model_ref': model_ref, 'validation_quality': model_quality, 'reference_quality': baseline,
              'credit': ledger.credit_view()}
    return _outcome(ledger, ctx, 'completed', result)


def hpc_compare(arguments, ctx):
    ledger = open_ledger(ctx.store, arguments['owner_episode_id'])
    operands = _operands(arguments)
    try:
        result = {'comparisons': comparisons(ledger, operands['model_ref'], operands['queue_ref'])}
    except (ValueError, KeyError) as error:
        return _outcome(ledger, ctx, 'invalid', None, _invalid(
            error, recovery='Use a model_ref from hpc_model_fit or hpc_model_ref and a queue_ref '
                            'from hpc_queue_observe or hpc_queue_refs; a resource identity is not a queue observation.'))
    result['comparison_ref'] = ledger.put('comparison', {**result, **operands, 'episode_id': ctx.episode_id,
                                                         'operation_key': ctx.operation_key})
    return _outcome(ledger, ctx, 'completed', result)


TOOLS = {'hpc_initialize': hpc_initialize, 'hpc_read': hpc_read, 'hpc_compare': hpc_compare,
         'hpc_history_refresh': hpc_history_refresh, 'hpc_discovery_run': hpc_discovery_run,
         'hpc_candidate_propose': hpc_candidate_propose, 'hpc_queue_observe': hpc_queue_observe,
         'hpc_model_fit': hpc_model_fit}


# ---------------------------------------------------------------------------------------------------------
# Deciding

def _instructions(summary, ctx):
    text = INSTRUCTIONS + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    if not summary['initialized']:
        return ToolCall('hpc_initialize', {'owner_episode_id': summary['owner_episode_id']})
    offered = catalog(_memory(ctx))
    launch = LaunchInstructions(ctx.settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(ctx.settings['tool_knowledge_directory'])
    commission = summary['commission']
    additions = {
        'goal': 'Improve the predicted resource needs of the planned HPC work',
        'hpc_commission': commission,
        'hpc_owner_episode_id': summary['owner_episode_id'],
        'hpc_resource': ctx.settings['resources'][commission['resource_id']],
        **summary['ledger'],
        'hpc_credit': summary['hpc_credit'],
        'current_credit': summary['credit'],
        'controller': summary['controller_state'],
        'requested_action_history': summary['requested_action_history'],
        'last_outcome': summary['last_outcome'],
        'feedback': feedback,
        'tools': offered,
        'tool_knowledge': knowledge.context(),
        'launch_instruction_library': launch.context(),
        'time': {'now': ctx.clock.now.isoformat(), 'elapsed_seconds': ctx.clock.elapsed_seconds}}
    if summary['launch_instructions'] is not None:
        additions['selected_launch_instructions'] = launch.materialize(summary['launch_instructions'])
    if 'execution_expectations' in ctx.settings:
        # BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call below (the old binding's execution expectations
        # for grain hpc_prediction, resource and native estimates, native event targets)
        additions['execution_expectations'] = ctx.services['estimate_table'].read(
            'execution_expectations', 'hpc_prediction')
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
              'properties': {'tool': {'type': 'string', 'enum': [entry['name'] for entry in offered]},
                             'arguments_json': {'type': 'string'}}}
    return ModelRequest('REASONING', _instructions(summary, ctx), additions, schema)


def action(response, summary, records, ctx):
    try:
        offered = {entry['name']: entry for entry in catalog(_memory(ctx))}
        name = response['tool']
        if name not in offered:
            raise ValueError('tool_not_available_to_hpc_role')
        arguments = json.loads(response['arguments_json'])
        Draft202012Validator(offered[name]['input_schema']).validate(arguments)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {**arguments, 'owner_episode_id': summary['owner_episode_id']})
