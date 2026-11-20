"""One database search of the public NCBI BLAST service, as the actions of the ``database_blast`` episode: the checks
of the model's filled JSON (``check_*``), and the three tools that run when a check passes (``submit_search``,
``check_search``, ``fetch_and_grade_search``), plus the readers of what the episode holds (``search_view``,
``search_state``, ``seconds_until_allowed``, ``graded_rows``).

Every action has ONE deterministic check over the model's JSON and what the episode holds. It returns the things to
fix (each a ``field`` and a ``code``, and what to choose from); an empty list means the action can run, and the
episode's ``action`` rejects anything else before a unit is made. A tool that runs after a passed check simply works:
a failure then is a fault of the environment, returned once as a ``failed`` outcome with a code of the fixed
vocabulary ``FAILURE_CODES`` and ``retryable`` false. The one exception is the service's spacing refusal of a
status request (``provider_spacing_required``: nothing was sent), which is retryable.

What exists and is called, not written again: the route and its spacing (``api_job_route``), ``JobAccess.launch``,
``check`` and ``fetch`` (rows in custody), ``job_wait.wait_for_job`` (the wait of a check), ``job_records`` (the
rows), the kind (``blast_analysis_kind.checked_analysis_kind``), the grader (``grade_blast_result``, database mode),
``retain_tool_grading``, the search row ``SEARCHES``, the feature reader ``blast_database_features`` and the estimate
table (``episode_runtime.estimate_table``).

What is written here, because nothing existing does it:

* the checks and the three tools above (compositions of the existing functions);
* the prediction and the measurement of a search's duration on the estimate table. Before a submission the
  expectation is recorded with the duration predicted from the measured durations of earlier searches of the same
  kind (``search_kind``: the service, the database and the program), or without a duration (``duration_basis``
  ``no_earlier_measurement``) when none exists: the service's own estimate (RTOE) is only known from its reply to the
  submission, so it is kept beside the prediction in the handoff row and shown to the model. When a status request
  first shows the search ended, or the service cannot be reached, the duration from the submission to that
  observation is recorded as the resolution of the expectation (``duration_seconds``), so the next search of the
  kind is predicted from it. The estimate table never enters credit and nothing here is a deadline.
"""
from datetime import datetime, timezone
import hashlib
import json

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    checked_analysis_kind)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    saved_grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_graders import (
    grade_blast_result)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import checks, closure, job_rows
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search import blast_search
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)

PROVIDER = 'ncbi_blast'
SERVICE = 'ncbi_blast'
JOB_NAME = 'database_blast'
QUERY_FILE = 'query.fasta'
REPORT = 'blast_result.json'
ANALYSIS_KIND = 'database_search'
# The unit a query's residues are counted in, by molecule.
MOLECULE_UNITS = {'protein': 'aa', 'dna': 'nt', 'rna': 'nt'}
# The hosted databases the episode offers, by name as the service spells it, with the unit of their sequences. The
# service documents ``swissprot`` and ``core_nt`` as its examples of the DATABASE parameter
# (https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html, read 2026-11-20); a name is added here only when the
# documentation names it.
DATABASES = {'swissprot': 'aa', 'core_nt': 'nt'}
HITLIST_RANGE = (1, 200)
STATES = ('not_submitted', 'outstanding', 'finished', 'graded', 'failed')
HOLD_REASONS = ('search_not_finished', 'failure_not_retryable', 'graded_result_established')
HOLD_REASON_OF_STATE = {'outstanding': 'search_not_finished', 'failed': 'failure_not_retryable',
                        'graded': 'graded_result_established'}
STATUS_FIELDS = ('execution_status', 'result_available')
FAILURE_CODES = (
    'provider_spacing_required', 'provider_connection_failed', 'provider_request_timeout', 'provider_http_error',
    'provider_redirect_not_followed', 'provider_submission_response_invalid', 'provider_status_response_invalid',
    'provider_result_response_invalid', 'submission_outcome_unknown', 'results_not_available', 'job_state_unknown',
    'result_file_missing', 'result_not_in_catalog', 'service_reported_failed', 'service_lost_the_job',
    'grading_refused', 'result_of_another_query', 'result_of_another_database')
SPACING = 'provider_spacing_required'
# The service stamps its last contact a few milliseconds after the time a row carries; the wait of a check adds this.
CLOCK_MARGIN_SECONDS = 1.0
ENDED_STATES = ('finished', 'failed', 'unknown')


def failure_code(code):
    """A code of the route as a value of the fixed vocabulary (the HTTP status of ``provider_http_<n>`` is dropped)."""
    if code.startswith('provider_http_'):
        return 'provider_http_error'
    if code not in FAILURE_CODES:
        raise ValueError('database_blast_failure_code_not_in_the_vocabulary:' + code)
    return code


def now_text():
    return datetime.now(timezone.utc).isoformat()


def seconds_between(earlier, later):
    return (datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).total_seconds()


def search_kind(program, database):
    """The kind a search is recorded under in the estimate table: later searches of the same service, database and
    program read what earlier ones measured."""
    return 'database_blast:' + SERVICE + ':' + database + ':' + program


# -- what the episode holds -----------------------------------------------------------------------------------------
def search_view(reader):
    """The one search the episode holds, from its job ledger rows: ``{'handoff', 'checks', 'closure'}`` (rows), or
    ``None`` while it holds no handoff. A second handoff is an error: the check of ``submit`` refuses it."""
    handoffs = [row for row in job_rows(reader) if row['event'] == 'handoff']
    if not handoffs:
        return None
    (handoff,) = handoffs
    return {'handoff': handoff, 'checks': checks(reader, handoff['job']), 'closure': closure(reader, handoff['job'])}


def graded_rows(reader):
    """The graded searches the episode holds: one row per held source of the provider, with the grading artifact
    and the controlled features the feature reader gives, and the hit count of the sheet."""
    rows = []
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        grading_ref = source['auxiliary_artifact_refs'][0]
        grading = json.loads(reader.get_artifact(grading_ref))['grading']
        rows.append({'source_ref': source['id'], 'grading_ref': grading_ref, 'hit_count': len(grading['sheet']['hits']),
                     'features': saved_grading_features(reader, grading_ref)})
    return rows


def latest_check(search):
    return search['checks'][-1] if search['checks'] else None


def search_state(search, graded, failures):
    """The state of the search, from the fixed ``STATES``, and its last failure code (``None`` when none).
    ``failures`` are the codes and retryability of the units that failed, in order: ``[(code, retryable)]``.
    Graded wins; then failed (a service that reported the search failed or lost, or a unit that failed and cannot be
    retried); then finished (the latest check shows it ended with results); then outstanding."""
    last = None
    if search is not None and latest_check(search) is not None:
        state = latest_check(search)['detail']['state']
        last = {'failed': 'service_reported_failed', 'unknown': 'service_lost_the_job'}.get(state)
    unrepaired = [code for code, retryable in failures if not retryable]
    last = unrepaired[-1] if unrepaired else last
    if graded:
        return 'graded', last
    if search is None:
        return ('failed', last) if unrepaired else ('not_submitted', None)
    shown = latest_check(search)
    if unrepaired or (shown is not None and shown['detail']['state'] in ('failed', 'unknown')):
        return 'failed', last
    if shown is not None and shown['detail']['state'] == 'finished' and shown['detail']['result_available']:
        return 'finished', last
    return 'outstanding', last


def search_facts(search):
    """The held search as controlled facts (``None`` while none is held): its records, the prediction recorded with
    its submission, the service's own estimate and its latest check (with the seconds from the submission to it)."""
    if search is None:
        return None
    handoff, shown = search['handoff'], latest_check(search)
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
    """Seconds until the service allows the next status request of the held search (0.0 when now): the longer of
    the spacing between two contacts, from the latest contact (the submission or the latest check), and the spacing
    between two status requests of one job, from the latest check (``description`` is the resource's, with both
    spacings; ``facts`` is ``search_facts``)."""
    shown = facts['latest_check']
    last = facts['submitted_at'] if shown is None else shown['observed_at']
    remaining = description['request_spacing_seconds'] - seconds_between(last, now)
    if shown is not None:
        remaining = max(remaining, description['poll_spacing_seconds'] - seconds_between(shown['observed_at'], now))
    return max(0.0, remaining)


def timing(facts, now):
    """The controlled facts of the search's duration as of ``now``: what was predicted (from the learned durations
    when the search was submitted, or none), the service's own estimate, the seconds since the submission, and how
    far past each the search is (negative: before it)."""
    elapsed = seconds_between(facts['submitted_at'], now)
    predicted, service = facts['predicted_seconds'], facts['service_estimate_seconds']
    return {'seconds_since_submission': elapsed, 'predicted_seconds': predicted,
            'prediction_basis': facts['prediction_basis'], 'service_estimate_seconds': service,
            'seconds_past_prediction': None if predicted is None else elapsed - predicted,
            'seconds_past_service_estimate': None if service is None else elapsed - service}


# -- the checks: the things to fix in the model's JSON ----------------------------------------------------------------
def _choose(field, code, **detail):
    return {'field': field, 'code': code, **detail}


def check_submit(request, *, fields, query_molecule, resources, search, failures):
    """``request`` holds ``program``, ``database``, ``hitlist_size``, ``resource_id``. The conditions, each one problem
    with the field it concerns: the resource is a bound API service; each value is the commission's; the program takes
    the query's molecule; the database holds what the program searches; the hit-list size is in its range; no search
    is held; no earlier submission failed (a failure after a passed check is the environment's and not retried)."""
    problems = []
    if resources.get(request['resource_id']) != 'api':
        problems.append(_choose('resource_id', 'resource_is_not_an_api_service',
                                choose_from=[name for name, kind in resources.items() if kind == 'api']))
    for name in ('program', 'database', 'hitlist_size', 'resource_id'):
        if request[name] != fields[name]:
            problems.append(_choose(name, 'differs_from_the_commission', commission=fields[name]))
    units = PROGRAM_UNITS[request['program']]
    if units[0] != MOLECULE_UNITS[query_molecule]:
        problems.append(_choose('program', 'program_does_not_take_the_query_molecule', query_molecule=query_molecule,
                                choose_from=[name for name, (unit, *_) in PROGRAM_UNITS.items()
                                             if unit == MOLECULE_UNITS[query_molecule]]))
    if DATABASES[request['database']] != units[1]:
        problems.append(_choose('database', 'database_does_not_hold_what_the_program_searches',
                                choose_from=[name for name, unit in DATABASES.items() if unit == units[1]]))
    if not HITLIST_RANGE[0] <= request['hitlist_size'] <= HITLIST_RANGE[1]:
        problems.append(_choose('hitlist_size', 'hitlist_size_out_of_range', minimum=HITLIST_RANGE[0],
                                maximum=HITLIST_RANGE[1]))
    if search is not None:
        problems.append(_choose('action', 'search_already_held'))
    if failures and any(not retryable for _, retryable in failures):
        problems.append(_choose('action', 'submission_already_failed_and_cannot_be_retried'))
    return problems


def _held(request, search):
    if search is None:
        return [_choose('handoff_ref', 'no_search_held')]
    if request['handoff_ref'] != search['handoff']['id']:
        return [_choose('handoff_ref', 'handoff_is_not_the_held_search', choose_from=[search['handoff']['id']])]
    return []


def check_status_request(request, *, search, state):
    """The things to fix in a ``check``: the handoff is the held search; the search is outstanding (not already known
    to be finished, not graded, not failed beyond repair)."""
    problems = _held(request, search)
    if not problems and state != 'outstanding':
        problems.append(_choose('action', {'finished': 'search_already_shows_finished', 'graded': 'search_already_graded',
                                           'failed': 'search_failed_and_cannot_be_retried'}[state]))
    return problems


def check_fetch_request(request, *, search, state):
    """The things to fix in a ``fetch_and_grade``: the handoff is the held search and its latest held check shows the
    search finished with results available (the state ``finished``)."""
    problems = _held(request, search)
    if not problems and state != 'finished':
        problems.append(_choose('action', {'outstanding': 'search_not_known_to_be_finished',
                                           'graded': 'search_already_graded',
                                           'failed': 'search_failed_and_cannot_be_retried'}[state]))
    return problems


def check_hold(request, *, state):
    """The things to fix in a ``hold``: the reason is the one the state of the search gives."""
    allowed = HOLD_REASON_OF_STATE.get(state)
    if request['reason'] != allowed:
        return [_choose('reason', 'reason_does_not_hold_for_the_state', state=state,
                        choose_from=[] if allowed is None else [allowed])]
    return []


def held_searches(reader, sequences):
    """The searches of the service a parent (the head) holds, from its job ledger rows: one row per handoff of an API
    job, with its request, its query (the held subject whose sequence artifact was staged), the state its latest held
    check showed (``submitted`` before any) and whether it is outstanding (no closure held, and not shown failed or
    lost), and the references of its handoff, status and closure rows: ``outstanding`` searches are continued by a later commission. ``sequences`` is ``{subject record: its
    sequence artifact}``."""
    found = []
    for handoff in (row for row in job_rows(reader) if row['event'] == 'handoff' and row['detail']['kind'] == 'api'):
        shown, ended = checks(reader, handoff['job']), closure(reader, handoff['job'])
        state = 'submitted' if not shown else shown[-1]['detail']['state']
        request = handoff['detail']['native']['request']
        (query,) = [ref for ref, artifact in sequences.items() if artifact == handoff['detail']['input_refs'][QUERY_FILE]]
        found.append({'handoff_ref': handoff['id'], 'resource_id': handoff['detail']['resource_id'], 'query_ref': query,
                      'program': request['program'], 'database': request['database'],
                      'hitlist_size': request['hitlist_size'], 'latest_state': state,
                      'closed': ended is not None, 'outstanding': ended is None and state not in ('failed', 'unknown'),
                      'check_refs': [row['id'] for row in shown],
                      'closure_refs': [] if ended is None else [ended['id']]})
    return found


def check_commission(request, *, sequences, scope_subjects, resources, searches, failed):
    """The things to fix in the head's commission of this episode (``request``: ``query_ref``, ``program``,
    ``database``, ``hitlist_size``, ``resource_id``), before any child is commissioned. ``sequences`` is
    ``{record: molecule}``, ``searches`` is ``held_searches`` and ``failed`` the commissions (query, program, database,
    hit-list size) whose child reported the search failed. The conditions: the query is a sequence of the scope; the
    program takes its molecule; the database holds what the program searches; the hit-list size is in its range; the
    resource is a bound API service; a search of the query held outstanding is continued (its program, database,
    hit-list size and resource, no other); a search already closed or already failed is not commissioned again."""
    query, program, database = request['query_ref'], request['program'], request['database']
    key = (query, program, database, request['hitlist_size'])
    problems = []
    if query not in scope_subjects:
        problems.append(_choose('query_ref', 'query_is_not_a_sequence_of_the_scope',
                                choose_from=[ref for ref in scope_subjects if ref in sequences]))
    units = PROGRAM_UNITS[program]
    if units[0] != MOLECULE_UNITS[sequences[query]]:
        problems.append(_choose('program', 'program_does_not_take_the_query_molecule', query_molecule=sequences[query],
                                choose_from=[name for name, (unit, *_) in PROGRAM_UNITS.items()
                                             if unit == MOLECULE_UNITS[sequences[query]]]))
    if DATABASES[database] != units[1]:
        problems.append(_choose('database', 'database_does_not_hold_what_the_program_searches',
                                choose_from=[name for name, unit in DATABASES.items() if unit == units[1]]))
    if not HITLIST_RANGE[0] <= request['hitlist_size'] <= HITLIST_RANGE[1]:
        problems.append(_choose('hitlist_size', 'hitlist_size_out_of_range', minimum=HITLIST_RANGE[0],
                                maximum=HITLIST_RANGE[1]))
    if resources.get(request['resource_id']) != 'api':
        problems.append(_choose('resource_id', 'resource_is_not_an_api_service',
                                choose_from=[name for name, kind in resources.items() if kind == 'api']))
    for held in searches:
        if held['query_ref'] != query:
            continue
        same = (held['program'], held['database'], held['hitlist_size'], held['resource_id']) == (
            program, database, request['hitlist_size'], request['resource_id'])
        if held['outstanding'] and not same:
            problems.append(_choose('program', 'commission_must_continue_the_outstanding_search',
                                    program=held['program'], database=held['database'],
                                    hitlist_size=held['hitlist_size'], resource_id=held['resource_id']))
        if held['closed'] and same:
            problems.append(_choose('database', 'search_already_held'))
    if key in failed:
        problems.append(_choose('database', 'search_already_failed_and_cannot_be_retried'))
    return problems


# -- the tools --------------------------------------------------------------------------------------------------------
def _failed(code, retryable, **detail):
    return {'status': 'failed', 'failure_code': failure_code(code), 'retryable': retryable, 'record_refs': [],
            'detail': detail}


def _ended(table, handle, outcome, duration):
    table.resolve(handle, {'gain': 0.0, 'cost': 0.0, 'outcome': outcome, 'duration_seconds': duration}, at=now_text())


def submit_search(ctx, *, request, fields, sequence_ref):
    """One submission, with the duration predicted first. The kind derived from the job must be the declared one."""
    access, table = ctx.services['job_access'], ctx.services['estimate_table']
    job = {'program': request['program'], 'database': request['database'], 'hitlist_size': request['hitlist_size'],
           'query_file': QUERY_FILE}
    checked_analysis_kind(fields['analysis_kind'], job)
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
        _ended(table, handle, 'submit_failed:' + failure_code(failure['code']),
               seconds_between(started, now_text()))
        return {**_failed(failure['code'], False, sent=failure['detail'].get('sent')), 'handoff_refs': []}
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'handoff_refs': [launched['handoff_ref']],
            'record_refs': [launched['handoff_ref'], launched['reply_ref']], 'predicted_seconds': predicted,
            'duration_basis': basis, 'submitted_at': launched['submitted_at']}


async def check_search(ctx, *, handoff_ref, description):
    """One status request of the held search. When the service's spacing does not allow it yet, the unit waits the
    seconds that spacing needs (the existing wait helper) and then makes the one request. The first check that
    shows the search ended, or a request the service did not answer, resolves the duration on the estimate table."""
    table = ctx.services['estimate_table']
    search = search_view(ctx.store)
    wait = seconds_until_allowed(description, search_facts(search), now_text())
    checked = await wait_for_job(ctx, handoff_ref, seconds=wait + CLOCK_MARGIN_SECONDS if wait > 0 else 0)
    handoff = search['handoff']
    if checked['status'] != 'completed':
        code = failure_code(checked['failure']['code'])
        retryable = code == SPACING
        if not retryable:
            _ended(table, handoff['job'], 'check_failed:' + code, seconds_between(handoff['at'], now_text()))
        return {**_failed(code, retryable, waited_seconds=checked['waited_seconds']), 'handoff_refs': []}
    if checked['state'] in ENDED_STATES:
        _ended(table, handoff['job'], checked['state'], seconds_between(handoff['at'], checked['observed_at']))
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'state': checked['state'],
            'result_available': checked['result_available'], 'check_ref': checked['check_ref'],
            'record_refs': [checked['check_ref'], checked['reply_ref']], 'waited_seconds': checked['waited_seconds']}


def _grading(store, result_ref, fields, query_ref, sequence):
    """The grading of the fetched report into the database sheet of the original query: a report of another type,
    query or database is refused (``ValueError`` with its code)."""
    operand = {'subject_ref': query_ref, 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
               'database': fields['database']}
    grading = grade_blast_result(store.get_artifact(result_ref), mode='database', resource='api',
                                 output_format='json2', request=operand, _retain_correspondence=True)
    normalized = grading['sheet']['normalized_result']
    if normalized['mode'] != 'database' or normalized['query']['length'] != len(sequence):
        raise ValueError('result_of_another_query')
    if normalized['search']['database'] != fields['database']:
        raise ValueError('result_of_another_database')
    return grading


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


def fetch_and_grade_search(ctx, *, handoff_ref, fields, query_ref):
    """Fetch the report of the finished search and grade it in the same unit into the database sheet, kept through
    custody as the old ``blast_grade`` kept it: the grading artifact, a source of the provider over the fetched report
    and the search row that enters the search into the A101 sheet's tool profile. No step stands between the fetch
    and the grading."""
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


__all__ = ['ANALYSIS_KIND', 'DATABASES', 'FAILURE_CODES', 'HITLIST_RANGE', 'HOLD_REASONS', 'MOLECULE_UNITS', 'PROVIDER',
           'STATES', 'STATUS_FIELDS', 'check_fetch_request', 'check_hold', 'check_search', 'check_status_request',
           'check_commission', 'check_submit', 'failure_code', 'held_searches', 'fetch_and_grade_search', 'graded_rows', 'search_kind', 'search_state',
           'search_facts', 'search_view', 'seconds_until_allowed', 'submit_search', 'timing']
