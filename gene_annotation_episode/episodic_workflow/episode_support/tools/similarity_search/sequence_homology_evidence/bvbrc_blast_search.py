"""One database search through the BV-BRC application service (the ``Homology`` application), as plain library
functions that the actions of the ``bvbrc_blast`` episode call: one function per thing done (``record_estimate``,
``launch_search``, ``monitor_search``, ``fetch_and_grade_search``), the one deterministic check of each action
(``check_*``) and the readers of what the episode holds (``episode_state``, ``search_view``, ``graded_rows``).

Every action has ONE deterministic check over the model's filled JSON and what the episode holds. It returns the things
to fix (each a ``field`` and a ``code``, and what to choose from); an empty list means the action can run, and the
episode's ``action`` rejects anything else before a unit is made. A tool that runs after a passed check simply works: a
failure then is the environment's, returned once as ``failed`` with a code of the fixed vocabulary
``database_blast_search.FAILURE_CODES`` (the route, ``jobs/bvbrc_job_route.py``, uses those codes and keeps the service's
own error in the detail) and ``retryable`` false; the one exception is the service's spacing refusal of a status request
(nothing was sent).

What exists and is called, not written again: the route and its spacing (``bvbrc_job_route``), ``JobAccess.launch``,
``check`` and ``fetch`` (rows in custody), ``job_wait.wait_for_job`` (the wait of a status request),
``database_blast_search``: ``search_facts``, ``timing``, ``seconds_until_allowed``, ``failure_code``, ``now_text``,
``seconds_between``, ``_failed``, ``_ended`` and ``_observations`` (the hit references and comparison observations of a
graded report: nothing in them is specific to a service; imported, not copied), the grader (``grade_blast_result``: the
report of ``blast_formatter -outfmt 15`` is the single-query JSON15 the BLAST parser takes), ``retain_tool_grading``, the
search row ``SEARCHES``, ``job_progress.progress_information`` and the estimate table.

What is written here, because nothing existing serves: the vocabulary and checks of this episode's five actions, the walk
over the episode's own units that gives its state (the public episode's ``search_state`` knows one handoff and no fix),
``search_view`` of the latest handoff (a relaunch after a fix is a second handoff), the estimate recorded before the launch
and the revision and resolution of it at each status request, and the fetch-and-grade of this service's report (its file
name and its database name differ from the public service's)."""
import hashlib
import json
import math
import posixpath

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    saved_grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_graders import (
    grade_blast_result)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.bvbrc_job_route import PRECOMPUTED_DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import checks, closure, job_rows
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    ENDED_STATES, FAILURE_CODES, MOLECULE_UNITS, SPACING, STATUS_FIELDS, _choose, _ended, _failed, _observations,
    failure_code, now_text, search_facts, seconds_between, seconds_until_allowed, timing)

PROVIDER = 'bvbrc_blast'
SERVICE = 'bvbrc_homology'
JOB_NAME = 'bvbrc_blast'
QUERY_FILE = 'query.fasta'
REPORT = 'blast_out.raw.json'
ROUTE_KIND = 'bvbrc'
# The precomputed databases, by name as the application takes it (``db_precomputed_database``), with the unit of their
# sequences. Each was run against the live service before it was added (the design note records which).
DATABASES = {name: spec['unit'] for name, spec in PRECOMPUTED_DATABASES.items()}
ACTIONS = ('estimate', 'launch', 'fix', 'monitor', 'extract')
STATES = ('no_estimate', 'estimated', 'launched', 'finished', 'extracted', 'failed')
ESTIMATE_BASES = ('learned_from_earlier_searches', 'no_earlier_measurement')
REQUEST_FIELDS = ('program', 'database', 'resource_id')
# The range of the seconds an estimate may name, and of one wait of a status request. A wait is a granule the model
# chooses within the range (its lower end is what the service's spacing needs); it is no deadline on the search.
ESTIMATE_RANGE = (1, 604800)
WAIT_RANGE_MAX = 1800
CLOCK_MARGIN_SECONDS = 1.0


def search_kind(program, database):
    """The kind a search is recorded under in the estimate table: later searches of the same service, database and
    program read what earlier ones measured."""
    return 'bvbrc_blast:' + SERVICE + ':' + database + ':' + program


def combinations():
    """The (program, database) pairs the episode offers: each program that searches the unit of a database."""
    return [(program, database) for program, (_, unit, _) in sorted(PROGRAM_UNITS.items())
            for database, held in DATABASES.items() if held == unit]


def learned_statistics(table):
    """What the estimate table has learned of each offered kind of search, by ``program:database`` (read through the
    table's read handle in a decision): the number of resolved searches and the band of their measured durations."""
    return {program + ':' + database: (lambda found: {'resolved': found['resolved'],
                                                      'duration_seconds': found['duration_seconds']})(
        table.read('kind_statistics', search_kind(program, database))) for program, database in combinations()}


# -- what the episode holds -----------------------------------------------------------------------------------------
def search_view(reader):
    """The latest search the episode holds, from its job ledger rows: ``{'handoff', 'checks', 'closure'}`` (rows), or
    ``None`` while it holds no handoff. A launch after a fix is a second handoff: the latest is the search."""
    handoffs = [row for row in job_rows(reader) if row['event'] == 'handoff']
    if not handoffs:
        return None
    handoff = handoffs[-1]
    return {'handoff': handoff, 'checks': checks(reader, handoff['job']), 'closure': closure(reader, handoff['job'])}


def graded_rows(reader):
    """The graded searches the episode holds: one row per held source of this provider, with the grading artifact, the
    hit count of the sheet and the controlled features the feature reader gives."""
    rows = []
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        grading_ref = source['auxiliary_artifact_refs'][0]
        grading = json.loads(reader.get_artifact(grading_ref))['grading']
        rows.append({'source_ref': source['id'], 'grading_ref': grading_ref, 'hit_count': len(grading['sheet']['hits']),
                     'features': saved_grading_features(reader, grading_ref)})
    return rows


def episode_state(rows):
    """The state the episode's own units give, walked in order. ``rows`` are the unit rows of the summary: ``action``,
    ``status``, ``failure_code``, ``retryable`` and, by action, ``estimate`` (the estimate a completed estimate unit
    held), ``request`` (the request of a launch, completed or failed), ``state`` (what a completed monitor showed)
    and ``fix`` (the failure code and the request field a fix named). Returns ``{'state', 'estimate', 'request',
    'failed_request', 'fixed_field', 'last_failure_code', 'estimates_made', 'launches'}``: ``estimate`` is the
    held estimate not yet used by a launch; ``request`` the request of the latest completed launch;
    ``failed_request`` the request of the latest launch, search or extraction that failed and ``fixed_field`` the field
    a fix named for it (``None`` before the fix and after the next launch)."""
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
             'launched' if active else 'estimated' if held['estimate'] is not None else 'no_estimate')
    return {'state': state, **held}


# -- the checks: the things to fix in the model's JSON ----------------------------------------------------------------
def _program_and_database_problems(program, database, query_molecule):
    problems = []
    units = PROGRAM_UNITS[program]
    if units[0] != MOLECULE_UNITS[query_molecule]:
        problems.append(_choose('program', 'program_does_not_take_the_query_molecule', query_molecule=query_molecule,
                                choose_from=[name for name, (unit, *_) in PROGRAM_UNITS.items()
                                             if unit == MOLECULE_UNITS[query_molecule]]))
    if DATABASES[database] != units[1]:
        problems.append(_choose('database', 'database_does_not_hold_what_the_program_searches',
                                choose_from=[name for name, unit in DATABASES.items() if unit == units[1]]))
    return problems


def check_estimate(request, *, state, learned, query_molecule):
    """``request``: ``program``, ``database``, ``expected_seconds``, ``basis``. The conditions: no search is running or
    waiting for a fix (an estimate is made before a launch, again to revise it, and again after a fix); the program
    takes the query's molecule and the database holds what it searches; the seconds are in range; the basis says what the
    estimate rests on: ``learned_from_earlier_searches`` only when the table has measured searches of this kind, and
    ``no_earlier_measurement`` only when it has none (``learned`` is ``learned_statistics``)."""
    problems = _program_and_database_problems(request['program'], request['database'], query_molecule)
    if state['state'] in ('launched', 'finished', 'failed'):
        problems.append(_choose('action', {'launched': 'search_running_monitor_it', 'finished': 'search_finished_extract_it',
                                           'failed': 'failure_needs_a_fix'}[state['state']]))
    if not ESTIMATE_RANGE[0] <= request['expected_seconds'] <= ESTIMATE_RANGE[1]:
        problems.append(_choose('expected_seconds', 'expected_seconds_out_of_range', minimum=ESTIMATE_RANGE[0],
                                maximum=ESTIMATE_RANGE[1]))
    found = learned[request['program'] + ':' + request['database']]['resolved']
    if (request['basis'] == 'learned_from_earlier_searches') != (found > 0):
        problems.append(_choose('basis', 'basis_does_not_match_the_learned_statistics', measured_searches=found,
                                choose_from=['learned_from_earlier_searches' if found else 'no_earlier_measurement']))
    return problems


def check_launch(request, *, state, fields, query_molecule, resources):
    """``request``: ``program``, ``database``, ``resource_id``. The conditions: an estimate is held (the gate: nothing
    is launched before one is made), for this program and database; the resource is a bound BV-BRC service; the program
    takes the query's molecule and the database what it searches; no search is running, finished or extracted; the first
    request is the commission's, and after a failure only after a fix, with a request that differs from the failed one
    in the field the fix named."""
    problems = _program_and_database_problems(request['program'], request['database'], query_molecule)
    if state['estimate'] is None:
        problems.append(_choose('action', 'estimate_required', take_first='estimate'))
    elif (state['estimate']['program'], state['estimate']['database']) != (request['program'], request['database']):
        problems.append(_choose('database', 'differs_from_the_estimate', estimate={
            'program': state['estimate']['program'], 'database': state['estimate']['database']}))
    if resources.get(request['resource_id']) != ROUTE_KIND:
        problems.append(_choose('resource_id', 'resource_is_not_a_bvbrc_service',
                                choose_from=[name for name, kind in resources.items() if kind == ROUTE_KIND]))
    if state['state'] in ('launched', 'finished', 'extracted'):
        problems.append(_choose('action', {'launched': 'search_already_launched', 'finished': 'search_already_finished',
                                           'extracted': 'result_already_held'}[state['state']]))
    elif state['state'] == 'failed':
        problems.append(_choose('action', 'fix_required_after_the_failure', take_first='fix'))
    elif state['failed_request'] is None:
        for name in REQUEST_FIELDS:
            if request[name] != fields[name]:
                problems.append(_choose(name, 'differs_from_the_commission', commission=fields[name]))
    else:
        if request[state['fixed_field']] == state['failed_request'][state['fixed_field']]:
            problems.append(_choose(state['fixed_field'], 'repeats_the_failed_request_in_the_fixed_field',
                                    failed=state['failed_request'][state['fixed_field']]))
    return problems


def check_fix(request, *, state):
    """``request``: ``failure_code``, ``field``. The conditions: a failure is waiting for its fix, the failure code is
    that of the last failure, and the field is one of the request's."""
    if state['state'] != 'failed':
        return [_choose('action', 'nothing_to_fix')]
    problems = []
    if request['failure_code'] != state['last_failure_code']:
        problems.append(_choose('failure_code', 'is_not_the_last_failure', choose_from=[state['last_failure_code']]))
    if request['field'] not in REQUEST_FIELDS:
        problems.append(_choose('field', 'is_not_a_request_field', choose_from=list(REQUEST_FIELDS)))
    return problems


def _held(request, search):
    if search is None:
        return [_choose('handoff_ref', 'no_search_held')]
    if request['handoff_ref'] != search['handoff']['id']:
        return [_choose('handoff_ref', 'handoff_is_not_the_held_search', choose_from=[search['handoff']['id']])]
    return []


def minimum_wait(description, facts, now):
    """The fewest seconds a status request of the held search must wait (0 when it may be made now): what
    ``seconds_until_allowed`` gives, and the clock margin when it is above 0."""
    allowed = seconds_until_allowed(description, facts, now)
    return 0.0 if allowed <= 0 else math.ceil(allowed + CLOCK_MARGIN_SECONDS)


def check_monitor(request, *, state, search, minimum):
    """``request``: ``handoff_ref``, ``wait_seconds``, ``expected_remaining_seconds``. The conditions: a search is
    launched and not known to have ended; the handoff is the held search; the wait is within its range, whose lower end
    is ``minimum`` (what the service's spacing needs); the expected remaining seconds are in range."""
    problems = _held(request, search)
    if not problems and state['state'] != 'launched':
        problems.append(_choose('action', {'no_estimate': 'nothing_launched', 'estimated': 'nothing_launched',
                                           'finished': 'search_already_shows_finished',
                                           'extracted': 'result_already_held',
                                           'failed': 'search_failed_fix_required'}[state['state']]))
    if not minimum <= request['wait_seconds'] <= WAIT_RANGE_MAX:
        problems.append(_choose('wait_seconds', 'wait_seconds_out_of_range', minimum=minimum, maximum=WAIT_RANGE_MAX))
    if not 0 <= request['expected_remaining_seconds'] <= ESTIMATE_RANGE[1]:
        problems.append(_choose('expected_remaining_seconds', 'expected_seconds_out_of_range', minimum=0,
                                maximum=ESTIMATE_RANGE[1]))
    return problems


def check_extract(request, *, state, search):
    """``request``: ``handoff_ref``. The conditions: the handoff is the held search and its latest monitor shows the
    search finished with results available; the result is not already held."""
    problems = _held(request, search)
    if not problems and state['state'] != 'finished':
        problems.append(_choose('action', {'no_estimate': 'nothing_launched', 'estimated': 'nothing_launched',
                                           'launched': 'search_not_known_to_be_finished',
                                           'extracted': 'result_already_held',
                                           'failed': 'search_failed_fix_required'}[state['state']]))
    return problems


def check_commission(request, *, programs, sequences, scope_subjects, resources, commissioned):
    """The things to fix in the head's commission of this episode (``request``: ``query_ref``, ``program``,
    ``database``, ``resource_id``), before any child is commissioned. ``programs`` are the programs the commissioning
    episode offers (those its own credit can score). ``sequences`` is ``{record: molecule}``, ``commissioned`` the
    (query, program, database) of the earlier commissions of this child: one commission does the whole search, and
    nothing is passed back to a later one, so a repeat would submit the search again and is refused."""
    query, program, database = request['query_ref'], request['program'], request['database']
    problems = []
    if program not in programs:
        problems.append(_choose('program', 'program_is_not_offered', choose_from=list(programs)))
    if query not in scope_subjects:
        problems.append(_choose('query_ref', 'query_is_not_a_sequence_of_the_scope',
                                choose_from=[ref for ref in scope_subjects if ref in sequences]))
    problems.extend(_program_and_database_problems(program, database, sequences[query]))
    if resources.get(request['resource_id']) != ROUTE_KIND:
        problems.append(_choose('resource_id', 'resource_is_not_a_bvbrc_service',
                                choose_from=[name for name, kind in resources.items() if kind == ROUTE_KIND]))
    if (query, program, database) in commissioned:
        problems.append(_choose('database', 'search_already_commissioned'))
    return problems


# -- the tools --------------------------------------------------------------------------------------------------------
def record_estimate(ctx, *, estimate):
    """Record the expected duration of the coming launch on the estimate table, before the launch: the expectation under
    a key of this unit (``estimate_key``), of the kind of the search, with the basis the model named."""
    key = job_handle(ctx.operation_key, 'estimate', JOB_NAME)
    ctx.services['estimate_table'].expect(
        search_kind(estimate['program'], estimate['database']),
        {'gain': {'value': 0.0, 'lower': 0.0, 'upper': 0.0}, 'cost': 0.0,
         'duration_seconds': estimate['expected_seconds'], 'duration_basis': estimate['basis']},
        key=key, at=now_text())
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': [],
            'estimate': {**estimate, 'estimate_key': key}}


def launch_search(ctx, *, request, estimate, sequence_ref):
    """One submission of the search the held estimate was made for: the estimate's key is kept in the handoff row, so
    the status requests resolve it. A failed submission resolves the estimate with that outcome."""
    access, table = ctx.services['job_access'], ctx.services['estimate_table']
    job = {'program': request['program'], 'database': request['database'], 'query_file': QUERY_FILE}
    started = now_text()
    launched = access.launch(ctx, request['resource_id'], job, inputs={QUERY_FILE: sequence_ref}, name=JOB_NAME,
                             estimates={'kind': search_kind(request['program'], request['database']),
                                        'estimate_key': estimate['estimate_key'],
                                        'predicted_seconds': estimate['expected_seconds'],
                                        'duration_basis': estimate['basis']})
    if launched['status'] != 'completed':
        failure = launched['failure']
        _ended(table, estimate['estimate_key'], 'submit_failed:' + failure_code(failure['code']),
               seconds_between(started, now_text()))
        return {**_failed(failure['code'], False, sent=failure['detail'].get('sent'),
                          http_status=failure['detail'].get('http_status'),
                          rpc_error=failure['detail'].get('rpc_error')), 'handoff_refs': [], 'request': dict(request)}
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'handoff_refs': [launched['handoff_ref']],
            'record_refs': [launched['handoff_ref'], launched['reply_ref']], 'request': dict(request),
            'predicted_seconds': estimate['expected_seconds'], 'duration_basis': estimate['basis'],
            'submitted_at': launched['submitted_at']}


async def monitor_search(ctx, *, handoff_ref, wait_seconds, expected_remaining_seconds):
    """One status request of the held search after the wait (the existing wait helper). What it shows is kept as a check
    row. The estimate is updated: while the search has not ended, the model's revised expected remaining seconds are
    recorded as a new expectation of the kind ``<kind>:remaining``; the first request that shows the search ended (or a
    failed request) resolves the launch's estimate with the duration from the submission to that observation, so the
    next search of the kind learns from it."""
    table = ctx.services['estimate_table']
    handoff = search_view(ctx.store)['handoff']
    estimates = handoff['detail']['estimates']
    checked = await wait_for_job(ctx, handoff_ref, seconds=wait_seconds)
    if checked['status'] != 'completed':
        code = failure_code(checked['failure']['code'])
        retryable = code == SPACING
        if not retryable:
            _ended(table, estimates['estimate_key'], 'check_failed:' + code, seconds_between(handoff['at'], now_text()))
        return {**_failed(code, retryable, waited_seconds=checked['waited_seconds']), 'handoff_refs': []}
    if checked['state'] in ENDED_STATES:
        _ended(table, estimates['estimate_key'], checked['state'], seconds_between(handoff['at'], checked['observed_at']))
    else:
        table.expect(estimates['kind'] + ':remaining',
                     {'gain': {'value': 0.0, 'lower': 0.0, 'upper': 0.0}, 'cost': 0.0,
                      'duration_seconds': expected_remaining_seconds, 'duration_basis': 'model_revision_at_status'},
                     key=job_handle(ctx.operation_key, 'revision', JOB_NAME), at=now_text())
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'state': checked['state'],
            'result_available': checked['result_available'], 'check_ref': checked['check_ref'],
            'record_refs': [checked['check_ref'], checked['reply_ref']], 'waited_seconds': checked['waited_seconds'],
            'expected_remaining_seconds': expected_remaining_seconds}


def _grading(store, result_ref, fields, query_ref, sequence):
    """The grading of the fetched report into the database sheet of the original query: a report of another query or
    database is refused (``ValueError`` with its code). The report names its database by the file the service searched
    (``search_target.db``): its last path component is the database's file."""
    operand = {'subject_ref': query_ref, 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
               'database': fields['database']}
    grading = grade_blast_result(store.get_artifact(result_ref), mode='database', resource='api',
                                 output_format='json2', request=operand, _retain_correspondence=True)
    normalized = grading['sheet']['normalized_result']
    if normalized['mode'] != 'database' or normalized['query']['length'] != len(sequence):
        raise ValueError('result_of_another_query')
    if posixpath.basename(normalized['search']['database']) != PRECOMPUTED_DATABASES[fields['database']]['database_file']:
        raise ValueError('result_of_another_database')
    return grading


def fetch_and_grade_search(ctx, *, handoff_ref, fields, query_ref):
    """Fetch the report of the finished search and grade it in the same unit into the database sheet, kept through
    custody as ``database_blast_search.fetch_and_grade_search`` keeps its sheet: the grading artifact, a source of the
    provider over the fetched report, the search row that enters the search into the A101 sheet's tool profile, one
    reference record per hit and one comparison observation per alignment (what the head's credit reads). No step
    stands between the fetch and the grading."""
    store = ctx.store
    fetched = ctx.services['job_access'].fetch(ctx, handoff_ref, names=[REPORT])
    if fetched['status'] != 'completed':
        return {**_failed(fetched['failure']['code'], False), 'closure_ref': None}
    (result_ref,) = [item['ref'] for item in fetched['results'] if item['name'] == REPORT]
    sequence = store.get_artifact(store.get(query_ref)['sequence_ref']).decode('ascii').upper()
    try:
        grading = _grading(store, result_ref, fields, query_ref, sequence)
    except (ValueError, ContractError) as error:
        code = str(error) if str(error) in FAILURE_CODES else 'grading_refused'
        return {**_failed(code, False, reason=str(error)), 'closure_ref': fetched['closure_ref']}
    normalized = grading['sheet']['normalized_result']
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=result_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': result_ref, 'text_ref': None,
            'request_ref': None, 'version': normalized['search']['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref]}, origin='tool')
        search = store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': query_ref, 'profile': 'blast'})
        observations, references, unprojected = _observations(
            store, store.get_artifact(result_ref), grading, grading_ref, result_ref, source['id'], query_ref,
            fields['program'], len(sequence))
    refs = [source['id'], grading_ref, search['id'], *references, *observations]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'closure_ref': fetched['closure_ref'],
            'graded_refs': refs, 'record_refs': [*refs, fetched['closure_ref']],
            'hit_count': len(grading['sheet']['hits']), 'observation_count': len(observations),
            'unprojected_alignment_count': unprojected}


__all__ = ['ACTIONS', 'DATABASES', 'ESTIMATE_BASES', 'ESTIMATE_RANGE', 'FAILURE_CODES', 'PROVIDER', 'REQUEST_FIELDS',
           'ROUTE_KIND', 'STATES', 'STATUS_FIELDS', 'WAIT_RANGE_MAX', 'check_commission', 'check_estimate',
           'check_extract', 'check_fix', 'check_launch', 'check_monitor', 'combinations', 'episode_state',
           'fetch_and_grade_search', 'graded_rows', 'launch_search', 'learned_statistics', 'minimum_wait',
           'monitor_search', 'record_estimate', 'search_facts', 'search_kind', 'search_view', 'timing']
