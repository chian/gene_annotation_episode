"""Closed supplied-input and artifact associations for GenomeAlignment.

These functions validate stored relationships. They do not authenticate custody,
parse native bytes, acquire sequences, select a resource or calculate alignment
scores. Bound staged lengths require the complete explicit component mapping;
the extractor and host must separately establish its actual source evidence.
"""
from copy import deepcopy
import re

from .bvbrc_appservice_contracts import validate_contract
from .phylogeny_calculation_contracts import evidence as _check_evidence
from .phylogeny_format_contracts import _artifact, _location
from .xmfa_source_contracts import validate_xmfa_original_map, validate_xmfa_source_inputs

ASSOCIATION_STATES = ('bound', 'missing', 'unverified', 'conflicting')
NAMESPACES = ('mauve1_member_1based', 'mauve_v4_member_0based', 'mauve_sidecar_member_0based')
FORMATS = ('mauve1_xmfa', 'mauve_v4', 'mauve_backbone', 'mauve_bbcols',
           'p3_mauve_visualization_json')
ROLES = ('genome_alignment_primary', 'genome_alignment_backbone',
         'genome_alignment_bbcols', 'genome_alignment_visualization')
DIAGNOSTIC_CODES = frozenset('bvbrc_genome_alignment_' + code for code in '''
argument_invalid original_task_invalid application_mismatch genome_input_missing
genome_occurrence_conflict duplicate_genome_occurrence recipe_conflict
explicit_zero_not_forwarded source_option_unsupported invocation_missing
invocation_conflict metadata_type_unsupported metadata_record_unverified
metadata_task_conflict content_missing content_digest_conflict staged_file_missing
staged_file_run_unverified native_path_missing native_path_conflict
source_records_partial source_sequence_mismatch source_span_outside_input
genome_census_unknown contig_identity_missing contig_identity_conflict
feature_map_missing feature_map_conflict artifact_task_conflict
artifact_version_unverified artifact_role_conflict artifact_format_conflict
primary_output_missing duplicate_representation member_join_missing
member_join_conflict interval_join_missing interval_join_conflict
native_execution_unverified
'''.split())
_DNA = re.compile(r'[ACGTRYSWKMBDHVNacgtryswkmbdhvn]*\Z')


def _require(condition, code='argument_invalid'):
    if not condition:
        raise ValueError('bvbrc_genome_alignment_' + code)


def _shape(value, fields):
    _require(type(value) is dict and set(value) == set(fields))


def _array(value):
    _require(type(value) is list)


def _text(value, *, nullable=False, empty=False):
    _require(nullable and value is None or type(value) is str and (empty or bool(value)))


def _integer(value, *, nullable=False, minimum=0):
    _require(nullable and value is None or type(value) is int and value >= minimum)


def _enum(value, choices, *, nullable=False):
    _require(nullable and value is None or type(value) is str and value in choices)


def _strings(value, *, unique=True, empty=False):
    _array(value)
    for item in value:
        _text(item, empty=empty)
    _require(not unique or len(value) == len(set(value)))


def _indices(value, *, allowed=None):
    _array(value)
    for item in value:
        _integer(item)
    _require(len(value) == len(set(value)))
    _require(allowed is None or set(value) <= set(allowed), 'genome_occurrence_conflict')


def _interval(value):
    _array(value)
    _require(len(value) == 2)
    for item in value:
        _integer(item)
    _require(value[0] <= value[1], 'source_span_outside_input')


def _evidence(value):
    try:
        _check_evidence(value)
    except ValueError as error:
        raise ValueError('bvbrc_genome_alignment_metadata_record_unverified') from error


def _reports(value):
    _array(value['requirements'])
    _array(value['diagnostics'])
    ids = []
    for row in value['requirements']:
        validate_contract('AcquisitionRequirement', row)
        _require(row['reason_code'] in DIAGNOSTIC_CODES)
        ids.append(row['requirement_id'])
    _require(len(ids) == len(set(ids)))
    for row in value['diagnostics']:
        validate_contract('Diagnostic', row)
        _require(row['code'] in DIAGNOSTIC_CODES)
    return set(ids)


def _requirement_refs(value, declared):
    _strings(value)
    _require(set(value) <= declared)


def validate_genome_alignment_native_member(value):
    """Validate a namespace-qualified native ordinal, without mapping it."""
    _shape(value, ('namespace', 'index'))
    _enum(value['namespace'], NAMESPACES)
    _integer(value['index'], minimum=1 if value['namespace'] == 'mauve1_member_1based' else 0)
    return deepcopy(value)


def _member_key(value):
    validate_genome_alignment_native_member(value)
    return value['namespace'], value['index']


def _occurrence(value):
    _shape(value, ('input_binding_id', 'member_id', 'occurrence_index'))
    _text(value['input_binding_id'])
    _text(value['member_id'])
    _integer(value['occurrence_index'])
    return tuple(value[k] for k in ('input_binding_id', 'member_id', 'occurrence_index'))


def _task(value):
    validate_contract('OriginalTask', value)
    _require(value['required_application_id'] == value['native_application_id'] == 'GenomeAlignment',
             'application_mismatch')
    ids = value['submitted_parameters'].get('genome_ids')
    _require(type(ids) is list and bool(ids) and all(type(x) is str and x for x in ids),
             'genome_input_missing')
    return ids


def _retrieval(value):
    _shape(value, ('query', 'requested_record_limit', 'reported_total_records',
                   'returned_records', 'state', 'evidence'))
    _text(value['query'], nullable=True, empty=True)
    _integer(value['requested_record_limit'], nullable=True)
    _integer(value['reported_total_records'], nullable=True)
    _integer(value['returned_records'])
    _enum(value['state'], ('complete', 'partial', 'unknown', 'conflicting'))
    _evidence(value['evidence'])
    if value['state'] == 'complete':
        _require(value['reported_total_records'] is not None and
                 value['reported_total_records'] == value['returned_records'] and
                 bool(value['evidence']), 'genome_census_unknown')


def _file(value, occurrences, requirements):
    _shape(value, ('file_id', 'native_path_token', 'path_state', 'artifact', 'content',
        'format', 'genome_occurrence_indices', 'same_run_state', 'record_completeness',
        'records', 'retrieval', 'path_evidence', 'same_run_evidence', 'requirement_ids'))
    _text(value['file_id'])
    _text(value['native_path_token'], nullable=True)
    _enum(value['path_state'], ASSOCIATION_STATES)
    _enum(value['same_run_state'], ASSOCIATION_STATES)
    _require(value['format'] == 'FastA')
    _indices(value['genome_occurrence_indices'], allowed=occurrences)
    _enum(value['record_completeness'], ('complete', 'partial', 'unknown'))
    _array(value['records'])
    _retrieval(value['retrieval'])
    _evidence(value['path_evidence'])
    _evidence(value['same_run_evidence'])
    _requirement_refs(value['requirement_ids'], requirements)
    _require((value['artifact'] is None) == (value['content'] is None), 'content_missing')
    if value['artifact'] is None:
        _require(not value['records'] and value['record_completeness'] != 'complete', 'content_missing')
    else:
        _artifact(value['artifact'])
        validate_contract('ContentBinding', value['content'])
        artifact, content = value['artifact'], value['content']
        _require(artifact['source_ref'] == content['source_ref'] and
                 artifact['raw_artifact_ref'] == content['artifact_ref'] and
                 artifact['sha256'] == content['sha256'], 'content_digest_conflict')
    if value['path_state'] == 'bound':
        _require(value['native_path_token'] is not None and bool(value['path_evidence']),
                 'native_path_missing')
    if value['same_run_state'] == 'bound':
        _require(value['artifact'] is not None and bool(value['same_run_evidence']),
                 'staged_file_run_unverified')
    ids, entries = set(), []
    for record in value['records']:
        _shape(record, ('record_id', 'entry_1based', 'header', 'sequence', 'source_location'))
        _text(record['record_id'])
        _integer(record['entry_1based'], minimum=1)
        _text(record['header'], nullable=True, empty=True)
        _text(record['sequence'], empty=True)
        _require(_DNA.fullmatch(record['sequence']) is not None, 'source_sequence_mismatch')
        _location(record['source_location'], artifact=value['artifact'])
        location = record['source_location']
        _require(location['xml_path'] is None and all(type(location[k]) is int for k in
            ('byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based',
             'line_end_1based_inclusive')), 'content_missing')
        _require(location['byte_end_0based_exclusive'] <= value['content']['byte_count'],
                 'source_span_outside_input')
        _require(record['record_id'] not in ids, 'source_records_partial')
        ids.add(record['record_id'])
        entries.append(record['entry_1based'])
    _require(entries == sorted(set(entries)), 'source_records_partial')
    if value['record_completeness'] == 'complete':
        _require(entries == list(range(1, len(entries) + 1)), 'source_records_partial')
        _require(len(entries) == value['retrieval']['returned_records'], 'source_records_partial')


def _invocation(value, original, files):
    _shape(value, ('requested_recipe', 'effective_recipe', 'recipe_basis', 'observed_argv',
        'observed_program_version', 'mode', 'mode_basis', 'ordered_file_ids', 'evidence'))
    recipes = ('progressiveMauve', 'mauveAligner')
    _enum(value['requested_recipe'], recipes, nullable=True)
    _enum(value['effective_recipe'], recipes, nullable=True)
    _enum(value['recipe_basis'], ('observed_argv', 'retained_source_default', 'unknown', 'conflicting'))
    _enum(value['mode'], ('multiple_files_concatenated', 'single_file_entries', 'unknown'))
    _enum(value['mode_basis'], ('observed_invocation', 'source_and_submitted_parameters',
                              'unknown', 'conflicting'))
    _text(value['observed_program_version'], nullable=True)
    if value['observed_argv'] is not None:
        _strings(value['observed_argv'], unique=False, empty=True)
        _require(bool(value['observed_argv']), 'invocation_conflict')
    _strings(value['ordered_file_ids'], unique=False)
    _require(set(value['ordered_file_ids']) <= set(files), 'staged_file_missing')
    _evidence(value['evidence'])
    requested = original['submitted_parameters'].get('recipe')
    if requested in recipes:
        _require(value['requested_recipe'] == requested, 'recipe_conflict')
    else:
        _require(value['requested_recipe'] is None, 'recipe_conflict')
    if value['recipe_basis'] == 'observed_argv':
        _require(value['observed_argv'] is not None and value['effective_recipe'] is not None
                 and bool(value['evidence']), 'invocation_missing')
    if value['mode_basis'] == 'observed_invocation':
        _require(value['observed_argv'] is not None and bool(value['evidence']), 'invocation_missing')
    if value['mode'] == 'single_file_entries':
        _require(len(value['ordered_file_ids']) == 1, 'invocation_conflict')
    elif value['mode'] == 'multiple_files_concatenated':
        _require(len(value['ordered_file_ids']) > 1, 'invocation_conflict')


def _component(value, files):
    _shape(value, ('file_id', 'record_id', 'member_interval_0based_half_open',
                   'record_interval_0based_half_open'))
    _text(value['file_id'])
    _text(value['record_id'])
    _require(value['file_id'] in files, 'staged_file_missing')
    records = {r['record_id']: r for r in files[value['file_id']]['records']}
    _require(value['record_id'] in records, 'source_records_partial')
    _interval(value['member_interval_0based_half_open'])
    _interval(value['record_interval_0based_half_open'])
    a, b = value['member_interval_0based_half_open']
    x, y = value['record_interval_0based_half_open']
    _require(b-a == y-x and y <= len(records[value['record_id']]['sequence']),
             'source_span_outside_input')


def _member_binding(value, invocation, files, occurrences, requirements):
    _shape(value, ('member', 'state', 'genome_occurrence_indices', 'components',
                   'source_length', 'evidence', 'requirement_ids'))
    key = _member_key(value['member'])
    _enum(value['state'], ASSOCIATION_STATES)
    _indices(value['genome_occurrence_indices'], allowed=occurrences)
    _array(value['components'])
    _integer(value['source_length'], nullable=True)
    _evidence(value['evidence'])
    _requirement_refs(value['requirement_ids'], requirements)
    for component in value['components']:
        _component(component, files)
    if value['state'] != 'bound':
        _require(value['source_length'] is None, 'staged_file_run_unverified')
        return key
    _require(bool(value['evidence']) and bool(value['components']) and
             value['source_length'] is not None, 'member_join_missing')
    native_index = value['member']['index'] - (value['member']['namespace'] == 'mauve1_member_1based')
    mode = invocation['mode']
    order = invocation['ordered_file_ids']
    _require(mode != 'unknown' and bool(invocation['evidence']), 'invocation_missing')
    if mode == 'multiple_files_concatenated':
        _require(native_index < len(order), 'member_join_conflict')
        file_id = order[native_index]
        expected_records = files[file_id]['records']
    else:
        file_id = order[0]
        expected_records = [r for r in files[file_id]['records'] if r['entry_1based'] == native_index + 1]
        _require(len(expected_records) == 1, 'member_join_conflict')
    file = files[file_id]
    _require(file['same_run_state'] == file['path_state'] == 'bound' and
             file['record_completeness'] == 'complete', 'staged_file_run_unverified')
    _require(value['genome_occurrence_indices'] == file['genome_occurrence_indices'],
             'genome_occurrence_conflict')
    _require(len(value['components']) == len(expected_records), 'source_records_partial')
    cursor = 0
    for component, record in zip(value['components'], expected_records):
        length = len(record['sequence'])
        _require(component == {'file_id': file_id, 'record_id': record['record_id'],
            'member_interval_0based_half_open': [cursor, cursor + length],
            'record_interval_0based_half_open': [0, length]}, 'member_join_conflict')
        cursor += length
    _require(value['source_length'] == cursor, 'source_span_outside_input')
    return key


def _feature_segment(value, *, files=None, length=None):
    _shape(value, ('segment_id', 'file_id', 'record_id', 'feature_interval_0based_half_open',
                   'record_interval_0based_half_open', 'strand', 'transformation_id', 'evidence'))
    for key in ('segment_id', 'file_id', 'record_id', 'transformation_id'):
        _text(value[key])
    _interval(value['feature_interval_0based_half_open'])
    _interval(value['record_interval_0based_half_open'])
    _enum(value['strand'], ('+', '-'))
    _evidence(value['evidence'])
    a, b = value['feature_interval_0based_half_open']
    x, y = value['record_interval_0based_half_open']
    _require(b-a == y-x and (length is None or b <= length), 'feature_map_conflict')
    if files is not None:
        _require(value['file_id'] in files, 'feature_map_missing')
        records = {r['record_id']: r for r in files[value['file_id']]['records']}
        _require(value['record_id'] in records, 'feature_map_missing')
        _require(y <= len(records[value['record_id']]['sequence']), 'source_span_outside_input')


def _contigs_features(value, files, occurrences, requirements):
    contig_keys = set()
    for row in value['contig_bindings']:
        _shape(row, ('file_id', 'record_id', 'sequence_id', 'accession', 'accession_version',
                     'genome_occurrence_indices', 'state', 'evidence', 'requirement_ids'))
        for key in ('file_id', 'record_id'):
            _text(row[key])
        for key in ('sequence_id', 'accession', 'accession_version'):
            _text(row[key], nullable=True)
        _indices(row['genome_occurrence_indices'], allowed=occurrences)
        _enum(row['state'], ASSOCIATION_STATES)
        _evidence(row['evidence'])
        _requirement_refs(row['requirement_ids'], requirements)
        key = row['file_id'], row['record_id']
        _require(key not in contig_keys, 'contig_identity_conflict')
        contig_keys.add(key)
        _require(row['file_id'] in files, 'contig_identity_missing')
        file = files[row['file_id']]
        _require(row['record_id'] in {r['record_id'] for r in file['records']}, 'contig_identity_missing')
        _require(set(row['genome_occurrence_indices']) <= set(file['genome_occurrence_indices']),
                 'genome_occurrence_conflict')
        if row['state'] == 'bound':
            _require(bool(row['evidence']) and any(row[k] is not None for k in
                ('sequence_id', 'accession', 'accession_version')), 'contig_identity_missing')
            _require(file['same_run_state'] == 'bound' and bool(row['genome_occurrence_indices']),
                     'staged_file_run_unverified')
    feature_keys, maps = set(), []
    for row in value['feature_bindings']:
        _shape(row, ('feature', 'original_length', 'genome_occurrence_index', 'segments',
                     'state', 'evidence', 'requirement_ids'))
        key = _occurrence(row['feature'])
        _require(key not in feature_keys, 'feature_map_conflict')
        feature_keys.add(key)
        _integer(row['original_length'], nullable=True)
        _integer(row['genome_occurrence_index'])
        _require(row['genome_occurrence_index'] in occurrences, 'genome_occurrence_conflict')
        _enum(row['state'], ASSOCIATION_STATES)
        _evidence(row['evidence'])
        _requirement_refs(row['requirement_ids'], requirements)
        _array(row['segments'])
        segment_ids = set()
        for segment in row['segments']:
            _feature_segment(segment, files=files, length=row['original_length'])
            _require(segment['segment_id'] not in segment_ids, 'feature_map_conflict')
            segment_ids.add(segment['segment_id'])
            _require(row['genome_occurrence_index'] in files[segment['file_id']]['genome_occurrence_indices'],
                     'genome_occurrence_conflict')
            if row['state'] == 'bound':
                _require(bool(segment['evidence']) and files[segment['file_id']]['same_run_state'] == 'bound',
                         'feature_map_missing')
                if row['original_length'] is not None:
                    maps.append({'file_id': segment['file_id'], 'record_id': segment['record_id'],
                        'staged_interval_0based_half_open': segment['record_interval_0based_half_open'],
                        'original_member': row['feature'], 'original_length': row['original_length'],
                        'original_interval_0based_half_open': segment['feature_interval_0based_half_open'],
                        'strand': segment['strand'], 'transformation_id': segment['transformation_id'],
                        'evidence': segment['evidence']})
        if row['state'] == 'bound':
            _require(bool(row['evidence']) and bool(row['segments']), 'feature_map_missing')
    for mapping in value['original_maps']:
        validate_xmfa_original_map(mapping)
        _require(mapping in maps, 'feature_map_conflict')


def validate_genome_alignment_inputs(value):
    """Validate exact C input records; return detached data without I/O."""
    _shape(value, ('schema_version', 'original_task', 'genome_occurrences', 'invocation', 'files',
        'member_bindings', 'contig_bindings', 'feature_bindings', 'original_maps',
        'xmfa_source_inputs', 'genome_census_state', 'requirements', 'diagnostics'))
    _require(value['schema_version'] == 'bvbrc_genome_alignment_inputs_v1')
    genome_ids = _task(value['original_task'])
    requirements = _reports(value)
    for field in ('genome_occurrences', 'files', 'member_bindings', 'contig_bindings',
                  'feature_bindings', 'original_maps'):
        _array(value[field])
    _require(len(value['genome_occurrences']) == len(genome_ids), 'genome_occurrence_conflict')
    for index, row in enumerate(value['genome_occurrences']):
        _shape(row, ('occurrence_index', 'genome_id', 'parameter_pointer', 'input_binding_id', 'evidence'))
        _integer(row['occurrence_index'])
        _text(row['genome_id'])
        _text(row['parameter_pointer'])
        _text(row['input_binding_id'], nullable=True)
        _evidence(row['evidence'])
        _require(row['occurrence_index'] == index and row['genome_id'] == genome_ids[index] and
                 row['parameter_pointer'] == '/genome_ids/' + str(index), 'genome_occurrence_conflict')
    occurrences, files = set(range(len(genome_ids))), {}
    for file in value['files']:
        _file(file, occurrences, requirements)
        _require(file['file_id'] not in files, 'native_path_conflict')
        files[file['file_id']] = file
    _invocation(value['invocation'], value['original_task'], files)
    member_keys = set()
    for member in value['member_bindings']:
        key = _member_binding(member, value['invocation'], files, occurrences, requirements)
        _require(key not in member_keys, 'member_join_conflict')
        member_keys.add(key)
    _contigs_features(value, files, occurrences, requirements)
    neutral = value['xmfa_source_inputs']
    if neutral is not None:
        validate_xmfa_source_inputs(neutral)
        _require(neutral['invocation'] == {k: value['invocation'][k] for k in
            ('mode', 'ordered_file_ids', 'evidence')}, 'invocation_conflict')
        _require(neutral['original_maps'] == value['original_maps'], 'feature_map_conflict')
        for file in neutral['files']:
            _require(file['file_id'] in files, 'staged_file_missing')
            source = files[file['file_id']]
            _require(source['same_run_state'] == source['path_state'] == 'bound', 'staged_file_run_unverified')
            _require(file == {k: source[k] for k in ('file_id', 'native_path_token', 'artifact',
                'format', 'record_completeness', 'records')} | {'path_binding_evidence': source['path_evidence']},
                'source_sequence_mismatch')
    _enum(value['genome_census_state'], ('complete', 'partial', 'unknown', 'conflicting'))
    if value['genome_census_state'] == 'complete':
        _require(bool(files) and set().union(*(set(f['genome_occurrence_indices']) for f in files.values())) == occurrences
            and all(f['same_run_state'] == 'bound' and f['record_completeness'] == 'complete'
                    and f['retrieval']['state'] == 'complete' for f in files.values()), 'genome_census_unknown')
    return deepcopy(value)


def validate_genome_alignment_associations(value):
    """Validate exact artifact/member/interval associations without guessing joins."""
    _shape(value, ('schema_version', 'original_task', 'artifacts', 'native_member_joins',
                   'bbcols_interval_joins', 'duplicate_representations', 'requirements', 'diagnostics'))
    _require(value['schema_version'] == 'bvbrc_genome_alignment_associations_v1')
    _task(value['original_task'])
    requirements = _reports(value)
    for key in ('artifacts', 'native_member_joins', 'bbcols_interval_joins', 'duplicate_representations'):
        _array(value[key])
    artifacts, documents = {}, {}
    role_formats = {'genome_alignment_primary': ('mauve1_xmfa', 'mauve_v4'),
        'genome_alignment_backbone': ('mauve_backbone',), 'genome_alignment_bbcols': ('mauve_bbcols',),
        'genome_alignment_visualization': ('p3_mauve_visualization_json',)}
    for row in value['artifacts']:
        _shape(row, ('artifact', 'role', 'observed_format', 'document_id', 'state', 'evidence', 'requirement_ids'))
        validate_contract('ArtifactMember', row['artifact'])
        _enum(row['role'], ROLES)
        _enum(row['observed_format'], FORMATS, nullable=True)
        _text(row['document_id'], nullable=True)
        _enum(row['state'], ASSOCIATION_STATES)
        _evidence(row['evidence'])
        _requirement_refs(row['requirement_ids'], requirements)
        artifact = row['artifact']
        key = artifact['raw_artifact_ref'], artifact['source_ref'], artifact['sha256']
        _require(key not in artifacts, 'duplicate_representation')
        artifacts[key] = row
        if row['document_id'] is not None:
            _require(row['document_id'] not in documents, 'duplicate_representation')
            documents[row['document_id']] = row
        if row['state'] == 'bound':
            _require(artifact['task_association']['task_id'] == value['original_task']['task_id'],
                     'artifact_task_conflict')
            _require(artifact['role'] == row['role'], 'artifact_role_conflict')
            _require(row['observed_format'] in role_formats[row['role']], 'artifact_format_conflict')
            _require(artifact['declared_format']['format'] == row['observed_format'],
                     'artifact_format_conflict')
            expected_version = {'mauve1_xmfa': 'Mauve1', 'mauve_v4': '4'}.get(row['observed_format'])
            if expected_version is not None:
                _require(artifact['declared_format']['version'] in (None, expected_version),
                         'artifact_format_conflict')
            _require(bool(row['evidence']), 'artifact_version_unverified')
            if row['role'] != 'genome_alignment_visualization':
                _require(row['document_id'] is not None, 'primary_output_missing')
    member_joins = set()
    for row in value['native_member_joins']:
        _shape(row, ('artifact', 'member', 'input_member', 'state', 'evidence', 'requirement_ids'))
        _artifact(row['artifact'])
        key = tuple(row['artifact'][k] for k in ('raw_artifact_ref', 'source_ref', 'sha256'))
        _require(key in artifacts, 'member_join_missing')
        member = _member_key(row['member'])
        _enum(row['state'], ASSOCIATION_STATES)
        _evidence(row['evidence'])
        _requirement_refs(row['requirement_ids'], requirements)
        if row['input_member'] is not None:
            _member_key(row['input_member'])
        _require((key, member) not in member_joins, 'member_join_conflict')
        member_joins.add((key, member))
        if row['state'] == 'bound':
            _require(row['input_member'] is not None and bool(row['evidence']) and
                     artifacts[key]['state'] == 'bound', 'member_join_missing')
            expected_namespace = {'mauve1_xmfa': 'mauve1_member_1based',
                'mauve_v4': 'mauve_v4_member_0based', 'mauve_backbone': 'mauve_sidecar_member_0based',
                'mauve_bbcols': 'mauve_sidecar_member_0based'}.get(artifacts[key]['observed_format'])
            _require(member[0] == expected_namespace, 'member_join_conflict')
    interval_joins, bound_targets = set(), set()
    for row in value['bbcols_interval_joins']:
        _shape(row, ('bbcols_document_id', 'native_interval_index_0based', 'xmfa_document_id',
                     'xmfa_block_index', 'state', 'evidence', 'requirement_ids'))
        _text(row['bbcols_document_id'])
        _integer(row['native_interval_index_0based'])
        _text(row['xmfa_document_id'], nullable=True)
        _integer(row['xmfa_block_index'], nullable=True)
        _enum(row['state'], ASSOCIATION_STATES)
        _evidence(row['evidence'])
        _requirement_refs(row['requirement_ids'], requirements)
        _require(row['bbcols_document_id'] in documents and
                 documents[row['bbcols_document_id']]['observed_format'] == 'mauve_bbcols',
                 'interval_join_missing')
        key = row['bbcols_document_id'], row['native_interval_index_0based']
        _require(key not in interval_joins, 'interval_join_conflict')
        interval_joins.add(key)
        _require((row['xmfa_document_id'] is None) == (row['xmfa_block_index'] is None),
                 'interval_join_conflict')
        if row['xmfa_document_id'] is not None:
            _require(row['xmfa_document_id'] in documents and
                     documents[row['xmfa_document_id']]['observed_format'] == 'mauve1_xmfa',
                     'interval_join_conflict')
        if row['state'] == 'bound':
            _require(row['xmfa_document_id'] is not None and bool(row['evidence']) and
                documents[row['bbcols_document_id']]['state'] == 'bound' and
                documents[row['xmfa_document_id']]['state'] == 'bound', 'interval_join_missing')
            target = row['bbcols_document_id'], row['xmfa_document_id'], row['xmfa_block_index']
            _require(target not in bound_targets, 'interval_join_conflict')
            bound_targets.add(target)
    duplicate_hashes = set()
    for row in value['duplicate_representations']:
        _shape(row, ('sha256', 'raw_artifact_refs', 'source_refs', 'scientific_identity'))
        _require(type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None)
        _strings(row['raw_artifact_refs'])
        _strings(row['source_refs'])
        _enum(row['scientific_identity'], ('same_bytes_only', 'same_original_task_bytes'))
        _require(row['sha256'] not in duplicate_hashes, 'duplicate_representation')
        duplicate_hashes.add(row['sha256'])
        matched = [r['artifact'] for r in artifacts.values() if r['artifact']['sha256'] == row['sha256']
            and r['artifact']['raw_artifact_ref'] in row['raw_artifact_refs']
            and r['artifact']['source_ref'] in row['source_refs']]
        _require(len(matched) > 1 and {r['raw_artifact_ref'] for r in matched} == set(row['raw_artifact_refs'])
            and {r['source_ref'] for r in matched} == set(row['source_refs']), 'duplicate_representation')
        if row['scientific_identity'] == 'same_original_task_bytes':
            _require(all(r['task_association']['task_id'] == value['original_task']['task_id']
                         for r in matched), 'artifact_task_conflict')
    return deepcopy(value)


__all__ = ['validate_genome_alignment_inputs', 'validate_genome_alignment_associations',
           'validate_genome_alignment_native_member']
