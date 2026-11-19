"""The task: improve the time/resource model of the parent-owned HPC ledger, one model-selected action per unit.

Carried from the old ``prediction_operations.py`` (``catalog``, ``execute``), ``prediction_state.py``
(``state``, ``initialize``, ``_current_model``), ``prediction_history.py`` (``_history``, ``_shared_history``),
``portfolio_comparison.py`` (``_candidates``, ``_features``, ``_comparisons``), ``queue_observations.py``
(``_observe_queue``, ``_queue``), ``received_evidence.py`` (``resolve_received_reference``, ``read_evidence``),
``configuration.py`` (the settings values and their checks), ``task_instructions.py``, ``decision_inputs.py``,
``decision_state.py`` and ``task.py`` / ``task_decision.py`` (the decision machine: now ``decide`` and ``action``).
One unit is one tool call; the old ``permitted_common_actions`` was ``('tool',)`` (no reasoning commit, no wait,
no child). The task always offers a unit and never ends the Episode: only the yield controller does. The model's
old ``report_update`` is not carried: the return's facts are recorded facts (``messages/final_to_parent.py``).

Tool names are ``[a-z][a-z0-9_]*`` now: the old ``hpc.read``, ``hpc.compare``, ``hpc.history.refresh``,
``hpc.discovery.run``, ``hpc.candidate.propose``, ``hpc.queue.observe`` and ``hpc.model.fit`` are ``hpc_read``,
``hpc_compare``, ``hpc_history_refresh``, ``hpc_discovery_run``, ``hpc_candidate_propose``, ``hpc_queue_observe``
and ``hpc_model_fit``. ``hpc_initialize`` is the old ``initialize`` (the write of the reference model, the initial
model from shared history and the entry quality, which the old decision context did before the first decision):
``decide`` offers it as the first unit, because ``decide`` cannot write.

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``resources`` (resource id ->
configuration; at least one ``pbs_ssh``), ``shared_execution_memory`` (present when shared memory is configured),
``resource`` is not a setting (the resource shown is the commission's), ``initial_information`` (optional),
``launch_instructions_directory`` and ``knowledge_library_directory`` (optional). The old ``directory``,
``commissions`` (the commission is the ledger's own ``commission`` record) and ``require_commission_yield`` are not
carried.

BLOCKED-ON-JOB-SERVICE (each is named where it is reached and raises there):

* the parent-owned HPC ledger as custody records (``ledger_find``, ``ledger_select``, ``ledger_write``,
  ``ledger_credits``, ``ledger_write_credit``): the ledger was a SQLite file the episode opened by path; no job
  record kind or work table is declared for it;
* the service ``job_access`` (the queue observation and the discovery command, both through the SSH transport) and
  the service ``estimate_table`` (the shared execution memory: its history, its latest observation, its policy);
  neither is provided."""
import json
import shlex
import time
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.structural_homology_evidence.execution_contracts import (
    obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_campaign import (
    validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_resource_prediction import (
    physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, plain, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

TRANSPORT_ERROR = 'a102_hpc_resource_prediction_selection_has_no_argument_transport'
WORKSPACE = '/lus/flare/projects/BioReason-Aurora-Test'
DISCOVERY_STDOUT_BYTES = 65536
DISCOVERY_STDERR_BYTES = 8192
BLOCKED = 'BLOCKED-ON-JOB-SERVICE: '

TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}

# The old model-facing catalog (``PredictionOperations.catalog``), under the new tool names.
CATALOG = {
    'hpc_read': {'description': 'Read retained HPC evidence by its exact identity.',
                 'input_schema': obj({'reference': TEXT})},
    'hpc_compare': {'description': 'Compare all approved portfolios; no work is selected or launched.',
                    'input_schema': obj({'model_ref': TEXT, 'queue_ref': TEXT})},
    'hpc_history_refresh': {'description': 'Read age-weighted shared timing history once. No remote discovery, '
                            'polling credit, or new scientific work.', 'input_schema': obj({})},
    'hpc_discovery_run': {'description': 'Run one lightweight remote inspection or documentation retrieval through '
                          'the established SSH transport. No job submission, installation or scientific '
                          'computation; those belong to Launch and the allocation.',
                          'input_schema': obj({'command': TEXT})},
    'hpc_candidate_propose': {'description': (
        'Retain an executable portfolio selected by this episode. candidate_json is JSON with id, queue, nodes, '
        'wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), '
        'optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units '
        '(unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files '
        '[{path: relative path, text: exact contents}], and preparation instructions for Launch. effort is a '
        'positive finite number expressing relative work, for example 1.0; workload sizes belong in features. No '
        'per-unit execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate '
        'identities are immutable.'), 'input_schema': obj({'candidate_json': TEXT})},
    'hpc_queue_observe': {'description': 'Acquire PBS queue and ALCF score/status once and transform them.',
                          'input_schema': obj({})},
    'hpc_model_fit': {'description': 'Fit selected measured history; validate on the fixed disjoint cases.',
                      'input_schema': obj({'training_ids': STRINGS})},
}


def memory_configured(settings):
    """The old ``self.memory`` was set: the settings name a shared execution memory."""
    return settings.get('shared_execution_memory') is not None


def operation_catalog(memory):
    """The old ``catalog``: ``hpc.history.refresh`` only with shared memory."""
    return [{'name': name, **deepcopy(entry)} for name, entry in CATALOG.items()
            if name != 'hpc_history_refresh' or memory]


def resources_of(settings):
    """The old ``PredictionConfiguration.__init__`` check of the resources: at least one ``pbs_ssh``."""
    resources = plain(settings['resources'])
    if not any(row.get('kind') == 'pbs_ssh' for row in resources.values()):
        raise ValueError('explicit_hpc_resource_required')
    return resources


# ---------------------------------------------------------------------------------------------------------------
# The parent-owned HPC ledger, in custody. The old ``HPCLedger`` was a SQLite file (``evidence``, ``credits``)
# opened by path. Its five primitives are the BLOCKED-ON-JOB-SERVICE points: each names the call it wants and
# raises. Everything built on them below is the old ledger logic, unchanged.
# ---------------------------------------------------------------------------------------------------------------

def ledger_find(reader, owner, identity):
    """The evidence row ``{'id', 'kind', 'body'}`` of the ledger owned by ``owner``, or ``None``.

    BLOCKED-ON-JOB-SERVICE: HPC ledger evidence record (a job record kind; no work table is declared); wanted call:
    ``reader.table(HPC_LEDGER).select({'owner': owner, 'id': identity})`` (``HPC_LEDGER`` is the job library's work
    table, not written yet)."""
    raise NotImplementedError(BLOCKED + 'HPC ledger evidence record; wanted call: '
                              "reader.table(HPC_LEDGER).select({'owner': owner, 'id': identity})")
    return next(iter(reader.table(None).select({'owner': owner, 'id': identity})), None)


def ledger_select(reader, owner, kind):
    """The evidence rows of ``kind`` in receipt order (the old ``records(kind)``, ``ORDER BY recorded, id``).

    BLOCKED-ON-JOB-SERVICE: HPC ledger evidence record; wanted call:
    ``reader.table(HPC_LEDGER).select({'owner': owner, 'kind': kind})``."""
    raise NotImplementedError(BLOCKED + 'HPC ledger evidence record; wanted call: '
                              "reader.table(HPC_LEDGER).select({'owner': owner, 'kind': kind})")
    return reader.table(None).select({'owner': owner, 'kind': kind})


def ledger_write(store, owner, identity, kind, body):
    """Write one evidence row (the old ``INSERT OR IGNORE INTO evidence``).

    BLOCKED-ON-JOB-SERVICE: HPC ledger evidence record; wanted call:
    ``store.table(HPC_LEDGER).put({'owner': owner, 'id': identity, 'kind': kind, 'body': body})``."""
    raise NotImplementedError(BLOCKED + 'HPC ledger evidence record; wanted call: '
                              "store.table(HPC_LEDGER).put({'owner': owner, 'id': identity, 'kind': kind, "
                              "'body': body})")
    return store.table(None).put({'owner': owner, 'id': identity, 'kind': kind, 'body': body})


def ledger_credits(reader, owner):
    """The credit rows ``{'slot', 'kind', 'credit', 'evidence_id'}`` of the ledger (the old ``credits`` table).

    BLOCKED-ON-JOB-SERVICE: HPC ledger credit record; wanted call: ``reader.table(HPC_CREDITS).select({'owner':
    owner})``."""
    raise NotImplementedError(BLOCKED + 'HPC ledger credit record; wanted call: '
                              "reader.table(HPC_CREDITS).select({'owner': owner})")
    return reader.table(None).select({'owner': owner})


def ledger_write_credit(store, owner, slot, kind, credit, evidence_id):
    """Replace one credit row (the old ``INSERT OR REPLACE INTO credits``).

    BLOCKED-ON-JOB-SERVICE: HPC ledger credit record; wanted call: ``store.table(HPC_CREDITS).put({'owner': owner,
    'slot': slot, 'kind': kind, 'credit': credit, 'evidence_id': evidence_id})``."""
    raise NotImplementedError(BLOCKED + 'HPC ledger credit record; wanted call: '
                              "store.table(HPC_CREDITS).put({'owner': owner, 'slot': slot, 'kind': kind, "
                              "'credit': credit, 'evidence_id': evidence_id})")
    return store.table(None).put({'owner': owner, 'slot': slot, 'kind': kind, 'credit': credit,
                                  'evidence_id': evidence_id})


def ledger_read(reader, owner, identity):
    """The old ``HPCLedger.read``: the body of an evidence row."""
    row = ledger_find(reader, owner, identity)
    if row is None:
        raise ValueError('unknown_hpc_evidence:' + identity)
    return row['body']


def ledger_records(reader, owner, kind):
    """The old ``HPCLedger.records``: ``[{'id', 'body'}]`` in receipt order."""
    return [{'id': row['id'], 'body': row['body']} for row in ledger_select(reader, owner, kind)]


def ledger_put(store, owner, kind, body, *, identity=None):
    """The old ``HPCLedger.put``: evidence is immutable; the same identity with another kind or body is a conflict."""
    identity = identity or kind + '_' + hpc_queue.digest(body)
    prior = ledger_find(store, owner, identity)
    if prior is not None:
        if (prior['kind'], hpc_queue.canonical(prior['body'])) != (kind, hpc_queue.canonical(body)):
            raise ValueError('immutable_hpc_evidence_conflict:' + identity)
        return identity
    ledger_write(store, owner, identity, kind, body)
    return identity


def ledger_once(store, owner, identity, kind, calculate):
    """The old ``HPCLedger.once``: recover a committed step without another calculation."""
    prior = ledger_find(store, owner, identity)
    if prior is not None:
        return prior['body']
    value = calculate()
    ledger_put(store, owner, kind, value, identity=identity)
    return value


def ledger_commission(reader, owner):
    """The commission the ledger was opened with (the old ``ledger.commission``)."""
    return json.loads(hpc_queue.canonical(ledger_read(reader, owner, 'commission')))


def ledger_credit_view(reader, owner):
    """The old ``HPCLedger.credit_view``: the credit rows by kind."""
    rows = ledger_credits(reader, owner)
    components = {kind: sum(row['credit'] for row in rows if row['kind'] == kind)
                  for kind in ('actual', 'model', 'validation')}
    return {'credit': sum(components.values()), 'components': components,
            'contributions': [{name: row[name] for name in ('slot', 'kind', 'credit', 'evidence_id')}
                              for row in sorted(rows, key=lambda row: row['slot'])]}


def model_credit(store, owner, commission, model_ref, improvement):
    """The old ``HPCLedger.model_credit``: a new model replaces the projection, including negative corrections."""
    ledger_write_credit(store, owner, 'model', 'model', commission['credit']['model_scale'] * improvement,
                        model_ref)


def accepted_obligations(reader, owner):
    """The obligations with accepted actual results (the ``actual:`` credit slots)."""
    return [row['slot'].removeprefix('actual:') for row in ledger_credit_view(reader, owner)['contributions']
            if row['kind'] == 'actual']


# ---------------------------------------------------------------------------------------------------------------
# Services. Each call below is a BLOCKED-ON-JOB-SERVICE point: it names the call it wants and raises.
# ---------------------------------------------------------------------------------------------------------------

def shared_memory_record(ctx):
    """The shared memory's policy record (the old ``self.memory.as_record()``).

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].read('as_record')`` (a
    read handle in ``decide``)."""
    raise NotImplementedError(BLOCKED + "estimate_table; wanted call: ctx.services['estimate_table'].read("
                              "'as_record')")
    return ctx.services['estimate_table'].read('as_record')


def estimate_history(ctx, profile, *, now, queue_only=False):
    """Age-weighted shared timing history (the old ``self.memory.history(profile, now=now, queue_only=...)``).

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].history(profile,
    now=now, queue_only=queue_only)``."""
    raise NotImplementedError(BLOCKED + "estimate_table; wanted call: ctx.services['estimate_table'].history("
                              'profile, now=now, queue_only=queue_only)')
    return ctx.services['estimate_table'].history(profile, now=now, queue_only=queue_only)


def estimate_latest(ctx, resource, kind):
    """The latest shared observation (the old ``self.memory.latest(resource, kind)``).

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].latest(resource,
    kind)``."""
    raise NotImplementedError(BLOCKED + "estimate_table; wanted call: ctx.services['estimate_table'].latest("
                              'resource, kind)')
    return ctx.services['estimate_table'].latest(resource, kind)


def estimate_observe(ctx, resource, kind, data, *, observed_at, provenance):
    """Add a shared observation (the old ``self.memory.observe(...)``), once per ``ctx.operation_key``.

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].observe(resource, kind,
    data, observed_at=observed_at, provenance=provenance, key=ctx.operation_key)``."""
    raise NotImplementedError(BLOCKED + "estimate_table; wanted call: ctx.services['estimate_table'].observe("
                              'resource, kind, data, observed_at=observed_at, provenance=provenance, '
                              'key=ctx.operation_key)')
    return ctx.services['estimate_table'].observe(resource, kind, data, observed_at=observed_at,
                                                  provenance=provenance, key=ctx.operation_key)


async def observe_queue_service(ctx, configuration):
    """One PBS queue and ALCF activity acquisition (the old ``hpc_queue.observe(configuration)``): ``{'snapshot',
    'acquisition'}``.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].observe_queue(
    configuration, key=ctx.operation_key, resumed=ctx.resumed)``, idempotent on ``ctx.operation_key``."""
    raise NotImplementedError(BLOCKED + "job_access; wanted call: await ctx.services['job_access'].observe_queue("
                              'configuration, key=ctx.operation_key, resumed=ctx.resumed)')
    return await ctx.services['job_access'].observe_queue(configuration, key=ctx.operation_key,
                                                          resumed=ctx.resumed)


async def run_discovery_service(ctx, configuration, command):
    """One read-only command through the resource's SSH argv (the old ``subprocess.run([*ssh_argv, command])``):
    ``{'returncode', 'stdout', 'stderr'}`` with the bytes of both streams. The old call carried a fixed 90 second
    cutoff; no cutoff is carried.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].run_discovery(
    configuration['ssh_argv'], command, key=ctx.operation_key, resumed=ctx.resumed)``, idempotent on
    ``ctx.operation_key``."""
    raise NotImplementedError(BLOCKED + "job_access; wanted call: await ctx.services['job_access'].run_discovery("
                              "configuration['ssh_argv'], command, key=ctx.operation_key, resumed=ctx.resumed)")
    return await ctx.services['job_access'].run_discovery(configuration['ssh_argv'], command,
                                                          key=ctx.operation_key, resumed=ctx.resumed)


# ---------------------------------------------------------------------------------------------------------------
# The prediction state, history, comparison and received evidence (old methods, now functions of the ledger).
# ---------------------------------------------------------------------------------------------------------------

def current_model(reader, owner):
    """The old ``_current_model``: the last chosen model, or the reference model."""
    records = ledger_records(reader, owner, 'model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'


def model_quality(commission, model):
    """The old ``HPCEpisodeCredit._quality``: held-out quality of a model trained only on the commission's original
    history, else ``None`` (no measured quality)."""
    if not set(model['training_ids']) <= {row['id'] for row in commission['history']}:
        return None
    selected = [row for row in commission['history'] if row['id'] in commission['validation_ids']]
    return prediction.quality(model, selected) if selected else None


def candidates(reader, owner, commission):
    """The old ``_candidates``: the commission's candidates and the ones this episode proposed."""
    return commission['candidates'] + [row['body'] for row in ledger_records(reader, owner, 'candidate')]


def history_cases(reader, owner, commission):
    """The old ``_history``: the original cases, the latest shared snapshot and one latest observation per closed
    actual allocation (never one training example per poll)."""
    rows = {row['id']: row for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()} - {None}
    for snapshot in ledger_records(reader, owner, 'shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in ledger_records(reader, owner, 'plan')}
    closed = {row['body']['plan_id'] for row in ledger_records(reader, owner, 'closed')}
    latest = {}
    for row in ledger_records(reader, owner, 'measured'):
        if row['body']['plan_id'] in closed:
            latest[row['body']['plan_id']] = row
    for plan_id, row in latest.items():
        body = row['body']
        rows['allocation:' + plan_id] = {
            'id': 'allocation:' + plan_id, 'observed_at': body['observed_at'],
            'features': plans[plan_id]['original_prediction']['features'], 'metrics': body['metrics'],
            'success': body['success'], 'provenance': [row['id']]}
    return rows


def shared_history(ctx, owner, commission, configuration):
    """The old ``_shared_history``: age-weighted shared timing, resource-wide for the queue and only for a matching
    execution profile for the work; at most 2000 new observations."""
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], configuration)
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in estimate_history(ctx, query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in estimate_history(ctx, profile, now=now)})
    queues = {candidate['queue'] for candidate in candidates(ctx.store, owner, commission)}
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
    return {'captured_at': now, 'policy': shared_memory_record(ctx)['policy'],
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts][:2000]}


async def observed_queue(ctx, commission, configuration):
    """The old ``_observe_queue``: a fresh shared observation within ``queue_max_age_seconds`` is reused; else one
    acquisition, added to the shared memory when there is one."""
    memory = memory_configured(ctx.settings)
    resource = resource_identity(commission['resource_id'], configuration)
    if memory:
        cached = estimate_latest(ctx, resource, 'queue')
        if cached['state'] == 'fresh' and cached['age_seconds'] <= commission['limits']['queue_max_age_seconds']:
            return cached['data']
    value = await observe_queue_service(ctx, configuration)
    if memory:
        estimate_observe(ctx, resource, 'queue', value, observed_at=value['snapshot']['captured_at'],
                         provenance=value['acquisition'])
    return value


def queue_snapshot(reader, owner, commission, reference, *, require_fresh=False):
    """The old ``_queue``: the snapshot of a recorded queue observation, optionally required to be fresh."""
    observation = ledger_read(reader, owner, reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


def candidate_features(candidate, queue):
    """The old ``_features``."""
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def comparisons(reader, owner, commission, model_ref, queue_ref):
    """The old ``_comparisons``: every approved candidate forecast with the model and the queue observation,
    compared with the obligations and preferences (excluding obligations already credited), best first."""
    model = ledger_read(reader, owner, model_ref)
    observed = queue_snapshot(reader, owner, commission, queue_ref)
    actual = accepted_obligations(reader, owner)
    results = []
    for candidate in candidates(reader, owner, commission):
        queue = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, candidate_features(candidate, queue))
        row = prediction.compare(candidate, forecast, commission['obligations'], commission['preferences'],
                                 already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def resolve_result_source(reader, run_id, reference, namespace=None):
    """The old ``resolve_received_reference`` for an ``episode.hpc_result`` source: ``None`` when the reference is
    not a result source this episode holds, ``False`` when it is one but not usable, ``True`` when it is a held
    source whose body belongs to this run. The old ``_known`` (the received references) is custody: ``holds``. The
    old scope comparison is custody too: there is no scope object."""
    if not reader.holds(reference):
        return None
    source = reader.get(reference)
    if source.get('provider') != 'episode.hpc_result':
        return None
    if namespace not in (None, 'source'):
        return False
    body = json.loads(reader.get_artifact(source['artifact_ref']))
    return body['run_id'] == run_id


def read_evidence(ctx, owner, commission, reference):
    """The old ``read_evidence``: a history case, a ledger record, or a held result source whose body equals the
    ledger receipt (the source and its artifact are both passed in custody)."""
    history = history_cases(ctx.store, owner, commission)
    if reference in history:
        return history[reference]
    if not reference.startswith('source_'):
        return ledger_read(ctx.store, owner, reference)
    rows = [row['body'] for row in ledger_records(ctx.store, owner, 'result')
            if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or resolve_result_source(ctx.store, ctx.run_id, reference, 'source') is not True:
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


def initialize(ctx, owner, commission, configuration):
    """The old ``initialize``: the reference model (the commission's prior), the initial model fitted from shared
    history when shared memory is configured, and the entry quality, once per episode."""
    ledger_put(ctx.store, owner, 'model', prediction.prior_model(commission['model']), identity='reference_model')
    if memory_configured(ctx.settings):
        imported = ledger_once(ctx.store, owner, 'shared_history_entry', 'shared_history',
                               lambda: shared_history(ctx, owner, commission, configuration))
        if imported['observations'] and not ledger_records(ctx.store, owner, 'model_choice'):
            model = prediction.fit(commission['model'], imported['observations'])
            reference = ledger_put(ctx.store, owner, 'model', model)
            ledger_put(ctx.store, owner, 'model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')

    def entry():
        current = current_model(ctx.store, owner)
        return {'model_ref': current, 'quality': model_quality(commission, ledger_read(ctx.store, owner, current))}

    ledger_once(ctx.store, owner, 'entry:' + ctx.episode_id, 'model_entry', entry)


# ---------------------------------------------------------------------------------------------------------------
# The tools.
# ---------------------------------------------------------------------------------------------------------------

def outcome(result=None, *, code=None, recovery=None):
    """The old outcome shape: ``completed``, or ``invalid`` with feedback when it carries a code."""
    feedback = None if code is None else {'category': 'arguments_or_reference', 'code': code,
                                          **({} if recovery is None else {'recovery': recovery})}
    return {'status': 'invalid' if code else 'completed', 'record_refs': [], 'changed_record_refs': [],
            'result': result, 'feedback': feedback}


def state_of(ctx, arguments):
    """The old ``state``: the ledger owner, its commission and the commission's resource configuration."""
    owner = arguments['owner_episode_id']
    commission = ledger_commission(ctx.store, owner)
    return owner, commission, resources_of(ctx.settings)[commission['resource_id']]


def hpc_initialize(arguments, ctx):
    owner, commission, configuration = state_of(ctx, arguments)
    initialize(ctx, owner, commission, configuration)
    return outcome({'initialized': True, 'owner_episode_id': owner})


def hpc_read(arguments, ctx):
    owner, commission, _ = state_of(ctx, arguments)
    try:
        result = read_evidence(ctx, owner, commission, arguments['reference'])
    except (ValueError, KeyError) as error:
        return outcome(code=str(error))
    return outcome(result)


def hpc_history_refresh(arguments, ctx):
    owner, commission, configuration = state_of(ctx, arguments)
    result = ledger_once(ctx.store, owner, 'shared_history:' + ctx.operation_key, 'shared_history',
                         lambda: shared_history(ctx, owner, commission, configuration))
    return outcome(result)


async def hpc_discovery_run(arguments, ctx):
    """One lightweight read-only command over the resource's SSH argv in the project workspace (stdout and stderr
    kept to 64 KiB and 8 KiB: a size bound), cached in the shared memory when there is one. A read-only discovery
    can be repeated after an interrupted observation; every mutation and submission belongs to Launch."""
    owner, commission, configuration = state_of(ctx, arguments)
    command = 'cd ' + shlex.quote(WORKSPACE) + ' && ' + arguments['command']
    memory = memory_configured(ctx.settings)
    identity = 'discovery:' + ctx.operation_key
    prior = ledger_find(ctx.store, owner, identity)
    if prior is not None:
        return outcome(prior['body'])
    cache_key = resource_identity(commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
    value = None
    if memory:
        cached = estimate_latest(ctx, cache_key, 'inventory')
        if cached['state'] == 'fresh':
            value = cached['data']
    if value is None:
        completed = await run_discovery_service(ctx, configuration, command)
        value = {'command': arguments['command'], 'returncode': completed['returncode'],
                 'stdout': completed['stdout'][:DISCOVERY_STDOUT_BYTES].decode('utf-8', 'replace'),
                 'stderr': completed['stderr'][:DISCOVERY_STDERR_BYTES].decode('utf-8', 'replace'),
                 'observed_at': time.time(), 'truncated': len(completed['stdout']) > DISCOVERY_STDOUT_BYTES}
        if memory and completed['returncode'] == 0:
            estimate_observe(ctx, cache_key, 'inventory', value, observed_at=value['observed_at'],
                             provenance=['discovery:' + ctx.operation_key])
    ledger_put(ctx.store, owner, 'discovery', value, identity=identity)
    return outcome(value)


def hpc_candidate_propose(arguments, ctx):
    owner, commission, _ = state_of(ctx, arguments)
    resources = resources_of(ctx.settings)
    try:
        candidate = json.loads(arguments['candidate_json'])
        known = candidates(ctx.store, owner, commission)
        prior = next((row for row in known if row['id'] == candidate['id']), None)
        if prior is not None and prior != candidate:
            raise ValueError('candidate_identity_is_immutable')
        validate_commission({**commission, 'candidates': known if prior else known + [candidate]}, resources)
    except (ValueError, KeyError, TypeError) as error:
        return outcome(code=str(error))
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates'] else
                 ledger_put(ctx.store, owner, 'candidate', candidate, identity='candidate:' + candidate['id']))
    return outcome({'candidate_ref': reference, 'candidate_id': candidate['id']})


async def hpc_queue_observe(arguments, ctx):
    owner, commission, configuration = state_of(ctx, arguments)
    reference = 'queue:' + hpc_queue.digest(ctx.operation_key)
    prior = ledger_find(ctx.store, owner, reference)
    if prior is not None:
        observed = prior['body']
    else:
        observed = await observed_queue(ctx, commission, configuration)
        ledger_put(ctx.store, owner, 'queue', observed, identity=reference)
    return outcome({'queue_ref': reference,
                    'features': [hpc_queue.features(observed['snapshot'], candidate)
                                 for candidate in candidates(ctx.store, owner, commission)],
                    'snapshot': observed['snapshot']})


def hpc_model_fit(arguments, ctx):
    owner, commission, configuration = state_of(ctx, arguments)
    selected = set(arguments['training_ids'])
    if memory_configured(ctx.settings):
        ledger_once(ctx.store, owner, 'shared_history:' + ctx.operation_key, 'shared_history',
                    lambda: shared_history(ctx, owner, commission, configuration))
    cases = history_cases(ctx.store, owner, commission)
    if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
        raise ValueError('training_ids_must_be_original_nonvalidation_cases')
    heldout = [cases[key] for key in commission['validation_ids']]
    historical_selected = selected.intersection(row['id'] for row in commission['history'])
    if historical_selected and heldout and (max(cases[key]['observed_at'] for key in historical_selected)
                                            >= min(row['observed_at'] for row in heldout)):
        raise ValueError('training_must_precede_temporal_validation')
    model = prediction.fit(commission['model'], [cases[key] for key in selected])
    model_ref = ledger_put(ctx.store, owner, 'model', model)
    # Fixed historical validation cannot measure a model trained on later completed allocations. Those updates
    # earn prospective credit when the next real outcomes arrive, not retrospective quality.
    later_training = selected - set(row['id'] for row in commission['history'])
    quality = None if later_training else model_quality(commission, model)
    baseline = model_quality(commission, ledger_read(ctx.store, owner, 'reference_model'))
    ledger_put(ctx.store, owner, 'model_choice', {'operation_key': ctx.operation_key, 'model_ref': model_ref,
                                                  'episode_id': ctx.episode_id})
    model_credit(ctx.store, owner, commission, model_ref, quality - baseline if quality is not None else 0.)
    return outcome({'model_ref': model_ref, 'validation_quality': quality, 'reference_quality': baseline,
                    'credit': ledger_credit_view(ctx.store, owner)})


def hpc_compare(arguments, ctx):
    owner, commission, _ = state_of(ctx, arguments)
    try:
        result = {'comparisons': comparisons(ctx.store, owner, commission, arguments['model_ref'],
                                             arguments['queue_ref'])}
    except (ValueError, KeyError) as error:
        return outcome(code=str(error), recovery=(
            'Use a model_ref from hpc_model_fit or hpc_model_ref and a queue_ref from hpc_queue_observe or '
            'hpc_queue_refs; a resource identity is not a queue observation.'))
    selection = {key: arguments[key] for key in ('model_ref', 'queue_ref')}
    result['comparison_ref'] = ledger_put(ctx.store, owner, 'comparison', {
        **result, **selection, 'episode_id': ctx.episode_id, 'operation_key': ctx.operation_key})
    return outcome(result)


TOOLS = {'hpc_initialize': hpc_initialize, 'hpc_read': hpc_read, 'hpc_history_refresh': hpc_history_refresh,
         'hpc_discovery_run': hpc_discovery_run, 'hpc_candidate_propose': hpc_candidate_propose,
         'hpc_queue_observe': hpc_queue_observe, 'hpc_model_fit': hpc_model_fit, 'hpc_compare': hpc_compare}


# ---------------------------------------------------------------------------------------------------------------
# Deciding.
# ---------------------------------------------------------------------------------------------------------------

def selection_schema(memory):
    """What the model answers with: one offered tool and its arguments (the old action schema, tool kind only)."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
        for entry in operation_catalog(memory)]}})


def generation_schema(schema):
    return strict_output_schema(schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decode_response(value, schema):
    return decode_strict_output(value, schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def instructions(*, knowledge, launch_library):
    """The old composition (``task_instructions.instructions``): the goal text, then the tool-knowledge and
    launch-library texts when those libraries are present."""
    text = GOAL
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    """The first unit is the initialization of the ledger state; then ask the model for the next action, shown the
    assignment, the ledger state (the old ``hpc_*`` decision context), the credit, the last outcome, the tools, the
    measured time, the yield table and the library listings."""
    if not summary['initialized']:
        return ToolCall('hpc_initialize', {'owner_episode_id': summary['owner_episode_id']})
    settings = ctx.settings
    ledger = summary['ledger']
    memory = memory_configured(settings)
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    yields = summary['action_yields']
    selected_launch = (None if launch is None
                       else launch.materialize(summary['message'].get('launch_instructions')))
    context = {'goal': GOAL, 'hpc_assignment': {'owner_episode_id': summary['owner_episode_id'],
                                                'commission_identity': summary['commission_identity']},
               **ledger, 'hpc_resource': resources_of(settings)[ledger['hpc_commission']['resource_id']],
               'current_credit': None if yields is None else yields['current_credit'],
               'credit_binding': CREDIT_BINDING, 'last_local_outcome': summary['last_outcome'],
               'requested_action_history': summary['history'], 'tools': operation_catalog(memory),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': yields, 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': selected_launch,
        'initial_information': settings.get('initial_information'),
        'hpc_shared_memory': shared_memory_record(ctx) if memory else None},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema(memory)))


CREDIT_BINDING = {'credit_kind': 'operational',
                  'rule': ('credit = commission credit.model_scale x (held-out quality of the current model minus '
                           'its quality at this episode\'s entry) + the validation credit the parent ledger '
                           'attributes to predictions made in this episode; signed; a model trained on any case '
                           'outside the commission\'s original history has no measured quality; actual job credit '
                           'is not counted here')}


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). The tool travels with the ledger owner,
    because a tool is handed no summary."""
    memory = memory_configured(ctx.settings)
    schema = selection_schema(memory)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    return ToolCall(selection['tool'], {**selection['arguments'], 'owner_episode_id': summary['owner_episode_id']})
