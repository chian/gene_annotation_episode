"""Closed RNA return shapes and exact projections of retained numerical cells.

Projection selects supplied data; it does not acquire, interpret or score science.
Failure ordinals are frozen before the selected action receipt is published.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.rna_structure_contracts import CELL_STATES, COORDINATE_SYSTEM, METRIC_UNITS, MODES, OPERATIONS, RNA_ISSUE_CODES, RNA_SYMBOLS, ROW_METRICS
FAMILY_METRICS = {'summary': ROW_METRICS['summary'], 'pair': ROW_METRICS['pairs'], 'stem': ROW_METRICS['stems'], 'region': ROW_METRICS['regions'], 'failure': ()}
FAMILY_SOURCES = {family: 'execution_rna_structure_' + family + '_rows' for family in FAMILY_METRICS}
REFERENCE_SOURCE = 'execution_rna_structure_result_refs'
SAVED_SOURCE = 'execution_rna_structure_saved_sheet_inputs'
IDENTIFIER_NAMESPACES = ('native_rna_structure_row', 'native_rna_structure_calculation', 'native_rna_structure_result_receipt')
TEXT = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000]+$'}
COUNT = {'type': 'integer', 'minimum': 0}
NUMBER = {'type': 'number'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}

def nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def reference(namespace):
    return {**TEXT, 'format': 'reference', 'x-reference-namespace': namespace}

def identifier(namespace):
    return {**TEXT, 'format': 'identifier', 'x-reference-namespace': namespace}
PARAMETERS_SCHEMA = obj({'schema': {'const': 'rna_calculation_parameters_v1'}, 'topology': obj({'long_stem_min_pairs': {'type': 'integer', 'minimum': 1}, 'include_exterior_in_loop_size_statistics': {'const': False}}), 'pair_composition': obj({'accepted_ordered_pair_types': {'type': 'array', 'uniqueItems': True, 'items': {'enum': [a + b for a in 'ACGU' for b in 'ACGU']}}, 'denominator': {'const': 'unambiguous_pairs'}}), 'energy': obj({'normalization': {'enum': ['none', 'per_nt']}})})
SAVED_INPUT_SCHEMA = obj({'schema': {'const': 'rna_structure_saved_sheet_input_v1'}, 'result_receipt_key': identifier(IDENTIFIER_NAMESPACES[2]), 'handoff_ref': reference('execution_handoff'), 'source_ref': reference('execution_result'), 'bundle_artifact_ref': reference('artifact'), 'sheet_artifact_ref': reference('artifact'), 'sheet_sha256': SHA, 'record_key': TEXT, 'operation': {'enum': list(OPERATIONS.values())}, 'mode': {'enum': list(MODES)}})
ISSUE_SCHEMA = obj({'stage': {'enum': ['input', 'native', 'capture', 'parse', 'calculate', 'binding', 'selection']}, 'code': {'enum': sorted(RNA_ISSUE_CODES)}, 'record_key': nullable(TEXT), 'field': nullable(TEXT), 'index': nullable(COUNT), 'artifact_role': nullable({'enum': ['input', 'model_parameter_input', 'native_result', 'model', 'effective_parameters', 'stdout', 'stderr']})})
PAIR_SCHEMA = {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': COUNT}
_ORIGINS = ['native_prediction', 'native_evaluation', 'derived_topology', 'derived_sequence_composition']

def rna_structure_row_schema(family):
    if family not in FAMILY_METRICS:
        raise ValueError('rna_invalid_input_schema')
    common = {'family': {'const': family}, 'record_key': TEXT, 'row_key': identifier(IDENTIFIER_NAMESPACES[0]), 'source_ref': reference('execution_result'), 'operation': {'enum': list(OPERATIONS.values())}, 'mode': {'enum': list(MODES)}}
    if family == 'failure':
        return obj({**common, 'source_ref': nullable(reference('execution_result')), 'result_receipt_key': identifier(IDENTIFIER_NAMESPACES[2]), 'issue_ordinal': COUNT, 'issue': ISSUE_SCHEMA})
    measurement = {'name': {'enum': list(FAMILY_METRICS[family])}, 'unit': {'enum': sorted(set(METRIC_UNITS.values()))}, 'numerator': nullable(NUMBER), 'denominator': nullable(NUMBER), 'origin': {'enum': _ORIGINS}}
    common.update({'structure_key': nullable(TEXT), 'subject_ref': nullable(reference('subject')), 'sequence_id': nullable(TEXT), 'structure_id': nullable(TEXT), 'structure_origin': nullable({'enum': ['native_prediction', 'supplied_unknown', 'supplied_prediction', 'supplied_observation']}), 'coordinate_system': {'const': COORDINATE_SYSTEM}, 'status': {'enum': ['bound', 'unbound', 'partial', 'invalid']}, 'measurements': {'type': 'array', 'items': obj({**measurement, 'value': NUMBER})}, 'unavailable': {'type': 'array', 'items': obj({**measurement, 'state': {'enum': sorted(CELL_STATES - {'present'})}, 'reason': {'enum': sorted(RNA_ISSUE_CODES)}})}, 'qualification_codes': {'type': 'array', 'uniqueItems': True, 'items': {'enum': sorted(RNA_ISSUE_CODES)}}, 'calculation_key': identifier(IDENTIFIER_NAMESPACES[1]), 'calculation_parameters': PARAMETERS_SCHEMA})
    if family == 'pair':
        symbol = {'type': 'string', 'pattern': '^[' + RNA_SYMBOLS + ']$'}
        common.update(pair_key=TEXT, indices=PAIR_SCHEMA, symbol_i=nullable(symbol), symbol_j=nullable(symbol), ordered_pair=nullable({'type': 'string', 'pattern': '^[' + RNA_SYMBOLS + ']{2}$'}))
    elif family == 'stem':
        common.update(stem_key=TEXT, pair_keys={'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, pair_indices={'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': PAIR_SCHEMA})
    elif family == 'region':
        common.update(region_key=TEXT, region_kind={'enum': ['exterior', 'hairpin', 'bulge', 'internal', 'multibranch']}, closing_pair_key=nullable(TEXT), immediate_branch_pair_keys={'type': 'array', 'uniqueItems': True, 'items': TEXT}, unpaired_intervals={'type': 'array', 'items': PAIR_SCHEMA})
    return obj(common)

def rna_structure_fact_sources():
    result = {source: {'type': 'array', 'meaning': 'Exactly requested original RNA quantities and specific qualifications; no annotation confidence or implied artifact access.', 'report_schema': {'type': 'array', 'items': rna_structure_row_schema(family), 'x-source': source}} for family, source in FAMILY_SOURCES.items()}
    result[REFERENCE_SOURCE] = {'type': 'array', 'meaning': 'Requested RNA result sources only; no auxiliary bytes or unrequested numerical rows.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': reference('execution_result'), 'x-source': REFERENCE_SOURCE}}
    result[SAVED_SOURCE] = {'type': 'array', 'meaning': 'Explicit original saved-sheet operands for deterministic recalculation; no new acquisition credit.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': SAVED_INPUT_SCHEMA, 'x-source': SAVED_SOURCE}}
    return deepcopy(result)
