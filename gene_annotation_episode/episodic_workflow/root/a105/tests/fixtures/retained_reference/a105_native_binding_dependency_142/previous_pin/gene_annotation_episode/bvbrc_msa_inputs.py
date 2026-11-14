"""Extract MSA native measurements and associations from supplied saved documents.

No native analysis, calculator, parser, file or service is invoked. Consensus
correspondence follows the retained frequency tokens, never a new majority vote.
"""
from copy import deepcopy
import math

from . import bvbrc_msa_provider_contracts as c
from . import bvbrc_alignment_provider_contracts as common
from .bvbrc_alignment_values import diagnostic
from .bvbrc_msa_format_contracts import PROTEIN_SYMBOLS


def _qualify(sheet, reason, role, *, kind='scientific_metadata'):
    row = c.need(sheet['analysis']['analysis_id'], role, reason, kind=kind)
    sheet['requirements'] = c.merge_reports(sheet['requirements'], [row])
    sheet['diagnostics'] = c.merge_reports(sheet['diagnostics'], [diagnostic(reason, path='/' + role)])


def _observations(sheet):
    result = []
    for document in sheet['documents']:
        if document['kind'] != 'msa_frequency':
            continue
        table = document['value']; population = c.native_population(sheet, table)
        for row, suffix, field, indices, unit, number in c.native_fields(table):
            result.append({'observation_id': table['table_id'] + '/rows/' + str(row['row_index']) + '/' + suffix,
                'document_id': table['table_id'], 'row_index': row['row_index'], 'field': field,
                'nested_indices': indices, 'number': deepcopy(number), 'unit': unit,
                'population_id': population, 'category_id': None, 'group_ids': [],
                'association_state': 'resolved' if population is not None else 'missing',
                'evidence': deepcopy(sheet['analysis']['output_role_evidence'])})
    return result


def _consensus(sheet):
    analysis = sheet['analysis']; consensus = c.lookup_alignment(sheet, analysis['consensus_alignment_id'])
    if consensus is None:
        return []
    alignment = c.lookup_alignment(sheet, analysis['alignment_id'])
    table = c.lookup_document(sheet, analysis['frequency_table_id'], 'msa_frequency')
    population_id = c.native_population(sheet, table) if table else None
    if population_id is None or alignment is None:
        _qualify(sheet, 'msa_consensus_correspondence_unresolved', 'consensus_associations')
        return []
    columns, symbol_string = [], None
    positions = {}
    if table is not None:
        for row in table['rows']:
            position = row['alignment_position']
            if position['state'] == 'available':
                positions.setdefault(position['value']-1, []).append(row)
        width = alignment['observed_column_count']
        if width is not None and len(table['rows']) == width and set(positions) == set(range(width)) and all(len(r) == 1 for r in positions.values()):
            symbols = [positions[i][0]['consensus_token'] if table['alphabet'] == 'dna' else PROTEIN_SYMBOLS.get(positions[i][0]['consensus_token']) for i in range(width)]
            if all(type(s) is str and len(s) == 1 for s in symbols):
                offset = 0
                for index, symbol in enumerate(symbols):
                    columns.append({'source_column_0based': index, 'consensus_position_0based': None if symbol == '-' else offset, 'symbol': symbol})
                    offset += symbol != '-'
                symbol_string = ''.join(s for s in symbols if s != '-')
    result = []
    for row in consensus['rows']:
        resolved = symbol_string is not None and symbol_string == row['sequence']
        result.append({'consensus_alignment_id': consensus['alignment_id'], 'consensus_row_index': row['row_index'],
            'source_alignment_id': alignment['alignment_id'], 'source_population_id': population_id,
            'frequency_table_id': table['table_id'] if table else None,
            'columns': deepcopy(columns) if resolved else [],
            'method': 'native_table_consensus_then_remove_dash' if resolved else 'unresolved',
            'state': 'resolved' if resolved else 'conflicting' if symbol_string is not None else 'missing',
            'evidence': deepcopy(analysis['output_role_evidence'])})
        if not resolved:
            _qualify(sheet, 'msa_consensus_correspondence_unresolved', 'consensus_associations')
    return result


def _trees(sheet):
    observations, supports = [], []
    bindings = {r['tree_id']: r for r in sheet['tree_bindings']}
    for document in sheet['documents']:
        if document['kind'] != 'tree':
            continue
        for tree in document['value']['trees']:
            tid = tree['tree_id']; binding = bindings.get(tid)
            branch_unit, support_method, scale = c.effective_tree_semantics(sheet, binding)
            evidence = deepcopy(binding['evidence'] if binding else sheet['analysis']['output_role_evidence'])
            for node in tree['nodes']:
                subject = tid + '/node/' + str(node['node_index'])
                def record(field, value, token, unit, method):
                    obs = {'observation_id': subject + '/' + field, 'field': field, 'value': value,
                        'raw_token': token, 'state': 'available' if value is not None else 'failed', 'unit': unit,
                        'population_id': tid, 'subject_id': subject, 'method': method,
                        'location': deepcopy(node['source_location']), 'evidence': deepcopy(evidence),
                        'uncertainty': None, 'requirement_ids': []}
                    observations.append(obs)
                    return obs
                if node['branch_length_token'] is not None:
                    record('branch_length', node['branch_length'], node['branch_length_token'], branch_unit, 'native_branch_length')
                if node['parent_index'] is None or not node['child_indices'] or node['decoded_label'] is None:
                    continue
                if not c.numeric_label(node['decoded_label']):
                    continue
                value = c._native_number(node['decoded_label'])
                obs = record('branch_support_native', value, node['label_token'],
                    {'fraction': 'fraction', 'percent': 'percent', 'statistic': 'native_statistic', 'native_unknown': 'native_unknown'}[scale], support_method)
                supports.append({'tree_id': tid, 'node_index': node['node_index'], 'native_observation_id': obs['observation_id'],
                    'source_kind': 'internal_label', 'method': support_method, 'scale': scale,
                    'command_id': binding['command_id'] if binding else None, 'bootstrap_population_id': None, 'evidence': deepcopy(evidence)})
    return observations, supports


def extract_msa_sheet(*, analysis: dict, inputs: tuple[dict, ...], documents: tuple[dict, ...],
        read_outcomes: tuple[dict, ...], run: dict, associations: dict, populations: dict,
        segments: tuple[dict, ...], tree_bindings: tuple[dict, ...], parameters: dict,
        xmfa_bindings: tuple[dict, ...] = ()) -> dict:
    """Retain every usable native record; qualify missing independent evidence."""
    try:
        c.shape(parameters, {'source_dialect'}); c.require(parameters['source_dialect'] == 'retained_bvbrc_msa', 'source_dialect_invalid')
        for rows in (inputs, documents, read_outcomes, segments, tree_bindings, xmfa_bindings):
            c.require(type(rows) in (tuple, list), 'array_invalid')
        docs, alignments, trees = common.document_maps(documents)
        common.validate_association_set(associations, inputs=inputs, documents=documents)
        common.validate_populations(populations, documents=documents, associations=associations)
        common.validate_run_record(run)
        sheet = {'schema_version': 'bvbrc_msa_sheet_v1', 'tool': 'C-L204-MSA', 'analysis': deepcopy(analysis),
            'inputs': deepcopy(list(inputs)), 'run': deepcopy(run), 'documents': deepcopy(list(documents)),
            'read_outcomes': deepcopy(list(read_outcomes)), 'associations': deepcopy(associations),
            'populations': deepcopy(populations), 'segments': deepcopy(list(segments)),
            'tree_bindings': deepcopy(list(tree_bindings)), 'consensus_associations': [],
            'native_observations': [], 'native_tree_measurements': [], 'support_observations': [],
            'xmfa_bindings': deepcopy(list(xmfa_bindings)),
            'requirements': c.merge_reports(associations['requirements'], *(b['requirements'] for b in xmfa_bindings)),
            'diagnostics': c.merge_reports(associations['diagnostics'], *(r['diagnostics'] for r in read_outcomes), *(b['diagnostics'] for b in xmfa_bindings))}
        reference = sheet['analysis']['reference']
        if reference is not None and reference['native_ref_type'] == 'string' and not c.reference_identity_proven(sheet, reference):
            reference['identity_state'] = 'unresolved'
            _qualify(sheet, 'msa_reference_unresolved', 'reference')
        analysis = sheet['analysis']
        c.validate_analysis(analysis, sheet, docs, alignments, trees)
        c._segments(sheet, alignments); c._tree_bindings(sheet, alignments, trees)
        if analysis['alignment_id'] is None and analysis['mode'] != 'mauve_blocks':
            _qualify(sheet, 'alignment_document_unavailable', 'alignment', kind='output_bytes')
        if analysis['mode'] == 'ordinary_prealigned' and not any(s['name'] == 'prealigned_bypass' and s['value'] is True and s['origin'] == 'observed' and s['evidence'] for s in run['settings']):
            _qualify(sheet, 'msa_prealigned_definition_mismatch', 'prealigned_bypass', kind='definition')
        if analysis['mode'] in ('segment_alignment', 'segment_concatenation') and (not segments or any(s['state'] != 'resolved' for s in segments)):
            _qualify(sheet, 'msa_segment_membership_unresolved', 'segments')
        if analysis['mode'] == 'mauve_first_block_projection' and not any(t['kind'] == 'mauve_first_block_projection' and t['xmfa_slot_id'] == analysis['full_xmfa_slot_id'] and any(r['alignment_id'] == analysis['alignment_id'] for r in t['output_rows']) for t in associations['transformations']):
            _qualify(sheet, 'alignment_transformation_unproven', 'mauve_first_block_projection')
        if analysis['mode'] == 'mauve_blocks' and analysis['xmfa_document_id'] is None:
            _qualify(sheet, 'msa_full_xmfa_binding_required', 'full_xmfa', kind='output_bytes')
        if analysis['reference'] is not None and analysis['reference']['identity_state'] != 'resolved':
            _qualify(sheet, 'msa_reference_unresolved', 'reference')
        if not any(v['origin'] == 'observed' and v['component'] == 'app_msa' and v['version'] is not None and v['evidence'] for v in run['versions']):
            _qualify(sheet, 'alignment_deployed_version_unproven', 'run')
        sheet['native_observations'] = _observations(sheet)
        sheet['consensus_associations'] = _consensus(sheet)
        sheet['native_tree_measurements'], sheet['support_observations'] = _trees(sheet)
        sheet = c.validate_msa_sheet(sheet)
        return {'status': 'partial' if sheet['requirements'] or sheet['diagnostics'] else 'ok', 'value': sheet, 'diagnostics': deepcopy(sheet['diagnostics'])}
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).replace('_', '').isalnum() else c.PREFIX + 'shape_invalid'
        return {'status': 'invalid', 'value': None, 'diagnostics': [diagnostic(code, severity='error')]}


__all__ = ['extract_msa_sheet']
