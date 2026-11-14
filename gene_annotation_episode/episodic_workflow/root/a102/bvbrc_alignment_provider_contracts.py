"""Closed pure provider records for BV-BRC MSA and MetaCATS associations.

These checks establish supplied relationships, not custody. They neither read
artifacts nor choose work, and do not calculate biological scores.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from functools import wraps
import hashlib
import math
import re
from urllib.parse import quote, unquote

from . import phylogeny_calculation_contracts as shared
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_alignment_values import diagnostic, requirement
from .phylogeny_format_contracts import _artifact, _location, validate_alignment_document, validate_tree_record
from .bvbrc_msa_format_contracts import validate_msa_frequency_table
from .xmfa_format_contracts import validate_xmfa_document
from .bvbrc_metacats_format_contracts import (
    validate_metacats_chisq_table, validate_metacats_pair_table,
    validate_metacats_raw_r_table, validate_metacats_metadata,
    validate_metacats_adjusted_matrix,
)

PREFIX = 'bvbrc_alignment_provider_'
COMPLETENESS = ('complete', 'partial', 'truncated', 'unknown')
MOLECULES = ('dna', 'rna', 'protein', 'mixed', 'unknown')
ASSOCIATION_KEYS = ('original_members', 'inline_inputs', 'row_members', 'transformations',
    'correspondences', 'feature_genomes', 'source_records', 'functions',
    'function_equivalences', 'taxonomy', 'member_entities', 'dependence_groups', 'requirements', 'diagnostics')


def require(condition, code):
    if not condition:
        raise ValueError(PREFIX + code)


def closed(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as exc:
            if str(exc).startswith(PREFIX):
                raise
            raise ValueError(PREFIX + 'dependency_invalid') from exc
        except (KeyError, TypeError, IndexError, OverflowError, UnicodeError, RecursionError) as exc:
            raise ValueError(PREFIX + 'shape_invalid') from exc
    return checked


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'shape_invalid')


def text(value, *, empty=False, nullable=False):
    require(nullable and value is None or type(value) is str and (empty or bool(value)), 'text_invalid')


def integer(value, *, minimum=0, nullable=False):
    require(nullable and value is None or type(value) is int and value >= minimum, 'integer_invalid')


def array(value):
    require(type(value) is list, 'array_invalid')


def strings(value):
    array(value)
    for item in value:
        text(item)
    require(len(value) == len(set(value)), 'duplicate_identifier')


def indices(value):
    array(value)
    for item in value:
        integer(item)
    require(len(value) == len(set(value)), 'duplicate_index')


def pointer(value):
    text(value, empty=True)
    require((not value or value.startswith('/')) and re.search(r'~(?![01])', value) is None, 'pointer_invalid')


def evidence(value):
    shared.evidence(value)


def unique(values, key):
    array(values)
    result = {}
    for row in values:
        identity = key(row) if callable(key) else row[key]
        require(identity not in result, 'duplicate_record')
        result[identity] = row
    return result


def reports(value):
    unique(value['requirements'], 'requirement_id')
    for row in value['requirements']:
        shape(row, ('requirement_id', 'kind', 'role', 'source_refs', 'reason_code'))
        require(requirement(**row) == row, 'requirement_invalid')
    array(value['diagnostics'])
    for row in value['diagnostics']:
        shape(row, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        pointer(row['path'])
        require(diagnostic(**row) == row, 'diagnostic_invalid')


def member_key(value):
    shape(value, ('input_binding_id', 'member_id', 'occurrence_index'))
    text(value['input_binding_id']); text(value['member_id']); integer(value['occurrence_index'])
    return value['input_binding_id'], value['member_id'], value['occurrence_index']


def occurrence_id(binding, member, occurrence):
    text(binding); text(member); integer(occurrence)
    return 'input_member_occurrence:' + quote(binding, safe='') + '/' + quote(member, safe='') + '/' + str(occurrence)


def document_identity(document):
    value = document['value']
    return value.get('alignment_id', value.get('table_id', value.get('document_id')))


@closed
def validate_parsed_document(value: dict) -> dict:
    shape(value, ('kind', 'value'))
    readers = {'alignment': validate_alignment_document, 'msa_frequency': validate_msa_frequency_table,
        'metacats_chisq': validate_metacats_chisq_table, 'metacats_pair': validate_metacats_pair_table,
        'metacats_raw_r': validate_metacats_raw_r_table, 'metadata': validate_metacats_metadata,
        'adjusted_matrix': validate_metacats_adjusted_matrix, 'xmfa': validate_xmfa_document}
    text(value['kind'])
    if value['kind'] == 'tree':
        tree = value['value']
        shape(tree, ('document_id', 'artifact', 'format', 'dialect', 'completeness', 'trees'))
        _artifact(tree['artifact'])
        require(tree['document_id'] == tree['artifact']['raw_artifact_ref'] + '#tree_document', 'tree_identity_conflict')
        require(tree['format'] == 'newick' and tree['dialect'] in ('newick', 'raxml_branch_labels', 'bvbrc_double_quoted_names'), 'tree_format_invalid')
        require(tree['completeness'] in COMPLETENESS, 'completeness_invalid')
        unique(tree['trees'], 'tree_id')
        previous = -1
        for row in tree['trees']:
            validate_tree_record(row)
            require(row['document_id'] == tree['document_id'] and row['source_format'] == 'newick'
                    and row['source_location']['artifact'] == tree['artifact'], 'tree_document_conflict')
            require(row['tree_index'] > previous, 'tree_order_invalid'); previous = row['tree_index']
    else:
        require(value['kind'] in readers, 'document_kind_invalid')
        readers[value['kind']](value['value'])
    return deepcopy(value)


def document_maps(documents):
    require(type(documents) in (tuple, list), 'documents_invalid')
    docs, alignments, trees = {}, {}, {}
    for document in documents:
        validate_parsed_document(document)
        identity = document_identity(document)
        require(identity not in docs, 'duplicate_document'); docs[identity] = document
        if document['kind'] == 'alignment':
            alignments[identity] = document['value']
        elif document['kind'] == 'tree':
            for tree in document['value']['trees']:
                require(tree['tree_id'] not in trees, 'duplicate_tree'); trees[tree['tree_id']] = tree
    return docs, alignments, trees


READERS = {
    'aligned_fasta': {'id_rule', 'encoding'}, 'metacats_input_fasta': {'id_rule', 'encoding'},
    'msa_frequency': {'alphabet', 'layout', 'encoding'},
    'metacats_chisq': {'layout', 'category_id', 'encoding'},
    'metacats_pair': {'layout', 'category_id', 'encoding'},
    'metacats_raw_r': {'kind', 'layout', 'category_id', 'encoding'},
    'metacats_metadata': {'delimiter', 'header', 'encoding'},
    'metacats_adjusted_matrix': {'category_id', 'encoding'},
    'newick': {'dialect', 'allow_multiple'},
    'mauve_xmfa_v1': {'dialect', 'alphabet', 'encoding'},
}
READER_KINDS = {'aligned_fasta': 'alignment', 'metacats_input_fasta': 'alignment',
    'msa_frequency': 'msa_frequency', 'metacats_chisq': 'metacats_chisq',
    'metacats_pair': 'metacats_pair', 'metacats_raw_r': 'metacats_raw_r',
    'metacats_metadata': 'metadata', 'metacats_adjusted_matrix': 'adjusted_matrix', 'newick': 'tree', 'mauve_xmfa_v1': 'xmfa'}


@closed
def validate_reader_spec(value: dict, *, provider: str) -> dict:
    require(provider in ('msa', 'metacats'), 'provider_invalid')
    require(type(value) is dict and type(value.get('reader')) is str and value['reader'] in READERS, 'reader_invalid')
    reader = value['reader']; shape(value, READERS[reader] | {'reader'})
    allowed = ('aligned_fasta', 'msa_frequency', 'newick', 'mauve_xmfa_v1') if provider == 'msa' else tuple(r for r in READERS if r.startswith('metacats_')) + ('aligned_fasta',)
    require(reader in allowed, 'reader_provider_conflict')
    if 'encoding' in value:
        require(value['encoding'] in ('ascii', 'utf-8'), 'encoding_invalid')
    if 'id_rule' in value:
        require(value['id_rule'] == 'first_whitespace_token', 'id_rule_invalid')
    if 'category_id' in value:
        text(value['category_id'])
    if reader == 'msa_frequency':
        require(value['alphabet'] in ('dna', 'protein') and value['layout'] in ('current_without_reference', 'current_with_reference'), 'reader_parameter_invalid')
    elif reader == 'metacats_chisq':
        require(value['layout'] in ('current_filtered_tsv', 'legacy_example_tsv'), 'reader_parameter_invalid')
    elif reader == 'metacats_pair':
        require(value['layout'] == 'current_filtered_tsv', 'reader_parameter_invalid')
    elif reader == 'metacats_raw_r':
        require(value['layout'] == 'r_write_table_single_result_string' and value['kind'] in ('omnibus', 'pairwise'), 'reader_parameter_invalid')
    elif reader == 'metacats_metadata':
        require(value['delimiter'] == 'tab' and value['header'] in ('present', 'absent'), 'reader_parameter_invalid')
    elif reader == 'newick':
        require(value['dialect'] in ('newick', 'raxml_branch_labels', 'bvbrc_double_quoted_names') and type(value['allow_multiple']) is bool, 'reader_parameter_invalid')
    elif reader == 'mauve_xmfa_v1':
        require(value['dialect'] == 'mauve1' and value['alphabet'] == 'dna', 'reader_parameter_invalid')
    return deepcopy(value)


@closed
def validate_reader_outcome(value: dict, *, documents: tuple[dict, ...]) -> dict:
    shape(value, ('read_id', 'slot_id', 'artifact', 'reader', 'status', 'document_ids', 'diagnostics'))
    text(value['read_id']); text(value['slot_id']); _artifact(value['artifact'])
    reader = value['reader']['reader']
    validate_reader_spec(value['reader'], provider='metacats' if reader.startswith('metacats_') else 'msa')
    require(value['status'] in ('ok', 'partial', 'invalid'), 'reader_status_invalid')
    strings(value['document_ids']); reports({'requirements': [], 'diagnostics': value['diagnostics']})
    docs, _, _ = document_maps(documents)
    for identity in value['document_ids']:
        require(identity in docs, 'reader_document_unknown')
        document = docs[identity]
        require(document['kind'] == READER_KINDS[reader] and document['value']['artifact'] == value['artifact'], 'reader_document_conflict')
        for key, expected in value['reader'].items():
            if key not in ('reader', 'allow_multiple'):
                require(document['value'][key] == expected, 'reader_parameter_conflict')
        if reader == 'newick' and not value['reader']['allow_multiple']:
            require(len(document['value']['trees']) <= 1, 'reader_multiple_trees_conflict')
    require(len(value['document_ids']) <= 1, 'reader_document_count_invalid')
    require(value['status'] != 'ok' or bool(value['document_ids']), 'reader_ok_document_missing')
    return deepcopy(value)


SETTING_ENUMS = {
    'input_mode': ('ordinary_new_alignment', 'ordinary_prealigned', 'segment_alignment', 'segment_concatenation', 'mauve_first_block_projection', 'mauve_blocks', 'files', 'groups', 'auto'),
    'requested_molecule': ('dna', 'rna', 'protein', 'na', 'aa', 'unknown'),
    'observed_molecule': ('dna', 'rna', 'protein', 'na', 'aa', 'unknown'),
    'aligner': ('mafft', 'muscle', 'progressive_mauve', 'unknown'),
    'mafft_strategy': ('auto', 'fftns1', 'fftns2', 'fftnsi', 'einsi', 'linsi', 'ginsi', 'unknown'),
    'case_policy': ('preserve', 'uppercase', 'unknown'),
    'terminal_gap_policy': ('exclude_terminal_dash', 'unknown'),
    'original_hash_policy': ('exclude_hash', 'unknown'),
    'export_cutoff_comparison': ('strict_less_than', 'unknown'),
    'tree_rooting': ('original', 'midpoint', 'unknown'),
}


@closed
def validate_run_record(value: dict) -> dict:
    shape(value, ('original_task_id', 'settings', 'commands', 'versions', 'conflicts', 'completeness'))
    text(value['original_task_id']); require(value['completeness'] in COMPLETENESS, 'completeness_invalid')
    for name in ('settings', 'commands', 'versions', 'conflicts'):
        array(value[name])
    def provenance(row, requested=False):
        require(row['origin'] in (('requested', 'observed', 'retained_source') if requested else ('observed', 'retained_source')), 'origin_invalid')
        evidence(row['evidence'])
        if row['location'] is not None:
            _location(row['location'])
    for row in value['settings']:
        shape(row, ('name', 'value', 'origin', 'evidence', 'location')); provenance(row, True)
        name, operand = row['name'], row['value']; text(name)
        if name in SETTING_ENUMS:
            require(operand in SETTING_ENUMS[name], 'setting_value_invalid')
        elif name == 'prealigned_bypass':
            require(type(operand) is bool, 'setting_value_invalid')
        elif name in ('snp_reference_type', 'snp_reference_string', 'tree_model', 'native_engine_version'):
            text(operand, empty=True, nullable=name == 'snp_reference_string')
        elif name in ('threads', 'translation_table'):
            integer(operand, minimum=1, nullable=name == 'translation_table')
        elif name in ('epsilon', 'export_cutoff'):
            require(type(operand) in (int, float) and math.isfinite(operand) and operand >= 0 and (name != 'export_cutoff' or operand <= 1), 'setting_value_invalid')
        else:
            require(False, 'setting_name_invalid')
    unique(value['commands'], 'command_id')
    for row in value['commands']:
        shape(row, ('command_id', 'role', 'argv', 'raw_command', 'origin', 'evidence', 'location')); provenance(row)
        text(row['command_id']); text(row['raw_command'], empty=True, nullable=True)
        require(row['role'] in ('input_preparation', 'alignment', 'snp_analysis', 'association_test', 'tree_inference', 'reroot', 'unknown'), 'command_role_invalid')
        if row['argv'] is not None:
            array(row['argv'])
            for token in row['argv']:
                text(token, empty=True)
        require(row['argv'] is not None or row['raw_command'] is not None, 'command_missing')
    for row in value['versions']:
        shape(row, ('component', 'version', 'source_revision', 'origin', 'evidence', 'location')); provenance(row)
        require(row['component'] in ('app_msa', 'msa_sequence_alignment', 'snp_analysis', 'app_metacats', 'metadata_parser', 'metacats_r', 'mafft', 'muscle', 'progressive_mauve', 'fasttree', 'r', 'perl'), 'component_invalid')
        text(row['version'], empty=True, nullable=True); text(row['source_revision'], empty=True, nullable=True)
    for row in value['conflicts']:
        shape(row, ('name', 'setting_indices', 'code')); indices(row['setting_indices'])
        require(bool(row['setting_indices']) and all(i < len(value['settings']) and value['settings'][i]['name'] == row['name'] for i in row['setting_indices']), 'setting_conflict_reference_invalid')
        require(row['code'] in ('requested_observed_conflict', 'observed_values_conflict', 'source_deployment_unproven'), 'setting_conflict_code_invalid')
    return deepcopy(value)


def input_map(inputs):
    require(type(inputs) in (tuple, list), 'inputs_invalid')
    bindings = unique(list(inputs), 'binding_id')
    for binding in bindings.values():
        validate_contract('InputBinding', binding); pointer(binding['parameter_pointer'])
        for member in binding['members']:
            pointer(member['member_pointer'])
    return bindings


def row_ref(value, alignments):
    shape(value, ('alignment_id', 'row_index')); text(value['alignment_id']); integer(value['row_index'])
    require(value['alignment_id'] in alignments and value['row_index'] < len(alignments[value['alignment_id']]['rows']), 'row_reference_unknown')
    return value['alignment_id'], value['row_index']


def key_list(values, members=None):
    array(values); keys = [member_key(row) for row in values]
    require(len(keys) == len(set(keys)), 'duplicate_member_key')
    require(members is None or all(key in members for key in keys), 'member_reference_unknown')
    return keys


def interval(value):
    array(value); require(len(value) == 2, 'interval_invalid')
    integer(value[0]); integer(value[1]); require(value[0] < value[1], 'interval_invalid')


def _source_records(values):
    records = unique(values, 'source_record_id')
    for row in values:
        shape(row, ('source_record_id', 'kind', 'evidence')); text(row['source_record_id'])
        require(row['kind'] in ('original_input', 'feature', 'genome', 'sequence', 'function_assignment', 'taxonomy', 'metadata', 'native_run', 'parent_declaration'), 'source_kind_invalid')
        evidence([row['evidence']])
    return records


def _original_member(row, bindings, docs):
    shape(row, ('key', 'host_member_id', 'original_input_pointer', 'source_document_id', 'source_row_index', 'raw_header', 'member_label', 'sequence_sha256', 'original_length', 'molecule', 'feature_ids', 'genome_ids', 'source_record_ids', 'evidence'))
    key = member_key(row['key']); require(key[0] in bindings, 'input_binding_unknown')
    binding = bindings[key[0]]
    pointer(row['original_input_pointer']); text(row['host_member_id'], nullable=True)
    text(row['source_document_id'], nullable=True); integer(row['source_row_index'], nullable=True)
    text(row['raw_header'], empty=True, nullable=True); text(row['member_label'], empty=True, nullable=True)
    shared.digest(row['sequence_sha256'], nullable=True); integer(row['original_length'], nullable=True)
    require(row['molecule'] in MOLECULES, 'molecule_invalid'); evidence(row['evidence'])
    for name in ('feature_ids', 'genome_ids', 'source_record_ids'):
        strings(row[name])
    host = {m['member_id']: m for m in binding['members']}
    if row['host_member_id'] is not None:
        require(row['host_member_id'] in host, 'host_member_unknown')
        h = host[row['host_member_id']]
        require(row['original_input_pointer'] == h['member_pointer'], 'original_pointer_conflict')
        for original, field in (('original_length', 'length'), ('sequence_sha256', 'sequence_sha256')):
            require(h[field] is None or row[original] is None or h[field] == row[original], 'host_member_fact_conflict')
        require(h['molecule'] in (None, 'unknown') or row['molecule'] in ('unknown', h['molecule']), 'host_member_molecule_conflict')
    else:
        require(row['original_input_pointer'] == binding['parameter_pointer'], 'original_pointer_conflict')
    if row['source_document_id'] is not None:
        require(row['source_document_id'] in docs and docs[row['source_document_id']]['kind'] == 'alignment', 'original_document_unknown')
        document = docs[row['source_document_id']]['value']
        require(row['source_row_index'] is not None and row['source_row_index'] < len(document['rows']), 'original_row_unknown')
        source = document['rows'][row['source_row_index']]
        require(row['raw_header'] == source['raw_header'] and row['member_label'] == source['member_label'] == key[1], 'original_header_conflict')
        require(row['original_length'] == len(source['sequence']) and row['sequence_sha256'] == hashlib.sha256(source['sequence'].encode(document['encoding'])).hexdigest(), 'original_sequence_conflict')
        require(key[2] == sum(r['member_label'] == key[1] for r in document['rows'][:row['source_row_index']]), 'occurrence_index_conflict')
        if binding['content'] is not None:
            a, b = document['artifact'], binding['content']
            require((a['raw_artifact_ref'], a['source_ref'], a['sha256']) == (b['artifact_ref'], b['source_ref'], b['sha256']), 'original_artifact_conflict')
    elif row['source_row_index'] is None:
        require(row['host_member_id'] is not None and key[1] == row['host_member_id'] and key[2] == 0 and row['raw_header'] is None and row['member_label'] is None, 'metadata_member_invalid')
    else:
        require(binding['kind'] == 'inline_parameter' and type(binding['inline_value']) is str, 'inline_original_missing')
    return key


TRANSFORM_FIELDS = {
    'identity': (), 'rename': ('mappings',), 'uppercase': (), 'remove_symbols': ('symbols',),
    'align_insert_gaps': ('gap_symbol',), 'reverse_complement': ('alphabet',),
    'translate': ('translation_table', 'frame', 'strand', 'input_intervals'),
    'concatenate': ('segment_order', 'output_intervals'),
    'missing_segment_gap_fill': ('segment_id', 'output_interval_0based_half_open'),
    'native_terminal_dash_to_hash': ('alignment_id', 'row_indices'),
    'native_duplicate_merge': ('native_key', 'rule'),
    'native_first_contig': ('genome_id', 'genome_sequence_record_id'),
    'mauve_first_block_projection': ('xmfa_slot_id', 'block_index', 'native_input_order'),
}


def _transformations(values, members, alignments):
    transforms = unique(values, 'transformation_id')
    for row in values:
        kind = row['kind']; text(kind); require(kind in TRANSFORM_FIELDS, 'transformation_kind_invalid')
        shape(row, {'transformation_id', 'kind', 'input_members', 'input_rows', 'output_rows', 'evidence'} | set(TRANSFORM_FIELDS[kind]))
        text(row['transformation_id']); evidence(row['evidence']); key_list(row['input_members'], members)
        for name in ('input_rows', 'output_rows'):
            array(row[name]); refs = [row_ref(r, alignments) for r in row[name]]
            require(len(refs) == len(set(refs)), 'duplicate_row_reference')
        if kind == 'rename':
            unique(row['mappings'], lambda r: member_key(r['input_member']))
            for mapping in row['mappings']:
                shape(mapping, ('input_member', 'before', 'after')); require(mapping['input_member'] in row['input_members'], 'rename_member_conflict')
                text(mapping['before'], empty=True); text(mapping['after'], empty=True)
                member = members[member_key(mapping['input_member'])]
                require(mapping['before'] in (member['raw_header'], member['member_label']), 'rename_before_conflict')
                require(any(mapping['after'] in (alignments[r['alignment_id']]['rows'][r['row_index']]['raw_header'], alignments[r['alignment_id']]['rows'][r['row_index']]['member_label']) for r in row['output_rows']), 'rename_after_conflict')
        elif kind == 'remove_symbols':
            strings(row['symbols']); require(all(len(s) == 1 for s in row['symbols']), 'symbol_invalid')
        elif kind == 'align_insert_gaps':
            require(row['gap_symbol'] == '-', 'gap_symbol_invalid')
        elif kind == 'reverse_complement':
            require(row['alphabet'] in ('dna', 'rna'), 'alphabet_invalid')
        elif kind == 'translate':
            integer(row['translation_table'], minimum=1, nullable=True)
            require(type(row['frame']) is int and row['frame'] in (0, 1, 2) and row['strand'] in ('+', '-'), 'translation_invalid')
            array(row['input_intervals'])
            for operand in row['input_intervals']:
                interval(operand)
        elif kind == 'concatenate':
            strings(row['segment_order']); unique(row['output_intervals'], 'segment_id')
            for operand in row['output_intervals']:
                shape(operand, ('segment_id', 'interval_0based_half_open')); interval(operand['interval_0based_half_open'])
                require(operand['segment_id'] in row['segment_order'], 'segment_unknown')
            require([x['segment_id'] for x in row['output_intervals']] == row['segment_order'], 'segment_order_conflict')
            require(all(a['interval_0based_half_open'][1] <= b['interval_0based_half_open'][0] for a, b in zip(row['output_intervals'], row['output_intervals'][1:])), 'segment_interval_conflict')
        elif kind == 'missing_segment_gap_fill':
            text(row['segment_id']); interval(row['output_interval_0based_half_open'])
        elif kind == 'native_terminal_dash_to_hash':
            require(row['alignment_id'] in alignments, 'alignment_unknown'); indices(row['row_indices'])
            require(all(i < len(alignments[row['alignment_id']]['rows']) for i in row['row_indices']), 'row_reference_unknown')
        elif kind == 'native_duplicate_merge':
            text(row['native_key'], empty=True); require(row['rule'] in ('overwrite_last', 'concatenate_in_order'), 'merge_rule_invalid')
        elif kind == 'native_first_contig':
            text(row['genome_id']); text(row['genome_sequence_record_id'])
        elif kind == 'mauve_first_block_projection':
            text(row['xmfa_slot_id']); require(type(row['block_index']) is int and row['block_index'] == 0, 'block_index_invalid')
            key_list(row['native_input_order'], members)
    return transforms


def _row_members(values, members, alignments, transforms):
    unique(values, 'association_id'); result = unique(values, lambda r: (r['alignment_id'], r['row_index']))
    for row in values:
        shape(row, ('association_id', 'alignment_id', 'row_index', 'member_keys', 'transformation_ids', 'state', 'basis', 'evidence'))
        text(row['association_id']); ref = row_ref({k: row[k] for k in ('alignment_id', 'row_index')}, alignments)
        key_list(row['member_keys'], members); strings(row['transformation_ids']); evidence(row['evidence'])
        require(row['state'] in ('resolved', 'missing', 'conflicting', 'native_duplicate_merge'), 'row_state_invalid')
        require(row['basis'] in ('explicit_map', 'exact_unique_header', 'exact_unique_sequence', 'transformation_record', 'unresolved'), 'join_basis_invalid')
        require(row['state'] != 'missing' or not row['member_keys'], 'missing_member_conflict')
        require(row['state'] not in ('resolved', 'native_duplicate_merge') or bool(row['member_keys']), 'resolved_member_missing')
        for tid in row['transformation_ids']:
            require(tid in transforms, 'transformation_unknown'); tr = transforms[tid]
            require({'alignment_id': ref[0], 'row_index': ref[1]} in tr['output_rows'], 'transformation_row_conflict')
            require(all(m in row['member_keys'] for m in tr['input_members']), 'transformation_member_conflict')
        kinds = [transforms[t]['kind'] for t in row['transformation_ids']]
        require(row['state'] != 'resolved' or len(row['member_keys']) <= 1 or 'concatenate' in kinds, 'multiple_originals_without_concatenation')
        require(row['state'] != 'native_duplicate_merge' or 'native_duplicate_merge' in kinds, 'merge_evidence_missing')
    return result


def _correspondences(values, members, alignments, transforms, row_members):
    unique(values, lambda r: (r['alignment_id'], r['row_index'], r['column_0based']))
    for row in values:
        shape(row, ('alignment_id', 'row_index', 'column_0based', 'staged_ungapped_position_0based', 'original_member', 'original_interval_0based_half_open', 'strand', 'translation_table', 'transformation_id', 'evidence'))
        ref = row_ref({k: row[k] for k in ('alignment_id', 'row_index')}, alignments); integer(row['column_0based'])
        seq = alignments[ref[0]]['rows'][ref[1]]['sequence']; col = row['column_0based']
        require(col < len(seq), 'column_unknown'); evidence(row['evidence'])
        integer(row['staged_ungapped_position_0based'], nullable=True); integer(row['translation_table'], nullable=True, minimum=1)
        require(row['strand'] in ('+', '-', 'unknown'), 'strand_invalid'); text(row['transformation_id'], nullable=True)
        expected = None if seq[col] == '-' else sum(c != '-' for c in seq[:col])
        require(row['staged_ungapped_position_0based'] is None or row['staged_ungapped_position_0based'] == expected, 'staged_coordinate_conflict')
        candidates = []
        if row['original_member'] is not None:
            key = shared.member(row['original_member']); candidates = [m for k, m in members.items() if k[:2] == key]
            require(len(candidates) == 1, 'original_member_occurrence_ambiguous')
            require(ref in row_members and candidates[0]['key'] in row_members[ref]['member_keys'], 'original_row_join_missing')
        if row['transformation_id'] is not None:
            require(row['transformation_id'] in transforms and ref in row_members and row['transformation_id'] in row_members[ref]['transformation_ids'], 'correspondence_transformation_conflict')
            tr = transforms[row['transformation_id']]
            require(not candidates or candidates[0]['key'] in tr['input_members'], 'correspondence_member_conflict')
            require(tr['kind'] != 'translate' or row['translation_table'] == tr['translation_table'], 'translation_table_conflict')
        if row['original_interval_0based_half_open'] is not None:
            interval(row['original_interval_0based_half_open']); require(bool(candidates) and seq[col] != '-', 'original_interval_missing_member')
            length = candidates[0]['original_length']
            require(length is not None and row['original_interval_0based_half_open'][1] <= length, 'original_interval_outside_member')


def _subject(value, members, records, feature_genomes):
    shared.subject(value); require(value['source_record_id'] in records, 'subject_source_unknown')
    if value['kind'] == 'input_member':
        candidates = [m for key, m in members.items() if occurrence_id(*key) == value['id']]
        require(len(candidates) == 1 and value['source_record_id'] in candidates[0]['source_record_ids'], 'subject_member_unknown')
    elif value['kind'] == 'feature':
        require(records[value['source_record_id']]['kind'] in ('feature', 'parent_declaration', 'sequence', 'original_input'), 'feature_source_kind_invalid')
    elif value['kind'] == 'genome':
        require(records[value['source_record_id']]['kind'] in ('genome', 'parent_declaration', 'original_input'), 'genome_source_kind_invalid')


def _semantic_assignments(value, members, records):
    for row in value['feature_genomes']:
        shape(row, ('feature_id', 'genome_id', 'source_record_id', 'evidence'))
        for key in ('feature_id', 'genome_id', 'source_record_id'):
            text(row[key])
        evidence(row['evidence']); require(row['source_record_id'] in records, 'feature_source_unknown')
    unique(value['feature_genomes'], lambda r: (r['feature_id'], r['genome_id'], r['source_record_id']))
    unique(value['member_entities'], lambda r: (member_key(r['member_key']), shared.subject(r['subject'])))
    for row in value['member_entities']:
        shape(row, ('member_key', 'subject', 'evidence')); key = member_key(row['member_key'])
        require(key in members, 'entity_member_unknown'); shared.subject(row['subject'])
        subject = row['subject']; require(subject['kind'] in ('feature', 'genome'), 'entity_subject_kind_invalid')
        require(subject['source_record_id'] in records and records[subject['source_record_id']]['kind'] == subject['kind'], 'entity_source_kind_invalid')
        evidence(row['evidence']); require(bool(row['evidence']), 'entity_evidence_missing')
    for key, member in members.items():
        expected = entity_arrays(key, value['member_entities'], value['feature_genomes'])
        require(member['feature_ids'] == expected['feature_ids'] and member['genome_ids'] == expected['genome_ids'], 'member_entity_array_conflict')
        sources = [r['source_record_id'] for r in records.values() if r['evidence'] in member['evidence']]
        sources.extend(s for s in expected['source_record_ids'] if s not in sources)
        require(member['source_record_ids'] == sources, 'member_source_array_conflict')
    unique(value['functions'], 'assignment_id')
    for row in value['functions']:
        shape(row, ('assignment_id', 'subject', 'function_key', 'function_label', 'source_record_id', 'evidence'))
        for key in ('assignment_id', 'function_key', 'source_record_id'):
            text(row[key])
        text(row['function_label'], empty=True); evidence(row['evidence'])
        _subject(row['subject'], members, records, value['feature_genomes']); require(row['source_record_id'] in records, 'function_source_unknown')
    unique(value['function_equivalences'], 'equivalence_id'); canonical = {}
    for row in value['function_equivalences']:
        shape(row, ('equivalence_id', 'function_keys', 'canonical_function_key', 'evidence'))
        text(row['equivalence_id']); strings(row['function_keys']); text(row['canonical_function_key']); evidence(row['evidence'])
        require(bool(row['function_keys']), 'empty_equivalence')
        for key in row['function_keys'] + [row['canonical_function_key']]:
            require(key not in canonical or canonical[key] == row['canonical_function_key'], 'function_equivalence_conflict'); canonical[key] = row['canonical_function_key']
    unique(value['taxonomy'], lambda r: (shared.subject(r['subject']), r['source_record_id'], r['taxon_id']))
    for row in value['taxonomy']:
        shape(row, ('subject', 'taxon_id', 'rank', 'lineage', 'source_record_id', 'evidence'))
        _subject(row['subject'], members, records, value['feature_genomes']); text(row['taxon_id']); text(row['rank'], nullable=True)
        text(row['source_record_id']); require(row['source_record_id'] in records, 'taxonomy_source_unknown'); evidence(row['evidence']); array(row['lineage'])
        for ancestor in row['lineage']:
            shape(ancestor, ('taxon_id', 'rank')); text(ancestor['taxon_id']); text(ancestor['rank'], nullable=True)


def entity_arrays(key, links, feature_genomes):
    result = {'feature_ids': [], 'genome_ids': [], 'source_record_ids': []}
    def add(field, value):
        if value not in result[field]:
            result[field].append(value)
    for link in links:
        if member_key(link['member_key']) == key:
            subject = link['subject']; add('feature_ids' if subject['kind'] == 'feature' else 'genome_ids', subject['id'])
            add('source_record_ids', subject['source_record_id'])
            if subject['kind'] == 'feature':
                for relation in feature_genomes:
                    if relation['feature_id'] == subject['id']:
                        add('genome_ids', relation['genome_id']); add('source_record_ids', relation['source_record_id'])
    return result


@closed
def validate_association_set(value: dict, *, inputs: tuple[dict, ...], documents: tuple[dict, ...]) -> dict:
    shape(value, ASSOCIATION_KEYS)
    for rows in value.values():
        array(rows)
    bindings = input_map(inputs); docs, alignments, _ = document_maps(documents)
    records = _source_records(value['source_records']); members = {}
    for row in value['original_members']:
        key = _original_member(row, bindings, docs); require(key not in members, 'duplicate_original_member'); members[key] = row
        require(set(row['source_record_ids']) <= set(records), 'member_source_unknown')
    unique(value['inline_inputs'], 'input_binding_id')
    inline_rows = set()
    for row in value['inline_inputs']:
        shape(row, ('input_binding_id', 'parameter_pointer', 'id_rule', 'encoding', 'completeness', 'rows', 'members', 'requirements', 'diagnostics'))
        require(row['input_binding_id'] in bindings, 'inline_binding_unknown'); b = bindings[row['input_binding_id']]
        require(b['kind'] == 'inline_parameter' and type(b['inline_value']) is str and row['parameter_pointer'] == b['parameter_pointer'], 'inline_binding_conflict')
        require(row['id_rule'] == 'first_whitespace_token' and row['encoding'] in ('ascii', 'utf-8') and row['completeness'] in COMPLETENESS, 'inline_parameters_invalid')
        array(row['rows']); array(row['members']); reports(row)
        prior = 0
        for i, source in enumerate(row['rows']):
            shape(source, ('row_index', 'raw_header', 'member_label', 'sequence', 'character_start_0based', 'character_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive'))
            require(type(source['row_index']) is int and source['row_index'] == i, 'inline_row_order_invalid')
            for key in ('raw_header', 'member_label', 'sequence'):
                text(source[key], empty=True)
            a, z = source['character_start_0based'], source['character_end_0based_exclusive']; integer(a); integer(z)
            require(prior <= a < z <= len(b['inline_value']), 'inline_range_invalid'); prior = z
            chunk = b['inline_value'][a:z]; lines = chunk.splitlines()
            require(lines and lines[0] == '>' + source['raw_header'], 'inline_header_conflict')
            label = source['raw_header'].split(); require(source['member_label'] == (label[0] if label else ''), 'inline_label_conflict')
            require(source['sequence'] == ''.join(line.replace(' ', '').replace('\t', '') for line in lines[1:] if line.strip()), 'inline_sequence_conflict')
            starts = [m.end() for m in re.finditer(r'\r\n|\r|\n', b['inline_value'])]
            require(type(source['line_start_1based']) is int and source['line_start_1based'] == 1 + sum(p <= a for p in starts)
                and type(source['line_end_1based_inclusive']) is int and source['line_end_1based_inclusive'] == 1 + sum(p <= z - 1 for p in starts), 'inline_line_conflict')
        for member in row['members']:
            key = member_key(member['key']); require(key in members and members[key] == member, 'inline_member_conflict')
            i = member['source_row_index']; require(member['source_document_id'] is None and i is not None and i < len(row['rows']), 'inline_member_row_unknown')
            source = row['rows'][i]; inline_rows.add((key[0], i))
            require(member['member_label'] == source['member_label'] == key[1] and member['raw_header'] == source['raw_header'] and member['original_length'] == len(source['sequence']), 'inline_member_sequence_conflict')
            try:
                digest = hashlib.sha256(source['sequence'].encode(row['encoding'])).hexdigest()
            except UnicodeError:
                digest = None
            require(member['sequence_sha256'] == digest and key[2] == sum(r['member_label'] == key[1] for r in row['rows'][:i]), 'inline_member_digest_or_occurrence_conflict')
            require(member['host_member_id'] is None or sum(r['member_label'] == key[1] for r in row['rows']) == 1, 'duplicate_inline_host_identity')
        require({m['source_row_index'] for m in row['members']} == {r['row_index'] for r in row['rows'] if r['member_label']}, 'inline_occurrence_missing')
    require(all(m['source_document_id'] is not None or m['source_row_index'] is None or (k[0], m['source_row_index']) in inline_rows for k, m in members.items()), 'inline_member_document_missing')
    transforms = _transformations(value['transformations'], members, alignments)
    rows = _row_members(value['row_members'], members, alignments, transforms)
    _correspondences(value['correspondences'], members, alignments, transforms, rows)
    _semantic_assignments(value, members, records)
    unique(value['dependence_groups'], 'group_id')
    for row in value['dependence_groups']:
        shape(row, ('group_id', 'kind', 'member_keys', 'alignment_rows', 'document_ids', 'source_record_ids', 'evidence'))
        text(row['group_id']); require(row['kind'] in ('duplicate_original_label', 'identical_sequence', 'same_original_member', 'same_source_record', 'repeated_artifact', 'derived_representation', 'shared_group_membership'), 'dependence_kind_invalid')
        key_list(row['member_keys'], members); array(row['alignment_rows'])
        unique(row['alignment_rows'], lambda r: row_ref(r, alignments))
        strings(row['document_ids']); strings(row['source_record_ids']); evidence(row['evidence'])
        require(set(row['document_ids']) <= set(docs) and set(row['source_record_ids']) <= set(records), 'dependence_reference_unknown')
    reports(value)
    return deepcopy(value)


@closed
def validate_populations(value: dict, *, documents: tuple[dict, ...], associations: dict) -> dict:
    shape(value, ('alignments', 'composition', 'taxonomy', 'leaves')); _, alignments, trees = document_maps(documents)
    records = _source_records(associations['source_records']); members = {member_key(m['key']): m for m in associations['original_members']}
    seen = set()
    for kind, rows in value.items():
        for identity, row in unique(rows, 'population_id').items():
            text(identity); require(identity not in seen, 'population_identity_conflict'); seen.add(identity)
            if kind == 'alignments':
                require(row['alignment_id'] in alignments, 'population_alignment_unknown'); shared.alignment_population(row, alignments[row['alignment_id']])
                require(row['completeness'] != 'complete' or alignments[row['alignment_id']]['completeness'] == 'complete', 'population_completeness_overstated')
            elif kind == 'leaves':
                shape(row, ('population_id', 'tree_id', 'node_indices', 'completeness', 'evidence')); indices(row['node_indices']); evidence(row['evidence'])
                require(row['tree_id'] in trees and row['completeness'] == 'complete', 'leaf_population_invalid')
                nodes = trees[row['tree_id']]['nodes']; require(all(i < len(nodes) and not nodes[i]['child_indices'] for i in row['node_indices']), 'leaf_population_tip_unknown')
            else:
                (shared.composition_population if kind == 'composition' else shared.taxon_population)(row)
                for subject in row['member_subjects']:
                    _subject(subject, members, records, associations['feature_genomes'])
    return deepcopy(value)


@closed
def validate_alignment_association_declarations(value: dict, *, inputs: tuple[dict, ...], documents: tuple[dict, ...]) -> dict:
    shape(value, ('common', 'functions', 'taxonomy')); common = value['common']
    shape(common, ('version', 'analysis_id', 'input_sequences', 'row_joins', 'automatic_row_joins', 'transformations', 'correspondences', 'feature_genomes', 'source_records', 'member_entities'))
    require(common['version'] == 'bvbrc_alignment_associations_v1', 'declaration_version_invalid'); text(common['analysis_id'])
    bindings = input_map(inputs); docs, alignments, _ = document_maps(documents)
    unique(common['input_sequences'], 'input_binding_id')
    for row in common['input_sequences']:
        require(row['kind'] in ('parsed_document', 'inline_fasta'), 'input_selection_kind_invalid')
        fields = ('document', 'member_id_rule', 'host_member_joins') if row['kind'] == 'parsed_document' else ('id_rule', 'encoding')
        shape(row, {'kind', 'input_binding_id', 'molecule', 'evidence'} | set(fields)); evidence(row['evidence'])
        require(row['input_binding_id'] in bindings and row['molecule'] in MOLECULES, 'input_selection_invalid'); b = bindings[row['input_binding_id']]
        if row['kind'] == 'parsed_document':
            require(row['document'] in docs and docs[row['document']]['kind'] == 'alignment' and row['member_id_rule'] == 'first_whitespace_token', 'input_document_invalid')
            unique(row['host_member_joins'], 'source_row_index')
            for join in row['host_member_joins']:
                shape(join, ('source_row_index', 'host_member_id')); integer(join['source_row_index']); text(join['host_member_id'])
                require(join['source_row_index'] < len(docs[row['document']]['value']['rows']) and join['host_member_id'] in {m['member_id'] for m in b['members']}, 'host_member_join_invalid')
        else:
            require(b['kind'] == 'inline_parameter' and type(b['inline_value']) is str and row['id_rule'] == 'first_whitespace_token' and row['encoding'] in ('ascii', 'utf-8'), 'inline_input_invalid')
    unique(common['automatic_row_joins'], 'alignment')
    for row in common['automatic_row_joins']:
        shape(row, ('alignment', 'input_binding_ids', 'method', 'case_policy', 'gap_policy', 'transformation_ids', 'evidence'))
        require(row['alignment'] in alignments, 'automatic_alignment_unknown'); strings(row['input_binding_ids']); strings(row['transformation_ids']); evidence(row['evidence'])
        require(set(row['input_binding_ids']) <= set(bindings) and bool(row['input_binding_ids']), 'automatic_input_unknown')
        require(row['method'] in ('exact_unique_header', 'exact_unique_sequence') and row['case_policy'] in ('literal', 'uppercase') and row['gap_policy'] in ('literal', 'remove_alignment_dash'), 'automatic_policy_invalid')
    for key, version, fields in (('functions', 'bvbrc_alignment_functions_v1', ('assignments', 'equivalences')), ('taxonomy', 'bvbrc_alignment_taxonomy_v1', ('assignments',))):
        if value[key] is not None:
            shape(value[key], {'version', 'analysis_id'} | set(fields)); require(value[key]['version'] == version and value[key]['analysis_id'] == common['analysis_id'], 'semantic_declaration_scope_invalid')
            for field in fields:
                array(value[key][field])
    # Validate all references against actual original occurrences before a join
    # can be returned. This helper only consumes supplied strings/documents.
    from .bvbrc_alignment_associations import _input_records, _automatic_joins
    originals, inline, needs, diagnostics = _input_records(bindings, docs, common)
    probe = {key: [] for key in ASSOCIATION_KEYS}
    probe.update(original_members=originals, inline_inputs=inline, requirements=needs, diagnostics=diagnostics,
        row_members=common['row_joins'], transformations=common['transformations'], correspondences=common['correspondences'],
        feature_genomes=common['feature_genomes'], source_records=common['source_records'], member_entities=common['member_entities'],
        functions=value['functions']['assignments'] if value['functions'] else [],
        function_equivalences=value['functions']['equivalences'] if value['functions'] else [],
        taxonomy=value['taxonomy']['assignments'] if value['taxonomy'] else [])
    transforms = {t['transformation_id']: t for t in common['transformations']}
    _transformations(common['transformations'], {member_key(m['key']): m for m in originals}, alignments)
    for row in common['automatic_row_joins']:
        require(set(row['transformation_ids']) <= set(transforms), 'automatic_transformation_unknown')
        require(all(t['kind'] in ('identity', 'rename', 'uppercase', 'remove_symbols', 'align_insert_gaps') for t in (transforms[k] for k in row['transformation_ids'])), 'automatic_transform_unsupported')
    probe['row_members'] = deepcopy(common['row_joins'])
    explicit = {(r['alignment_id'], r['row_index']) for r in probe['row_members']}
    for plan in common['automatic_row_joins']:
        probe['row_members'].extend(r for r in _automatic_joins(plan, originals, docs, {x['input_binding_id']: x for x in inline}, transforms)
            if (r['alignment_id'], r['row_index']) not in explicit)
    validate_association_set(probe, inputs=inputs, documents=documents)
    return deepcopy(value)


__all__ = ['validate_parsed_document', 'validate_reader_spec', 'validate_reader_outcome',
    'validate_run_record', 'validate_association_set', 'validate_populations',
    'validate_alignment_association_declarations']
