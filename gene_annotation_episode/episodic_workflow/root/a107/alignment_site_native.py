"""Bind selected retained alignments to explicit numerical-grader inputs.

This host adapter reads actual assigned records and retained artifacts. It never
executes an aligner, chooses a result, acquires a reference or assigns credit.
"""
from __future__ import annotations

import json
from copy import deepcopy

from .domain import ContractError, identity
from .episode_return_records import EpisodeReturnRecords


def immutable_record(record):
    payload = {k: v for k, v in record.items() if k not in {'id', 'record_type', 'origin'}}
    kind = record['record_type']
    if kind == 'input':
        # materials.create_problem / library_targets.bind hash the original
        # input payload directly, before adding caller ownership metadata.
        expected = identity('input', payload)
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    elif kind == 'read_subject':
        # A read subject is resolved from fixed library membership, rather than
        # stored as an independently hashed scientific record.
        from .library_targets import read_ref
        expected = read_ref(record['library_ref'], record['member_ref'])
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    else:
        expected = identity(kind, {'origin': record['origin'], 'record': payload})
    if record['id'] != expected:
        raise ContractError('site_record_identity_conflict')


def source_descriptor(store, source, alignment):
    if alignment.get('native_blast_standard_database') is not None:
        from .native_blast_standard_database_result_publication import validate_standard_blast_database_observation
        validate_standard_blast_database_observation(store, alignment)
        raise ContractError('native_blast_standard_database_biological_reference_unavailable')
    if alignment.get('native_blast_database') is not None:
        from .native_blast_database_result_publication import validate_native_blast_database_observation
        validate_native_blast_database_observation(store, alignment)
        raise ContractError('native_blast_database_biological_reference_unavailable')
    provider = source['provider']
    if provider == 'episode.execution_result':
        from .native_blast_hsp_views import native_blast_pairwise_hsp
        bound = native_blast_pairwise_hsp(store, alignment)
        if not EpisodeReturnRecords._equal(source, bound['source']):
            raise ContractError('site_native_source_conflict')
        return bound['source_descriptor']
    formats = {'biopython.alignment': 'biopython_pairwise_json',
               'native.phmmer.alignment': 'native_phmmer_alignment_json',
               'minimap2.mapping': 'minimap2_paf_row',
               'ncbi_blast': 'ncbi_blast_json_hsp'}
    if provider not in formats:
        raise ContractError('native_alignment_site_mapping_unavailable')
    locator, artifact = {}, source['artifact_ref']
    native_version = source['version']
    if provider == 'native.phmmer.alignment':
        # Homology source.version identifies its parser. The actual HMMER
        # version belongs to the original retained native-result sheet.
        from .tool_grading_artifacts import source_tool_gradings
        operations = [grading['sheet'].get('operation')
            for grading in source_tool_gradings(store, source['id'])
            if isinstance(grading.get('sheet'), dict)
            and grading['sheet'].get('schema') == 'hmmer_search_sheet_v1']
        if len(operations) > 1:
            raise ContractError('site_native_version_ambiguous')
        native_version = None
        if operations:
            operation, = operations
            if not isinstance(operation, dict):
                raise ContractError('site_native_operation_invalid')
            if operation.get('program') != 'phmmer':
                raise ContractError('site_native_program_conflict')
            native_version = operation.get('engine_version')
            if native_version is not None and (
                    not isinstance(native_version, str) or not native_version):
                raise ContractError('site_native_version_invalid')
    if provider == 'minimap2.mapping':
        native = alignment.get('native_minimap2')
        if native is None or source.get('stdout_ref') is None:
            raise ContractError('native_alignment_site_mapping_unavailable')
        locator = {name: native[name] for name in ('line_number', 'row_start', 'row_end')}
        artifact = source['stdout_ref']
    elif provider == 'ncbi_blast':
        locator = {name: alignment['native_blast'][name]
                   for name in ('report_ordinal', 'hit_ordinal', 'hsp_ordinal')}
    return {'alignment_ref': alignment['id'], 'source_ref': source['id'],
            'native_artifact_ref': artifact, 'provider': provider,
            'format': formats[provider], 'native_version': native_version,
            'native_locator': locator}


def operand_descriptor(store, reference, *, alignment_unit, native_length=None):
    record = store.get(reference)
    immutable_record(record)
    if record['record_type'] == 'read_subject':
        immutable_record(store.get(record['library_ref']))
    if record.get('record_type') == 'reference' and record.get('sequence_ref') is None:
        length = record.get('length')
    else:
        length = store.subject_length(reference)
    if native_length is not None and length != native_length:
        raise ContractError('site_operand_identity_conflict')
    molecule = store.subject_molecule(reference)
    return {'subject_ref': reference, 'length': length,
            'unit': store.subject_unit(reference), 'alignment_unit': alignment_unit,
            'molecule': molecule if molecule in {'dna', 'rna', 'protein'} else 'unknown'}


def original_mappings(store, operands):
    return {role: store.sequence_mapping(row['subject_ref'])
            if store.has_exact_mapping(row['subject_ref']) else None
            for role, row in operands.items()}


def _reference_alignment_require(condition, code):
    if not condition:
        raise ContractError('reference_alignment_' + code)


def _reference_alignment_artifact(store, reference, *, read=False):
    metadata = store.get(reference)
    sha = metadata.get('sha256')
    _reference_alignment_require(metadata.get('record_type') == 'artifact'
        and metadata.get('id') == reference and type(sha) is str and len(sha) == 64
        and set(sha) <= set('0123456789abcdef') and reference == 'artifact_' + sha
        and type(metadata.get('size')) is int and metadata['size'] >= 0,
        'artifact_identity_conflict')
    if not read:
        return metadata
    raw = store.get_artifact(reference)  # Existing Store authority checks the digest.
    _reference_alignment_require(len(raw) == metadata['size'], 'artifact_size_conflict')
    return json.loads(raw)


def _reference_alignment_sheet(sheet, native, *, molecule):
    """Validate saved cells against their native body using existing readers only."""
    from .biopython_pairwise_grader import (_validate_sheet, _traceback, _geometry,
        _no_alignment_conflict, _empty_geometry, _number, _REPORTED_FIELDS)
    _validate_sheet(sheet)
    same = EpisodeReturnRecords._equal
    _reference_alignment_require(same(sheet['native_result'], native)
        and sheet['molecule'] == molecule and sheet['mode'] == native['mode']
        and same(sheet['aligned'], native.get('aligned')), 'saved_native_conflict')
    for role in ('query', 'reference'):
        length = native.get(role + '_length')
        expected = length if type(length) is int and length >= 0 else None
        _reference_alignment_require(same(sheet['lengths'][role], expected), 'saved_native_length_conflict')
    issues = []
    _reference_alignment_require(same(sheet['native_score'], _number(native.get('native_score'),
        'native_score', issues, required=sheet['aligned'])), 'saved_native_score_conflict')
    parameters = {'matrix': native.get('matrix') if type(native.get('matrix')) is str and native['matrix'] else None,
        **{key: _number(native.get(key), key, issues, required=sheet['aligned'])
            for key in ('gap_open', 'gap_extend')}}
    reported = {key: _number(native.get(key), key, issues, integer=key.endswith('positions'),
        minimum=0, maximum=None if key.endswith('positions') else 1)
        for key in _REPORTED_FIELDS}
    _reference_alignment_require(same(sheet['native_parameters'], parameters)
        and same(sheet['reported_measurements'], reported), 'saved_native_measurement_conflict')
    if sheet['aligned']:
        issues = []
        traceback, counts = _traceback(native, issues)
        _reference_alignment_require(same(traceback, sheet['traceback'])
            and (counts is None or same(counts, sheet['measured_column_counts'])), 'saved_traceback_conflict')
        if counts is not None:
            geometry, rows = _geometry(native, traceback, counts, sheet['lengths'], native['mode'], issues)
            _reference_alignment_require(same(geometry, sheet['geometry'])
                and same(rows, sheet['residue_correspondence']), 'saved_geometry_conflict')
        else:
            _reference_alignment_require(same(sheet['geometry'], _empty_geometry())
                and sheet['residue_correspondence'] == [], 'saved_geometry_conflict')
    else:
        expected = 'conflicting' if _no_alignment_conflict(native) else 'no_alignment'
        _reference_alignment_require(sheet['alignment_state'] == expected, 'saved_native_conflict')


def _selected_reference_alignment_authority(store, context, alignment_ref, *, before_decision_index):
    """Authenticate selected alignment custody using metadata, never File bytes.

    The admission is a reproducible witness, not a transferable authority. Saved
    consumers reconstruct the original receiver context/cutoff and call this
    same helper again before comparing it with their privately retained witness.
    """
    from .communication import plain
    from .execution_contracts import digest
    from .tool_grading_artifacts import MEDIA_TYPE

    require, same = _reference_alignment_require, EpisodeReturnRecords._equal
    require(type(before_decision_index) is int and before_decision_index >= 0, 'cutoff_invalid')
    returns = EpisodeReturnRecords(store, context.run_id, failure_prefix='reference_alignment_')
    returns.authenticate(context)
    require(type(alignment_ref) is str and returns._received_before(context.episode_id,
        alignment_ref, before_decision_index), 'observation_not_received')
    alignment = store.get(alignment_ref)
    require(alignment.get('record_type') == 'observation' and alignment.get('origin') == 'tool'
        and alignment.get('kind') == 'alignment', 'observation_required')
    immutable_record(alignment)
    source = store.get(alignment['source_ref'])
    require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
        and source.get('provider') == 'biopython.alignment', 'source_required')
    immutable_record(source)
    require(returns._received_before(context.episode_id, source['id'], before_decision_index), 'source_not_received')
    require(type(alignment.get('subject_refs')) is list and len(alignment['subject_refs']) == 1
        and type(alignment.get('source_subject_refs')) is list and len(alignment['source_subject_refs']) == 1,
        'operand_identity_conflict')
    query, reference = alignment['subject_refs'][0], alignment['source_subject_refs'][0]
    expected_refs = list(dict.fromkeys([query, reference]))
    require(alignment.get('dependencies') == expected_refs, 'operand_identity_conflict')
    operands = {role: operand_descriptor(store, ref, alignment_unit='nt')
        for role, ref in (('query', query), ('reference', reference))}
    require(all(row['unit'] in ('nt', 'symbol') and row['molecule'] in ('dna', 'rna', 'unknown')
        for row in operands.values()), 'nucleotide_operands_required')
    footprint = store.coverage(query)
    rooted = bool(store.roots(query))
    require(not rooted or bool(footprint) and store.scope_covers(footprint, plain(context.scope)), 'query_outside_scope')
    rows = store.db.execute("""SELECT operation.*, action.run_id AS producer_run_id,
        action.episode_id AS producer_episode_id, action.decision_index AS producer_decision_index,
        action.action AS selected_action, action.result AS actual_outcome
        FROM tool_operations operation JOIN runtime_actions action
          ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index
        WHERE operation.name IN ('sequence.align','reads.align')
          AND EXISTS(SELECT 1 FROM json_each(operation.result,'$.record_refs') WHERE value IN (?,?))""",
        (alignment['id'], source['id'])).fetchall()
    require(len(rows) == 1, 'unique_producer_required')
    row, = rows
    require(type(row['producer_decision_index']) is int and row['producer_decision_index'] >= 0
        and row['actual_outcome'] is not None, 'producer_invalid')
    producer_records = EpisodeReturnRecords(store, row['producer_run_id'], failure_prefix='reference_alignment_')
    producer = producer_records.context(row['producer_episode_id'])
    arguments, outcome = json.loads(row['arguments']), json.loads(row['result'])
    action, actual = json.loads(row['selected_action']), json.loads(row['actual_outcome'])
    require(type(arguments) is dict and type(outcome) is dict and type(actual) is dict, 'producer_invalid')
    require(same(action, dict(kind='tool', tool=row['name'], arguments=arguments))
        and same(json.loads(row['scope']), plain(producer.scope)), 'producer_action_conflict')
    expected_id = identity('operation', dict(key=row['operation_key'], name=row['name'], arguments=arguments))
    require(row['id'] == expected_id and outcome.get('operation_ref') == expected_id
        and same({key: value for key, value in actual.items() if key != 'pending_work_after_action'}, outcome)
        and outcome.get('status') in ('completed', 'partial'), 'producer_outcome_conflict')
    require(type(outcome.get('record_refs')) is list
        and {alignment['id'], source['id']} <= set(outcome['record_refs']), 'producer_membership_conflict')
    fields = {'query_ref' if row['name'] == 'sequence.align' else 'subject_refs', 'reference_ref', 'molecule', 'mode'}
    require(set(arguments) == fields and arguments['reference_ref'] == reference
        and type(arguments['molecule']) is str and arguments['molecule'] in ('dna', 'rna')
        and type(arguments['mode']) is str and arguments['mode'] in ('local', 'global'), 'producer_arguments_conflict')
    if row['name'] == 'sequence.align':
        require(arguments['query_ref'] == query and type(outcome.get('result')) is dict
            and outcome['result'].get('observation_ref') == alignment['id']
            and outcome['result'].get('source_ref') == source['id'], 'producer_operand_conflict')
        previews = [outcome['result']]
    else:
        queries, result = arguments['subject_refs'], outcome.get('result')
        require(type(queries) is list and queries.count(query) == 1
            and store.get(query)['record_type'] == 'read_subject' and type(result) is dict
            and type(result.get('count')) is int and result['count'] == len(queries)
            and type(result.get('records')) is list, 'producer_operand_conflict')
        previews = [item for item in result['records'] if type(item) is dict
            and (item.get('observation_ref') == alignment['id'] or item.get('source_ref') == source['id'])]
        require(all(item.get('subject_ref') == query and item.get('observation_ref') == alignment['id']
            and item.get('source_ref') == source['id'] for item in previews), 'producer_preview_conflict')
    require(not rooted or bool(footprint) and store.scope_covers(footprint, plain(producer.scope)), 'producer_query_outside_scope')
    if producer.run_id == context.run_id and producer.episode_id == context.episode_id:
        require(type(row['producer_decision_index']) is int
            and row['producer_decision_index'] < before_decision_index, 'producer_after_cutoff')
    if 'operand_refs' in source:
        require(source['operand_refs'] == expected_refs, 'source_operand_conflict')
    grading_refs = [ref for ref in source.get('auxiliary_artifact_refs', [])
        if _reference_alignment_artifact(store, ref)['media_type'] == MEDIA_TYPE]
    require(len(grading_refs) <= 1, 'ambiguous_grading')

    # Retain only metadata identities. The existing receipt checks above own
    # admission; hashing raw manifests adds no interpretation of legacy fields.
    receipt_lineage, current, through, seen = [], context.episode_id, None, set()
    while current is not None and current not in seen:
        seen.add(current)
        manifest = store.db.execute('SELECT * FROM runtime_receipt_inheritance '
            'WHERE run_id=? AND episode_id=?', (context.run_id, current)).fetchone()
        receipts = store.db.execute('SELECT * FROM runtime_record_receipts WHERE run_id=? '
            'AND episode_id=? AND record_ref IN (?,?) ORDER BY record_ref',
            (context.run_id, current, alignment['id'], source['id'])).fetchall()
        receipts = [receipt for receipt in receipts
            if (through is None or receipt['receipt_index'] <= through)
            and (current != context.episode_id or receipt['receipt_kind'] == 'initial'
                or type(receipt['source_index']) is int
                and (receipt['source_index'] <= before_decision_index
                    if receipt['receipt_kind'] == 'decision_input'
                    else receipt['source_index'] < before_decision_index))]
        receipt_lineage.append(dict(episode_id=current, through_receipt_index=through,
            manifest=None if manifest is None else dict(manifest),
            receipts=[dict(receipt) for receipt in receipts]))
        if manifest is None:
            break
        current, through = manifest['parent_episode_id'], manifest['through_receipt_index']
    admission = dict(version='selected_reference_alignment_admission_v1',
        receiver=dict(run_id=context.run_id, episode_id=context.episode_id,
            before_decision_index=before_decision_index,
            request_sha256=digest(plain(context.request)), scope_sha256=digest(plain(context.scope)),
            receipt_lineage_sha256=digest(receipt_lineage)),
        selection=dict(alignment_ref=alignment['id'], alignment_record_sha256=digest(alignment),
            source_ref=source['id'], source_record_sha256=digest(source),
            native_artifact=_reference_alignment_artifact(store, source['artifact_ref']),
            grading_artifacts=[_reference_alignment_artifact(store, ref) for ref in grading_refs]),
        producer=dict(run_id=row['producer_run_id'], episode_id=row['producer_episode_id'],
            decision_index=row['producer_decision_index'], operation_key=row['operation_key'],
            operation_ref=row['id'], name=row['name'], arguments=arguments,
            scope=json.loads(row['scope']), operation_outcome_sha256=digest(outcome),
            selected_action_sha256=digest(action), actual_outcome_sha256=digest(actual)))
    return deepcopy(dict(alignment=alignment, source=source, operands=operands,
        arguments=arguments, previews=previews, admission=admission))


def read_selected_reference_alignment(store, context, alignment_ref, *, before_decision_index):
    """Capture one actually received nucleotide alignment without work or grants.

    Original action, receipt, record and scope authentication precedes every
    native/grading byte read. Existing readers validate retained measured cells;
    no aligner or public scientific calculator runs and nothing is recomputed
    for publication. Legacy grading and missing companions remain literal.
    """
    from .tool_grading_artifacts import source_tool_grading_entries

    authority = _selected_reference_alignment_authority(store, context, alignment_ref,
        before_decision_index=before_decision_index)
    alignment, source, operands, arguments, previews = (authority[key] for key in
        ('alignment', 'source', 'operands', 'arguments', 'previews'))
    require = _reference_alignment_require

    # All custody checks above use records and saved actions, never sequence Files.
    descriptor = source_descriptor(store, source, alignment)
    require(descriptor['format'] == 'biopython_pairwise_json', 'source_format_conflict')
    native = _reference_alignment_artifact(store, source['artifact_ref'], read=True)
    require(type(native) is dict and native.get('mode') == arguments['mode'], 'native_model_conflict')
    json.dumps(native, allow_nan=False)
    if native.get('biopython_version') is not None:
        require(native['biopython_version'] == source['version'], 'native_version_conflict')
    for role in operands:
        length = native.get(role + '_length')
        if type(length) is int and length >= 0:
            require(length == operands[role]['length'], 'native_length_conflict')
    require(all(item.get('mode') == arguments['mode'] for item in previews), 'native_preview_conflict')
    entries = source_tool_grading_entries(store, source['id'])
    require(len(entries) <= 1, 'ambiguous_grading')
    grading = correspondence = None
    if entries:
        entry, = entries
        body = _reference_alignment_artifact(store, entry['artifact_ref'], read=True)
        raw = entry['grading']
        require(set(raw) <= {'sheet', 'scores', 'failure'} and {'sheet', 'scores'} <= set(raw)
            and all(raw.get(key) is None or type(raw[key]) is dict for key in ('sheet', 'scores', 'failure')),
            'grading_invalid')
        grading = {key: raw.get(key) for key in ('sheet', 'scores', 'failure')}
        if grading['sheet'] is not None:
            _reference_alignment_sheet(grading['sheet'], native, molecule=arguments['molecule'])
        correspondence = body.get('correspondence')
        # The existing retained-artifact reader already authenticates a present
        # canonical companion. A missing legacy companion remains missing; no
        # scores are promoted and no replacement companion/failure is invented.
    capture = dict(source=descriptor, operands=operands, grading=grading,
        correspondence=correspondence, original_mappings=original_mappings(store, operands))
    json.dumps(capture, allow_nan=False)
    return deepcopy(capture)


def read_quality(store, query_ref):
    """Return the bound original read member's quality and declared encoding."""
    from . import materials_packing as packing
    query = store.get(query_ref)
    if query['record_type'] != 'read_subject':
        return None, 'unspecified'
    member = store.get(query['member_ref'])
    quality = (packing.component_window(store, member, 'quality', 0,
        query['length']).decode('ascii') if query['quality_present'] else None)
    return quality, query['quality_encoding']


def paf_row_bytes(store, source, locator):
    """Validate the retained artifact, then read one exact row with bounded memory."""
    from .materials import artifact_path
    path = artifact_path(store, source['stdout_ref'])
    start, end = locator['row_start'], locator['row_end']
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= path.stat().st_size):
        raise ContractError('native_minimap2_row_locator_conflict')
    with path.open('rb') as handle:
        remaining, lines, last = start, 0, b''
        while remaining:
            data = handle.read(min(1024 * 1024, remaining))
            if not data:
                raise ContractError('native_minimap2_row_locator_conflict')
            remaining -= len(data)
            lines += data.count(b'\n')
            last = data[-1:]
        raw = handle.read(end - start)
    if (start and last != b'\n' or lines + 1 != locator['line_number']
            or end < path.stat().st_size and raw[-1:] != b'\n'
            or b'\n' in raw.rstrip(b'\r\n')):
        raise ContractError('native_minimap2_row_locator_conflict')
    return raw


def reference_operands(store, alignment, body, *, molecule):
    if len(alignment['subject_refs']) != 1 or len(alignment['source_subject_refs']) != 1:
        raise ContractError('site_operand_identity_conflict')
    unit = 'aa' if molecule == 'protein' else 'nt'
    return {role: operand_descriptor(store, reference, alignment_unit=unit,
                                    native_length=body.get(role + '_length'))
            for role, reference in (('query', alignment['subject_refs'][0]),
                                    ('reference', alignment['source_subject_refs'][0]))}


def reference_source_operands(store, alignment, source):
    """Bind the original producer's operands, independently of a new observation.

    New pairwise sources retain the ordered operands. Earlier Biopython
    publications can be proved by their saved original tool operation. Merely
    supplying an observation with a valid hash and equal lengths is not proof.
    """
    query, = alignment['subject_refs']
    reference, = alignment['source_subject_refs']
    expected = list(dict.fromkeys([query, reference]))
    if 'operand_refs' in source:
        if source['operand_refs'] != expected:
            raise ContractError('site_native_source_operand_conflict')
        return
    if source['provider'] != 'biopython.alignment':
        raise ContractError('site_native_source_operands_unavailable')
    rows = store.db.execute("SELECT name,arguments FROM tool_operations WHERE "
        "name IN ('sequence.align','reads.align') "
        "AND json_extract(result,'$.status') IN ('completed','partial') "
        "AND EXISTS(SELECT 1 FROM json_each(result,'$.record_refs') WHERE value=?)",
        (alignment['id'],))
    for row in rows:
        arguments = json.loads(row['arguments'])
        queries = ([arguments['query_ref']] if row['name'] == 'sequence.align'
                   else arguments['subject_refs'])
        if query in queries and reference == arguments['reference_ref']:
            return
    raise ContractError('site_native_source_operand_conflict')


def biopython_molecule(store, source, body):
    from .tool_grading_artifacts import source_tool_gradings
    candidates = [g['sheet'] for g in source_tool_gradings(store, source['id'])
                  if isinstance(g.get('sheet'), dict)
                  and g['sheet'].get('schema') == 'biopython_pairwise_sheet_v1']
    if len(candidates) != 1:
        raise ValueError('site_processing_model_unavailable')
    sheet = candidates[0]
    if not EpisodeReturnRecords._equal(sheet['native_result'], body):
        raise ContractError('site_native_source_conflict')
    molecule = sheet['molecule']
    if molecule not in {'dna', 'rna', 'protein'}:
        raise ContractError('site_processing_model_conflict')
    return molecule


def _reference_result(reader, native, arguments):
    from .alignment_site_calculators import calculate_reference_site_components
    sheet = reader(native, **arguments)
    return {'sheet': sheet, 'scores': calculate_reference_site_components(sheet)}


def reference_grading(store, alignment, selection, *, sequence_reader, grade_result):
    """Supply real native bytes/operands to pure selected-site functions."""
    from .alignment_site_inputs import (extract_biopython_reference_sites,
        extract_phmmer_reference_sites, extract_minimap2_reference_sites)
    source = store.get(alignment['source_ref'])
    immutable_record(alignment)
    immutable_record(source)
    descriptor = source_descriptor(store, source, alignment)
    body = json.loads(store.get_artifact(source['artifact_ref']))
    if source['provider'] in {'biopython.alignment', 'native.phmmer.alignment'}:
        reference_source_operands(store, alignment, source)
        molecule = (biopython_molecule(store, source, body)
                    if source['provider'] == 'biopython.alignment' else 'protein')
        operands = reference_operands(store, alignment, body, molecule=molecule)
        common = {'selection': selection, 'operands': operands, 'source': descriptor,
                  'original_mappings': original_mappings(store, operands)}
        if source['provider'] == 'biopython.alignment':
            reader, arguments = extract_biopython_reference_sites, {**common, 'molecule': molecule}
        else:
            reader, arguments = extract_phmmer_reference_sites, common
    elif source['provider'] == 'minimap2.mapping':
        from .minimap2_grading_inputs import parse_minimap2_paf_row
        native = alignment['native_minimap2']
        row = parse_minimap2_paf_row(paf_row_bytes(store, source, native))
        if (row['query_name'] != alignment['subject_refs'][0]
                or row['reference_name'] != alignment['source_subject_refs'][0]
                or row['strand'] != native['strand']
                or row['mapping_quality'] != native['mapping_quality']
                or row['native_alignment_type'] != native['native_alignment_type']):
            raise ContractError('native_minimap2_operand_identity_mismatch')
        operands = reference_operands(store, alignment, row, molecule='dna')
        for role in ('query', 'reference'):
            expected = [item for item in alignment.get('operand_intervals') or []
                        if item['role'] == role]
            if (len(expected) != 1 or expected[0]['subject_ref'] != operands[role]['subject_ref']
                    or [expected[0]['start'], expected[0]['end']] != row[role + '_interval']):
                raise ContractError('native_minimap2_operand_geometry_conflict')
        metadata = {role: {'name': row[role + '_name'], 'length': row[role + '_length'],
                           'subject_ref': operands[role]['subject_ref'],
                           'sequence': sequence_reader(operands[role]['subject_ref'], molecule_model='dna')}
                    for role in ('query', 'reference')}
        quality, encoding = read_quality(store, operands['query']['subject_ref'])
        reader = extract_minimap2_reference_sites
        arguments = dict(preset=body['settings']['preset'], native_version=body['native_version'],
            selection=selection, query_metadata=metadata['query'],
            reference_metadata=metadata['reference'], source=descriptor,
            quality=quality, quality_encoding=encoding,
            original_mappings=original_mappings(store, operands))
        body = row
    else:
        raise ContractError('native_alignment_site_mapping_unavailable')
    # Host custody errors above remain errors before publication. Only pure
    # grading-input failures enter the existing partial-retention path.
    return grade_result(_reference_result, reader, body, arguments)


def _blast_result(native, arguments):
    from .blast_hsp_site_inputs import extract_blast_hsp_columns
    from .blast_hsp_site_calculators import calculate_blast_hsp_column_components
    sheet = extract_blast_hsp_columns(native, **arguments)
    return {'sheet': sheet, 'scores': calculate_blast_hsp_column_components(sheet)}


def blast_grading(store, observation, source, reference, native, offset, limit, *, grade_result):
    from .blast_search import PROGRAM_UNITS
    if observation.get('native_blast_standard_database') is not None:
        from .native_blast_standard_database_result_publication import validate_standard_blast_database_observation
        validate_standard_blast_database_observation(store, observation)
        raise ContractError('native_blast_standard_database_biological_reference_unavailable')
    if observation.get('native_blast_database') is not None:
        from .native_blast_database_result_publication import validate_native_blast_database_observation
        validate_native_blast_database_observation(store, observation)
        raise ContractError('native_blast_database_biological_reference_unavailable')
    if observation.get('native_blast_pairwise'):
        from .native_blast_hsp_views import native_blast_pairwise_hsp
        bound = native_blast_pairwise_hsp(store, observation)
        if any(not EpisodeReturnRecords._equal(value, bound[key]) for key, value in (
                ('source', source), ('reference', reference), ('native_hsp', native))):
            raise ContractError('site_native_source_conflict')
        program, query_length = bound['program'], bound['query_length']
        descriptor = bound['source_descriptor']
    else:
        metadata = json.loads(store.get_artifact(source['request_ref']))
        request = metadata['request']
        program, query_length = request['algorithm'], request['query_length']
        descriptor = source_descriptor(store, source, observation)
    query_unit, reference_unit, alignment_unit = PROGRAM_UNITS[program]
    operands = {role: operand_descriptor(store, ref, alignment_unit=alignment_unit,
                                        native_length=length)
                for role, ref, length in (
                    ('query', observation['subject_refs'][0], query_length),
                    ('reference', reference['id'], reference['length']))}
    for role, unit in (('query', query_unit), ('reference', reference_unit)):
        if operands[role]['unit'] not in {unit, 'symbol'}:
            raise ContractError('site_operand_identity_conflict')
    arguments = dict(program=program,
        query_length=query_length, reference_length=reference['length'],
        column_offset=offset, column_limit=limit, operands=operands,
        source=descriptor,
        original_mappings=original_mappings(store, operands))
    if observation.get('native_blast', {}).get('shared_projection') is not None:
        from .blast_result_views import _original_hsp, retained_hsp_component
        checked, checked_source, checked_reference, checked_native = _original_hsp(
            store, observation['id'], [observation['id']], None)
        if any(not EpisodeReturnRecords._equal(left, right) for left, right in (
                (observation, checked), (source, checked_source),
                (reference, checked_reference), (native, checked_native))):
            raise ContractError('site_native_source_conflict')
        arguments['whole_hsp_input'] = {
            'binding': observation['native_blast']['shared_projection'],
            'native_locator': descriptor['native_locator'],
            'component': retained_hsp_component(store, observation, source)}
    return grade_result(_blast_result, native, arguments)


def compatibility_sites(sheet):
    """Preserve the existing small view using the checked sheet's rows."""
    mapping = sheet['mode'] == 'minimap2_placement'
    rows = []
    for site in sheet['sites']:
        row = {'reference_position': site['reference_position'],
               'reference_residue': site['reference_symbol'],
               'query_position': site['query_position'], 'query_residue': site['query_symbol'],
               'relationship': 'gap' if site['relationship'] == 'query_gap' else site['relationship']}
        if mapping:
            row['query_strand'] = site['query_strand']
            if site['relationship'] != 'outside_alignment':
                row.update(query_original_residue=site['query_original_symbol'],
                    **{key: site[key] for key in ('query_quality_character', 'query_quality_score',
                        'quality_encoding', 'native_operation')})
        rows.append(row)
    return rows


def compatibility_insertions(sheet):
    """Keep the existing compact insertion view; full ancestry stays in the sheet."""
    encoding = (sheet['native_input']['quality_encoding']
                if sheet['mode'] == 'minimap2_placement' else 'unspecified')
    return [{**{key: row[key] for key in ('reference_boundary', 'query_interval',
        'query_strand', 'query_sequence', 'query_quality_characters')},
        'quality_encoding': encoding, 'native_operation': 'I'}
        for row in sheet['insertions']]


__all__ = ['reference_grading', 'blast_grading', 'source_descriptor',
           'operand_descriptor', 'original_mappings', 'compatibility_sites', 'immutable_record',
           'paf_row_bytes', 'read_quality', 'compatibility_insertions',
           'reference_source_operands', 'read_selected_reference_alignment']
