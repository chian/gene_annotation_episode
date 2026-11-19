"""The task: one plan step per unit; each step is a tool that runs one records library function on the records the
Episode holds, through ``ctx.store``. The task always offers a unit; the Episode ends when its yield controller
stops it (one credit per plan step)."""
import hashlib
import importlib
import json

from episode_runtime import Rejected, ToolCall

SUPPORT = 'gene_annotation_episode.episodic_workflow.episode_support.'
CHILD_SLOTS = {}
SERVICES = ()


def library(axis, module):
    return importlib.import_module(SUPPORT + 'records.' + axis + '.' + module)


def grading(axis, module):
    return importlib.import_module(SUPPORT + 'grading.' + axis + '.' + module)


def idle(arguments, ctx):
    return {'idle': True}


def publish_measurement(arguments, ctx):
    """An A103 host measurement is published with its grader and its use grant (a table row), received back,
    and its private locus payload is kept in a table row and read back."""
    store, publication = ctx.store, library(arguments['axis'], 'publication')
    ref = publication.publish(store, arguments['body'])
    received = publication.received_measurement(store, ref)
    out = {'ref': ref, 'kind': received['grade']['kind'], 'body': received['body'],
           'rows': [row['id'] for row in store.table(publication.PUBLICATIONS).select({'source_ref': ref})]}
    if arguments['axis'] == 'gene_context_evidence':
        out['measurement_ref'] = ref
    if 'binding' in arguments:
        store.table(publication.BINDINGS).put({'source_ref': ref, 'body': arguments['binding']})
        out['binding'] = publication.binding_body(store, ref, {ref})
    return out


def publish_comparison(arguments, ctx):
    """An A102 native comparison is published and its numerical receipt resolved."""
    publication = library('structural_homology_evidence', 'publication')
    published = publication.publish_comparison(ctx.store, arguments['native'])
    received = publication.received_grade(ctx.store, published['source_ref'])
    return {'source_ref': published['source_ref'], 'same': received == published,
            'B': received['grade']['components']['B'],
            'rows': [row['id'] for row in ctx.store.table(publication.NATIVE_PUBLICATIONS).select()]}


def attach_a104(arguments, ctx):
    store, attachments = ctx.store, library('evolutionary_history_evidence', 'attachments')
    scoring = grading('evolutionary_history_evidence', 'scoring')
    tool_grading = grading('evolutionary_history_evidence', 'tool_grading_artifacts')
    body = arguments['body']
    artifact = store.artifact(json.dumps(body, sort_keys=True, separators=(',', ':')), 'application/json')
    retained = tool_grading.retain_tool_grading(store, provider=attachments.PROVIDER, native_artifact_ref=artifact,
                                                grading={'grader': scoring.VERSION, 'failure': None, 'sheet': body})
    source = store.put('source', {'provider': attachments.PROVIDER, 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None,
        'auxiliary_artifact_refs': [retained]}, origin='tool')['id']
    store.table(attachments.ATTACHMENTS).put({'source_ref': source, 'body': body, 'grading_artifact_ref': retained})
    return {'source': source, 'received': attachments.received_attachments(store, [source])}


def attach_a103(arguments, ctx):
    store, attachments = ctx.store, library('gene_context_evidence', 'attachments')
    publication = library('gene_context_evidence', 'publication')
    measurement = publication.publish(store, arguments['measurement'])
    source = attachments._publish(store, measurement, arguments['body'], [measurement, arguments['target_ref']])
    return {'source': source, 'measurement': measurement,
            'received': attachments.received_attachments(store, [source]),
            'rows': [row['source_ref'] for row in store.table(attachments.ATTACHMENTS).select()]}


def attach_a102(arguments, ctx):
    store, attachments = ctx.store, library('structural_homology_evidence', 'attachments')
    request = attachments.request(store, arguments['request'], [arguments['target_ref']])
    source = attachments._publish(store, request, arguments['body'], [request, arguments['target_ref']])
    return {'request': request, 'source': source,
            'received': attachments.received_attachments(store, [source]),
            'request_rows': [row['source_ref'] for row in store.table(attachments.ATTACHMENT_REQUESTS).select()],
            'attachment_rows': [row['source_ref'] for row in store.table(attachments.TOOL_ATTACHMENTS).select()]}


def search_receipt(arguments, ctx):
    """A completed native search snapshot, kept as a source and a table row, is authenticated."""
    store = ctx.store
    receipt = importlib.import_module(SUPPORT + 'records.similarity_search.' + arguments['axis']
                                      + '.homology_search_receipt')
    component = store.get(arguments['component_ref'])
    sequence = store.get_artifact(component['sequence_ref']).decode().strip().upper()
    text = store.artifact('phmmer output', 'text/plain')
    native = store.put('source', {'provider': 'native.phmmer.snapshot', 'accession': None, 'uri': None,
        'artifact_ref': text, 'text_ref': text, 'request_ref': None, 'version': None, 'retrieved_at': None},
        origin='tool')['id']
    body = {'native_source_ref': native, 'native_text_artifact': text, 'native_termination_seen': True,
            'parse_inventory': {'parser_finished': True, 'native_error_count': 0},
            'parse_execution': {'failure': None},
            'query_sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest()}
    snapshot_artifact = store.artifact(json.dumps(body, sort_keys=True), 'application/json')
    snapshot = store.put('source', {'provider': 'native.phmmer.parsed_snapshot', 'accession': None, 'uri': None,
        'artifact_ref': snapshot_artifact, 'text_ref': snapshot_artifact, 'request_ref': None, 'version': None,
        'retrieved_at': None}, origin='tool')['id']
    store.table(receipt.SNAPSHOTS).put({'source_ref': snapshot, 'body': body})
    found, found_sequence = receipt.search_receipt(store, snapshot, native, arguments['component_ref'],
                                                   {snapshot, native, arguments['component_ref']})
    return {'same_body': found == body, 'sequence': found_sequence == sequence}


def source_restriction(arguments, ctx):
    """Public acquisition sources and their private auxiliaries judged among the held sources."""
    store = ctx.store
    restriction = library('sequence_and_context_sources', 'genomic_source_receipts')
    artifact = store.artifact('public result', 'text/plain')
    request = store.artifact('request', 'application/json')
    private = store.artifact('private diagnostic', 'text/plain')
    source = store.put('source', {'provider': 'ensembl', 'accession': 'E1', 'uri': None, 'artifact_ref': artifact,
        'text_ref': artifact, 'request_ref': request, 'version': None, 'retrieved_at': None,
        'auxiliary_artifact_refs': [private]}, origin='external')['id']
    other = store.artifact('another', 'text/plain')
    permitted = (source, artifact)
    ask = restriction.source_reference_restriction
    return {'source': ask(store, permitted, source, None), 'artifact': ask(store, permitted, artifact, None),
            'request': ask(store, permitted, request, None), 'private': ask(store, permitted, private, None),
            'not_permitted': ask(store, (), source, None), 'private_only': ask(store, permitted, source, None,
                                                                                 private_only=True),
            'unrelated': ask(store, permitted, other, None), 'wrong_namespace': ask(store, permitted, source,
                                                                                    'artifact')}


def capture_file(arguments, ctx):
    """A producer file is retained as an artifact and its identity verified through the held record."""
    capture = importlib.import_module(SUPPORT + 'records.local_execution.' + arguments['axis'] + '.native_file_capture')
    store = ctx.store
    identity = capture.capture_native_file(store, directory=arguments['directory'], relative_path='out/result.txt',
                                           format='text')
    metadata = capture.retained_native_file(store, identity)
    declared = capture.capture_declared_native_files(store, directory=arguments['directory'], declarations=[
        {'relative_path': 'out/result.txt', 'format': 'text', 'state': 'present',
         'sha256': identity['sha256'], 'size_bytes': identity['size_bytes']},
        {'relative_path': 'out/missing.txt', 'format': 'text', 'state': 'present', 'sha256': '0' * 64,
         'size_bytes': 1},
        {'relative_path': 'out/absent.txt', 'format': 'text', 'state': 'absent', 'sha256': None,
         'size_bytes': None}])
    return {'identity': identity, 'bytes': store.get_artifact(identity['artifact_ref']).decode(),
            'held_as_produced': store.receipt(identity['artifact_ref'])['how'],
            'size': metadata['size'], 'outcomes': [row['outcome'] for row in declared]}


def references_in(arguments, ctx):
    """The handles a value and typed forms name, among the held records, visible under a scope."""
    module = importlib.import_module(SUPPORT + 'records.received_records')
    forms = [(item['payload'], item['schema']) for item in arguments.get('forms', [])]
    return {'references': module.references_in(arguments['value'], ctx.store, arguments['scope'],
                                               reference_formats=tuple(arguments['formats']), forms=forms)}


def scope_checks(arguments, ctx):
    """Whether each reference is a held record visible under the scope, of the namespace asked."""
    module = importlib.import_module(SUPPORT + 'records.received_records')
    return {'visible': [module.reference_in_scope(ctx.store, ref, arguments['scope'], namespace)
                         for ref, namespace in arguments['asks']]}


def read_in_scope(arguments, ctx):
    module = importlib.import_module(SUPPORT + 'records.received_records')
    try:
        return {'id': module.read_record_in_scope(ctx.store, arguments['ref'], arguments['scope'],
                                                    arguments.get('namespace'))['id']}
    except module.ContractError as error:
        return {'refused': str(error)}


def library_identity(arguments, ctx):
    targets = library(arguments['axis'], 'library_targets')
    return {'is_library': targets.is_library(ctx.store.get(arguments['input_ref'])),
            'read': targets.read_ref('input_' + 'a' * 24, 'member_' + 'b' * 24)}


def rfam_scope(arguments, ctx):
    module = importlib.import_module(SUPPORT + 'records.similarity_search.rfam_batch_publication')
    store = ctx.store
    note = store.artifact('rfam metadata', 'text/plain')
    source = store.put('source', {'provider': 'rfam', 'accession': 'RF1', 'uri': None, 'artifact_ref': note,
        'text_ref': note, 'request_ref': None, 'version': None, 'retrieved_at': None,
        'operand_refs': [arguments['target_ref']]}, origin='tool')['id']
    return {'source': module.validate_rfam_metadata_source_scope(store, source,
                {'subject_refs': [arguments['target_ref']]})['id'] == source}


def captured(arguments, ctx):
    """The captured artifacts of a native bundle are copied into a scratch directory of the unit."""
    store = ctx.store
    module = importlib.import_module(SUPPORT + 'records.similarity_search.' + arguments['axis']
                                     + '.native_' + arguments['program'] + '_result_publication')
    data = arguments['text'].encode()
    sha = hashlib.sha256(data).hexdigest()
    artifact = store.artifact(data, 'text/plain')
    bundle = {'inputs': [{'role': 'query', 'format': 'fasta', 'relative_path': 'query.fa', 'actual_sha256': sha,
                          'expected_sha256': sha, 'sha256': sha, 'size_bytes': len(data),
                          'expected_size_bytes': len(data)}], 'artifacts': []}
    items = [{'role': 'query', 'format': 'fasta', 'relative_path': 'query.fa', 'artifact_ref': artifact}]
    checked = module._captured_custody(store, bundle, items)
    with store.scratch('captured') as scratch:
        paths, failures = module._captured_paths(scratch, store, bundle, items)
        copies = [open(row['path'], 'rb').read().decode() for row in paths]
    return {'custody': checked[0] == [{**items[0], 'kind': 'input'}], 'failures': failures,
            'copies': copies, 'names': [row['relative_path'] for row in paths]}


def staged_file(arguments, ctx):
    """An artifact is given to a native worker as a file of a scratch directory (twice: once copied)."""
    store = ctx.store
    module = importlib.import_module(SUPPORT + 'records.' + arguments['module'])
    artifact = store.artifact(arguments['text'], 'text/plain')
    with store.scratch('staged') as scratch:
        first, again = module._file(scratch, store, artifact), module._file(scratch, store, artifact)
        return {'first': first['path'] == again['path'], 'text': open(first['path']).read(),
                'identity': {key: value for key, value in first.items() if key != 'path'},
                'same_identity': module._identity(store, artifact) == {key: value for key, value in first.items()
                                                                        if key != 'path'}}


def subject_window(arguments, ctx):
    module = importlib.import_module(SUPPORT + 'records.similarity_search.' + arguments['axis']
                                     + '.native_hmmer_result_publication')
    return {'window': b''.join(module._subject_chunks(ctx.store, arguments['ref'], arguments['start'],
                                                      arguments['end'])).decode()}


TOOLS = {'idle': idle, 'publish_measurement': publish_measurement, 'publish_comparison': publish_comparison,
         'attach_a104': attach_a104, 'attach_a103': attach_a103, 'attach_a102': attach_a102,
         'search_receipt': search_receipt, 'source_restriction': source_restriction, 'capture_file': capture_file,
         'references_in': references_in, 'scope_checks': scope_checks, 'read_in_scope': read_in_scope,
         'library_identity': library_identity, 'rfam_scope': rfam_scope,
         'captured': captured, 'subject_window': subject_window, 'staged_file': staged_file}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    raise Rejected({'status': 'invalid', 'category': 'no_model_decision', 'detail': 'this task decides by plan'})
