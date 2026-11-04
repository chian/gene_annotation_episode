"""Closed MSA provider records and detached, source-bound saved validation.

No validator acquires data, parses native bytes or invokes a calculator. Native
observations retain the original tokens; shared quantities and MSA/XMFA cells
keep their different contracts. External custody belongs to the host adapter.
"""
from __future__ import annotations
from copy import deepcopy
from functools import wraps
import math
import re
from urllib.parse import quote

from . import bvbrc_alignment_provider_contracts as common
from . import phylogeny_calculation_contracts as shared
from . import bvbrc_msa_calculation_contracts as native
from . import xmfa_calculation_contracts as xmfa
from .bvbrc_alignment_values import diagnostic, requirement, validate_native_number, validate_numeric_cell
from .bvbrc_msa_format_contracts import PROTEIN_SYMBOLS
from .phylogeny_format_contracts import _native_number
from .bvbrc_msa_xmfa_inputs import validate_msa_xmfa_binding_record

PREFIX = 'bvbrc_msa_provider_'
VERSION = 'bvbrc_msa_components_v1'
MODES = ('ordinary_new_alignment', 'ordinary_prealigned', 'segment_alignment',
    'segment_concatenation', 'mauve_first_block_projection', 'mauve_blocks')
COMMON_KINDS = {'alignment', 'ungapped_map', 'original_coverage', 'function_composition', 'taxonomy'}
REQUEST_FIELDS = {
    'alignment': {'population_id', 'alphabet', 'case_policy', 'pairs'},
    'ungapped_map': {'alignment_id', 'row_indices'},
    'original_coverage': {'population_id'}, 'function_composition': {'population_id'},
    'taxonomy': {'population_id', 'rank'},
    'tree': {'population_id', 'branch_unit', 'pairs'},
    'relationship_comparison': {'comparison_id', 'gene_tree_id', 'organismal_tree_id', 'injective_tip_join'},
    'msa_entropy': {'population_id', 'alphabet', 'case_policy', 'terminal_gap', 'observed_table_id', 'native_rounding'},
    'msa_reference_differences': {'population_id', 'reference', 'member_row_indices', 'alphabet', 'case_policy'},
    'xmfa_column_coordinates': {'document_id', 'cells', 'use_source_bindings'},
    'xmfa_source_positions': {'document_id', 'queries', 'use_source_bindings'},
    'xmfa_alignment_components': {'document_id', 'selection', 'selected_pairs', 'case_policy'},
    'xmfa_interval_coverage': {'document_id', 'selection', 'use_source_bindings', 'basis'},
}
SHEET_KEYS = {'schema_version', 'tool', 'analysis', 'inputs', 'run', 'documents',
    'read_outcomes', 'associations', 'populations', 'segments', 'consensus_associations',
    'tree_bindings', 'native_observations', 'native_tree_measurements',
    'support_observations', 'xmfa_bindings', 'requirements', 'diagnostics'}


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
            raise ValueError(PREFIX + 'dependency_contract_invalid') from exc
        except (KeyError, TypeError, IndexError, OverflowError, UnicodeError, RecursionError) as exc:
            raise ValueError(PREFIX + 'shape_invalid') from exc
    return checked


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'shape_invalid')


def number(value, *, nullable=False):
    require(nullable and value is None or type(value) in (int, float) and math.isfinite(value), 'number_invalid')


def merge_reports(*collections):
    result, known = [], {}
    for rows in collections:
        for row in rows:
            if 'requirement_id' in row:
                identity = row['requirement_id']
                require(identity not in known or known[identity] == row, 'requirement_identity_conflict')
                known[identity] = row
            if row not in result:
                result.append(deepcopy(row))
    return result


def need(analysis_id, request_id, reason, *, kind='scientific_metadata', source_refs=()):
    return requirement('msa/' + '/'.join(quote(v, safe='') for v in (analysis_id, request_id, reason)),
        kind=kind, role=request_id, source_refs=source_refs, reason_code=reason)


def _pairs(value, minimum=0, distinct=False, unordered=False):
    common.array(value); seen = set()
    for pair in value:
        common.array(pair); require(len(pair) == 2, 'pair_invalid')
        for item in pair:
            common.integer(item, minimum=minimum)
        key = tuple(sorted(pair) if unordered else pair)
        require(key not in seen and (not distinct or pair[0] != pair[1]), 'pair_duplicate_or_self')
        seen.add(key)


def _tip_join(value):
    common.array(value); a, b, subjects = set(), set(), set()
    for row in value:
        shape(row, {'gene_tree_id', 'gene_node_index', 'organismal_tree_id', 'organismal_node_index', 'subject', 'evidence'})
        for key in ('gene_tree_id', 'organismal_tree_id'):
            common.text(row[key])
        for key in ('gene_node_index', 'organismal_node_index'):
            common.integer(row[key])
        subject = shared.subject(row['subject']); common.evidence(row['evidence'])
        require(row['gene_node_index'] not in a and row['organismal_node_index'] not in b and subject not in subjects, 'tip_join_not_injective')
        a.add(row['gene_node_index']); b.add(row['organismal_node_index']); subjects.add(subject)


@closed
def validate_msa_parameters(parameters: dict) -> dict:
    shape(parameters, {'version', 'requests'}); require(parameters['version'] == VERSION, 'parameters_version_invalid')
    requests = common.unique(parameters['requests'], 'request_id')
    for row in requests.values():
        common.text(row['request_id']); kind = row['kind']
        require(type(kind) is str and kind in REQUEST_FIELDS, 'request_kind_invalid')
        shape(row, REQUEST_FIELDS[kind] | {'kind', 'request_id'})
        for key in ('population_id', 'alignment_id', 'document_id', 'rank', 'comparison_id', 'gene_tree_id', 'organismal_tree_id'):
            if key in row:
                common.text(row[key])
        if kind == 'alignment':
            require(row['alphabet'] in ('dna', 'rna', 'protein', 'unknown') and row['case_policy'] in ('uppercase', 'literal'), 'alignment_parameters_invalid'); _pairs(row['pairs'])
        elif kind == 'ungapped_map':
            common.indices(row['row_indices'])
        elif kind == 'tree':
            require(row['branch_unit'] in shared.BRANCH_UNITS, 'branch_unit_invalid'); _pairs(row['pairs'])
        elif kind == 'relationship_comparison':
            _tip_join(row['injective_tip_join'])
            require(all(x['gene_tree_id'] == row['gene_tree_id'] and x['organismal_tree_id'] == row['organismal_tree_id'] for x in row['injective_tip_join']), 'comparison_tree_conflict')
        elif kind == 'msa_entropy':
            require(row['alphabet'] in ('dna', 'protein') and row['case_policy'] == 'uppercase' and row['terminal_gap'] == '-' and row['native_rounding'] in (native.ROUNDING, None), 'entropy_parameters_invalid')
            common.text(row['observed_table_id'], nullable=True)
        elif kind == 'msa_reference_differences':
            require(row['alphabet'] in ('dna', 'protein') and row['case_policy'] in ('preserve', 'uppercase'), 'reference_parameters_invalid')
            common.indices(row['member_row_indices']); native._validate_reference(row['reference'])
        elif kind.startswith('xmfa_'):
            if 'use_source_bindings' in row:
                require(type(row['use_source_bindings']) is bool, 'source_selection_invalid')
            if 'selection' in row:
                xmfa.validate_xmfa_selection(row['selection']); require(row['selection']['document_id'] == row['document_id'], 'selection_document_conflict')
            if kind == 'xmfa_alignment_components':
                require(row['case_policy'] in ('preserve', 'uppercase'), 'case_policy_invalid'); _pairs(row['selected_pairs'], minimum=1, distinct=True, unordered=True)
                require(all(i in row['selection']['member_numbers'] for pair in row['selected_pairs'] for i in pair), 'pair_member_unknown')
            elif kind == 'xmfa_interval_coverage':
                require(row['basis'] in xmfa.BASES, 'coverage_basis_invalid')
            elif kind == 'xmfa_column_coordinates':
                common.array(row['cells']); keys = [xmfa.ref(v, cell=True) for v in row['cells']]
                require(len(set(keys)) == len(keys), 'duplicate_cell')
            else:
                common.array(row['queries']); keys = []
                for query in row['queries']:
                    shape(query, {'member_number', 'position_0based'}); common.integer(query['member_number'], minimum=1); common.integer(query['position_0based']); keys.append(tuple(query[k] for k in ('member_number', 'position_0based')))
                require(len(set(keys)) == len(keys), 'duplicate_query')
    return deepcopy(parameters)


def lookup_population(sheet, kind, identity):
    return next((row for row in sheet['populations'][kind] if row['population_id'] == identity), None)


def lookup_alignment(sheet, identity):
    return next((d['value'] for d in sheet['documents'] if d['kind'] == 'alignment' and d['value']['alignment_id'] == identity), None)


def lookup_document(sheet, identity, kind):
    return next((d['value'] for d in sheet['documents'] if d['kind'] == kind and common.document_identity(d) == identity), None)


def lookup_tree(sheet, identity):
    return next((t for d in sheet['documents'] if d['kind'] == 'tree' for t in d['value']['trees'] if t['tree_id'] == identity), None)


def coverage_operands(sheet, population):
    members = sheet['associations']['original_members']; result = []
    for index in population['row_indices']:
        rows = [r for r in sheet['associations']['row_members'] if r['alignment_id'] == population['alignment_id'] and r['row_index'] == index]
        if len(rows) != 1 or rows[0]['state'] != 'resolved' or len(rows[0]['member_keys']) != 1:
            return None
        key = rows[0]['member_keys'][0]
        candidates = [m for m in members if all(m['key'][k] == key[k] for k in ('input_binding_id', 'member_id'))]
        if len(candidates) != 1:
            return None
        member = candidates[0]
        result.append({'row': {'alignment_id': population['alignment_id'], 'row_index': index},
            'member': {k: key[k] for k in ('input_binding_id', 'member_id')},
            'original_length': member['original_length'], 'original_sequence_sha256': member['sequence_sha256'], 'evidence': member['evidence']})
    return result


def reference_identity_proven(sheet, reference):
    """Check retained input/row identity without interpreting a FASTA string.

    The existing inline reader supplied physical occurrences and exact input
    text. Unsupported compound transforms remain unresolved; no string-equality
    fallback selects one of several original occurrences.
    """
    if reference['native_ref_type'] != 'string':
        return reference['identity_state'] == 'resolved'
    matches = [b for b in sheet['inputs'] if b['kind'] == 'inline_parameter'
               and type(b['inline_value']) is str and b['inline_value'] == reference['native_ref_string']]
    if len(matches) != 1:
        return False
    binding = matches[0]; aid, index = reference['alignment_id'], reference['row_index']
    rows = [r for r in sheet['associations']['row_members'] if r['alignment_id'] == aid and r['row_index'] == index]
    if len(rows) != 1 or rows[0]['state'] != 'resolved' or len(rows[0]['member_keys']) != 1:
        return False
    key = rows[0]['member_keys'][0]
    if key['input_binding_id'] != binding['binding_id']:
        return False
    if reference['original_member'] is not None and any(key[k] != v for k,v in reference['original_member'].items()):
        return False
    members = [m for m in sheet['associations']['original_members'] if all(m['key'][k] == key[k] for k in ('input_binding_id','member_id'))]
    inline = [v for v in sheet['associations']['inline_inputs'] if v['input_binding_id'] == binding['binding_id']]
    if len(members) != 1 or len(inline) != 1 or inline[0]['completeness'] != 'complete' or len(inline[0]['rows']) != 1:
        return False
    member = members[0]
    if member['source_row_index'] is None or member['source_row_index'] >= len(inline[0]['rows']):
        return False
    source = inline[0]['rows'][member['source_row_index']]['sequence']
    alignment = lookup_alignment(sheet, aid)
    if alignment is None or index >= len(alignment['rows']):
        return False
    output = alignment['rows'][index]['sequence']; gaps = False
    transforms = {t['transformation_id']: t for t in sheet['associations']['transformations']}
    for identity in rows[0]['transformation_ids']:
        transform = transforms.get(identity)
        if transform is None or key not in transform['input_members'] or {'alignment_id':aid,'row_index':index} not in transform['output_rows']:
            return False
        kind = transform['kind']
        if kind == 'uppercase':
            source = source.upper()
        elif kind == 'remove_symbols':
            source = ''.join(s for s in source if s not in transform['symbols'])
        elif kind == 'align_insert_gaps':
            gaps = True
        elif kind not in ('identity','rename'):
            return False
    return source == (output.replace('-', '') if gaps else output)


def effective_reference(sheet, requested):
    actual = sheet['analysis']['reference']
    if actual is None:
        return None
    require(all(requested[k] == actual[k] for k in requested if k != 'identity_state'), 'reference_request_conflict')
    require(requested['identity_state'] == actual['identity_state'] or requested['identity_state'] == 'resolved' and actual['identity_state'] == 'unresolved', 'reference_request_conflict')
    return actual


def _reference(value, sheet, alignments):
    native._validate_reference(value)
    aid, index = value['alignment_id'], value['row_index']
    require(aid in alignments and index < len(alignments[aid]['rows']), 'reference_row_unknown')
    if value['original_member'] is not None:
        keys = [m['key'] for m in sheet['associations']['original_members'] if all(m['key'][k] == v for k, v in value['original_member'].items())]
        require(len(keys) == 1, 'reference_original_occurrence_ambiguous')
        rows = [r for r in sheet['associations']['row_members'] if r['alignment_id'] == aid and r['row_index'] == index]
        require(len(rows) == 1 and keys[0] in rows[0]['member_keys'], 'reference_original_conflict')
    if value['identity_state'] == 'resolved' and value['native_ref_type'] == 'string':
        require(reference_identity_proven(sheet, value), 'reference_original_proof_missing')


def validate_analysis(value, sheet, docs, alignments, trees):
    shape(value, {'analysis_id', 'mode', 'alignment_id', 'frequency_table_id', 'consensus_alignment_id', 'tree_id', 'full_xmfa_slot_id', 'xmfa_document_id', 'segment_ids', 'reference', 'output_role_evidence'})
    common.text(value['analysis_id']); require(value['mode'] in MODES, 'mode_invalid'); common.strings(value['segment_ids']); common.evidence(value['output_role_evidence'])
    for key, kind in (('alignment_id', 'alignment'), ('frequency_table_id', 'msa_frequency'), ('consensus_alignment_id', 'alignment'), ('xmfa_document_id', 'xmfa')):
        identity = value[key]; common.text(identity, nullable=True)
        require(identity is None or identity in docs and docs[identity]['kind'] == kind, 'analysis_document_conflict')
    common.text(value['tree_id'], nullable=True); require(value['tree_id'] is None or value['tree_id'] in trees, 'analysis_tree_unknown')
    common.text(value['full_xmfa_slot_id'], nullable=True)
    if value['xmfa_document_id'] is not None:
        require(value['full_xmfa_slot_id'] is not None, 'xmfa_slot_missing')
        matches = [r for r in sheet['read_outcomes'] if r['slot_id'] == value['full_xmfa_slot_id']]
        require(len(matches) == 1 and value['xmfa_document_id'] in matches[0]['document_ids'] and matches[0]['reader']['reader'] == 'mauve_xmfa_v1', 'xmfa_slot_document_conflict')
    if value['reference'] is not None:
        _reference(value['reference'], sheet, alignments)
        require(value['reference']['alignment_id'] == value['alignment_id'], 'reference_analysis_conflict')


def _segments(sheet, alignments):
    values = common.unique(sheet['segments'], 'segment_id')
    require(set(values) == set(sheet['analysis']['segment_ids']), 'segment_population_conflict')
    members = {common.member_key(m['key']): m for m in sheet['associations']['original_members']}
    records = {s['source_record_id']: s for s in sheet['associations']['source_records']}
    ordered = []
    for row in values.values():
        shape(row, {'segment_id', 'native_segment_token', 'genome_id', 'genome_sequence_record_id', 'contig_id', 'original_interval_0based_half_open', 'strand', 'input_member', 'alignment_id', 'concatenated_interval_0based_half_open', 'order_index', 'state', 'evidence'})
        common.text(row['segment_id']); common.text(row['native_segment_token'], empty=True); common.evidence(row['evidence'])
        for key in ('genome_id', 'genome_sequence_record_id', 'contig_id', 'alignment_id'):
            common.text(row[key], nullable=True)
        require(row['strand'] in ('+', '-', 'unknown') and row['state'] in ('resolved', 'missing', 'conflicting'), 'segment_state_invalid')
        common.integer(row['order_index'], nullable=True)
        require(row['alignment_id'] is None or row['alignment_id'] in alignments, 'segment_alignment_unknown')
        if row['genome_sequence_record_id'] is not None:
            require(row['genome_sequence_record_id'] in records and records[row['genome_sequence_record_id']]['kind'] == 'sequence', 'segment_source_unknown')
        member = None
        if row['input_member'] is not None:
            key = common.member_key(row['input_member']); require(key in members, 'segment_member_unknown'); member = members[key]
            require(row['genome_id'] is None or row['genome_id'] in member['genome_ids'], 'segment_genome_conflict')
        for field in ('original_interval_0based_half_open', 'concatenated_interval_0based_half_open'):
            if row[field] is not None:
                common.interval(row[field])
        if member is not None and row['original_interval_0based_half_open'] is not None and member['original_length'] is not None:
            require(row['original_interval_0based_half_open'][1] <= member['original_length'], 'segment_original_interval_conflict')
        if row['concatenated_interval_0based_half_open'] is not None:
            final = alignments.get(sheet['analysis']['alignment_id']); require(final is not None, 'segment_final_alignment_missing')
            bound = max((len(r['sequence']) for r in final['rows']), default=0)
            require(row['concatenated_interval_0based_half_open'][1] <= bound, 'segment_concatenated_interval_conflict')
        if row['order_index'] is not None:
            ordered.append(row)
    require(len({r['order_index'] for r in ordered}) == len(ordered), 'segment_order_duplicate')
    for transform in sheet['associations']['transformations']:
        if transform['kind'] == 'concatenate':
            require(all(i in values for i in transform['segment_order']), 'transformation_segment_unknown')
            for item in transform['output_intervals']:
                row = values[item['segment_id']]
                require(row['concatenated_interval_0based_half_open'] == item['interval_0based_half_open'], 'transformation_segment_interval_conflict')
            require([values[i]['order_index'] for i in transform['segment_order']] == sorted(values[i]['order_index'] for i in transform['segment_order'] if values[i]['order_index'] is not None), 'transformation_segment_order_conflict')
        elif transform['kind'] == 'missing_segment_gap_fill':
            require(transform['segment_id'] in values, 'transformation_segment_unknown')
            start, end = transform['output_interval_0based_half_open']
            require(values[transform['segment_id']]['concatenated_interval_0based_half_open'] == [start, end], 'gap_fill_segment_interval_conflict')
            for ref in transform['output_rows']:
                require(alignments[ref['alignment_id']]['rows'][ref['row_index']]['sequence'][start:end] == '-' * (end-start), 'gap_fill_sequence_conflict')


def _tree_bindings(sheet, alignments, trees):
    bindings = common.unique(sheet['tree_bindings'], 'tree_id'); commands = {r['command_id']: r for r in sheet['run']['commands']}
    for row in bindings.values():
        shape(row, {'tree_id', 'role', 'source_tree_id', 'alignment_id', 'command_id', 'branch_unit', 'support_method', 'support_scale', 'tip_rows', 'evidence'})
        require(row['tree_id'] in trees and row['role'] in ('inference', 'midpoint_display', 'organismal'), 'tree_binding_invalid')
        for key in ('source_tree_id', 'alignment_id', 'command_id'):
            common.text(row[key], nullable=True)
        require(row['source_tree_id'] is None or row['source_tree_id'] in trees and row['source_tree_id'] != row['tree_id'], 'source_tree_unknown')
        require(row['alignment_id'] is None or row['alignment_id'] in alignments, 'tree_alignment_unknown')
        require(row['command_id'] is None or row['command_id'] in commands, 'tree_command_unknown')
        require(row['branch_unit'] in shared.BRANCH_UNITS and row['support_method'] in ('fasttree_sh_like', 'native_unknown') and row['support_scale'] in shared.SUPPORT_SCALES, 'tree_semantics_invalid'); common.evidence(row['evidence'])
        common.unique(row['tip_rows'], 'node_index')
        for tip in row['tip_rows']:
            shape(tip, {'node_index', 'alignment_id', 'row_index', 'evidence'}); common.integer(tip['node_index']); common.evidence(tip['evidence'])
            common.row_ref({k: tip[k] for k in ('alignment_id', 'row_index')}, alignments)
            require(tip['alignment_id'] == row['alignment_id'] and tip['node_index'] < len(trees[row['tree_id']]['nodes']) and not trees[row['tree_id']]['nodes'][tip['node_index']]['child_indices'], 'tree_tip_conflict')
    return bindings


def native_fields(table):
    """Native field paths only; this performs no numerical calculation."""
    for row in table['rows']:
        yield row, 'score', 'msa_score', [], 'hundredths_of_bit', row['score']
        yield row, 'n_sequences', 'msa_sequence_count', [], 'sequences', row['n_sequences']
        if table['alphabet'] == 'dna':
            for index, symbol in enumerate(('A', 'T', 'G', 'C', 'Deletion')):
                yield row, 'dna_counts/' + symbol, 'msa_symbol_count', [index], 'observations', row['dna_counts'][symbol]
        else:
            for index, entry in enumerate(row['protein_detail']):
                yield row, 'protein_detail/' + str(index) + '/count', 'msa_symbol_count', [index], 'observations', entry['count']


def native_population(sheet, table):
    if table['table_id'] != sheet['analysis']['frequency_table_id']:
        return None
    alignment = lookup_alignment(sheet, sheet['analysis']['alignment_id'])
    if alignment is None:
        return None
    width = alignment['observed_column_count']
    candidates = [p for p in sheet['populations']['alignments'] if p['alignment_id'] == alignment['alignment_id'] and p['completeness'] == 'complete' and set(p['row_indices']) == set(range(len(alignment['rows']))) and width is not None and set(p['columns_0based']) == set(range(width))]
    return candidates[0]['population_id'] if len(candidates) == 1 else None


def _native_observations(sheet, docs):
    observations = common.unique(sheet['native_observations'], 'observation_id'); expected = set()
    for document in docs.values():
        if document['kind'] != 'msa_frequency':
            continue
        table = document['value']; population = native_population(sheet, table)
        for row, suffix, field, indices, unit, source in native_fields(table):
            identity = table['table_id'] + '/rows/' + str(row['row_index']) + '/' + suffix; expected.add(identity)
            require(identity in observations, 'native_observation_missing'); obs = observations[identity]
            shape(obs, {'observation_id', 'document_id', 'row_index', 'field', 'nested_indices', 'number', 'unit', 'population_id', 'category_id', 'group_ids', 'association_state', 'evidence'})
            validate_native_number(obs['number']); common.evidence(obs['evidence'])
            require(obs['document_id'] == table['table_id'] and obs['row_index'] == row['row_index'] and obs['field'] == field and obs['nested_indices'] == indices and obs['unit'] == unit and obs['number'] == source, 'native_observation_source_conflict')
            require(obs['category_id'] is None and obs['group_ids'] == [] and obs['population_id'] == population and obs['association_state'] == ('resolved' if population is not None else 'missing'), 'native_observation_population_conflict')
    require(set(observations) == expected, 'native_observation_population_conflict')


def _consensus(sheet, docs, alignments):
    seen = set()
    for row in sheet['consensus_associations']:
        shape(row, {'consensus_alignment_id', 'consensus_row_index', 'source_alignment_id', 'source_population_id', 'frequency_table_id', 'columns', 'method', 'state', 'evidence'})
        key = row['consensus_alignment_id'], row['consensus_row_index']; require(key not in seen, 'consensus_duplicate'); seen.add(key)
        common.row_ref({'alignment_id': key[0], 'row_index': key[1]}, alignments)
        require(row['source_alignment_id'] == sheet['analysis']['alignment_id'] and key[0] == sheet['analysis']['consensus_alignment_id'], 'consensus_alignment_conflict')
        common.text(row['source_population_id']); common.text(row['frequency_table_id'], nullable=True); common.evidence(row['evidence']); common.array(row['columns'])
        population = lookup_population(sheet, 'alignments', row['source_population_id']); require(population is not None and population['alignment_id'] == row['source_alignment_id'], 'consensus_population_unknown')
        require(row['state'] in ('resolved', 'missing', 'conflicting') and row['method'] in ('native_table_consensus_then_remove_dash', 'unresolved'), 'consensus_state_invalid')
        if row['state'] != 'resolved':
            require(row['method'] == 'unresolved' and not row['columns'], 'consensus_unresolved_columns'); continue
        require(row['method'] == 'native_table_consensus_then_remove_dash' and row['frequency_table_id'] == sheet['analysis']['frequency_table_id'], 'consensus_table_conflict')
        table = docs[row['frequency_table_id']]['value']; source = alignments[row['source_alignment_id']]
        require(native_population(sheet, table) == row['source_population_id'], 'consensus_full_population_required')
        positions = {r['alignment_position']['value']-1: r for r in table['rows'] if r['alignment_position']['state'] == 'available'}
        require(len(positions) == len(table['rows']) == source['observed_column_count'] and set(positions) == set(range(source['observed_column_count'])), 'consensus_coordinate_conflict')
        require([x['source_column_0based'] for x in row['columns']] == list(range(source['observed_column_count'])), 'consensus_column_population_conflict')
        sequence, offset = [], 0
        for mapping in row['columns']:
            shape(mapping, {'source_column_0based', 'consensus_position_0based', 'symbol'}); common.integer(mapping['consensus_position_0based'], nullable=True)
            token = positions[mapping['source_column_0based']]['consensus_token']; symbol = token if table['alphabet'] == 'dna' else PROTEIN_SYMBOLS.get(token)
            require(type(symbol) is str and len(symbol) == 1 and mapping['symbol'] == symbol, 'consensus_symbol_conflict')
            require(mapping['consensus_position_0based'] == (None if symbol == '-' else offset), 'consensus_position_conflict')
            if symbol != '-':
                sequence.append(symbol); offset += 1
        require(''.join(sequence) == alignments[key[0]]['rows'][key[1]]['sequence'], 'consensus_sequence_conflict')


def effective_tree_semantics(sheet, binding):
    if binding is None:
        return 'native_unknown', 'native_unknown', 'native_unknown'
    command = next((r for r in sheet['run']['commands'] if r['command_id'] == binding['command_id']), None)
    observed = command is not None and command['origin'] == 'observed' and command['role'] in ('tree_inference', 'reroot') and bool(command['evidence']) and bool(binding['evidence'])
    return (binding['branch_unit'], binding['support_method'], binding['support_scale']) if observed else ('native_unknown', 'native_unknown', 'native_unknown')


def numeric_label(token):
    return type(token) is str and (re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', token.strip()) is not None or token.strip().lower() in ('nan','inf','+inf','-inf','infinity'))


def _tree_measurements(sheet, trees, bindings):
    observations = common.unique(sheet['native_tree_measurements'], 'observation_id'); supports = common.unique(sheet['support_observations'], 'native_observation_id')
    for row in observations.values():
        shared.native_observation(row)
        candidates = [(tid, n) for tid, tree in trees.items() for n in tree['nodes'] if row['subject_id'] == tid + '/node/' + str(n['node_index'])]
        require(len(candidates) == 1, 'native_tree_node_unknown'); tid, node = candidates[0]
        require(row['population_id'] == tid and row['location'] == node['source_location'], 'native_tree_source_conflict')
        unit, method, scale = effective_tree_semantics(sheet, bindings.get(tid))
        if row['field'] == 'branch_length':
            require(row['value'] == node['branch_length'] and row['raw_token'] == node['branch_length_token'] and row['unit'] == unit and row['method'] == 'native_branch_length', 'native_branch_length_conflict')
        else:
            require(row['field'] == 'branch_support_native' and node['parent_index'] is not None and node['child_indices'], 'native_support_node_conflict')
            require(row['raw_token'] == node['label_token'] and row['unit'] == {'fraction':'fraction','percent':'percent','statistic':'native_statistic','native_unknown':'native_unknown'}[scale] and row['method'] == method, 'native_support_source_conflict')
            expected = _native_number(node['decoded_label'])
            require(row['value'] == expected, 'native_support_value_conflict')
            require(row['observation_id'] in supports, 'support_association_missing')
    expected_support = {tid + '/node/' + str(n['node_index']) + '/branch_support_native' for tid, tree in trees.items() for n in tree['nodes'] if n['parent_index'] is not None and n['child_indices'] and numeric_label(n['decoded_label'])}
    require({o['observation_id'] for o in observations.values() if o['field'] == 'branch_support_native'} == expected_support, 'native_support_population_conflict')
    expected_lengths = {tid + '/node/' + str(n['node_index']) + '/branch_length' for tid, tree in trees.items() for n in tree['nodes'] if n['branch_length_token'] is not None}
    require({o['observation_id'] for o in observations.values() if o['field'] == 'branch_length'} == expected_lengths, 'native_length_population_conflict')
    for row in supports.values():
        shape(row, {'tree_id', 'node_index', 'native_observation_id', 'source_kind', 'method', 'scale', 'command_id', 'bootstrap_population_id', 'evidence'})
        require(row['tree_id'] in trees and row['native_observation_id'] in observations, 'support_reference_unknown'); common.integer(row['node_index']); common.evidence(row['evidence'])
        obs = observations[row['native_observation_id']]; binding = bindings.get(row['tree_id']); _, method, scale = effective_tree_semantics(sheet, binding)
        require(obs['subject_id'] == row['tree_id'] + '/node/' + str(row['node_index']) and obs['field'] == 'branch_support_native' and row['method'] == method and row['scale'] == scale and row['source_kind'] == 'internal_label' and row['bootstrap_population_id'] is None and row['command_id'] == (binding['command_id'] if binding else None), 'support_association_conflict')


@closed
def validate_msa_sheet(sheet: dict) -> dict:
    shape(sheet, SHEET_KEYS); require(sheet['schema_version'] == 'bvbrc_msa_sheet_v1' and sheet['tool'] == 'C-L204-MSA', 'sheet_version_invalid')
    common.input_map(sheet['inputs']); docs, alignments, trees = common.document_maps(sheet['documents'])
    require(all(d['kind'] in ('alignment', 'msa_frequency', 'tree', 'xmfa') for d in sheet['documents']), 'document_provider_conflict')
    common.validate_run_record(sheet['run']); common.validate_association_set(sheet['associations'], inputs=tuple(sheet['inputs']), documents=tuple(sheet['documents']))
    common.validate_populations(sheet['populations'], documents=tuple(sheet['documents']), associations=sheet['associations'])
    common.unique(sheet['read_outcomes'], 'read_id')
    for row in sheet['read_outcomes']:
        common.validate_reader_spec(row['reader'], provider='msa'); common.validate_reader_outcome(row, documents=tuple(sheet['documents']))
    validate_analysis(sheet['analysis'], sheet, docs, alignments, trees); _segments(sheet, alignments)
    bindings = _tree_bindings(sheet, alignments, trees)
    _native_observations(sheet, docs); common.array(sheet['consensus_associations']); _consensus(sheet, docs, alignments)
    _tree_measurements(sheet, trees, bindings)
    common.unique(sheet['xmfa_bindings'], 'document_id')
    for binding in sheet['xmfa_bindings']:
        require(binding['document_id'] in docs and docs[binding['document_id']]['kind'] == 'xmfa', 'xmfa_binding_document_unknown')
        validate_msa_xmfa_binding_record(binding, document=docs[binding['document_id']]['value'], associations=sheet['associations'])
    common.reports(sheet)
    for source in [sheet['associations'], *sheet['xmfa_bindings']]:
        require(all(r in sheet['requirements'] for r in source['requirements']) and all(d in sheet['diagnostics'] for d in source['diagnostics']), 'source_reports_missing')
    return deepcopy(sheet)


def _quantity(cell, *, population, unit, method=None, origin='derived'):
    shape(cell, {'value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_ref', 'method', 'evidence', 'requirement_ids'})
    require(cell['population_ref'] == population and cell['unit'] == unit, 'quantity_population_or_unit_conflict')
    common.text(cell['method']); require(method is None or cell['method'] == method, 'quantity_method_conflict')
    require(cell['state'] in shared.STATES and cell['origin'] == origin, 'quantity_state_invalid')
    for key in ('value', 'numerator', 'denominator'):
        number(cell[key], nullable=True)
    require((cell['value'] is not None) == (cell['state'] == 'available'), 'quantity_availability_conflict')
    common.evidence(cell['evidence']); common.strings(cell['requirement_ids'])
    if unit == 'fraction' and cell['value'] is not None:
        require(0 <= cell['value'] <= 1, 'quantity_fraction_invalid')


def _shared_result(value, request, sheet):
    kind = request['kind']
    if kind == 'ungapped_map':
        alignment = lookup_alignment(sheet, request['alignment_id']); require(alignment is not None, 'result_alignment_unknown')
        common.array(value)
        expected = [(i, j) for i in request['row_indices'] for j in range(len(alignment['rows'][i]['sequence']))]
        require([(r['row_index'], r['column_0based']) for r in value] == expected, 'coordinate_population_conflict')
        offsets = {i: 0 for i in request['row_indices']}
        for row in value:
            shape(row, {'alignment_id', 'row_index', 'column_0based', 'ungapped_position_0based'})
            require(row['alignment_id'] == request['alignment_id'], 'coordinate_alignment_conflict')
            symbol = alignment['rows'][row['row_index']]['sequence'][row['column_0based']]
            require(row['ungapped_position_0based'] == (None if symbol == '-' else offsets[row['row_index']]), 'coordinate_value_conflict')
            offsets[row['row_index']] += symbol != '-'
        return
    population_kind = 'composition' if kind == 'function_composition' else 'taxonomy' if kind == 'taxonomy' else 'alignments'
    population = lookup_population(sheet, population_kind, request['population_id']); require(population is not None, 'result_population_unknown')
    pid = population['population_id']
    require(value['population_id'] == pid, 'result_population_conflict')
    if kind == 'alignment':
        classifications = ('gap', 'canonical', 'ambiguity', 'stop', 'other_nongap')
        shape(value, {'population_id', 'alignment_id', 'member_count', 'site_count', 'cell_count', 'sites', 'rows', 'pairs', 'identical_sequence_groups',
            *(k + suffix for k in classifications for suffix in ('_cells', '_fraction'))})
        require(value['alignment_id'] == population['alignment_id'], 'result_alignment_conflict')
        for key, unit, method in (('member_count', 'rows', 'selected_row_count'), ('site_count', 'columns', 'selected_column_count'), ('cell_count', 'characters', 'selected_cell_count')):
            _quantity(value[key], population=pid, unit=unit, method=method)
        for key, expected in (('member_count', len(population['row_indices'])), ('site_count', len(population['columns_0based'])), ('cell_count', len(population['row_indices']) * len(population['columns_0based']))):
            require(value[key]['value'] is None or value[key]['value'] == expected, 'alignment_denominator_conflict')
        for key in classifications:
            _quantity(value[key + '_cells'], population=pid, unit='characters', method=key + '_symbol_count')
            _quantity(value[key + '_fraction'], population=pid, unit='fraction', method=key + '_cell_fraction')
        require([r['column_0based'] for r in value['sites']] == population['columns_0based'], 'site_population_conflict')
        for row in value['sites']:
            shape(row, {'column_0based', 'symbol_counts', *(k + '_count' for k in classifications), 'gap_fraction', 'canonical_fraction', 'canonical_majority_fraction', 'canonical_entropy_bits'})
            common.array(row['symbol_counts']); symbols = set()
            for item in row['symbol_counts']:
                shape(item, {'symbol', 'count'}); require(type(item['symbol']) is str and len(item['symbol']) == 1 and item['symbol'] not in symbols, 'site_symbol_invalid'); symbols.add(item['symbol']); common.integer(item['count'], minimum=1)
            for key in classifications:
                _quantity(row[key + '_count'], population=pid, unit='characters', method=key + '_symbol_count')
            for key in ('gap_fraction', 'canonical_fraction', 'canonical_majority_fraction', 'canonical_entropy_bits'):
                method = 'site_' + key if key in ('gap_fraction', 'canonical_fraction') else key
                _quantity(row[key], population=pid, unit='bits' if key.endswith('bits') else 'fraction', method=method)
        require([r['row_index'] for r in value['rows']] == population['row_indices'], 'row_population_conflict')
        for row in value['rows']:
            shape(row, {'row_index', 'nongap_count', 'matrix_occupancy'})
            _quantity(row['nongap_count'], population=pid, unit='characters', method='row_nongap_count')
            _quantity(row['matrix_occupancy'], population=pid, unit='fraction', method='row_matrix_occupancy')
        require([[r['row_a'], r['row_b']] for r in value['pairs']] == request['pairs'], 'pair_population_conflict')
        pair_keys = ('identical_positions', 'substitutions', 'both_gap_positions', 'a_gap_only_positions', 'b_gap_only_positions', 'unpaired_nongap_ambiguous_positions')
        for row in value['pairs']:
            shape(row, {'row_a', 'row_b', *pair_keys, 'identity_fraction'})
            for key in pair_keys:
                _quantity(row[key], population=pid, unit='columns', method='pairwise_' + key)
            _quantity(row['identity_fraction'], population=pid, unit='fraction', method='pairwise_canonical_identity')
        common.array(value['identical_sequence_groups']); seen = set()
        for row in value['identical_sequence_groups']:
            shape(row, {'row_indices', 'size'}); common.indices(row['row_indices'])
            require(len(row['row_indices']) > 1 and set(row['row_indices']) <= set(population['row_indices']) and not seen.intersection(row['row_indices']), 'identical_group_population_conflict'); seen.update(row['row_indices'])
            _quantity(row['size'], population=pid, unit='rows', method='identical_final_sequence_group_size')
    elif kind == 'original_coverage':
        shape(value, {'population_id', 'alignment_id', 'rows', 'missing_requirements', 'diagnostics'})
        require(value['alignment_id'] == population['alignment_id'], 'coverage_alignment_conflict')
        members = coverage_operands(sheet, population); require(members is not None, 'coverage_original_identity_missing')
        require([(r['row_index'], r['member']) for r in value['rows']] == [(r['row']['row_index'], r['member']) for r in members], 'coverage_member_conflict')
        common.reports({'requirements': value['missing_requirements'], 'diagnostics': value['diagnostics']})
        for row in value['rows']:
            shape(row, {'row_index', 'member', 'original_length', 'original_covered_positions', 'original_member_coverage'})
            for key in ('original_length', 'original_covered_positions', 'original_member_coverage'):
                _quantity(row[key], population=pid, unit='fraction' if key.endswith('coverage') else 'positions', origin='native_observed' if key == 'original_length' else 'derived')
    elif kind == 'function_composition':
        shape(value, {'population_id', 'unit', 'total_members', 'members_with_recorded_assignment', 'members_without_recorded_assignment', 'rows'})
        require(value['unit'] == population['unit'], 'composition_unit_conflict')
        for key in ('total_members', 'members_with_recorded_assignment', 'members_without_recorded_assignment'):
            _quantity(value[key], population=pid, unit='members')
        common.unique(value['rows'], 'function_key')
        allowed_functions = {r['function_key'] for r in sheet['associations']['functions']} | {r['canonical_function_key'] for r in sheet['associations']['function_equivalences']}
        for row in value['rows']:
            shape(row, {'function_key', 'member_subjects', 'assigned_members', 'fraction_all', 'fraction_recorded'})
            require(row['function_key'] in allowed_functions, 'composition_function_unknown')
            common.unique(row['member_subjects'], shared.subject)
            require(all(s in population['member_subjects'] for s in row['member_subjects']), 'composition_member_unknown')
            for key in ('assigned_members', 'fraction_all', 'fraction_recorded'):
                _quantity(row[key], population=pid, unit='members' if key == 'assigned_members' else 'fraction')
    else:
        keys = {'known_members': 'members', 'unknown_members': 'members', 'distinct_known_taxa': 'taxa', 'same_taxon_pairs': 'pairs', 'known_taxon_pairs': 'pairs', 'same_taxon_pair_fraction': 'fraction'}
        shape(value, {'population_id', 'rank', 'rows', *keys}); require(value['rank'] == request['rank'], 'taxonomy_rank_conflict')
        for key, unit in keys.items():
            _quantity(value[key], population=pid, unit=unit)
        common.unique(value['rows'], 'taxon_id')
        for row in value['rows']:
            shape(row, {'taxon_id', 'member_subjects', 'member_count'}); common.text(row['taxon_id'])
            common.unique(row['member_subjects'], shared.subject)
            require(all(s in population['member_subjects'] for s in row['member_subjects']), 'taxonomy_member_unknown')
            _quantity(row['member_count'], population=pid, unit='members')



def _split(row, *, tree, selected, prefix):
    shape(row, {'split_id', 'tree_id', 'side_node_indices', 'complement_node_indices', 'edge_node_indices'})
    require(row['tree_id'] == tree['tree_id'], 'split_tree_conflict')
    for field in ('side_node_indices', 'complement_node_indices', 'edge_node_indices'):
        common.indices(row[field])
    left, right = set(row['side_node_indices']), set(row['complement_node_indices'])
    require(not left & right and left | right == set(selected) and len(left) >= 2 and len(right) >= 2, 'split_population_conflict')
    require(row['split_id'] == prefix + '/split/' + ','.join(str(i) for i in row['side_node_indices']), 'split_identity_conflict')
    require(all(i < len(tree['nodes']) and tree['nodes'][i]['parent_index'] is not None for i in row['edge_node_indices']), 'split_edge_unknown')


def _tree_result(value, request, sheet):
    population = lookup_population(sheet, 'leaves', request['population_id']); require(population is not None, 'tree_population_unknown')
    tree = lookup_tree(sheet, population['tree_id']); pid = population['population_id']
    shape(value, {'population_id', 'tree_id', 'tip_count', 'internal_node_count', 'rooted_representation_polytomies', 'unrooted_degree_polytomies', 'branch_length_sum', 'known_branch_length_sum', 'missing_branch_length_count', 'splits', 'branches', 'distances'})
    require(value['population_id'] == pid and value['tree_id'] == tree['tree_id'], 'tree_result_identity_conflict')
    methods = {'tip_count': ('tips', 'tree_tip_count'), 'internal_node_count': ('nodes', 'internal_node_count'),
        'rooted_representation_polytomies': ('nodes', 'rooted_child_degree_gt2'), 'unrooted_degree_polytomies': ('nodes', 'unrooted_degree_gt3'),
        'missing_branch_length_count': ('edges', 'missing_branch_length_count')}
    for field, (unit, method) in methods.items():
        _quantity(value[field], population=pid, unit=unit, method=method)
    for field in ('branch_length_sum', 'known_branch_length_sum'):
        require(value[field]['unit'] in shared.BRANCH_UNITS, 'branch_unit_invalid'); _quantity(value[field], population=pid, unit=value[field]['unit'], method=field)
    splits = common.unique(value['splits'], 'split_id')
    for row in splits.values():
        _split(row, tree=tree, selected=population['node_indices'], prefix=tree['tree_id'])
    require([r['node_index'] for r in value['branches']] == [n['node_index'] for n in tree['nodes'] if n['parent_index'] is not None], 'branch_population_conflict')
    saved_support = {r['native_observation_id']: r for r in sheet['support_observations']}
    for row in value['branches']:
        shape(row, {'node_index', 'split_id', 'length', 'native_support_observation_ids', 'support_method', 'support_scale', 'support_rescaled'})
        require(row['split_id'] is None or row['split_id'] in splits and row['node_index'] in splits[row['split_id']]['edge_node_indices'], 'branch_split_conflict')
        common.strings(row['native_support_observation_ids'])
        require(all(i in saved_support and saved_support[i]['tree_id'] == tree['tree_id'] and saved_support[i]['node_index'] == row['node_index'] for i in row['native_support_observation_ids']), 'branch_support_unknown')
        require(row['support_method'] in shared.SUPPORT_METHODS and row['support_scale'] in shared.SUPPORT_SCALES, 'branch_support_meaning_invalid')
        require(row['length']['unit'] in shared.BRANCH_UNITS, 'branch_unit_invalid')
        _quantity(row['length'], population=pid, unit=row['length']['unit'], method='native_branch_length', origin='native_fitted')
        require(row['length']['value'] == tree['nodes'][row['node_index']]['branch_length'], 'branch_length_source_conflict')
        _quantity(row['support_rescaled'], population=pid, unit='fraction', method=row['support_method'])
    require([[r['node_a'], r['node_b']] for r in value['distances']] == request['pairs'], 'tree_pair_conflict')
    for row in value['distances']:
        shape(row, {'node_a', 'node_b', 'value'}); require(row['value']['unit'] in shared.BRANCH_UNITS, 'branch_unit_invalid')
        _quantity(row['value'], population=pid, unit=row['value']['unit'], method='patristic_distance')


def _relationship_result(value, request, sheet):
    shape(value, {'comparison_id', 'matched_tip_pairs', 'omitted_gene_tips', 'omitted_organismal_tips', 'matched_tips', 'gene_splits', 'organismal_splits', 'shared_splits', 'rf', 'rf_fraction', 'restricted_gene_splits', 'restricted_organismal_splits', 'shared_split_pairs'})
    require(value['comparison_id'] == request['comparison_id'] and value['matched_tip_pairs'] == request['injective_tip_join'], 'comparison_identity_conflict')
    members = {common.member_key(m['key']): m for m in sheet['associations']['original_members']}
    sources = {r['source_record_id']: r for r in sheet['associations']['source_records']}
    for join in request['injective_tip_join']:
        common._subject(join['subject'], members, sources, sheet['associations']['feature_genomes'])
    pid = request['comparison_id']; methods = {'matched_tips': ('tips', 'explicit_matched_tip_count'), 'gene_splits': ('splits', 'restricted_gene_nontrivial_unrooted_splits'), 'organismal_splits': ('splits', 'restricted_organismal_nontrivial_unrooted_splits'), 'shared_splits': ('splits', 'shared_nontrivial_unrooted_splits'), 'rf': ('splits', 'unrooted_robinson_foulds'), 'rf_fraction': ('fraction', 'unrooted_robinson_foulds_fraction')}
    for key, (unit, method) in methods.items():
        _quantity(value[key], population=pid, unit=unit, method=method)
    split_sets = {}
    for axis in ('gene', 'organismal'):
        tree = lookup_tree(sheet, request[axis + '_tree_id']); require(tree is not None, 'comparison_tree_unknown')
        selected = [r[axis + '_node_index'] for r in request['injective_tip_join']]
        tips = [n['node_index'] for n in tree['nodes'] if not n['child_indices']]
        require(set(selected) <= set(tips), 'comparison_tip_unknown')
        require(value['omitted_' + axis + '_tips'] == [{'tree_id': tree['tree_id'], 'node_index': i} for i in tips if i not in selected], 'comparison_omitted_population_conflict')
        split_sets[axis] = common.unique(value['restricted_' + axis + '_splits'], 'split_id')
        for row in split_sets[axis].values():
            _split(row, tree=tree, selected=selected, prefix=pid + '/' + axis)
    common.unique(value['shared_split_pairs'], lambda r: (r['gene_split_id'], r['organismal_split_id']))
    for row in value['shared_split_pairs']:
        shape(row, {'gene_split_id', 'organismal_split_id'}); require(row['gene_split_id'] in split_sets['gene'] and row['organismal_split_id'] in split_sets['organismal'], 'shared_split_unknown')
    for field, count in (('matched_tips', len(request['injective_tip_join'])), ('gene_splits', len(split_sets['gene'])), ('organismal_splits', len(split_sets['organismal'])), ('shared_splits', len(value['shared_split_pairs']))):
        require(value[field]['value'] == count, 'comparison_count_conflict')


def _saved_cell(cell, *, population, method, unit, requirements, count=False, fraction=False):
    """Validate stored numerical meaning, without evaluating its formula."""
    validate_numeric_cell(cell)
    require(cell['population_id'] == population and cell['method_id'] == method and cell['unit'] == unit
        and cell['origin'] == 'calculated' and cell['uncertainty'] is None, 'saved_cell_meaning_conflict')
    require(set(cell['requirement_ids']) <= requirements, 'saved_cell_requirement_unknown')
    if count:
        common.integer(cell['value'], nullable=True)
    if fraction:
        common.integer(cell['numerator'], nullable=True); common.integer(cell['denominator'], nullable=True)
        if cell['value'] is not None:
            require(0 <= cell['value'] <= 1 and cell['numerator'] is not None and cell['denominator'] is not None
                and 0 <= cell['numerator'] <= cell['denominator'] and cell['denominator'] > 0, 'saved_fraction_operands_invalid')
    else:
        require(cell['numerator'] is None, 'saved_numerator_invalid')
        if count:
            require(cell['denominator'] is None, 'saved_count_denominator_invalid')
    if unit == 'bits' and cell['value'] is not None:
        require(cell['value'] >= 0, 'saved_entropy_invalid')


def _saved_msa_result(value, kind):
    """Check saved records; entropy, rounding and reference tallies stay saved."""
    fields = {'status','analysis_id','population_id','alignment_id','method_parameters','requirements','diagnostics'}
    shape(value, fields | ({'sites'} if kind == 'msa_entropy' else {'reference','differences','counts'}))
    ids = native._metadata(value); pid = value['population_id']; params = value['method_parameters']
    shape(params, {'alphabet','case_policy','terminal_gap','native_rounding'} if kind == 'msa_entropy' else {'alphabet','case_policy'})
    if kind == 'msa_entropy':
        common.array(value['sites']); common.unique(value['sites'],'column_0based')
        for site in value['sites']:
            shape(site, {'column_0based','included_row_indices','excluded_terminal_row_indices','symbol_counts','eligible_count',
                'internal_gap_count','terminal_gap_excluded_count','literal_entropy_bits','native_score_recalculated','score_residual',
                'strict_majority_consensus','native_observation_ids'})
            common.integer(site['column_0based']); common.indices(site['included_row_indices']); common.indices(site['excluded_terminal_row_indices'])
            require(not set(site['included_row_indices']) & set(site['excluded_terminal_row_indices']), 'terminal_inclusion_conflict')
            symbols = common.unique(site['symbol_counts'],'symbol')
            for symbol,row in symbols.items():
                shape(row,{'symbol','count'}); require(type(symbol) is str and len(symbol)==1 and symbol==symbol.upper(),'literal_symbol_invalid'); common.integer(row['count'],minimum=1)
            for field in ('eligible_count','internal_gap_count','terminal_gap_excluded_count'):
                _saved_cell(site[field],population=pid,method='msa_'+field+'_v1',unit='characters',requirements=ids,count=True)
            require(len({site[f]['state'] for f in ('eligible_count','internal_gap_count','terminal_gap_excluded_count')})==1,'site_count_states_conflict')
            entropy,score,residual=site['literal_entropy_bits'],site['native_score_recalculated'],site['score_residual']
            for cell,method,unit in ((entropy,native.ENTROPY_METHOD,'bits'),(score,native.ROUNDING_METHOD,'hundredths_of_bit'),(residual,native.RESIDUAL_METHOD,'hundredths_of_bit')):
                _saved_cell(cell,population=pid,method=method,unit=unit,requirements=ids)
            require(score['denominator'] is None and residual['denominator'] is None,'score_denominator_invalid')
            if params['native_rounding'] is None:
                require(score['value'] is None and score['state']=='not_measured','rounding_not_requested_conflict')
            if score['value'] is not None:
                require(params['native_rounding']==native.ROUNDING and entropy['value'] is not None and score['value']>=0,'score_operands_missing')
            if entropy['value'] is not None:
                require(site['eligible_count']['value'] is not None and entropy['denominator']==site['eligible_count']['value'] and entropy['denominator']>0,'entropy_denominator_conflict')
            if site['eligible_count']['state']=='available':
                require((entropy['value'] is not None)==(site['eligible_count']['value']>0) and entropy['denominator']==site['eligible_count']['value'],'entropy_availability_conflict')
            common.strings(site['native_observation_ids'])
            if residual['value'] is not None:
                require(score['value'] is not None and len(site['native_observation_ids'])==1,'residual_operands_missing')
            consensus=site['strict_majority_consensus']
            require(consensus is None or type(consensus) is str and len(consensus)==1 and consensus==consensus.upper(),'consensus_symbol_invalid')
            require((consensus is not None)==(site['eligible_count']['state']=='available' and site['eligible_count']['value']>0),'consensus_availability_conflict')
        return
    native._validate_reference(value['reference']); common.array(value['differences']); common.array(value['counts'])
    common.unique(value['differences'],lambda row:(row['row_index'],row['column_0based']))
    repeated={}
    for row in value['differences']:
        shape(row, {'row_index','column_0based','member_character','reference_character','category','member_ungapped_position_0based',
            'reference_ungapped_position_0based','member_original_correspondence','reference_original_correspondence'})
        common.integer(row['row_index']); common.integer(row['column_0based']); require(row['category'] in native.CATEGORIES,'difference_category_invalid')
        for axis,index in (('member',row['row_index']),('reference',value['reference']['row_index'])):
            char=row[axis+'_character']; require(type(char) is str and len(char)==1,'difference_character_invalid')
            position=row[axis+'_ungapped_position_0based']; common.integer(position,nullable=True)
            require((position is None)==(char=='-'),'gap_coordinate_conflict')
            mapping=row[axis+'_original_correspondence']; key=index,row['column_0based']; saved=(char,position,mapping)
            require(key not in repeated or repeated[key]==saved,'repeated_coordinate_conflict'); repeated[key]=saved
            if mapping is not None:
                native._validate_correspondence(mapping)
                require(mapping['alignment_id']==value['alignment_id'] and mapping['row_index']==index and mapping['column_0based']==row['column_0based']
                    and mapping['staged_ungapped_position_0based'] in (None,position),'reference_correspondence_conflict')
    common.unique(value['counts'],lambda row:(row['row_index'],row['category']))
    for row in value['counts']:
        shape(row,{'row_index','category','count'}); common.integer(row['row_index']); require(row['category'] in native.CATEGORIES,'reference_category_invalid')
        _saved_cell(row['count'],population=pid,method=native.REFERENCE_METHOD,unit='columns',requirements=ids,count=True)


def _saved_xmfa_cell(cell, field, unit, population, ids, *, prefix='xmfa_', fraction=False):
    _saved_cell(cell,population=population,method=prefix+field+'_v1',unit=unit,requirements=ids,count=unit not in ('bits','fraction'),fraction=fraction)
    if not fraction:
        require(cell['denominator'] is None,'xmfa_cell_denominator_invalid')


def _saved_xmfa_alignment(value):
    ids=xmfa._envelope(value,{'schema_version','document_id','status','selection','parameters','blocks','requirements','diagnostics'})
    require(value['schema_version']=='mauve_xmfa_alignment_components_v1','xmfa_result_version_invalid')
    selection=xmfa.validate_xmfa_selection(value['selection']); pid=selection['population_id']; members=selection['member_numbers']
    require(selection['document_id']==value['document_id'],'xmfa_selection_document_conflict')
    shape(value['parameters'],{'case_policy','selected_pairs'}); _pairs(value['parameters']['selected_pairs'],minimum=1,distinct=True,unordered=True)
    require(value['parameters']['case_policy'] in ('preserve','uppercase'),'xmfa_case_policy_invalid')
    require(len(value['blocks'])==len(selection['block_columns']),'xmfa_block_population_conflict')
    for block,chosen in zip(value['blocks'],selection['block_columns']):
        shape(block,{'block_index','present_members','zero_members','omitted_members','conflicting_members','record_refs','selected_column_count',
            'present_member_count','zero_member_count','omitted_member_count','sites','pairs'})
        require(block['block_index']==chosen['block_index'],'xmfa_block_population_conflict'); seen=set()
        for field in ('present_members','zero_members','omitted_members','conflicting_members'):
            common.indices(block[field]); require(set(block[field])<=set(members) and not seen.intersection(block[field]),'xmfa_member_population_conflict'); seen.update(block[field])
        refs=[xmfa.ref(row) for row in block['record_refs']]; require(len(set(refs))==len(refs) and all(r[0]==block['block_index'] for r in refs),'xmfa_record_reference_conflict')
        for field in ('selected_column_count','present_member_count','zero_member_count','omitted_member_count'):
            _saved_xmfa_cell(block[field],field,'columns' if field=='selected_column_count' else 'members',pid,ids)
        member_state=block['present_member_count']['state']
        require(block['selected_column_count']['state']=='available' and all(block[f]['state']==member_state for f in ('zero_member_count','omitted_member_count')),'xmfa_population_state_conflict')
        require(not block['conflicting_members'] or member_state=='incompatible','xmfa_population_state_conflict')
        require([r['column_0based'] for r in block['sites']]==chosen['columns_0based'],'xmfa_site_population_conflict')
        for site in block['sites']:
            shape(site,{'column_0based','symbol_counts',*xmfa.SITE_COUNTS,'literal_entropy_bits','canonical_entropy_bits','canonical_majority_fraction'})
            symbols=common.unique(site['symbol_counts'],'symbol')
            for symbol,row in symbols.items():
                shape(row,{'symbol','count'}); require(type(symbol) is str and len(symbol)==1,'xmfa_symbol_invalid')
                require(value['parameters']['case_policy']!='uppercase' or symbol==symbol.upper(),'xmfa_symbol_case_conflict')
                _saved_xmfa_cell(row['count'],'symbol_count','characters',pid,ids)
            for field in xmfa.SITE_COUNTS:
                _saved_xmfa_cell(site[field],field,'members' if 'member' in field else 'characters',pid,ids)
                require(site[field]['state']==member_state,'xmfa_population_state_conflict')
            require(all(r['count']['state']==member_state for r in site['symbol_counts']),'xmfa_population_state_conflict')
            for field in ('literal_entropy_bits','canonical_entropy_bits'):
                _saved_xmfa_cell(site[field],field,'bits',pid,ids)
            _saved_xmfa_cell(site['canonical_majority_fraction'],'canonical_majority_fraction','fraction',pid,ids,fraction=True)
            if member_state!='available':
                require(all(site[f]['state']==member_state for f in ('literal_entropy_bits','canonical_entropy_bits','canonical_majority_fraction')),'xmfa_population_state_conflict')
        require([[r['member_a'],r['member_b']] for r in block['pairs']]==value['parameters']['selected_pairs'],'xmfa_pair_population_conflict')
        for pair in block['pairs']:
            shape(pair,{'member_a','member_b','state',*xmfa.PAIR_COUNTS,'identity_fraction'})
            require(pair['state'] in ('available','not_coobserved','incompatible','incomplete'),'xmfa_pair_state_invalid')
            for field in xmfa.PAIR_COUNTS:
                _saved_xmfa_cell(pair[field],field,'columns',pid,ids)
            _saved_xmfa_cell(pair['identity_fraction'],'identity_fraction','fraction',pid,ids,fraction=True)
            if pair['state']!='available':
                state={'incompatible':'incompatible','incomplete':'truncated','not_coobserved':'not_measured'}[pair['state']]
                require(all(pair[field]['state']==state for field in (*xmfa.PAIR_COUNTS,'identity_fraction')),'xmfa_pair_availability_conflict')


def _saved_intervals(rows):
    common.array(rows); previous=None
    for row in rows:
        common.interval(row); require(row[0]<row[1] and (previous is None or previous<row[0]),'saved_interval_order_conflict'); previous=row[1]


def _saved_xmfa_coverage(value):
    ids=xmfa._envelope(value,{'schema_version','document_id','status','selection','parameters','members','requirements','diagnostics'})
    require(value['schema_version']=='mauve_xmfa_coverage_components_v1','xmfa_result_version_invalid')
    selection=xmfa.validate_xmfa_selection(value['selection']); pid=selection['population_id']
    require(selection['document_id']==value['document_id'],'xmfa_selection_document_conflict')
    shape(value['parameters'],{'basis'}); require(value['parameters']['basis'] in xmfa.BASES,'xmfa_coverage_basis_invalid')
    prefix='xmfa_'+value['parameters']['basis']+'_'; blocks={b['block_index'] for b in selection['block_columns']}
    require([r['member_number'] for r in value['members']]==selection['member_numbers'],'xmfa_member_population_conflict')
    for member in value['members']:
        shape(member,{'member_number','source_length','placements','known_union_intervals','known_union_bases','placement_bases',
            'multiply_represented_bases','excess_placement_bases','selected_coverage_fraction','complement_intervals','complement_bases','membership_completeness','original_coverage'})
        require(member['membership_completeness'] in xmfa.COMPLETENESS,'xmfa_completeness_invalid'); common.array(member['placements'])
        for placement in member['placements']:
            shape(placement,{'record','interval_0based_half_open','strand'}); key=xmfa.ref(placement['record'])
            require(key[0] in blocks and placement['strand'] in ('+','-'),'xmfa_placement_identity_invalid'); common.interval(placement['interval_0based_half_open'])
        _saved_intervals(member['known_union_intervals'])
        for field in ('source_length','known_union_bases','placement_bases','multiply_represented_bases','excess_placement_bases','complement_bases'):
            _saved_xmfa_cell(member[field],field,'nucleotide_placements' if field in ('placement_bases','excess_placement_bases') else 'nucleotides',pid,ids,prefix=prefix)
        _saved_xmfa_cell(member['selected_coverage_fraction'],'selected_coverage_fraction','fraction',pid,ids,prefix=prefix,fraction=True)
        if member['complement_intervals'] is not None:
            _saved_intervals(member['complement_intervals']); require(member['source_length']['value'] is not None and member['membership_completeness']=='complete','xmfa_complement_dependency_missing')
            require(all(end<=member['source_length']['value'] for _,end in member['known_union_intervals']+member['complement_intervals']),'xmfa_interval_outside_source')
        else:
            require(member['complement_bases']['value'] is None and member['selected_coverage_fraction']['state']!='available','xmfa_complement_availability_conflict')
        if member['selected_coverage_fraction']['state']=='available':
            require(member['membership_completeness']=='complete' and member['selected_coverage_fraction']['numerator']==member['known_union_bases']['value']
                and member['selected_coverage_fraction']['denominator']==member['source_length']['value'],'xmfa_coverage_operands_conflict')
        common.unique(member['original_coverage'],lambda row:common.member_key(row['original_member']))
        for original in member['original_coverage']:
            shape(original,{'original_member','original_length','known_union_intervals','known_union_bases','coverage_fraction','mapping_completeness','evidence'})
            require(original['mapping_completeness'] in xmfa.COMPLETENESS,'xmfa_completeness_invalid'); common.evidence(original['evidence']); _saved_intervals(original['known_union_intervals'])
            for field in ('original_length','known_union_bases'):
                _saved_xmfa_cell(original[field],field,'nucleotides',pid,ids,prefix=prefix+'original_')
            _saved_xmfa_cell(original['coverage_fraction'],'coverage_fraction','fraction',pid,ids,prefix=prefix+'original_',fraction=True)
            length=original['original_length']['value']; require(length is None or all(end<=length for _,end in original['known_union_intervals']),'xmfa_original_interval_outside_source')
            if original['coverage_fraction']['state']=='available':
                require(original['mapping_completeness']==member['membership_completeness']=='complete' and original['coverage_fraction']['numerator']==original['known_union_bases']['value']
                    and original['coverage_fraction']['denominator']==length,'xmfa_original_coverage_operands_conflict')


def _native_cell_relation(document, cell):
    common.shape(cell, {'block_index', 'record_index', 'column_0based'})
    for value in cell.values():
        common.integer(value)
    require(cell['block_index'] < len(document['blocks']), 'xmfa_cell_block_unknown')
    block = document['blocks'][cell['block_index']]
    require(cell['record_index'] < len(block['records']), 'xmfa_cell_record_unknown')
    record = block['records'][cell['record_index']]; column = cell['column_0based']
    require(column < len(record['sequence']), 'xmfa_cell_column_unknown')
    position = None
    if record['coordinate_state'] == 'present' and record['sequence'][column] != '-':
        preceding = sum(symbol != '-' for symbol in record['sequence'][:column])
        start, end = record['interval_0based_half_open']
        position = start + preceding if record['strand'] == '+' else end - 1 - preceding
    return record, position


def _xmfa_coordinate_source(row, record, position, binding):
    require(row['native_position_0based'] == position and row['native_strand'] == record['strand'], 'xmfa_native_coordinate_conflict')
    if row['source_coordinate'] is None:
        return
    require(binding is not None and binding['bindings'] is not None, 'xmfa_source_binding_missing')
    bindings = binding['bindings']; sc = row['source_coordinate']
    member = next((m for m in bindings['members'] if m['member_number'] == row['member_number']), None)
    check = next((v for v in bindings['source_checks'] if v['record'] == {k:row['cell'][k] for k in ('block_index','record_index')}), None)
    require(member is not None and member['state'] == 'resolved' and check is not None and check['state'] == 'match', 'xmfa_coordinate_source_unverified')
    candidates = [v for v in member['components'] if v['file_id'] == sc['file_id'] and v['record_id'] == sc['record_id'] and v['entry_1based'] == sc['entry_1based'] and v['member_interval_0based_half_open'][0] <= position < v['member_interval_0based_half_open'][1]]
    require(len(candidates) == 1 and sc['position_0based'] == position - candidates[0]['member_interval_0based_half_open'][0], 'xmfa_source_coordinate_conflict')
    for original in row['original_coordinates']:
        maps = [m for m in bindings['original_maps'] if m['file_id'] == sc['file_id'] and m['record_id'] == sc['record_id'] and m['original_member'] == original['original_member'] and m['transformation_id'] == original['transformation_id'] and m['original_length'] == original['original_length'] and m['staged_interval_0based_half_open'][0] <= sc['position_0based'] < m['staged_interval_0based_half_open'][1]]
        require(bool(maps), 'xmfa_original_coordinate_unknown')
        for mapping in maps:
            offset = sc['position_0based'] - mapping['staged_interval_0based_half_open'][0]
            expected = mapping['original_interval_0based_half_open'][0] + offset if mapping['strand'] == '+' else mapping['original_interval_0based_half_open'][1] - 1 - offset
            require(original['position_0based'] == expected and original['strand'] == ('+' if mapping['strand'] == sc['strand'] else '-') and original['evidence'] == mapping['evidence'], 'xmfa_original_coordinate_conflict')


def _xmfa_result(value, request, sheet):
    kind = request['kind']; require(sheet['analysis']['mode'] == 'mauve_blocks', 'xmfa_analysis_mode_conflict')
    doc = lookup_document(sheet, request['document_id'], 'xmfa'); require(doc is not None, 'xmfa_document_unknown')
    validators = {'xmfa_column_coordinates': xmfa.validate_xmfa_coordinates, 'xmfa_source_positions': xmfa.validate_xmfa_inverse_coordinates,
        'xmfa_alignment_components': _saved_xmfa_alignment, 'xmfa_interval_coverage': _saved_xmfa_coverage}
    validators[kind](value); require(value['document_id'] == request['document_id'], 'xmfa_document_conflict')
    binding = next((b for b in sheet['xmfa_bindings'] if b['document_id'] == request['document_id']), None) if request.get('use_source_bindings') else None
    if 'selection' in request:
        require(value['selection'] == request['selection'], 'xmfa_selection_conflict')
        for chosen in request['selection']['block_columns']:
            require(chosen['block_index']<len(doc['blocks']),'xmfa_selection_block_unknown')
            block=doc['blocks'][chosen['block_index']]; bound=max((len(r['sequence']) for r in block['records']),default=0)
            require(all(i<bound for i in chosen['columns_0based']),'xmfa_selection_column_unknown')
        expected = {k: request[k] for k in ('case_policy', 'selected_pairs')} if kind == 'xmfa_alignment_components' else {'basis': request['basis']}
        require(value['parameters'] == expected, 'xmfa_parameters_conflict')
        if kind == 'xmfa_alignment_components':
            for block in value['blocks']:
                records=doc['blocks'][block['block_index']]['records']
                for ref in block['record_refs']:
                    require(ref['record_index']<len(records) and records[ref['record_index']]['member_number']['value'] in request['selection']['member_numbers'],'xmfa_record_reference_conflict')
        if kind == 'xmfa_interval_coverage':
            source_members = {} if binding is None or binding['bindings'] is None else {m['member_number']:m for m in binding['bindings']['members']}
            original_members = {common.member_key(m['key']):m for m in sheet['associations']['original_members']}
            for row in value['members']:
                member = source_members.get(row['member_number'])
                require(row['source_length']['value'] == (member['source_length'] if member else None), 'xmfa_source_length_conflict')
                for placement in row['placements']:
                    ref = placement['record']; require(ref['block_index'] < len(doc['blocks']), 'xmfa_placement_block_unknown')
                    records = doc['blocks'][ref['block_index']]['records']; require(ref['record_index'] < len(records), 'xmfa_placement_record_unknown')
                    record = records[ref['record_index']]; interval = placement['interval_0based_half_open']
                    require(record['coordinate_state'] == 'present' and record['member_number']['value'] == row['member_number'] and placement['strand'] == record['strand'] and record['interval_0based_half_open'][0] <= interval[0] < interval[1] <= record['interval_0based_half_open'][1], 'xmfa_placement_source_conflict')
                for original in row['original_coverage']:
                    key = common.member_key(original['original_member']); require(key in original_members, 'xmfa_original_member_unknown')
                    require(original['original_length']['value'] in (None, original_members[key]['original_length']), 'xmfa_original_length_conflict')

    elif kind == 'xmfa_column_coordinates':
        require([r['cell'] for r in value['cells']] == request['cells'], 'xmfa_requested_cells_conflict')
        blocks = {b['block_index']: b for b in doc['blocks']}
        for row in value['cells']:
            ref = row['cell']; require(ref['block_index'] in blocks, 'xmfa_cell_block_unknown')
            records = {r['record_index']: r for r in blocks[ref['block_index']]['records']}
            require(ref['record_index'] in records, 'xmfa_cell_record_unknown'); record = records[ref['record_index']]
            require(ref['column_0based'] < len(record['sequence']) and row['aligned_symbol'] == record['sequence'][ref['column_0based']] and row['member_number'] == (record['member_number']['value'] if record['member_number']['state'] == 'available' and record['member_number']['value'] > 0 else None), 'xmfa_cell_source_conflict')
            _, position = _native_cell_relation(doc, ref)
            _xmfa_coordinate_source(row, record, position, binding)
            if not request['use_source_bindings']:
                require(row['source_coordinate'] is None and not row['original_coordinates'], 'xmfa_unrequested_source_claim')
    else:
        require([{k:r[k] for k in ('member_number', 'position_0based')} for r in value['queries']] == request['queries'], 'xmfa_requested_queries_conflict')
        for row in value['queries']:
            require(row['search_completeness'] == doc['completeness'], 'xmfa_inverse_completeness_conflict')
            for cell in row['matches']:
                record, position = _native_cell_relation(doc, cell)
                require(record['member_number']['state'] == 'available' and record['member_number']['value'] == row['member_number'] and position == row['position_0based'], 'xmfa_inverse_source_conflict')


def _result_requirements(value):
    """Inspect saved cells only. Do not call calculation_requirements here."""
    emitted = set(); stack = [value]
    while stack:
        node = stack.pop()
        if type(node) is dict:
            if 'requirement_ids' in node:
                common.strings(node['requirement_ids']); emitted.update(node['requirement_ids'])
            stack.extend(node.values())
        elif type(node) is list:
            stack.extend(node)
    return emitted


@closed
def validate_msa_components(components: dict, *, sheet: dict) -> dict:
    sheet = validate_msa_sheet(sheet)
    shape(components, {'schema_version', 'analysis_id', 'parameters', 'results', 'requirements', 'diagnostics'})
    require(components['schema_version'] == VERSION and components['analysis_id'] == sheet['analysis']['analysis_id'], 'components_identity_conflict')
    parameters = validate_msa_parameters(components['parameters']); common.reports(components)
    common.array(components['results']); require(len(components['results']) == len(parameters['requests']), 'result_population_conflict')
    for outcome, request in zip(components['results'], parameters['requests']):
        shape(outcome, {'request_id', 'kind', 'status', 'value', 'requirements', 'diagnostics'}); common.reports(outcome)
        require(outcome['request_id'] == request['request_id'] and outcome['kind'] == request['kind'] and outcome['status'] in ('ok', 'partial', 'invalid'), 'result_request_conflict')
        value, kind = outcome['value'], request['kind']
        if value is None:
            require(outcome['status'] != 'ok' and outcome['requirements'], 'null_result_unqualified'); continue
        require(outcome['status'] != 'invalid', 'invalid_result_has_value')
        if kind in COMMON_KINDS:
            _shared_result(value, request, sheet)
        elif kind == 'tree':
            _tree_result(value, request, sheet)
        elif kind == 'relationship_comparison':
            _relationship_result(value, request, sheet)
        elif kind.startswith('xmfa_'):
            _xmfa_result(value, request, sheet)
        else:
            population = lookup_population(sheet, 'alignments', request['population_id']); require(population is not None, 'result_population_unknown')
            _saved_msa_result(value,kind)
            require(value['analysis_id'] == components['analysis_id'] and value['population_id'] == population['population_id'] and value['alignment_id'] == population['alignment_id'], 'native_result_identity_conflict')
            method_keys = ('alphabet', 'case_policy', 'terminal_gap', 'native_rounding') if kind == 'msa_entropy' else ('alphabet', 'case_policy')
            require(value['method_parameters'] == {k: request[k] for k in method_keys}, 'native_result_parameters_conflict')
            if kind == 'msa_entropy':
                require([r['column_0based'] for r in value['sites']] == population['columns_0based'], 'entropy_column_conflict')
                observations = {r['observation_id']: r for r in sheet['native_observations']}
                table=lookup_document(sheet,request['observed_table_id'],'msa_frequency')
                for row in value['sites']:
                    require(set(row['included_row_indices'] + row['excluded_terminal_row_indices']) <= set(population['row_indices']), 'entropy_row_population_conflict')
                    require(all(i in observations and observations[i]['document_id'] == request['observed_table_id'] and observations[i]['field']=='msa_score' for i in row['native_observation_ids']), 'entropy_observation_conflict')
                    expected=[] if table is None else [table['table_id']+'/rows/'+str(r['row_index'])+'/score' for r in table['rows'] if r['alignment_position']['state']=='available' and r['alignment_position']['value']==row['column_0based']+1]
                    require(row['native_observation_ids']==expected,'entropy_observation_coordinate_conflict')
                    if row['score_residual']['value'] is not None:
                        obs = observations[row['native_observation_ids'][0]]['number']; require(obs['state'] == 'available' and row['native_score_recalculated']['value'] is not None, 'entropy_residual_source_conflict')
            else:
                require(value['reference'] == effective_reference(sheet, request['reference']), 'reference_request_conflict')
                require([(r['row_index'],r['category']) for r in value['counts']] == [(i,category) for i in request['member_row_indices'] for category in native.CATEGORIES], 'reference_member_population_conflict')
                alignment = lookup_alignment(sheet, population['alignment_id'])
                expected = [(i,j) for i in request['member_row_indices'] for j in population['columns_0based'] if j < len(alignment['rows'][i]['sequence']) and j < len(alignment['rows'][request['reference']['row_index']]['sequence'])]
                require([(r['row_index'],r['column_0based']) for r in value['differences']] == expected, 'reference_site_population_conflict')
                for row in value['differences']:
                    for axis, index in (('member',row['row_index']),('reference',request['reference']['row_index'])):
                        token = alignment['rows'][index]['sequence'][row['column_0based']]
                        require(row[axis+'_character'] == (token.upper() if request['case_policy']=='uppercase' else token), 'reference_character_source_conflict')
                        mapping = row[axis+'_original_correspondence']; require(mapping is None or mapping in sheet['associations']['correspondences'], 'reference_map_source_conflict')
        ids = {r['requirement_id'] for r in outcome['requirements']}
        require(_result_requirements(value) <= ids, 'result_requirement_missing')
        if type(value) is dict:
            require(all(r in outcome['requirements'] for r in value.get('requirements', value.get('missing_requirements', []))) and all(d in outcome['diagnostics'] for d in value.get('diagnostics', [])), 'result_reports_missing')
        require(outcome['status'] != 'ok' or not outcome['requirements'] and not outcome['diagnostics'], 'result_status_conflict')
    require(components['requirements'] == merge_reports(*(r['requirements'] for r in components['results'])) and components['diagnostics'] == merge_reports(*(r['diagnostics'] for r in components['results'])), 'components_reports_conflict')
    return deepcopy(components)


__all__ = ['validate_msa_sheet', 'validate_msa_parameters', 'validate_msa_components']
