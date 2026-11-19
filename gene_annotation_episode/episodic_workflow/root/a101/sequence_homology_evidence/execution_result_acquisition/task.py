"""The task: acquire the results of the original handoff.

The model chooses one native result operation from what preceded it: a status observation of the exact handed-off
attempt, or a bounded read window inside the original requested paths and interval (the old
``execution.results.status``, ``execution.results.collect`` and ``execution.results.read``; tool names are
lowercase identifiers now). The acquisition itself is done through the ``job_access`` service, which observes the
attempt and reads the requested files on the resource. Each tool keeps what it acquired as a retained result record
the Episode holds: an artifact with the information body and a ``source`` record of provider
``episode.execution_result`` over it. The task always offers a unit and never ends the Episode; the yield controller
stops it.

``wait`` is the old selected wait of an API service assignment (``api_service_assignment_v1``): an ``async`` tool
that awaits the native event ledger through the job service. A wait earns what its summary earns: nothing.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet"). The tools name it and call it; each raises where the call is made.

The BLAST database grader return (family ``blast_graded``, the old ``blast_result_grading.py`` of this episode) is
placed on the ``job_access`` service as it is built: ``execution_results_fetch`` fetches the handoff's result files
(``JobAccess.fetch``) and ``blast_grade`` grades one fetched native BLAST JSON2 result into the
``blast_database_sheet_v1`` of the original query, retains it and enters the search into the A101 tool profile. The
grader's meanings and the owner's request contract reach the model in the instruction text
(``GRADER_INSTRUCTIONS``); the finding is the controlled features code reads from the saved sheet.

The generic native byte-window family is placed on job service members that the built service does not offer
(``observe_target``, ``read_file``). The old typed result families (masking, utility, standard BLAST database, BLAST
database, HMMER preparation, HMMER, BLAST pairwise), the other API service results and the local file sources were
classes of the old shared root that are in no place now: ``decide`` raises ``NotImplementedError('unplaced:<family>
...')`` where their catalog would have been read.

Settings (``ctx.settings``): ``log_window_bytes`` (the old bounded first window of ``collect``),
``launch_instructions_directory`` and ``tool_knowledge_directory``."""
import base64
import hashlib
import inspect
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
    TEXT, canonical, digest, obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v2'
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
BODY_FIELDS = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments',
               'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
FILE_LIMIT = 1024 * 1024
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}

# The old ``native_result_operation_catalog()``.
CATALOG = [
    {'name': 'execution_results_status',
     'description': 'Observe the exact handed-off physical attempt once (old execution.results.status).',
     'input_schema': obj({})},
    {'name': 'execution_results_collect',
     'description': 'Observe the original attempt and acquire bounded first windows of the requested paths (old '
                    'execution.results.collect).',
     'input_schema': obj({})},
    {'name': 'execution_results_read',
     'description': 'Acquire one selected bounded byte window within the original requested paths and interval (old '
                    'execution.results.read).',
     'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': {**LIMIT, 'maximum': FILE_LIMIT}})}]
# The old ``wait`` selection of an API service assignment: an event_condition_v1 over registered native event targets.
WAIT = {'name': 'wait',
        'description': 'Wait for native job events of the targets this episode owns or received (an '
                       'event_condition_v1 condition).',
        'input_schema': obj({'condition': {'type': 'object'}})}

# The old results goal text replaced the default instructions; the old composer added the tool-knowledge and
# launch-instruction library texts, and the native-event wait text when ``wait`` is permitted.
ANSWER_INSTRUCTION = (' Answer with one tool and its operands as one JSON object in arguments_json (an empty object '
                      'for execution_results_status and execution_results_collect).')


def _outcome(result=None, *, references=(), code=None):
    """The old ``_outcome``: the outcome of an acquisition, or an invalid one with its code."""
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def _service_call(ctx, member, wanted, *arguments, **keywords):
    service = ctx.services['job_access']
    if not hasattr(service, member):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + member + '; wanted call: ' + wanted)
    return getattr(service, member)(*arguments, **keywords)


async def _settled(reply):
    return await reply if inspect.isawaitable(reply) else reply


def _validate_result_body(body, arguments, ctx):
    """The episode's check of its own acquisition (old ``_validate_result_body``): the closed body, and every
    window inside the original requested windows with the bytes it claims."""
    if (not isinstance(body, dict) or set(body) != BODY_FIELDS or body['version'] != RESULT_VERSION
            or body['run_id'] != ctx.run_id or body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
        raise ValueError('invalid_execution_result_information')
    requested = arguments['requested']
    for window in body['windows']:
        if window['path'] not in requested:
            raise ValueError('execution_result_selector_conflict')
        raw = base64.b64decode(window['bytes_base64'], validate=True)
        start, length = requested[window['path']]
        if (window['offset'] < start or window['returned_bytes'] != len(raw)
                or (length is not None and window['offset'] + len(raw) > start + length)
                or window['size_bytes'] < 0):
            raise ValueError('execution_result_window_conflict')


def _publish_result(body, ctx):
    """Keep the acquisition as an artifact and a ``source`` record over it (old ``_publish_result``)."""
    artifact = ctx.store.artifact(canonical(body), 'application/json')
    payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id,
                                                                                         body['operation_key']]),
               'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
               'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
    return ctx.store.put('source', payload, origin='tool')['id'], artifact


def _windows(tool_name, arguments):
    """The windows one operation reads (old ``_execute_native_results``)."""
    requested, model = arguments['requested'], arguments['arguments']
    if tool_name == 'execution_results_read':
        if model['path'] not in requested:
            raise ValueError('execution_results_selector_conflict')
        start, length = requested[model['path']]
        if model['offset'] < start or (length is not None and model['offset'] + model['limit'] > start + length):
            raise ValueError('execution_results_selector_conflict')
        return [model]
    if tool_name == 'execution_results_collect':
        bound = min(arguments['log_window_bytes'], FILE_LIMIT)
        return [{'path': path, 'offset': start, 'limit': min(bound, length) if length is not None else bound}
                for path, (start, length) in requested.items()]
    return []


async def _execute_native_results(tool_name, arguments, ctx):
    try:
        if arguments['completed']:
            raise ValueError('execution_results_assignment_already_completed')
        windows = _windows(tool_name, arguments)
        target = arguments['target']
        observation = await _settled(_service_call(
            ctx, 'observe_target', 'await ctx.services["job_access"].observe_target(arguments["target"], '
                                   'key=ctx.operation_key)', target, key=ctx.operation_key))
        acquired, failures = [], []
        for index, window in enumerate(windows):
            try:
                data = await _settled(_service_call(
                    ctx, 'read_file', 'await ctx.services["job_access"].read_file(arguments["target"], path=, '
                                      'offset=, limit=, key=ctx.operation_key + ":file:<index>")',
                    target, **window, key=ctx.operation_key + ':file:' + str(index)))
                acquired.append(data)
            except (ValueError, OSError) as error:
                failures.append({'path': window['path'],
                                 'code': str(error) if isinstance(error, ValueError)
                                 else 'execution_result_file_unavailable',
                                 'exception_type': type(error).__name__})
        body = {'version': RESULT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
                'scope': target['scope'], 'assignment': arguments['assignment'], 'operation_key': ctx.operation_key,
                'tool_name': tool_name, 'arguments': arguments['arguments'], 'target': target,
                'observation': observation, 'windows': acquired, 'failures': failures,
                'acquisition_origin': dict(NATIVE_RESULT_ORIGIN)}
        _validate_result_body(body, arguments, ctx)
        source_ref, artifact_ref = _publish_result(body, ctx)
    except (ValueError, TypeError) as error:
        return _outcome(code=str(error))
    return {**_outcome(body, references=[source_ref]), 'artifact_ref': artifact_ref}


async def execution_results_status(arguments, ctx):
    return await _execute_native_results('execution_results_status', arguments, ctx)


async def execution_results_collect(arguments, ctx):
    return await _execute_native_results('execution_results_collect', arguments, ctx)


async def execution_results_read(arguments, ctx):
    return await _execute_native_results('execution_results_read', arguments, ctx)


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
    """Fetch the result files of the original handoff through the job service: each file becomes an artifact this
    Episode holds and the handoff is closed by the service's closure row. A refused request (the job has not
    ended, the transport is down) is the ``failed`` outcome the service returns."""
    return ctx.services['job_access'].fetch(ctx, arguments['handoff_ref'])


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
         'phmmer_grade': phmmer_grade}

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


def _catalog(summary):
    """The operations offered for the original target (the old ``catalog`` branches)."""
    family = summary['family']
    if family == 'blast_graded':
        return _blast_catalog(summary)
    if family == 'phmmer_graded':
        return _phmmer_catalog(summary)
    if family == 'native_bytes':
        return CATALOG
    raise NotImplementedError('unplaced:' + family + '.operation_catalog')


def _instructions(settings, summary):
    library = LaunchInstructions(settings['launch_instructions_directory'])
    text = goal_file.GOAL + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION
    if summary['family'] == 'blast_graded':
        text += GRADER_INSTRUCTIONS
    if summary['family'] == 'phmmer_graded':
        text += PHMMER_GRADER_INSTRUCTIONS
    return text, library


def _task_text(summary):
    """The old selected-execution presentation over this episode's own summary: the assignment, the target, what was
    acquired so far and the progress."""
    parts = ['TASK', '', 'Acquire the selected results of the original handoff.', '', 'Assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True), '', 'Execution target', '',
             json.dumps(summary['target'], indent=1, sort_keys=True)]
    if summary['selected_execution_task'] is not None:
        parts.extend(['', 'Selected execution task', '',
                      json.dumps(summary['selected_execution_task'], indent=1, sort_keys=True)])
    if summary['acquisitions']:
        parts.extend(['', 'Acquisitions so far', '', json.dumps(summary['acquisitions'], indent=1, sort_keys=True)])
    parts.extend(['', 'Progress', '', json.dumps({'execution_progress': summary['execution_progress']},
                                                 indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _output_schema(catalog):
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': [entry['name'] for entry in catalog]},
                           'arguments_json': {'type': 'string',
                                              'description': 'The operands as one JSON object: ' + json.dumps(
                                                  {entry['name']: entry['input_schema'] for entry in catalog},
                                                  sort_keys=True)}}}


def decide(summary, feedback, ctx):
    """One acquisition: the model chooses it from the assignment, the target, the acquisitions so far and their
    credit. For a BLAST database grader return it is shown the fetched result files, its gradings so far and the
    controlled features of the saved sheets."""
    catalog = _catalog(summary)
    instructions, library = _instructions(ctx.settings, summary)
    knowledge = ToolKnowledge(ctx.settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary), 'feedback': feedback, 'execution_assignment': summary['assignment'],
               'execution_progress': summary['execution_progress'], 'execution_target': summary['target'],
               'acquisitions': summary['acquisitions'], 'launch_instruction_library': library.context(),
               'tool_knowledge': knowledge.context(), 'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    if summary['family'] == 'blast_graded':
        context.update(graded_return_request=summary['selector'], fetched_results=summary['fetched_results'],
                       gradings=summary['gradings'], graded_sheets=summary['graded_sheets'])
    if summary['family'] == 'phmmer_graded':
        context.update(fetched_results=summary['fetched_results'], gradings=summary['gradings'],
                       profile_sheets=summary['profile_sheets'])
    if summary['selected_execution_task'] is not None:
        context['selected_execution_task'] = summary['selected_execution_task']
    return ModelRequest('REASONING', instructions, context, _output_schema(catalog))


def action(response, summary, records, ctx):
    """The one operation the answer selects, or a rejection: it names an offered tool and operands that fit its
    schema."""
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
    if response['tool'] == 'execution_results_fetch':
        return ToolCall('execution_results_fetch', {'handoff_ref': summary['assignment']['handoff_ref']})
    if response['tool'] == 'blast_grade':
        return ToolCall('blast_grade', {'result_ref': arguments['result_ref'], 'request': summary['selector']})
    if response['tool'] == 'phmmer_grade':
        return ToolCall('phmmer_grade', {'files': arguments, 'query_ref': summary['query_ref'],
                                         'scope': summary['target']['scope'],
                                         'handoff_ref': summary['assignment']['handoff_ref'],
                                         'native_parameters': summary['target']['assignment']['requested_job'][
                                             'native_hmmer']})
    return ToolCall(response['tool'], {'arguments': arguments, 'assignment': summary['assignment'],
                                       'target': summary['target'], 'requested': summary['requested'],
                                       'completed': summary['execution_completed'],
                                       'log_window_bytes': ctx.settings['log_window_bytes']})
