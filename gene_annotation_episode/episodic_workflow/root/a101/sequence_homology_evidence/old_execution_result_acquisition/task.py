"""The task: acquire the results of the handed-off job through the job service.

The model is the router: at each decision it selects one defined operation with controlled operands, and code
carries it out. No operation runs a command the model wrote.

The plain file results of a job (family ``native_bytes``: requested paths and byte intervals inside the job's
directory) are acquired with three operations on the ``job_access`` service and the Episode's store:

- ``execution_results_status``: one status request for the job of the held handoff row (``JobAccess.check``); the
  service writes the check row.
- ``execution_results_collect``: the fetch of the requested result files (``JobAccess.fetch`` with the job service's
  names of the requested paths): each file becomes an artifact this Episode holds and the service writes the
  closure row; the bounded first window of each requested path is then read from the fetched artifact through
  custody (``ctx.store.open_artifact``) and retained.
- ``execution_results_read``: one further bounded window of a fetched file, inside the requested interval of its
  path, read from the held artifact in the same way.

A window names the fetched artifact it lies in, where it lies, how many bytes it holds and their digest; the bytes
stay in the fetched artifact. Each collect and read keeps its windows as a result record the Episode holds: an
artifact with the information body and a ``source`` record of provider ``episode.execution_result`` over it. A
request the job service refuses (the job has not ended: ``results_not_available``; a requested file the job did not
leave: ``result_not_in_catalog``; the transport is down) is the ``failed`` outcome the service returns: it is an
outcome of the unit and earns what the summary earns, nothing.

The BLAST database grader return (family ``blast_graded``): ``execution_results_fetch`` fetches the handoff's result
files and ``blast_grade`` grades one fetched native BLAST JSON2 result into the ``blast_database_sheet_v1`` of the
original query, retains it and enters the search into the A101 tool profile. The local phmmer return (family
``phmmer_graded``): ``phmmer_grade`` grades the fetched native output into HMMER search sheets. The grader's
meanings and the owner's request contract reach the model in the instruction text; the finding is the controlled
features code reads from the saved sheets.

The pairwise BLAST return (family ``blast_pairwise``, A101's own job of one query sequence against one subject sequence):
``execution_results_fetch`` fetches only the one report file the job declares, and ``blast_pairwise_grade`` grades that
native JSON document into the ``blast_pairwise_sheet_v1`` of the job's own operands (which operands they are comes from
the job, and the grading is refused when the document is of other sequences), retains the grading with its source and
the search's tool-profile row, and the finding is the controlled features code reads from the saved sheet. The job
declares no stdout or stderr output and nothing here fetches, writes or checks one.

The task always offers a unit and never ends the Episode; the yield controller stops it. This episode does not wait
for a job: a status request stays available when nothing else is.

``wait`` is the old selected wait of an API service assignment (``api_service_assignment_v1``); no placed family
offers it. The old typed result families (masking, standard BLAST database, BLAST database, HMMER
preparation, HMMER), the other API service results and the local file sources were classes of the
old shared root that are in no place now: ``decide`` raises ``NotImplementedError('unplaced:<family> ...')`` where
their catalog would have been read.

Settings (``ctx.settings``): ``log_window_bytes`` (the bound of the first window ``execution_results_collect``
retains of each requested path)."""
import hashlib
import json

from episode_runtime import ModelRequest, Rejected, ToolCall

from . import goal as goal_file
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_graders import (
    grade_blast_result)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_graders import (
    HMMER_DOMAIN_METRICS)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.phmmer_format import (
    VERSION as PHMMER_FORMAT_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.phmmer_grading_values import (
    VERSION as PHMMER_GRADING_VERSION, extract as extract_phmmer)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical, digest, obj)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError, validate_schema)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v3'
FILE_LIMIT = 1024 * 1024
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}

# The operations on the plain file results of a job.
STATUS = {'name': 'execution_results_status',
          'description': 'Ask the job service once for the state of the handed-off job (queued, running, finished, '
                         'failed, cancelled or unknown) and whether its results are available. The check is '
                         'recorded; no bytes are acquired.',
          'input_schema': obj({})}
COLLECT = {'name': 'execution_results_collect',
           'description': 'Fetch the requested result files of the job through the job service. Each fetched file '
                          'is kept whole, the job is closed, and the first window of each requested path (at most '
                          'first_window_bytes) is retained. The job service refuses while the job has not ended '
                          '(failure code results_not_available).',
           'input_schema': obj({})}
# The old ``wait`` selection of an API service assignment: an event_condition_v1 over registered native event targets.
WAIT = {'name': 'wait',
        'description': 'Wait for native job events of the targets this episode owns or received (an '
                       'event_condition_v1 condition).',
        'input_schema': obj({'condition': {'type': 'object'}})}


def execution_results_status(arguments, ctx):
    """One status request for the handed-off job. The job service writes the check row, with the route's reply as
    its artifact, through the Episode's store: that row is the record of the observation. A request that fails is
    the ``failed`` outcome the service returns."""
    return ctx.services['job_access'].check(ctx, arguments['handoff_ref'])


def _window(store, path, file, offset, limit):
    """One byte window of a fetched result file, read through custody: the artifact it lies in, where it lies, the
    bytes it holds and their digest."""
    with store.open_artifact(file['ref']) as stream:
        stream.seek(offset)
        data = stream.read(limit)
    return {'path': path, 'artifact_ref': file['ref'], 'offset': offset, 'returned_bytes': len(data),
            'size_bytes': file['bytes'], 'sha256': hashlib.sha256(data).hexdigest()}


def _retain(ctx, tool_name, arguments, windows):
    """Keep one acquisition as a result record this Episode holds: an artifact with its information body (the
    assignment it serves, the closure row of the fetch and the windows) and a ``source`` record over it."""
    closure = arguments['closure']
    body = {'version': RESULT_VERSION, 'assignment': arguments['assignment'], 'tool_name': tool_name,
            'closure_ref': closure['ref'], 'windows': windows}
    with ctx.store.transaction():
        artifact = ctx.store.artifact(canonical(body), 'application/json')
        source = ctx.store.put('source', {
            'provider': RESULT_PROVIDER,
            'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id, ctx.operation_key]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': RESULT_VERSION, 'retrieved_at': closure['at']}, origin='tool')
    return {'status': 'completed', 'result_ref': source['id'], 'artifact_ref': artifact}


def execution_results_collect(arguments, ctx):
    """Fetch the requested result files of the handed-off job and retain the bounded first window of each requested
    path. The job service fetches each file whole as an artifact this Episode holds and writes the closure row; a
    request it refuses is the ``failed`` outcome it returns."""
    requested, names = arguments['requested'], arguments['names']
    fetched = ctx.services['job_access'].fetch(ctx, arguments['handoff_ref'],
                                               names=[names[path] for path in requested])
    if fetched['status'] != 'completed':
        return fetched
    files = {item['name']: item for item in fetched['results']}
    bound = min(arguments['log_window_bytes'], FILE_LIMIT)
    windows = [_window(ctx.store, path, files[names[path]], start, bound if length is None else min(bound, length))
               for path, (start, length) in requested.items()]
    closure = {'ref': fetched['closure_ref'], 'at': fetched['closed_at']}
    return _retain(ctx, 'execution_results_collect', {**arguments, 'closure': closure}, windows)


def execution_results_read(arguments, ctx):
    """Retain one selected byte window of a fetched result file. A window outside the requested interval of its path
    is an invalid outcome."""
    window = arguments['window']
    start, length = arguments['requested'][window['path']]
    if window['offset'] < start or (length is not None and window['offset'] + window['limit'] > start + length):
        return _invalid('execution_results_selector_conflict')
    return _retain(ctx, 'execution_results_read', arguments,
                   [_window(ctx.store, window['path'], arguments['file'], window['offset'], window['limit'])])


async def wait(arguments, ctx):
    """The old ``_execute_selected_wait``: await the native event ledger; an unusable target is a failed outcome that
    enters the iterator (``selected_wait`` returns it)."""
    service = ctx.services['job_access']
    if not (hasattr(service, 'validate_event_targets') and hasattr(service, 'wait_events')):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.validate_event_targets and wait_events (the '
                                  'native event ledger); wanted call: await selected_wait(ctx.services["job_access"], '
                                  'arguments["condition"])')
    return await selected_wait(service, arguments['condition'])


def execution_results_fetch(arguments, ctx):
    """Fetch the result files of the original handoff through the job service (all of them, or the ``names`` the
    assignment's family needs): each file becomes an artifact this Episode holds and the handoff is closed by the
    service's closure row. A refused request (the job has not ended, the transport is down) is the ``failed``
    outcome the service returns."""
    return ctx.services['job_access'].fetch(ctx, arguments['handoff_ref'], names=arguments.get('names'))


def _invalid(code):
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': code}}


def blast_grade(arguments, ctx):
    """Return only original retained database-grader results that meet the request.

    The fetched native BLAST JSON2 result of the original query is graded by the A101 BLAST graders into its
    database sheet and probabilities; the grading must be of the requested return type, for the original query
    (its length) and, when the request names one, for the requested database (the old ``_blast_grader_rows``
    checks). The result is retained as an ``ncbi_blast`` source over the fetched artifact with the full grading
    artifact beside it (``retain_tool_grading``), and the search enters the A101 sheet's tool profile from the
    identity of its producer (``native_correspondence.SEARCHES``), also when it reported no hit."""
    request, result_ref = arguments['request'], arguments['result_ref']
    query = request['query_subject_ref']
    try:
        if not ctx.store.holds(result_ref):
            raise ValueError('blast_grader_result_not_held')
        sequence = ctx.store.get_artifact(ctx.store.get(query)['sequence_ref']).decode('ascii').upper()
        operand = {'subject_ref': query, 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest()}
        if 'database' in request:
            operand['database'] = request['database']
        grading = grade_blast_result(ctx.store.get_artifact(result_ref), mode='database', resource='api',
                                     output_format='json2', request=operand, _retain_correspondence=True)
        sheet = grading['sheet']
        normalized = sheet['normalized_result']
        if sheet['schema'] != request['return_type']:
            raise ValueError('blast_grader_result_type_conflict')
        if (normalized['mode'] != 'database' or normalized['resource'] != 'api'
                or normalized['query']['length'] != len(sequence)):
            raise ValueError('blast_grader_result_query_conflict')
        database = normalized['search']['database']
        if not isinstance(database, str) or not database:
            raise ValueError('blast_grader_native_database_missing')
        if 'database' in request and database != request['database']:
            raise ValueError('blast_grader_result_database_conflict')
    except ValueError as error:
        return _invalid(str(error))
    with ctx.store.transaction():
        grading_ref = retain_tool_grading(ctx.store, provider='ncbi_blast', native_artifact_ref=result_ref,
                                          grading=grading)
        source = ctx.store.put('source', {
            'provider': 'ncbi_blast', 'accession': None, 'uri': None, 'artifact_ref': result_ref,
            'text_ref': None, 'request_ref': None, 'version': normalized['search']['version'],
            'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query]},
            origin='tool')
        search = ctx.store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': query, 'profile': 'blast'})
    return {'status': 'completed', 'record_refs': [source['id'], grading_ref, search['id']],
            'changed_record_refs': [source['id'], grading_ref, search['id']],
            'result': {'result_ref': source['id'], 'grading_artifact_ref': grading_ref,
                       'search_ref': search['id'], 'sheet_schema': sheet['schema']}, 'feedback': None}


def _fasta_residues(data):
    """The residues (upper case) of a FASTA file of exactly one record."""
    lines = data.decode('ascii').splitlines()
    if sum(1 for line in lines if line.startswith('>')) != 1:
        raise ValueError('blast_pairwise_operand_single_record_required')
    return ''.join(line.strip() for line in lines if not line.startswith('>')).upper()


def blast_pairwise_grade(arguments, ctx):
    """Grade the fetched native JSON report of the job's one query against its one subject into the pairwise sheet,
    and keep the grading.

    Which sequences the report must be about is the job's own declaration: each operand is a FASTA artifact this
    Episode holds (its digest is the one the job declares), the query operand is bound to a subject record whose
    sequence it carries, and the sheet's query and subject lengths are those of the operands. A report of other
    sequences, or of another sheet type than the request, is refused (an invalid outcome, nothing retained). The
    result is retained as a ``native.blast.pairwise`` source over the fetched artifact with the full grading artifact
    beside it (``retain_tool_grading``), and the search enters the A101 sheet's tool profile from the identity of its
    producer (``native_correspondence.SEARCHES``)."""
    request, job, result_ref = arguments['request'], arguments['job'], arguments['result_ref']
    try:
        if not ctx.store.holds(result_ref):
            raise ValueError('blast_pairwise_result_not_held')
        residues = {}
        for operand in job['operands']:
            if operand['artifact_ref'] is None or not ctx.store.holds(operand['artifact_ref']):
                raise ValueError('blast_pairwise_operand_not_held:' + operand['role'])
            data = ctx.store.get_artifact(operand['artifact_ref'])
            if hashlib.sha256(data).hexdigest() != operand['sha256']:
                raise ValueError('blast_pairwise_operand_digest_conflict:' + operand['role'])
            residues[operand['role']] = _fasta_residues(data)
        bound = [row['subject_ref'] for row in job['operand_bindings']
                 if row['operand_role'] == 'query_sequence' and row['subject_ref']]
        if len(bound) != 1:
            raise ValueError('blast_pairwise_query_subject_binding_required')
        query = bound[0]
        if ctx.store.get_artifact(ctx.store.get(query)['sequence_ref']).decode('ascii').upper() != residues[
                'query_sequence']:
            raise ValueError('blast_pairwise_query_operand_conflict')
        grading = grade_blast_result(ctx.store.get_artifact(result_ref), mode='pairwise', resource='local',
                                     output_format='json2', request={'program': job['program'],
                                                                     'query_length': len(residues['query_sequence'])},
                                     _retain_correspondence=True)
        sheet = grading['sheet']
        if sheet['schema'] != request['return_type']:
            raise ValueError('blast_pairwise_result_type_conflict')
        if (sheet['query']['length'] != len(residues['query_sequence'])
                or sheet['reference']['length'] != len(residues['subject_sequence'])):
            raise ValueError('blast_pairwise_result_operand_conflict')
    except (ValueError, ContractError) as error:
        return _invalid(str(error))
    with ctx.store.transaction():
        grading_ref = retain_tool_grading(ctx.store, provider='native.blast.pairwise', native_artifact_ref=result_ref,
                                          grading=grading)
        source = ctx.store.put('source', {
            'provider': 'native.blast.pairwise', 'accession': None, 'uri': None, 'artifact_ref': result_ref,
            'text_ref': None, 'request_ref': None, 'version': sheet['input']['search']['version'],
            'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query]},
            origin='tool')
        search = ctx.store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': query, 'profile': 'blast'})
    return {'status': 'completed', 'record_refs': [source['id'], grading_ref, search['id']],
            'changed_record_refs': [source['id'], grading_ref, search['id']],
            'result': {'result_ref': source['id'], 'grading_artifact_ref': grading_ref,
                       'search_ref': search['id'], 'sheet_schema': sheet['schema']}, 'feedback': None}


PHMMER_FILES = ('native_text_ref', 'hit_table_ref', 'domain_table_ref', 'query_fasta_ref', 'reference_fasta_ref')
PHMMER_REQUIRED = ('native_text_ref', 'query_fasta_ref', 'reference_fasta_ref')
PHMMER_TABLE_ROLES = (('hit_table_ref', 'hit_table', 'phmmer.tblout'),
                      ('domain_table_ref', 'domain_table', 'phmmer.domtblout'))


def _phmmer_source(store, provider, body, *, parents=(), operands=(), artifact=None, tool_grading=None,
                   parser_version=PHMMER_FORMAT_VERSION):
    """The old ``HomologyResults._source``: a ``source`` over the body (or over the given native artifact, with
    the body as its request) and, when given, the full grading retained beside it."""
    request = store.artifact(canonical(body), 'application/json') if artifact is not None else None
    artifact = artifact or store.artifact(canonical(body), 'application/json')
    auxiliary = ([retain_tool_grading(store, provider=provider, native_artifact_ref=artifact,
                                      grading=tool_grading)] if tool_grading is not None else [])
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                'text_ref': artifact, 'request_ref': request, 'version': parser_version,
                                'retrieved_at': None, 'parent_source_refs': list(parents),
                                'operand_refs': list(operands),
                                **({'auxiliary_artifact_refs': auxiliary} if auxiliary else {})}, origin='tool')


def _phmmer_reference(store, native, database_sha256):
    """The old ``HomologyResults._reference``: a local reference record of one native reference sequence. This is
    explicitly a local source identity, never an invented public accession; the full native identifier/header
    stays in its source."""
    database = _phmmer_source(store, 'native.phmmer.database_manifest', {'database_sha256': database_sha256})
    sequence = store.artifact(native['symbols'], 'text/plain')
    if store.get(sequence)['sha256'] != native['sequence_sha256']:
        raise ContractError('parsed_native_reference_sequence_changed')
    body = {'native_identifier': native['reference_id'], 'database_description': native['database_description'],
            'sequence_sha256': native['sequence_sha256'], 'length': native['length']}
    source = _phmmer_source(store, 'native.phmmer.reference', body, parents=[database['id']])
    accession = 'phmmer.reference.' + hashlib.sha256(native['reference_id'].encode()).hexdigest()
    return store.put('reference', {'reference_type': 'protein', 'source_ref': source['id'], 'accession': accession,
                                   'label': accession, 'sequence_ref': sequence, 'molecule': 'protein',
                                   'length': native['length'], 'term_refs': [], 'context_refs': []}, origin='tool')


def _phmmer_grading(store, row, reference, native_parameters):
    """The old ``HomologyResults._grading``: one saved sheet, its association qualified before projection."""
    grading = row['grading']
    if grading.get('failure'):
        return grading
    try:
        sheet, scores = grading['sheet'], grading['scores']
        if len(sheet['domains']) != 1 or len(scores['domains']) != 1:
            raise ValueError('phmmer_grading_domain_association_invalid')
        domain, score = sheet['domains'][0], scores['domains'][0]
        if (domain['record_key'] != score['record_key'] or score['target_name'] != row['reference_id']
                or score['intervals']['model'] != row['query_interval_aa_zero_based_half_open']
                or score['intervals']['sequence'] != row['reference_interval_aa_zero_based_half_open']):
            raise ValueError('phmmer_grading_domain_association_invalid')
        artifact = store.get(reference['sequence_ref'])
        if sheet['inputs']['targets'][0]['sequence_digest'] != artifact['sha256']:
            raise ValueError('phmmer_grading_reference_sequence_mismatch')
        # This artifact is the exact already validated sequence consumed by the bounded extraction, now
        # retained under its canonical Store ID; the capture's own supplied settings are retained in the sheet.
        sheet['artifacts']['reference_sequence'] = {'artifact_ref': artifact['id'], 'sha256': artifact['sha256'],
                                                    'availability': 'retained'}
        sheet['inputs']['native_parameters'] = native_parameters
        return grading
    except (ValueError, KeyError, TypeError) as error:
        return {'sheet': None, 'scores': None, 'failure': {
            'code': str(error) if isinstance(error, ValueError) else 'phmmer_grading_saved_result_unavailable',
            'exception_type': type(error).__name__}}


def phmmer_grade(arguments, ctx):
    """Grade the fetched native phmmer output of the original query and publish what it measured (the old
    ``HomologyResults.prepare`` and ``extract``).

    A local phmmer alignment is graded into the HMMER search sheet (``hmmer_search_sheet_v1``) by joining its
    printed alignment to exactly one table row: ambiguity or absence is recorded on the row, never guessed. A
    repeated capture of unchanged measurements is the same grading, not a new one (``grading_identity``). The
    native bytes are retained as sources even when parsing or a later row fails; each graded alignment becomes a
    ``native.phmmer.alignment`` source with its grading retained beside it and an alignment observation of the
    query; and the search enters the A101 sheet's tool profile from the identity of its producer
    (``native_correspondence.SEARCHES``), also when it printed no alignment."""
    files, query, scope = arguments['files'], arguments['query_ref'], arguments['scope']
    store = ctx.store
    if not all(store.holds(ref) for ref in files.values()):
        return _invalid('phmmer_result_file_not_held')
    sequence = store.get_artifact(store.get(query)['sequence_ref']).decode('ascii').upper()
    query_sha256 = hashlib.sha256(sequence.encode()).hexdigest()
    database_sha256 = store.get(files['reference_fasta_ref'])['sha256']
    metadata = {'query_ref': query, 'native_text_artifact': files['native_text_ref'],
                **{role + '_artifact': files[name] for name, role, _ in PHMMER_TABLE_ROLES if name in files},
                'query_fasta_artifact': files['query_fasta_ref'], 'database_sha256': database_sha256,
                'query_sequence_sha256': query_sha256, 'parser_version': PHMMER_GRADING_VERSION}
    capture = hashlib.sha256(canonical(metadata).encode()).hexdigest()
    try:
        with store.scratch('phmmer') as scratch, store.transaction():
            paths = {'native_text': scratch.copy_artifact(files['native_text_ref'], 'phmmer.stdout'),
                     'query_fasta': scratch.copy_artifact(files['query_fasta_ref'], 'query.faa'),
                     'reference_fasta': scratch.copy_artifact(files['reference_fasta_ref'], 'references.faa')}
            for name, role, filename in PHMMER_TABLE_ROLES:
                paths[role] = (scratch.copy_artifact(files[name], filename) if name in files
                               else scratch.path / ('missing-' + filename))
            request = {**{role: str(path) for role, path in paths.items()},
                       'expected_query_sha256': query_sha256, 'database_sha256': database_sha256,
                       'executable_sha256': None, 'native_parameters': arguments['native_parameters'],
                       'grading_artifacts': {role: {'artifact_ref': files.get(name),
                                                    'availability': 'retained' if name in files else 'unavailable'}
                                             for role, name in (('stdout', 'native_text_ref'),
                                                                ('tblout', 'hit_table_ref'),
                                                                ('domtblout', 'domain_table_ref'),
                                                                ('query_fasta', 'query_fasta_ref'))}}
            extracted = extract_phmmer(store, request, capture=capture)
            provenance = _phmmer_source(store, 'native.phmmer.execution', {'handoff_ref': arguments['handoff_ref'],
                                                                           'native_parameters': request[
                                                                               'native_parameters']},
                                        operands=[query])
            native = _phmmer_source(store, 'native.phmmer.snapshot', metadata, parents=[provenance['id']],
                                    operands=[query], artifact=files['native_text_ref'],
                                    parser_version=PHMMER_GRADING_VERSION)
            snapshot = _phmmer_source(store, 'native.phmmer.parsed_snapshot', {
                **metadata, 'execution_source_ref': provenance['id'], 'native_source_ref': native['id'],
                'capture': capture, 'parse_summary': extracted['summary'], 'native_termination':
                    extracted['termination'], 'errors': extracted['errors']},
                parents=[native['id']], operands=[query], parser_version=PHMMER_GRADING_VERSION)
            search = store.table(SEARCHES).put({'source_ref': snapshot['id'], 'query_ref': query,
                                                'profile': 'hmmer'})
            references, gradings, observations, errors = {}, [], [], []
            for ordinal, row in enumerate(extracted['measurements'], start=1):
                if row['kind'] == 'reference':
                    references[row['reference_id']] = _phmmer_reference(store, row, database_sha256)
                    continue
                reference = references[row['reference_id']]
                grading = _phmmer_grading(store, row, reference, request['native_parameters'])
                semantic = {key: value for key, value in row.items()
                            if key not in {'source_byte_span', 'kind', 'grading'}}
                if grading.get('failure'):
                    semantic['grading_publication_failure'] = grading['failure']['code']
                    errors.append({'ordinal': ordinal, 'code': 'phmmer_grading_unavailable',
                                   'grading_failure': grading['failure']})
                key = hashlib.sha256(canonical({'measurement': semantic, 'query_ref': query,
                                                'database_sha256': database_sha256,
                                                'parser_version': PHMMER_GRADING_VERSION}).encode()).hexdigest()
                source = _phmmer_source(store, 'native.phmmer.alignment', {
                    **semantic, 'measurement_key': key,
                    'numerical_projection_version': 'hmmer_shared_paired_aliases_v1'},
                    parents=[snapshot['id']], operands=[query, reference['id']], tool_grading=grading,
                    parser_version=PHMMER_GRADING_VERSION)
                gradings.extend(source['auxiliary_artifact_refs'])
                values = {'evalue': row['independent_domain_evalue'], 'bitscore': row['domain_bitscore']}
                if not grading.get('failure'):
                    graded = grading['scores']['domains'][0]
                    values.update({name: graded[name] for name in HMMER_DOMAIN_METRICS
                                   if graded.get(name) is not None})
                    # These native aliases describe actual paired residues;
                    # the API publisher's endpoint-span aliases are distinct.
                    values.update({alias: graded[component] for alias, component in (
                        ('query_coverage', 'paired_model_coverage'),
                        ('target_coverage', 'paired_sequence_coverage'),
                        ('identity_fraction', 'sequence_identity_fraction'))
                        if graded.get(component) is not None})
                measurements = [{'name': name, 'value': {'type': 'number', 'value': value, 'unit_ref': None}}
                                for name, value in values.items()]
                measurements.append({'name': 'reference_ref', 'value': {'type': 'reference',
                                                                        'ref': reference['id']}})
                operands = [{'role': role, 'subject_ref': ref, 'start': start, 'end': end, 'unit': 'aa',
                             'model_unit': 'aa'}
                            for role, ref in (('query', query), ('reference', reference['id']))
                            for start, end in row['paired_intervals'][role]]
                observation = store.put('observation', {
                    'subject_refs': [query], 'source_subject_refs': [reference['id']], 'kind': 'alignment',
                    'source_ref': source['id'], 'measurements': measurements,
                    'dependencies': [query, reference['id']], 'anchor': None, 'operand_intervals': operands},
                    origin='tool', scope=scope)
                observations.append({'observation_ref': observation['id'], 'source_ref': source['id']})
    except (ValueError, ContractError) as error:
        return _invalid(str(error))
    refs = [snapshot['id'], search['id'], *(row['id'] for row in references.values()),
            *(ref for row in observations for ref in (row['source_ref'], row['observation_ref'])), *gradings]
    failures = [*extracted['errors'], *errors]
    return {'status': 'partial' if failures else 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {'snapshot_ref': snapshot['id'], 'search_ref': search['id'], 'grading_artifact_refs': gradings,
                       'reference_refs': [row['id'] for row in references.values()],
                       'observations': observations, 'grading_failure_count': len(errors),
                       'native_error_count': len(extracted['errors'])},
            'feedback': None if not failures else {'category': 'partial_execution',
                                                   'code': 'phmmer_extraction_incomplete',
                                                   'error_codes': sorted({row['code'] for row in failures})}}


TOOLS = {'execution_results_status': execution_results_status, 'execution_results_collect': execution_results_collect,
         'execution_results_read': execution_results_read, 'wait': wait,
         'execution_results_fetch': execution_results_fetch, 'blast_grade': blast_grade,
         'blast_pairwise_grade': blast_pairwise_grade, 'phmmer_grade': phmmer_grade}

FETCH = {'name': 'execution_results_fetch',
         'description': 'Fetch the result files of the original handoff once its job has ended; each file is kept '
                        'as an artifact and the handoff is closed.',
         'input_schema': obj({})}

# The grader's own meanings (``blast_database_grader``) and the owner's request contract
# (``blast_return_contracts``), given to the model with the grading tool.
GRADER_INSTRUCTIONS = (
    '\n\nBLAST database grader return. A BLAST launch may request a graded database result while leaving the child '
    'free to select its search program and, unless constrained, its database. The original query operand is a '
    'required result identity, not a prewritten service command. A submitted RID is an intermediate handoff; the '
    'grader is available after the separately selected results acquisition. Select blast_grade with one fetched '
    'result file to grade it into the blast_database_sheet_v1 of the original query: only original retained '
    'database-grader results that meet the request are returned. The sheet keeps every supplied hit row; sequence '
    'groups collapse demonstrated sequence identity, and distinct groups are not claimed independent experiments. '
    'Hitting a limit can censor evidence; fewer hits do not establish database completeness. Its function weights '
    'are conditional on the supplied candidate functions and returned matches: native bit score differences define '
    'a chosen reference-similarity kernel, not a measured functional likelihood, and unreported or unannotated '
    'functions remain outside that distribution.')


def _blast_catalog(summary):
    """The operations offered for a BLAST database grader return: fetching while the handoff is held and not
    closed, and grading one fetched result file."""
    catalog = [FETCH] if summary['fetch_offered'] else []
    refs = [row['result_ref'] for row in summary['fetched_results']]
    if refs:
        catalog.append({'name': 'blast_grade',
                        'description': 'Grade one fetched native BLAST JSON2 result file into the '
                                       'blast_database_sheet_v1 of the original query and keep the grading.',
                        'input_schema': obj({'result_ref': {'enum': refs}})})
    return catalog


PAIRWISE_GRADER_INSTRUCTIONS = (
    '\n\nPairwise BLAST return. The job compared one query sequence with one subject sequence; its report says which '
    'residues of the two correspond and how many. Fetch the job\'s report once it has ended (the job service refuses '
    'before that and the job stays open), then select blast_pairwise_grade to grade the fetched native report into '
    'the blast_pairwise_sheet_v1 of the job\'s own operands: a report of other sequences is refused. The sheet '
    'records every reported alignment, the residue pairs of their union, and the counts and fractions of paired and '
    'identical residues; it does not sum alternative alignments. The smallest native E-value of the alignments is '
    'reported with what the report gives to interpret it: the lengths of the two sequences, the effective search '
    'space, the effective alignment length, the scoring system\'s Karlin-Altschul parameters and the E-value '
    'threshold of the search. A value the report does not give is absent. The scientific parent interprets them.')


def _pairwise_catalog(summary):
    """The operations offered for a pairwise BLAST return: a status request always, the fetch while the job is not
    closed, and the grading once the report is fetched."""
    catalog = [STATUS]
    if summary['fetch_offered']:
        catalog.append(FETCH)
    if any(row['name'] == summary['report_name'] for row in summary['fetched_results']):
        catalog.append({'name': 'blast_pairwise_grade',
                        'description': 'Grade the fetched native BLAST report of the job into the '
                                       'blast_pairwise_sheet_v1 of its query and subject and keep the grading.',
                        'input_schema': obj({})})
    return catalog


# The owner's grading decisions for a local phmmer result (``phmmer_grading_values``, ``phmmer_format`` and the old
# ``homology_results``), given to the model with the grading tool.
PHMMER_GRADER_INSTRUCTIONS = (
    '\n\nLocal phmmer result grading. Select phmmer_grade naming which fetched file is the native phmmer text, the '
    'per-sequence hit table (tblout), the per-domain table (domtblout), the query FASTA and the reference FASTA. '
    'A local phmmer alignment is graded into the HMMER search sheet (hmmer_search_sheet_v1) by joining its printed '
    'alignment to exactly one table row; ambiguity or absence is recorded on the row, never guessed. A new raw '
    'capture is another witness to unchanged scientific measurements: a repeated capture is the same grading, and '
    'only an actual component change is a new explicit measurement version. The documented HMMER3 tables and '
    'printed residue coordinates define this representation; native inclusion flags are data, not selection. '
    'Numerical native-tool components extend the alignment observations; no annotation score or additional '
    'action is created, and the scientific parent interprets them. The search enters the sequence homology tool '
    'profile from its producer even when it printed no alignment: a missing operand in an included channel cannot '
    'be removed as though the tool was never used.')


def _phmmer_catalog(summary):
    """The operations offered for a local phmmer result: fetching while the handoff is held and not closed, and
    grading the fetched files."""
    catalog = [FETCH] if summary['fetch_offered'] else []
    refs = [row['result_ref'] for row in summary['fetched_results']]
    if refs:
        catalog.append({'name': 'phmmer_grade',
                        'description': 'Grade the fetched native phmmer output of the original query into HMMER '
                                       'search sheets and publish the graded alignments.',
                        'input_schema': obj({name: {'enum': refs} for name in PHMMER_FILES},
                                            required=list(PHMMER_REQUIRED))})
    return catalog


PLAIN_INSTRUCTIONS = (
    '\n\nPlain file results. The context shows the job (its last observed state and whether its results were '
    'fetched), the requested paths with their byte intervals, and the outcome of every operation so far. The job '
    'service fetches the result files of a job only once the job has ended: before that it refuses with the failure '
    'code results_not_available, nothing is acquired and the job stays open for a later acquisition. This episode '
    'does not wait for a job. A fetched file is the file of the job\'s directory as it stood at the fetch, kept '
    'whole with its digest; a window is a part of that one fetched file. The state of the job does not establish '
    'that the bytes are the output of that attempt.'
    '\n\nCredit. The credit is the credit unit times the fraction of the requested bytes that the retained windows '
    'cover, each byte position counted once, averaged over the requested paths. A status request, a refused fetch '
    'and a window of bytes already retained earn nothing. When the results are not available, or when every '
    'requested byte is retained, select execution_results_status.')
BLAST_CREDIT = (
    '\n\nCredit. The credit unit is earned once, when a grading of the requested sheet type for the original query '
    'is saved. A fetch and a refused grading earn nothing.')
PAIRWISE_CREDIT = (
    '\n\nCredit. The credit unit is earned once, when a grading of the pairwise sheet for the job\'s own query and '
    'subject is saved. A status request, a fetch and a refused grading earn nothing.')
PHMMER_CREDIT = (
    '\n\nCredit. The credit unit is earned once, when the fetched capture is graded and published. A fetch and a '
    'refused grading earn nothing.')
FAMILY_INSTRUCTIONS = {'native_bytes': PLAIN_INSTRUCTIONS, 'blast_graded': GRADER_INSTRUCTIONS + BLAST_CREDIT,
                       'phmmer_graded': PHMMER_GRADER_INSTRUCTIONS + PHMMER_CREDIT,
                       'blast_pairwise': PAIRWISE_GRADER_INSTRUCTIONS + PAIRWISE_CREDIT}
ANSWER_INSTRUCTION = (
    '\n\nAnswer with one of these operations and its operands as one JSON object in arguments_json (an empty object '
    'for an operation without operands). You select the operation; code carries it out. No operation ends the '
    'episode: it ends when further operations no longer earn credit.')


def _plain_catalog(summary):
    """The operations offered for the plain file results of a job: a status request always, the fetch while the
    job is not closed, and a further window once files are fetched."""
    catalog = [STATUS]
    if not summary['job']['closed']:
        catalog.append(COLLECT)
    if summary['fetched_files']:
        catalog.append({'name': 'execution_results_read',
                        'description': 'Retain one further byte window (path, offset, limit) of a fetched file, '
                                       'inside the requested interval of that path.',
                        'input_schema': obj({'path': {'enum': sorted(summary['fetched_files'])}, 'offset': OFFSET,
                                             'limit': {**LIMIT, 'maximum': FILE_LIMIT}})})
    return catalog


def _catalog(summary):
    """The operations offered for the original target (the old ``catalog`` branches)."""
    family = summary['family']
    if family == 'blast_graded':
        return _blast_catalog(summary)
    if family == 'phmmer_graded':
        return _phmmer_catalog(summary)
    if family == 'blast_pairwise':
        return _pairwise_catalog(summary)
    if family == 'native_bytes':
        return _plain_catalog(summary)
    raise NotImplementedError('unplaced:' + family + '.operation_catalog')


def _instructions(summary, catalog):
    """What the episode is for, what its family of result means and earns, and the operations available now."""
    operations = ''.join('\n- ' + entry['name'] + ': ' + entry['description'] for entry in catalog)
    return (goal_file.GOAL + FAMILY_INSTRUCTIONS[summary['family']] + '\n\nOperations available now:' + operations
            + ANSWER_INSTRUCTION)


def _context(summary, feedback, settings):
    """What the decision needs: the job, what was requested, what was acquired so far and the credit."""
    context = {'feedback': feedback, 'job': summary['job'], 'complete': summary['execution_completed'],
               'credit': summary['credit_view']}
    if summary['family'] == 'blast_graded':
        context.update(graded_return_request=summary['selector'], fetched_results=summary['fetched_results'],
                       gradings=summary['gradings'], graded_sheets=summary['graded_sheets'])
    elif summary['family'] == 'blast_pairwise':
        context.update(graded_return_request=summary['selector'], analysis_kind=summary['analysis_kind'],
                       job={**summary['job'], 'report_name': summary['report_name']},
                       fetched_results=summary['fetched_results'], gradings=summary['gradings'],
                       pairwise_sheets=summary['pairwise_sheets'])
    elif summary['family'] == 'phmmer_graded':
        context.update(fetched_results=summary['fetched_results'], gradings=summary['gradings'],
                       profile_sheets=summary['profile_sheets'])
    else:
        job, fetched = summary['job'], summary['fetched_files']
        context.update(
            job={'handoff_ref': summary['assignment']['handoff_ref'], 'job': job['job'],
                 'resource_id': job['resource_id'], 'kind': job['kind'], 'submitted_at': job['submitted_at'],
                 'last_observed_state': job['last_observed_state'] or 'not_observed',
                 'last_observed_at': job['last_observed_at'], 'results_fetched': job['closed']},
            requested=[{'path': path, 'offset': start, 'limit': length,
                        'fetched_file_bytes': fetched[path]['bytes'] if path in fetched else None}
                       for path, (start, length) in summary['requested'].items()],
            first_window_bytes=min(settings['log_window_bytes'], FILE_LIMIT), acquisitions=summary['acquisitions'])
    return context


def _output_schema(catalog):
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': [entry['name'] for entry in catalog]},
                           'arguments_json': {'type': 'string',
                                              'description': 'The operands as one JSON object: ' + json.dumps(
                                                  {entry['name']: entry['input_schema'] for entry in catalog},
                                                  sort_keys=True)}}}


def decide(summary, feedback, ctx):
    """One operation: the model selects it from the job, what was requested, what was acquired so far and the
    credit. For a graded return it is shown the fetched result files, its gradings so far and the controlled
    features of the saved sheets."""
    catalog = _catalog(summary)
    return ModelRequest('REASONING', _instructions(summary, catalog), _context(summary, feedback, ctx.settings),
                        _output_schema(catalog))


def action(response, summary, records, ctx):
    """The one operation the answer selects, or a rejection: it names an offered tool and operands that fit its
    schema. Every operand of the tool call that is not the model's own choice is taken from the summary."""
    entries = {entry['name']: entry for entry in _catalog(summary)}
    try:
        if response['tool'] not in entries:
            raise ValueError('execution_operation_not_available')
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        validate_schema(arguments, entries[response['tool']]['input_schema'])
    except (KeyError, TypeError, ValueError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    tool, assignment = response['tool'], summary['assignment']
    if tool == 'execution_results_status':
        return ToolCall(tool, {'handoff_ref': assignment['handoff_ref']})
    if tool == 'execution_results_collect':
        return ToolCall(tool, {'handoff_ref': assignment['handoff_ref'], 'assignment': assignment,
                               'requested': summary['requested'], 'names': summary['result_names'],
                               'log_window_bytes': ctx.settings['log_window_bytes']})
    if tool == 'execution_results_read':
        return ToolCall(tool, {'window': arguments, 'file': summary['fetched_files'][arguments['path']],
                               'closure': {'ref': summary['job']['closure_ref'], 'at': summary['job']['closed_at']},
                               'assignment': assignment, 'requested': summary['requested']})
    if tool == 'execution_results_fetch':
        return ToolCall(tool, {'handoff_ref': assignment['handoff_ref'],
                               'names': [summary['report_name']] if summary['family'] == 'blast_pairwise' else None})
    if tool == 'blast_pairwise_grade':
        report = next(row['result_ref'] for row in summary['fetched_results']
                      if row['name'] == summary['report_name'])
        return ToolCall(tool, {'result_ref': report, 'request': summary['selector'],
                               'job': summary['target']['assignment']['requested_job']['blast_pairwise']})
    if tool == 'blast_grade':
        return ToolCall(tool, {'result_ref': arguments['result_ref'], 'request': summary['selector']})
    return ToolCall('phmmer_grade', {'files': arguments, 'query_ref': summary['query_ref'],
                                     'scope': summary['target']['scope'], 'handoff_ref': assignment['handoff_ref'],
                                     'native_parameters': summary['target']['assignment']['requested_job'][
                                         'native_hmmer']})
