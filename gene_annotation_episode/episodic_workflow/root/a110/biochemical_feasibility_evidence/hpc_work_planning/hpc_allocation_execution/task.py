"""The task: prepare, plan, launch, observe and parse real allocation work, one action per unit.

Carried from the old ``work_operations.py`` (``catalog``, ``execute``), ``portfolio_state.py``,
``received_evidence.py``, ``measured_history.py``, ``portfolio_candidates.py``, ``portfolio_comparison.py``,
``portfolio_planning.py``, ``queue_observations.py``, ``resource_discovery.py``, ``allocation_handoff.py``,
``allocation_observations.py``, ``forecast_observations.py``, ``allocation_results.py``, ``allocation_order.py``,
``waiting.py`` (the tool ``hpc.monitor.wait``), ``task.py``, ``task_instructions.py``, ``task_decision.py``,
``decision_inputs.py`` and the instruction text of ``goal.py``. One unit is one model-selected action: a tool call
(the twelve old HPC tools) or the commission of the ``launch``, ``monitor`` or ``results`` child. The task always
offers a unit and never ends the Episode: only the yield controller does. The old ``wait`` and ``redeliver_report``
actions, the reasoning-commit (the old episode had none) and the decision exchange are not carried.

Tool names are ``[a-z][a-z0-9_]*`` now: ``hpc.read`` is ``hpc_read``, ``hpc.monitor.wait`` is ``hpc_monitor_wait``,
and so on. A tool returns a failure of the model's arguments as an outcome (``status`` ``invalid``) and raises for a
broken ledger or receipt. Every outcome carries ``ledger_view``: what the owner ledger shows after the tool (the old
``decision_context`` read it live at every decision; ``internal_summary`` is pure now and takes the latest view from
the outcomes). Its ``credit`` is the owner ledger's credit view: ``credit.py`` reads the number from it.

Settings this episode reads (``ctx.settings``; the old ``configuration.py`` values): ``directory`` (the root of the
owner ledgers and the launch input files), ``resources`` (the configured resources by id; one must be a ``pbs_ssh``
resource), ``shared_execution_memory`` (boolean: whether the shared timing memory is used), ``handoff_unit``,
``information_unit`` and ``acquired_record_unit`` (the credits one received handoff, one informative progress
snapshot and one acquired selector or result earn in the three children; they ride in the child commissions),
``launch_instruction_directory`` and ``tool_knowledge_directory`` (optional library directories) and the yield
settings ``cutoff`` and ``parameters`` (``yield_estimator.py``).

The owner ledger (``HpcLedger``, rows of the work table ``HPC_LEDGER`` in custody, shared with its prediction sibling)
is opened with ``HpcLedger.existing(ctx.store, ledger)``; the parent passes the ledger id and the rows in custody.

BLOCKED-ON-JOB-SERVICE: every call that reaches the scheduler, the resource or the shared timing memory, and the
read of the handoff record the launch child returned, are not provided. ``handoff_target``, ``observe_target``,
``read_window``, ``write_allocation_control``, ``observe_queue_value``, ``run_command``, ``estimate_latest``,
``estimate_observe``, ``estimate_history``, ``estimate_policy`` and ``estimate_record`` each name the call they want
and raise where they are reached. ``decide`` reads ``ctx.services['estimate_table']`` for the tool estimates: no such
service exists, so a run cannot be linked until the caller supplies one.

Not placed (A110 only): the old ``initial_information.py`` (``resource_information`` of the readers a recipient
selected from the old ``catalog``: ``execution_initial_information.presentation``) and
``received_execution_information.py`` (``catalog.received`` / ``catalog.configured``): neither is in
``episode_support/``; the model is shown the configured resource (``hpc_resource``) and the tool estimates instead."""
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

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.execution_contracts import (
    obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import canonical, digest
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence.hpc_campaign import (
    accepts, bind_progress, build_plan, incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence.hpc_history import (
    closed_measurement)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HpcLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence.hpc_resource_prediction import (
    forecast_metric, measured_value, pbs_resource_metrics, physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import (
    time_accounting, yield_table)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    RECORD_SCHEMAS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

_PREFIX = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/'
CHILD_SLOTS = {'launch': _PREFIX + 'execution_job_submission',
               'monitor': _PREFIX + 'execution_progress_assessment',
               'results': _PREFIX + 'execution_result_acquisition'}
SERVICES = ('job_access', 'estimate_table')
MODEL_ROLE = 'REASONING'
PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'
MONITOR_FIELD_OPTIONS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
                         'result_available')
MONITOR_SELECTION = ('monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available',
                     'monitoring_observed_at_unix_seconds', 'monitoring_committed_record_refs',
                     'monitoring_progress_snapshots')
# The launch child returns its handoff records and its completion as required fields and the results child returns
# its result records, their artifacts and its completion as required fields: nothing is left to select.
LAUNCH_SELECTION = ()
RESULTS_SELECTION = ()
# The resource of this episode is a ``pbs_ssh`` resource, the kind the results child calls ``hpc``.
RESULTS_RESOURCE_KIND = 'hpc'
# The keys the action adds to every tool's arguments: they come from the commission, not from the model.
INJECTED = ('owner_episode_id', 'commission_identity', 'scope')

INSTRUCTIONS = (
    'Iterate toward the original accomplishment while balancing expected credit against real elapsed time and '
    'resource demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction '
    'fits/measures/compares; execution prepares, launches, monitors and parses the selected work. Both sisters '
    'work on the same owner ledger and inherit the same scope, including an empty subject_refs list for an '
    'operational task with no biological inputs. Candidate IDs, model IDs, queue observations and resource IDs are '
    'not biological subject_refs. Use the shared current model and comparisons; resource observations and '
    'candidate requests are different quantities. If suitable history is available, a prediction iteration can '
    'improve sizing before launching. No historical validation support means no invented model-improvement '
    'credit. Queue/setup costs belong to an allocation, which should carry enough useful work. When candidates are '
    'absent, discover the remote environment and documentation with hpc_discovery_run, then design candidate '
    'portfolios with hpc_candidate_propose. Discover is for lightweight inspection; leave installation and file '
    'staging to Launch, and scientific computation to the actual allocation. You choose the real inputs, '
    'database, executable commands, resources, worker code and preparation instructions. Never fabricate inputs or '
    'receipts. Every work unit writes result.json and progress.json under os.environ["HPC_UNIT_DIRECTORY"], its '
    'original per-unit working directory. The allocation workspace is for staged inputs, not these unit outputs; '
    'its fields must satisfy the caller acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. '
    'Candidate files use relative paths; {allocation_workspace} expands in files, argv, environment and '
    'preparation. Compute commands must run on allocated compute nodes using the facility launcher. Compare '
    'portfolios using current queue features and measured history. A plan freezes its original forecast, '
    'scientific manifest and acceptance criteria. Commission launch (the child slot launch) with that actual job '
    'and resource: name the plan_ref of a frozen plan; the launch commission is built from that plan. The '
    'execution agent chooses its scripts, environment and operational commands from the supplied resource '
    'instructions and observations. Supplied reference sources are available in the local input file; do not '
    'transcribe them into a child goal or prescribe a setup/submit sequence. A plan is launched once: the '
    'launch child returns the received handoff reference, and a launch must not be commissioned again for the '
    'same plan. Attach that received handoff with hpc_handoff. Use hpc_monitor once when another observation can '
    'affect your decision; it revises conditional predictions and attainable credit. Use hpc_results directly for '
    'known parsing. Commission the monitor and results children only for actual investigation. Completed unit '
    'outputs can await parsing while PBS is still running or cleaning up. When a monitor shows completed units '
    'whose outputs are not yet parsed, use hpc_results for those original outputs; completion is not '
    'acceptance. When hpc_monitor_controllers is present, select hpc_monitor_wait for a scheduled observation: '
    'its attached controller evaluates the conditional forecast, persists a wake time, and executes the original '
    'monitor at that time. This preserves pending accomplishment value across waits without credit for sleeping. '
    'The timer cannot turn into another unobserved wait. Do not poll for credit or duplicate a submitted attempt. '
    'Never replace an uncertain submission. Accepted accomplishment, model improvement, and fixed prospective '
    'forecast validation are the only parent credit components; launch-local credits are not added again. '
    'Read the owner commission with hpc_read (reference commission) when you need it again. Answer with one '
    'selection from the offered actions and its arguments as JSON object text in arguments_json (the actions list '
    'gives the argument schema of each).')

LAUNCH_JOB_INSTRUCTIONS = (
    'The supplied local input file contains the frozen scientific manifest and reference source files. Use general '
    'terminal commands on the coordinator or assigned resource as needed; choose your scripts, environment and '
    'transfer method. Do not transcribe supplied source code into a child goal. Reference implementation files are '
    'available inputs, not a required execution procedure. Preserve original unit identities, scientific inputs, '
    'output/progress formats and acceptance predicates. Run computation in the actual allocation and retain its '
    'original identity. An uncertain submission must be investigated rather than duplicated.')

_TEXT = {'type': 'string', 'minLength': 1}
_STRINGS = {'type': 'array', 'uniqueItems': True, 'items': _TEXT}

# The old tool catalogue (``HPCWorkOperations.catalog``), under the new tool names. ``shared`` entries first.
TOOL_CATALOG = {
    'hpc_read': ('Read retained HPC evidence by its exact identity.', obj({'reference': _TEXT})),
    'hpc_compare': ('Compare all approved portfolios; no work is selected or launched.',
                    obj({'model_ref': _TEXT, 'queue_ref': _TEXT})),
    'hpc_history_refresh': ('Read age-weighted shared timing history once. No remote discovery, polling credit, or '
                            'new scientific work.', obj({})),
    'hpc_discovery_run': ('Run one lightweight remote inspection or documentation retrieval through the '
                          'established SSH transport. No job submission, installation or scientific computation; '
                          'those belong to Launch and the allocation.', obj({'command': _TEXT})),
    'hpc_candidate_propose': (
        'Retain an executable portfolio selected by this episode. candidate_json is JSON with id, queue, nodes, '
        'wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), '
        'optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units '
        '(unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: '
        'relative path, text: exact contents}], and preparation instructions for Launch. effort is a positive '
        'finite number expressing relative work, for example 1.0; workload sizes belong in features. No per-unit '
        'execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate identities '
        'are immutable.', obj({'candidate_json': _TEXT})),
    'hpc_queue_observe': ('Acquire PBS queue and ALCF score/status once and transform them.', obj({})),
    'hpc_plan': ('Freeze one useful portfolio and its forecasts; return a concrete launch assignment.',
                 obj({'candidate_id': _TEXT, 'model_ref': _TEXT, 'queue_ref': _TEXT})),
    'hpc_handoff': ('Bind the original received PBS handoff to the exact frozen portfolio.',
                    obj({'plan_ref': _TEXT, 'handoff_ref': _TEXT})),
    'hpc_monitor': ('Observe the original job and progress once; update and freeze conditional forecasts.',
                    obj({'plan_ref': _TEXT, 'refresh_queue': {'type': 'boolean'}})),
    'hpc_monitor_wait': ('Use the attached forecast-valued monitor controller: persist a timer, release the '
                         'coordinator while waiting, then observe this original job exactly once when due. No '
                         'earned credit for waiting.', obj({'plan_ref': _TEXT})),
    'hpc_results': ('Parse compact results from the original allocation and apply original acceptance '
                    'predicates.', obj({'plan_ref': _TEXT})),
    'hpc_allocation_order': ('Reorder original pending units at the next unit boundary, retaining all unstarted '
                             'work.', obj({'plan_ref': _TEXT, 'unit_ids': _STRINGS})),
}
# The children the model may commission (the old ``launch``, ``monitor`` and ``results`` roles). The commission is
# built in ``messages/msg_to_child.py`` from these arguments and the summary.
CHILD_CATALOG = {
    'launch': ('Commission the launch of one frozen plan on its explicit resource; returns the received handoff '
               'reference. Launched once per plan.', obj({'plan_ref': _TEXT})),
    'monitor': ('Commission the monitor child to report the state of one execution target (a handoff handle). This '
                'parent requests information; it never polls here.',
                obj({'target_handle': _TEXT,
                     'requested_fields': {'type': 'array', 'uniqueItems': True,
                                          'items': {'type': 'string', 'enum': list(MONITOR_FIELD_OPTIONS)}},
                     'known_progress_refs': {'type': 'array', 'items': _TEXT},
                     'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                                          'items': {'type': 'string',
                                                                    'enum': sorted(RECORD_SCHEMAS)}}})),
    'results': ('Commission the result-acquisition child for actual investigation of result files of a received '
                'handoff; known parsing is done directly with hpc_results.',
                obj({'handoff_ref': _TEXT, 'selector': {'type': 'object'}},
                    required=['handoff_ref', 'selector'])),
}


# ---------------------------------------------------------------- the missing job services (BLOCKED-ON-JOB-SERVICE)

def handoff_target(store, handoff_ref):
    """The execution target (handle, resource, workspace, assignment) the held handoff record names: the old
    ``targets.read_target(handoff_ref, scope)`` of ``ExecutionTargetReader``.

    BLOCKED-ON-JOB-SERVICE: job ledger handoff record (the handoff row the launching child writes and returns; no
    job record kind is declared); wanted call: ``store.table(JOB_LEDGER).get(handoff_ref)`` read as the execution
    target (``JOB_LEDGER`` is the job library's work table, not written yet)."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call: '
                              'ctx.store.table(JOB_LEDGER).get(handoff_ref) as the execution target')
    return store.table(None).get(handoff_ref)


async def observe_target(target, key, ctx):
    """One observation of the original job: the old ``targets.observe_target(target, operation_key=key)``.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].observe_target(target,
    key=key, resumed=ctx.resumed)``, idempotent on ``key``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].observe_target(target, key=key, resumed=ctx.resumed)")
    return await ctx.services['job_access'].observe_target(target, key=key, resumed=ctx.resumed)


async def read_window(target, path, limit, key, ctx):
    """One bounded read of a file of the allocation: the old ``targets.read_file(target, path=path, offset=0,
    limit=limit + 1, operation_key=key)``.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].read_file(target,
    path=path, offset=0, limit=limit + 1, key=key, resumed=ctx.resumed)``, idempotent on ``key``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].read_file(target, path=path, offset=0, limit=limit + 1, "
                              'key=key, resumed=ctx.resumed)')
    return await ctx.services['job_access'].read_file(target, path=path, offset=0, limit=limit + 1, key=key,
                                                      resumed=ctx.resumed)


async def write_allocation_control(target, unit_ids, key, ctx):
    """Write the unit order into the allocation: the old ``targets.operations[resource_id].write_allocation_control(
    assignment, execution_id, **native_identity, unit_ids=..., operation_key=key)``.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].write_allocation_control(
    target, unit_ids=unit_ids, key=key, resumed=ctx.resumed)``, idempotent on ``key``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].write_allocation_control(target, unit_ids=unit_ids, "
                              'key=key, resumed=ctx.resumed)')
    return await ctx.services['job_access'].write_allocation_control(target, unit_ids=unit_ids, key=key,
                                                                     resumed=ctx.resumed)


async def observe_queue_value(configuration, key, ctx):
    """One read-only acquisition of the PBS queue and facility status: the old ``hpc_queue.observe(configuration)``
    (library function over the resource's SSH transport).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].observe_queue(
    configuration, key=key)`` (the service wraps ``hpc_queue.observe``)."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].observe_queue(configuration, key=key)")
    return await ctx.services['job_access'].observe_queue(configuration, key=key)


async def run_command(configuration, command, key, ctx):
    """One lightweight remote command over the resource's established SSH transport: the old ``subprocess.run([*
    configuration['ssh_argv'], command], ...)``. The old 90-second timeout and the truncation of the output were
    limits of that call; the service owns whatever limits it has.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].run_command(configuration,
    command, key=key)`` returning ``{'command', 'returncode', 'stdout', 'stderr', 'observed_at', 'truncated'}``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].run_command(configuration, command, key=key)")
    return await ctx.services['job_access'].run_command(configuration, command, key=key)


def estimate_latest(ctx, resource, kind):
    """The old ``memory.latest(resource, kind)`` (``{'state', 'age_seconds', 'data', ...}``).

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].latest(resource,
    kind)``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: '
                              "ctx.services['estimate_table'].latest(resource, kind)")
    return ctx.services['estimate_table'].latest(resource, kind)


def estimate_observe(ctx, resource, kind, data, *, observed_at, provenance):
    """The old ``memory.observe(resource, kind, data, observed_at=..., provenance=...)``.

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].observe(resource, kind,
    data, observed_at=observed_at, provenance=provenance, key=ctx.operation_key)``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: '
                              "ctx.services['estimate_table'].observe(resource, kind, data, observed_at=observed_at, "
                              'provenance=provenance, key=ctx.operation_key)')
    return ctx.services['estimate_table'].observe(resource, kind, data, observed_at=observed_at,
                                                  provenance=provenance, key=ctx.operation_key)


def estimate_history(ctx, query, *, now, queue_only=False):
    """The old ``memory.history(query, now=now, queue_only=queue_only)`` (every row: the old call kept the first
    2000, a count limit that is not carried).

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].history(query, now=now,
    queue_only=queue_only)``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: '
                              "ctx.services['estimate_table'].history(query, now=now, queue_only=queue_only)")
    return ctx.services['estimate_table'].history(query, now=now, queue_only=queue_only)


def estimate_policy(ctx):
    """The old ``memory.as_record()['policy']``.

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].policy()``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: "
                              "ctx.services['estimate_table'].policy()")
    return ctx.services['estimate_table'].policy()


def estimate_record(ctx, measurement):
    """The old ``memory.record(**closed_measurement(...))`` of a closed allocation.

    BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ``ctx.services['estimate_table'].record(**measurement,
    key=ctx.operation_key)``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: '
                              "ctx.services['estimate_table'].record(**measurement, key=ctx.operation_key)")
    return ctx.services['estimate_table'].record(**measurement, key=ctx.operation_key)


def monitor_attach(ledger, plan, job_id, policy):
    """Attach the forecast-valued monitor controller to the original job: the old ``MonitorCronController(ledger).
    attach(plan, job_id, policy)``.

    Not placed: ``MonitorCronController`` is not in this axis's ``episode_support/jobs/hpc/biochemical_feasibility_
    evidence/hpc_monitoring.py`` (which holds ``validate_policy`` only; the old module was in the old shared root, not
    read). Reached only when the commission declares ``monitoring``."""
    raise NotImplementedError('hpc_monitor_controller_not_placed:A110; wanted call: '
                              'MonitorCronController(ledger).attach(plan, job_id, policy)')
    return MonitorCronController(ledger).attach(plan, job_id, policy)  # noqa: F821


def monitor_reserve(ledger, plan, candidate, monitor, key):
    """The schedule the controller reserves for the next observation: the old ``MonitorCronController(ledger).
    reserve(plan, candidate, monitor, key)`` (not placed, see ``monitor_attach``)."""
    raise NotImplementedError('hpc_monitor_controller_not_placed:A110; wanted call: '
                              'MonitorCronController(ledger).reserve(plan, candidate, monitor, key)')
    return MonitorCronController(ledger).reserve(plan, candidate, monitor, key)  # noqa: F821


async def monitor_wait(ledger, schedule):
    """Persist the wake time and wait for it: the old ``await MonitorCronController(ledger).wait(schedule)`` (not
    placed, see ``monitor_attach``)."""
    raise NotImplementedError('hpc_monitor_controller_not_placed:A110; wanted call: '
                              'await MonitorCronController(ledger).wait(schedule)')
    await MonitorCronController(ledger).wait(schedule)  # noqa: F821


# ------------------------------------------------------------------------------------------- the owner ledger state

def memory_enabled(ctx):
    return bool(ctx.settings['shared_execution_memory'])


def resource_of(ledger, ctx):
    return ctx.settings['resources'][ledger.commission['resource_id']]


def candidates_of(ledger):
    return ledger.commission['candidates'] + [row['body'] for row in ledger.records('candidate')]


def candidate_of(ledger, plan):
    return next(row for row in candidates_of(ledger) if row['id'] == plan['candidate_id'])


def current_model(ledger):
    records = ledger.records('model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'


def candidate_features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:' + candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}


def accepted_obligations(ledger):
    return [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
            if row['kind'] == 'actual']


def measured_history(ledger):
    """The measured history used for fitting (one latest observation per closed allocation)."""
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


def collected_unit_ids(ledger, plan):
    return {row['body']['unit']['unit_id'] for row in ledger.records('result')
            if row['body'].get('plan_id') == plan['plan_id'] and isinstance(row['body'].get('unit'), dict)
            and isinstance(row['body']['unit'].get('unit_id'), str)}


def uncollected_completed_unit_ids(ledger, plan, current):
    allowed = {unit['unit_id'] for unit in candidate_of(ledger, plan)['units']}
    observed = set(current.get('telemetry', {}).get('completed_unit_ids', ()))
    return (observed & allowed) - collected_unit_ids(ledger, plan)


def last_forecast(ledger, plan):
    monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
    if monitors:
        return monitors[-1]
    forecasts = [row for row in ledger.records('forecast') if row['body']['plan_id'] == plan['plan_id']]
    return {'conditional_prediction': plan['original_prediction'], 'forecast_ref': forecasts[0]['id']}


def launch_input_ref(ledger, plan_id):
    """The held artifact of the frozen plan supplied to the launch child (the old local input file under the ledger
    directory; the ledger has no directory now: the plan is an artifact the ledger names)."""
    return [row['body']['artifact_ref'] for row in ledger.records('launch_input')
            if row['body']['plan_id'] == plan_id][-1]


def ledger_view(ledger, ctx):
    """What the owner ledger shows now: the old ``HPCSummary.decision_context`` ledger fields, with the credit view
    the old ``HPCEpisodeCredit.credit_view`` read."""
    commission = ledger.commission
    model_ref = current_model(ledger)
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    plans = [{'plan_ref': row['id'], 'plan_id': row['body']['plan_id'], 'candidate_id': row['body']['candidate_id'],
              'closed': row['body']['plan_id'] in closed, 'launch_assignment': row['body']['launch_assignment'],
              'manifest': row['body']['manifest'],
              'supplied_input_artifact_ref': launch_input_ref(ledger, row['body']['plan_id'])}
             for row in ledger.records('plan')]
    view = {'ledger': ledger.ledger, 'row_refs': ledger.refs(), 'credit': ledger.credit_view(), 'owner_episode_id': ledger.read('owner')['episode_id'],
            'commission': commission, 'candidates': candidates_of(ledger), 'model_ref': model_ref,
            'model_refs': [row['id'] for row in ledger.records('model')],
            'model_support': prediction.predict(ledger.read(model_ref), {})['support'],
            'tool_requests': [row['body'] for row in ledger.records('tool_request')],
            'latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                   if key not in ('episode_id', 'operation_key')}}
                                  for row in ledger.records('comparison')[-1:]],
            'plans': plans, 'latest_monitor': ledger.records('monitor')[-1:],
            'monitor_controllers': ledger.records('monitor_controller'),
            'queue_refs': [row['id'] for row in ledger.records('queue')],
            'coordinator_workspace': str(Path(ctx.settings['directory']).resolve()),
            'available_training_ids': sorted(set(measured_history(ledger)) - set(commission['validation_ids']))}
    if memory_enabled(ctx):
        view['shared_history_refs'] = [row['id'] for row in ledger.records('shared_history')]
    return view


def completed(ledger, ctx, result, references=()):
    return {'status': 'completed', 'record_refs': list(references), 'result': result, 'feedback': None,
            'ledger_view': ledger_view(ledger, ctx)}


def invalid(ledger, ctx, feedback):
    return {'status': 'invalid', 'record_refs': [], 'result': None, 'feedback': feedback,
            'ledger_view': ledger_view(ledger, ctx)}


def argument_error(code, **more):
    return {'category': 'arguments_or_reference', 'code': code, **more}


def shared_history(ledger, ctx):
    """The shared timing history for this resource (the old ``_shared_history``); no row is dropped to a count."""
    commission = ledger.commission
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], resource_of(ledger, ctx))
    # Queue timing is resource-wide. Work timing requires explicit matching algorithm, parameters, software and
    # hardware, never just 'Aurora'.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
                        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in estimate_history(ctx, query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in estimate_history(ctx, profile, now=now)})
    queues = {candidate['queue'] for candidate in candidates_of(ledger)}
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
    return {'captured_at': now, 'policy': estimate_policy(ctx),
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts]}


def recorded(ledger, identity, kind, calculate):
    """The evidence ``calculate()`` under ``identity`` (the same evidence again is the same row)."""
    value = calculate()
    ledger.put(kind, value, identity=identity)
    return value


def open_ledger(arguments, ctx):
    """The owner's ledger for this commission, with the reference model in place (the old ``state`` and
    ``initialize``). The ledger must carry this commission's scope and commission identity
    (``sister_scope_must_equal_original_parent_scope``)."""
    ledger = HpcLedger.existing(ctx.store, arguments['ledger'])
    original = ledger.read('owner')
    identity = {name: original[name] for name in ('commission_id', 'commission_source_ref') if name in original}
    if original['scope'] != arguments['scope'] or identity != arguments['commission_identity']:
        raise ValueError('sister_scope_must_equal_original_parent_scope')
    if not ledger.records('model'):
        prior = prediction.prior_model(ledger.commission['model'])
        ledger.put('model', prior, identity='reference_model')
        if memory_enabled(ctx):
            imported = recorded(ledger, 'shared_history_entry', 'shared_history', lambda: shared_history(ledger, ctx))
            if imported['observations'] and not ledger.records('model_choice'):
                model = prediction.fit(ledger.commission['model'], imported['observations'])
                reference = ledger.put('model', model)
                ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                           identity='shared_history_initial_model')
    return ledger


async def once(ledger, identity, kind, calculate):
    """Recover a committed step without another observation (the old ``ledger.once``), for an awaited step."""
    try:
        return ledger.read(identity)
    except ValueError as error:
        if not str(error).startswith('unknown_hpc_evidence:'):
            raise
    value = await calculate()
    ledger.put(kind, value, identity=identity)
    return value


def queue_snapshot(ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits'][
            'queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


async def observe_queue(ledger, ctx, key):
    """One queue observation, from the shared memory while it is fresh (the old ``_observe_queue``)."""
    configuration = resource_of(ledger, ctx)
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if memory_enabled(ctx):
        cached = estimate_latest(ctx, resource, 'queue')
        if cached['state'] == 'fresh' and cached['age_seconds'] <= ledger.commission['limits'][
                'queue_max_age_seconds']:
            return cached['data']
    value = await observe_queue_value(configuration, key, ctx)
    if memory_enabled(ctx):
        estimate_observe(ctx, resource, 'queue', value, observed_at=value['snapshot']['captured_at'],
                         provenance=value['acquisition'])
    return value


def comparisons(ledger, model_ref, queue_ref):
    model = ledger.read(model_ref)
    observed = queue_snapshot(ledger, queue_ref)
    actual = accepted_obligations(ledger)
    results = []
    for candidate in candidates_of(ledger):
        queue = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, candidate_features(candidate, queue))
        row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                 ledger.commission['preferences'], already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)


def freeze_forecast(ledger, plan, predicted, reference, current, phase, key):
    elapsed = {'queue': current.get('queue_elapsed_seconds', 0.), 'work': current.get('work_elapsed_seconds', 0.)}
    slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
             if slot['phase'] == phase and elapsed.get(slot['metric'], elapsed['work']) >= slot[
                 'minimum_elapsed_seconds'] and forecast_metric(predicted, slot['metric']) is not None]
    body = recorded(ledger, 'issued:' + key, 'forecast_issue', lambda: {
        'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted, 'reference': reference,
        'phase': phase, 'elapsed': elapsed, 'model_ref': plan.get('model_ref'),
        'prediction_episode_id': plan.get('prediction_episode_id')})
    return ledger.freeze(body, slots)


def measure(ledger, plan, observation, current, allocation):
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


def export_closed(ledger, ctx, plan):
    """Retained completed runs enter the shared history; no remote work (the old ``export_closed``)."""
    if not memory_enabled(ctx):
        return
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('only_closed_allocations_enter_shared_history')
    measured = recorded(ledger, 'export_measurement:' + plan['plan_id'], 'export_measurement', lambda: [
        row for row in ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
    handoff = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']][-1]
    estimate_record(ctx, closed_measurement(ledger.commission, plan, measured, handoff, resources=ctx.settings[
        'resources'], ledger=ledger.ledger))


def read_evidence(arguments, ctx, ledger, reference):
    """Retained HPC evidence by exact identity: a history row, a ledger record or a result source this Episode
    holds (the old ``read_evidence``)."""
    history = measured_history(ledger)
    if reference in history:
        return history[reference]
    if not reference.startswith('source_'):
        return ledger.read(reference)
    # Results publish ordinary Store sources as well as ledger receipts. Resolve only a held source owned by this
    # original HPC ledger.
    rows = [row['body'] for row in ledger.records('result') if row['body'].get('source_ref') == reference]
    if len(rows) != 1 or not resolve_result_source(ctx, arguments['scope'], reference):
        raise ValueError('hpc_result_source_not_received_or_not_owned')
    source = ctx.store.get(reference)
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
    if body != expected:
        raise ValueError('hpc_result_source_receipt_conflict')
    return rows[0]


def resolve_result_source(ctx, scope, reference):
    """Whether ``reference`` is a held ``episode.hpc_result`` source of this run within ``scope`` (the old
    ``resolve_received_reference`` for the namespace ``source``)."""
    if not ctx.store.holds(reference):
        return False
    source = ctx.store.get(reference)
    if source.get('provider') != 'episode.hpc_result':
        return False
    body = json.loads(ctx.store.get_artifact(source['artifact_ref']))
    if body['run_id'] != ctx.run_id:
        return False
    try:
        ctx.store.validate_scope(body['scope'], parent_scope=scope)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------------- the allocation of one frozen plan

def original_target(arguments, ctx, ledger, plan):
    """The target of the handoff attached to ``plan`` (the old ``_target``). The handoff record must be held."""
    handoff = ledger.read('handoff:' + plan['plan_id'])
    if not ctx.store.holds(handoff['handoff_ref']):
        raise ValueError('original_handoff_not_received_by_this_parent')
    target = handoff_target(ctx.store, handoff['handoff_ref'])
    if target['assignment'] != plan['practical_assignment']:
        raise ValueError('handoff_does_not_match_frozen_portfolio')
    return target


async def window(target, path, limit, key, ctx):
    value = await read_window(target, path, limit, key, ctx)
    payload = base64.b64decode(value['bytes_base64'], validate=True)
    if len(payload) != value['size_bytes'] or len(payload) > limit:
        raise ValueError('compact_result_incomplete_or_too_large')
    return value, payload


async def window_value(target, path, limit, key, ctx):
    return (await window(target, path, limit, key, ctx))[0]


async def allocation_receipt(target, plan, key, ctx):
    path = plan['manifest']['workspace'] + '/allocation-status.json'
    try:
        value_window, payload = await window(target, path, 512 * 1024, key, ctx)
    except (FileNotFoundError, ValueError) as error:
        # Absence before the runner starts is normal; other failures remain visible and do not manufacture a
        # progress estimate.
        return [None, {'path': path, 'failure': str(error)}]
    value = json.loads(payload)
    if (value['plan_id'] != plan['plan_id'] or value['job_id'] != target['execution_id']
            or value['manifest_sha256'] != plan['manifest_sha256']):
        raise ValueError('allocation_receipt_identity_conflict')
    expected = {unit['unit_id'] for unit in plan['manifest']['units']}
    if len({row['unit_id'] for row in value['units']}) != len(value['units']) or not {
            row['unit_id'] for row in value['units']} <= expected:
        raise ValueError('allocation_receipt_units_conflict')
    return [value, value_window]


async def observe_allocation(ctx, ledger, plan, target, candidate, key):
    """One observation of the original job and its progress, with a measurement (the old
    ``_observe_original_allocation``, up to the branch on the tool)."""
    observation = await once(ledger, 'status:' + key, 'native_status', lambda: observe_target(target, key, ctx))
    allocation, allocation_window = await once(
        ledger, 'allocation:' + key, 'allocation_snapshot',
        lambda: allocation_receipt(target, plan, key + ':allocation', ctx))
    observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                                                 'allocation': allocation, 'allocation_window': allocation_window})
    current = telemetry(observation, allocation, candidate)
    if current.get('current_unit_id') is not None:
        unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
        if unit.get('reports_progress', False):
            progress_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/progress.json'
            try:
                progress_window = await once(
                    ledger, 'unit-progress:' + key, 'unit_progress',
                    lambda: window_value(target, progress_path, 16384, key + ':progress', ctx))
                progress = bind_progress(json.loads(base64.b64decode(progress_window['bytes_base64'],
                                                                     validate=True)), plan['plan_id'])
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
    measured_ref = measure(ledger, plan, observation, current, allocation)
    return {'observation': observation, 'allocation': allocation, 'allocation_window': allocation_window,
            'observation_ref': observation_ref, 'current': current, 'measured_ref': measured_ref}


async def update_conditional_forecast(arguments, ctx, ledger, plan, target, candidate, observed, key):
    commission = ledger.commission
    refreshed = None
    queue_ref = plan['queue_ref']
    if arguments['refresh_queue']:
        queue_ref = 'queue:' + digest(key)
        queue_value = await once(ledger, queue_ref, 'queue', lambda: observe_queue(ledger, ctx, key))
        queue = hpc_queue.features(queue_value['snapshot'], candidate, job_id=target['execution_id'])
        refreshed = prediction.predict(ledger.read(current_model(ledger)),
                                       candidate_features(candidate, queue))['times']['queue']
    current = observed['current']
    predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
    reference = prediction.update(plan['original_reference'], current)
    forecast_ref = freeze_forecast(ledger, plan, predicted, reference, current, current['state'], key)
    orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
    ordered_candidate = deepcopy(candidate)
    if orders:
        units = {row['unit_id']: row for row in candidate['units']}
        first = [current['current_unit_id']] if current.get('current_unit_id') else []
        ids = list(dict.fromkeys([*first, *orders[-1]['unit_ids'], *units]))
        ordered_candidate['units'] = [units[identity] for identity in ids]
    result = {'plan_id': plan['plan_id'], 'observation_ref': observed['observation_ref'],
              'measured_ref': observed['measured_ref'], 'forecast_ref': forecast_ref, 'queue_ref': queue_ref,
              'conditional_prediction': predicted,
              'remaining_work': prediction.compare(ordered_candidate, predicted, commission['obligations'],
                                                   commission['preferences']),
              'next_observation': 'Choose an event/elapsed threshold where changed evidence could alter a '
                                  'decision.'}
    ledger.put('monitor', result)
    return result


def publish_result(ctx, body):
    artifact = ctx.store.artifact(canonical(body), 'application/json')
    stored = ctx.store.put('source', {
        'provider': 'episode.hpc_result', 'accession': 'hpc_' + digest([ctx.run_id, ctx.episode_id, body]),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'hpc_result_v1',
        'retrieved_at': datetime.fromtimestamp(body['unit']['finished_at'], timezone.utc).isoformat()},
        origin='tool')
    return stored['id']


async def collect_original_results(arguments, ctx, ledger, plan, target, candidate, observed, key):
    commission = ledger.commission
    allocation, current = observed['allocation'], observed['current']
    accepted, failures, references = [], [], []
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
        unit_key = key + ':' + unit['unit_id']
        result_window = await once(
            ledger, 'result-window:' + key + ':' + unit['unit_id'], 'result_window',
            lambda: window_value(target, expected_path, commission['limits']['result_limit_bytes'], unit_key, ctx))
        payload = base64.b64decode(result_window['bytes_base64'], validate=True)
        if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
            raise ValueError('result_changed_since_unit_completion')
        document = json.loads(payload)
        receipt = {'run_id': ctx.run_id, 'episode_id': ctx.episode_id, 'scope': arguments['scope'],
                   'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row, 'document': document,
                   'window': result_window, 'observation_ref': observed['observation_ref']}
        source_ref = publish_result(ctx, receipt)
        references.append(source_ref)
        result_ref = ledger.put('result', {**receipt, 'source_ref': source_ref})
        if row['state'] == 'complete' and row.get('returncode') == 0 and accepts(
                document, commission['obligations'][unit['obligation_id']]):
            ledger.accept(unit['obligation_id'], result_ref)
            accepted.append({'obligation_id': unit['obligation_id'], 'result_ref': result_ref})
        else:
            failures.append({'unit_id': unit['unit_id'], 'reason': 'original_acceptance_predicate_not_met'})
    if current['state'] in ('complete', 'failed'):
        measured = ledger.read(observed['measured_ref'])
        if allocation is not None:
            measured['success'] = len(accepted) == len(candidate['units'])
            measured['observed_at'] = max(measured['observed_at'], time.time())
            ledger.put('measured', measured)
        ledger.put('closed', {'plan_id': plan['plan_id'], 'observation_ref': observed['observation_ref']})
        export_closed(ledger, ctx, plan)
    return ({'accepted': accepted, 'rejected': failures, 'observation_ref': observed['observation_ref'],
             'credit': ledger.credit_view()}, references)


def original_plan(ledger, arguments, ctx):
    """The frozen plan the arguments name, or the failure outcome when its handoff is not attached yet."""
    plan = ledger.read(arguments['plan_ref'])
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff')):
        return plan, invalid(ledger, ctx, argument_error(
            'original_handoff_not_attached',
            recovery='If the launch child already returned its handoff, attach the returned reference with '
                     'hpc_handoff. Do not launch replacement work.'))
    return plan, None


# ------------------------------------------------------------------------------------------------------------ tools

def hpc_read(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    try:
        result = read_evidence(arguments, ctx, ledger, arguments['reference'])
    except (ValueError, KeyError) as error:
        return invalid(ledger, ctx, argument_error(str(error)))
    return completed(ledger, ctx, result)


def hpc_compare(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    try:
        result = {'comparisons': comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
    except (ValueError, KeyError) as error:
        return invalid(ledger, ctx, argument_error(
            str(error), recovery='Use a model_ref from hpc_model_ref and a queue_ref from hpc_queue_observe or '
                                 'hpc_queue_refs; a resource identity is not a queue observation.'))
    result['comparison_ref'] = ledger.put('comparison', {**result, 'model_ref': arguments['model_ref'],
                                                         'queue_ref': arguments['queue_ref'],
                                                         'episode_id': ctx.episode_id,
                                                         'operation_key': ctx.operation_key})
    return completed(ledger, ctx, result)


def hpc_history_refresh(arguments, ctx):
    if not memory_enabled(ctx):
        raise ValueError('hpc_history_refresh_requires_shared_execution_memory')
    ledger = open_ledger(arguments, ctx)
    result = recorded(ledger, 'shared_history:' + ctx.operation_key, 'shared_history',
                         lambda: shared_history(ledger, ctx))
    return completed(ledger, ctx, result)


async def hpc_discovery_run(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    configuration = resource_of(ledger, ctx)
    command = 'cd ' + shlex.quote(PROJECT_DIRECTORY) + ' && ' + arguments['command']

    async def observe():
        resource = resource_identity(ledger.commission['resource_id'], configuration)
        cache_key = resource + ':' + digest(command)
        if memory_enabled(ctx):
            cached = estimate_latest(ctx, cache_key, 'inventory')
            if cached['state'] == 'fresh':
                return cached['data']
        value = await run_command(configuration, command, ctx.operation_key, ctx)
        if memory_enabled(ctx) and value['returncode'] == 0:
            estimate_observe(ctx, cache_key, 'inventory', value, observed_at=value['observed_at'],
                             provenance=[ledger.ledger, 'discovery:' + ctx.operation_key])
        return value
    result = await once(ledger, 'discovery:' + ctx.operation_key, 'discovery', observe)
    return completed(ledger, ctx, result)


def hpc_candidate_propose(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    commission = ledger.commission
    try:
        candidate = json.loads(arguments['candidate_json'])
        candidates = candidates_of(ledger)
        prior = next((row for row in candidates if row['id'] == candidate['id']), None)
        if prior is not None and prior != candidate:
            raise ValueError('candidate_identity_is_immutable')
        validate_commission({**commission, 'candidates': candidates if prior else candidates + [candidate]},
                            ctx.settings['resources'])
    except (ValueError, KeyError, TypeError) as error:
        return invalid(ledger, ctx, argument_error(str(error)))
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates']
                 else ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return completed(ledger, ctx, {'candidate_ref': reference, 'candidate_id': candidate['id']})


async def hpc_queue_observe(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    reference = 'queue:' + digest(ctx.operation_key)
    value = await once(ledger, reference, 'queue', lambda: observe_queue(ledger, ctx, ctx.operation_key))
    result = {'queue_ref': reference,
              'features': [hpc_queue.features(value['snapshot'], candidate) for candidate in candidates_of(ledger)],
              'snapshot': value['snapshot']}
    return completed(ledger, ctx, result)


def hpc_plan(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    commission = ledger.commission
    configuration = resource_of(ledger, ctx)
    existing = ledger.records('plan')
    own = next((row for row in existing if row['body'].get('operation_key') == ctx.operation_key), None)
    if own is not None:
        plan = own['body']
        forecast_ref = freeze_forecast(ledger, plan, plan['original_prediction'], plan['original_reference'], {},
                                       'planned', ctx.operation_key)
        plan_ref = own['id']
    else:
        observed = queue_snapshot(ledger, arguments['queue_ref'], require_fresh=True)
        candidate = next((row for row in candidates_of(ledger) if row['id'] == arguments['candidate_id']), None)
        if candidate is None:
            return invalid(ledger, ctx, argument_error('unknown_candidate:' + arguments['candidate_id']))
        queue = hpc_queue.features(observed, candidate)
        rules = queue['queue_rules']
        if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
            raise ValueError('choose_an_observed_enabled_execution_queue')
        for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
            if (rules['min_' + key] is not None and value < rules['min_' + key]
                    or rules['max_' + key] is not None and value > rules['max_' + key]):
                raise ValueError('candidate_violates_observed_queue_limits')
        plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
        features = candidate_features(candidate, queue)
        predicted = prediction.predict(ledger.read(arguments['model_ref']), features)
        reference = prediction.predict(ledger.read('reference_model'), features)
        plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'],
                    original_prediction=predicted, original_reference=reference, operation_key=ctx.operation_key)
        choices = [row['body'] for row in ledger.records('model_choice')
                   if row['body']['model_ref'] == arguments['model_ref']]
        plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
        plan_ref = ledger.put('plan', plan)
        forecast_ref = freeze_forecast(ledger, plan, predicted, reference, {}, 'planned', ctx.operation_key)
    # The frozen plan is supplied to the launch child as a held input artifact (the old local input file of the first
    # decision of the launch), named by the ledger.
    artifact = ctx.store.artifact(canonical(plan), 'application/json')
    ledger.put('launch_input', {'plan_id': plan['plan_id'], 'artifact_ref': artifact}, source_refs=[artifact])
    result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref,
              **{key: value for key, value in plan.items() if key != 'prediction_episode_id'},
              'supplied_input_artifact_ref': artifact}
    return completed(ledger, ctx, result)


async def hpc_handoff(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    commission = ledger.commission
    plan = ledger.read(arguments['plan_ref'])
    if not ctx.store.holds(arguments['handoff_ref']):
        return invalid(ledger, ctx, argument_error('handoff_not_received'))
    target = handoff_target(ctx.store, arguments['handoff_ref'])
    if target['assignment'] != plan['practical_assignment']:
        return invalid(ledger, ctx, argument_error('handoff_does_not_match_frozen_portfolio'))
    ledger.put('handoff', {'handoff_ref': arguments['handoff_ref'], 'job_id': target['execution_id'],
                           'plan_id': plan['plan_id']}, identity='handoff:' + plan['plan_id'])
    result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
    if 'monitoring' in commission:
        result['monitor_controller_ref'] = monitor_attach(ledger, plan, target['execution_id'],
                                                          commission['monitoring'])
    return completed(ledger, ctx, result)


async def hpc_monitor(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(arguments, ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    observed = await observe_allocation(ctx, ledger, plan, target, candidate, ctx.operation_key)
    result = await update_conditional_forecast(arguments, ctx, ledger, plan, target, candidate, observed,
                                               ctx.operation_key)
    return completed(ledger, ctx, result)


async def hpc_monitor_wait(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(arguments, ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    key = ctx.operation_key
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor_controller')):
        return invalid(ledger, ctx, argument_error(
            'hpc_monitor_controller_not_attached',
            next_step='This original commission has no attached monitor controller. Use hpc_monitor on the '
                      'original plan, then hpc_results when its outputs are ready. Retain the original '
                      'submitted job; do not launch replacement work.'))

    async def monitor_once(monitor_key):
        observed = await observe_allocation(ctx, ledger, plan, target, candidate, monitor_key)
        return await update_conditional_forecast({'refresh_queue': True}, ctx, ledger, plan, target, candidate,
                                                 observed, monitor_key)
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor')):
        await monitor_once(key + ':initial-monitor')
    monitor = last_forecast(ledger, plan)
    ready = uncollected_completed_unit_ids(ledger, plan, monitor['conditional_prediction'])
    if monitor['conditional_prediction']['telemetry']['state'] in ('complete', 'failed'):
        result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_terminal_job_collect_now'}
    elif ready:
        result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_unit_outputs_collect_now',
                  'ready_unit_ids': sorted(ready)}
    else:
        schedule = monitor_reserve(ledger, plan, candidate, monitor, key)
        if schedule['job_id'] != target['execution_id']:
            raise ValueError('monitor_schedule_original_job_conflict')
        if schedule['valuation']['schedule']:
            await monitor_wait(ledger, schedule)
            observed = await monitor_once(key + ':monitor')
            ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'], 'job_id': target['execution_id'],
                                        'observed': {'status': 'completed', 'result': observed}},
                       identity='wake:' + key)
            result = {'schedule': schedule, 'monitor': observed}
        else:
            result = {'schedule': schedule, 'monitor': None}
    return completed(ledger, ctx, result)


async def hpc_results(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(arguments, ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    observed = await observe_allocation(ctx, ledger, plan, target, candidate, ctx.operation_key)
    result, references = await collect_original_results(arguments, ctx, ledger, plan, target, candidate, observed,
                                                        ctx.operation_key)
    return completed(ledger, ctx, result, references)


async def hpc_allocation_order(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(arguments, ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    allowed = {unit['unit_id'] for unit in candidate['units']}
    if not set(arguments['unit_ids']) <= allowed:
        return invalid(ledger, ctx, argument_error('only_original_work_units_can_be_selected'))
    result = await write_allocation_control(target, arguments['unit_ids'], ctx.operation_key, ctx)
    ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': ctx.operation_key,
                                    'unit_ids': arguments['unit_ids'], 'receipt': result})
    return completed(ledger, ctx, result)


TOOLS = {'hpc_read': hpc_read, 'hpc_compare': hpc_compare, 'hpc_history_refresh': hpc_history_refresh,
         'hpc_discovery_run': hpc_discovery_run, 'hpc_candidate_propose': hpc_candidate_propose,
         'hpc_queue_observe': hpc_queue_observe, 'hpc_plan': hpc_plan, 'hpc_handoff': hpc_handoff,
         'hpc_monitor': hpc_monitor, 'hpc_monitor_wait': hpc_monitor_wait, 'hpc_results': hpc_results,
         'hpc_allocation_order': hpc_allocation_order}


# -------------------------------------------------------------------------------------- deciding and choosing

def offered(ctx):
    """The actions this decision offers: every tool (the history refresh only with the shared memory) and the
    three child commissions."""
    names = [name for name in TOOL_CATALOG if name != 'hpc_history_refresh' or memory_enabled(ctx)]
    return names + list(CHILD_CATALOG)


def argument_schema(name):
    return (TOOL_CATALOG[name] if name in TOOL_CATALOG else CHILD_CATALOG[name])[1]


def output_schema(names):
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection', 'arguments_json'],
            'properties': {'selection': {'type': 'string', 'enum': list(names),
                                         'description': 'The one action of this decision.'},
                           'arguments_json': {'type': 'string',
                                              'description': 'The arguments of the action as a JSON object text.'}}}


def owner_arguments(summary, arguments):
    """The arguments of a tool: the model's, and what the commission fixes (the owner, its scope and commission)."""
    return {**arguments, 'owner_episode_id': summary['owner_episode_id'],
            'commission_identity': summary['commission_identity'], 'scope': summary['scope'], 'ledger': summary['ledger']}


def decide(summary, feedback, ctx):
    view = summary['ledger_view']
    if view is None:
        # The first part of the task: the owner commission, read through the episode's own tool.
        return ToolCall('hpc_read', owner_arguments(summary, {'reference': 'commission'}))
    settings = ctx.settings
    names = offered(ctx)
    commission = view['commission']
    context = {
        'hpc_commission': commission, 'hpc_owner_episode_id': view['owner_episode_id'],
        'hpc_candidates': view['candidates'], 'hpc_resource': settings['resources'][commission['resource_id']],
        'hpc_child_scope': summary['scope'], 'hpc_child_commission': summary['commission_identity'],
        'hpc_launches': summary['launches'], 'hpc_tool_request': view['tool_requests'],
        'hpc_model_ref': view['model_ref'], 'hpc_credit': view['credit'],
        'hpc_latest_comparison': view['latest_comparison'], 'hpc_model_support': view['model_support'],
        'hpc_plans': [{'plan_ref': plan['plan_ref'], 'candidate_id': plan['candidate_id']}
                      for plan in view['plans']],
        'hpc_latest_monitor': view['latest_monitor'], 'hpc_monitor_controllers': view['monitor_controllers'],
        'hpc_queue_refs': view['queue_refs'], 'hpc_available_training_ids': view['available_training_ids'],
        'requested_action_history': summary['actions'], 'feedback': feedback,
        'time_accounting': time_accounting(ctx.clock.progress_time),
        # BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: the read below. No such service exists.
        'resource_tool_estimates': ctx.services['estimate_table'].read('resource_tool_estimates', 'hpc_execution'),
        'actions': [{'selection': name, 'description': (TOOL_CATALOG.get(name) or CHILD_CATALOG[name])[0],
                     'input_schema': argument_schema(name)} for name in names]}
    if memory_enabled(ctx):
        context['hpc_shared_history_refs'] = view['shared_history_refs']
    instructions = INSTRUCTIONS
    library = settings.get('launch_instruction_directory')
    if library is not None:
        context['launch_instruction_library'] = LaunchInstructions(library).context()
        instructions += LAUNCH_INSTRUCTIONS
    knowledge = settings.get('tool_knowledge_directory')
    if knowledge is not None:
        context['tool_knowledge'] = ToolKnowledge(knowledge).context()
        instructions += KNOWLEDGE_INSTRUCTIONS
    if summary['action_yields'] is not None:
        context['action_yields'] = summary['action_yields']
    return ModelRequest(MODEL_ROLE, instructions, context, output_schema(names))


def action(response, summary, records, ctx):
    """Admit the model's selection. An invalid answer creates no unit: the model decides again with the feedback.
    A tool is called with its arguments and what the commission fixes; a commission is called with the model's
    arguments and the credit units of its child from the settings."""
    names = offered(ctx)
    try:
        Draft202012Validator(output_schema(names)).validate(response)
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_encode_an_object')
        Draft202012Validator(argument_schema(response['selection'])).validate(arguments)
        selection = response['selection']
        plans = {plan['plan_ref']: plan for plan in summary['ledger_view']['plans']}
        if 'plan_ref' in arguments and arguments['plan_ref'] not in plans:
            raise ValueError('unknown_plan_ref:' + arguments['plan_ref'])
        if selection == 'launch':
            plan = plans[arguments['plan_ref']]
            if plan['closed']:
                raise ValueError('hpc_allocation_already_closed')
            if any(item['plan_ref'] == arguments['plan_ref'] for item in summary['launches']):
                raise ValueError('hpc_plan_already_launched_once')
        named = [arguments['handoff_ref']] if 'handoff_ref' in arguments else []
        for reference in named:
            if not records.holds(reference):
                raise ValueError('record_not_held:' + reference)
    except (ValidationError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selection in TOOLS:
        return ToolCall(selection, owner_arguments(summary, arguments))
    units = {'launch': ('handoff_unit', 'acquired_record_unit'), 'monitor': ('information_unit',),
             'results': ('acquired_record_unit',)}[selection]
    return ChildCall(selection, {**arguments, **{unit: ctx.settings[unit] for unit in units}})
