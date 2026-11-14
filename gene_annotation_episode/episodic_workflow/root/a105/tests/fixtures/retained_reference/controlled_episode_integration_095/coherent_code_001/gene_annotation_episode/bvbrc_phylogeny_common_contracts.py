"""Closed, pure association checks for saved BV-BRC phylogeny common fields.

These checks validate supplied relationships. They do not authenticate Store
custody, original task provenance, or the provider-only locus/family tables.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re
from urllib.parse import quote
from typing import Literal

from . import phylogeny_calculation_contracts as c
from .phylogeny_format_contracts import validate_alignment_document, validate_tree_record
from .bvbrc_appservice_contracts import validate_contract

COMMON_KEYS = frozenset(('inputs', 'artifact_refs', 'observed_run', 'documents', 'joins', 'populations',
    'native_measurements', 'support_observations', 'dependence_groups', 'qualifications',
    'missing_requirements', 'assembly', 'read_outcomes'))
POPULATION_KEYS = ('alignments', 'leaves', 'composition', 'taxonomy', 'genomes', 'families', 'bootstraps', 'native')
COMMON_PARAMETER_KEYS = frozenset(('alignment_requests', 'original_coverage_population_ids', 'tree_requests',
    'bootstrap_requests', 'composition_population_ids', 'taxon_requests', 'comparisons'))
COMMON_COMPONENT_KEYS = frozenset(('alignments', 'trees', 'bootstrap', 'coordinate_maps', 'original_coverage',
    'composition', 'taxonomy', 'comparisons', 'missing_requirements', 'diagnostics'))
_SETTING_NAMES = ('recipe', 'alphabet', 'bootstrap_replicates', 'substitution_model', 'alignment_program', 'threads',
    'max_genes', 'max_genomes_missing', 'max_allowed_duplicates', 'family_namespace', 'analyze_codons',
    'analyze_proteins', 'end_trim_threshold', 'max_gaps_allowed', 'concatenate', 'protein_model_sample_proportion')
_TRANSFORMS = ('header_tokenization', 'duplicate_suffix', 'amino_acid_J_to_X', 'selected_segment', 'end_trim',
    'missing_locus_gap_fill', 'codon_gap_projection', 'concatenate')
_NATIVE_UNITS = {'log_likelihood': 'natural_log_likelihood', 'distinct_alignment_patterns': 'patterns',
    'gap_undetermined_percent_native': 'percent', 'family_native_length': 'columns',
    'family_native_sequences': 'sequences', 'family_native_gaps': 'characters',
    'family_native_sum_squared_freq': 'column_summed_squared_fraction',
    'family_native_mean_squared_freq': 'mean_squared_fraction', 'family_native_ranking_score': 'square_root_columns',
    'family_native_worst_sequence_ratio': 'ratio', 'sequence_native_mean_log2_frequency': 'bits_per_column',
    'genome_native_all_families': 'families', 'genome_native_single_copy_families': 'families',
    'genome_native_filtered_single_copy_families': 'families', 'analysis_native_reported_counts': 'reported_count'}


def _require(condition, code):
    if not condition:
        raise ValueError('bvbrc_phylogeny_' + code)


def _shape(value, keys, code='shape_invalid'):
    _require(type(value) is dict and set(value) == set(keys), code)


def _json(value, ancestors=None):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        _require(math.isfinite(value), 'nonfinite_number')
        return
    _require(type(value) in (dict, list), 'plain_json_required')
    ancestors = set() if ancestors is None else ancestors
    _require(id(value) not in ancestors, 'cyclic_json')
    ancestors.add(id(value))
    if type(value) is dict:
        _require(all(type(k) is str for k in value), 'json_key_invalid')
        children = value.values()
    else:
        children = value
    for item in children:
        _json(item, ancestors)
    ancestors.remove(id(value))


def _pointer(value):
    c.text(value, empty=True)
    _require((not value or value.startswith('/')) and re.search(r'~(?![01])', value) is None, 'pointer_invalid')


def _support_number(token):
    if type(token) is not str or re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', token.strip()) is None:
        return None
    number = float(token)
    if not math.isfinite(number) or number == 0 and re.search(r'[1-9]', token.strip().lower().split('e')[0]):
        return None
    return number


def _artifact(value):
    _shape(value, ('raw_artifact_ref', 'source_ref', 'sha256'), 'artifact_shape_invalid')
    c.text(value['raw_artifact_ref']); c.text(value['source_ref']); c.digest(value['sha256'])


def _unique(rows, key, *, equal=False):
    c.sequence(rows, stored=True)
    result = {}
    for row in rows:
        _require(type(row) is dict and key in row, 'record_identity_missing')
        c.text(row[key])
        if row[key] in result:
            _require(equal and result[row[key]] == row, 'record_identity_conflict')
        else:
            result[row[key]] = row
    return result


def _member_id(binding_id, member_id):
    c.text(binding_id); c.text(member_id)
    return 'member/' + quote(binding_id, safe='-._~') + '/' + quote(member_id, safe='-._~')


def _whole_id(analysis_id, kind, document_id):
    return 'analysis/' + quote(analysis_id, safe='-._~') + '/' + kind + '/' + quote(document_id, safe='-._~') + '/whole'


def _diag(value):
    validate_contract('Diagnostic', value)


def _requirement(value):
    validate_contract('AcquisitionRequirement', value)


def _command(value):
    _shape(value, ('command_id', 'role', 'argv', 'raw_text', 'origin', 'evidence', 'location'), 'command_shape_invalid')
    c.text(value['command_id']); c.text(value['raw_text'], nullable=True, empty=True)
    _require(value['role'] in ('alignment', 'model_selection', 'inference', 'bootstrap', 'support_mapping', 'rooting', 'rendering', 'unknown'), 'command_role_invalid')
    _require(value['origin'] in ('requested', 'observed', 'source_expected'), 'command_origin_invalid')
    if value['argv'] is not None:
        c.sequence(value['argv'], stored=True)
        for token in value['argv']:
            c.text(token, empty=True)
    c.evidence(value['evidence'])
    if value['location'] is not None:
        c.location(value['location'])


def _engine(value, commands):
    _shape(value, ('name', 'version', 'version_location', 'version_evidence', 'command_ids'), 'engine_shape_invalid')
    _require(value['name'] in ('raxml', 'phyml', 'fasttree', 'unknown'), 'engine_name_invalid')
    c.text(value['version'], nullable=True); c.evidence(value['version_evidence']); c.strings(value['command_ids'])
    _require(set(value['command_ids']) <= set(commands), 'engine_command_unknown')
    if value['version_location'] is not None:
        c.location(value['version_location'])


def _run(value):
    _shape(value, ('original_task_id', 'source_revision', 'settings', 'commands', 'engines', 'conflicts', 'completeness'), 'run_shape_invalid')
    c.text(value['original_task_id'], nullable=True); c.text(value['source_revision'], nullable=True)
    _require(value['completeness'] in c.COMPLETENESS, 'run_completeness_invalid')
    commands = _unique(value['commands'], 'command_id')
    for row in commands.values():
        _command(row)
    c.sequence(value['settings'], stored=True)
    for row in value['settings']:
        _shape(row, ('name', 'value', 'origin', 'evidence', 'location'), 'setting_shape_invalid')
        _require(row['name'] in _SETTING_NAMES and row['origin'] in ('requested', 'observed', 'source_expected'), 'setting_invalid')
        c.evidence(row['evidence'])
        if row['location'] is not None:
            c.location(row['location'])
        item = row['value']
        if item is None:
            continue
        name = row['name']
        if name in ('analyze_codons', 'analyze_proteins', 'concatenate'):
            _require(type(item) is bool, 'setting_type_invalid')
        elif name in ('bootstrap_replicates', 'threads', 'max_genes', 'max_genomes_missing', 'max_allowed_duplicates'):
            c.integer(item)
        elif name in ('end_trim_threshold', 'max_gaps_allowed', 'protein_model_sample_proportion'):
            c.number(item)
        else:
            c.text(item)
            enums = {'recipe': ('raxml', 'phyml', 'fasttree', 'unknown'), 'alphabet': ('dna', 'rna', 'protein', 'mixed', 'unknown'),
                     'family_namespace': ('PGFam', 'PLFam'), 'alignment_program': ('mafft', 'muscle', 'unknown')}
            if name in enums:
                _require(item in enums[name], 'setting_value_invalid')
    c.sequence(value['engines'], stored=True)
    for row in value['engines']:
        _engine(row, commands)
    c.sequence(value['conflicts'], stored=True)
    seen = set()
    for row in value['conflicts']:
        _shape(row, ('setting_name', 'requested_index', 'observed_index', 'diagnostic_code'), 'setting_conflict_shape_invalid')
        c.text(row['diagnostic_code'])
        for key in ('requested_index', 'observed_index'):
            c.integer(row[key]); _require(row[key] < len(value['settings']), 'setting_conflict_index_invalid')
        a, b = (value['settings'][row[k]] for k in ('requested_index', 'observed_index'))
        _require(a['origin'] == 'requested' and b['origin'] == 'observed' and a['name'] == b['name'] == row['setting_name'] and a['value'] != b['value'], 'setting_conflict_invalid')
        key = row['requested_index'], row['observed_index']
        _require(key not in seen, 'duplicate_setting_conflict'); seen.add(key)
    expected = {(i, j) for i, a in enumerate(value['settings']) for j, b in enumerate(value['settings'])
                if a['origin'] == 'requested' and b['origin'] == 'observed' and a['name'] == b['name'] and a['value'] != b['value']}
    _require(seen == expected, 'setting_conflicts_incomplete')
    return commands


def _table(value):
    _shape(value, ('table_id', 'artifact', 'dialect', 'header_tokens', 'rows', 'completeness'), 'native_table_shape_invalid')
    _artifact(value['artifact']); c.text(value['table_id']); c.text(value['dialect'])
    _require(value['table_id'].startswith(value['artifact']['raw_artifact_ref'] + '#'), 'native_table_identity_invalid')
    _require(value['completeness'] in c.COMPLETENESS, 'table_completeness_invalid')
    c.sequence(value['header_tokens'], stored=True)
    for token in value['header_tokens']:
        c.text(token, empty=True)
    c.sequence(value['rows'], stored=True)
    for i, row in enumerate(value['rows']):
        _shape(row, ('row_index', 'record_kind', 'raw_text', 'fields', 'family_id', 'location'), 'native_table_row_shape_invalid')
        _require(type(row['row_index']) is int and row['row_index'] == i, 'native_row_index_invalid')
        _require(row['record_kind'] in ('data', 'bad_sequences', 'disqualification', 'missing_codon_alignment', 'other_retained'), 'native_record_kind_invalid')
        c.text(row['raw_text'], empty=True); c.text(row['family_id'], nullable=True)
        c.sequence(row['fields'], stored=True)
        for token in row['fields']:
            c.text(token, empty=True)
        c.location(row['location']); _require(row['location']['artifact'] == value['artifact'], 'native_table_artifact_conflict')


def _partition(value):
    _shape(value, ('document_id', 'artifact', 'format', 'alignment_column_count', 'completeness', 'partitions', 'uncovered_columns_0based', 'overlapping_columns_0based'), 'partition_shape_invalid')
    _artifact(value['artifact']); c.integer(value['alignment_column_count'])
    _require(value['document_id'] == value['artifact']['raw_artifact_ref'] + '#partitions' and value['format'] == 'raxml_partitions', 'partition_identity_invalid')
    _require(value['completeness'] in c.COMPLETENESS, 'partition_completeness_invalid')
    c.sequence(value['partitions'], stored=True)
    counts = {}
    for i, row in enumerate(value['partitions']):
        _shape(row, ('partition_index', 'name', 'model_token', 'native_ranges', 'columns_0based', 'source_location'), 'partition_row_shape_invalid')
        _require(type(row['partition_index']) is int and row['partition_index'] == i, 'partition_index_invalid')
        c.text(row['name']); c.text(row['model_token']); c.location(row['source_location'])
        _require(row['source_location']['artifact'] == value['artifact'], 'partition_artifact_conflict')
        c.unique_indices(row['columns_0based']); c.sequence(row['native_ranges'], stored=True)
        columns = []
        for interval in row['native_ranges']:
            _shape(interval, ('start_1based', 'end_1based_inclusive', 'step'), 'partition_range_shape_invalid')
            for key in interval:
                c.integer(interval[key], minimum=1)
            _require(interval['end_1based_inclusive'] >= interval['start_1based'], 'partition_range_invalid')
            columns.extend(range(interval['start_1based'] - 1, interval['end_1based_inclusive'], interval['step']))
        _require(row['columns_0based'] == sorted(set(columns)), 'partition_columns_conflict')
        for col in columns:
            counts[col] = counts.get(col, 0) + 1
    for key in ('uncovered_columns_0based', 'overlapping_columns_0based'):
        c.unique_indices(value[key])
    _require(value['uncovered_columns_0based'] == [i for i in range(value['alignment_column_count']) if not counts.get(i)], 'partition_uncovered_conflict')
    _require(value['overlapping_columns_0based'] == sorted(i for i, n in counts.items() if n > 1), 'partition_overlap_conflict')


def _xml_property(value, artifact):
    _shape(value, ('ref', 'datatype', 'applies_to', 'value', 'source_location'), 'xml_property_shape_invalid')
    for key in ('ref', 'datatype', 'applies_to'):
        c.text(value[key], nullable=True, empty=True)
    c.text(value['value'], empty=True); c.location(value['source_location'])
    _require(value['source_location']['artifact'] == artifact, 'xml_artifact_conflict')


def _store(value):
    _shape(value, ('alignments', 'tree_documents', 'partitions', 'phyloxml', 'source_records', 'native_tables'), 'store_shape_invalid')
    alignments = _unique(value['alignments'], 'alignment_id')
    for row in alignments.values():
        validate_alignment_document(row)
    trees, documents = {}, {}
    for kind in ('tree_documents', 'phyloxml', 'partitions'):
        for did, doc in _unique(value[kind], 'document_id').items():
            _require(did not in documents, 'document_identity_conflict'); documents[did] = doc
            if kind == 'partitions':
                _partition(doc); continue
            keys = ('document_id', 'artifact', 'format', 'dialect', 'completeness', 'trees') if kind == 'tree_documents' else ('document_id', 'artifact', 'format', 'namespace', 'version', 'completeness', 'trees')
            _shape(doc, keys, 'tree_document_shape_invalid'); _artifact(doc['artifact'])
            _require(doc['completeness'] in c.COMPLETENESS, 'tree_document_completeness_invalid')
            suffix = '#tree_document' if kind == 'tree_documents' else '#phyloxml'
            _require(did == doc['artifact']['raw_artifact_ref'] + suffix, 'document_identity_invalid')
            _require(doc['format'] == ('newick' if kind == 'tree_documents' else 'phyloxml'), 'document_format_invalid')
            if kind == 'tree_documents':
                _require(doc['dialect'] in ('newick', 'raxml_branch_labels', 'bvbrc_double_quoted_names'), 'newick_dialect_invalid')
            else:
                c.text(doc['namespace'], nullable=True); c.text(doc['version'], nullable=True)
            c.sequence(doc['trees'], stored=True)
            indices = []
            for entry in doc['trees']:
                tree = entry if kind == 'tree_documents' else entry['tree']
                validate_tree_record(tree)
                _require(tree['document_id'] == did and tree['source_location']['artifact'] == doc['artifact'], 'tree_document_conflict')
                _require(tree['tree_id'] not in trees, 'tree_identity_conflict')
                trees[tree['tree_id']] = tree; indices.append(tree['tree_index'])
                if kind == 'phyloxml':
                    _shape(entry, ('tree', 'annotations', 'properties', 'native_attributes'), 'xml_tree_shape_invalid')
                    for key in ('annotations', 'properties', 'native_attributes'):
                        c.sequence(entry[key], stored=True)
                    for prop in entry['properties']:
                        _xml_property(prop, doc['artifact'])
                    for attr in entry['native_attributes']:
                        _shape(attr, ('name', 'value'), 'xml_attribute_shape_invalid'); c.text(attr['name']); c.text(attr['value'], empty=True)
                    seen = set()
                    for ann in entry['annotations']:
                        _shape(ann, ('node_index', 'names', 'ids', 'accessions', 'confidences', 'properties', 'source_location'), 'xml_annotation_shape_invalid')
                        c.integer(ann['node_index']); _require(ann['node_index'] < len(tree['nodes']) and ann['node_index'] not in seen, 'xml_annotation_node_invalid'); seen.add(ann['node_index'])
                        c.location(ann['source_location']); _require(ann['source_location']['artifact'] == doc['artifact'], 'xml_artifact_conflict')
                        for key in ('names', 'ids', 'accessions', 'confidences', 'properties'):
                            c.sequence(ann[key], stored=True)
                        for item in ann['names'] + ann['ids']:
                            c.text(item, empty=True)
                        for item in ann['accessions']:
                            _shape(item, ('source', 'value', 'source_location'), 'xml_accession_shape_invalid')
                            c.text(item['source'], nullable=True); c.text(item['value'], empty=True); c.location(item['source_location'])
                            _require(item['source_location']['artifact'] == doc['artifact'], 'xml_artifact_conflict')
                        for item in ann['confidences']:
                            _shape(item, ('type', 'value', 'raw_token', 'source_location'), 'xml_confidence_shape_invalid')
                            c.text(item['type'], nullable=True); c.number(item['value'], nullable=True); c.text(item['raw_token'], empty=True); c.location(item['source_location'])
                            _require(item['source_location']['artifact'] == doc['artifact'], 'xml_artifact_conflict')
                        for item in ann['properties']:
                            _xml_property(item, doc['artifact'])
            _require(indices == sorted(set(indices)), 'tree_document_indices_invalid')
    tables = _unique(value['native_tables'], 'table_id')
    for table in tables.values():
        _table(table)
    records = _unique(value['source_records'], 'source_record_id')
    for record in records.values():
        _shape(record, ('source_record_id', 'subject', 'artifact', 'evidence', 'pointer', 'source_database', 'source_version'), 'source_record_shape_invalid')
        c.subject(record['subject']); c.evidence(record['evidence']); _pointer(record['pointer'])
        c.text(record['source_database'], nullable=True); c.text(record['source_version'], nullable=True)
        if record['artifact'] is not None:
            _artifact(record['artifact'])
    return alignments, trees, documents, tables, records


def _analysis(documents, provider, alignments, trees, docs, tables):
    _shape(documents, ('store', 'analyses'), 'documents_shape_invalid')
    _require(type(documents['analyses']) is list and len(documents['analyses']) == 1, 'one_primary_analysis_required')
    row = documents['analyses'][0]
    common = {'analysis_id', 'mode', 'raw_tree_id', 'phyloxml_tree_id', 'native_engine_observation_ids', 'output_role_evidence'}
    if provider == 'gene_tree':
        _shape(row, common | {'locus_ids', 'aligned_document_id'}, 'gene_analysis_shape_invalid')
        _require(row['mode'] in ('gene_tree', 'concatenated_sequence_loci'), 'analysis_mode_invalid'); c.strings(row['locus_ids'])
        aid = row['aligned_document_id']
    else:
        _shape(row, common | {'final_alignment_id', 'partition_document_id', 'supported_tree_id', 'rooted_derivative_tree_id', 'display_tree_id', 'membership_document_id', 'family_stats_document_id', 'genome_counts_document_id', 'analysis_stats_document_id', 'bootstrap_tree_document_id', 'per_family_final_alignment_ids', 'explicit_family_matrix_id'}, 'codon_analysis_shape_invalid')
        _require(row['mode'] == 'core_genome_codon_protein', 'analysis_mode_invalid'); aid = row['final_alignment_id']
        for key in ('partition_document_id', 'bootstrap_tree_document_id'):
            c.text(row[key], nullable=True); _require(row[key] is None or row[key] in docs, 'analysis_document_unknown')
        if row['partition_document_id'] is not None:
            _require(docs[row['partition_document_id']]['format'] == 'raxml_partitions', 'analysis_partition_wrong_format')
        if row['bootstrap_tree_document_id'] is not None:
            _require(docs[row['bootstrap_tree_document_id']]['format'] == 'newick', 'analysis_bootstrap_wrong_format')
        for key in ('membership_document_id', 'family_stats_document_id', 'genome_counts_document_id', 'analysis_stats_document_id'):
            c.text(row[key], nullable=True); _require(row[key] is None or row[key] in tables, 'analysis_table_unknown')
        c.strings(row['per_family_final_alignment_ids']); _require(set(row['per_family_final_alignment_ids']) <= set(alignments), 'analysis_alignment_unknown')
        c.text(row['explicit_family_matrix_id'], nullable=True)
    c.text(row['analysis_id']); c.text(aid, nullable=True); _require(aid is None or aid in alignments, 'analysis_alignment_unknown')
    for key in ('raw_tree_id', 'phyloxml_tree_id') + (() if provider == 'gene_tree' else ('supported_tree_id', 'rooted_derivative_tree_id', 'display_tree_id')):
        c.text(row[key], nullable=True); _require(row[key] is None or row[key] in trees, 'analysis_tree_unknown')
        if row[key] is not None:
            expected = 'phyloxml' if key == 'phyloxml_tree_id' else 'newick'
            _require(trees[row[key]]['source_format'] == expected, 'analysis_tree_wrong_format')
    c.strings(row['native_engine_observation_ids']); c.evidence(row['output_role_evidence'])
    return row


def _subjects_and_inputs(inputs, records):
    bindings = _unique(inputs, 'binding_id')
    members, original_facts = {}, {}
    for binding in bindings.values():
        validate_contract('InputBinding', binding)
        for member in binding['members']:
            members[(binding['binding_id'], member['member_id'])] = member
            if member['evidence'] is not None:
                evidence = member['evidence']; content = evidence['content']
                locator = (content['source_ref'], content['artifact_ref'], content['sha256'], evidence['pointer'], member['member_pointer'])
                if locator in original_facts:
                    for field in ('length', 'molecule', 'sequence_sha256'):
                        prior = original_facts[locator][field]
                        _require(prior is None or member[field] is None or prior == member[field], 'shared_original_member_facts_conflict')
                        if prior is None and member[field] is not None:
                            original_facts[locator][field] = member[field]
                else:
                    original_facts[locator] = {field: member[field] for field in ('length', 'molecule', 'sequence_sha256')}
    anchors, actual = {}, {_member_id(*key): key for key in members}
    for record in records.values():
        subject = record['subject']; key = subject['kind'], subject['id']
        anchor = subject['source_record_id']
        _require(anchor in records and records[anchor]['subject'] == subject, 'subject_anchor_conflict')
        _require(key not in anchors or anchors[key] == subject, 'subject_anchor_conflict'); anchors[key] = subject
        if subject['kind'] == 'input_member':
            _require(subject['id'] in actual, 'input_member_subject_unknown')
    return bindings, members, anchors


def _subject(value, records, anchors):
    c.subject(value)
    _require((value['kind'], value['id']) in anchors and anchors[(value['kind'], value['id'])] == value, 'subject_anchor_conflict')
    _require(value['source_record_id'] in records and records[value['source_record_id']]['subject'] == value, 'subject_anchor_conflict')


def _row_ref(value, alignments):
    _shape(value, ('alignment_id', 'row_index'), 'row_ref_shape_invalid'); c.integer(value['row_index'])
    _require(value['alignment_id'] in alignments and value['row_index'] < len(alignments[value['alignment_id']]['rows']), 'row_reference_unknown')
    return value['alignment_id'], value['row_index']


def _tip(tree_id, node_index, trees):
    c.integer(node_index)
    _require(tree_id in trees and node_index < len(trees[tree_id]['nodes']) and not trees[tree_id]['nodes'][node_index]['child_indices'], 'terminal_reference_unknown')
    return tree_id, node_index


def _member(value, members):
    key = c.member(value); _require(key in members, 'member_reference_unknown'); return key


def _joins(value, provider, alignments, trees, members, records, anchors):
    keys = {'input_rows', 'tip_rows', 'feature_genomes', 'functions', 'function_equivalences', 'taxa', 'display_tips', 'transformations', 'residues', 'organismal_tips'}
    _shape(value, keys | ({'family_blocks'} if provider == 'codon_tree' else set()), 'joins_shape_invalid')
    for rows in value.values():
        c.sequence(rows, stored=True)
    transforms = _unique(value['transformations'], 'transformation_id')
    for row in transforms.values():
        _shape(row, ('transformation_id', 'kind', 'input_members', 'output_rows', 'before_header', 'after_label', 'segment_id', 'locus_order', 'removed_alignment_columns_0based', 'before_sequence_sha256', 'after_sequence_sha256', 'evidence'), 'transformation_shape_invalid')
        _require(row['kind'] in _TRANSFORMS, 'transformation_kind_invalid'); c.evidence(row['evidence'])
        for field in ('before_header', 'after_label', 'segment_id'):
            c.text(row[field], nullable=True, empty=True)
        c.strings(row['locus_order'])
        c.sequence(row['input_members'], stored=True); c.sequence(row['output_rows'], stored=True)
        original = [_member(m, members) for m in row['input_members']]
        outputs = [_row_ref(r, alignments) for r in row['output_rows']]
        _require(len(original) == len(set(original)) and len(outputs) == len(set(outputs)), 'transformation_duplicate_reference')
        for field in ('before_sequence_sha256', 'after_sequence_sha256'):
            c.digest(row[field], nullable=True)
        if row['removed_alignment_columns_0based'] is not None:
            c.unique_indices(row['removed_alignment_columns_0based'])
        if row['before_sequence_sha256'] is not None:
            _require(len(original) == 1, 'transformation_before_digest_ambiguous')
            digest = members[original[0]]['sequence_sha256']
            _require(digest is not None and row['before_sequence_sha256'] == digest, 'transformation_before_digest_conflict')
        if row['after_sequence_sha256'] is not None:
            _require(len(outputs) == 1, 'transformation_after_digest_ambiguous')
            for aid, index in outputs:
                _require(alignments[aid]['completeness'] == 'complete', 'transformation_after_digest_incomplete')
                seq = alignments[aid]['rows'][index]['sequence']
                _require(row['after_sequence_sha256'] == hashlib.sha256(seq.encode('utf-8')).hexdigest(), 'transformation_after_digest_conflict')
        if row['after_label'] is not None:
            _require(all(alignments[a]['rows'][i]['member_label'] == row['after_label'] for a, i in outputs), 'transformation_label_conflict')
    input_keys = set()
    for row in value['input_rows']:
        _shape(row, ('alignment_id', 'row_index', 'input_binding_id', 'member_id', 'locus_id', 'transformation_id', 'evidence'), 'input_row_shape_invalid')
        output = _row_ref({k: row[k] for k in ('alignment_id', 'row_index')}, alignments)
        member = _member({k: row[k] for k in ('input_binding_id', 'member_id')}, members)
        c.text(row['locus_id']); c.text(row['transformation_id'], nullable=True); c.evidence(row['evidence'])
        key = output + member + (row['locus_id'],)
        _require(key not in input_keys, 'duplicate_input_row_join'); input_keys.add(key)
        if row['transformation_id'] is not None:
            _require(row['transformation_id'] in transforms, 'transformation_reference_unknown')
            transform = transforms[row['transformation_id']]
            _require({'input_binding_id': member[0], 'member_id': member[1]} in transform['input_members'] and {'alignment_id': output[0], 'row_index': output[1]} in transform['output_rows'], 'input_row_transformation_conflict')
    tip_keys = {}
    for row in value['tip_rows']:
        _shape(row, ('tree_id', 'node_index', 'alignment_id', 'row_index', 'evidence'), 'tip_row_shape_invalid')
        tip = _tip(row['tree_id'], row['node_index'], trees); ref = _row_ref({k: row[k] for k in ('alignment_id', 'row_index')}, alignments); c.evidence(row['evidence'])
        _require(tip not in tip_keys or tip_keys[tip] == ref, 'tip_row_conflict'); tip_keys[tip] = ref
    features = {}
    for row in value['feature_genomes']:
        _shape(row, ('feature_id', 'genome_id', 'family_id', 'family_namespace', 'evidence'), 'feature_genome_shape_invalid')
        c.text(row['feature_id']); c.text(row['genome_id']); c.text(row['family_id'], nullable=True); c.evidence(row['evidence'])
        _require(row['family_namespace'] in (None, 'PGFam', 'PLFam'), 'family_namespace_invalid')
        _require((row['family_id'] is None) == (row['family_namespace'] is None), 'family_identity_incomplete')
        meaning = row['genome_id'], row['family_id'], row['family_namespace']
        _require(row['feature_id'] not in features or features[row['feature_id']] == meaning, 'feature_genome_conflict'); features[row['feature_id']] = meaning
    function_ids = set()
    for row in value['functions']:
        _shape(row, ('assignment_id', 'subject', 'function_key', 'function_label', 'source_record_id', 'evidence'), 'function_assignment_shape_invalid')
        _subject(row['subject'], records, anchors)
        for field in ('assignment_id', 'function_key', 'source_record_id'):
            c.text(row[field])
        c.text(row['function_label'], empty=True); c.evidence(row['evidence'])
        _require(row['assignment_id'] not in function_ids, 'duplicate_function_assignment'); function_ids.add(row['assignment_id'])
        _require(row['source_record_id'] in records and records[row['source_record_id']]['subject'] == row['subject'], 'function_source_subject_conflict')
    equivalences = _unique(value['function_equivalences'], 'equivalence_id'); canonical = {}
    for row in equivalences.values():
        _shape(row, ('equivalence_id', 'function_keys', 'canonical_function_key', 'evidence'), 'function_equivalence_shape_invalid')
        c.strings(row['function_keys']); c.text(row['canonical_function_key']); c.evidence(row['evidence']); _require(bool(row['function_keys']), 'empty_function_equivalence')
        for key in row['function_keys'] + [row['canonical_function_key']]:
            _require(key not in canonical or canonical[key] == row['canonical_function_key'], 'function_equivalence_conflict'); canonical[key] = row['canonical_function_key']
    taxonomy = {}
    for row in value['taxa']:
        _shape(row, ('subject', 'taxon_id', 'rank', 'lineage', 'source_record_id', 'evidence'), 'taxon_assignment_shape_invalid')
        _subject(row['subject'], records, anchors); c.text(row['taxon_id']); c.text(row['rank'], nullable=True); c.text(row['source_record_id']); c.evidence(row['evidence']); c.sequence(row['lineage'], stored=True)
        _require(row['source_record_id'] in records and records[row['source_record_id']]['subject'] == row['subject'], 'taxon_source_subject_conflict')
        for anc in [{'taxon_id': row['taxon_id'], 'rank': row['rank']}] + row['lineage']:
            _shape(anc, ('taxon_id', 'rank'), 'taxon_lineage_shape_invalid'); c.text(anc['taxon_id']); c.text(anc['rank'], nullable=True)
            if anc['rank'] is not None:
                key = (row['subject']['kind'], row['subject']['id'], anc['rank'])
                _require(key not in taxonomy or taxonomy[key] == anc['taxon_id'], 'taxon_assignment_conflict'); taxonomy[key] = anc['taxon_id']
    display_forward, display_reverse = {}, {}
    for row in value['display_tips']:
        _shape(row, ('raw_tree_id', 'raw_node_index', 'display_tree_id', 'display_node_index', 'source_id', 'display_name', 'evidence'), 'display_tip_shape_invalid')
        a = _tip(row['raw_tree_id'], row['raw_node_index'], trees); b = _tip(row['display_tree_id'], row['display_node_index'], trees)
        c.text(row['source_id']); c.text(row['display_name'], empty=True); c.evidence(row['evidence'])
        _require(trees[a[0]]['nodes'][a[1]]['decoded_label'] == row['source_id'] and trees[b[0]]['nodes'][b[1]]['decoded_label'] == row['display_name'], 'display_label_conflict')
        _require((a, b[0]) not in display_forward or display_forward[(a, b[0])] == b, 'display_join_not_injective')
        _require((b, a[0]) not in display_reverse or display_reverse[(b, a[0])] == a, 'display_join_not_injective')
        display_forward[(a, b[0])], display_reverse[(b, a[0])] = b, a
    offsets = {}
    for aid, alignment in alignments.items():
        for row in alignment['rows']:
            offset = 0
            for col, symbol in enumerate(row['sequence']):
                offsets[(aid, row['row_index'], col)] = None if symbol == '-' else offset
                offset += symbol != '-'
    mapped = {}
    for row in value['residues']:
        _shape(row, ('alignment_id', 'row_index', 'column_0based', 'staged_ungapped_position_0based', 'original_member', 'original_interval_0based_half_open', 'strand', 'translation_table', 'transformation_id', 'evidence'), 'residue_shape_invalid')
        ref = _row_ref({k: row[k] for k in ('alignment_id', 'row_index')}, alignments); c.integer(row['column_0based']); key = ref + (row['column_0based'],)
        _require(key in offsets, 'residue_column_unknown'); c.integer(row['staged_ungapped_position_0based'], nullable=True)
        _require(row['staged_ungapped_position_0based'] is None or row['staged_ungapped_position_0based'] == offsets[key], 'staged_coordinate_conflict')
        _require(row['strand'] in ('+', '-', 'unknown'), 'strand_invalid'); c.integer(row['translation_table'], nullable=True, minimum=1); c.text(row['transformation_id'], nullable=True); c.evidence(row['evidence'])
        _require(row['translation_table'] is None or row['translation_table'] in (1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33), 'translation_table_invalid')
        member = None if row['original_member'] is None else _member(row['original_member'], members)
        if member is not None:
            _require(any(k[:4] == ref + member for k in input_keys), 'residue_input_join_missing')
        if row['transformation_id'] is not None:
            _require(row['transformation_id'] in transforms, 'transformation_reference_unknown')
            tr = transforms[row['transformation_id']]
            _require({'alignment_id': ref[0], 'row_index': ref[1]} in tr['output_rows'] and (member is None or row['original_member'] in tr['input_members']), 'residue_transformation_conflict')
        interval = row['original_interval_0based_half_open']
        if interval is not None:
            c.sequence(interval, stored=True); _require(len(interval) == 2 and member is not None and offsets[key] is not None, 'original_interval_invalid')
            for pos in interval:
                c.integer(pos)
            width = interval[1] - interval[0]
            _require(width in (1, 3), 'original_coordinate_width_invalid')
            fact = members[member]
            _require(fact['length'] is None or interval[1] <= fact['length'], 'original_interval_outside_member')
            if width == 3:
                _require(fact['molecule'] in ('dna', 'rna', 'unknown', None), 'translation_molecule_conflict')
            if fact['molecule'] == 'protein':
                _require(width == 1 and row['translation_table'] is None, 'protein_coordinate_conflict')
        semantic = tuple((k, repr(v)) for k, v in row.items() if k != 'evidence')
        _require(key not in mapped or mapped[key] == semantic, 'residue_correspondence_conflict'); mapped[key] = semantic
    comparison_keys = {}
    for row in value['organismal_tips']:
        _shape(row, ('gene_tree_id', 'gene_node_index', 'organismal_tree_id', 'organismal_node_index', 'subject', 'evidence'), 'organismal_tip_shape_invalid')
        a = _tip(row['gene_tree_id'], row['gene_node_index'], trees); b = _tip(row['organismal_tree_id'], row['organismal_node_index'], trees); _subject(row['subject'], records, anchors); c.evidence(row['evidence'])
        scope = (a[0], b[0]); bucket = comparison_keys.setdefault(scope, [set(), set(), set()]); subj = (row['subject']['kind'], row['subject']['id'])
        _require(a[1] not in bucket[0] and b[1] not in bucket[1] and subj not in bucket[2], 'organismal_join_not_injective')
        bucket[0].add(a[1]); bucket[1].add(b[1]); bucket[2].add(subj)
    if provider == 'codon_tree':
        for row in value['family_blocks']:
            _shape(row, ('alignment_id', 'family_id', 'representation', 'columns_0based', 'member_row_indices', 'evidence'), 'family_block_shape_invalid')
            _require(row['alignment_id'] in alignments, 'family_block_alignment_unknown'); c.text(row['family_id']); _require(row['representation'] in ('protein', 'coding_nucleotide'), 'representation_invalid'); c.evidence(row['evidence'])
            c.alignment_population({'population_id': 'family-block', 'alignment_id': row['alignment_id'], 'row_indices': row['member_row_indices'], 'columns_0based': row['columns_0based'], 'completeness': 'unknown', 'evidence': row['evidence']}, alignments[row['alignment_id']])


def _populations(value, alignments, trees, records, anchors):
    _shape(value, POPULATION_KEYS, 'populations_shape_invalid'); all_ids = set()
    for kind in POPULATION_KEYS:
        rows = _unique(value[kind], 'population_id')
        _require(not (set(rows) & all_ids), 'population_identity_conflict'); all_ids.update(rows)
        for row in rows.values():
            if kind == 'alignments':
                _require(row.get('alignment_id') in alignments, 'population_alignment_unknown'); c.alignment_population(row, alignments[row['alignment_id']])
                _require(row['completeness'] != 'complete' or alignments[row['alignment_id']]['completeness'] == 'complete', 'population_completeness_overstated')
            elif kind == 'leaves':
                _shape(row, ('population_id', 'tree_id', 'node_indices', 'completeness', 'evidence'), 'leaf_population_shape_invalid'); c.unique_indices(row['node_indices']); c.evidence(row['evidence'])
                _require(row['completeness'] in c.COMPLETENESS and row['tree_id'] in trees, 'population_tree_unknown')
                for node in row['node_indices']:
                    _tip(row['tree_id'], node, trees)
            elif kind in ('composition', 'taxonomy'):
                (c.composition_population if kind == 'composition' else c.taxon_population)(row)
                for subject in row['member_subjects']:
                    _subject(subject, records, anchors)
            elif kind in ('genomes', 'families'):
                field = 'genome_ids' if kind == 'genomes' else 'family_ids'
                _shape(row, ('population_id', field, 'stage', 'completeness', 'evidence'), 'biological_population_shape_invalid'); c.strings(row[field]); c.evidence(row['evidence'])
                stages = ('requested_main', 'requested_optional', 'actually_forwarded_optional', 'returned_family_records', 'used_final_alignment', 'used_final_tree') if kind == 'genomes' else ('returned', 'eligible', 'evaluated_pretrim', 'selected')
                _require(row['stage'] in stages and row['completeness'] in c.COMPLETENESS, 'population_stage_invalid')
            elif kind == 'bootstraps':
                _shape(row, ('population_id', 'tree_ids', 'expected_replicates', 'completeness', 'expected_count_evidence'), 'bootstrap_population_shape_invalid'); c.strings(row['tree_ids']); c.integer(row['expected_replicates'], nullable=True); c.evidence(row['expected_count_evidence'])
                _require(set(row['tree_ids']) <= set(trees), 'bootstrap_tree_unknown'); _require(row['completeness'] in c.COMPLETENESS, 'population_completeness_invalid')
                _require(row['expected_replicates'] is None or row['expected_replicates'] >= len(row['tree_ids']), 'bootstrap_expected_count_conflict')
            else:
                _shape(row, ('population_id', 'kind', 'observed_member_count', 'observed_site_count', 'members', 'membership_completeness', 'evidence', 'locations'), 'native_population_shape_invalid')
                _require(row['kind'] in ('native_pretrim_alignment', 'native_log_alignment', 'native_reported_population', 'native_tree') and row['membership_completeness'] in c.COMPLETENESS, 'native_population_invalid')
                c.integer(row['observed_member_count'], nullable=True); c.integer(row['observed_site_count'], nullable=True); c.evidence(row['evidence']); c.sequence(row['members'], stored=True); c.sequence(row['locations'], stored=True)
                keys = []
                for subject in row['members']:
                    _subject(subject, records, anchors); keys.append((subject['kind'], subject['id']))
                _require(len(keys) == len(set(keys)), 'duplicate_native_population_member')
                for loc in row['locations']:
                    c.location(loc)
                if row['membership_completeness'] == 'complete' and row['observed_member_count'] is not None:
                    _require(row['observed_member_count'] == len(keys), 'native_population_count_conflict')
    return all_ids


def _assembly(value, provider, analysis, alignments, trees, records, anchors, members):
    _shape(value, ('version', 'analysis_id', 'caller_populations', 'locus_bindings', 'genome_request_sets', 'family_matrices', 'historical_frequencies', 'model_associations'), 'assembly_shape_invalid')
    _require(value['version'] == 'bvbrc_phylogeny_assembly_v1' and value['analysis_id'] == analysis['analysis_id'], 'assembly_analysis_conflict')
    _populations(value['caller_populations'], alignments, trees, records, anchors)
    _require(not value['caller_populations']['native'], 'caller_native_population_forbidden')
    for key in ('locus_bindings', 'genome_request_sets', 'family_matrices', 'historical_frequencies', 'model_associations'):
        c.sequence(value[key], stored=True)
    if provider == 'gene_tree':
        _require(not any(value[k] for k in ('genome_request_sets', 'family_matrices', 'historical_frequencies', 'model_associations')), 'gene_codon_assembly_conflict')
    else:
        _require(not value['locus_bindings'], 'codon_locus_assembly_conflict')
    for row in _unique(value['locus_bindings'], 'locus_id').values():
        _shape(row, ('locus_id', 'input_members', 'completeness', 'evidence'), 'locus_binding_shape_invalid'); c.evidence(row['evidence']); c.sequence(row['input_members'], stored=True); _require(row['completeness'] in c.COMPLETENESS, 'locus_completeness_invalid')
        keys = [_member(m, members) for m in row['input_members']]; _require(len(keys) == len(set(keys)), 'duplicate_locus_member')
    # Provider-specific stage/matrix/model relationships remain with CodonTree.
    for row in value['genome_request_sets']:
        _shape(row, ('set_id', 'kind', 'input_binding_ids', 'group_id', 'derived_from_set_ids', 'population'), 'genome_request_set_shape_invalid')
        c.text(row['set_id']); c.strings(row['input_binding_ids']); c.text(row['group_id'], nullable=True); c.strings(row['derived_from_set_ids'])
        _require(row['kind'] in ('main_ids', 'optional_ids', 'group_members', 'main_union', 'actually_forwarded_optional'), 'genome_request_kind_invalid')
        _require(row['population'] in value['caller_populations']['genomes'], 'genome_request_population_conflict')
    for row in value['family_matrices']:
        _shape(row, ('matrix_id', 'namespace', 'family_population_id', 'genome_population_id', 'rows', 'completeness', 'evidence'), 'family_matrix_shape_invalid')
        for key in ('matrix_id', 'family_population_id', 'genome_population_id'):
            c.text(row[key])
        _require(row['namespace'] in ('PGFam', 'PLFam') and row['completeness'] in c.COMPLETENESS, 'family_matrix_invalid'); c.evidence(row['evidence']); c.sequence(row['rows'], stored=True)
        for cell in row['rows']:
            _shape(cell, ('family_id', 'genome_id', 'feature_ids', 'evidence'), 'family_matrix_cell_shape_invalid'); c.text(cell['family_id']); c.text(cell['genome_id']); c.strings(cell['feature_ids']); c.evidence(cell['evidence'])
    for row in value['historical_frequencies']:
        _shape(row, ('evaluated_family_population', 'pretrim_sequence_rows'), 'historical_frequency_shape_invalid')
        _shape(row['evaluated_family_population'], ('population', 'expected_sequence_memberships', 'completeness'), 'historical_population_shape_invalid')
        ep = row['evaluated_family_population']; _require(ep['completeness'] in c.COMPLETENESS, 'historical_completeness_invalid'); c.sequence(ep['expected_sequence_memberships'], stored=True)
        for m in ep['expected_sequence_memberships']:
            _shape(m, ('family_id', 'feature_ids'), 'historical_membership_shape_invalid'); c.text(m['family_id']); c.strings(m['feature_ids'])
        c.sequence(row['pretrim_sequence_rows'], stored=True)
        for seq in row['pretrim_sequence_rows']:
            _shape(seq, ('family_id', 'feature_id', 'genome_id', 'value'), 'historical_row_shape_invalid')
            for key in ('family_id', 'feature_id', 'genome_id'):
                c.text(seq[key])
            _shape(seq['value'], ('value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_ref', 'method', 'evidence', 'requirement_ids'), 'quantity_shape_invalid')
            c.number(seq['value']['value'], nullable=True); c.evidence(seq['value']['evidence']); c.strings(seq['value']['requirement_ids'])
    for row in value['model_associations']:
        _shape(row, ('read_id', 'log_model_index', 'partition_document_id', 'partition_index', 'model_selection_command_id', 'sample_alignment_id', 'sample_column_map', 'evidence'), 'model_association_shape_invalid')
        c.text(row['read_id']); c.integer(row['log_model_index']); c.integer(row['partition_index'], nullable=True); c.evidence(row['evidence'])
        for key in ('partition_document_id', 'model_selection_command_id', 'sample_alignment_id'):
            c.text(row[key], nullable=True)
        if row['sample_column_map'] is not None:
            c.unique_indices(row['sample_column_map'])


def _reader_spec(value):
    _require(type(value) is dict and 'reader' in value, 'reader_spec_invalid')
    variants = {'newick': {'dialect', 'allow_multiple'}, 'aligned_fasta': {'id_rule', 'encoding'},
        'relaxed_phylip': {'layout', 'continuation_ids'}, 'raxml_partitions': {'alignment_column_count'},
        'phyloxml': set(), 'raxml_run_log': {'dialect'}, 'codon_membership': {'dialect'},
        'codon_family_statistics': {'dialect'}, 'codon_genome_counts': set(), 'codon_analysis_statistics': {'dialect'}}
    reader = value['reader']; _require(reader in variants, 'reader_name_invalid'); _shape(value, variants[reader] | {'reader'}, 'reader_spec_invalid')
    expected = {'newick': {'dialect': ('newick', 'raxml_branch_labels', 'bvbrc_double_quoted_names')},
        'aligned_fasta': {'id_rule': ('first_whitespace_token',), 'encoding': ('ascii', 'utf-8')},
        'relaxed_phylip': {'layout': ('sequential', 'interleaved'), 'continuation_ids': ('absent', 'repeated')},
        'raxml_run_log': {'dialect': ('raxml_8',)}, 'codon_membership': {'dialect': ('pgfams_legacy', 'homologs_current')},
        'codon_family_statistics': {'dialect': ('current_missing_header_tab',)},
        'codon_analysis_statistics': {'dialect': ('retained_current_source',)}}
    for key, allowed in expected.get(reader, {}).items():
        _require(value[key] in allowed, 'reader_spec_invalid')
    if reader == 'newick':
        _require(type(value['allow_multiple']) is bool, 'reader_spec_invalid')
    if reader == 'raxml_partitions':
        c.integer(value['alignment_column_count'])


def _read_outcomes(values, artifact_map, alignments, docs, tables, observations):
    outcomes = _unique(values, 'read_id')
    for row in outcomes.values():
        _shape(row, ('read_id', 'artifact', 'reader', 'status', 'value_present', 'document_ids', 'observation_ids', 'diagnostics'), 'read_outcome_shape_invalid')
        _artifact(row['artifact']); _reader_spec(row['reader'])
        _require(artifact_map.get(row['artifact']['raw_artifact_ref']) == row['artifact'], 'read_artifact_unknown')
        _require(row['status'] in ('ok', 'partial', 'invalid') and type(row['value_present']) is bool, 'read_outcome_invalid')
        _require(row['status'] != 'ok' or row['value_present'], 'ok_read_value_missing')
        c.strings(row['document_ids']); c.strings(row['observation_ids']); c.sequence(row['diagnostics'], stored=True)
        _require(row['value_present'] or not row['document_ids'] and not row['observation_ids'], 'absent_read_references')
        for diag in row['diagnostics']:
            _diag(diag)
        for did in row['document_ids']:
            obj = alignments.get(did, docs.get(did, tables.get(did)))
            _require(obj is not None and obj['artifact'] == row['artifact'], 'read_document_conflict')
            expected = {'newick': 'newick', 'aligned_fasta': 'aligned_fasta', 'relaxed_phylip': 'relaxed_phylip',
                        'raxml_partitions': 'raxml_partitions', 'phyloxml': 'phyloxml'}
            if row['reader']['reader'] in expected:
                _require(obj.get('format') == expected[row['reader']['reader']], 'read_document_format_conflict')
            else:
                _require(did in tables and row['reader']['reader'].startswith('codon_'), 'read_document_format_conflict')
        for oid in row['observation_ids']:
            _require(oid in observations, 'read_observation_unknown')
            obs = observations[oid]
            _require(obs['location'] is not None and obs['location']['artifact'] == row['artifact'], 'read_observation_artifact_conflict')
    return outcomes


def _validate_common(value, provider):
    _require(provider in ('gene_tree', 'codon_tree'), 'provider_invalid'); _shape(value, COMMON_KEYS, 'common_fields_shape_invalid'); _json(value)
    _shape(value['documents'], ('store', 'analyses'), 'documents_shape_invalid')
    alignments, trees, docs, tables, records = _store(value['documents']['store'])
    analysis = _analysis(value['documents'], provider, alignments, trees, docs, tables)
    bindings, members, anchors = _subjects_and_inputs(value['inputs'], records)
    artifact_map = _unique(value['artifact_refs'], 'raw_artifact_ref')
    for ref in artifact_map.values():
        _artifact(ref)
    for obj in list(alignments.values()) + list(docs.values()) + list(tables.values()) + [r for r in records.values() if r['artifact'] is not None]:
        _require(artifact_map.get(obj['artifact']['raw_artifact_ref']) == obj['artifact'], 'artifact_registry_conflict')
    commands = _run(value['observed_run'])
    _joins(value['joins'], provider, alignments, trees, members, records, anchors)
    population_ids = _populations(value['populations'], alignments, trees, records, anchors)
    _assembly(value['assembly'], provider, analysis, alignments, trees, records, anchors, members)
    for kind in POPULATION_KEYS:
        by_id = {p['population_id']: p for p in value['populations'][kind]}
        for pop in value['assembly']['caller_populations'][kind]:
            _require(by_id.get(pop['population_id']) == pop, 'caller_population_changed')
    whole_alignments = {p['population_id']: p for p in value['populations']['alignments']}
    whole_leaves = {p['population_id']: p for p in value['populations']['leaves']}
    for aid, alignment in alignments.items():
        pid = _whole_id(analysis['analysis_id'], 'alignment', aid)
        count = alignment['observed_column_count']
        if count is None:
            count = alignment['declared_column_count']
        if count is None:
            count = max((len(r['sequence']) for r in alignment['rows']), default=0)
        expected = {'population_id': pid, 'alignment_id': aid, 'row_indices': [r['row_index'] for r in alignment['rows']],
                    'columns_0based': list(range(count)), 'completeness': alignment['completeness'], 'evidence': []}
        _require(whole_alignments.get(pid) == expected, 'whole_alignment_population_conflict')
    for tid, tree in trees.items():
        pid = _whole_id(analysis['analysis_id'], 'tree', tid)
        expected = {'population_id': pid, 'tree_id': tid, 'node_indices': [n['node_index'] for n in tree['nodes'] if not n['child_indices']], 'completeness': 'complete', 'evidence': []}
        _require(whole_leaves.get(pid) == expected, 'whole_tree_population_conflict')
    for population in value['populations']['bootstraps']:
        if population['completeness'] == 'complete':
            _require(all(docs[trees[tid]['document_id']]['completeness'] == 'complete' for tid in population['tree_ids']), 'bootstrap_forest_completeness_conflict')
    observations = _unique(value['native_measurements'], 'observation_id')
    requirements = _unique(value['missing_requirements'], 'requirement_id')
    for req in requirements.values():
        _requirement(req)
    for obs in observations.values():
        c.native_observation(obs); _require(obs['population_id'] in population_ids, 'observation_population_unknown')
        if obs['field'] in _NATIVE_UNITS:
            _require(obs['unit'] == _NATIVE_UNITS[obs['field']], 'native_field_unit_conflict')
            if obs['value'] is not None and obs['raw_token'] is not None:
                try:
                    number = float(obs['raw_token'])
                except (ValueError, OverflowError):
                    _require(False, 'native_token_value_conflict')
                _require(math.isfinite(number) and number == obs['value'], 'native_token_value_conflict')
        if obs['value'] is not None and obs['unit'] in ('patterns', 'columns', 'sequences', 'characters', 'families', 'reported_count'):
            _require(type(obs['value']) is int and obs['value'] >= 0, 'native_count_invalid')
        _require(set(obs['requirement_ids']) <= set(requirements), 'observation_requirement_unknown')
        if obs['location'] is not None:
            _require(artifact_map.get(obs['location']['artifact']['raw_artifact_ref']) == obs['location']['artifact'], 'observation_artifact_unknown')
        if obs['field'] in ('branch_length', 'branch_support_native'):
            matches = [(tid, node['node_index']) for tid, tree in trees.items() for node in tree['nodes'] if obs['subject_id'] == tid + '/node/' + str(node['node_index'])]
            _require(len(matches) == 1, 'observation_edge_unknown')
            tid, ni = matches[0]
            _require(obs['location'] is not None and obs['location']['artifact'] == trees[tid]['source_location']['artifact'], 'observation_edge_artifact_conflict')
            _require(obs['population_id'] == _whole_id(analysis['analysis_id'], 'tree', tid), 'observation_tree_population_conflict')
            if obs['field'] == 'branch_length':
                node = trees[tid]['nodes'][ni]
                _require(obs['value'] == node['branch_length'] and obs['raw_token'] == node['branch_length_token'], 'branch_observation_conflict')
    _require(set(analysis['native_engine_observation_ids']) <= set(observations), 'analysis_engine_observation_unknown')
    seen = set()
    for row in value['support_observations']:
        _shape(row, ('tree_id', 'node_index', 'native_observation_id', 'source_kind', 'method', 'scale', 'command_id', 'bootstrap_population_id', 'evidence'), 'support_observation_shape_invalid')
        c.integer(row['node_index']); _require(row['tree_id'] in trees and row['node_index'] < len(trees[row['tree_id']]['nodes']), 'support_node_invalid')
        _require(row['source_kind'] in ('internal_label', 'branch_comment', 'phyloxml_confidence') and row['method'] in c.SUPPORT_METHODS and row['scale'] in c.SUPPORT_SCALES, 'support_semantics_invalid')
        c.text(row['command_id'], nullable=True); c.text(row['bootstrap_population_id'], nullable=True); c.evidence(row['evidence'])
        _require(row['command_id'] is None or row['command_id'] in commands, 'support_command_unknown')
        _require(row['bootstrap_population_id'] is None or row['bootstrap_population_id'] in {p['population_id'] for p in value['populations']['bootstraps']}, 'support_bootstrap_population_unknown')
        oid = row['native_observation_id']; _require(oid in observations and oid not in seen, 'support_observation_identity_invalid'); seen.add(oid)
        obs = observations[oid]
        _require(obs['field'] == 'branch_support_native' and obs['subject_id'] == row['tree_id'] + '/node/' + str(row['node_index']), 'support_edge_conflict')
        unit = {'percent': 'percent', 'fraction': 'fraction', 'statistic': 'native_statistic', 'native_unknown': 'native_unknown'}[row['scale']]
        _require(obs['unit'] == unit and obs['method'] in ('native_unknown', row['method']), 'support_unit_method_conflict')
        tree = trees[row['tree_id']]; node = tree['nodes'][row['node_index']]
        if row['source_kind'] == 'internal_label':
            _require(tree['source_format'] == 'newick' and bool(node['child_indices']) and obs['raw_token'] == node['label_token'] and obs['location'] == node['source_location'], 'support_label_source_conflict')
            _require(obs['value'] == _support_number(node['decoded_label']), 'support_token_value_conflict')
        elif row['source_kind'] == 'branch_comment':
            document = docs[tree['document_id']]
            _require(document.get('dialect') == 'raxml_branch_labels' and any(comment['position'] == 'after_length' and comment['text'] == obs['raw_token'] and comment['location'] == obs['location'] for comment in node['comments']), 'support_comment_source_conflict')
            _require(obs['value'] == _support_number(obs['raw_token']), 'support_token_value_conflict')
        else:
            document = docs[tree['document_id']]
            matches = [confidence for entry in document.get('trees', []) if 'tree' in entry and entry['tree']['tree_id'] == tree['tree_id'] for annotation in entry['annotations'] if annotation['node_index'] == row['node_index'] for confidence in annotation['confidences']]
            _require(any(confidence['raw_token'] == obs['raw_token'] and confidence['value'] == obs['value'] and confidence['source_location'] == obs['location'] for confidence in matches), 'support_xml_source_conflict')
    c.sequence(value['qualifications'], stored=True)
    for diag in value['qualifications']:
        _diag(diag)
    outcomes = _read_outcomes(value['read_outcomes'], artifact_map, alignments, docs, tables, observations)
    materialized = {did for row in outcomes.values() for did in row['document_ids']}
    _require(materialized == set(alignments) | set(docs) | set(tables), 'saved_reader_outcome_missing')
    recorded_observations = {oid for row in outcomes.values() for oid in row['observation_ids']}
    _require(all(o['field'] in ('branch_length', 'branch_support_native') or oid in recorded_observations for oid, o in observations.items()), 'native_reader_observation_missing')
    linked_reads = [row for row in outcomes.values() if row['reader']['reader'] == 'raxml_run_log' and row['status'] != 'invalid'
                    and set(row['observation_ids']) & set(analysis['native_engine_observation_ids'])]
    associated_trees = {analysis[key] for key in analysis if key.endswith('tree_id') and analysis[key] is not None}
    verified_commands = {}
    for engine in value['observed_run']['engines']:
        if engine['name'] != 'raxml' or engine['version'] is None or engine['version_location'] is None:
            continue
        if not any(engine['version_location']['artifact'] == row['artifact'] for row in linked_reads):
            continue
        for cid in engine['command_ids']:
            command = commands[cid]
            if command['origin'] == 'observed' and command['location'] is not None and command['argv'] is not None and any(command['location']['artifact'] == row['artifact'] for row in linked_reads):
                verified_commands[cid] = command
    for observation in observations.values():
        if observation['field'] == 'branch_length' and observation['unit'] != 'native_unknown':
            _require(bool(analysis['output_role_evidence']) and any(observation['subject_id'].startswith(tid + '/node/') for tid in associated_trees) and any(cmd['role'] == 'inference' for cmd in verified_commands.values()), 'branch_unit_provenance_unverified')
    for support in value['support_observations']:
        if support['method'] == 'native_unknown':
            continue
        _require(bool(analysis['output_role_evidence']) and support['tree_id'] in associated_trees and support['command_id'] in verified_commands, 'support_method_provenance_unverified')
        command = verified_commands[support['command_id']]; argv = command['argv']
        mode = 'a' if support['method'] == 'rapid_bootstrap' else 'D' if support['method'] == 'rell_bootstrap' else None
        _require(mode is not None and command['role'] == 'inference' and any(token == '-f' and argv[i + 1] == mode for i, token in enumerate(argv[:-1])), 'support_method_command_conflict')
    for i, outcome in enumerate(value['read_outcomes']):
        for j, diag in enumerate(outcome['diagnostics']):
            outward = deepcopy(diag); outward['path'] = f'/read_outcomes/{i}/diagnostics/{j}'
            outward['evidence_refs'] = list(dict.fromkeys(diag['evidence_refs'] + [outcome['artifact']['source_ref']]))
            _require(outward in value['qualifications'], 'reader_diagnostic_not_retained')
    for row in _unique(value['dependence_groups'], 'group_id').values():
        _shape(row, ('group_id', 'kind', 'subject_ids', 'evidence'), 'dependence_group_shape_invalid'); c.strings(row['subject_ids']); c.evidence(row['evidence'])
        _require(row['kind'] in ('identical_final_sequence', 'shared_original_member', 'protein_and_coding_nucleotide', 'derived_tree', 'same_source_record'), 'dependence_kind_invalid')
        _require(len(row['subject_ids']) >= 2, 'dependence_members_missing')
        row_refs = {aid + '/row/' + str(r['row_index']): (aid, r) for aid, alignment in alignments.items() for r in alignment['rows']}
        if row['kind'] == 'identical_final_sequence':
            _require(all(s in row_refs for s in row['subject_ids']), 'dependence_row_unknown')
            _require(all(alignments[row_refs[s][0]]['completeness'] == 'complete' for s in row['subject_ids']) and len({row_refs[s][1]['sequence'] for s in row['subject_ids']}) == 1, 'identical_sequence_dependence_conflict')
        elif row['kind'] == 'shared_original_member':
            origins = []
            for sid in row['subject_ids']:
                _require(sid in row_refs, 'dependence_row_unknown')
                aid, alignment_row = row_refs[sid]; identities = set()
                for join in value['joins']['input_rows']:
                    if join['alignment_id'] == aid and join['row_index'] == alignment_row['row_index']:
                        member = (join['input_binding_id'], join['member_id']); fact = members[member]
                        identities.add(('member',) + member)
                        if fact['evidence'] is not None:
                            ev = fact['evidence']; content = ev['content']
                            identities.add(('source', content['source_ref'], content['artifact_ref'], content['sha256'], ev['pointer'], fact['member_pointer']))
                origins.append(identities)
            _require(bool(set.intersection(*origins)), 'shared_original_dependence_conflict')
        elif row['kind'] == 'derived_tree':
            _require(set(row['subject_ids']) <= set(trees), 'dependence_tree_unknown')
            linked = {tid for join in value['joins']['display_tips'] for tid in (join['raw_tree_id'], join['display_tree_id']) if join['raw_tree_id'] in row['subject_ids'] and join['display_tree_id'] in row['subject_ids']}
            _require(linked == set(row['subject_ids']), 'derived_tree_dependence_unproven')
        elif row['kind'] == 'same_source_record':
            _require(set(row['subject_ids']) <= set(records), 'dependence_source_unknown')
            sources = []
            for sid in row['subject_ids']:
                record = records[sid]; _require(record['artifact'] is not None, 'dependence_source_unproven')
                sources.append((record['artifact'], record['pointer']))
            _require(all(source == sources[0] for source in sources), 'dependence_source_conflict')
        else:
            native_rows = {tid + '/row/' + str(r['row_index']) for tid, table in tables.items() for r in table['rows']}
            _require(set(row['subject_ids']) <= native_rows, 'dependence_native_row_unknown')
    return {'alignments': alignments, 'trees': trees, 'documents': docs, 'tables': tables, 'records': records,
            'members': members, 'anchors': anchors, 'analysis': analysis, 'observations': observations, 'commands': commands}


def validate_shared_fields(sheet: dict, *, provider: Literal['gene_tree', 'codon_tree']) -> dict:
    """Validate only the common portion of one exact saved provider sheet.

    Provider-only arrays must exist, but their scientific semantics are checked
    by the GeneTree or CodonTree validator that calls this function.
    """
    _require(provider in ('gene_tree', 'codon_tree'), 'provider_invalid')
    specific = {'loci'} if provider == 'gene_tree' else {'genomes', 'families', 'models'}
    _shape(sheet, COMMON_KEYS | specific | {'schema_version', 'tool', 'mode'}, 'sheet_shape_invalid')
    expected = ('bvbrc_gene_tree_sheet_v1', 'C-L194-GeneTree') if provider == 'gene_tree' else ('bvbrc_codon_tree_sheet_v1', 'C-L193-CodonTree')
    _require((sheet['schema_version'], sheet['tool']) == expected, 'sheet_header_invalid')
    for key in specific:
        c.sequence(sheet[key], stored=True)
    common = {key: sheet[key] for key in COMMON_KEYS}
    index = _validate_common(common, provider)
    _require(sheet['mode'] == index['analysis']['mode'], 'sheet_mode_conflict')
    return deepcopy(common)


__all__ = ['validate_shared_fields']
