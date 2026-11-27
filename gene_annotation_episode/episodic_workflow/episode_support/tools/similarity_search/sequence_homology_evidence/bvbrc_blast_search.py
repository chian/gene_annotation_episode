"""One database search through the BV-BRC application service (the ``Homology`` application), as plain library
functions that the actions of the ``bvbrc_blast`` episode call: one function per thing done (``record_estimate``,
``launch_search``, ``monitor_search``, ``fetch_and_grade_search``), the one deterministic check of each action
(``check_*``) and the readers of what the episode holds (``episode_state``, ``search_view``, ``graded_rows``).

Every action has ONE deterministic check over the model's filled JSON and what the episode holds. It returns the things
to fix (each a ``field`` and a ``code``, and what to choose from); an empty list means the action can run, and the
episode's ``action`` rejects anything else before a unit is made. A tool that runs after a passed check simply works: a
failure then is the environment's, returned once as ``failed`` with a code of the fixed vocabulary
``bvbrc_job_child.FAILURE_CODES`` (the route, ``jobs/bvbrc_job_route.py``, uses those codes and keeps the service's own
error in the detail) and ``retryable`` false; the one exception is the service's spacing refusal of a status request
(nothing was sent).

What exists and is called, not written again: the route and its spacing (``bvbrc_job_route``), ``JobAccess.launch``,
``check`` and ``fetch`` (rows in custody), ``job_wait.wait_for_job`` (the wait of a status request),
``bvbrc_job_child``: ``search_facts``, ``timing``, ``seconds_until_allowed``, ``failure_code``, ``now_text``,
``seconds_between``, ``_choose``, ``_failed``, ``_ended``, ``ledger_estimate`` and ``estimate_problems`` (imported, not copied), the grader (``grade_blast_result``:
the report of ``blast_formatter -outfmt 15`` is the single-query JSON15 the BLAST parser takes), ``retain_tool_grading``,
the search row ``SEARCHES``, ``job_progress.progress_information`` and the estimate table.

What is written here, because nothing existing serves: the vocabulary and checks of this episode's five actions, the walk
over the episode's own units that gives its state, ``search_view`` of the latest handoff (a relaunch after a fix is a
second handoff), the estimate recorded before the launch and the revision and resolution of it at each status request,
the fetch-and-grade of this service's report, and ``_observations`` (the hit references and comparison observations of
the graded report)."""
import hashlib
import json
import math
import posixpath

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    search_hits)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    compile_native_sheet, intervals)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    saved_grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_graders import (
    grade_blast_result)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_bvbrc import (
    DEFAULT_BASE_URL as DATA_BASE_URL)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_grading_inputs import (
    metadata_accounting)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.bvbrc_job_route import (
    NUCLEOTIDE_DATABASES, PRECOMPUTED_DATABASES, homology_job, report_names_database)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.duration_trend import duration_trend
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import checks, closure, job_rows
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import (
    find_reusable, record_product)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError, canonical)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search import blast_search
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    document as blast_document)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_hit_metadata import (
    BATCH, FAMILY_FIELDS, FEATURE_FIELDS, GENOME_FIELDS, SETTLE, lookup, name_hits, reference_metadata)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    CURVE_BASIS, FAILURE_CODES, SPACING, _choose, _ended, _failed, estimate_problems, failure_code, job_curve,
    ledger_estimate, now_text,
    search_facts, seconds_between, seconds_until_allowed, timing)

# The source's provider names the service that ran the search. The Store admits an observation carrying native BLAST
# rows from a source of this provider (``state.py``: ``NATIVE_BLAST_DATABASE_PROVIDERS``).
PROVIDER = 'bvbrc_homology'
SERVICE = 'bvbrc_homology'
JOB_NAME = 'bvbrc_blast'
QUERY_FILE = 'query.fasta'
REPORT = 'blast_out.raw.json'
ROUTE_KIND = 'bvbrc'
PRODUCT_KIND = 'sequence_search_results'
METADATA_PROVIDER = 'bvbrc_data'
METADATA_KIND = 'search_hit_metadata'
# The precomputed databases, by name as the application takes it (``db_precomputed_database``), with the unit of their
# sequences. Each was run against the live service before it was added (the design note records which).
DATABASES = {name: spec['unit'] for name, spec in PRECOMPUTED_DATABASES.items()}
# The set of databases an episode searches is its own: every function here that looks a database up takes it as
# ``databases``, ``{name: entry}`` with the entries of the route's lists (``bvbrc_job_route.PRECOMPUTED_DATABASES``, the
# protein databases, and ``bvbrc_job_route.NUCLEOTIDE_DATABASES``, the nucleotide databases; an entry's ``unit`` is the
# unit of its sequences). An episode that names no set searches ``PRECOMPUTED_DATABASES``, the databases of
# ``DATABASES``.
ACTIONS = ('estimate', 'launch', 'fix', 'monitor', 'extract')
STATES = ('no_estimate', 'estimated', 'launched', 'finished', 'extracted', 'failed')
UNTIL = ('launched', 'extracted')
ENDED_SEARCH_STATES = ('finished', 'failed', 'unknown')
# The unit a query's residues are counted in, by molecule.
MOLECULE_UNITS = {'protein': 'aa', 'dna': 'nt', 'rna': 'nt'}
ESTIMATE_BASES = ('learned_from_earlier_searches', CURVE_BASIS, 'no_earlier_measurement')
# The duration curve a search's measured jobs are fitted from (``jobs.duration_curve``), each kind (database and
# program) its own: seconds against the query's length, as the job rows record it.
DURATION_CURVE = {'constant': 10.0, 'powers': {'query_length': 1.0}}
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


def search_settings(program, database):
    """The settings of a search's report as a data product (closed JSON): the reuse key and the product's settings."""
    return {'application': 'Homology', 'program': program, 'database': database}


def reusable_search(reader, sequence_ref, program, database):
    """The held report product of exactly this query sequence, program and database, or ``None``."""
    return find_reusable(reader, PRODUCT_KIND, [sequence_ref], search_settings(program, database))


def record_search_product(store, *, handoff_ref, result_ref, query_ref, fields, workspace_path):
    """Label the fetched report ``result_ref`` as a ``sequence_search_results`` data product and return its row:
    generated by the job's handoff row, made from the query's sequence artifact, with the search's settings and its
    place in the BV-BRC workspace (the job's output folder, from the fetch's catalog)."""
    return record_product(
        store, artifact_ref=result_ref, kind=PRODUCT_KIND, generated_by=handoff_ref,
        used=[store.get(query_ref)['sequence_ref']], settings=search_settings(fields['program'], fields['database']),
        locations=[{'service': 'bvbrc_workspace', 'path': workspace_path}])


def metadata_settings():
    """The settings of the hit metadata as a data product (closed JSON): the data service, the fields asked of each
    collection, the batch and the settling step of the naming (``bvbrc_hit_metadata.name_hits``)."""
    return {'service': METADATA_PROVIDER, 'base_url': DATA_BASE_URL, 'batch': BATCH, 'settle': SETTLE,
            'fields': {'genome_feature': FEATURE_FIELDS, 'protein_family_ref': FAMILY_FIELDS, 'genome': GENOME_FIELDS}}


def record_metadata_product(store, *, metadata_ref, metadata_source_ref, result_ref, search_product_ref):
    """Label the hit metadata ``metadata_ref`` as a ``search_hit_metadata`` data product and return its row: generated by its
    source record (provider ``bvbrc_data``), made from the search's report (whose hits were named) and derived from the
    report's data product, with ``metadata_settings``."""
    return record_product(store, artifact_ref=metadata_ref, kind=METADATA_KIND, generated_by=metadata_source_ref,
                          used=[result_ref], derived_from=[search_product_ref], settings=metadata_settings())


def combinations(databases=PRECOMPUTED_DATABASES):
    """The (program, database) pairs the episode offers: each program that searches the unit of a database of
    ``databases`` (the set the episode searches)."""
    return [(program, database) for program, (_, unit, _) in sorted(PROGRAM_UNITS.items())
            for database, entry in databases.items() if entry['unit'] == unit]


LEDGER_ROWS = 500


def learned_statistics(table, query_length, now, databases=PRECOMPUTED_DATABASES):
    """What the estimate ledger has learned of each offered kind of search, by ``program:database`` (read through the
    table's read handle in a decision, whose time is ``now``): the short trend of its measured durations (``duration_trend``:
    how many were measured, their band and the latest ones), ``duration_curve`` (``bvbrc_job_child.job_curve``: the curve its
    measured searches make from ``DURATION_CURVE``, with its seconds for a query of ``query_length``), with ``ledger_estimate``
    (``bvbrc_job_child.ledger_estimate``): the basis and seconds an estimate of that kind of search must state. The
    kinds are the ``combinations`` of ``databases`` (the set the episode searches)."""
    found = {}
    for program, database in combinations(databases):
        kind = search_kind(program, database)
        trend = {key: value for key, value in duration_trend(table.read('rows', kind, LEDGER_ROWS)).items()
                 if key != 'size_fit'}
        curve = job_curve(table, kind, DURATION_CURVE, {'query_length': query_length}, now)
        found[program + ':' + database] = {
            **trend, 'duration_curve': curve,
            'ledger_estimate': ledger_estimate(trend, curve, 'learned_from_earlier_searches')}
    return found


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


def held_searches(reader, sequences, searched_types=('input',)):
    """The searches of the BV-BRC service the parent (the head) holds, from its job ledger rows: one row per handoff of a
    ``bvbrc`` job, with its request, its query (the held subject whose sequence artifact was staged), the state its latest
    held check showed (``submitted`` before any), whether it is outstanding (no closure held and not shown failed or lost)
    and the references of its handoff, status and closure rows: an outstanding search is continued by a later commission
    (``until`` ``extracted``). ``sequences`` is ``{subject record: its sequence artifact}``. ``searched_types`` are the
    record types a head searches: inputs only by default; a head that also searches sequences derived from its input (a
    translation, an extracted stretch: ``product`` records, each tied to the positions it came from by its ``mapping``)
    names them."""
    found = []
    for handoff in (row for row in job_rows(reader) if row['event'] == 'handoff' and row['detail']['kind'] == ROUTE_KIND
                    and row['detail']['estimates']['kind'].startswith(JOB_NAME + ':')):
        shown, ended = checks(reader, handoff['job']), closure(reader, handoff['job'])
        state = 'submitted' if not shown else shown[-1]['detail']['state']
        request = handoff['detail']['native']['request']
        (query,) = [ref for ref, artifact in sequences.items() if ref.split('_')[0] in searched_types
                    and artifact == handoff['detail']['input_refs'][QUERY_FILE]]
        found.append({'handoff_ref': handoff['id'], 'resource_id': handoff['detail']['resource_id'], 'query_ref': query,
                      'program': request['program'], 'database': request['database'], 'latest_state': state,
                      'closed': ended is not None, 'outstanding': ended is None and state not in ('failed', 'unknown'),
                      'known_ended': state in ENDED_SEARCH_STATES, 'launched_at': handoff['at'], 'check_refs': [row['id'] for row in shown],
                      'closure_refs': [] if ended is None else [ended['id']],
                      'estimated_seconds': handoff['detail']['estimates']['predicted_seconds'],
                      'estimate_basis': handoff['detail']['estimates']['duration_basis'],
                      'seconds_known_since_launch': (0.0 if not shown else seconds_between(handoff['at'], shown[-1]['at']))})
    return found


def search_notice(facts, revised_remaining=None):
    """The wait notice of a search that is launched and not extracted, as controlled numbers: the seconds since the launch
    as of the latest thing the holder knows (the launch, or its latest status request), the estimated total seconds and the
    expected remaining seconds: the estimate minus the seconds since the launch, not below zero, unless a status request
    came with a revised remaining time (``revised_remaining``), which is the later fact and stands. ``facts`` is
    ``search_facts``."""
    elapsed = 0.0 if facts['latest_check'] is None else facts['latest_check']['observed_seconds']
    estimated = facts['predicted_seconds']
    remaining = revised_remaining if revised_remaining is not None else max(estimated - elapsed, 0.0)
    return {'seconds_since_launch': elapsed, 'estimated_seconds': estimated, 'expected_remaining_seconds': remaining}


def resumed_rows(search):
    """The unit rows a passed-back search stands for in ``episode_state``: its estimate and launch (the estimate recorded
    with the launch, and the request the handoff records) and, when it holds status records, the state the latest shows."""
    handoff = search['handoff']
    request = handoff['detail']['native']['request']
    estimates = handoff['detail']['estimates']
    done = {'status': 'completed', 'failure_code': None, 'retryable': False}
    rows = [{'action': 'estimate', **done, 'estimate': {'program': request['program'], 'database': request['database'],
                                                         'expected_seconds': estimates['predicted_seconds'],
                                                         'basis': estimates['duration_basis']}},
            {'action': 'launch', **done, 'request': {'program': request['program'], 'database': request['database'],
                                                     'resource_id': handoff['detail']['resource_id']}}]
    if search['checks']:
        latest = search['checks'][-1]['detail']
        rows.append({'action': 'monitor', **done, 'state': latest['state'], 'result_available': latest['result_available'],
                     'waited_seconds': 0})
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
def _program_and_database_problems(program, database, query_molecule, databases):
    problems = []
    units = PROGRAM_UNITS[program]
    if units[0] != MOLECULE_UNITS[query_molecule]:
        problems.append(_choose('program', 'program_does_not_take_the_query_molecule', query_molecule=query_molecule,
                                choose_from=[name for name, (unit, *_) in PROGRAM_UNITS.items()
                                             if unit == MOLECULE_UNITS[query_molecule]]))
    if databases[database]['unit'] != units[1]:
        problems.append(_choose('database', 'database_does_not_hold_what_the_program_searches',
                                choose_from=[name for name, entry in databases.items() if entry['unit'] == units[1]]))
    return problems


def check_estimate(request, *, state, learned, query_molecule, databases=PRECOMPUTED_DATABASES):
    """``request``: ``program``, ``database``, ``expected_seconds``, ``basis``. The conditions: no search is running or
    waiting for a fix (an estimate is made before a launch, again to revise it, and again after a fix); the program
    takes the query's molecule and the database (one of ``databases``, the set the episode searches) holds what it
    searches; the seconds are in range; the estimate is the
    ledger's for this kind of search (``learned_statistics``' ``ledger_estimate``, which the decision shows): the basis says
    what it rests on (the duration curve of the measured searches of this kind, else their median,
    ``no_earlier_measurement`` only when it has none) and the seconds are the ledger's figure for it."""
    problems = _program_and_database_problems(request['program'], request['database'], query_molecule, databases)
    if state['state'] in ('launched', 'finished', 'failed'):
        problems.append(_choose('action', {'launched': 'search_running_monitor_it', 'finished': 'search_finished_extract_it',
                                           'failed': 'failure_needs_a_fix'}[state['state']]))
    if not ESTIMATE_RANGE[0] <= request['expected_seconds'] <= ESTIMATE_RANGE[1]:
        problems.append(_choose('expected_seconds', 'expected_seconds_out_of_range', minimum=ESTIMATE_RANGE[0],
                                maximum=ESTIMATE_RANGE[1]))
    trend = learned.get(request['program'] + ':' + request['database'])
    if trend is not None:
        problems.extend(estimate_problems(request, trend['ledger_estimate'], trend['measured'], 'measured_searches'))
    return problems


def check_launch(request, *, state, fields, query_molecule, resources, databases=PRECOMPUTED_DATABASES):
    """``request``: ``program``, ``database``, ``resource_id``. The conditions: an estimate is held (the gate: nothing
    is launched before one is made), for this program and database; the resource is a bound BV-BRC service; the program
    takes the query's molecule and the database (one of ``databases``, the set the episode searches) what it searches;
    no search is running, finished or extracted; the first
    request is the commission's, and after a failure only after a fix, with a request that differs from the failed one
    in the field the fix named."""
    problems = _program_and_database_problems(request['program'], request['database'], query_molecule, databases)
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


def check_commission(request, *, programs, sequences, scope_subjects, resources, searches,
                     databases=PRECOMPUTED_DATABASES):
    """The things to fix in the head's commission of this episode (``request``: ``query_ref``, ``program``,
    ``database``, ``resource_id``, ``until``), before any child is commissioned. ``programs`` are the programs the
    commissioning episode offers (those its own credit can score) and ``databases`` the set of databases it searches.
    ``sequences`` is ``{record: molecule}``, ``searches``
    is ``held_searches``.
    The conditions: the query is a sequence of the scope; the program takes its molecule; the database holds what the
    program searches; the resource is a bound BV-BRC service; a search of the query held outstanding is continued: the
    same program, database and resource, and ``until`` ``extracted`` (a continuation submits nothing)."""
    query, program, database = request['query_ref'], request['program'], request['database']
    problems = []
    if program not in programs:
        problems.append(_choose('program', 'program_is_not_offered', choose_from=list(programs)))
    if query not in scope_subjects:
        problems.append(_choose('query_ref', 'query_is_not_a_sequence_of_the_scope',
                                choose_from=[ref for ref in scope_subjects if ref in sequences]))
    problems.extend(_program_and_database_problems(program, database, sequences[query], databases))
    if resources.get(request['resource_id']) != ROUTE_KIND:
        problems.append(_choose('resource_id', 'resource_is_not_a_bvbrc_service',
                                choose_from=[name for name, kind in resources.items() if kind == ROUTE_KIND]))
    held = [search for search in searches if search['query_ref'] == query]
    for search in held:
        same = (search['program'], search['database'], search['resource_id']) == (program, database,
                                                                                    request['resource_id'])
        if search['outstanding'] and not same:
            problems.append(_choose('program', 'commission_must_continue_the_outstanding_search',
                                    program=search['program'], database=search['database'],
                                    resource_id=search['resource_id']))
        if search['outstanding'] and same and request['until'] != 'extracted':
            problems.append(_choose('until', 'a_continuation_follows_the_search_to_its_result', choose_from=['extracted']))
    return problems


# -- the tools --------------------------------------------------------------------------------------------------------
def record_estimate(ctx, *, estimate):
    """The estimate the model committed, as the outcome of its unit. Nothing is written on the estimate table here: the
    table gets ONE expectation per launch, written by ``launch_search`` just before the submission, so a revised estimate
    or an estimate made when no launch can follow leaves no row."""
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': [], 'estimate': dict(estimate)}


def launch_search(ctx, *, request, estimate, sequence_ref, databases=PRECOMPUTED_DATABASES):
    """One submission of the search the held estimate was made for. The expectation is recorded on the estimate table
    first (one row per launch, keyed by the launch's job handle, kept in the handoff row so the status requests resolve
    it); a failed submission resolves it with that outcome. ``databases`` is the set of databases the episode searches:
    the job is of that set (``bvbrc_job_route.homology_job``)."""
    access, table = ctx.services['job_access'], ctx.services['estimate_table']
    job = homology_job(request['program'], request['database'], QUERY_FILE, databases)
    handle = job_handle(ctx.operation_key, request['resource_id'], JOB_NAME)
    started = now_text()
    table.expect(search_kind(request['program'], request['database']),
                 {'gain': {'value': 0.0, 'lower': 0.0, 'upper': 0.0}, 'cost': 0.0,
                  'duration_seconds': estimate['expected_seconds'], 'duration_basis': estimate['basis'],
                  'job': {'service': SERVICE, 'program': request['program'], 'database': request['database'],
                          'query_length': len(ctx.store.get_artifact(sequence_ref).decode('ascii').strip())}},
                 key=handle, at=started)
    launched = access.launch(ctx, request['resource_id'], job, inputs={QUERY_FILE: sequence_ref}, name=JOB_NAME,
                             estimates={'kind': search_kind(request['program'], request['database']),
                                        'estimate_key': handle,
                                        'predicted_seconds': estimate['expected_seconds'],
                                        'duration_basis': estimate['basis']})
    if launched['status'] != 'completed':
        failure = launched['failure']
        _ended(table, handle, 'submit_failed:' + failure_code(failure['code']),
               seconds_between(started, now_text()))
        return {**_failed(failure['code'], False, sent=failure['detail'].get('sent'),
                          http_status=failure['detail'].get('http_status'),
                          rpc_error=failure['detail'].get('rpc_error')), 'handoff_refs': [], 'request': dict(request)}
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'handoff_refs': [launched['handoff_ref']],
            'record_refs': [launched['handoff_ref'], launched['reply_ref']], 'request': dict(request),
            'predicted_seconds': estimate['expected_seconds'], 'duration_basis': estimate['basis'],
            'submitted_at': launched['submitted_at']}


def _service_seconds(store, reply_ref):
    """The seconds the service's own task record gives from the submission of the job to its completion (its
    ``submit_time`` and ``completed_time``, UTC), or ``None`` when the record names no completion time. The reply of
    the status request is the source artifact of the check row."""
    reply = json.loads(store.get_artifact(reply_ref))
    if not reply.get('submit_time') or not reply.get('completed_time'):
        return None
    return seconds_between(*(reply[name].replace(' ', 'T') + '+00:00' for name in ('submit_time', 'completed_time')))


async def monitor_search(ctx, *, handoff_ref, wait_seconds, expected_remaining_seconds):
    """One status request of the held search after the wait (the existing wait helper). What it shows is kept as a check
    row. The estimate is updated: while the search has not ended, the model's revised expected remaining seconds are
    kept in this unit's outcome (not on the ledger, which holds one row per launch); the first request that shows the
    search ended (or a failed request) resolves the launch's row, so the next search of the kind learns from it. The
    duration recorded is the service's own: its task record's completion time minus its submission time
    (``_service_seconds``). The seconds from the submission to this observation are kept beside it as
    ``observed_seconds``: they depend on when this unit asked, and are not the duration of the search."""
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
    if checked['state'] in ENDED_SEARCH_STATES:
        observed = seconds_between(handoff['at'], checked['observed_at'])
        measured = _service_seconds(ctx.store, checked['reply_ref'])
        table.resolve(estimates['estimate_key'], {
            'gain': 0.0, 'cost': 0.0, 'outcome': checked['state'], 'observed_seconds': observed,
            'duration_seconds': observed if measured is None else measured,
            'duration_source': 'first_status_showing_the_end' if measured is None else 'service_task_record'},
            at=now_text())
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'state': checked['state'],
            'result_available': checked['result_available'], 'check_ref': checked['check_ref'],
            'record_refs': [checked['check_ref'], checked['reply_ref']], 'waited_seconds': checked['waited_seconds'],
            'expected_remaining_seconds': expected_remaining_seconds}


def _grading(store, result_ref, fields, query_ref, sequence, metadata, databases):
    """The grading of the fetched report into the database sheet of the original query, with the hits' reference
    metadata: a report of another query or database is refused (``ValueError`` with its code). The report names its
    database by the file the service searched (``search_target.db``): its last path component is the database's file
    (``bvbrc_job_route.report_names_database``, with the database's entry of ``databases``)."""
    operand = {'subject_ref': query_ref, 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
               'database': fields['database']}
    grading = grade_blast_result(store.get_artifact(result_ref), mode='database', resource='api',
                                 output_format='json2', request=operand, reference_metadata=metadata,
                                 _retain_correspondence=True)
    normalized = grading['sheet']['normalized_result']
    if normalized['mode'] != 'database' or normalized['query']['length'] != len(sequence):
        raise ValueError('result_of_another_query')
    if not report_names_database(posixpath.basename(normalized['search']['database']), databases[fields['database']]):
        raise ValueError('result_of_another_database')
    return grading


def _accessions(report):
    """The accession of the first description of each hit of the report, in hit order (``accession``, else ``id``)."""
    found = []
    for hit in blast_document(report)['search'].get('hits', []):
        first = (hit.get('description') or [{}])[0]
        found.append(first.get('accession') or first.get('id'))
    return found


def _named(report, rows):
    """The report with each hit's title set to the product its metadata row names (the label of its reference record);
    only the copy given to the reference records is changed, never the stored report or the grading."""
    document = json.loads(report)
    products = {row['accession']: row['functions'][0]['function'] for row in rows if row['functions']}
    for entry in document['BlastOutput2']:
        for hit in entry['report']['results']['search'].get('hits', []):
            first = hit['description'][0]
            first['title'] = products.get(first.get('accession') or first.get('id'), first.get('title'))
    return json.dumps(document).encode()


def ordered_hits(report, grading, length):
    """The hits of the report as ``[(accession, value)]``, highest value first, ties by accession: the per-hit value is the
    one the head's credit reads (``candidate_measurements.search_hits``: the subscore of the hit's alignments over the whole
    query). ``grading`` is the grading of the report (with or without reference metadata)."""
    regions = intervals([[0, length]], length=length)
    accessions = _accessions(report)
    rows = search_hits(grading, lambda rows_: compile_native_sheet(rows_, supplied_length=length, regions=regions)['value'])
    return sorted(((accessions[row['hit_index']], row['value']) for row in rows), key=lambda pair: (-pair[1], pair[0]))


def _observations(store, report, grading, grading_ref, result_ref, source_ref, query_ref, program, query_length):
    """One ``reference`` record for each hit of the report and one ``comparison`` observation for each of its
    alignments, projected from the already graded cell of the sheet (nothing is calculated or graded again), with the
    address of that cell and the grading artifact on its source: what the A101 native-correspondence projection reads
    (``native_correspondence.read_details`` scores the graded cell of each held ``comparison`` observation), in the shape the
    registry's ``_import_blast`` gives them (without its taxon terms and processing context). An alignment that
    cannot be projected is counted, never hidden: ``(observation refs, reference refs, unprojected alignment count)``."""
    _, reference_unit, model_unit = blast_search.PROGRAM_UNITS[program]
    parsed = blast_search.document(report)
    observations, references, unprojected = [], [], 0
    for hit_index, hit in enumerate(parsed['search'].get('hits', [])):
        first = (hit.get('description') or [{}])[0]
        accession = first.get('accession') or first.get('id')
        reference = store.put('reference', {
            'reference_type': 'protein' if reference_unit == 'aa' else 'sequence', 'source_ref': source_ref,
            'accession': accession, 'label': first.get('title') or accession, 'sequence_ref': None,
            'molecule': 'protein' if reference_unit == 'aa' else 'unspecified',
            'length': blast_search.integer(hit['len'], 'hit_length', minimum=1), 'term_refs': [],
            'context_refs': []}, origin='external')
        references.append(reference['id'])
        for hsp_index, native in enumerate(hit.get('hsps', [])):
            try:
                component, address = blast_search.shared_hsp_component(grading, hit_ordinal=hit_index,
                                                                       hsp_ordinal=hsp_index)
                row = blast_search.hsp_row(native, component=component, program=program, query_length=query_length,
                                           reference_length=hit['len'], hit_ordinal=hit_index, hsp_ordinal=hsp_index)
            except (ValueError, TypeError, KeyError):
                unprojected += 1
                continue
            row['native_blast']['shared_projection'] = {
                'version': blast_search.HSP_PROJECTION_VERSION, 'grading_artifact_ref': grading_ref,
                'native_artifact_ref': result_ref, **address}
            (start, end), (reference_start, reference_end) = row['query_interval'], row['reference_interval']
            observations.append(store.put('observation', {
                'kind': 'comparison', 'subject_refs': [query_ref], 'source_subject_refs': [reference['id']],
                'source_ref': source_ref, 'anchor': None,
                'measurements': measurements(reference_ref=ref(reference['id']),
                                             **{name: number(value) for name, value in row['measurements'].items()}),
                'dependencies': [query_ref, reference['id']],
                'operand_intervals': [
                    {'role': 'query', 'subject_ref': query_ref, 'start': start, 'end': end,
                     'unit': store.subject_unit(query_ref),
                     'model_unit': model_unit},
                    {'role': 'reference', 'subject_ref': reference['id'], 'start': reference_start,
                     'end': reference_end, 'unit': store.subject_unit(reference['id']),
                     'model_unit': model_unit}],
                'native_blast': row['native_blast']}, origin='tool')['id'])
    return observations, references, unprojected


def fetch_and_grade_search(ctx, *, handoff_ref, fields, query_ref, databases=PRECOMPUTED_DATABASES, order=ordered_hits):
    """Fetch the report of the finished search, learn what its hits are from BV-BRC's data service
    (``bvbrc_hit_metadata``) and grade the report with that as reference metadata, all in the same unit, kept through
    custody: the grading artifact, a source of the provider over the fetched report, the search row that enters the search into the A101 sheet's tool profile, one
    reference record per hit (its accession and, where the service named it, its product as label) and one comparison
    observation per alignment (what the head's credit reads), and the metadata the hits were graded with (an artifact
    with BV-BRC's field names, and its source); the report, the metadata and the grading are labelled as data products
    (``sequence_search_results``, ``search_hit_metadata``, ``tool_grading_sheet``). A hit with no metadata is counted as missing by
    ``metadata_accounting``. No step stands between the fetch and the grading. ``databases`` is the set of databases the
    episode searches: the report is checked to be of the database of ``fields`` by that database's entry of the set.
    ``order`` gives the order in which the hits are named, as ``order(report, grading, query length) -> [(accession,
    value)]``, highest value first: by default the value the sequence homology head's credit reads (``ordered_hits``,
    which reads protein-to-protein alignments only); an episode that searches with other programs names its own."""
    store = ctx.store
    fetched = ctx.services['job_access'].fetch(ctx, handoff_ref, names=[REPORT])
    if fetched['status'] != 'completed':
        return {**_failed(fetched['failure']['code'], False), 'closure_ref': None}
    (result_ref,) = [item['ref'] for item in fetched['results'] if item['name'] == REPORT]
    report = store.get_artifact(result_ref)
    sequence = store.get_artifact(store.get(query_ref)['sequence_ref']).decode('ascii').upper()
    try:
        ordered = order(report, _grading(store, result_ref, fields, query_ref, sequence, [], databases), len(sequence))
    except (ValueError, ContractError) as error:
        code = str(error) if str(error) in FAILURE_CODES else 'grading_refused'
        return {**_failed(code, False, reason=str(error)), 'closure_ref': fetched['closure_ref']}
    found = name_hits(ordered)
    rows = reference_metadata(found)
    try:
        grading = _grading(store, result_ref, fields, query_ref, sequence, rows, databases)
    except (ValueError, ContractError) as error:
        code = str(error) if str(error) in FAILURE_CODES else 'grading_refused'
        return {**_failed(code, False, reason=str(error)), 'closure_ref': fetched['closure_ref']}
    normalized = grading['sheet']['normalized_result']
    accounting = metadata_accounting(normalized, rows)
    (path,) = [item['workspace_path'] for item in json.loads(store.get_artifact(fetched['reply_ref']))['catalog']
               if item['name'] == REPORT]
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=result_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': result_ref, 'text_ref': None,
            'request_ref': None, 'version': normalized['search']['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref]}, origin='tool')
        metadata_ref = store.artifact(canonical({key: found[key] for key in (
            'features', 'families', 'genomes', 'requests', 'failures', 'responses', 'duplicate_feature_ids',
            'naming')}), 'application/json')
        metadata_source = store.put('source', {
            'provider': METADATA_PROVIDER, 'accession': None, 'uri': DATA_BASE_URL, 'artifact_ref': metadata_ref,
            'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None,
            'auxiliary_artifact_refs': [], 'operand_refs': [query_ref]}, origin='tool')
        search = store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': query_ref, 'profile': 'blast'})
        observations, references, unprojected = _observations(
            store, _named(report, rows), grading, grading_ref, result_ref, source['id'], query_ref,
            fields['program'], len(sequence))
        product = record_search_product(store, handoff_ref=handoff_ref, result_ref=result_ref, query_ref=query_ref,
                                        fields=fields, workspace_path=path)
        metadata_product = record_metadata_product(store, metadata_ref=metadata_ref, metadata_source_ref=metadata_source['id'],
                                                   result_ref=result_ref, search_product_ref=product['id'])
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[result_ref, metadata_ref],
                                                 derived_from=[product['id'], metadata_product['id']])
    refs = [source['id'], grading_ref, search['id'], metadata_source['id'], product['id'], metadata_product['id'],
            grading_product['id'], *references, *observations]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'closure_ref': fetched['closure_ref'],
            'graded_refs': refs, 'record_refs': [*refs, fetched['closure_ref']], 'product_ref': product['id'],
            'hit_count': len(grading['sheet']['hits']), 'observation_count': len(observations),
            'unprojected_alignment_count': unprojected, 'metadata_covered_count': accounting['covered_count'],
            'metadata_hit_count': accounting['hit_accession_count'], 'metadata_request_count': found['requests'],
            'metadata_failure_count': len(found['failures']), 'metadata_complete': accounting['complete'],
            'named_hit_count': found['naming']['named'], 'not_asked_hit_count': found['naming']['not_asked'],
            'naming_batch_count': found['naming']['batches'], 'naming_stopped': found['naming']['stopped']}


__all__ = ['ACTIONS', 'DATABASES', 'NUCLEOTIDE_DATABASES', 'PRECOMPUTED_DATABASES', 'ESTIMATE_BASES', 'ESTIMATE_RANGE', 'FAILURE_CODES', 'PROVIDER', 'REQUEST_FIELDS',
           'PRODUCT_KIND', 'METADATA_KIND', 'ROUTE_KIND', 'STATES', 'WAIT_RANGE_MAX', 'check_commission', 'check_estimate', 'held_searches', 'resumed_rows', 'search_notice', 'UNTIL', 'ENDED_SEARCH_STATES',
           'check_extract', 'check_fix', 'check_launch', 'check_monitor', 'combinations', 'episode_state',
           'fetch_and_grade_search', 'graded_rows', 'launch_search', 'learned_statistics', 'minimum_wait',
           'metadata_settings', 'monitor_search', 'record_estimate', 'record_metadata_product', 'record_search_product', 'reusable_search', 'search_facts', 'search_settings', 'search_kind', 'search_view', 'timing']
