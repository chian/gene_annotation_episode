"""Bind selected retained alignments to explicit numerical-grader inputs.

This host adapter reads actual assigned records and retained artifacts. It never
executes an aligner, chooses a result, acquires a reference or assigns credit.
"""
from __future__ import annotations

import json

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
           'reference_source_operands']
