"""The task: bring one HPC commission to completion by commissioning the prediction and the allocation-execution
sisters over the commission's HPC ledger, or by a single planning action of its own; one action per unit.

Carried from the old ``work_operations.py`` (``catalog``, ``execute``), ``portfolio_state.py``,
``received_evidence.py``, ``measured_history.py``, ``portfolio_candidates.py``, ``portfolio_comparison.py``,
``portfolio_planning.py``, ``queue_observations.py``, ``resource_discovery.py``, ``allocation_handoff.py``,
``allocation_observations.py``, ``forecast_observations.py``, ``allocation_results.py``, ``allocation_order.py``,
``waiting.py`` (the tool ``hpc.monitor.wait``), ``task.py``, ``task_instructions.py``, ``task_decision.py``,
``decision_inputs.py``, ``configuration.py`` and the instruction text of ``goal.py`` (all at ``97308b94c``, this
episode's own files). One unit is one model-selected action: a tool call (the twelve old HPC tools) or the
commission of the ``hpc_prediction``, ``hpc_execution``, ``launch``, ``monitor`` or ``results`` child. The task
always offers a unit and never ends the Episode: only the yield controller does. The old ``wait`` and
``redeliver_report`` actions, the decision exchange and the report-repair instruction text are not carried.

**The ledger** is the work table ``HPC_LEDGER`` in custody (``episode_support/jobs/hpc_ledger.py``), and this
episode owns it. ``hpc_open`` (the first unit: ``decide`` issues it, the model is not offered it) opens the ledger
of the assignment's commission with ``HpcLedger.open(ctx.store, commission)`` and records the owner; rows an
earlier episode of this commission wrote and the commissioner passed (``received_record_refs``) are found under
it. Every later tool is handed the ledger id in its arguments and reads the held rows with
``HpcLedger.existing(ctx.store, ledger)``. A sister is commissioned with the ledger id and the ledger's rows
(``ledger_row_refs``); the rows it wrote come back in ``hpc_ledger_refs`` of its return and are held from then on.
``internal_summary`` reads the ledger through ``view.records`` at every decision, so a sister's work is in the
credit of the unit that commissioned it and in the next decision's view: nothing is read again and nothing is
stale. A frozen plan's launch input is an artifact the ledger names (the row ``launch_input:<plan_id>``), passed
to the launch child in custody: there is no directory and no local file.

**The prompt** is ``INSTRUCTIONS`` (what the episode is for, what the model is shown, how to work, what earns
credit) and the descriptions of ``TOOL_CATALOG`` and ``CHILD_CATALOG``; ``decide`` shows the commission, the
resource, the ledger, what the sisters and the job children returned, the credit and the episode's own units, and
nothing of the yield controller or the progress clock.

Tool names are ``[a-z][a-z0-9_]*``: ``hpc.read`` is ``hpc_read``, ``hpc.monitor.wait`` is ``hpc_monitor_wait``, and
so on. A tool returns a failure of the model's arguments as an outcome (``status`` ``invalid``), a request the
resource did not answer as an outcome (``status`` ``failed``), and raises for a broken ledger or receipt.

**The resource** is reached only through the run's ``job_access`` service: ``hpc_remote.command``, ``read_file``
and ``write_file`` (one login-mode command on the route bound to the commission's resource id),
``hpc_queue.observe``, and for a handed-off job ``hpc_remote.handoff_target`` (the held ``JOB_LEDGER`` handoff row
the launch child returned) and ``job_status`` (one status request, written as the job's check row). **The shared
timing memory** is the ``estimate_table`` service (``latest``, ``observe``, ``history``, ``policy``, ``record``,
and ``profiles`` for the decision), used when the setting ``shared_execution_memory`` is true.

Settings this episode reads (``ctx.settings``): ``resources`` (the configured resources by id; the commission's is
a ``pbs_ssh`` resource with its ``account``, ``workspace`` and ``python_executable``), ``commissions`` (the
configured commissions by id, for ``commission_id``), ``shared_execution_memory`` (boolean), ``handoff_unit``,
``information_unit`` and ``acquired_record_unit`` (the credits one received handoff, one informative progress
snapshot and one acquired selector earn in the three job children; they ride in the child commissions) and the
yield settings ``cost`` and ``parameters`` (``yield_estimator.py``)."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import shlex
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.execution_contracts import (
    obj)
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.execution_guidance import (
    resource_identity)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue, hpc_remote
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import canonical, digest
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence import (
    hpc_commission_sources, hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_campaign import (
    accepts, bind_progress, build_plan, incorporate_progress, telemetry, validate_commission)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_history import (
    closed_measurement)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HpcLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_monitoring import (
    MonitorCronController)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_resource_prediction import (
    forecast_metric, measured_value, pbs_resource_metrics, physical_attempt_key)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    RECORD_SCHEMAS)

_PREFIX = 'partner_presence_evidence/hpc_work_planning/'
CHILD_SLOTS = {'launch': _PREFIX + 'execution_job_submission',
               'monitor': _PREFIX + 'execution_progress_assessment',
               'results': _PREFIX + 'execution_result_acquisition',
               'hpc_execution': _PREFIX + 'hpc_allocation_execution',
               'hpc_prediction': _PREFIX + 'hpc_resource_prediction'}
SERVICES = ('job_access', 'estimate_table')
MODEL_ROLE = 'REASONING'
PROJECT_DIRECTORY = '/lus/flare/projects/BioReason-Aurora-Test'
MONITOR_FIELD_OPTIONS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
                         'result_available')
# The selectable return fields each child declares that this episode asks for (the parent selects). A sister's
# credit, finding and ledger rows are required fields of its return and cannot be selected.
LAUNCH_SELECTION = ('execution_handoff_refs', 'execution_completed')
MONITOR_SELECTION = ('monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available',
                     'monitoring_observed_at_unix_seconds', 'monitoring_committed_record_refs',
                     'monitoring_progress_snapshots')
RESULTS_SELECTION = ('execution_result_refs', 'execution_result_artifact_refs', 'execution_completed')
PREDICTION_SELECTION = ()
EXECUTION_SELECTION = ('hpc_result_refs', 'hpc_result_artifact_refs')
# The keys the action adds to every tool's arguments: they come from the commission, not from the model.
INJECTED = ('ledger', 'commission_id', 'commission_source_ref', 'tool_request', 'scope')

INSTRUCTIONS = (
    'You are the HPC planning episode of one commission and the owner of its HPC ledger. Your job is to bring the '
    'commissioned computation to completion on the HPC resource by commissioning two sister episodes that work '
    'over the ledger: hpc_prediction, which predicts the time and resources the work needs and records that '
    'expectation in the ledger (a fitted model and a comparison of the candidate portfolios), and hpc_execution, '
    'which plans the allocation from the ledger, has the plan launched, observes the job and parses and accepts '
    'its results. You may also take a single planning step yourself with a tool. Iterate toward the original '
    'accomplishment while balancing expected credit against real elapsed time and resource demand.\n\n'
    'What you are shown. commission: the work, its obligations with their credit and acceptance predicates, the '
    'cost preferences and limits. resource: the configured HPC resource. ledger: what the HPC ledger of this '
    'commission holds now: the current resource model and its support, how many measured cases there are to fit '
    'and validate on, the candidate portfolios, the queue observations, the latest comparison, the frozen plans '
    'with whether each is handed off and closed, the latest monitor and the monitor controllers. Both sisters '
    'work on this ledger; what a sister records is in it as soon as the sister returns. predictions and '
    'executions: what each sister commission returned, its credit and its counts. launches, monitors and '
    'acquisitions: what the job children you commissioned yourself returned. credit: what this episode has earned so '
    'far, and the ledger\'s credit by component. '
    'units_so_far and last_outcome: what you already did and what the last action returned. actions: '
    'every action you can select now, with its argument schema.\n\n'
    'How to work. Each decision selects exactly one action; it runs as one unit. Commission hpc_prediction when '
    'model improvement warrants its own iteration: when the model is prior-only or there are measured cases it '
    'was not fitted on, a prediction iteration improves the sizing before anything is launched. No historical '
    'validation support means no invented model-improvement credit. Commission hpc_execution to plan the '
    'allocation from the ledger and carry the plan through. A sister\'s credit, and the trend of its credit over '
    'your commissions of it, say whether it was productive: do not commission again a sister that has just '
    'returned no credit unless the ledger has changed so that it has new work. The tools are the single steps of '
    'the same work, for a step you take yourself: hpc_queue_observe, hpc_compare, hpc_plan (a plan freezes its '
    'original forecast, scientific manifest and acceptance criteria), launch (a plan is launched once and a '
    'launch must not be commissioned again for the same plan), hpc_handoff, hpc_monitor when another observation '
    'can affect your decision, and hpc_results (completion is not acceptance). Queue and setup costs belong to an '
    'allocation, which should carry enough useful work. When candidates are absent, discover the remote '
    'environment and documentation with hpc_discovery_run, then design candidate portfolios with '
    'hpc_candidate_propose. Every work unit of a candidate writes result.json and progress.json under '
    'os.environ["HPC_UNIT_DIRECTORY"]; the fields of result.json must satisfy the acceptance predicates. '
    'Candidate files use relative paths; {allocation_workspace} expands in files, argv, environment and '
    'preparation. Compute commands must run on allocated compute nodes using the facility launcher. When the '
    'ledger shows a monitor controller for a plan, select hpc_monitor_wait for a scheduled observation, without '
    'credit for sleeping. Commission the monitor and results children only for actual investigation. Never '
    'fabricate inputs or receipts, never duplicate a submitted attempt and never replace an uncertain submission. '
    'When an action or a sister reports that the resource could not be reached, do not repeat it: without a '
    'queue observation no plan can be frozen, and nothing may be invented in its place.\n\n'
    'What earns credit. The ledger\'s credit has three components and no other: accepted accomplishment (an '
    'obligation whose unit completed with return code 0 and whose result satisfies its acceptance predicate earns '
    'the obligation\'s credit, once), model improvement (the measured held-out improvement of the model the '
    'prediction sister fits), and fixed prospective forecast validation (a forecast frozen at planning is scored '
    'against the measured outcome; signed). A commission earns what the sister\'s work adds to the ledger; '
    'launch-local credits are not added again. Observing, comparing, planning, launching, waiting and polling '
    'earn nothing by themselves: do not poll for credit. You do not end the episode: it ends by itself when '
    'further units stop earning.\n\n'
    'Answer with one selection from actions and its arguments as JSON object text in arguments_json.')

LAUNCH_JOB_INSTRUCTIONS = (
    'The supplied launch input (a record passed with this commission) contains the frozen scientific manifest and '
    'reference source files. Choose your scripts, environment and transfer method. Do not transcribe supplied '
    'source code into a child goal. Reference implementation files are available inputs, not a required execution '
    'procedure. Preserve original unit identities, scientific inputs, output/progress formats and acceptance '
    'predicates. Run computation in the actual allocation and retain its original identity. An uncertain '
    'submission must be investigated rather than duplicated.')

_TEXT = {'type': 'string', 'minLength': 1}
_STRINGS = {'type': 'array', 'uniqueItems': True, 'items': _TEXT}

# The tools the model may select (the old ``HPCWorkOperations.catalog``), each with what it records in the ledger.
TOOL_CATALOG = {
    'hpc_queue_observe': ('Observe the scheduler queue and the facility status once on the resource and record the '
                          'observation in the ledger (a queue_ref). hpc_compare and hpc_plan need one; hpc_plan '
                          'needs it fresh.', obj({})),
    'hpc_compare': ('Forecast every candidate portfolio under one model and one queue observation and record the '
                    'comparison in the ledger: predicted times, success probability, expected credit and net '
                    'expected value per candidate. model_ref is one of the ledger\'s model_refs, queue_ref one of '
                    'its queue_refs. No work is selected or launched.',
                    obj({'model_ref': _TEXT, 'queue_ref': _TEXT})),
    'hpc_plan': ('Freeze one candidate portfolio as a plan in the ledger, with its forecast under model_ref and the '
                 'fresh queue observation queue_ref, its scientific manifest and its launch assignment. The queue '
                 'of the candidate must be an enabled, started execution queue and the candidate within its node '
                 'and walltime limits. Returns the plan_ref to launch.',
                 obj({'candidate_id': _TEXT, 'model_ref': _TEXT, 'queue_ref': _TEXT})),
    'hpc_handoff': ('Attach the handoff the launch of a plan returned (a handoff_ref of launches) to that plan in '
                    'the ledger, so that the original job can be monitored and its results parsed.',
                    obj({'plan_ref': _TEXT, 'handoff_ref': _TEXT})),
    'hpc_monitor': ('Observe the original job of a handed-off plan and its progress once; record the measurement, '
                    'score the frozen forecasts it settles, and update and freeze the conditional forecast. '
                    'refresh_queue also takes a new queue observation.',
                    obj({'plan_ref': _TEXT, 'refresh_queue': {'type': 'boolean'}})),
    'hpc_monitor_wait': ('Use the monitor controller attached to a plan: it values a later observation from the '
                         'conditional forecast, waits until its wake time and then observes this original job '
                         'exactly once. No earned credit for waiting.', obj({'plan_ref': _TEXT})),
    'hpc_results': ('Parse the compact results of the original allocation of a handed-off plan, publish each as a '
                    'source record and apply the commission\'s acceptance predicates: an accepted obligation earns '
                    'its credit.', obj({'plan_ref': _TEXT})),
    'hpc_allocation_order': ('Reorder the pending units of a running allocation at the next unit boundary, '
                             'retaining all unstarted work.', obj({'plan_ref': _TEXT, 'unit_ids': _STRINGS})),
    'hpc_candidate_propose': (
        'Record an executable portfolio in the ledger. candidate_json is JSON with id, queue, nodes, '
        'wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), '
        'optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units '
        '(unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: '
        'relative path, text: exact contents}], and preparation instructions for Launch. effort is a positive '
        'finite number expressing relative work, for example 1.0; workload sizes belong in features. No per-unit '
        'execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate identities '
        'are immutable.', obj({'candidate_json': _TEXT})),
    'hpc_discovery_run': ('Run one read-only shell command on the login node of the resource, in the project '
                          'directory, and record its output in the ledger: a lightweight inspection or a '
                          'documentation lookup. No job submission, installation or scientific computation; '
                          'those belong to the launch and the allocation.', obj({'command': _TEXT})),
    'hpc_read': ('Read one record of the ledger by its exact identity: a model_ref, a queue_ref, a plan_ref, a '
                 'comparison_ref, a result source, or commission.', obj({'reference': _TEXT})),
    'hpc_history_refresh': ('Read the shared timing history of earlier runs once and record it in the ledger. No '
                            'remote discovery, polling credit, or new scientific work.', obj({})),
}
# The children the model may commission (the old child roles ``hpc_prediction``, ``hpc_execution``, ``launch``,
# ``monitor`` and ``results``). The commission is built in ``messages/msg_to_child.py`` from these arguments and
# the summary.
CHILD_CATALOG = {
    'hpc_prediction': ('Commission the resource-prediction sister over this ledger: it fits the time/resource '
                       'model on the measured cases, measures its held-out quality and compares the candidate '
                       'portfolios, and returns what it recorded. It earns the measured model improvement.',
                       obj({})),
    'hpc_execution': ('Commission the allocation-execution sister over this ledger: it plans the allocation from '
                      'the ledger (queue observation, comparison, frozen plan), has the plan launched, observes '
                      'the job and parses and accepts its results, and returns what it recorded. It earns the '
                      'accepted accomplishment and the forecast validation.', obj({})),
    'launch': ('Commission the launch child to submit one frozen plan on its resource; it returns the handoff '
               'reference of the submitted job. Launched once per plan. launch_instructions is the selection of '
               'launch instruction sections for this launch, when you have one.',
               obj({'plan_ref': _TEXT, 'launch_instructions': {'type': 'object'}}, required=['plan_ref'])),
    'monitor': ('Commission the monitor child to report the state of one execution target (a handoff handle). For '
                'actual investigation only: hpc_monitor is the ordinary observation.',
                obj({'target_handle': _TEXT,
                     'requested_fields': {'type': 'array', 'uniqueItems': True,
                                          'items': {'type': 'string', 'enum': list(MONITOR_FIELD_OPTIONS)}},
                     'known_progress_refs': {'type': 'array', 'items': _TEXT},
                     'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                                          'items': {'type': 'string',
                                                                    'enum': sorted(RECORD_SCHEMAS)}}},
                    required=['target_handle', 'requested_fields', 'permitted_committed_record_types'])),
    'results': ('Commission the result-acquisition child to investigate result files of a received handoff. For '
                'actual investigation only: known parsing is done directly with hpc_results.',
                obj({'handoff_ref': _TEXT, 'selector': {'type': 'object'}, 'constraints': {'type': 'object'}},
                    required=['handoff_ref', 'selector'])),
}

# ------------------------------------------------------------------------------------------- the ledger's state

class ResourceRequestFailed(Exception):
    """A request the resource did not answer (``failure`` is ``{'code', 'detail'}``, as ``hpc_remote`` returned
    it). The tool that made the request returns it as a failed unit."""

    def __init__(self, failure):
        super().__init__(failure['code'])
        self.failure = failure


def answered(reply):
    """``reply`` of a request to the resource when it was answered; ``ResourceRequestFailed`` otherwise."""
    if reply['status'] != 'completed':
        raise ResourceRequestFailed(reply['failure'])
    return reply


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
    """The artifact that holds the frozen plan for its launch: the ledger names it (``hpc_plan`` wrote it)."""
    return ledger.read('launch_input:' + plan_id)['artifact_ref']


def ledger_view(ledger):
    """What the ledger of the commission shows now, from the rows this Episode holds: for the model's next decision
    (``internal_summary`` reads it through ``view.records`` and arranges it), for the commissions (``plans`` with
    their launch assignment, manifest and launch input; ``ledger_refs`` to pass a sister), for the credit
    (``credit``) and for the return (``ledger_refs``: every held row and the records they name)."""
    commission = ledger.commission
    model_ref = current_model(ledger)
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    handed_off = {row['body']['plan_id'] for row in ledger.records('handoff')}
    plans = [{'plan_ref': row['id'], 'plan_id': row['body']['plan_id'], 'candidate_id': row['body']['candidate_id'],
              'handed_off': row['body']['plan_id'] in handed_off, 'closed': row['body']['plan_id'] in closed,
              'launch_assignment': row['body']['launch_assignment'], 'manifest': row['body']['manifest'],
              'launch_input_ref': launch_input_ref(ledger, row['body']['plan_id'])}
             for row in ledger.records('plan')]
    cases = measured_history(ledger)
    return {'ledger_id': ledger.ledger, 'ledger_refs': ledger.refs(), 'credit': ledger.credit_view(),
            'owner_episode_id': ledger.read('owner')['episode_id'],
            'commission': {name: commission[name] for name in ('objective', 'resource_id', 'obligations',
                                                                 'preferences', 'limits', 'credit')},
            'measured_cases': {'validation': len(commission['validation_ids']),
                               'training': len(set(cases) - set(commission['validation_ids']))},
            'candidates': candidates_of(ledger), 'model_ref': model_ref,
            'model_refs': [row['id'] for row in ledger.records('model')],
            'model_support': prediction.predict(ledger.read(model_ref), {})['support'],
            'tool_requests': [row['body'] for row in ledger.records('tool_request')],
            'comparison_refs': [row['id'] for row in ledger.records('comparison')],
            'latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                   if key not in ('episode_id', 'operation_key')}}
                                  for row in ledger.records('comparison')[-1:]],
            'plans': plans, 'latest_monitor': ledger.records('monitor')[-1:],
            'monitor_controllers': ledger.records('monitor_controller'),
            'queue_refs': [row['id'] for row in ledger.records('queue')],
            'result_source_refs': [row['body']['source_ref'] for row in ledger.records('result')],
            'shared_history_refs': [row['id'] for row in ledger.records('shared_history')]}


def completed(result, references=(), artifacts=()):
    return {'status': 'completed', 'record_refs': list(references), 'artifact_refs': list(artifacts),
            'result': result, 'feedback': None}


def invalid(feedback):
    return {'status': 'invalid', 'record_refs': [], 'artifact_refs': [], 'result': None, 'feedback': feedback}


def failed(failure):
    """A request the resource did not answer: an outcome of the unit, with the route's own failure."""
    return {'status': 'failed', 'record_refs': [], 'artifact_refs': [], 'result': None,
            'feedback': {'category': 'resource_request', **failure}}


def argument_error(code, **more):
    return {'category': 'arguments_or_reference', 'code': code, **more}


def shared_history(ledger, ctx):
    """The shared timing history for this resource (the old ``_shared_history``), from the estimate table."""
    commission = ledger.commission
    memory = ctx.services['estimate_table']
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], resource_of(ledger, ctx))
    # Queue timing is resource-wide. Work timing requires explicit matching algorithm, parameters, software and
    # hardware, never just 'Aurora'.
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
    return {'captured_at': now, 'policy': memory.policy(),
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts]}


def recorded(ledger, identity, kind, value):
    """Keep ``value`` as the evidence ``identity`` of this unit."""
    ledger.put(kind, value, identity=identity)
    return value


def commission_identity(arguments):
    return {name: arguments[name] for name in ('commission_id', 'commission_source_ref')
            if arguments.get(name) is not None}


def commission_of(arguments, ctx):
    """The commission of the assignment (the old ``HPCAssignment._commission``): a configured commission by id, or a
    host grant read from a held Store source."""
    resources = plain(ctx.settings['resources'])
    if arguments.get('commission_source_ref') is not None:
        return hpc_commission_sources.read(ctx.store, arguments['commission_source_ref'],
                                           scope=plain(arguments['scope']), resources=resources)
    return validate_commission(plain(ctx.settings['commissions'][arguments['commission_id']]), resources)


def tool_request_record(request):
    """What the ledger keeps of the commissioner's tool request (the old ``HPCAssignment._tool_request``): the
    requested tool, its arguments, the tool that reads the result and the rule for carrying it out. The tool's
    contract is the commissioner's: it knows what it asks for."""
    return {'objective': request['objective'], 'tool': {'name': request['name'], 'resources': request['resources']},
            'arguments': json.loads(request['arguments_json']), 'result_reader': request['result_reader'],
            'execution_rule': 'Implement this exact requested computation through the HPC template. '
                              'The declared resources describe the original callable; they do not grant a remote '
                              'adapter. Establish the software, staged operands and owning result reader before '
                              'launch. Return complete original artifacts for that reader; do not replace '
                              'scientific grading with the allocation acceptance score.'}


def open_ledger(arguments, ctx):
    """The ledger of this episode as it holds it now (its own rows, the rows its sisters returned and the rows it
    was passed), for a tool after ``hpc_open``."""
    return HpcLedger.existing(ctx.store, arguments['ledger'])


def create_ledger(arguments, ctx):
    """Open the ledger of the commission and put in place what it needs once: the owner (this Episode, unless an
    earlier episode of the commission already owns the passed rows), the commissioner's tool request and the
    reference model (the old ``state`` and ``initialize``)."""
    ledger = HpcLedger.open(ctx.store, commission_of(arguments, ctx))
    if not ledger.records('owner'):
        ledger.put('owner', {'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
                             'scope': plain(arguments['scope']), **commission_identity(arguments)},
                   identity='owner')
    if arguments['tool_request'] is not None and not ledger.records('tool_request'):
        ledger.put('tool_request', tool_request_record(plain(arguments['tool_request'])), identity='tool_request')
    if not ledger.records('model'):
        ledger.put('model', prediction.prior_model(ledger.commission['model']), identity='reference_model')
        if memory_enabled(ctx):
            imported = recorded(ledger, 'shared_history_entry', 'shared_history', shared_history(ledger, ctx))
            if imported['observations']:
                model = prediction.fit(ledger.commission['model'], imported['observations'])
                reference = ledger.put('model', model)
                ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                           identity='shared_history_initial_model')
    return ledger


def queue_snapshot(ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time() - observation['captured_at'] > ledger.commission['limits'][
            'queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation


async def observe_queue(ledger, ctx, name):
    """One queue observation ``{'snapshot', 'acquisition'}``: the shared memory's while it is fresh (the old
    ``_observe_queue``), else one acquisition on the resource through the run's job access."""
    configuration = resource_of(ledger, ctx)
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if memory_enabled(ctx):
        cached = ctx.services['estimate_table'].latest(resource, 'queue')
        if cached['state'] == 'fresh' and cached['age_seconds'] <= ledger.commission['limits'][
                'queue_max_age_seconds']:
            return cached['data']
    acquired = answered(await hpc_queue.observe(ctx, ledger.commission['resource_id'], name=name))
    value = {'snapshot': acquired['snapshot'], 'acquisition': acquired['acquisition']}
    if memory_enabled(ctx):
        ctx.services['estimate_table'].observe(resource, 'queue', value,
                                               observed_at=value['snapshot']['captured_at'],
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
    body = recorded(ledger, 'issued:' + key, 'forecast_issue', {
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
    if current['started_at'] is not None:
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
    measured = recorded(ledger, 'export_measurement:' + plan['plan_id'], 'export_measurement', [
        row for row in ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
    handoff = ledger.read('handoff:' + plan['plan_id'])
    ctx.services['estimate_table'].record(**closed_measurement(
        ledger.commission, plan, measured, handoff, resources=ctx.settings['resources'], ledger=ledger.ledger))


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

def original_target(ctx, ledger, plan):
    """The handed-off job of ``plan`` (the old ``_target``): the held handoff row the ledger attached to it."""
    return hpc_remote.handoff_target(ctx.store, ledger.read('handoff:' + plan['plan_id'])['handoff_ref'])


async def allocation_receipt(ctx, target, plan, name):
    """The allocation's own status file, or ``[None, why]`` while the runner has not written a readable one."""
    path = plan['manifest']['workspace'] + '/allocation-status.json'
    limit = 512 * 1024
    read = await hpc_remote.read_file(ctx, target['resource_id'], path, limit, name=name)
    if read['status'] != 'completed' and read['failure']['code'] != 'remote_file_unreadable':
        raise ResourceRequestFailed(read['failure'])
    if read['status'] != 'completed' or read['size_bytes'] > limit:
        # Absence before the runner starts is normal; it does not manufacture a progress estimate.
        return [None, {'path': path, 'failure': 'allocation_status_not_readable'}]
    value = json.loads(base64.b64decode(read['bytes_base64'], validate=True))
    if (value['plan_id'] != plan['plan_id'] or value['job_id'] != target['execution_id']
            or value['manifest_sha256'] != plan['manifest_sha256']):
        raise ValueError('allocation_receipt_identity_conflict')
    expected = {unit['unit_id'] for unit in plan['manifest']['units']}
    if len({row['unit_id'] for row in value['units']}) != len(value['units']) or not {
            row['unit_id'] for row in value['units']} <= expected:
        raise ValueError('allocation_receipt_units_conflict')
    return [value, read]


async def observe_allocation(ctx, ledger, plan, target, candidate, key):
    """One observation of the original job and its progress, with a measurement (the old
    ``_observe_original_allocation``, up to the branch on the tool)."""
    status = answered(hpc_remote.job_status(ctx, target))
    observation = recorded(ledger, 'status:' + key, 'native_status', {
        name: status[name] for name in ('state', 'observed_at', 'native', 'check_ref')})
    allocation, allocation_window = recorded(ledger, 'allocation:' + key, 'allocation_snapshot',
                                             await allocation_receipt(ctx, target, plan, 'allocation:' + key))
    observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                                                 'allocation': allocation, 'allocation_window': allocation_window})
    current = telemetry(observation, allocation, candidate)
    if current.get('current_unit_id') is not None:
        unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
        if unit.get('reports_progress', False):
            progress_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/progress.json'
            read = await hpc_remote.read_file(ctx, target['resource_id'], progress_path, 16384,
                                              name='progress:' + key)
            if read['status'] != 'completed':
                current['progress_failure'] = read['failure']['code']
            else:
                recorded(ledger, 'unit-progress:' + key, 'unit_progress', read)
                try:
                    progress = bind_progress(json.loads(base64.b64decode(read['bytes_base64'], validate=True)),
                                             plan['plan_id'])
                    current = incorporate_progress(current, progress, candidate)
                except (ValueError, KeyError, TypeError) as error:
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
        queue_value = recorded(ledger, queue_ref, 'queue', await observe_queue(ledger, ctx, 'queue:' + key))
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
    artifact = ctx.store.artifact(canonical(body).encode(), 'application/json')
    stored = ctx.store.put('source', {
        'provider': 'episode.hpc_result', 'accession': 'hpc_' + digest([ctx.run_id, ctx.episode_id, body]),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'hpc_result_v1',
        'retrieved_at': datetime.fromtimestamp(body['unit']['finished_at'], timezone.utc).isoformat()},
        origin='tool')
    return stored['id'], artifact


async def collect_original_results(arguments, ctx, ledger, plan, target, candidate, observed, key):
    commission = ledger.commission
    allocation, current = observed['allocation'], observed['current']
    accepted, failures, references, artifacts = [], [], [], []
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
        limit = commission['limits']['result_limit_bytes']
        result_window = answered(await hpc_remote.read_file(ctx, target['resource_id'], expected_path, limit,
                                                            name='result:' + key + ':' + unit['unit_id']))
        if result_window['size_bytes'] > limit:
            raise ValueError('compact_result_incomplete_or_too_large')
        recorded(ledger, 'result-window:' + key + ':' + unit['unit_id'], 'result_window', result_window)
        payload = base64.b64decode(result_window['bytes_base64'], validate=True)
        if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
            raise ValueError('result_changed_since_unit_completion')
        document = json.loads(payload)
        receipt = {'run_id': ctx.run_id, 'episode_id': ctx.episode_id, 'scope': arguments['scope'],
                   'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row, 'document': document,
                   'window': result_window, 'observation_ref': observed['observation_ref']}
        source_ref, artifact_ref = publish_result(ctx, receipt)
        references.append(source_ref)
        artifacts.append(artifact_ref)
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
             'credit': ledger.credit_view()}, references, artifacts)


def original_plan(ledger, arguments, ctx):
    """The frozen plan the arguments name, or the failure outcome when its handoff is not attached yet."""
    plan = ledger.read(arguments['plan_ref'])
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff')):
        return plan, invalid(argument_error(
            'original_handoff_not_attached',
            recovery='If the launch child already returned its handoff, attach the returned reference with '
                     'hpc_handoff. Do not launch replacement work.'))
    return plan, None


# ------------------------------------------------------------------------------------------------------------ tools

def hpc_open(arguments, ctx):
    """Open the ledger of the commission, creating it when this Episode holds none of its rows. The ledger id is
    what every later tool and every sister is handed; the credit the ledger already holds is not this episode's."""
    ledger = create_ledger(arguments, ctx)
    return completed({'ledger': ledger.ledger, 'credit_at_open': ledger.credit_view()['credit']})


def hpc_read(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    try:
        result = read_evidence(arguments, ctx, ledger, arguments['reference'])
    except (ValueError, KeyError) as error:
        return invalid(argument_error(str(error)))
    return completed(result)


def hpc_compare(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    try:
        result = {'comparisons': comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
    except (ValueError, KeyError) as error:
        return invalid(argument_error(
            str(error), recovery='Use a model_ref of the ledger\'s model_refs and a queue_ref of its queue_refs '
                                 '(hpc_queue_observe records one); a resource identity is not a queue '
                                 'observation.'))
    result['comparison_ref'] = ledger.put('comparison', {**result, 'model_ref': arguments['model_ref'],
                                                         'queue_ref': arguments['queue_ref'],
                                                         'episode_id': ctx.episode_id,
                                                         'operation_key': ctx.operation_key})
    return completed(result)


def hpc_history_refresh(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    result = recorded(ledger, 'shared_history:' + ctx.operation_key, 'shared_history', shared_history(ledger, ctx))
    return completed(result)


async def hpc_discovery_run(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    configuration = resource_of(ledger, ctx)
    command = 'cd ' + shlex.quote(PROJECT_DIRECTORY) + ' && ' + arguments['command']
    cache_key = resource_identity(ledger.commission['resource_id'], configuration) + ':' + digest(command)
    cached = (ctx.services['estimate_table'].latest(cache_key, 'inventory') if memory_enabled(ctx)
              else {'state': 'unknown'})
    if cached['state'] == 'fresh':
        value = cached['data']
    else:
        ran = await hpc_remote.command(ctx, ledger.commission['resource_id'], command, name='discovery')
        if ran['status'] != 'completed':
            return failed(ran['failure'])
        value = {'command': arguments['command'], 'returncode': ran['returncode'],
                 'stdout': ran['files']['stdout.log'].decode('utf-8', 'replace'),
                 'stderr': ran['files']['stderr.log'].decode('utf-8', 'replace'), 'observed_at': time.time()}
        if memory_enabled(ctx) and ran['returncode'] == 0:
            ctx.services['estimate_table'].observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                                                   provenance=[ledger.ledger, 'discovery:' + ctx.operation_key])
    recorded(ledger, 'discovery:' + ctx.operation_key, 'discovery', value)
    return completed(value)


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
        return invalid(argument_error(str(error)))
    reference = ('caller_candidate:' + candidate['id'] if candidate in commission['candidates']
                 else ledger.put('candidate', candidate, identity='candidate:' + candidate['id']))
    return completed({'candidate_ref': reference, 'candidate_id': candidate['id']})


async def hpc_queue_observe(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    try:
        value = await observe_queue(ledger, ctx, 'queue')
    except ResourceRequestFailed as error:
        return failed(error.failure)
    reference = 'queue:' + digest(ctx.operation_key)
    recorded(ledger, reference, 'queue', value)
    result = {'queue_ref': reference,
              'features': [hpc_queue.features(value['snapshot'], candidate) for candidate in candidates_of(ledger)],
              'snapshot': value['snapshot']}
    return completed(result)


def hpc_plan(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    commission = ledger.commission
    configuration = resource_of(ledger, ctx)
    existing = ledger.records('plan')
    candidate = next((row for row in candidates_of(ledger) if row['id'] == arguments['candidate_id']), None)
    if candidate is None:
        return invalid(argument_error('unknown_candidate:' + arguments['candidate_id']))
    try:
        # What the model named: a queue observation that must be fresh, and a model of the ledger.
        observed = queue_snapshot(ledger, arguments['queue_ref'], require_fresh=True)
        model = ledger.read(arguments['model_ref'])
        queue = hpc_queue.features(observed, candidate)
        rules = queue['queue_rules']
        if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
            raise ValueError('choose_an_observed_enabled_execution_queue')
        for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
            if (rules['min_' + key] is not None and value < rules['min_' + key]
                    or rules['max_' + key] is not None and value > rules['max_' + key]):
                raise ValueError('candidate_violates_observed_queue_limits')
    except (ValueError, KeyError) as error:
        return invalid(argument_error(
            str(error), recovery='hpc_plan needs a queue_ref of the ledger\'s queue_refs that is still fresh '
                                 '(hpc_queue_observe records one) and a model_ref of its model_refs.'))
    plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
    features = candidate_features(candidate, queue)
    predicted = prediction.predict(model, features)
    reference = prediction.predict(ledger.read('reference_model'), features)
    plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'],
                original_prediction=predicted, original_reference=reference, operation_key=ctx.operation_key)
    choices = [row['body'] for row in ledger.records('model_choice')
               if row['body']['model_ref'] == arguments['model_ref']]
    plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
    plan_ref = ledger.put('plan', plan)
    forecast_ref = freeze_forecast(ledger, plan, predicted, reference, {}, 'planned', ctx.operation_key)
    # The frozen plan is the launch child's input: an artifact of this unit that the ledger names, so that it
    # travels in custody with the ledger's rows (the old local input file).
    artifact = ctx.store.artifact((canonical(plan) + '\n').encode(), 'application/json')
    ledger.put('launch_input', {'plan_id': plan['plan_id'], 'artifact_ref': artifact},
               identity='launch_input:' + plan['plan_id'], source_refs=[artifact])
    result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref,
              **{key: value for key, value in plan.items() if key != 'prediction_episode_id'},
              'launch_input_ref': artifact}
    return completed(result)


def hpc_handoff(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    commission = ledger.commission
    plan = ledger.read(arguments['plan_ref'])
    target = hpc_remote.handoff_target(ctx.store, arguments['handoff_ref'])
    if target['resource_id'] != commission['resource_id']:
        return invalid(argument_error('handoff_does_not_match_frozen_portfolio'))
    ledger.put('handoff', {'handoff_ref': arguments['handoff_ref'], 'job_id': target['execution_id'],
                           'plan_id': plan['plan_id']}, identity='handoff:' + plan['plan_id'],
               source_refs=[arguments['handoff_ref']])
    result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
    if 'monitoring' in commission:
        result['monitor_controller_ref'] = MonitorCronController(ledger).attach(
            plan, target['execution_id'], commission['monitoring'])
    return completed(result)


async def hpc_monitor(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    try:
        observed = await observe_allocation(ctx, ledger, plan, target, candidate, ctx.operation_key)
        result = await update_conditional_forecast(arguments, ctx, ledger, plan, target, candidate, observed,
                                                   ctx.operation_key)
    except ResourceRequestFailed as error:
        return failed(error.failure)
    return completed(result)


async def hpc_monitor_wait(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    key = ctx.operation_key
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor_controller')):
        return invalid(argument_error(
            'hpc_monitor_controller_not_attached',
            next_step='This original commission has no attached monitor controller. Use hpc_monitor on the '
                      'original plan, then hpc_results when its outputs are ready. Retain the original '
                      'submitted job; do not launch replacement work.'))

    async def monitor_once(monitor_key):
        observed = await observe_allocation(ctx, ledger, plan, target, candidate, monitor_key)
        return await update_conditional_forecast({'refresh_queue': True}, ctx, ledger, plan, target, candidate,
                                                 observed, monitor_key)
    try:
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
            controller = MonitorCronController(ledger)
            schedule = controller.reserve(plan, candidate, monitor, key)
            if schedule['job_id'] != target['execution_id']:
                raise ValueError('monitor_schedule_original_job_conflict')
            if schedule['valuation']['schedule']:
                await controller.wait(schedule)
                observed = await monitor_once(key + ':monitor')
                ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'],
                                            'job_id': target['execution_id'],
                                            'observed': {'status': 'completed', 'result': observed}},
                           identity='wake:' + key)
                result = {'schedule': schedule, 'monitor': observed}
            else:
                result = {'schedule': schedule, 'monitor': None}
    except ResourceRequestFailed as error:
        return failed(error.failure)
    return completed(result)


async def hpc_results(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    try:
        observed = await observe_allocation(ctx, ledger, plan, target, candidate, ctx.operation_key)
        result, references, artifacts = await collect_original_results(arguments, ctx, ledger, plan, target,
                                                                       candidate, observed, ctx.operation_key)
    except ResourceRequestFailed as error:
        return failed(error.failure)
    return completed(result, references, artifacts)


async def hpc_allocation_order(arguments, ctx):
    ledger = open_ledger(arguments, ctx)
    plan, failure = original_plan(ledger, arguments, ctx)
    if failure is not None:
        return failure
    target = original_target(ctx, ledger, plan)
    candidate = candidate_of(ledger, plan)
    allowed = {unit['unit_id'] for unit in candidate['units']}
    if not set(arguments['unit_ids']) <= allowed:
        return invalid(argument_error('only_original_work_units_can_be_selected'))
    # The allocation's runner reads this control file at its next unit boundary.
    control = ctx.store.artifact(canonical({'manifest_sha256': plan['manifest_sha256'],
                                            'unit_ids': arguments['unit_ids']}).encode(), 'application/json')
    written = await hpc_remote.write_file(ctx, target['resource_id'],
                                          plan['manifest']['workspace'] + '/allocation-control.json', control,
                                          name='order')
    if written['status'] != 'completed':
        return failed(written['failure'])
    ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': ctx.operation_key,
                                    'unit_ids': arguments['unit_ids'], 'receipt': written},
               source_refs=[control])
    return completed(written)


TOOLS = {'hpc_open': hpc_open, 'hpc_read': hpc_read, 'hpc_compare': hpc_compare,
         'hpc_history_refresh': hpc_history_refresh,
         'hpc_discovery_run': hpc_discovery_run, 'hpc_candidate_propose': hpc_candidate_propose,
         'hpc_queue_observe': hpc_queue_observe, 'hpc_plan': hpc_plan, 'hpc_handoff': hpc_handoff,
         'hpc_monitor': hpc_monitor, 'hpc_monitor_wait': hpc_monitor_wait, 'hpc_results': hpc_results,
         'hpc_allocation_order': hpc_allocation_order}


# -------------------------------------------------------------------------------------- deciding and choosing

def offered(ctx):
    """The actions this decision offers: the two sister commissions, every tool but ``hpc_open`` (the history
    refresh only with the shared memory) and the three job children."""
    names = [name for name in TOOL_CATALOG if name != 'hpc_history_refresh' or memory_enabled(ctx)]
    return ['hpc_prediction', 'hpc_execution', *names, 'launch', 'monitor', 'results']


def argument_schema(name):
    return (TOOL_CATALOG[name] if name in TOOL_CATALOG else CHILD_CATALOG[name])[1]


def output_schema(names):
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection', 'arguments_json'],
            'properties': {'selection': {'type': 'string', 'enum': list(names),
                                         'description': 'The one action of this decision.'},
                           'arguments_json': {'type': 'string',
                                              'description': 'The arguments of the action as a JSON object text.'}}}


def owner_arguments(summary, arguments):
    """The arguments of a tool: the model's, and what the commission fixes (the ledger id once it is open, the
    commission identity, the tool request and the scope)."""
    return {**arguments, **{name: summary[name] for name in INJECTED}}


def decide(summary, feedback, ctx):
    """The first unit opens the ledger (no model is asked). After it the model is shown the commission, the
    resource, the ledger, what the sisters and the job children returned, the credit and what it did so far, and
    selects one action. The yield controller's own state and the progress clock are not shown: nothing in them
    is the model's to decide."""
    if summary['ledger_view'] is None:
        return ToolCall('hpc_open', owner_arguments(summary, {}))
    names = offered(ctx)
    context = {
        'commission': summary['commission'],
        'resource': ctx.settings['resources'][summary['commission']['resource_id']],
        'ledger': summary['ledger_state'], 'predictions': summary['predictions'],
        'executions': summary['executions'], 'launches': summary['launches'], 'monitors': summary['monitors'],
        'acquisitions': summary['acquisitions'], 'credit': summary['credit'],
        'units_so_far': summary['units_so_far'], 'last_outcome': summary['last_outcome'], 'feedback': feedback,
        'actions': [{'selection': name, 'description': (TOOL_CATALOG.get(name) or CHILD_CATALOG[name])[0],
                     'input_schema': argument_schema(name)} for name in names]}
    if memory_enabled(ctx):
        # The measured execution profiles of earlier runs (a recorded read of the estimate table).
        context['shared_timing_profiles'] = ctx.services['estimate_table'].read('profiles')
    return ModelRequest(MODEL_ROLE, INSTRUCTIONS, context, output_schema(names))


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
            if plan['handed_off'] or any(item['plan_ref'] == arguments['plan_ref'] for item in summary['launches']):
                raise ValueError('hpc_plan_already_launched_once')
        if 'handoff_ref' in arguments and not records.holds(arguments['handoff_ref']):
            raise ValueError('record_not_held:' + arguments['handoff_ref'])
        if selection == 'hpc_handoff' and not any(
                item['plan_ref'] == arguments['plan_ref'] and arguments['handoff_ref'] in item['handoff_refs']
                for item in summary['launches']):
            # The handoff of a plan is the one the launch of that plan returned.
            raise ValueError('handoff_does_not_match_frozen_portfolio')
    except (ValidationError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selection in TOOLS:
        return ToolCall(selection, owner_arguments(summary, arguments))
    units = {'hpc_prediction': (), 'hpc_execution': (), 'launch': ('handoff_unit', 'acquired_record_unit'),
             'monitor': ('information_unit',), 'results': ('acquired_record_unit',)}[selection]
    return ChildCall(selection, {**arguments, **{unit: ctx.settings[unit] for unit in units}})
