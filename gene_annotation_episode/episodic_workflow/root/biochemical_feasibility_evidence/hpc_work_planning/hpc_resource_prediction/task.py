"""The task: one selected tool per unit over the parent-owned HPC ledger: read evidence, refresh shared history,
run one read-only discovery command, propose a candidate portfolio, observe the PBS queue once, fit a model on
measured cases, compare the portfolios. There are no children and the only actions are tools (the old
``permitted_common_actions`` was ``('tool',)``).

Carried from the old ``task.py`` (``ResourcePredictionTask.next``, ``apply_response``, ``execute``),
``task_decision.py``, ``task_instructions.py``, ``prediction_operations.py`` (``catalog`` and ``execute``),
``prediction_state.py``, ``prediction_history.py``, ``portfolio_comparison.py``, ``queue_observations.py``,
``received_evidence.py``, ``decision_inputs.py`` and ``decision_state.py``. The old decision-exchange loop, the
``report_update`` the model wrote with each decision, the checkpoint/restore, the redelivery, the wait
(``waiting.py``) and the operation ledger (``ledger.cached``/``save_action``/``once``: the system's attempts
journal, ``ctx.operation_key``) are not carried (README 3a, 3b, 3e). The task always offers a unit and never ends
the Episode: ``action`` accepts a tool at every decision and rejects an answer that selects none.

The ledger. The old ``HPCLedger`` was a SQLite file of the parent that every sister opened by path. Here it is the
work table ``HPC_EVIDENCE`` (``evidence_id``, ``kind``, ``body``), under custody: this Episode reads the rows its
parent named in ``ledger_refs`` and the rows it wrote itself (``read_ledger``). Evidence is immutable by
``evidence_id`` (``put_evidence`` raises ``immutable_hpc_evidence_conflict``). The credit slots of the old
``credits`` table are rows of kind ``credit`` (``evidence_id`` ``credit:<slot>``, a rewrite is the next revision,
as the old ``INSERT OR REPLACE``). The old ``forecast_slots`` table is the parent's and is not read here.

Settings this episode reads (``ctx.settings``): ``resources`` (the configured resources by id, the old
``configuration.resources``; the commission names one), ``shared_execution_memory`` (present when the shared
execution memory is configured: the tool ``hpc_history_refresh`` is then offered; the memory itself is the
``estimate_table`` service), ``launch_instructions_directory`` and ``knowledge_library_directory`` (optional: the
libraries whose context is shown to the model); ``cost`` and ``parameters`` (``yield_estimator.py``).

BLOCKED-ON-JOB-SERVICE: the remote reads (one discovery command and one PBS/ALCF queue observation) are the
service ``job_access``, and the shared execution memory (``ExecutionMemory``: ``latest``, ``observe``, ``history``,
``as_record``) is the service ``estimate_table``; no service wraps either. ``_blocked`` names the service and the
call wanted and raises where it is reached. The old fixed ``subprocess.run(..., timeout=90)`` of the discovery is not
carried (an elapsed-time cutoff); its stdout/stderr byte cuts (65536, 8192) are not carried either. The old
cut of the shared observations to 2000 is not carried.

Tool names. A tool name is ``[a-z][a-z0-9_]*``: the old ``hpc.read`` is ``hpc_read``, ``hpc.compare`` is
``hpc_compare``, ``hpc.history.refresh`` is ``hpc_history_refresh``, ``hpc.discovery.run`` is
``hpc_discovery_run``, ``hpc.candidate.propose`` is ``hpc_candidate_propose``, ``hpc.queue.observe`` is
``hpc_queue_observe``, ``hpc.model.fit`` is ``hpc_model_fit``.

Not found in the library, so not called (listed as unplaced): the old prompt renderer ``render_hpc_prompt`` and its
``is_hpc_context``, ``resource_information`` (old ``initial_information``), ``completed_action_reports``,
``requested_action_history`` (here the outcome page of the Episode's own outcomes), the resource estimator and
execution expectations, the contract-information profile and ``hpc_commission_sources.read`` (no A110 copy)."""
import json
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, TableDeclaration, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence.hpc_campaign import (
    validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence.hpc_resource_prediction import (
    physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from . import goal as goal_file
from .credit import quality

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

HPC_EVIDENCE = TableDeclaration(name='hpc_evidence', columns=('evidence_id', 'kind', 'body'), key=('evidence_id',))
PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'
MODEL_ROLE = 'REASONING'
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'hpc_prediction_argument_transport_not_carried'}
ACTION_BOUNDARY = 'Do not emit a stop action or invent a turn budget; select exactly one tool.\n'

TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _blocked(service, call):
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: ' + service + '; wanted call: ' + call)


def memory_configured(settings):
    return settings.get('shared_execution_memory') is not None


# ---- the parent-owned ledger, under custody (old HPCLedger, PredictionState.state) -------------------------------

def read_ledger(reader):
    """Every held row of ``hpc_evidence`` as the old ledger's reads: ``records[kind]`` (``{'id', 'body'}`` in receipt
    order), ``by_id`` (the latest row of each evidence identity), the credit slots (the latest row of each slot) and
    the commission. A missing commission raises the old error."""
    records, by_id, slots = {}, {}, {}
    for row in reader.table(HPC_EVIDENCE).select():
        entry = {'id': row['evidence_id'], 'kind': row['kind'], 'body': row['body']}
        records.setdefault(row['kind'], []).append({'id': entry['id'], 'body': entry['body']})
        by_id[row['evidence_id']] = entry
        if row['kind'] == 'credit':
            slots[row['body']['slot']] = row['body']
    if 'commission' not in by_id:
        raise ValueError('original_hpc_commission_missing')
    credits = [{'slot': slot, 'kind': body['kind'], 'credit': body['value'], 'evidence_id': body['evidence_id']}
               for slot, body in sorted(slots.items())]
    return {'commission': by_id['commission']['body'], 'owner': by_id.get('owner', {}).get('body'),
            'records': records, 'by_id': by_id, 'credits': credits}


def records_of(ledger, kind):
    return ledger['records'].get(kind, [])


def read(ledger, identity):
    """The old ``ledger.read``; ``reference_model`` is the prior model of the commission's model specification."""
    if identity in ledger['by_id']:
        return ledger['by_id'][identity]['body']
    if identity == 'reference_model':
        return prediction.prior_model(ledger['commission']['model'])
    raise ValueError('unknown_hpc_evidence:' + identity)


def credit_view(ledger):
    components = {kind: sum(row['credit'] for row in ledger['credits'] if row['kind'] == kind)
                  for kind in ('actual', 'model', 'validation')}
    return {'credit': sum(components.values()), 'components': components, 'contributions': ledger['credits']}


def put_evidence(store, evidence_id, kind, body):
    """The old ``HPCLedger._put``: evidence is immutable by identity; the row is written through custody."""
    held = store.table(HPC_EVIDENCE).select({'evidence_id': evidence_id})
    if held and (held[-1]['kind'], hpc_queue.canonical(held[-1]['body'])) != (kind, hpc_queue.canonical(body)):
        raise ValueError('immutable_hpc_evidence_conflict:' + evidence_id)
    store.table(HPC_EVIDENCE).put({'evidence_id': evidence_id, 'kind': kind, 'body': body})
    return evidence_id


def check_owner(ledger, parent_input):
    """The old ``PredictionState.state`` check that the ledger is the original one of the assignment's owner (its
    scope comparison is not carried: no scope reaches this episode)."""
    owner = ledger['owner']
    identity = {key: parent_input[key] for key in ('commission_id', 'commission_source_ref') if key in parent_input}
    if (owner is None or owner['episode_id'] != parent_input['owner_episode_id']
            or {key: owner[key] for key in ('commission_id', 'commission_source_ref') if key in owner} != identity):
        raise ValueError('sister_scope_must_equal_original_parent_scope')
    return ledger


def current_model(ledger):
    """The old ``PredictionState._current_model`` over the model choices the Episode holds."""
    choices = records_of(ledger, 'model_choice')
    return choices[-1]['body']['model_ref'] if choices else 'reference_model'


# ---- history, candidates, queue, comparison (old PredictionHistory, PortfolioComparison, QueueObservations) -------

def history(ledger):
    rows = {row['id']: row for row in ledger['commission']['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()} - {None}
    for snapshot in records_of(ledger, 'shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in records_of(ledger, 'plan')}
    closed = {row['body']['plan_id'] for row in records_of(ledger, 'closed')}
    # One latest observation per actual allocation, not one training example per poll. Failed unfinished work
    # retains a censored duration.
    latest = {}
    for row in records_of(ledger, 'measured'):
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
    commission = ledger['commission']
    profile = commission.get('execution_profile')
    resources = ctx.settings['resources']
    resource = resource_identity(commission['resource_id'], resources[commission['resource_id']])
    # Queue timing is resource-wide. Work timing requires explicit matching algorithm, parameters, software and
    # hardware, never just 'Aurora'.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in _blocked(
        'estimate_table', "ctx.services['estimate_table'].history(query, now=now, queue_only=True)")}
    if profile:
        rows.update({row['id']: row for row in _blocked(
            'estimate_table', "ctx.services['estimate_table'].history(profile, now=now)")})
    queues = {candidate['queue'] for candidate in candidates(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        queue = row.get('queue')
        # Different PBS queues are not interchangeable. Pool only when the portfolio has one matching queue, or
        # the model explicitly carries its categorical indicator.
        if 'queue' in row['metrics'] and not (queue and (queues == {queue} or 'queue:' + queue in model_features)):
            row['metrics'].pop('queue')
        if queue:
            row['features']['queue:' + queue] = 1.
        if row['metrics'] or row['success'] is not None:
            filtered.append(row)
    original = {row['id'] for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in commission['history']} - {None}
    return {'captured_at': now,
            'policy': _blocked('estimate_table', "ctx.services['estimate_table'].as_record()['policy']"),
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts]}


def candidates(ledger):
    return ledger['commission']['candidates'] + [row['body'] for row in records_of(ledger, 'candidate')]


def candidate_features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def comparisons(ledger, model_ref, queue_ref):
    model = read(ledger, model_ref)
    observed = queue_observation(ledger, queue_ref)
    actual = [row['slot'].removeprefix('actual:') for row in ledger['credits'] if row['kind'] == 'actual']
    results = []
    for candidate in candidates(ledger):
        queue = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, candidate_features(candidate, queue))
        row = prediction.compare(candidate, forecast, ledger['commission']['obligations'],
                                 ledger['commission']['preferences'], already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def observe_queue(ctx, ledger, configuration):
    commission = ledger['commission']
    resource = resource_identity(commission['resource_id'], configuration)
    if memory_configured(ctx.settings):
        cached = _blocked('estimate_table', "ctx.services['estimate_table'].latest(resource, 'queue')")
        if cached['state'] == 'fresh' and cached['age_seconds'] <= commission['limits']['queue_max_age_seconds']:
            return cached['data']
    value = _blocked('job_access', "ctx.services['job_access'].observe_queue(configuration, "
                                   "key=ctx.operation_key), the old hpc_queue.observe(configuration)")
    if memory_configured(ctx.settings):
        _blocked('estimate_table', "ctx.services['estimate_table'].observe(resource, 'queue', value, "
                                   "observed_at=value['snapshot']['captured_at'], provenance=value['acquisition'])")
    return value


def queue_observation(ledger, reference, *, require_fresh=False):
    observation = read(ledger, reference)['snapshot']
    if require_fresh and (time.time() - observation['captured_at']
                          > ledger['commission']['limits']['queue_max_age_seconds']):
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def read_evidence(ctx, ledger, reference):
    """The old ``ReceivedEvidence.read_evidence`` (and ``resolve_received_reference``): history, ledger evidence, or
    a result Source this episode holds and this ledger owns."""
    cases = history(ledger)
    if reference in cases:
        return cases[reference]
    if not reference.startswith('source_'):
        return read(ledger, reference)
    # Results publish ordinary Store Sources as well as ledger receipts: only a received Source owned by this ledger.
    rows = [row['body'] for row in records_of(ledger, 'result') if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or not _result_source_received(ctx, reference):
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


def _result_source_received(ctx, reference):
    if not ctx.store.holds(reference):
        return False
    source = ctx.store.get(reference)
    if source.get('provider') != 'episode.hpc_result':
        return False
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    if body['run_id'] != ctx.run_id:
        return False
    try:
        ctx.store.validate_scope(body['scope'])
    except ValueError:
        return False
    return True


# ---- the tools (old PredictionOperations.execute) ---------------------------------------------------------------

def _completed(result):
    return {'status': 'completed', 'result': result}


def _invalid(error, **feedback):
    return {'status': 'invalid', 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **feedback}}


def hpc_read(arguments, ctx):
    ledger = read_ledger(ctx.store)
    try:
        return _completed(read_evidence(ctx, ledger, arguments['reference']))
    except (ValueError, KeyError) as error:
        return _invalid(error)


def hpc_history_refresh(arguments, ctx):
    if not memory_configured(ctx.settings):
        raise ValueError('tool_not_available_to_hpc_role')
    ledger = read_ledger(ctx.store)
    identity = 'shared_history:' + ctx.operation_key
    held = ledger['by_id'].get(identity)
    value = held['body'] if held else shared_history(ctx, ledger)
    if held is None:
        put_evidence(ctx.store, identity, 'shared_history', value)
    return _completed(value)


def hpc_discovery_run(arguments, ctx):
    # Read-only discovery can be repeated after an interrupted observation; all mutations and submissions belong to
    # the launch operations of the execution sister.
    ledger = read_ledger(ctx.store)
    commission = ledger['commission']
    configuration = ctx.settings['resources'][commission['resource_id']]
    identity = 'discovery:' + ctx.operation_key
    held = ledger['by_id'].get(identity)
    if held:
        return _completed(held['body'])
    command = 'cd ' + shlex.quote(PROJECT_DIRECTORY) + ' && ' + arguments['command']
    cache_key = resource_identity(commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
    if memory_configured(ctx.settings):
        cached = _blocked('estimate_table', "ctx.services['estimate_table'].latest(cache_key, 'inventory')")
        if cached['state'] == 'fresh':
            put_evidence(ctx.store, identity, 'discovery', cached['data'])
            return _completed(cached['data'])
    completed = _blocked('job_access', "ctx.services['job_access'].run_discovery(configuration, command, "
                                       "key=ctx.operation_key), returning returncode, stdout and stderr (bytes)")
    value = {'command': arguments['command'], 'returncode': completed.returncode,
             'stdout': completed.stdout.decode('utf-8', 'replace'),
             'stderr': completed.stderr.decode('utf-8', 'replace'),
             'observed_at': time.time()}
    if memory_configured(ctx.settings) and completed.returncode == 0:
        _blocked('estimate_table', "ctx.services['estimate_table'].observe(cache_key, 'inventory', value, "
                                   "observed_at=value['observed_at'], provenance=[identity])")
    put_evidence(ctx.store, identity, 'discovery', value)
    return _completed(value)


def hpc_candidate_propose(arguments, ctx):
    ledger = read_ledger(ctx.store)
    commission = ledger['commission']
    try:
        candidate = json.loads(arguments['candidate_json'])
        held = candidates(ledger)
        prior = next((row for row in held if row['id'] == candidate['id']), None)
        if prior is not None and prior != candidate:
            raise ValueError('candidate_identity_is_immutable')
        validate_commission({**commission, 'candidates': held if prior else held + [candidate]},
                            ctx.settings['resources'])
    except (ValueError, KeyError, TypeError) as error:
        return _invalid(error)
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates'] else
                 put_evidence(ctx.store, 'candidate:' + candidate['id'], 'candidate', candidate))
    return _completed({'candidate_ref': reference, 'candidate_id': candidate['id']})


def hpc_queue_observe(arguments, ctx):
    ledger = read_ledger(ctx.store)
    commission = ledger['commission']
    configuration = ctx.settings['resources'][commission['resource_id']]
    reference = 'queue:' + hpc_queue.digest(ctx.operation_key)
    held = ledger['by_id'].get(reference)
    value = held['body'] if held else observe_queue(ctx, ledger, configuration)
    if held is None:
        put_evidence(ctx.store, reference, 'queue', value)
    return _completed({'queue_ref': reference,
                       'features': [hpc_queue.features(value['snapshot'], candidate)
                                    for candidate in candidates(ledger)],
                       'snapshot': value['snapshot']})


def hpc_model_fit(arguments, ctx):
    ledger = read_ledger(ctx.store)
    commission = ledger['commission']
    if memory_configured(ctx.settings):
        hpc_history_refresh({}, ctx)
        ledger = read_ledger(ctx.store)
    cases = history(ledger)
    training = list(dict.fromkeys(arguments['training_ids']))
    selected = set(training)
    if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
        raise ValueError('training_ids_must_be_original_nonvalidation_cases')
    heldout = [cases[key] for key in commission['validation_ids']]
    historical_selected = selected.intersection(row['id'] for row in commission['history'])
    if historical_selected and heldout and (max(cases[key]['observed_at'] for key in historical_selected)
                                            >= min(row['observed_at'] for row in heldout)):
        raise ValueError('training_must_precede_temporal_validation')
    model = prediction.fit(commission['model'], [cases[key] for key in training])
    model_ref = put_evidence(ctx.store, 'model_' + hpc_queue.digest(model), 'model', model)
    # Fixed historical validation cannot measure a model trained on later completed allocations. Those updates
    # earn prospective credit when the next real outcomes arrive, not retrospective quality.
    later_training = selected - {row['id'] for row in commission['history']}
    measured = None if later_training else quality(ledger, model)
    baseline = quality(ledger, read(ledger, 'reference_model'))
    choice = {'operation_key': ctx.operation_key, 'model_ref': model_ref, 'episode_id': ctx.episode_id}
    put_evidence(ctx.store, 'model_choice_' + hpc_queue.digest(choice), 'model_choice', choice)
    improvement = measured - baseline if measured is not None else 0.
    # A new model replaces the projection, including negative corrections (the same slot, the next revision).
    slot = {'slot': 'model', 'kind': 'model', 'value': commission['credit']['model_scale'] * improvement,
            'evidence_id': model_ref}
    put_evidence_slot(ctx.store, slot)
    ledger = read_ledger(ctx.store)
    return _completed({'model_ref': model_ref, 'validation_quality': measured, 'reference_quality': baseline,
                       'credit': credit_view(ledger)})


def put_evidence_slot(store, slot):
    """The old ``HPCLedger.model_credit``: ``INSERT OR REPLACE`` of one credit slot (the next revision of its row)."""
    store.table(HPC_EVIDENCE).put({'evidence_id': 'credit:' + slot['slot'], 'kind': 'credit', 'body': slot})


def hpc_compare(arguments, ctx):
    ledger = read_ledger(ctx.store)
    try:
        result = {'comparisons': comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
    except (ValueError, KeyError) as error:
        return _invalid(error, recovery='Use a model_ref from hpc_model_fit or hpc_model_ref and a queue_ref '
                                        'from hpc_queue_observe or hpc_queue_refs; a resource identity is not a '
                                        'queue observation.')
    body = {**result, **arguments, 'episode_id': ctx.episode_id, 'operation_key': ctx.operation_key}
    result['comparison_ref'] = put_evidence(ctx.store, 'comparison_' + hpc_queue.digest(body), 'comparison', body)
    return _completed(result)


TOOLS = {'hpc_read': hpc_read, 'hpc_compare': hpc_compare, 'hpc_history_refresh': hpc_history_refresh,
         'hpc_discovery_run': hpc_discovery_run, 'hpc_candidate_propose': hpc_candidate_propose,
         'hpc_queue_observe': hpc_queue_observe, 'hpc_model_fit': hpc_model_fit}


# ---- deciding ---------------------------------------------------------------------------------------------------

def catalog(memory):
    """The tools offered (old ``PredictionOperations.catalog``); the history refresh only with shared memory."""
    entries = [
        ('hpc_read', 'Read retained HPC evidence by its exact identity.', _object({'reference': TEXT})),
        ('hpc_compare', 'Compare all approved portfolios; no work is selected or launched.',
         _object({'model_ref': TEXT, 'queue_ref': TEXT}))]
    if memory:
        entries.append(('hpc_history_refresh', 'Read age-weighted shared timing history once. No remote '
                        'discovery, polling credit, or new scientific work.', _object({})))
    entries += [
        ('hpc_discovery_run', 'Run one lightweight remote inspection or documentation retrieval through the '
         'established SSH transport. No job submission, installation or scientific computation; those belong to '
         'Launch and the allocation.', _object({'command': TEXT})),
        ('hpc_candidate_propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON '
         'with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including '
         'worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing '
         'actual allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional '
         'reports_progress), optional files [{path: relative path, text: exact contents}], and preparation '
         'instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; '
         'workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the '
         'eventual directory. Existing candidate identities are immutable.',
         _object({'candidate_json': TEXT})),
        ('hpc_queue_observe', 'Acquire PBS queue and ALCF score/status once and transform them.', _object({})),
        ('hpc_model_fit', 'Fit selected measured history; validate on the fixed disjoint cases.',
         _object({'training_ids': STRINGS}))]
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]


def selection_schema(tools):
    options = [_object({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                        'arguments': entry['input_schema']}) for entry in tools]
    return _object({'selection': {'anyOf': options}})


def instructions(summary, settings):
    text = goal_file.GOAL + '\n' + ACTION_BOUNDARY
    if settings.get('knowledge_library_directory') is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if settings.get('launch_instructions_directory') is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    settings = ctx.settings
    tools = catalog(memory_configured(settings))
    outcomes = summary['outcomes']
    context = {
        'goal': summary['hpc_goal'],
        **summary['decision_context'],
        'hpc_resource': settings['resources'][summary['decision_context']['hpc_commission']['resource_id']],
        'tools': tools,
        'last_local_outcome': outcomes[-1] if outcomes else None,
        'requested_action_history': outcome_page(outcomes, offset=0, limit=max(1, len(outcomes))),
        'feedback': feedback,
        'current_credit': summary['decision_context']['hpc_credit']['credit'],
        'hpc_credit_components': summary['credit_components'],
        'controller': summary['controller'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
    }
    if memory_configured(settings):
        context = extend_context(context, {'hpc_shared_memory': ctx.services['estimate_table'].read('as_record')},
                                 conflict='initial_binding_context_field_conflict')
    library = settings.get('launch_instructions_directory')
    if library is not None:
        launch = LaunchInstructions(library)
        context = extend_context(context, {
            'launch_instruction_library': launch.context(),
            'selected_launch_instructions': launch.materialize(summary['launch_instructions'])},
            conflict='initial_binding_context_field_conflict')
    knowledge = settings.get('knowledge_library_directory')
    if knowledge is not None:
        context = extend_context(context, {'tool_knowledge': ToolKnowledge(knowledge).context()},
                                 conflict='initial_binding_context_field_conflict')
    return ModelRequest(MODEL_ROLE, instructions(summary, settings), context,
                        strict_output_schema(selection_schema(tools), **TRANSPORT))


def action(response, summary, records, ctx):
    schema = selection_schema(catalog(memory_configured(ctx.settings)))
    try:
        decoded = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selected = decoded['selection']
    return ToolCall(selected['tool'], selected['arguments'])
