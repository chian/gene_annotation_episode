"""One database search through the BV-BRC application service (the ``Homology`` application), as the actions of the
``bvbrc_blast`` episode: the checks of the model's filled JSON (``check_*``) and the tools that run when a check passes
(``submit_search``, ``fetch_and_grade_search``; the status request is ``database_blast_search.check_search``, called as it
is), plus the readers of what the episode holds (``held_searches``, ``graded_rows``).

The rules are those of ``database_blast_search`` (read its docstring): every action has ONE deterministic check over the
model's filled JSON and what the episode holds, returning the things to fix; a tool that runs after a passed check
simply works and a failure then is the environment's, reported once as ``failed`` with a code of the fixed vocabulary
``database_blast_search.FAILURE_CODES`` (the route, ``jobs/bvbrc_job_route.py``, uses those codes and keeps the
service's own error in the detail).

What exists and is called, not written again: the route and its spacing (``bvbrc_job_route``), ``JobAccess.launch``,
``fetch`` (rows in custody), ``database_blast_search``: ``check_search`` (the status request and the duration
measurement; nothing in it is specific to a service), ``check_status_request``, ``check_fetch_request``, ``check_hold``,
``search_view``, ``search_state``, ``search_facts``, ``seconds_until_allowed``, ``timing``, ``failure_code``,
``now_text``, ``seconds_between``, ``_failed``, ``_ended`` and ``_observations`` (the hit references and comparison
observations of a graded report, which are not specific to a service either: imported, not copied), the grader
(``grade_blast_result``: the report of ``blast_formatter -outfmt 15`` is the single-query JSON15 the BLAST parser takes),
``retain_tool_grading``, the search row ``SEARCHES`` and the estimate table.

What is written here, because nothing existing serves: the vocabulary and the checks that name this service's values
(no hit-list size: the deployed ``Homology`` definition takes none; the resource is a ``bvbrc`` route), the submission
with its duration prediction (the job form differs from the public service's, which ``checked_analysis_kind`` reads),
the held-search reader for the ``bvbrc`` route and the fetch-and-grade of this service's report (its file name and its
database name differ)."""
import hashlib
import json
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
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    FAILURE_CODES, HOLD_REASONS, MOLECULE_UNITS, STATES, STATUS_FIELDS, _choose, _ended, _failed, _observations,
    check_fetch_request, check_hold, check_search, check_status_request, failure_code, latest_check, now_text,
    search_facts, search_state, search_view, seconds_between, seconds_until_allowed, timing)

PROVIDER = 'bvbrc_blast'
SERVICE = 'bvbrc_homology'
JOB_NAME = 'bvbrc_blast'
QUERY_FILE = 'query.fasta'
REPORT = 'blast_out.raw.json'
# The precomputed databases, by name as the application takes it (``db_precomputed_database``), with the unit of their
# sequences. Each was run against the live service before it was added (the design note records which).
DATABASES = {name: spec['unit'] for name, spec in PRECOMPUTED_DATABASES.items()}
ROUTE_KIND = 'bvbrc'


def search_kind(program, database):
    """The kind a search is recorded under in the estimate table: later searches of the same service, database and
    program read what earlier ones measured."""
    return 'bvbrc_blast:' + SERVICE + ':' + database + ':' + program


# -- what the episode holds -----------------------------------------------------------------------------------------
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


def held_searches(reader, sequences):
    """The searches of the BV-BRC service the parent (the head) holds, from its job ledger rows: one row per handoff of
    a ``bvbrc`` job, with its request, its query (the held subject whose sequence artifact was staged), the state its
    latest held check showed (``submitted`` before any), whether it is outstanding (no closure held and not shown failed
    or lost) and the references of its handoff, status and closure rows. ``sequences`` is ``{subject record: its
    sequence artifact}``."""
    found = []
    for handoff in (row for row in job_rows(reader) if row['event'] == 'handoff' and row['detail']['kind'] == ROUTE_KIND):
        shown, ended = checks(reader, handoff['job']), closure(reader, handoff['job'])
        state = 'submitted' if not shown else shown[-1]['detail']['state']
        request = handoff['detail']['native']['request']
        (query,) = [ref for ref, artifact in sequences.items() if artifact == handoff['detail']['input_refs'][QUERY_FILE]]
        found.append({'handoff_ref': handoff['id'], 'resource_id': handoff['detail']['resource_id'], 'query_ref': query,
                      'program': request['program'], 'database': request['database'], 'latest_state': state,
                      'closed': ended is not None, 'outstanding': ended is None and state not in ('failed', 'unknown'),
                      'check_refs': [row['id'] for row in shown],
                      'closure_refs': [] if ended is None else [ended['id']]})
    return found


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


def check_submit(request, *, fields, query_molecule, resources, search, failures):
    """``request`` holds ``program``, ``database``, ``resource_id``. The conditions, each one problem with the field it
    concerns: the resource is a bound BV-BRC service; each value is the commission's; the program takes the query's
    molecule; the database holds what the program searches; no search is held; no earlier submission failed (a failure
    after a passed check is the environment's and not retried)."""
    problems = []
    if resources.get(request['resource_id']) != ROUTE_KIND:
        problems.append(_choose('resource_id', 'resource_is_not_a_bvbrc_service',
                                choose_from=[name for name, kind in resources.items() if kind == ROUTE_KIND]))
    for name in ('program', 'database', 'resource_id'):
        if request[name] != fields[name]:
            problems.append(_choose(name, 'differs_from_the_commission', commission=fields[name]))
    problems.extend(_program_and_database_problems(request['program'], request['database'], query_molecule))
    if search is not None:
        problems.append(_choose('action', 'search_already_held'))
    if failures and any(not retryable for _, retryable in failures):
        problems.append(_choose('action', 'submission_already_failed_and_cannot_be_retried'))
    return problems


def check_commission(request, *, programs, sequences, scope_subjects, resources, searches, failed):
    """The things to fix in the head's commission of this episode (``request``: ``query_ref``, ``program``,
    ``database``, ``resource_id``), before any child is commissioned. ``programs`` are the programs the commissioning
    episode offers (those its own credit can score). ``sequences`` is ``{record: molecule}``, ``searches`` is
    ``held_searches`` and ``failed`` the commissions (query, program, database) whose child reported the search failed.
    The conditions: the query is a sequence of the scope; the program takes its molecule; the database holds what the
    program searches; the resource is a bound BV-BRC service; a search of the query held outstanding is continued (its
    program, database and resource, no other); a search already closed or already failed is not commissioned again."""
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
    for held in searches:
        if held['query_ref'] != query:
            continue
        same = (held['program'], held['database'], held['resource_id']) == (program, database, request['resource_id'])
        if held['outstanding'] and not same:
            problems.append(_choose('program', 'commission_must_continue_the_outstanding_search',
                                    program=held['program'], database=held['database'],
                                    resource_id=held['resource_id']))
        if held['closed'] and same:
            problems.append(_choose('database', 'search_already_held'))
    if (query, program, database) in failed:
        problems.append(_choose('database', 'search_already_failed_and_cannot_be_retried'))
    return problems


# -- the tools --------------------------------------------------------------------------------------------------------
def submit_search(ctx, *, request, sequence_ref):
    """One submission, with the duration predicted first (from the measured durations of earlier searches of the same
    kind, or none), recorded on the estimate table before the route is contacted."""
    access, table = ctx.services['job_access'], ctx.services['estimate_table']
    job = {'program': request['program'], 'database': request['database'], 'query_file': QUERY_FILE}
    handle = job_handle(ctx.operation_key, request['resource_id'], JOB_NAME)
    kind = search_kind(request['program'], request['database'])
    learned = table.kind_statistics(kind)['duration_seconds']
    predicted = None if learned is None else learned['typical']
    basis = 'no_earlier_measurement' if learned is None else 'median_of_measured_durations_of_this_kind'
    started = now_text()
    table.expect(kind, {'gain': {'value': 0.0, 'lower': 0.0, 'upper': 0.0}, 'cost': 0.0,
                        'duration_seconds': predicted, 'duration_basis': basis}, key=handle, at=started)
    launched = access.launch(ctx, request['resource_id'], job, inputs={QUERY_FILE: sequence_ref}, name=JOB_NAME,
                             estimates={'kind': kind, 'estimate_key': handle, 'predicted_seconds': predicted,
                                        'duration_basis': basis})
    if launched['status'] != 'completed':
        failure = launched['failure']
        _ended(table, handle, 'submit_failed:' + failure_code(failure['code']), seconds_between(started, now_text()))
        return {**_failed(failure['code'], False, sent=failure['detail'].get('sent'),
                          http_status=failure['detail'].get('http_status'),
                          rpc_error=failure['detail'].get('rpc_error')), 'handoff_refs': []}
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'handoff_refs': [launched['handoff_ref']],
            'record_refs': [launched['handoff_ref'], launched['reply_ref']], 'predicted_seconds': predicted,
            'duration_basis': basis, 'submitted_at': launched['submitted_at']}


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


__all__ = ['DATABASES', 'FAILURE_CODES', 'HOLD_REASONS', 'PROVIDER', 'ROUTE_KIND', 'STATES', 'STATUS_FIELDS',
           'check_commission', 'check_fetch_request', 'check_hold', 'check_search', 'check_status_request',
           'check_submit', 'fetch_and_grade_search', 'graded_rows', 'held_searches', 'latest_check', 'search_facts',
           'search_kind', 'search_state', 'search_view', 'seconds_until_allowed', 'submit_search', 'timing']
