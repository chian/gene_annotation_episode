"""A107 HPC work planning and resource prediction on the generic runner (``episode_runtime``).

Bound by ``hpc_work_planning`` (role ``hpc``) and its sister leaf
``hpc_work_planning/hpc_resource_prediction`` (role ``hpc_prediction``). Each
unit is selected by the model collaborator from the Episode's actual HPC state
and executed over the commission's own HPC ledger (``episode_support/jobs/hpc/partner_presence_evidence/hpc_ledger.py``):

- ``hpc``: read retained evidence, refresh shared timing history, run one
  lightweight remote discovery command, propose a candidate portfolio, observe
  the PBS queue once, compare portfolios, freeze a plan with its forecasts, or
  commission ``hpc_resource_prediction`` over its own ledger;
- ``hpc_prediction``: the shared operations above (no plan) and ``hpc.model.fit``.

Every executed outcome, including an invalid one, is recorded
(``outcome.<position>``) and enters the iterator with the credit measured after
it and the Episode's progress receipt. A response that fails admission creates
no unit; the model decides again with that feedback.

Credit is the ledger's own projection and is never bounded, clamped or rescaled:
``hpc`` reads ``HPCLedger.credit_view()`` (accepted accomplishment, model
improvement and prospective validation); ``hpc_prediction`` reads its model
quality gain since its entry plus the validation credit of forecasts made with
its models. Continuation is one ``AccumulationYieldController`` per Episode from
the commission's own ``yield_bindings[role]``.

Runtime collaborators (each required): ``model_provider`` and ``store``
(standard) and ``a107_hpc`` (an ``HPCServices``: the configured HPC resources,
the ledger directory and the shared execution memory or explicitly none).

Binding a launch handoff to a frozen plan, observing that job, parsing its
allocation results and reordering its units are operations of
``hpc_allocation_execution`` (``allocation_runtime``), not of these roles. The
``hpc`` role commissions only its ``hpc_prediction`` sister; its launch,
monitor, results and ``hpc_execution`` slots are declared but not commissioned
by it.

A parent's per-commission typed report form (C5) may add any of the role's finding fields
(``PLANNING_REPORT_FIELDS``) at the top level of its result; any other added field raises when the
Episode is built.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import shlex
import subprocess
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Commission
from method_loop import ChildEpisodeUnit, ClosedRecord, Episode, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_campaign import build_plan, validate_commission
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_resource_prediction import physical_attempt_key

AXIS = 'a107'
SERVICES = AXIS + '_hpc'
MODEL_ROLE = 'REASONING'
PLANNING, PREDICTION = 'hpc', 'hpc_prediction'
PREDICTION_SLOT = 'hpc_prediction'
# This axis's descendant assignment field holding the commissioning parent's typed HPC assignment.
ROLE_FIELD = 'assignment'
# The report this binding asks of the prediction sister it commissions.
REPORT = {'decision': 'Use the child finding in the parent cycle',
          'measurements': {'credit': "The child's own credit on its own scale"},
          'information': {'finding': 'What the child established, with its record references'}}
# The field of this axis's descendant return form that carries its finding.
FINDING = 'finding'
REMOTE_PROJECT = '/lus/flare/projects/BioReason-Aurora-Test'
_TEXT = {'type': 'string', 'minLength': 1}
_STRINGS = {'type': 'array', 'uniqueItems': True, 'items': _TEXT}


class HPCRuntimeError(ValueError):
    """An HPC collaborator, assignment or decision does not satisfy this binding's contract."""


def obj(properties, required=None):
    return {'type': 'object', 'additionalProperties': False, 'properties': properties,
            'required': list(properties) if required is None else list(required)}


def plain(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


@dataclass(frozen=True)
class HPCRecord(ClosedRecord):
    """A plain JSON record: a unit's controller input, a request message or a result."""
    value: Mapping

    def as_record(self):
        return deepcopy(dict(self.value))


class HPCServices:
    """The configured HPC resources, the ledger directory and the shared execution memory (or none)."""

    def __init__(self, *, resources, directory, shared_execution_memory):
        self.resources = plain(resources)
        if not isinstance(self.resources, dict) or not any(
                isinstance(row, dict) and row.get('kind') == 'pbs_ssh' for row in self.resources.values()):
            raise HPCRuntimeError(AXIS + '_hpc_configured_pbs_resource_required')
        self.directory = Path(directory)
        if shared_execution_memory is None:
            self.memory = None
        else:
            from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.execution_memory import ExecutionMemory
            self.memory = ExecutionMemory(**plain(shared_execution_memory))


def services_of(collaborators):
    value = collaborators[SERVICES]
    if not isinstance(value, HPCServices):
        raise HPCRuntimeError(AXIS + '_hpc_services_collaborator_must_be_HPCServices')
    return value


def _validate(value, schema, code):
    try:
        Draft202012Validator(schema).validate(value)
    except ValidationError as error:
        raise HPCRuntimeError(code + ':' + error.message) from error
    return value


# -- the ledger ------------------------------------------------------------------------------------------------

def _ledger_directory(services, run_id, owner):
    return services.directory / 'hpc' / hpc_queue.digest([run_id, owner])


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
    # One latest observation per actual closed allocation, not one training example per poll.
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


def _shared_history(services, ledger):
    from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.execution_guidance import resource_identity
    commission = ledger.commission
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], services.resources[commission['resource_id']])
    # Queue timing is resource-wide; work timing requires an explicit matching profile.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in services.memory.history(query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in services.memory.history(profile, now=now)})
    queues = {candidate['queue'] for candidate in _candidates(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        queue = row.get('queue')
        # Different PBS queues are not interchangeable: pool only one matching queue or a modelled indicator.
        if 'queue' in row['metrics'] and not (queue and (queues == {queue} or 'queue:' + queue in model_features)):
            row['metrics'].pop('queue')
        if queue:
            row['features']['queue:' + queue] = 1.
        if row['metrics'] or row['success'] is not None:
            filtered.append(row)
    original = {row['id'] for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in commission['history']} - {None}
    return {'captured_at': now, 'policy': services.memory.as_record()['policy'],
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts][:2000]}


def _initialize(services, ledger):
    """The fixed reference model and, with shared memory, the model fitted on imported history."""
    ledger.put('model', prediction.prior_model(ledger.commission['model']), identity='reference_model')
    if services.memory is not None:
        imported = ledger.once('shared_history_entry', 'shared_history', lambda: _shared_history(services, ledger))
        if imported['observations'] and not ledger.records('model_choice'):
            reference = ledger.put('model', prediction.fit(ledger.commission['model'], imported['observations']))
            ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')


def planning_assignment(role_assignment, services):
    value = _validate(plain(role_assignment), obj({'commission': {'type': 'object'}}),
                      AXIS + '_hpc_role_assignment_requires_exactly_commission')
    commission = validate_commission(value['commission'], services.resources)
    if 'yield_bindings' not in commission:
        raise HPCRuntimeError(AXIS + '_hpc_commission_yield_bindings_required')
    return commission


def open_ledger(role, bound, services, store):
    """The commission's ledger: created by the ``hpc`` owner, opened by its prediction sister."""
    scope = plain(bound.assignment['scope'])
    if plain(store.validate_scope(scope)) != scope:
        raise HPCRuntimeError(AXIS + '_hpc_scope_must_be_store_admitted')
    if role == PLANNING:
        commission = planning_assignment(bound.assignment[ROLE_FIELD], services)
        ledger = HPCLedger(_ledger_directory(services, bound.run_id, bound.episode_id), commission)
        ledger.put('owner', {'run_id': bound.run_id, 'episode_id': bound.episode_id, 'scope': scope}, identity='owner')
    else:
        value = _validate(plain(bound.assignment[ROLE_FIELD]), obj({'owner_episode_id': _TEXT}),
                          AXIS + '_hpc_prediction_role_assignment_requires_exactly_owner_episode_id')
        ledger = HPCLedger.open_existing(_ledger_directory(services, bound.run_id, value['owner_episode_id']))
        owner = ledger.read('owner')
        if owner['run_id'] != bound.run_id or owner['episode_id'] != value['owner_episode_id'] \
                or owner['scope'] != scope:
            raise HPCRuntimeError(AXIS + '_hpc_prediction_must_share_its_owner_run_and_scope')
    if not ledger.records('model'):
        _initialize(services, ledger)
    if role == PREDICTION:
        def entry():
            current = _current_model(ledger)
            return {'model_ref': current, 'quality': _quality(ledger, ledger.read(current))}
        ledger.once('entry:' + bound.episode_id, 'model_entry', entry)
    return ledger, scope


def credit_view(role, ledger, episode_id):
    if role == PLANNING:
        return ledger.credit_view()
    entry = ledger.read('entry:' + episode_id)
    current = _quality(ledger, ledger.read(_current_model(ledger)))
    gain = current - entry['quality'] if current is not None and entry['quality'] is not None else 0.
    validation = sum(row['credit'] for row in ledger.credit_view()['contributions']
                     if row['kind'] == 'validation'
                     and ledger.read(row['evidence_id']).get('prediction_episode_id') == episode_id)
    return {'credit': ledger.commission['credit']['model_scale'] * gain + validation,
            'model_quality_improvement': gain, 'prospective_validation_credit': validation,
            'actual_job_credit_counted_here': False}


def controller(role, bound, collaborators):
    from yield_control import AccumulationYieldController, YieldParameters
    ledger, _ = open_ledger(role, bound, services_of(collaborators), collaborators['store'])
    binding = ledger.commission['yield_bindings'][role]
    initial = credit_view(role, ledger, bound.episode_id)['credit']
    if not math.isfinite(initial):
        raise HPCRuntimeError(AXIS + '_hpc_initial_credit_not_finite')
    return AccumulationYieldController(role, initial, binding['cutoff'], YieldParameters(**binding['parameters']))


# -- operations ------------------------------------------------------------------------------------------------

def catalog(role, services):
    entries = [
        ('hpc.read', 'Read retained HPC evidence or a measured history case by its exact identity.',
         obj({'reference': _TEXT})),
        ('hpc.compare', 'Compare all approved portfolios; no work is selected or launched.',
         obj({'model_ref': _TEXT, 'queue_ref': _TEXT}))]
    if services.memory is not None:
        entries.append(('hpc.history.refresh', 'Read age-weighted shared timing history once. No remote discovery, '
                        'polling credit, or new scientific work.', obj({})))
    entries += [
        ('hpc.discovery.run', 'Run one lightweight remote inspection or documentation retrieval through the '
         'established SSH transport. No job submission, installation or scientific computation.',
         obj({'command': _TEXT})),
        ('hpc.candidate.propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON '
         'with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including '
         'worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes}, units (unit_id, '
         'obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: relative '
         'path, text: exact contents}], and preparation instructions. effort is a positive finite number of '
         'relative work. Use {allocation_workspace} for the eventual directory. Candidate identities are immutable.',
         obj({'candidate_json': _TEXT})),
        ('hpc.queue.observe', 'Acquire PBS queue and ALCF score/status once and transform them.', obj({}))]
    if role == PLANNING:
        entries.append(('hpc.plan', 'Freeze one useful portfolio and its forecasts; return its concrete launch '
                        'assignment.', obj({'candidate_id': _TEXT, 'model_ref': _TEXT, 'queue_ref': _TEXT})))
    else:
        entries.append(('hpc.model.fit', 'Fit selected measured history; validate on the fixed disjoint cases.',
                        obj({'training_ids': _STRINGS})))
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in entries]


def _features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def _queue(ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def _observe_queue(services, ledger, configuration):
    from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.execution_guidance import resource_identity
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if services.memory is not None:
        cached = services.memory.latest(resource, 'queue')
        if cached['state'] == 'fresh' and cached['age_seconds'] <= ledger.commission['limits']['queue_max_age_seconds']:
            return cached['data']
    value = hpc_queue.observe(configuration)
    if services.memory is not None:
        services.memory.observe(resource, 'queue', value, observed_at=value['snapshot']['captured_at'],
                                provenance=value['acquisition'])
    return value


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


def _freeze(ledger, plan, predicted, reference, operation_key):
    elapsed = {'queue': 0., 'work': 0.}
    slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
             if slot['phase'] == 'planned'
             and elapsed.get(slot['metric'], elapsed['work']) >= slot['minimum_elapsed_seconds']
             and prediction.forecast_metric(predicted, slot['metric']) is not None]
    body = ledger.once('issued:' + operation_key, 'forecast_issue', lambda: {
        'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted, 'reference': reference,
        'phase': 'planned', 'elapsed': elapsed, 'model_ref': plan.get('model_ref'),
        'prediction_episode_id': plan.get('prediction_episode_id')})
    return ledger.freeze(body, slots)


def _plan(ledger, configuration, arguments, operation_key):
    existing = ledger.records('plan')
    own = next((row for row in existing if row['body'].get('operation_key') == operation_key), None)
    if own is not None:
        plan, plan_ref = own['body'], own['id']
    else:
        observed = _queue(ledger, arguments['queue_ref'], require_fresh=True)
        matches = [row for row in _candidates(ledger) if row['id'] == arguments['candidate_id']]
        if len(matches) != 1:
            raise ValueError('unknown_candidate:' + arguments['candidate_id'])
        candidate = matches[0]
        queue = hpc_queue.features(observed, candidate)
        rules = queue['queue_rules']
        if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
            raise ValueError('choose_an_observed_enabled_execution_queue')
        for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
            if (rules['min_' + key] is not None and value < rules['min_' + key]
                    or rules['max_' + key] is not None and value > rules['max_' + key]):
                raise ValueError('candidate_violates_observed_queue_limits')
        plan = build_plan(ledger.commission, candidate, configuration, ledger.read('owner'), len(existing))
        features = _features(candidate, queue)
        predicted = prediction.predict(ledger.read(arguments['model_ref']), features)
        reference = prediction.predict(ledger.read('reference_model'), features)
        plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'],
                    original_prediction=predicted, original_reference=reference, operation_key=operation_key)
        choices = [row['body'] for row in ledger.records('model_choice')
                   if row['body']['model_ref'] == arguments['model_ref']]
        plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
        plan_ref = ledger.put('plan', plan)
    forecast_ref = _freeze(ledger, plan, plan['original_prediction'], plan['original_reference'], operation_key)
    return {'plan_ref': plan_ref, 'forecast_ref': forecast_ref,
            **{key: value for key, value in plan.items() if key != 'prediction_episode_id'}}


def _fit(services, ledger, arguments, operation_key, episode_id):
    commission = ledger.commission
    selected = set(arguments['training_ids'])
    if services.memory is not None:
        ledger.once('shared_history:' + operation_key, 'shared_history', lambda: _shared_history(services, ledger))
    cases = _history(ledger)
    if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
        raise ValueError('training_ids_must_be_original_nonvalidation_cases')
    heldout = [cases[key] for key in commission['validation_ids']]
    historical = selected.intersection(row['id'] for row in commission['history'])
    if historical and heldout and max(cases[key]['observed_at'] for key in historical) \
            >= min(row['observed_at'] for row in heldout):
        raise ValueError('training_must_precede_temporal_validation')
    model = prediction.fit(commission['model'], [cases[key] for key in selected])
    model_ref = ledger.put('model', model)
    # Fixed historical validation cannot measure a model trained on later allocations; those earn
    # prospective validation credit when real outcomes arrive.
    later = selected - {row['id'] for row in commission['history']}
    quality = None if later else _quality(ledger, model)
    baseline = _quality(ledger, ledger.read('reference_model'))
    ledger.put('model_choice', {'operation_key': operation_key, 'model_ref': model_ref, 'episode_id': episode_id})
    ledger.model_credit(model_ref, quality - baseline if quality is not None and baseline is not None else 0.)
    return {'model_ref': model_ref, 'validation_quality': quality, 'reference_quality': baseline,
            'credit': ledger.credit_view()}


def _discover(services, ledger, configuration, arguments, operation_key):
    command = 'cd ' + shlex.quote(REMOTE_PROJECT) + ' && ' + arguments['command']

    def observe():
        from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.execution_guidance import resource_identity
        cache_key = resource_identity(ledger.commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
        if services.memory is not None:
            cached = services.memory.latest(cache_key, 'inventory')
            if cached['state'] == 'fresh':
                return cached['data']
        completed = subprocess.run([*configuration['ssh_argv'], command], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        value = {'command': arguments['command'], 'returncode': completed.returncode,
                 'stdout': completed.stdout[:65536].decode('utf-8', 'replace'),
                 'stderr': completed.stderr[:8192].decode('utf-8', 'replace'),
                 'observed_at': time.time(), 'truncated': len(completed.stdout) > 65536}
        if services.memory is not None and completed.returncode == 0:
            services.memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                                    provenance=[str(ledger.path), 'discovery:' + operation_key])
        return value
    return ledger.once('discovery:' + operation_key, 'discovery', observe)


def _propose(services, ledger, arguments):
    candidate = json.loads(arguments['candidate_json'])
    if not isinstance(candidate, dict) or 'id' not in candidate:
        raise ValueError('candidate_json_must_be_a_candidate_record')
    candidates = _candidates(ledger)
    prior = next((row for row in candidates if row['id'] == candidate['id']), None)
    if prior is not None and prior != candidate:
        raise ValueError('candidate_identity_is_immutable')
    validate_commission({**ledger.commission, 'candidates': candidates if prior else candidates + [candidate]},
                        services.resources)
    reference = ('caller_candidate:' + candidate['id'] if candidate in ledger.commission['candidates']
                 else ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return {'candidate_ref': reference, 'candidate_id': candidate['id']}


def _read(ledger, arguments):
    history = _history(ledger)
    if arguments['reference'] in history:
        return history[arguments['reference']]
    return ledger.read(arguments['reference'])


async def execute(role, services, ledger, tool, arguments, operation_key, episode_id):
    """Execute one selected HPC operation; an argument or reference failure is a returned invalid outcome."""
    entries = {row['name']: row for row in catalog(role, services)}
    if tool not in entries:
        raise HPCRuntimeError(AXIS + '_hpc_tool_not_offered:' + tool)
    selection = {'tool': tool, 'arguments': arguments, 'episode_id': episode_id}
    old = ledger.cached(operation_key, selection)
    if old is not None:
        return old
    ledger.put('action_intent', selection, identity='action:' + operation_key)
    configuration = services.resources[ledger.commission['resource_id']]
    try:
        if tool == 'hpc.read':
            result = _read(ledger, arguments)
        elif tool == 'hpc.history.refresh':
            result = ledger.once('shared_history:' + operation_key, 'shared_history',
                                 lambda: _shared_history(services, ledger))
        elif tool == 'hpc.discovery.run':
            result = await asyncio.to_thread(_discover, services, ledger, configuration, arguments, operation_key)
        elif tool == 'hpc.candidate.propose':
            result = _propose(services, ledger, arguments)
        elif tool == 'hpc.queue.observe':
            reference = 'queue:' + hpc_queue.digest(operation_key)
            observed = await asyncio.to_thread(ledger.once, reference, 'queue',
                                               lambda: _observe_queue(services, ledger, configuration))
            result = {'queue_ref': reference, 'snapshot': observed['snapshot'],
                      'features': [hpc_queue.features(observed['snapshot'], candidate)
                                   for candidate in _candidates(ledger)]}
        elif tool == 'hpc.compare':
            result = {'comparisons': _comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
            result['comparison_ref'] = ledger.put('comparison', {**result, **arguments, 'episode_id': episode_id,
                                                                 'operation_key': operation_key})
        elif tool == 'hpc.plan':
            result = _plan(ledger, configuration, arguments, operation_key)
        else:
            result = _fit(services, ledger, arguments, operation_key, episode_id)
    except (ValueError, KeyError) as error:
        return ledger.save_action(operation_key, selection, {
            'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error)}})
    return ledger.save_action(operation_key, selection, {'status': 'completed', 'record_refs': [],
                                                         'changed_record_refs': [], 'result': plain(result)})


# -- the decision source ---------------------------------------------------------------------------------------

PLANNING_INSTRUCTIONS = (
    'Iterate toward the original HPC accomplishment while balancing expected credit against real elapsed time and '
    'resource demand. When candidates are absent, discover the remote environment and documentation with '
    'hpc.discovery.run, then design candidate portfolios with hpc.candidate.propose. Discovery is lightweight '
    'inspection only. You choose the real inputs, executable commands, resources and preparation instructions; '
    'never fabricate inputs or receipts. Every work unit writes result.json and progress.json under '
    'os.environ["HPC_UNIT_DIRECTORY"]; its fields must satisfy the caller acceptance predicates. Compute commands '
    'run on allocated compute nodes using the facility launcher. Observe the queue with hpc.queue.observe and '
    'compare portfolios with hpc.compare using the current model and that observation. Commission '
    'hpc_resource_prediction only when model improvement warrants its own iteration; it shares this ledger. A plan '
    '(hpc.plan) freezes its original forecast, manifest and acceptance criteria. Accepted accomplishment, model '
    'improvement and fixed prospective forecast validation are the only credit components. Binding a launch '
    'handoff, monitoring the launched job and parsing its results are not available in this episode yet. The '
    'configured controller owns continuation.')
PREDICTION_INSTRUCTIONS = (
    'Iterate on a generalized time/resource model using measured historical cases. Refresh shared history, inspect '
    'support and held-out quality, fit a disjoint training selection with hpc.model.fit, and compare useful '
    'portfolios. Inspect missing capacity, launcher and queue facts with lightweight discovery; propose executable '
    'resource alternatives when the parent has not supplied them. Forecast CPU time and memory demand as well as '
    'queue, setup and work time. Both sisters use the parent-owned ledger; preserve model and comparison identities. '
    'The fixed reference and validation set cannot change. Model credit is measured improvement on the fixed '
    'validation cases; the parent later scores frozen predictions against real outcomes. Unknown inputs stay '
    'unknown. The configured controller owns continuation.')


class HPCSource:
    """Model-selected HPC units over ``bound``, its collaborators and the commission's own ledger."""

    def __init__(self, binding, role, bound, collaborators, child_builders, report):
        self._binding, self._role, self._bound = binding, role, bound
        self._model = collaborators['model_provider']
        self._services = services_of(collaborators)
        self._ledger, self._scope = open_ledger(role, bound, self._services, collaborators['store'])
        self._builders = dict(child_builders)
        self._report = report
        if role == PREDICTION and self._builders:
            raise HPCRuntimeError(AXIS + '_hpc_prediction_has_no_child_slots')
        for slot, builder in self._builders.items():
            if not {'credit', FINDING} <= set(builder.return_form.fields):
                raise HPCRuntimeError(AXIS + '_hpc_child_return_form_lacks_credit_or_finding:' + slot)
        self.report_fields = commissioned_report_fields(binding, bound, PLANNING_REPORT_FIELDS)
        self.catalog = catalog(role, self._services)
        self.applied, self.last_outcome, self.feedback = 0, None, None

    def _apply(self, outcome):
        self.feedback = outcome.get('feedback')
        self.last_outcome, self.applied = outcome, self.applied + 1

    def _catch_up(self, position):
        while self.applied < position:
            self._apply(self._bound.recorder.recall('outcome.' + str(self.applied)))

    def credit(self):
        return credit_view(self._role, self._ledger, self._bound.episode_id)

    def action_schema(self):
        options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
                   for entry in self.catalog]
        if PREDICTION_SLOT in self._builders:
            options.append(obj({'kind': {'const': 'child'}, 'slot': {'const': PREDICTION_SLOT},
                                'objective': _TEXT}))
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view):
        ledger = self._ledger
        current = _current_model(ledger)
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(), 'scope': self._scope, 'hpc_role': self._role,
            'hpc_commission': ledger.commission, 'hpc_owner_episode_id': ledger.read('owner')['episode_id'],
            'hpc_resource': self._services.resources[ledger.commission['resource_id']],
            'hpc_candidates': _candidates(ledger), 'hpc_model_ref': current,
            'hpc_model_support': prediction.predict(ledger.read(current), {})['support'],
            'hpc_credit': self.credit(),
            'hpc_latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                       if key not in ('episode_id', 'operation_key')}}
                                      for row in ledger.records('comparison')[-1:]],
            'hpc_plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                          for row in ledger.records('plan')],
            'hpc_queue_refs': [row['id'] for row in ledger.records('queue')],
            'hpc_available_training_ids': sorted(set(_history(ledger)) - set(ledger.commission['validation_ids'])),
            **({'hpc_shared_memory': self._services.memory.as_record(),
                'hpc_shared_history_refs': [row['id'] for row in ledger.records('shared_history')]}
               if self._services.memory is not None else {}),
            'tools': [{key: value for key, value in entry.items() if key != 'input_schema'} for entry in self.catalog],
            'child_options': ({PREDICTION_SLOT: 'Commission a resource-prediction sister over this ledger; it returns '
                                                'its model-improvement credit and model.'}
                              if PREDICTION_SLOT in self._builders else {}),
            'controller': state.as_record(),
            'units_consumed': view.units_consumed, 'last_local_outcome': self.last_outcome, 'feedback': self.feedback}

    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        instructions = PLANNING_INSTRUCTIONS if self._role == PLANNING else PREDICTION_INSTRUCTIONS
        while True:
            schema, context = self.action_schema(), self.decision_context(view)
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._model.complete(self._bound.episode_id, MODEL_ROLE, instructions, context, schema))
            try:
                if not isinstance(response, Mapping) or set(response) != {'selection'}:
                    raise ValueError(AXIS + '_hpc_decision_response_must_be_exactly_selection')
                selection = plain(response['selection'])
                Draft202012Validator(schema['properties']['selection']).validate(selection)
            except (ValueError, TypeError, ValidationError) as error:
                # Rejected before acquisition: no unit and no observation; decide again with this feedback.
                self.feedback = {'status': 'invalid', 'category': 'action_contract',
                                 'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            if selection['kind'] == 'child':
                return self._child(position, selection)
            return Leaf(selection, lambda chosen: self._tool(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome),
                        chosen_label(selection, position))

    def _controller_input(self, position, outcome):
        return HPCRecord({'credit': self.credit()['credit'],
                          'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                          'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    async def _tool(self, position, selection):
        key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

        async def run():
            result = await execute(self._role, self._services, self._ledger, selection['tool'],
                                   selection['arguments'], key, self._bound.episode_id)
            return {'kind': 'tool', 'tool': selection['tool'], **plain(result)}
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), run)
        self._apply(outcome)
        return outcome

    def _child(self, position, selection):
        builder = self._builders[selection['slot']]
        assignment = {'scope': self._scope, ROLE_FIELD: {'owner_episode_id': self._bound.episode_id},
                      **builder.assignment_form.declared}
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                 result_contract=dict(self._report))
        commission = Commission(EpisodeRequest(goal, HPCRecord({'scope': self._scope}),
                                               ReportContract(**self._report)), assignment)
        child = builder(selection['slot'] + '_' + str(position), commission)
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'slot': selection['slot'],
                'child_credit': admitted['credit'], 'child_finding': admitted[FINDING],
                'child_completion': completion.as_record()})
            self._apply(outcome)
            return self._controller_input(position, outcome)

        def report_of(result, completion, request):
            admitted = builder.admit(result)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report_of)

    def build_result(self, record):
        self._catch_up(record.units_consumed)
        view = self.credit()
        if isinstance(view['credit'], bool) or not math.isfinite(view['credit']):
            raise HPCRuntimeError(AXIS + '_hpc_credit_must_be_finite')
        ledger = self._ledger
        finding = {'scope': self._scope, 'hpc_role': self._role, 'hpc_credit': view,
                   'hpc_model_ref': _current_model(ledger),
                   'hpc_plan_refs': [row['id'] for row in ledger.records('plan')],
                   'hpc_candidate_ids': [row['id'] for row in _candidates(ledger)],
                   'hpc_comparison_refs': [row['id'] for row in ledger.records('comparison')],
                   'hpc_ledger': str(ledger.path), 'ended_by': record.ended_by, 'units': record.units_consumed}
        return result_record(view['credit'], plain(finding), self.report_fields)


# The fields of a planning or prediction Episode's finding (``build_result``).
PLANNING_REPORT_FIELDS = ('scope', 'hpc_role', 'hpc_credit', 'hpc_model_ref', 'hpc_plan_refs', 'hpc_candidate_ids',
                          'hpc_comparison_refs', 'hpc_ledger', 'ended_by', 'units')


def commissioned_report_fields(binding, bound, held):
    """The fields a parent's commissioned report form (C5) adds to the binding's return form.

    Each added field is one of this Episode's finding fields (``held``), returned at the top level of its
    result; a field the finding does not hold raises when the Episode is built.
    """
    added = tuple(name for name in bound.report_form.fields if name not in binding.return_form.fields)
    missing = [name for name in added if name not in held]
    if missing:
        raise HPCRuntimeError(AXIS + '_hpc_commissioned_report_field_not_held:' + binding.binding_path + ':'
                              + ','.join(missing))
    return added


def result_record(credit, finding, added):
    """This axis's return form: its own credit and its finding record, plus each finding field the
    commissioned report form adds. An added field whose finding value is null stays absent; the runner's
    admission raises when the form requires it."""
    return HPCRecord({'credit': credit, 'finding': finding,
                      **{name: finding[name] for name in added if finding[name] is not None}})


def chosen_label(selection, position):
    return selection['tool'] + ':' + str(position)


class HPCRuntime:
    """The ``episode_runtime`` hooks of an A107 HPC planning or prediction binding.

    Mixed in before the axis's contract binding; the class declares ``hpc_role``.
    """

    hpc_role: str
    required_collaborators = ('model_provider', 'store', SERVICES)

    def build_controller(self, bound, collaborators):
        return controller(self.hpc_role, bound, collaborators)

    def build_episode(self, grain, bound, collaborators, child_builders):
        source = HPCSource(self, self.hpc_role, bound, collaborators, child_builders, REPORT)
        return Episode(grain, bound.key, source, bound.request, source.build_result)

    def restore_controller_input(self, record):
        return HPCRecord(dict(record))


__all__ = ['HPCRecord', 'HPCRuntime', 'HPCRuntimeError', 'HPCServices', 'HPCSource', 'PLANNING_REPORT_FIELDS',
           'SERVICES', 'catalog', 'commissioned_report_fields', 'controller', 'credit_view', 'execute', 'open_ledger',
           'result_record']
