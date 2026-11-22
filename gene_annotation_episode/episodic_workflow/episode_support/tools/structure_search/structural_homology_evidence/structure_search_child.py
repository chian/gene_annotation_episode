"""The shared machinery of A102's job child ``structure_search``: one job on the Foldseek web server (``jobs/foldseek_job_route``,
resource kind ``foldseek``) in the shape the owner ordered for job children (A101's ``bvbrc_job_child``), with the one action
A102 adds: ``get_model``. THIS IS A102'S OWN COPY of that machinery (the repository's per-axis library convention): A101's
module is fixed to the resource kind ``bvbrc`` and stays untouched, so tuning one axis never changes the other.

The actions, each with ONE deterministic check over the model's filled JSON and what the episode holds (a check with problems
makes the episode's ``action`` raise ``Rejected`` with the fix list; nothing is run; a passed check simply works):

* ``get_model`` (A102's own): obtain a model of the target from one source (``alphafold_db`` or ``esmfold``), offered only
  while no model is held and the source was not tried (``sources_offered``, ``check_get_model``). The unit itself is in
  ``foldseek_search.obtain_model``.
* ``estimate`` (gated): the seconds the search is expected to take and their basis, exactly the ledger's figure
  (``ledger_estimate``); any other figure is refused with its field and ``choose_from`` the figure.
* ``launch``: refused unless an estimate AND a model are held (``estimate_required``, ``model_required``); one launch per
  estimate; refused when the product it would make is already held.
* ``fix`` (only after a failure), ``monitor`` (a wait in a stated range, one status request, a revised remaining time) and
  ``extract`` (fetch and grade in one unit).

HOW THE CHILD BINDS THIS. ``foldseek_search.APPLICATION`` is the one ``JobApplication(...)``; the child's ``task.py`` calls the
functions here with it. The recipe is that of A101 (``JobApplication``'s fields, ``prepare``, ``extract``, ``describe_identity``,
``field_problems``): ``prepare`` runs in the launch unit and returns ``{'job', 'inputs', 'job_facts', 'identity'}``; the
identity is kept in the handoff row's ``estimates`` so that the head and a continuation read it from the row (a parent holds
the row, not the job's input artifacts); what the job was given is read from the handoff row's staged inputs
(``detail.input_refs``) and never recomputed.

Credit is bounded and counts each unit once: a model held (``model_unit``; only when this commission obtained it), an estimate
held, the job launched (once however many launches a fix needed), the job known ended and the graded result
(``bounded_credit``). The episode's yield controller is ``CompletionYieldController`` to the sum of the units the commission
can obtain (``read_common``, ``completion_controller``). A ``not_found`` answer of a model source is a completed unit that holds
nothing and earns nothing: it is a discovered fact, not a failure.

The ledger: one row per launch (``launch_job``), kind ``structure_search:foldseek:<mode>:<database>``, with the job facts
(service, application, database, mode, and the size field ``residues``: the model's residue count). The Foldseek ticket
carries no task times, so the duration written is the one observed (``monitor_job``: launch to the first status that showed
the end, ``duration_source`` ``first_status_showing_the_end``)."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from typing import Callable

from episode_runtime.job_access import job_handle
from yield_control import CompletionYieldController
from method_loop import ChoiceField, Field

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    ESMFOLD_MAX_LENGTH, PROTEIN_ALPHABET)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.duration_trend import duration_trend
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import checks, closure, job_rows
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job

ROUTE_KIND = 'foldseek'
ACTIONS = ('get_model', 'estimate', 'launch', 'fix', 'monitor', 'extract')
STATES = ('no_model', 'model_held', 'estimated', 'launched', 'finished', 'extracted', 'failed')
UNTIL = ('launched', 'extracted')
MODEL_SOURCES = ('alphafold_db', 'esmfold')
MODEL_STATUSES = ('found', 'not_found')
ENDED_JOB_STATES = ('finished', 'failed', 'unknown')
ESTIMATE_BASES = ('learned_from_earlier_jobs', 'no_earlier_measurement')
ESTIMATE_RANGE = (1, 604800)
# The seconds of the first job of a kind, when the ledger has measured none: the one figure not learned from the ledger (there
# is nothing to learn from); the first measured job of the kind replaces it. The live check of 2026-11-21 observed 6 to 10 s
# for a Foldseek search of a 70-residue model against afdb-swissprot (docs/plan/designs/a102_services.md).
FIRST_JOB_SECONDS = 10
WAIT_RANGE_MAX = 1800
CLOCK_MARGIN_SECONDS = 1.0
LEDGER_ROWS = 500
UNITS = ('handoff_unit', 'information_unit', 'graded_unit', 'model_unit')
PRIOR = ('handoff_refs', 'check_refs', 'closure_refs')
# The fixed vocabulary of failure codes: a failure after a passed check is the environment's and is returned once with one of
# these (the route, ``jobs/foldseek_job_route.py``, uses the first group and keeps the service's own error in the detail; the
# model sources use the last two).
FAILURE_CODES = (
    'provider_spacing_required', 'provider_connection_failed', 'provider_request_timeout', 'provider_http_error',
    'provider_redirect_not_followed', 'provider_submission_response_invalid', 'provider_status_response_invalid',
    'provider_result_response_invalid', 'submission_outcome_unknown', 'results_not_available', 'job_state_unknown',
    'result_file_missing', 'result_not_in_catalog', 'service_reported_failed', 'service_lost_the_job',
    'grading_refused', 'result_of_another_query', 'result_of_another_database',
    'model_source_request_failed', 'model_source_response_invalid')
# The service's spacing refusal of a status request (nothing was sent): the one retryable failure.
SPACING = 'provider_spacing_required'


def failure_code(code):
    """A code of the route as a value of the fixed vocabulary (the HTTP status of ``provider_http_<n>`` is dropped)."""
    if code.startswith('provider_http_'):
        return 'provider_http_error'
    if code not in FAILURE_CODES:
        raise ValueError('failure_code_not_in_the_vocabulary:' + code)
    return code


def now_text():
    return datetime.now(timezone.utc).isoformat()


def seconds_between(earlier, later):
    return (datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).total_seconds()


def search_facts(search):
    """The held job as controlled facts (``None`` while none is held): its records, the prediction recorded with its
    launch, the service's own estimate (none for this service) and its latest check (with the seconds from the launch to
    it). ``search`` is a view ``{'handoff', 'checks', 'closure'}`` of job ledger rows."""
    if search is None:
        return None
    handoff = search['handoff']
    shown = search['checks'][-1] if search['checks'] else None
    estimates = handoff['detail']['estimates']
    return {'handoff_ref': handoff['id'], 'check_refs': [row['id'] for row in search['checks']],
            'closure_ref': None if search['closure'] is None else search['closure']['id'],
            'submitted_at': handoff['at'], 'predicted_seconds': estimates['predicted_seconds'],
            'prediction_basis': estimates['duration_basis'],
            'service_estimate_seconds': handoff['detail']['native']['expected_seconds'],
            'latest_check': None if shown is None else {
                'check_ref': shown['id'], 'observed_at': shown['at'], 'state': shown['detail']['state'],
                'result_available': shown['detail']['result_available'],
                'observed_seconds': seconds_between(handoff['at'], shown['at'])}}


def seconds_until_allowed(description, facts, now):
    """Seconds until the service allows the next status request of the held job (0.0 when now): the longer of the
    spacing between two contacts, from the latest contact (the launch or the latest check), and the spacing between two
    status requests of one job, from the latest check (``description`` is the resource's, with both spacings; ``facts``
    is ``search_facts``)."""
    shown = facts['latest_check']
    last = facts['submitted_at'] if shown is None else shown['observed_at']
    remaining = description['request_spacing_seconds'] - seconds_between(last, now)
    if shown is not None:
        remaining = max(remaining, description['poll_spacing_seconds'] - seconds_between(shown['observed_at'], now))
    return max(0.0, remaining)


def timing(facts, now):
    """The controlled facts of the job's duration as of ``now``: what was predicted, the service's own estimate (none for
    this service), the seconds since the launch, and how far past each the job is (negative: before it)."""
    elapsed = seconds_between(facts['submitted_at'], now)
    predicted, service = facts['predicted_seconds'], facts['service_estimate_seconds']
    return {'seconds_since_submission': elapsed, 'predicted_seconds': predicted,
            'prediction_basis': facts['prediction_basis'], 'service_estimate_seconds': service,
            'seconds_past_prediction': None if predicted is None else elapsed - predicted,
            'seconds_past_service_estimate': None if service is None else elapsed - service}


def _choose(field, code, **detail):
    """One thing to fix in the model's JSON: the field, the code and what to choose from."""
    return {'field': field, 'code': code, **detail}


def _failed(code, retryable, **detail):
    """The outcome of a unit that failed after its check passed, with its code from the fixed vocabulary."""
    return {'status': 'failed', 'failure_code': failure_code(code), 'retryable': retryable, 'record_refs': [],
            'detail': detail}


def _ended(table, handle, outcome, duration):
    """Resolve the launch's estimate-ledger row with its outcome and measured duration."""
    table.resolve(handle, {'gain': 0.0, 'cost': 0.0, 'outcome': outcome, 'duration_seconds': duration}, at=now_text())


@dataclass(frozen=True)
class JobApplication:
    application: str
    child: str
    service: str
    provider: str
    product_kind: str
    request_fields: tuple
    estimate_fields: tuple
    field_schemas: dict
    size_field: str
    kind: Callable
    field_problems: Callable
    prepare: Callable
    extract: Callable
    describe_identity: Callable


def ledger_kind(binding, fields):
    """The kind a job is recorded under on the estimate ledger: later jobs of the same service and application settings
    read what earlier ones measured."""
    return binding.child + ':' + binding.service + ':' + binding.kind(fields)


def ledger_estimate(trend, learned_basis):
    """THE ESTIMATE THE LEDGER GIVES for a job, from the trend of its kind (``duration_trend``): ``{'basis',
    'expected_seconds'}``. With measured jobs the basis is ``learned_basis`` and the seconds are what the line of duration
    against size gives for this job when the line is fitted, else the median of the measured jobs; with none the basis is
    ``no_earlier_measurement`` and the seconds are ``FIRST_JOB_SECONDS``. Rounded to 0.1 s and held inside
    ``ESTIMATE_RANGE``, so the figure the model is shown is the figure the check requires."""
    if trend['measured']:
        fit = trend['size_fit']
        seconds = (fit['predicted_seconds'] if fit is not None and fit['predicted_seconds'] is not None
                   else trend['typical_seconds'])
        basis = learned_basis
    else:
        seconds, basis = FIRST_JOB_SECONDS, 'no_earlier_measurement'
    return {'basis': basis, 'expected_seconds': min(max(round(seconds, 1), ESTIMATE_RANGE[0]), ESTIMATE_RANGE[1])}


def estimate_problems(request, figure, found, field):
    """The things to fix in an estimate's ``basis`` and ``expected_seconds`` against ``figure`` (``ledger_estimate``):
    the basis must be the ledger's (``found`` measured jobs, reported as ``field``) and the seconds the ledger's figure."""
    problems = []
    if request['basis'] != figure['basis']:
        problems.append(_choose('basis', 'basis_does_not_match_the_learned_statistics', **{field: found},
                                choose_from=[figure['basis']]))
    if request['expected_seconds'] != figure['expected_seconds']:
        problems.append(_choose('expected_seconds', 'expected_seconds_is_not_the_ledger_estimate',
                                choose_from=[figure['expected_seconds']]))
    return problems


def learned(table, binding, fields, size):
    """What the ledger has learned of this kind of job (``duration_trend``: how many were measured, their band, the
    latest, and the line of duration against ``binding.size_field`` once enough different sizes are measured), with
    ``ledger_estimate``: the basis and seconds an estimate of this job must state."""
    trend = duration_trend(table.read('rows', ledger_kind(binding, fields), LEDGER_ROWS),
                           size_field=binding.size_field, size=size)
    return {**trend, 'ledger_estimate': ledger_estimate(trend, 'learned_from_earlier_jobs')}


# -- what the episode holds ------------------------------------------------------------------------------------------
def job_view(reader, binding):
    """The latest job of this binding the episode holds, from its job ledger rows: ``{'handoff', 'checks', 'closure'}``,
    or ``None`` while it holds no handoff. A launch after a fix is a second handoff: the latest is the job."""
    handoffs = [row for row in job_rows(reader) if row['event'] == 'handoff'
                and row['detail']['estimates']['kind'].startswith(binding.child + ':')]
    if not handoffs:
        return None
    handoff = handoffs[-1]
    return {'handoff': handoff, 'checks': checks(reader, handoff['job']), 'closure': closure(reader, handoff['job'])}


def held_jobs(reader, binding):
    """The jobs of this binding the parent holds: one row per handoff, with its request, the identity the binding
    describes, the state its latest held check showed (``submitted`` before any), whether it is outstanding (no closure
    held and not shown failed or lost) and the references of its rows: an outstanding job is continued by a later
    commission (``until`` ``extracted``)."""
    found = []
    for handoff in (row for row in job_rows(reader) if row['event'] == 'handoff'
                    and row['detail']['kind'] == ROUTE_KIND
                    and row['detail']['estimates']['kind'].startswith(binding.child + ':')):
        shown, ended = checks(reader, handoff['job']), closure(reader, handoff['job'])
        state = 'submitted' if not shown else shown[-1]['detail']['state']
        found.append({'handoff_ref': handoff['id'], 'resource_id': handoff['detail']['resource_id'],
                      'request': handoff['detail']['estimates']['request'],
                      'identity': binding.describe_identity(reader, handoff), 'latest_state': state,
                      'closed': ended is not None, 'outstanding': ended is None and state not in ('failed', 'unknown'),
                      'known_ended': state in ENDED_JOB_STATES, 'launched_at': handoff['at'],
                      'check_refs': [row['id'] for row in shown],
                      'closure_refs': [] if ended is None else [ended['id']],
                      'estimated_seconds': handoff['detail']['estimates']['predicted_seconds'],
                      'estimate_basis': handoff['detail']['estimates']['duration_basis']})
    return found


def job_notice(facts, revised_remaining=None):
    """The wait notice of a job launched and not extracted: seconds since the launch (as of the latest thing the holder
    knows), the estimated total seconds and the expected remaining seconds (the estimate minus the elapsed, not below
    zero, unless a status request came with a revised remaining time, which is the later fact). ``facts`` is
    ``search_facts``."""
    elapsed = 0.0 if facts['latest_check'] is None else facts['latest_check']['observed_seconds']
    estimated = facts['predicted_seconds']
    remaining = revised_remaining if revised_remaining is not None else max(estimated - elapsed, 0.0)
    return {'seconds_since_launch': elapsed, 'estimated_seconds': estimated, 'expected_remaining_seconds': remaining}


def resumed_rows(binding, job):
    """The unit rows a passed-back job stands for in ``episode_state``: its estimate and launch (as recorded with the
    handoff) and, when it holds status records, the state the latest shows."""
    handoff = job['handoff']
    estimates = handoff['detail']['estimates']
    request = estimates['request']
    done = {'status': 'completed', 'failure_code': None, 'retryable': False}
    rows = [{'action': 'estimate', **done, 'estimate': {**{name: request[name] for name in binding.estimate_fields},
                                                         'expected_seconds': estimates['predicted_seconds'],
                                                         'basis': estimates['duration_basis']}},
            {'action': 'launch', **done, 'request': dict(request)}]
    if job['checks']:
        latest = job['checks'][-1]['detail']
        rows.append({'action': 'monitor', **done, 'state': latest['state'], 'result_available': latest['result_available'],
                     'waited_seconds': 0})
    return rows


def episode_state(rows, model_held):
    """The state the episode's own units give, walked in order. ``rows`` are the unit rows: ``action``, ``status``,
    ``failure_code``, ``retryable`` and by action ``estimate``, ``request``, ``state`` and ``fix``; ``model_held``: whether a
    model of the target is held (a get_model unit that found one, or one the commission passed, or the job's own). Returns
    ``{'state', 'estimate', 'request', 'failed_request', 'fixed_field', 'last_failure_code', 'estimates_made',
    'launches'}``. Before a launch the state is ``estimated`` only with an estimate AND a model held, ``model_held`` with a
    model only, ``no_model`` otherwise (an estimate may be held without a model: it is the job's duration, which depends on
    the size of the target, and a launch is refused until a model is held)."""
    held = {'estimate': None, 'request': None, 'failed_request': None, 'fixed_field': None, 'last_failure_code': None,
            'estimates_made': 0, 'launches': 0}
    active = finished = extracted = needs_fix = False

    def failed(code):
        nonlocal active, finished, needs_fix
        active = finished = False
        needs_fix = True
        held['failed_request'], held['fixed_field'], held['last_failure_code'] = held['request'], None, code

    for row in rows:
        ok = row['status'] == 'completed'
        if row['action'] == 'estimate' and ok:
            held['estimate'] = row['estimate']
            held['estimates_made'] += 1
        elif row['action'] == 'launch':
            held['launches'] += 1
            held['estimate'] = None
            if ok:
                held['request'], held['fixed_field'] = row['request'], None
                active, finished, needs_fix = True, False, False
            else:
                held['request'] = row['request']
                failed(row['failure_code'])
        elif row['action'] == 'monitor':
            if not ok:
                if not row['retryable']:
                    failed(row['failure_code'])
            elif row['state'] == 'finished':
                active, finished = False, True
            elif row['state'] in ('failed', 'unknown'):
                failed({'failed': 'service_reported_failed', 'unknown': 'service_lost_the_job'}[row['state']])
        elif row['action'] == 'extract':
            if ok:
                finished, extracted = False, True
            else:
                failed(row['failure_code'])
        elif row['action'] == 'fix' and ok:
            needs_fix, held['fixed_field'] = False, row['fix']['field']
    state = ('extracted' if extracted else 'failed' if needs_fix else 'finished' if finished else
             'launched' if active else 'estimated' if held['estimate'] is not None and model_held else
             'model_held' if model_held else 'no_model')
    return {'state': state, **held}


def unit_row(position, unit):
    """One summary row of a completed unit of the loop (``unit``: ``tool``, ``arguments``, ``outcome``). A ``get_model`` row
    carries its source (always) and, when the unit completed, what the source answered (``model_status``) and the controlled
    facts of a model found (residues, mean pLDDT 0 to 100)."""
    outcome = unit['outcome']
    row = {'position': position, 'action': unit['tool'], 'status': outcome['status'],
           'failure_code': outcome.get('failure_code'), 'retryable': outcome.get('retryable', False)}
    if unit['tool'] == 'get_model':
        row['source'] = unit['arguments']['source']
    if outcome['status'] == 'completed':
        if unit['tool'] == 'get_model':
            row.update(model_status=outcome['model_status'], residues=outcome['residues'],
                       mean_plddt=outcome['mean_plddt'])
        elif unit['tool'] == 'estimate':
            row['estimate'] = outcome['estimate']
        elif unit['tool'] == 'monitor':
            row.update(state=outcome['state'], result_available=outcome['result_available'],
                       waited_seconds=outcome['waited_seconds'],
                       expected_remaining_seconds=outcome['expected_remaining_seconds'])
        elif unit['tool'] == 'fix':
            row['fix'] = outcome['fix']
    if unit['tool'] == 'launch':
        row['request'] = outcome['request']
    return row


# -- the checks: the things to fix in the model's JSON -----------------------------------------------------------------
def sources_offered(rows, *, model_held, sequence):
    """The model sources ``get_model`` offers: none while a model is held; else each source not tried by an earlier
    ``get_model`` unit of this episode (whatever its outcome), and ``esmfold`` only for a sequence the service takes (standard
    amino acids, at most ``ESMFOLD_MAX_LENGTH``); no source when the sequence has other letters."""
    if model_held or PROTEIN_ALPHABET.fullmatch(sequence) is None:
        return []
    tried = {row['source'] for row in rows if row['action'] == 'get_model'}
    return [source for source in MODEL_SOURCES if source not in tried
            and not (source == 'esmfold' and len(sequence) > ESMFOLD_MAX_LENGTH)]


def check_get_model(request, *, rows, model_held, sequence):
    """``request``: ``source``. The conditions: no model is held; the sequence has only standard amino acids; the source was
    not tried; ``esmfold`` only for a sequence of at most ``ESMFOLD_MAX_LENGTH`` residues."""
    problems = []
    if model_held:
        problems.append(_choose('action', 'model_already_held'))
    if PROTEIN_ALPHABET.fullmatch(sequence) is None:
        problems.append(_choose('action', 'target_sequence_has_residues_no_model_source_takes'))
    tried = [row['source'] for row in rows if row['action'] == 'get_model']
    if request['source'] in tried:
        problems.append(_choose('source', 'source_already_tried', choose_from=[
            source for source in MODEL_SOURCES if source not in tried]))
    if request['source'] == 'esmfold' and len(sequence) > ESMFOLD_MAX_LENGTH:
        problems.append(_choose('source', 'sequence_longer_than_the_esmfold_limit', maximum=ESMFOLD_MAX_LENGTH,
                                length=len(sequence)))
    return problems


def check_estimate(binding, request, *, state, learned_trend, commission):
    """``request``: the binding's ``estimate_fields``, ``expected_seconds``, ``basis``. The conditions: no job is
    running or waiting for a fix; the application's own checks of the fields pass; the seconds are in range; the estimate
    is the ledger's (``learned_trend['ledger_estimate']``, which the decision shows): the basis says what it rests on
    (``learned_from_earlier_jobs`` only when the ledger has measured jobs of this kind, ``no_earlier_measurement`` only
    when it has none) and the seconds are the ledger's figure for it."""
    problems = list(binding.field_problems(request, commission))
    if state['state'] in ('launched', 'finished', 'failed'):
        problems.append(_choose('action', {'launched': 'job_running_monitor_it', 'finished': 'job_finished_extract_it',
                                           'failed': 'failure_needs_a_fix'}[state['state']]))
    if not ESTIMATE_RANGE[0] <= request['expected_seconds'] <= ESTIMATE_RANGE[1]:
        problems.append(_choose('expected_seconds', 'expected_seconds_out_of_range', minimum=ESTIMATE_RANGE[0],
                                maximum=ESTIMATE_RANGE[1]))
    problems.extend(estimate_problems(request, learned_trend['ledger_estimate'], learned_trend['measured'], 'measured_jobs'))
    return problems


def check_launch(binding, request, *, state, fields, resources, commission, model, reusable=None):
    """``request``: the binding's ``request_fields``. The conditions: an estimate is held (the gate: nothing is
    launched before one is made) and it restates the same estimate fields; a model of the target is held (``model``: its
    facts, or ``None``); the application's own checks pass; the resource is a bound Foldseek service; no job is running,
    finished or extracted; the first request is the commission's, after a failure only after a fix, with a request that
    differs from the failed one in the field the fix named; and the product this job would make is not already held
    (``reusable``: the held product row, from the binding's ``find_reusable``)."""
    problems = list(binding.field_problems(request, commission))
    if state['estimate'] is None:
        problems.append(_choose('action', 'estimate_required', take_first='estimate'))
    elif any(state['estimate'][name] != request[name] for name in binding.estimate_fields):
        problems.append(_choose('action', 'differs_from_the_estimate', estimate={
            name: state['estimate'][name] for name in binding.estimate_fields}))
    if model is None:
        problems.append(_choose('action', 'model_required', take_first='get_model'))
    if resources.get(request['resource_id']) != ROUTE_KIND:
        problems.append(_choose('resource_id', 'resource_is_not_a_foldseek_service',
                                choose_from=[name for name, kind in resources.items() if kind == ROUTE_KIND]))
    if state['state'] in ('launched', 'finished', 'extracted'):
        problems.append(_choose('action', {'launched': 'job_already_launched', 'finished': 'job_already_finished',
                                           'extracted': 'result_already_held'}[state['state']]))
    elif state['state'] == 'failed':
        problems.append(_choose('action', 'fix_required_after_the_failure', take_first='fix'))
    elif state['failed_request'] is None:
        for name in binding.request_fields:
            if request[name] != fields[name]:
                problems.append(_choose(name, 'differs_from_the_commission', commission=fields[name]))
    elif request[state['fixed_field']] == state['failed_request'][state['fixed_field']]:
        problems.append(_choose(state['fixed_field'], 'repeats_the_failed_request_in_the_fixed_field',
                                failed=state['failed_request'][state['fixed_field']]))
    if reusable is not None:
        problems.append(_choose('action', binding.product_kind + '_already_held', row=reusable['id']))
    return problems


def check_fix(binding, request, *, state):
    """``request``: ``failure_code``, ``field``. A failure is waiting for its fix, the code is that of the last failure
    and the field is one of the request's."""
    if state['state'] != 'failed':
        return [_choose('action', 'nothing_to_fix')]
    problems = []
    if request['failure_code'] != state['last_failure_code']:
        problems.append(_choose('failure_code', 'is_not_the_last_failure', choose_from=[state['last_failure_code']]))
    if request['field'] not in binding.request_fields:
        problems.append(_choose('field', 'is_not_a_request_field', choose_from=list(binding.request_fields)))
    return problems


def _held(request, job):
    if job is None:
        return [_choose('handoff_ref', 'no_job_held')]
    if request['handoff_ref'] != job['handoff']['id']:
        return [_choose('handoff_ref', 'handoff_is_not_the_held_job', choose_from=[job['handoff']['id']])]
    return []


def minimum_wait(description, facts, now):
    """The fewest seconds a status request of the held job must wait (0 when it may be made now): what
    ``seconds_until_allowed`` gives and the clock margin when it is above 0."""
    allowed = seconds_until_allowed(description, facts, now)
    return 0.0 if allowed <= 0 else math.ceil(allowed + CLOCK_MARGIN_SECONDS)


def check_monitor(request, *, state, job, minimum):
    """``request``: ``handoff_ref``, ``wait_seconds``, ``expected_remaining_seconds``. A job is launched and not known to
    have ended; the handoff is the held job; the wait is within its range, whose lower end is ``minimum``."""
    problems = _held(request, job)
    if not problems and state['state'] != 'launched':
        problems.append(_choose('action', {'no_model': 'nothing_launched', 'model_held': 'nothing_launched',
                                           'estimated': 'nothing_launched', 'finished': 'job_already_shows_finished',
                                           'extracted': 'result_already_held',
                                           'failed': 'job_failed_fix_required'}[state['state']]))
    if not minimum <= request['wait_seconds'] <= WAIT_RANGE_MAX:
        problems.append(_choose('wait_seconds', 'wait_seconds_out_of_range', minimum=minimum, maximum=WAIT_RANGE_MAX))
    if not 0 <= request['expected_remaining_seconds'] <= ESTIMATE_RANGE[1]:
        problems.append(_choose('expected_remaining_seconds', 'expected_seconds_out_of_range', minimum=0,
                                maximum=ESTIMATE_RANGE[1]))
    return problems


def check_extract(request, *, state, job):
    """``request``: ``handoff_ref``. The handoff is the held job and its latest monitor shows it finished with results
    available; the result is not already held."""
    problems = _held(request, job)
    if not problems and state['state'] != 'finished':
        problems.append(_choose('action', {'no_model': 'nothing_launched', 'model_held': 'nothing_launched',
                                           'estimated': 'nothing_launched', 'launched': 'job_not_known_to_be_finished',
                                           'extracted': 'result_already_held',
                                           'failed': 'job_failed_fix_required'}[state['state']]))
    return problems


def check_resource_and_continuation(request, *, resources, jobs, same):
    """The commission conditions every job child shares: the resource is a bound Foldseek service; a job outstanding for this
    commission (``same(job)``: the job's identity and request are the commission's) is continued with ``until``
    ``extracted`` and one that is not the commission's blocks it; a job already closed for it is not commissioned again."""
    problems = []
    if resources.get(request['resource_id']) != ROUTE_KIND:
        problems.append(_choose('resource_id', 'resource_is_not_a_foldseek_service',
                                choose_from=[name for name, kind in resources.items() if kind == ROUTE_KIND]))
    for job in jobs:
        if job['outstanding'] and not same(job):
            problems.append(_choose('until', 'commission_must_continue_the_outstanding_job', job=job['identity']))
        if job['outstanding'] and same(job) and request['until'] != 'extracted':
            problems.append(_choose('until', 'a_continuation_follows_the_job_to_its_result', choose_from=['extracted']))
        if job['closed'] and same(job):
            problems.append(_choose('until', 'job_already_held'))
    return problems


# -- the tools -------------------------------------------------------------------------------------------------------
def record_estimate(ctx, *, estimate):
    """The estimate the model committed, as the outcome of its unit. The ledger gets ONE expectation per launch, written
    by ``launch_job`` just before the submission."""
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': [], 'estimate': dict(estimate)}


def launch_job(ctx, binding, *, request, estimate, commission):
    """One submission of the job the held estimate was made for. The binding prepares the job (its inputs kept through
    custody); the expectation is recorded on the ledger first (one row per launch, keyed by the job handle, with the
    job's facts); a failed submission resolves it with that outcome."""
    access, table = ctx.services['job_access'], ctx.services['estimate_table']
    prepared = binding.prepare(ctx, request, commission)
    handle = job_handle(ctx.operation_key, request['resource_id'], binding.child)
    kind = ledger_kind(binding, request)
    started = now_text()
    table.expect(kind, {'gain': {'value': 0.0, 'lower': 0.0, 'upper': 0.0}, 'cost': 0.0,
                        'duration_seconds': estimate['expected_seconds'], 'duration_basis': estimate['basis'],
                        'job': {'service': binding.service, 'application': binding.application,
                                **prepared['job_facts']}}, key=handle, at=started)
    launched = access.launch(ctx, request['resource_id'], prepared['job'], inputs=prepared['inputs'], name=binding.child,
                             estimates={'kind': kind, 'estimate_key': handle,
                                        'predicted_seconds': estimate['expected_seconds'],
                                        'duration_basis': estimate['basis'], 'request': dict(request),
                                        'identity': prepared['identity']})
    if launched['status'] != 'completed':
        failure = launched['failure']
        _ended(table, handle, 'submit_failed:' + failure_code(failure['code']), seconds_between(started, now_text()))
        return {**_failed(failure['code'], False, sent=failure['detail'].get('sent'),
                          http_status=failure['detail'].get('http_status')), 'handoff_refs': [], 'request': dict(request)}
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'handoff_refs': [launched['handoff_ref']],
            'record_refs': [launched['handoff_ref'], launched['reply_ref']], 'request': dict(request),
            'predicted_seconds': estimate['expected_seconds'], 'duration_basis': estimate['basis'],
            'submitted_at': launched['submitted_at']}


def service_seconds(store, reply_ref):
    """The seconds the service's own task record gives from the submission of the job to its completion, or ``None``
    when the record names no completion time (the Foldseek ticket names none)."""
    reply = json.loads(store.get_artifact(reply_ref))
    if not reply.get('submit_time') or not reply.get('completed_time'):
        return None
    return seconds_between(*(reply[name].replace(' ', 'T') + '+00:00' for name in ('submit_time', 'completed_time')))


async def monitor_job(ctx, binding, *, handoff_ref, wait_seconds, expected_remaining_seconds):
    """One status request of the held job after the wait. What it shows is kept as a check row. The first request that
    shows the job ended (or a failed request) resolves the launch's ledger row with the measured duration: the service's
    own when its reply has one, else the seconds from the launch to this first status that showed the end
    (``duration_source`` says which)."""
    table = ctx.services['estimate_table']
    handoff = job_view(ctx.store, binding)['handoff']
    estimates = handoff['detail']['estimates']
    checked = await wait_for_job(ctx, handoff_ref, seconds=wait_seconds)
    if checked['status'] != 'completed':
        code = failure_code(checked['failure']['code'])
        retryable = code == SPACING
        if not retryable:
            _ended(table, estimates['estimate_key'], 'check_failed:' + code, seconds_between(handoff['at'], now_text()))
        return {**_failed(code, retryable, waited_seconds=checked['waited_seconds']), 'handoff_refs': []}
    if checked['state'] in ENDED_JOB_STATES:
        observed = seconds_between(handoff['at'], checked['observed_at'])
        measured = service_seconds(ctx.store, checked['reply_ref'])
        table.resolve(estimates['estimate_key'], {
            'gain': 0.0, 'cost': 0.0, 'outcome': checked['state'], 'observed_seconds': observed,
            'duration_seconds': observed if measured is None else measured,
            'duration_source': 'first_status_showing_the_end' if measured is None else 'service_task_record'},
            at=now_text())
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'state': checked['state'],
            'result_available': checked['result_available'], 'check_ref': checked['check_ref'],
            'record_refs': [checked['check_ref'], checked['reply_ref']], 'waited_seconds': checked['waited_seconds'],
            'expected_remaining_seconds': expected_remaining_seconds}


# -- the model's answer ----------------------------------------------------------------------------------------------
def output_schema(binding, state, sources):
    """The answer: one defined action with its controlled fields. ``get_model`` is offered only with a source to try
    (``sources``: ``sources_offered``), ``fix`` only while a failure waits."""
    def one(name, **fields):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', *fields],
                'properties': {'name': {'type': 'string', 'enum': [name]}, **fields}}
    handoff = {'type': 'string', 'minLength': 1}
    seconds = {'type': 'number', 'minimum': 0, 'maximum': ESTIMATE_RANGE[1]}
    schemas = binding.field_schemas
    options = []
    if sources:
        options.append(one('get_model', source={'type': 'string', 'enum': list(sources)}))
    options += [
        one('estimate', **{name: schemas[name] for name in binding.estimate_fields},
            expected_seconds={'type': 'number', 'minimum': ESTIMATE_RANGE[0], 'maximum': ESTIMATE_RANGE[1]},
            basis={'type': 'string', 'enum': list(ESTIMATE_BASES)}),
        one('launch', **{name: schemas[name] for name in binding.request_fields}),
        one('monitor', handoff_ref=handoff, wait_seconds={'type': 'number', 'minimum': 0, 'maximum': WAIT_RANGE_MAX},
            expected_remaining_seconds=seconds),
        one('extract', handoff_ref=handoff)]
    if state == 'failed':
        options.append(one('fix', failure_code={'type': 'string', 'enum': list(FAILURE_CODES)},
                           field={'type': 'string', 'enum': list(binding.request_fields)}))
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': options}}}


def common_instructions(what, result):
    """The instructions of the child: facts the system enforces, and what each answer means. ``what`` is the work (one
    sentence) and ``result`` what the graded result means here. Nothing recommends an action."""
    return (
        'You are the agent for one job of the Foldseek structure search server: ' + what + ' The commission\'s until says '
        'where this commission ends. launched: the episode ends the moment the launch completes (the job keeps running at '
        'the service and the parent is told how long to expect; a later commission resumes it). extracted: the job is '
        'followed to its graded result; when resumed is true the job was launched by an earlier commission (state launched '
        'or finished): no estimate or launch is possible, the job is monitored and extracted. The episode ends by itself '
        'when its credit reaches the target of the commission; you cannot end it.\n\n'
        'You do not write a request. You answer with one action as JSON; code checks your JSON before anything runs and '
        'runs the job.\n'
        '- get_model: obtain a model of the target from one source. Offered only while no model is held and for the '
        'sources not tried yet (sources). alphafold_db: the AlphaFold DB model (a prediction) of the UniProt entry whose '
        'sequence is exactly the target\'s; the answer not_found (no such entry, or no model for it) is a completed unit that '
        'holds nothing and earns nothing, and the source is not offered again. '
        'esmfold: a prediction of the sequence by ESMFold. Only an alphafold_db model carries the entry\'s accession and '
        'model version: the parent\'s tests that are keyed by an accession (its ligand transplants) are possible only for '
        'such a model, and never for an esmfold model. A model found is kept with its facts (origin, residues covered, '
        'mean pLDDT 0 to 100); the confidence describes the model and is not similarity. model_tries shows each try (source, '
        'status, residues, mean pLDDT); no protein name is ever shown.\n'
        '- estimate: the seconds the job is expected to take (expected_seconds) and their basis, both exactly as '
        'learned_durations.ledger_estimate gives them: the estimate comes from the ledger. With measured jobs of this kind '
        '(measured is how many, typical_seconds their median, latest_seconds the newest first, size_fit, when present, a line '
        'of seconds against the model\'s residue count) the basis is learned_from_earlier_jobs and the seconds are what '
        'size_fit gives for this job, else typical_seconds; with none the basis is no_earlier_measurement and the seconds '
        'are the fixed first figure. Any other figure is refused.\n'
        '- launch: the job, with the fields of the commission and the model held. Refused unless an estimate and a model '
        'are held (state estimated). One launch per estimate. Refused when the product it would make is already held.\n'
        '- monitor: one status request of the launched job (handoff_ref: the handoff record in job). wait_seconds is how '
        'long the unit waits before it asks: at least minimum_wait_seconds and at most the maximum shown. '
        'expected_remaining_seconds is your revised expectation of the time left. The first request that shows the job '
        'ended records the measured duration, which the next estimate learns from. No deadline, no cancel.\n'
        '- extract: only when the latest monitor shows the job finished (state finished). Code fetches the result and '
        'grades it in the same unit: ' + result + '\n'
        '- fix: only after a failure (state failed): the failure code you address (last_failure_code) and the request field '
        'you will change. Only after a fix does a launch pass, with a request that differs from the failed one in that '
        'field, after a new estimate.\n'
        'If your JSON is wrong you are told each problem as a code with the field it concerns (feedback.problems) and nothing '
        'has run; each problem is a field, a code and what to choose from.\n\n'
        'States: no_model (no model held), model_held (a model, no estimate), estimated (a model and an estimate), launched, '
        'finished, extracted, failed.\n\n'
        'Credit is bounded and only for what is new in this commission: a model obtained by get_model (credit.model_unit; '
        'not when the commission passed a model), an estimate held (credit.information_unit), the job launched '
        '(credit.handoff_unit), the job known ended (credit.information_unit: the first status that shows finished or '
        'failed) and the graded result (credit.graded_unit). When the target cannot be reached a few actions that earn '
        'nothing follow and the yield controller ends the episode. You cannot end it.')


# -- the commission, the credit, the controller, the return --------------------------------------------------------------
COMMON_ASSIGNMENT = {
    'until': ChoiceField('text', 'Where this commission ends: launched (estimate and launch, then park and return) or '
                                 'extracted (follow the job to its graded result)', UNTIL),
    'handoff_unit': Field('number', 'The credit of the established handoff (positive)'),
    'information_unit': Field('number', 'The credit of an estimate held and of a status request that shows a fact the '
                                       'earlier ones did not (positive)'),
    'graded_unit': Field('number', 'The credit of the established graded result (positive)'),
    'model_unit': Field('number', 'The credit of a model of the target obtained by get_model (positive)'),
    'model_refs': Field('record_refs', 'The model of the target the child uses: zero or one held data-product row of kind '
                                       'protein_structure_model, passed in custody with the artifact it names; when present '
                                       'get_model is never offered', required=False),
    'handoff_refs': Field('record_refs', 'The handoff record of a job an earlier visit launched, passed back in custody',
                          required=False),
    'check_refs': Field('record_refs', 'The status records of that job, passed back in custody', required=False),
    'closure_refs': Field('record_refs', 'The closure record of that job, passed back in custody', required=False),
    'known_ended': Field('boolean', 'Whether a passed-back status record already shows the job ended', required=False),
}


def read_common(assignment, name):
    """The part of ``read_from_parent`` every job child shares: ``units``, ``until``, ``prior``, ``resumed``,
    ``known_ended``, ``model_passed`` and the commission's finite ``target``: the credit still obtainable under ``until``: the
    model (unless one is passed or a handoff is passed back), the estimate and the launch (unless a handoff is passed
    back), the job known ended (unless already known) and the graded result (the last two for ``until`` ``extracted``)."""
    if any(not math.isfinite(assignment[unit]) or assignment[unit] <= 0 for unit in UNITS):
        raise ValueError(name + '_credit_units_must_be_positive')
    units, until = {unit: assignment[unit] for unit in UNITS}, assignment['until']
    prior = {key: list(assignment.get(key, [])) for key in PRIOR}
    resumed, known_ended = bool(prior['handoff_refs']), assignment.get('known_ended', False)
    model_passed = bool(assignment.get('model_refs'))
    if until == 'launched' and resumed:
        raise ValueError(name + '_a_continuation_follows_the_job_to_its_result')
    if resumed and model_passed:
        raise ValueError(name + '_a_continuation_reads_its_model_from_the_handoff')
    target = 0.0 if resumed else units['information_unit'] + units['handoff_unit'] + (
        0.0 if model_passed else units['model_unit'])
    if until == 'extracted':
        target += units['graded_unit'] + (0.0 if known_ended else units['information_unit'])
    return {'units': units, 'until': until, 'prior': prior, 'resumed': resumed, 'known_ended': known_ended,
            'model_passed': model_passed, 'target': target}


def bounded_credit(summary, records, provider):
    """Credit, bounded and counted only when new in this commission: a model obtained (a ``get_model`` unit that found one,
    and none was passed), an estimate held, the job launched (once, however many launches a fix needed), the job known ended
    (the first new status row that shows it) and the graded result (a held source of ``provider``). Each term is counted
    exactly where ``read_common`` put its unit into the target."""
    units, until, prior = summary['units'], summary['until'], summary['prior']
    rows = summary['unit_rows']
    new = not summary['resumed']
    model = new and not summary['model_passed'] and any(
        row['action'] == 'get_model' and row['status'] == 'completed' and row['model_status'] == 'found' for row in rows)
    estimate = new and any(row['action'] == 'estimate' and row['status'] == 'completed' for row in rows)
    handoff = new and any(row['action'] == 'launch' and row['status'] == 'completed' for row in rows)
    extracted = until == 'extracted'
    ended = extracted and not summary['known_ended'] and any(
        row['event'] == 'check' and row['id'] not in prior['check_refs'] and row['detail']['state'] in ENDED_JOB_STATES
        for row in job_rows(records))
    graded = extracted and any(source['provider'] == provider for source in records.list('source'))
    return ((units['model_unit'] if model else 0.0) + (units['information_unit'] if estimate else 0.0)
            + (units['handoff_unit'] if handoff else 0.0) + (units['information_unit'] if ended else 0.0)
            + (units['graded_unit'] if graded else 0.0))


def completion_controller(name, initial_credit, settings, parent_input):
    """The completion controller: continue until the credit reaches the commission's target; the cost is
    ``settings['cost']`` times the smallest credit unit of the commission."""
    cost = settings['cost'] * min(parent_input['units'].values())
    return CompletionYieldController(name, initial_credit, cost, parent_input['target'], settings['parameters'])


COMMON_FINDING = {
    'parked': Field('boolean', 'The job is launched and not extracted: this child parked, and the parent is shown the wait '
                               'notice (seconds since the launch, estimated seconds, expected remaining seconds)',
                    required=False),
    'seconds_since_launch': Field('number', 'The seconds from the launch to the latest thing the child knew', required=False),
    'expected_remaining_seconds': Field('number', 'The seconds still expected: the estimate minus the seconds since the '
                                                  'launch (not below zero), or the revised figure of a status request',
                                        required=False),
    'estimated_seconds': Field('number', 'The seconds the job was expected to take, as estimated before the launch',
                               required=False),
    'estimate_basis': ChoiceField('text', 'What the estimate rested on', ESTIMATE_BASES, required=False),
    'observed_seconds': Field('number', 'The seconds from the launch to the latest status request', required=False),
    'seconds_past_estimate': Field('number', 'The observed seconds minus the estimated seconds', required=False),
    'last_failure_code': ChoiceField('text', 'The failure code of the last failure', FAILURE_CODES, required=False),
}


def common_finding(summary):
    """The values of ``COMMON_FINDING`` from the summary (``notice``, ``job`` facts, ``last_failure_code``)."""
    finding, job = {}, summary['job']
    if summary['notice'] is not None:
        finding.update(parked=True, seconds_since_launch=summary['notice']['seconds_since_launch'],
                       expected_remaining_seconds=summary['notice']['expected_remaining_seconds'])
    if job is not None:
        if job['predicted_seconds'] is not None:
            finding['estimated_seconds'] = job['predicted_seconds']
            finding['estimate_basis'] = job['prediction_basis']
        if job['latest_check'] is not None:
            finding['observed_seconds'] = job['latest_check']['observed_seconds']
            if job['predicted_seconds'] is not None:
                finding['seconds_past_estimate'] = job['latest_check']['observed_seconds'] - job['predicted_seconds']
    if summary['last_failure_code'] is not None:
        finding['last_failure_code'] = summary['last_failure_code']
    return finding


__all__ = ['ACTIONS', 'COMMON_ASSIGNMENT', 'COMMON_FINDING', 'ESTIMATE_BASES', 'ESTIMATE_RANGE', 'FAILURE_CODES',
           'FIRST_JOB_SECONDS', 'JobApplication', 'MODEL_SOURCES', 'MODEL_STATUSES', 'ROUTE_KIND', 'STATES', 'UNTIL',
           'WAIT_RANGE_MAX', 'bounded_credit', 'check_estimate', 'check_extract', 'check_fix', 'check_get_model',
           'check_launch', 'check_monitor', 'check_resource_and_continuation', 'common_finding', 'common_instructions',
           'completion_controller', 'episode_state', 'estimate_problems', 'held_jobs', 'job_notice', 'job_view',
           'launch_job', 'ledger_estimate', 'ledger_kind', 'learned', 'minimum_wait', 'monitor_job', 'output_schema',
           'read_common', 'record_estimate', 'resumed_rows', 'search_facts', 'seconds_between', 'seconds_until_allowed',
           'sources_offered', 'timing', 'unit_row']
